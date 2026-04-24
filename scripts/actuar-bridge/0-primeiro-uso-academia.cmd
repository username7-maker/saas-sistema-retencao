@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-actuar-workstation.ps1"
if errorlevel 1 (
  echo.
  echo Falha ao preparar o PC da academia.
  pause
)
