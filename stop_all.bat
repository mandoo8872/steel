@echo off
echo ========================================
echo Steel QR - 모든 서비스 종료
echo ========================================
echo.

echo [종료] 포트 8000 프로세스 찾는 중...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo [종료] PID %%a 종료 중...
    taskkill /F /PID %%a 2>nul
)

echo [종료] 포트 8100 프로세스 찾는 중...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8100.*LISTENING"') do (
    echo [종료] PID %%a 종료 중...
    taskkill /F /PID %%a 2>nul
)

echo.
echo [완료] 모든 서비스가 종료되었습니다.
pause

