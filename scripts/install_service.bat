@echo off
REM Windows 서비스 설치 스크립트

echo QR 스캔 관리 서비스 설치를 시작합니다...

REM 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 이 스크립트는 관리자 권한으로 실행해야 합니다.
    pause
    exit /b 1
)

REM Python 경로 설정 (필요시 수정)
set PYTHON_PATH=python

REM 서비스 설치
echo.
echo 서비스를 설치하는 중...
%PYTHON_PATH% ..\service_win.py install

REM 서비스 설정
echo.
echo 서비스를 설정하는 중...
sc config QRScanService start= auto
sc description QRScanService "QR 기반 인수증/상차증 스캔 관리 서비스 - PDF 파일을 자동으로 처리하고 업로드합니다."

REM 서비스 시작
echo.
echo 서비스를 시작하는 중...
net start QRScanService

echo.
echo 서비스 설치가 완료되었습니다.
echo.
echo 웹 UI 접속: http://localhost:8000
echo 기본 비밀번호: 1212
echo.
pause
