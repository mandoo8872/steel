@echo off
REM Windows 서비스 제거 스크립트

echo QR 스캔 관리 서비스 제거를 시작합니다...

REM 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 이 스크립트는 관리자 권한으로 실행해야 합니다.
    pause
    exit /b 1
)

REM Python 경로 설정 (필요시 수정)
set PYTHON_PATH=python

REM 서비스 중지
echo.
echo 서비스를 중지하는 중...
net stop QRScanService 2>nul

REM 서비스 제거
echo.
echo 서비스를 제거하는 중...
%PYTHON_PATH% ..\service_win.py remove

echo.
echo 서비스 제거가 완료되었습니다.
echo.
pause
