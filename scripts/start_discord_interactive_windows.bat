@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

cd /d "%~dp0.." || exit /b 1

echo Building image (if needed)...
docker build -f Notification\DiscordDockerfile -t discord_shared_image . || exit /b 1

echo Running discord process in interactive mode (Ctrl+C to stop)...
docker run --rm -it -v frbot_logs:/app/logs discord_shared_image python -u Notification/Discord.py /app/logs/shared.log

endlocal

