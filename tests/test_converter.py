import tempfile
import unittest
import wave
from pathlib import Path

import pymupdf
from PIL import Image
from docx import Document

from converter import convert


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.output = self.root / 'output'

    def tearDown(self):
        self.temp.cleanup()

    def test_images_transparency_and_collision(self):
        source = self.root / 'sample.png'
        Image.new('RGBA', (30, 20), (255, 0, 0, 0)).save(source)
        first, _ = convert(source, self.output, 'JPG')
        second, _ = convert(source, self.output, 'JPG')
        self.assertNotEqual(first, second)
        with Image.open(first) as result:
            self.assertEqual(result.size, (30, 20))
            self.assertEqual(result.getpixel((0, 0)), (255, 255, 255))
        png, _ = convert(first, self.output, 'PNG')
        with Image.open(png) as result:
            self.assertEqual(result.format, 'PNG')

    def test_pdf_text_and_image(self):
        source = self.root / 'sample.pdf'
        picture = self.root / 'picture.png'
        Image.new('RGB', (50, 50), 'red').save(picture)
        with pymupdf.open() as pdf:
            page = pdf.new_page()
            page.insert_text((50, 50), 'Hello converter')
            page.insert_image(pymupdf.Rect(50, 80, 100, 130), filename=str(picture))
            pdf.save(source)
        result, _ = convert(source, self.output, 'DOCX')
        document = Document(result)
        self.assertIn('Hello converter', '\n'.join(p.text for p in document.paragraphs))
        self.assertEqual(len(document.inline_shapes), 1)

    def test_audio_roundtrip(self):
        source = self.root / 'sample.wav'
        with wave.open(str(source), 'wb') as audio:
            audio.setparams((1, 2, 22050, 0, 'NONE', 'not compressed'))
            audio.writeframes(b'\x00\x00' * 22050)
        mp3, _ = convert(source, self.output, 'MP3')
        self.assertGreater(mp3.stat().st_size, 1000)
        wav, _ = convert(mp3, self.output, 'WAV')
        with wave.open(str(wav)) as result:
            self.assertAlmostEqual(result.getnframes() / result.getframerate(), 1, delta=0.15)

    def test_invalid_file_cleanup(self):
        source = self.root / 'broken.png'
        source.write_text('invalid')
        with self.assertRaises(Exception):
            convert(source, self.output, 'PNG')
        self.assertEqual(list(self.output.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
