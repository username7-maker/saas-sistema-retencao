@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-actuar-bridge.ps1"
if errorlevel 1 (
  echo.
  echo Falha ao iniciar a bridge.
  pause
)
