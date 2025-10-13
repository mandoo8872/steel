@echo off
echo ========================================
echo Steel QR - 키오스크 모드 시작
echo ========================================
echo.

REM 가상환경 활성화
call .venv\Scripts\activate.bat

echo [시작] 애플리케이션 실행 중...
echo [접속] http://localhost:8000
echo [종료] Ctrl+C를 누르세요
echo.

python main.py --mode kiosk --port 8000

pause

