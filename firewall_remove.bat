@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Steel QR - Windows 방화벽 규칙 제거
echo ========================================
echo.
echo 이 스크립트는 포트 8000과 8100에 대한 인바운드 규칙을 제거합니다.
echo.
echo [포트 8000 규칙 제거 중 (키오스크 모드)]
netsh advfirewall firewall delete rule name="Steel QR - Kiosk Mode (8000)"
echo.
echo [포트 8100 규칙 제거 중 (관리자 모드)]
netsh advfirewall firewall delete rule name="Steel QR - Admin Mode (8100)"
echo.
echo [완료] 방화벽 규칙이 제거되었습니다 (존재했을 경우).
echo.
pause
