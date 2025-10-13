@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Add Poppler to PATH (Permanent)
echo ========================================
echo.
echo This will add Poppler to your system PATH.
echo Administrator permission required.
echo.
pause

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo ERROR: Administrator permission required!
    echo.
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

echo Adding Poppler to PATH...
setx /M PATH "%PATH%;C:\Program Files\poppler\Library\bin"

echo.
echo ========================================
echo SUCCESS!
echo ========================================
echo.
echo Poppler has been added to system PATH.
echo.
echo Please restart your terminal to apply changes.
echo.
pause

