@echo off
REM Launch LEDsim (LEDcommander + desktop panel window)
REM   run_ledsim.bat              scaled default (x15)
REM   run_ledsim.bat --native     true 64x32 panel size
REM   run_ledsim.bat --scale 10   custom zoom
cd /d "%~dp0"

REM ---------------------------------------------------------------------------
REM Kill orphan LEDsim / LEDarcade / multiprocessing spawn children left over
REM from a previous crash (Access Violation, Ctrl+C, closed window, etc.).
REM Only targets python processes whose command line matches LEDarcade/LEDsim
REM or multiprocessing-fork — not every Python on the machine.
REM ---------------------------------------------------------------------------
echo [LEDsim] Pre-launch orphan cleanup...
call :kill_orphans

REM Drop stale bytecode so HWND / frame-IPC fixes always load
if exist "%~dp0ledsim\__pycache__" rd /s /q "%~dp0ledsim\__pycache__" 2>nul
if exist "%~dp0__pycache__\LEDsim*.pyc" del /q "%~dp0__pycache__\LEDsim*.pyc" 2>nul

set LEDARCADE_DISPLAY=sim
set LEDARCADE_STREAM_MODE=0
set LEDARCADE_GAMMA=1.0
set LEDARCADE_SKIP_BOOT_UPDATE=1
set PYTHONUNBUFFERED=1
set PYTHONFAULTHANDLER=1
REM Borderless panel; +/- resizes the whole window. Topmost off (SDL2 topmost AVed).
if not defined LEDARCADE_SIM_BORDERLESS set LEDARCADE_SIM_BORDERLESS=1
if not defined LEDARCADE_SIM_TOPMOST set LEDARCADE_SIM_TOPMOST=0

if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" -X faulthandler -u LEDsim.py %*
) else (
  python -X faulthandler -u LEDsim.py %*
)
set EXITCODE=%ERRORLEVEL%

echo [LEDsim] Post-exit orphan cleanup...
call :kill_orphans

if %EXITCODE% NEQ 0 (
  echo.
  echo LEDsim exited with error code %EXITCODE%.
  if "%EXITCODE%"=="-1073741819" (
    echo That code is Windows ACCESS_VIOLATION ^(0xC0000005^).
    echo Fault log ^(local^): "%~dp0localdata\ledsim_fault.log"
    if exist "%~dp0localdata\ledsim_fault.log" (
      echo ----- ledsim_fault.log -----
      type "%~dp0localdata\ledsim_fault.log"
      echo ----- end -----
    ) else (
      echo ^(no fault log written yet^)
    )
  )
  echo Ensure Python deps are installed:
  echo   .venv\Scripts\pip install pygame pillow numpy flask requests numba
  pause
)
exit /b %EXITCODE%

:kill_orphans
echo [LEDsim] Cleaning orphan Python processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$pat = 'LEDarcade|LEDsim\.py|ledsim|LEDcommander|multiprocessing-fork|multiprocessing\.spawn';" ^
  "$n = 0;" ^
  "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |" ^
  "  Where-Object { $_.Name -match '^python(\.exe)?$' -or $_.Name -match '^pythonw(\.exe)?$' } |" ^
  "  Where-Object { $_.CommandLine -and ($_.CommandLine -match $pat) } |" ^
  "  ForEach-Object {" ^
  "    $procId = $_.ProcessId;" ^
  "    Write-Host ('  taskkill /F /T /PID ' + $procId);" ^
  "    & taskkill.exe /F /T /PID $procId 2>$null | Out-Null;" ^
  "    $n++" ^
  "  };" ^
  "if ($n -eq 0) { Write-Host '  (none)' } else { Write-Host ('  cleaned ' + $n + ' process tree(s)') }"
exit /b 0
