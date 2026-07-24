REM Launch LEDsim (LEDcommander + desktop panel window)
REM   run_ledsim.bat              scaled default (x15)
REM   run_ledsim.bat --native     true 64x32 panel size
REM   run_ledsim.bat --scale 10   custom zoom
cd /d "%~dp0"
set LEDARCADE_DISPLAY=sim
set LEDARCADE_STREAM_MODE=0
set LEDARCADE_GAMMA=1.0
set LEDARCADE_SKIP_BOOT_UPDATE=1
set PYTHONUNBUFFERED=1
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" LEDsim.py %*
) else (
  python LEDsim.py %*
)
if errorlevel 1 (
  echo.
  echo LEDsim exited with an error. Ensure Python deps are installed:
  echo   .venv\Scripts\pip install pygame pillow numpy flask requests numba
  pause
)
