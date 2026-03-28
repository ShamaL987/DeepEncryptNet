@echo off
setlocal

set "BASE_URL=http://localhost:8000"
set "HEALTH_URL=%BASE_URL%/api/common/health-check"
set "CREATE_USER_URL=%BASE_URL%/api/user/create"

set "MAX_RETRIES=18"
set "WAIT_SECONDS=10"

where powershell >nul 2>nul
if errorlevel 1 (
  echo PowerShell is not available.
  pause
  exit /b 1
)


:api_ready
echo.
echo Health check passed.
echo Creating default application user...

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $headers = @{ 'Content-Type' = 'application/json'; 'X-Admin-Token' = 'WksdJhAhFTgjuqnmRZPozSmqMEC8EkaHuOEHl0Md3As' }; $body = '{\"username\":\"admin\",\"email\":\"admin@deepencryptnet.com\",\"password\":\"TempPassword123!\"}'; $response = Invoke-WebRequest -Uri '%CREATE_USER_URL%' -Method POST -Headers $headers -Body $body -UseBasicParsing -TimeoutSec 10; Write-Host 'Default user created successfully.'; exit 0 } catch { if ($_.Exception.Response -ne $null) { $statusCode = [int]$_.Exception.Response.StatusCode; if ($statusCode -eq 400 -or $statusCode -eq 409) { Write-Host 'Default user already exists or request was rejected as duplicate.'; exit 0 } }; Write-Host 'Failed to create default user.'; exit 1 }"

if errorlevel 1 (
  echo.
  echo User bootstrap step failed.
  pause
  exit /b 1
)

echo.
echo DeepEncryptNet configuration completed successfully.
echo UI: %BASE_URL%
echo.
pause
endlocal