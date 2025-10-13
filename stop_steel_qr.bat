@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Steel QR 애플리케이션 종료
echo ========================================
echo.

echo [1/3] Python 프로세스 확인 중...
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo       Python 프로세스 발견 - 종료 중...
    taskkill /IM python.exe /F >nul 2>&1
    echo       ✓ Python 프로세스 종료됨
) else (
    echo       × Python 프로세스 없음
)

echo.
echo [2/3] Py 프로세스 확인 중...
tasklist /FI "IMAGENAME eq py.exe" 2>NUL | find /I /N "py.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo       Py 프로세스 발견 - 종료 중...
    taskkill /IM py.exe /F >nul 2>&1
    echo       ✓ Py 프로세스 종료됨
) else (
    echo       × Py 프로세스 없음
)

echo.
echo [3/3] Steel-QR 실행파일 확인 중...
tasklist /FI "IMAGENAME eq steel-qr.exe" 2>NUL | find /I /N "steel-qr.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo       Steel-QR 프로세스 발견 - 종료 중...
    taskkill /IM steel-qr.exe /F >nul 2>&1
    echo       ✓ Steel-QR 프로세스 종료됨
) else (
    echo       × Steel-QR 프로세스 없음
)

echo.
echo ========================================
echo 종료 완료!
echo ========================================
echo.
pause

