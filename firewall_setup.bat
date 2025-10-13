@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Steel QR - Windows 방화벽 설정
echo ========================================
echo.
echo 이 스크립트는 포트 8000과 8100에 대한 인바운드 규칙을 추가합니다.
echo 다른 기기에서 Steel QR에 접속하려면 방화벽 규칙이 필요합니다.
echo.
echo [포트 8000 규칙 추가 중 (키오스크 모드)]
netsh advfirewall firewall add rule name="Steel QR - Kiosk Mode (8000)" dir=in action=allow protocol=TCP localport=8000 enable=yes
echo.
echo [포트 8100 규칙 추가 중 (관리자 모드)]
netsh advfirewall firewall add rule name="Steel QR - Admin Mode (8100)" dir=in action=allow protocol=TCP localport=8100 enable=yes
echo.
echo [완료] 방화벽 규칙이 성공적으로 추가되었습니다.
echo.
echo 이제 네트워크의 다른 기기에서 Steel QR에 접속할 수 있습니다.
echo.
pause
