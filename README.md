# Ultimate Converter

A Windows desktop app for converting images, PDF documents and audio files, and downloading public YouTube videos. The English interface uses a classic Windows look with resizable panels, batch conversion and a choice of output folder. File conversions run locally.

## Install

Run `release/Ultimate-Converter-Setup-1.0.1.exe` on Windows 10 or 11 (64-bit). Choose an installation folder and optionally create a desktop shortcut. Python, FFmpeg and the Node.js runtime are included; no separate installation is required. Uninstall through **Windows Settings → Apps**.

For the portable build, run `dist/updated/Ultimate Converter/Ultimate Converter.exe`. Copy the entire `Ultimate Converter` folder when moving it to another computer. `Run.bat` also launches the available build.

## Convert files

1. Choose **Images**, **Documents** or **Audio**.
2. Click **Add files…** and select one or more files.
3. Choose the output format and use **Browse…** to select a save location.
4. Click **Convert**. The results dialog shows the output paths and any warnings.

Use **Open folder** to view your converted files. The default location is `Downloads/Ultimate Converter` in your user folder. Original files are preserved, and existing output filenames receive a numeric suffix instead of being overwritten.

| Category | Input | Output |
| --- | --- | --- |
| Images | JPG/JPEG, PNG, WEBP, BMP, TIFF | PNG, JPG, WEBP, BMP, TIFF |
| Documents | PDF | DOCX |
| Audio | WAV, MP3, FLAC, OGG, M4A, AAC | MP3, WAV, FLAC, OGG |
| YouTube | Public video URL, including Shorts | MP4 (H.264/AAC), MP3 (192 kb/s) |

## YouTube

Open the **YouTube** tab, paste a video URL with Ctrl+V, select **MP4** or **MP3**, choose a save location and click **Download and convert**.

For MP4, the app loads the resolutions available for that video. Select a resolution and click **Download selected quality**. Resolutions above 1080p are supported when available. MP3 downloads audio at 192 kb/s without a resolution prompt.

Progress percentages refer to the current audio or video track. Conversion follows the download and uses an indeterminate progress indicator. **Cancel download** stops the operation and removes temporary files.

Only videos available without signing in are supported. Private videos, sign-in-required videos and live streams are not supported. A URL containing a playlist downloads only the selected video. Changes to YouTube may require updating yt-dlp and rebuilding the app.

## Conversion limitations

- PDF conversion preserves text and images in reading order with a simplified layout. Tables, columns and formatting may need adjustments in Word. Scanned pages are inserted as images; OCR is not included. Unlock password-protected PDFs before converting.
- Only the first frame or page of animated or multi-page images is converted. JPG and BMP replace transparency with white.
- MP3 output uses 192 kb/s.

## Run from source

Install Python 3.11 or later. Run `Install.bat` to create a virtual environment, install dependencies and launch the app. The initial dependency installation requires an internet connection.

Alternatively, from the project directory:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

YouTube downloads from source also require Node.js 22+ or Deno. The packaged app includes Node.js. See the [yt-dlp EJS documentation](https://github.com/yt-dlp/yt-dlp/wiki/EJS) for runtime details.

## Build

Install Node.js 22+ and the Python dependencies, then run:

```powershell
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe build_app.py
```

The portable application is written to `dist/updated/Ultimate Converter`.

To build the installer, install Inno Setup in `tools/InnoSetup` or add `ISCC.exe` to `PATH`, then run:

```powershell
.venv\Scripts\python.exe build_installer.py
```

The installer and its SHA-256 checksum are written to `release/`. The version is defined in `installer/UltimateConverter.iss`.

## Tests

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Third-party components

The app uses Pillow, PyMuPDF, python-docx, imageio-ffmpeg, yt-dlp and yt-dlp-ejs. Packaged builds also include FFmpeg and Node.js. Dependency license files and application source files are bundled in the installed `Documentation` folder. Review the licenses of the bundled dependencies before redistributing, particularly PyMuPDF (AGPL/commercial licensing) and FFmpeg.
