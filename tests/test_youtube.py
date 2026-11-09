import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
import wave

from youtube_downloader import DownloadCancelled, download_youtube, encode_media, normalize_url, available_qualities, video_selector


class YouTubeTests(unittest.TestCase):
    def test_available_qualities(self):
        def fmt(height, codec='avc1', drm=False):
            return {'height': height, 'vcodec': codec, 'has_drm': drm, 'url': 'https://example.com/video'}
        info = {'formats': [fmt(720), fmt(1080), fmt(720), fmt(2160), fmt(1440, drm=True), fmt(100, 'none')]}
        self.assertEqual(available_qualities(info), [2160, 1080, 720])
        from yt_dlp import YoutubeDL
        with YoutubeDL({'quiet': True}) as downloader:
            selector = downloader.build_format_selector(video_selector(720))
            formats = [
                {**fmt(720), 'format_id': '720', 'acodec': 'none', 'ext': 'mp4', 'protocol': 'https'},
                {**fmt(1080), 'format_id': '1080', 'acodec': 'none', 'ext': 'mp4', 'protocol': 'https'},
                {**fmt(None, 'none'), 'format_id': 'audio', 'acodec': 'aac', 'ext': 'm4a', 'protocol': 'https'},
            ]
            selected = list(selector({'formats': formats, 'has_merged_format': False, 'incomplete_formats': False}))
            self.assertEqual([item['format_id'] for item in selected], ['720', 'audio'])

    def test_links(self):
        expected = 'https://www.youtube.com/watch?v=BaW_jenozKc'
        for link in ['https://youtu.be/BaW_jenozKc?t=1', 'youtube.com/shorts/BaW_jenozKc', expected + '&list=example', 'https://m.youtube.com/watch?v=BaW_jenozKc']:
            self.assertEqual(normalize_url(link), expected)
        for link in ['', 'https://evil.youtube.com/watch?v=BaW_jenozKc', 'https://youtube.com.evil.com/watch?v=BaW_jenozKc', 'https://youtube.com/playlist?list=abc', 'file:///etc/passwd', 'https://youtu.be/invalid']:
            with self.assertRaises(ValueError, msg=link):
                normalize_url(link)

    def test_download_encode_publish_and_collision(self):
        class FakeDownloader:
            def __init__(self, options):
                self.options = options

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def extract_info(self, url, download):
                path = Path(self.options['outtmpl']).parent / 'audio.wav'
                with wave.open(str(path), 'wb') as audio:
                    audio.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
                    audio.writeframes(b'\0\0' * 22050)
                self.options['progress_hooks'][0]({'status': 'finished'})
                return {'title': 'Test video', 'id': 'BaW_jenozKc', 'requested_downloads': [{'filepath': str(path)}]}

        with tempfile.TemporaryDirectory() as folder, patch('yt_dlp.YoutubeDL', FakeDownloader):
            outputs = [download_youtube('https://youtu.be/BaW_jenozKc', folder, 'MP3', lambda *args: None, threading.Event()) for _ in range(2)]
            self.assertNotEqual(outputs[0], outputs[1])
            self.assertTrue(all(p.stat().st_size > 1000 for p in outputs))
            self.assertEqual(len(list(Path(folder).iterdir())), 2)

    def test_cancel_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            cancel = threading.Event()
            cancel.set()
            with self.assertRaises(DownloadCancelled):
                download_youtube('https://youtu.be/BaW_jenozKc', folder, 'MP3', lambda *args: None, cancel)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_mp4_encoding(self):
        import imageio_ffmpeg
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / 'video.mp4'
            audio = Path(folder) / 'audio.wav'
            output = Path(folder) / 'result.mp4'
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=64x48:d=1', '-an', str(video)], check=True, capture_output=True)
            with wave.open(str(audio), 'wb') as stream:
                stream.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
                stream.writeframes(b'\0\0' * 22050)
            encode_media([video, audio], output, 'MP4', threading.Event())
            result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', str(output), '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
