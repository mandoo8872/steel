@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Poppler Installation Guide
echo ========================================
echo.
echo Poppler is required for PDF to image conversion.
echo.
echo Installation Steps:
echo.
echo 1. Download Poppler:
echo    https://github.com/oschwartz10612/poppler-windows/releases/
echo.
echo 2. Extract to: C:\poppler
echo.
echo 3. Add to PATH:
echo    - Right-click "This PC" - Properties
echo    - Advanced system settings
echo    - Environment Variables
echo    - Edit "Path" variable
echo    - Add: C:\poppler\Library\bin
echo.
echo 4. Restart terminal
echo.
echo 5. Test: poppler --version
echo.
echo ========================================
echo Opening download page...
echo ========================================
start https://github.com/oschwartz10612/poppler-windows/releases/
pause

