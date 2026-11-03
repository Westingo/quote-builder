@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run run.bat once to install Quote Builder, then try again.
  pause
  exit /b 1
)
echo Quote Builder mobile host - keep this window open.
echo Local endpoint: http://127.0.0.1:8487
echo Remote access requires the protected Cloudflare tunnel described in MOBILE.md.
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8487 --proxy-headers --forwarded-allow-ips 127.0.0.1
pause
