@echo off
echo ========================================
echo 내 IP 주소 확인
echo ========================================
echo.

REM IPv4 주소만 표시
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    echo 내 IP: %%a
)

echo.
echo 이 IP를 관리자 모드에 등록하세요.
echo.
pause

