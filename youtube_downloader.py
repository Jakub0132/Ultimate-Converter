"""Download a single YouTube video into a private staging directory."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, urlparse


class DownloadCancelled(Exception):
    pass


def normalize_url(value):
    value = value.strip()
    if not value.startswith(('https://', 'http://')):
        value = 'https://' + value
    parsed = urlparse(value)
    host = (parsed.hostname or '').lower()
    if parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        raise ValueError('Enter a valid YouTube video URL.')
    if host == 'youtu.be':
        video_id = parsed.path.strip('/')
    elif host in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'}:
        parts = parsed.path.strip('/').split('/')
        video_id = parse_qs(parsed.query).get('v', [''])[0] if parsed.path == '/watch' else (parts[1] if len(parts) == 2 and parts[0] in {'shorts', 'embed', 'live'} else '')
    else:
        video_id = ''
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise ValueError('Enter a URL for a single YouTube video, not a channel or playlist.')
    return 'https://www.youtube.com/watch?v=' + video_id


def runtime_options():
    bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'runtime' / 'node.exe'
    node = str(bundled) if bundled.is_file() else shutil.which('node')
    if node:
        return {'node': {'path': node}}
    deno = shutil.which('deno')
    if deno:
        return {'deno': {'path': deno}}
    raise RuntimeError('Node.js (22+) or Deno is missing. Use the complete .exe build or install Node.js.')


def publish_file(source, destination, name):
    number = 0
    while True:
        output = destination / (name.stem + (f' ({number})' if number else '') + name.suffix)
        try:
            with output.open('xb'):
                pass
            break
        except FileExistsError:
            number += 1
    try:
        os.replace(source, output)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return output


def encode_media(inputs, output, target, cancel):
    import imageio_ffmpeg
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-y', '-v', 'error']
    for item in inputs:
        command += ['-i', str(item)]
    if target == 'MP3':
        command += ['-map', '0:a:0', '-vn', '-c:a', 'libmp3lame', '-b:a', '192k']
    else:
        command += ['-map', '0:v:0', '-map', '1:a:0' if len(inputs) > 1 else '0:a:0', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20', '-pix_fmt', 'yuv420p', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart']
    command.append(str(output))
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            while process.poll() is None:
                if cancel.wait(0.2):
                    raise DownloadCancelled('Download cancelled.')
            if process.returncode:
                log.seek(0)
                raise RuntimeError('Conversion failed: ' + log.read().decode('utf-8', errors='replace')[-800:])
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def available_qualities(info):
    """Unique downloadable video heights, excluding audio, storyboards and DRM."""
    return sorted({
        int(fmt['height']) for fmt in info.get('formats', [])
        if fmt.get('height') and fmt.get('vcodec') not in (None, 'none')
        and fmt.get('url') and not fmt.get('has_drm')
    }, reverse=True)


def video_selector(height):
    if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        raise ValueError('Invalid video quality.')
    return f'(bv[height={height}]/b[height={height}]),ba/b'


def download_youtube(url, destination, target, report, cancel, choose_quality=None):
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import sanitize_filename
    url = normalize_url(url)
    if target not in {'MP4', 'MP3'}:
        raise ValueError('Select MP4 or MP3.')
    destination = Path(destination).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    def check_cancel():
        if cancel.is_set():
            raise DownloadCancelled('Download cancelled.')

    class Logger:
        def debug(self, message):
            pass

        def warning(self, message):
            pass

        def error(self, message):
            pass

    def progress(data):
        check_cancel()
        if data['status'] == 'downloading':
            total = data.get('total_bytes') or data.get('total_bytes_estimate')
            percent = min(100, data.get('downloaded_bytes', 0) / total * 100) if total else None
            report('Downloading track' + (f' • {percent:.0f} %' if percent is not None else '…'), percent)
        elif data['status'] == 'finished':
            report('Track downloaded. Processing…', None)

    def filter_video(info, *, incomplete=False):
        check_cancel()
        if info.get('is_live') or info.get('live_status') in {'is_live', 'is_upcoming'}:
            return 'Live streams are not supported. Wait until the stream has ended.'

    options = {
        'noplaylist': True, 'quiet': True, 'no_warnings': True, 'logger': Logger(),
        'socket_timeout': 20, 'retries': 2, 'fragment_retries': 2,
        'js_runtimes': runtime_options(), 'cachedir': False,
        'progress_hooks': [progress], 'match_filter': filter_video,
        'windowsfilenames': True, 'fixup': 'never',
        # Comma downloads independent tracks. Our FFmpeg stage combines them,
        # avoiding the ffprobe dependency absent from imageio-ffmpeg.
        'format': 'ba/b' if target == 'MP3' else ('bv*+ba/b' if choose_quality else '(bv[height<=1080]/b[height<=1080]),ba/b'),
    }
    with tempfile.TemporaryDirectory(prefix='.youtube-', dir=destination) as staging:
        options['outtmpl'] = str(Path(staging) / '%(id)s.%(format_id)s.%(ext)s')
        report('Loading video information…', None)
        check_cancel()
        with YoutubeDL(options) as downloader:
            if target == 'MP4' and choose_quality is not None:
                metadata = downloader.extract_info(url, download=False)
                check_cancel()
                if not metadata or metadata.get('is_live') or metadata.get('live_status') in {'is_live', 'is_upcoming'}:
                    raise ValueError('The video is unavailable or is a live stream.')
                qualities = available_qualities(metadata)
                if not qualities:
                    raise ValueError('No available resolutions were found for this video.')
                selected = choose_quality(metadata.get('title', 'YouTube'), qualities)
                check_cancel()
                if selected not in qualities:
                    raise ValueError('The selected resolution is not available.')
                options['format'] = video_selector(selected)
                report(f'Downloading video at {selected}p…', None)
        # Recreate the downloader so its format selector uses the chosen height.
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
        check_cancel()
        if not info or not info.get('requested_downloads'):
            raise RuntimeError('Unable to download the video. It may be private, unavailable, or live.')
        inputs = [Path(item['filepath']) for item in info['requested_downloads']]
        if any(not item.is_file() for item in inputs):
            raise RuntimeError('The downloaded files are incomplete.')
        report(f'Converting to {target}…', None)
        result = Path(staging) / ('result.' + target.lower())
        encode_media(inputs, result, target, cancel)
        check_cancel()
        name = sanitize_filename(info.get('title') or info['id'], restricted=False)[:120].rstrip(' .') or info['id']
        output = publish_file(result, destination, Path(f'{name} [{info["id"]}].{target.lower()}'))
        report('Done', 100)
        return output
