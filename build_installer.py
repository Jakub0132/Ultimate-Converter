"""Package the existing Windows app as a per-user Inno Setup installer."""
from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import sysconfig

ROOT = Path(__file__).resolve().parent


def main():
    compiler = ROOT / 'tools' / 'InnoSetup' / 'ISCC.exe'
    if not compiler.is_file():
        found = shutil.which('ISCC.exe')
        if not found:
            raise SystemExit('Inno Setup is required: place it in tools/InnoSetup or add ISCC.exe to PATH.')
        compiler = Path(found)
    application = ROOT / 'dist' / 'updated' / 'Ultimate Converter' / 'Ultimate Converter.exe'
    if not application.is_file():
        raise SystemExit('Run build_app.py first.')
    extras = ROOT / 'build' / 'installer-extras'
    sources = extras / 'Source'
    sources.mkdir(parents=True, exist_ok=True)
    for name in ('app.py', 'retro_ui.py', 'converter.py', 'youtube_downloader.py', 'requirements.txt', 'build_app.py', 'build_installer.py', 'README.md'):
        shutil.copy2(ROOT / name, sources / name)
    for name in ('Run.bat', 'Install.bat'):
        shutil.copy2(ROOT / name, sources / name)
    (sources / 'installer').mkdir(exist_ok=True)
    shutil.copy2(ROOT / 'installer' / 'UltimateConverter.iss', sources / 'installer' / 'UltimateConverter.iss')
    shutil.copy2(ROOT / 'README.md', extras / 'README.md')
    for package in Path(sysconfig.get_paths()['purelib']).glob('*.dist-info'):
        for file in package.rglob('*'):
            if file.is_file() and any(word in file.name.lower() for word in ('license', 'copying', 'notice')):
                output = extras / 'Licenses' / package.name / file.relative_to(package)
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, output)
    subprocess.run([str(compiler), str(ROOT / 'installer' / 'UltimateConverter.iss')], check=True, cwd=ROOT)
    version = re.search(r'#define AppVersion "([^"]+)"', (ROOT / 'installer' / 'UltimateConverter.iss').read_text(encoding='utf-8')).group(1)
    setup = ROOT / 'release' / f'Ultimate-Converter-Setup-{version}.exe'
    with setup.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    setup.with_suffix('.sha256').write_text(f'{digest}  {setup.name}\n', encoding='ascii')
    print(f'Installer: {setup}\nSize: {setup.stat().st_size / 1024 / 1024:.1f} MiB')


if __name__ == '__main__':
    main()
