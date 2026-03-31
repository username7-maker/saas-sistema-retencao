@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0pair-actuar-bridge.ps1"
if errorlevel 1 (
  echo.
  echo Falha ao parear a bridge.
  pause
)
