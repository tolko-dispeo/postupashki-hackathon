@echo off
setlocal
cd /d "%~dp0"

where dotnet >nul 2>&1
if errorlevel 1 (
  echo .NET 8 SDK is not installed.
  echo Use the GitHub Actions workflow or install the SDK from https://dotnet.microsoft.com/download
  pause
  exit /b 1
)

echo Building PostupashkiLauncher.exe...
dotnet publish launcher\Postupashki.Launcher.csproj ^
  --configuration Release ^
  --runtime win-x64 ^
  --self-contained true ^
  --output launcher\publish

if errorlevel 1 (
  echo Launcher build failed.
  pause
  exit /b 1
)

echo.
echo Launcher is ready:
echo %CD%\launcher\publish\PostupashkiLauncher.exe
start "" "%CD%\launcher\publish"
pause
