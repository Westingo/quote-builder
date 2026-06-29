@echo off
rem  Shuts down the Quote Builder window/server if it is running.
setlocal
echo Stopping Metro Quote Builder...
rem kill any pythonw running desktop.py (the windowed app + its server)
taskkill /f /im pythonw.exe >nul 2>&1
echo Done.
timeout /t 1 >nul
endlocal
