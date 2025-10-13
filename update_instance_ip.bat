@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
cls
echo ========================================
echo 인스턴스 IP 주소 업데이트 도구
echo ========================================
echo.

REM 현재 IP 확인
echo [1/3] 현재 IP 주소 확인 중...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /C:"IPv4"') do (
    set CURRENT_IP=%%a
    set CURRENT_IP=!CURRENT_IP:~1!
    echo 현재 PC IP: !CURRENT_IP!
)

echo.
echo [2/3] 업데이트할 정보 입력
echo.

set /p INSTANCE_ID="인스턴스 ID (예: kiosk-1): "
set /p NEW_IP="새 IP 주소 (예: 192.168.0.105): "
set /p PORT="포트 번호 (기본: 8000): "

if "!PORT!"=="" set PORT=8000

echo.
echo [3/3] 확인
echo ----------------------------------------
echo 인스턴스 ID:  !INSTANCE_ID!
echo 새 주소:      http://!NEW_IP!:!PORT!
echo ----------------------------------------
echo.

set /p CONFIRM="이대로 진행하시겠습니까? (Y/N): "
if /i not "!CONFIRM!"=="Y" (
    echo 취소되었습니다.
    pause
    exit /b
)

echo.
echo ========================================
echo 다음 단계
echo ========================================
echo.
echo 1. 관리자 모드 열기: http://localhost:8100
echo 2. "인스턴스 레지스트리 편집기" 메뉴 클릭
echo 3. 인스턴스 ID 찾기: !INSTANCE_ID!
echo 4. 주소를 다음으로 변경:
echo    http://!NEW_IP!:!PORT!
echo 5. "저장" 버튼 클릭
echo.
echo 또는 instances.json 파일을 직접 편집하세요.
echo.
pause
