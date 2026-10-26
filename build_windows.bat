@echo off
setlocal
cd /d "%~dp0"

python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Could not install the app packaging dependency.
    exit /b 1
)

python -m PyInstaller --noconfirm --onefile --windowed --clean --add-data "assets;assets" --icon "assets\game_icon.ico" --collect-all pyttsx3 --hidden-import=pyttsx3.drivers.sapi5 --hidden-import=pythoncom --hidden-import=win32com.client --name "Echoes of the Fifty Six Worlds - Requiem of the Maid" main.py
if errorlevel 1 (
    echo.
    echo The Windows app build failed.
    exit /b 1
)

echo.
echo Build complete: %~dp0dist\Echoes of the Fifty Six Worlds - Requiem of the Maid.exe
endlocal
