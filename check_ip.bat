@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Check My IP Address
echo ========================================
echo.

REM Show IPv4 address only
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    echo My IP: %%a
)

echo.
echo Register this IP in Admin Mode.
echo.
pause

