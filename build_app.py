"""Build the portable Windows app, including the YouTube JavaScript runtime."""
from pathlib import Path
import shutil
import subprocess
import sys


if __name__ == '__main__':
    node = shutil.which('node')
    if not node:
        raise SystemExit('Install Node.js 22 or later to build the application.')
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--windowed',
        '--name', 'Ultimate Converter', '--distpath', 'dist/updated', '--collect-all', 'imageio_ffmpeg',
        '--collect-all', 'yt_dlp_ejs', '--collect-submodules', 'yt_dlp',
        '--copy-metadata', 'yt-dlp', '--copy-metadata', 'yt-dlp-ejs',
        '--add-binary', f'{node};runtime', 'app.py',
    ], check=True, cwd=Path(__file__).parent)
