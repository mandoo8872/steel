@echo off
REM Steel QR - 키오스크 모드 시작 스크립트

echo ========================================
echo Steel QR - 키오스크 모드 시작
echo ========================================
echo.

REM 설정 파일 확인
if not exist config.yaml (
    echo [오류] config.yaml 파일이 없습니다.
    echo config.example.yaml을 config.yaml로 복사하고 편집하세요.
    pause
    exit /b 1
)

REM 데이터 폴더 생성
if not exist data mkdir data
if not exist data\scanner_output mkdir data\scanner_output
if not exist data\pending mkdir data\pending
if not exist data\merged mkdir data\merged
if not exist data\uploaded mkdir data\uploaded
if not exist data\error mkdir data\error
if not exist logs mkdir logs

echo [시작] 키오스크 모드 실행 중...
echo [접속] http://localhost:8000
echo [종료] Ctrl+C를 누르세요
echo.

steel-qr.exe --mode kiosk --port 8000

pause

