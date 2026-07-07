@echo off
rem ===================================================================
rem  PUBLISH PRODUCTS
rem  Run this on YOUR machine after you edit Copy_Paste.xlsx.
rem  It rebuilds the product dictionary from the spreadsheet and pushes
rem  it to GitHub, so every employee's app picks up the change the next
rem  time they open it. (Save and CLOSE Copy_Paste.xlsx first.)
rem ===================================================================
setlocal
cd /d "%~dp0"
title Publish Products

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   Please double-click run.bat once first to set things up,
  echo   then run this again.
  echo.
  pause
  exit /b 1
)

echo.
echo   Rebuilding the product list from Copy_Paste.xlsx ...
".venv\Scripts\python.exe" build_codes.py Copy_Paste.xlsx
if errorlevel 1 (
  echo.
  echo   REBUILD FAILED - see the error above. Nothing was published.
  echo   ^(If the spreadsheet is open in Excel, close it and try again.^)
  echo.
  pause
  exit /b 1
)

echo.
echo   Publishing to GitHub ...
git add codes.yaml Copy_Paste.xlsx
git commit -m "Update products" >nul 2>&1
if errorlevel 1 (
  echo   Nothing changed since the last publish - nothing to send.
  echo.
  pause
  exit /b 0
)
git push
if errorlevel 1 (
  echo.
  echo   PUSH FAILED - check your internet connection / GitHub sign-in,
  echo   then run this again.
  echo.
  pause
  exit /b 1
)

echo.
echo   Done. Employees get the updated products the next time they open
echo   the app.
echo.
pause
endlocal
