@echo off
echo ========================================
echo Steel QR - 관리자 모드
echo ========================================
echo.

REM 설정 파일 확인
if not exist config.yaml (
    echo [경고] config.yaml 파일이 없습니다.
    echo config.example.yaml을 config.yaml로 복사하여 사용하세요.
    echo.
)

REM 필수 폴더 확인
if not exist templates (
    echo [오류] templates 폴더가 없습니다.
    echo 원본 프로젝트에서 templates 폴더를 복사하세요.
    pause
    exit /b 1
)
if not exist static (
    echo [오류] static 폴더가 없습니다.
    echo 원본 프로젝트에서 static 폴더를 복사하세요.
    pause
    exit /b 1
)

REM 데이터 폴더 생성
if not exist data mkdir data
if not exist logs mkdir logs

echo [시작] 관리자 모드 실행 중...
echo [접속] http://localhost:8100
echo [사용자] admin
echo [비밀번호] 1212
echo [종료] Ctrl+C를 누르세요
echo.

steel-qr.exe --mode admin --port 8100

pause

