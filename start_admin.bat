@echo off
REM Steel QR - 관리자 모드 시작 스크립트

echo ========================================
echo Steel QR - 관리자 모드 시작
echo ========================================
echo.

REM 설정 파일 확인
if not exist config.yaml (
    echo [오류] config.yaml 파일이 없습니다.
    echo config.example.yaml을 config.yaml로 복사하고 편집하세요.
    pause
    exit /b 1
)

REM 인스턴스 레지스트리 확인
if not exist instances.json (
    echo [경고] instances.json 파일이 없습니다.
    echo instances.example.json을 instances.json으로 복사하고 편집하세요.
    echo.
    echo 계속하려면 아무 키나 누르세요...
    pause > nul
)

REM 로그 폴더 생성
if not exist logs mkdir logs

echo [시작] 관리자 모드 실행 중...
echo [접속] http://localhost:8100
echo [종료] Ctrl+C를 누르세요
echo.

steel-qr.exe --mode admin --port 8100

pause

