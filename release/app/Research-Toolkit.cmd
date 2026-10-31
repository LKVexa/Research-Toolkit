@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Research.ps1" %*
if not "%~1"=="" exit /b %errorlevel%
pause
