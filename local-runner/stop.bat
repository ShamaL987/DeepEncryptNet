@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

docker compose -f "%SCRIPT_DIR%\docker-compose.yml" down

echo.
echo DeepEncryptNet stopped.
pause
endlocal