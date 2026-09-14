@echo off
setlocal
cd /d "%~dp0"

docker compose down
if errorlevel 1 (
  echo Docker Compose could not stop the project.
  pause
  exit /b 1
)

echo Postupashki containers stopped. Demo data was preserved.
pause

