@echo off
echo ========================================
echo Steel QR - Windows 방화벽 규칙 제거
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

echo [1/2] 포트 8000 방화벽 규칙 제거 중...
netsh advfirewall firewall delete rule name="Steel QR - Kiosk Mode (8000)" >nul 2>&1
if %errorLevel% EQU 0 (
    echo       ✓ 포트 8000 규칙 제거 완료
) else (
    echo       × 포트 8000 규칙을 찾을 수 없습니다
)

echo [2/2] 포트 8100 방화벽 규칙 제거 중...
netsh advfirewall firewall delete rule name="Steel QR - Admin Mode (8100)" >nul 2>&1
if %errorLevel% EQU 0 (
    echo       ✓ 포트 8100 규칙 제거 완료
) else (
    echo       × 포트 8100 규칙을 찾을 수 없습니다
)

echo.
echo ========================================
echo 방화벽 규칙 제거 완료!
echo ========================================
echo.
pause

