@echo off
:loop
echo time sync...
w32tm /resync
if %errorlevel% equ 0 (
    echo sync sucess.
) else (
    echo failed.
)
timeout /t 3600 /nobreak > nul
goto loop
