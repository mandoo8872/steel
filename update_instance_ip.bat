@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
cls
echo ========================================
echo Instance IP Update Tool
echo ========================================
echo.

REM Check current IP
echo [1/3] Checking current IP address...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    set CURRENT_IP=%%a
    set CURRENT_IP=!CURRENT_IP:~1!
    echo Current PC IP: !CURRENT_IP!
)

echo.
echo [2/3] Enter the information to update
echo.

set /p INSTANCE_ID="Instance ID (e.g., kiosk-1): "
set /p NEW_IP="New IP Address (e.g., 192.168.0.105): "
set /p PORT="Port Number (default: 8000): "

if "!PORT!"=="" set PORT=8000

echo.
echo [3/3] Confirm
echo ----------------------------------------
echo Instance ID:  !INSTANCE_ID!
echo New Address:  http://!NEW_IP!:!PORT!
echo ----------------------------------------
echo.

set /p CONFIRM="Is this correct? (Y/N): "
if /i not "!CONFIRM!"=="Y" (
    echo Cancelled.
    pause
    exit /b
)

echo.
echo ========================================
echo Next Steps
echo ========================================
echo.
echo 1. Open Admin Mode: http://localhost:8100
echo 2. Click "Instance Registry Editor" menu
echo 3. Find Instance ID: !INSTANCE_ID!
echo 4. Change address to:
echo    http://!NEW_IP!:!PORT!
echo 5. Click "Save" button
echo.
echo Or edit instances.json file directly.
echo.
pause

