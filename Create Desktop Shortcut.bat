@echo off
rem  Puts a "Metro Quote Builder" icon on your Desktop that launches the
rem  app through run.bat so GitHub updates are checked on every launch.
rem  The launcher runs minimized. Run run.bat once first so the
rem  environment exists.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  echo.
  echo   Run run.bat once first to set things up, then run this again.
  echo.
  pause
  exit /b 1
)

set "WORKDIR=%~dp0"

powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Metro Quote Builder.lnk'); $s.TargetPath=$env:ComSpec; $s.Arguments='/d /c '+[char]34+[char]34+(Join-Path $env:WORKDIR 'run.bat')+[char]34+[char]34; $s.WorkingDirectory=$env:WORKDIR; $s.WindowStyle=7; $s.IconLocation=(Join-Path $env:WORKDIR '.venv\Scripts\pythonw.exe'); $s.Save()"

echo.
echo   Created "Metro Quote Builder" on your Desktop.
echo   Double-click it any time to open the app.
echo   It will check GitHub for updates before opening.
echo.
pause
endlocal
