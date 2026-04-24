@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch-actuar-workstation.ps1"
if errorlevel 1 (
  echo.
  echo Falha ao abrir o modo academia.
  pause
)
