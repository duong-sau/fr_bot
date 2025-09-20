@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

REM Change to repo root if needed
cd /d "%~dp0.." || exit /b 1

REM Build image
echo Building discord_shared_image...
docker build -f Notification\DiscordDockerfile -t discord_shared_image .
if errorlevel 1 (
  echo Build failed. Please ensure Docker Desktop is running.
  exit /b 1
)

REM Ensure logs volume exists
echo Creating volume frbot_logs (if missing)...
docker volume create frbot_logs >NUL 2>&1

REM Remove old container if exists
echo Removing old container (if exists)...
docker stop discord_shared_container >NUL 2>&1
docker rm discord_shared_container >NUL 2>&1

REM Create container with log volume
echo Creating container discord_shared_container...
docker create --name discord_shared_container -v frbot_logs:/app/logs discord_shared_image
if errorlevel 1 (
  echo Failed to create container.
  exit /b 1
)

REM Start container
echo Starting container...
docker start discord_shared_container
if errorlevel 1 (
  echo Failed to start container.
  exit /b 1
)

echo Discord process started successfully.
endlocal

