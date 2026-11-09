@echo off
cd /d "%~dp0"
if exist "dist\updated\Ultimate Converter\Ultimate Converter.exe" (
    start "" "dist\updated\Ultimate Converter\Ultimate Converter.exe"
    exit /b
)
if not exist ".venv\Scripts\pythonw.exe" (
    echo Run Install.bat first.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "app.py"
