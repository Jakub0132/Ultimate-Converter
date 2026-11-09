"""Local conversion engine. Originals are never overwritten."""
from pathlib import Path
import io
import os
import subprocess
import tempfile

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac'}
MODES = {
    'Images': ('PNG', 'JPG', 'WEBP', 'BMP', 'TIFF'),
    'Documents': ('DOCX',),
    'Audio': ('MP3', 'WAV', 'FLAC', 'OGG'),
}


def accepts(path, mode):
    ext = Path(path).suffix.lower()
    return ext in (IMAGE_EXTENSIONS if mode == 'Images' else AUDIO_EXTENSIONS if mode == 'Audio' else {'.pdf'})


def convert(source, destination, target):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    target = target.lower()
    warning = ''
    fd, temporary = tempfile.mkstemp(prefix='.converter-', suffix='.' + target, dir=destination)
    os.close(fd)
    temporary = Path(temporary)
    try:
        if source.suffix.lower() in IMAGE_EXTENSIONS and target in {'png', 'jpg', 'webp', 'bmp', 'tiff'}:
            from PIL import Image, ImageOps
            with Image.open(source) as original:
                picture = ImageOps.exif_transpose(original)
                if getattr(original, 'n_frames', 1) > 1:
                    warning = 'Only the first frame or page of the image was converted.'
                if target in {'jpg', 'bmp'}:
                    rgba = picture.convert('RGBA')
                    picture = Image.new('RGB', rgba.size, 'white')
                    picture.paste(rgba, mask=rgba.getchannel('A'))
                elif picture.mode not in {'RGB', 'RGBA', 'L', 'LA', 'P'}:
                    picture = picture.convert('RGBA')
                picture.save(temporary, format={'jpg': 'JPEG'}.get(target, target.upper()), **({'quality': 95} if target in {'jpg', 'webp'} else {}))
        elif source.suffix.lower() == '.pdf' and target == 'docx':
            import pymupdf
            from docx import Document
            from docx.shared import Inches, Pt
            document = Document()
            document.styles['Normal'].font.name = 'Calibri'
            document.styles['Normal'].font.size = Pt(11)
            text_found = False
            with pymupdf.open(source) as pdf:
                if pdf.needs_pass:
                    raise ValueError('This PDF is password-protected. Unlock it first.')
                for index, page in enumerate(pdf):
                    if index:
                        document.add_page_break()
                    for block in page.get_text('dict', sort=True)['blocks']:
                        if block['type'] == 0:
                            lines = [''.join(span['text'] for span in line['spans']) for line in block['lines']]
                            value = '\n'.join(lines).strip()
                            if value:
                                document.add_paragraph(value)
                                text_found = True
                        elif block['type'] == 1:
                            from PIL import Image
                            with Image.open(io.BytesIO(block['image'])) as img:
                                normalized = io.BytesIO()
                                img.convert('RGB').save(normalized, format='PNG')
                                normalized.seek(0)
                                document.add_picture(normalized, width=Inches(min(block['width'] / 72, 6)))
            if not text_found:
                warning = 'This PDF contains no readable text. Images were added to Word; OCR is not available.'
            else:
                warning = 'The layout is simplified; check tables and columns in Word.'
            document.save(temporary)
        elif source.suffix.lower() in AUDIO_EXTENSIONS and target in {'mp3', 'wav', 'flac', 'ogg'}:
            import imageio_ffmpeg
            codec = {'mp3': ['-c:a', 'libmp3lame', '-b:a', '192k'], 'wav': ['-c:a', 'pcm_s16le'], 'flac': ['-c:a', 'flac'], 'ogg': ['-c:a', 'libvorbis', '-q:a', '5']}[target]
            result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-y', '-v', 'error', '-i', str(source), '-map', '0:a:0', '-vn', *codec, str(temporary)], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if result.returncode:
                raise ValueError('Audio conversion failed: ' + result.stderr.decode('utf-8', errors='replace')[-500:])
        else:
            raise ValueError('This format combination is not supported.')
        # Reserve a unique filename atomically, including across application instances.
        number = 0
        while True:
            suffix = f' ({number})' if number else ''
            output = destination / f'{source.stem}{suffix}.{target}'
            try:
                with output.open('xb'):
                    pass
                break
            except FileExistsError:
                number += 1
        try:
            os.replace(temporary, output)
        except Exception:
            output.unlink(missing_ok=True)
            raise
        return output, warning
    finally:
        temporary.unlink(missing_ok=True)
