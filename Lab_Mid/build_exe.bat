@echo off
REM Builds RenderServer.exe and RenderClient.exe into the "dist" folder (run on Windows).
cd /d "%~dp0"

REM Find a working Python: try the "py" launcher first, then "python"
set PY=
py -3 -c "import sys" >nul 2>&1 && set PY=py -3
if not defined PY (
  python -c "import sys" >nul 2>&1 && set PY=python
)
if not defined PY (
  echo Could not find Python. Install it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during setup, then run this again.
  goto :err
)
echo Using: %PY%

%PY% -m pip install --upgrade pyinstaller -r client\requirements.txt || goto :err

echo.
echo === Building RenderServer.exe ===
cd server
%PY% -m PyInstaller --noconfirm --onefile --console --name RenderServer server.py || goto :err
cd ..

echo.
echo === Building RenderClient.exe ===
cd client
%PY% -m PyInstaller --noconfirm --onefile --windowed --name RenderClient --collect-all customtkinter --hidden-import psutil gui.py || goto :err
cd ..

if not exist dist mkdir dist
copy /y server\dist\RenderServer.exe dist\ >nul
copy /y client\dist\RenderClient.exe dist\ >nul
echo.
echo Done. Your files are in the "dist" folder:
echo   dist\RenderServer.exe   (worker laptop)
echo   dist\RenderClient.exe   (client laptop)
echo NOTE: FFmpeg must still be installed on PATH (winget install ffmpeg).
pause
exit /b 0

:err
echo.
echo BUILD FAILED - see the messages above.
pause
exit /b 1
