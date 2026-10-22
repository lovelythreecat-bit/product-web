@echo off
setlocal
title Ecommerce AI - Complete Backend Stack

rem The PowerShell entry locates all paths relative to the project, including Unicode paths.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0infra\scripts\restart-api.ps1" %*
set "runtimeExitCode=%errorlevel%"

echo.
if not "%runtimeExitCode%"=="0" (
    echo Backend stack startup or health check failed. See the service and log path above.
) else (
    echo Launcher finished. Services continue running in the background.
)
pause
exit /b %runtimeExitCode%
