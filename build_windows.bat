@echo off
setlocal
cd /d "%~dp0"

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Could not install the app packaging dependency.
    exit /b 1
)

python -m PyInstaller --noconfirm --onefile --windowed --clean --add-data "assets;assets" --collect-all pyttsx3 --hidden-import=pyttsx3.drivers.sapi5 --hidden-import=pythoncom --hidden-import=win32com.client --name FiftySixLives main.py
if errorlevel 1 (
    echo.
    echo The Windows app build failed.
    exit /b 1
)

echo.
echo Build complete: %~dp0dist\FiftySixLives.exe
endlocal
