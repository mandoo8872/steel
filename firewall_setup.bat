@echo off
echo ========================================
echo Steel QR - Windows 방화벽 설정
echo ========================================
echo.

REM 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [오류] 이 스크립트는 관리자 권한이 필요합니다.
    echo.
    echo 우클릭 후 "관리자 권한으로 실행"을 선택하세요.
    echo.
    pause
    exit /b 1
)

echo [1/2] 포트 8000 (키오스크 모드) 허용 규칙 추가 중...
netsh advfirewall firewall add rule name="Steel QR - Kiosk Mode (8000)" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1
if %errorLevel% EQU 0 (
    echo       ✓ 포트 8000 허용 완료
) else (
    echo       ✓ 포트 8000 규칙이 이미 존재합니다
)

echo [2/2] 포트 8100 (관리자 모드) 허용 규칙 추가 중...
netsh advfirewall firewall add rule name="Steel QR - Admin Mode (8100)" dir=in action=allow protocol=TCP localport=8100 >nul 2>&1
if %errorLevel% EQU 0 (
    echo       ✓ 포트 8100 허용 완료
) else (
    echo       ✓ 포트 8100 규칙이 이미 존재합니다
)

echo.
echo ========================================
echo 방화벽 설정 완료!
echo ========================================
echo.
echo 이제 다른 기기에서 접속할 수 있습니다:
echo   - 키오스크: http://192.168.0.191:8000
echo   - 관리자:   http://192.168.0.191:8100
echo.
pause

