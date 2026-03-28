@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "HOST_FILES_DIR=%SCRIPT_DIR%"

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker is not installed or not available in PATH.
  pause
  exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
  echo Docker Compose is not available.
  pause
  exit /b 1
)

echo Using mounted folder:
echo %HOST_FILES_DIR%
echo.
echo Starting DeepEncryptNet...
echo Keep this window open while the container is running.
echo Press Ctrl+C to stop everything cleanly.
echo.

docker compose -f "%SCRIPT_DIR%\docker-compose.yml" up --pull always --remove-orphans

echo.
echo DeepEncryptNet stopped.
pause
endlocal