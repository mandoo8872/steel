@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo 내 PC IP 주소 확인
echo ========================================
echo.

REM IPv4 주소만 표시
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    echo 내 IP 주소: %%a
)

echo.
echo 관리자 모드에서 이 IP를 등록하세요.
echo.
pause
