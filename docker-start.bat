@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker is not installed. Install and start Docker Desktop, then try again.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running. Start it and try again.
  pause
  exit /b 1
)

echo Building and starting Postupashki...
docker compose up --build -d
if errorlevel 1 (
  echo Docker Compose could not start the project.
  docker compose logs --tail=80
  pause
  exit /b 1
)

echo Waiting for the dashboard...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$deadline = (Get-Date).AddMinutes(3); " ^
  "do { try { $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8080/health' -TimeoutSec 3; if ($response.StatusCode -eq 200) { exit 0 } } catch {}; Start-Sleep -Seconds 2 } while ((Get-Date) -lt $deadline); exit 1"

if errorlevel 1 (
  echo The project started, but the health check did not become ready.
  docker compose ps
  docker compose logs --tail=80
  pause
  exit /b 1
)

echo Postupashki is ready: http://127.0.0.1:8080
start "" "http://127.0.0.1:8080"
docker compose ps
echo.
echo The containers will keep running after this window closes.
echo Use docker-stop.bat to stop them.
pause

