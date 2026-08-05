@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\audit.ps1" %*
exit /b %ERRORLEVEL%
