"""
Windows 실행파일 빌드 스크립트
PyInstaller를 사용하여 단일 실행파일 생성
"""
import PyInstaller.__main__
import shutil
import os
from pathlib import Path

def build_windows_exe():
    """Windows .exe 파일 빌드"""
    
    # 기존 빌드 폴더 정리
    dist_dir = Path("dist")
    build_dir = Path("build")
    
    # dist 폴더가 잠겨있을 경우를 대비해 파일만 삭제
    try:
        if dist_dir.exists():
            for file in dist_dir.glob("*"):
                if file.is_file():
                    try:
                        file.unlink()
                    except:
                        pass
    except:
        pass
    
    if build_dir.exists():
        try:
            shutil.rmtree(build_dir)
        except:
            pass
    
    print("=" * 70)
    print("Steel QR - Windows 실행파일 빌드")
    print("=" * 70)
    
    # PyInstaller 옵션
    pyinstaller_args = [
        'main.py',                      # 진입점
        '--name=steel-qr',              # 실행파일 이름
        '--onefile',                    # 단일 파일로 패키징
        '--console',                    # 콘솔 창 표시 (로그 확인용)
        '--icon=NONE',                  # 아이콘 (나중에 추가 가능)
        
        # 데이터 파일 포함
        '--add-data=templates;templates',           # 템플릿
        '--add-data=static;static',                 # 정적 파일
        '--add-data=config.example.yaml;.',         # 설정 예제
        '--add-data=instances.example.json;.',      # 인스턴스 레지스트리 예제
        
        # pyzbar DLL 파일 포함
        '--add-binary=.venv/Lib/site-packages/pyzbar/libiconv.dll;pyzbar',
        '--add-binary=.venv/Lib/site-packages/pyzbar/libzbar-64.dll;pyzbar',
        
        # 숨겨진 imports (FastAPI, Uvicorn 등)
        '--hidden-import=uvicorn',
        '--hidden-import=uvicorn.logging',
        '--hidden-import=uvicorn.loops',
        '--hidden-import=uvicorn.loops.auto',
        '--hidden-import=uvicorn.protocols',
        '--hidden-import=uvicorn.protocols.http',
        '--hidden-import=uvicorn.protocols.http.auto',
        '--hidden-import=uvicorn.protocols.websockets',
        '--hidden-import=uvicorn.protocols.websockets.auto',
        '--hidden-import=uvicorn.lifespan',
        '--hidden-import=uvicorn.lifespan.on',
        '--hidden-import=fastapi',
        '--hidden-import=pydantic',
        '--hidden-import=sqlalchemy',
        '--hidden-import=watchdog',
        '--hidden-import=watchdog.observers',
        '--hidden-import=pyzbar',
        '--hidden-import=cv2',
        '--hidden-import=PIL',
        '--hidden-import=PyPDF2',
        '--hidden-import=pikepdf',
        '--hidden-import=cryptography',
        '--hidden-import=yaml',
        '--hidden-import=loguru',
        '--hidden-import=httpx',
        
        # Windows 전용
        '--hidden-import=win32api',
        '--hidden-import=win32con',
        '--hidden-import=win32event',
        '--hidden-import=win32service',
        '--hidden-import=win32serviceutil',
        
        # 최적화
        '--clean',                      # 빌드 전 정리
        '--noconfirm',                  # 확인 없이 진행
        
        # 콘솔 로그 (빌드 시)
        '--log-level=INFO',
    ]
    
    print("\n빌드 시작...")
    print(f"진입점: main.py")
    print(f"출력: dist/steel-qr.exe")
    print()
    
    # 빌드 실행
    PyInstaller.__main__.run(pyinstaller_args)
    
    print("\n" + "=" * 70)
    print("✅ 빌드 완료! 추가 파일 복사 중...")
    print("=" * 70)
    
    # 빌드 후 처리: 필수 파일 및 폴더 복사
    post_build_setup(dist_dir)
    
    print("\n" + "=" * 70)
    print("🎉 모든 작업 완료!")
    print("=" * 70)
    print(f"\n실행파일 위치: {dist_dir / 'steel-qr.exe'}")
    print("\n배포 패키지 구성:")
    print("  ✓ steel-qr.exe         - 실행 파일")
    print("  ✓ run_kiosk.bat        - 키오스크 모드 실행")
    print("  ✓ run_admin.bat        - 관리자 모드 실행")
    print("  ✓ firewall_setup.bat   - 방화벽 설정 (관리자 권한)")
    print("  ✓ firewall_remove.bat  - 방화벽 규칙 제거")
    print("  ✓ check_ip.bat         - IP 주소 확인")
    print("  ✓ setup_static_ip.bat  - 고정 IP 설정 (권장)")
    print("  ✓ update_instance_ip.bat - IP 변경 도구")
    print("  ✓ stop_steel_qr.bat    - 애플리케이션 종료")
    print("  ✓ README.txt           - 사용 설명서")
    print("  ✓ config.yaml          - 기본 설정 파일")
    print("  ✓ templates/           - HTML 템플릿")
    print("  ✓ static/              - 정적 파일")
    print("\n사용 방법:")
    print("  1. firewall_setup.bat을 관리자 권한으로 실행 (최초 1회)")
    print("  2. run_kiosk.bat 또는 run_admin.bat 실행")
    print("\n배포:")
    print("  dist 폴더 전체를 압축하여 배포하세요.")
    print("=" * 70)

def post_build_setup(dist_dir: Path):
    """빌드 후 필수 파일 복사"""
    print("\n[1/9] templates 폴더 복사 중...")
    src_templates = Path("templates")
    dst_templates = dist_dir / "templates"
    if src_templates.exists():
        if dst_templates.exists():
            shutil.rmtree(dst_templates)
        shutil.copytree(src_templates, dst_templates)
        print(f"      ✓ {src_templates} → {dst_templates}")
    else:
        print(f"      ⚠ templates 폴더를 찾을 수 없습니다")
    
    print("\n[2/9] static 폴더 복사 중...")
    src_static = Path("static")
    dst_static = dist_dir / "static"
    if src_static.exists():
        if dst_static.exists():
            shutil.rmtree(dst_static)
        shutil.copytree(src_static, dst_static)
        print(f"      ✓ {src_static} → {dst_static}")
    else:
        print(f"      ⚠ static 폴더를 찾을 수 없습니다")
    
    print("\n[3/7] config.yaml 복사 중...")
    src_config = Path("config.yaml")
    src_config_example = Path("config.example.yaml")
    dst_config = dist_dir / "config.yaml"
    
    if src_config.exists():
        shutil.copy2(src_config, dst_config)
        print(f"      ✓ {src_config} → {dst_config}")
    elif src_config_example.exists():
        shutil.copy2(src_config_example, dst_config)
        print(f"      ✓ {src_config_example} → {dst_config} (예제 파일 복사)")
    else:
        print(f"      ⚠ config.yaml 파일을 찾을 수 없습니다")
    
    print("\n[4/7] instances.json 생성 중...")
    dst_instances = dist_dir / "instances.json"
    if not dst_instances.exists():
        # 빈 instances.json 파일 생성
        import json
        instances_data = {
            "version": 1,
            "instances": []
        }
        with open(dst_instances, 'w', encoding='utf-8') as f:
            json.dump(instances_data, f, indent=2, ensure_ascii=False)
        print(f"      ✓ instances.json 생성 완료")
    else:
        print(f"      ✓ instances.json (이미 존재)")
    
    print("\n[5/9] 실행 배치 파일 생성 중...")
    
    # run_kiosk.bat 생성
    run_kiosk_content = """@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Steel QR - 키오스크 모드
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
if not exist data\\scanner_output mkdir data\\scanner_output
if not exist data\\pending mkdir data\\pending
if not exist data\\merged mkdir data\\merged
if not exist data\\uploaded mkdir data\\uploaded
if not exist data\\error mkdir data\\error
if not exist logs mkdir logs

echo [시작] 키오스크 모드 실행 중...
echo [접속] http://localhost:8000
echo [사용자] admin
echo [비밀번호] 1212
echo [종료] Ctrl+C를 누르세요
echo.

steel-qr.exe --mode kiosk --port 8000

pause
"""
    with open(dist_dir / "run_kiosk.bat", 'w', encoding='utf-8-sig') as f:
        f.write(run_kiosk_content)
    print(f"      ✓ run_kiosk.bat (UTF-8)")
    
    # run_admin.bat 생성
    run_admin_content = """@echo off
chcp 65001 >nul 2>&1
cls
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
"""
    with open(dist_dir / "run_admin.bat", 'w', encoding='utf-8-sig') as f:
        f.write(run_admin_content)
    print(f"      ✓ run_admin.bat (UTF-8)")
    
    print("\n[6/9] 방화벽 배치 파일 생성 중...")
    
    # firewall_setup.bat 생성
    firewall_setup_content = """@echo off
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
"""
    with open(dist_dir / "firewall_setup.bat", 'w', encoding='utf-8-sig') as f:
        f.write(firewall_setup_content)
    print(f"      ✓ firewall_setup.bat (UTF-8)")
    
    # firewall_remove.bat 생성
    firewall_remove_content = """@echo off
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
"""
    with open(dist_dir / "firewall_remove.bat", 'w', encoding='utf-8-sig') as f:
        f.write(firewall_remove_content)
    print(f"      ✓ firewall_remove.bat (UTF-8)")
    
    print("\n[7/9] 종료 배치 파일 생성 중...")
    stop_content = """@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo Steel QR 애플리케이션 종료
echo ========================================
echo.

echo [1/3] Python 프로세스 확인 중...
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I /N "python.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo       Python 프로세스 발견 - 종료 중...
    taskkill /IM python.exe /F >nul 2>&1
    echo       ✓ Python 프로세스 종료됨
) else (
    echo       × Python 프로세스 없음
)

echo.
echo [2/3] Py 프로세스 확인 중...
tasklist /FI "IMAGENAME eq py.exe" 2>NUL | find /I /N "py.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo       Py 프로세스 발견 - 종료 중...
    taskkill /IM py.exe /F >nul 2>&1
    echo       ✓ Py 프로세스 종료됨
) else (
    echo       × Py 프로세스 없음
)

echo.
echo [3/3] Steel-QR 실행파일 확인 중...
tasklist /FI "IMAGENAME eq steel-qr.exe" 2>NUL | find /I /N "steel-qr.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo       Steel-QR 프로세스 발견 - 종료 중...
    taskkill /IM steel-qr.exe /F >nul 2>&1
    echo       ✓ Steel-QR 프로세스 종료됨
) else (
    echo       × Steel-QR 프로세스 없음
)

echo.
echo ========================================
echo 종료 완료!
echo ========================================
echo.
pause
"""
    with open(dist_dir / "stop_steel_qr.bat", 'w', encoding='utf-8-sig') as f:
        f.write(stop_content)
    print(f"      ✓ stop_steel_qr.bat (UTF-8)")
    
    print("\n[8/9] IP 관리 배치 파일 생성 중...")
    
    # check_ip.bat 생성
    check_ip_content = """@echo off
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
"""
    with open(dist_dir / "check_ip.bat", 'w', encoding='utf-8-sig') as f:
        f.write(check_ip_content)
    print(f"      ✓ check_ip.bat (UTF-8)")
    
    # setup_static_ip.bat 생성  
    setup_static_ip_content = """@echo off
chcp 65001 >nul 2>&1
cls
echo ========================================
echo 고정 IP 설정 안내
echo ========================================
echo.
echo 이 스크립트는 고정 IP 설정 방법을 안내합니다.
echo.
echo [자동 설정 - 관리자 권한 필요]
echo Windows 네트워크 설정 창을 엽니다.
echo.
pause

REM 네트워크 설정 열기
start ms-settings:network-ethernet

echo.
echo ========================================
echo 고정 IP 설정 방법
echo ========================================
echo.
echo 1. "이더넷" 또는 "Wi-Fi" 클릭
echo 2. "IP 할당" - "편집" 클릭
echo 3. "수동" 선택
echo 4. IPv4 켜기
echo 5. 다음 정보 입력:
echo.
echo    IP 주소:      192.168.0.XXX  (예: 192.168.0.101)
echo    서브넷:       255.255.255.0
echo    게이트웨이:   192.168.0.1    (공유기 IP, 보통 .1 또는 .254)
echo    기본 DNS:     8.8.8.8        (Google DNS)
echo    보조 DNS:     8.8.4.4
echo.
echo 6. "저장" 클릭
echo.
echo ========================================
echo 권장 IP 할당 (안전한 범위)
echo ========================================
echo.
echo 옵션 1: 높은 범위 (가장 안전) - 권장
echo ------------------------------------------------
echo 관리자 PC:    192.168.0.200
echo 키오스크 1:   192.168.0.201
echo 키오스크 2:   192.168.0.202
echo 키오스크 3:   192.168.0.203
echo.
echo 옵션 2: 중간 범위
echo ------------------------------------------------
echo 관리자 PC:    192.168.0.150
echo 키오스크 1:   192.168.0.151
echo 키오스크 2:   192.168.0.152
echo 키오스크 3:   192.168.0.153
echo.
echo * DHCP 범위는 보통: 192.168.0.2 ~ 192.168.0.100
echo * .200+ 대역 사용으로 DHCP 충돌 방지
echo * 공유기 설정 확인: http://192.168.0.1
echo.
pause
"""
    with open(dist_dir / "setup_static_ip.bat", 'w', encoding='utf-8-sig') as f:
        f.write(setup_static_ip_content)
    print(f"      ✓ setup_static_ip.bat (UTF-8)")
    
    # update_instance_ip.bat 생성
    update_instance_ip_content = """@echo off
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
"""
    with open(dist_dir / "update_instance_ip.bat", 'w', encoding='utf-8-sig') as f:
        f.write(update_instance_ip_content)
    print(f"      ✓ update_instance_ip.bat (UTF-8)")
    
    print("\n[9/9] README.txt 생성 중...")
    # 항상 최신 버전으로 덮어쓰기
    src_readme = dist_dir / "README.txt"
    readme_content = """========================================
Steel QR - Windows 단독 실행파일
========================================

## 🚀 빠른 시작

### 1단계: 방화벽 설정 (최초 1회)
   - firewall_setup.bat 우클릭 → "관리자 권한으로 실행"

### 2단계: 내 IP 확인
   - check_ip.bat 실행 → IP 주소 메모

### 3단계: 실행
   - 키오스크 모드: run_kiosk.bat 더블클릭
   - 관리자 모드: run_admin.bat 더블클릭

========================================

## 📡 네트워크 구성 (중요!)

### 배포 시나리오
- 관리자 PC 1대: steel-qr.exe (관리자 모드)
- 키오스크 PC 3대: steel-qr.exe (키오스크 모드)

### IP 주소는 각 PC마다 다름!
예시:
  - 관리자 PC:   192.168.0.100 (8100 포트)
  - 키오스크 1:  192.168.0.101 (8000 포트)
  - 키오스크 2:  192.168.0.102 (8000 포트)
  - 키오스크 3:  192.168.0.103 (8000 포트)

⚠️ 각 PC는 다른 기기이므로 포트 충돌 없음!

========================================

## 📝 설치 가이드

### 관리자 PC (1대)
1. dist 폴더 전체 복사
2. firewall_setup.bat 실행 (관리자 권한)
3. run_admin.bat 실행
4. http://localhost:8100 접속
5. 각 키오스크의 IP 주소 등록
   예: http://192.168.0.101:8000

### 키오스크 PC (3대)
1. dist 폴더 전체 복사
2. firewall_setup.bat 실행 (관리자 권한)
3. check_ip.bat 실행 → IP 확인
4. run_kiosk.bat 실행
5. 확인된 IP를 관리자에게 알림

========================================

## 🔑 기본 계정

사용자명: admin
비밀번호: 1212

config.yaml에서 변경 가능

========================================

## 📂 포함된 파일

✓ steel-qr.exe          실행 파일
✓ run_kiosk.bat         키오스크 모드 실행
✓ run_admin.bat         관리자 모드 실행
✓ firewall_setup.bat    방화벽 설정
✓ firewall_remove.bat   방화벽 규칙 제거
✓ check_ip.bat          내 IP 주소 확인
✓ setup_static_ip.bat   고정 IP 설정 안내
✓ update_instance_ip.bat IP 변경 시 인스턴스 수정 도구
✓ stop_steel_qr.bat     애플리케이션 종료
✓ README.txt            이 파일
✓ config.yaml           설정 파일
✓ instances.json        인스턴스 레지스트리 (자동 생성됨)
✓ templates/            HTML 템플릿
✓ static/               정적 파일

========================================

## 🛑 종료 방법

1. 배치 파일 사용 (권장)
   - stop_steel_qr.bat 더블클릭

2. 콘솔 창에서 종료
   - 실행 중인 콘솔 창에서 Ctrl+C

3. 작업 관리자
   - Ctrl+Shift+Esc → steel-qr.exe 또는 python.exe 종료

========================================

## ❓ 문제 해결

1. 다른 기기에서 접속이 안됨
   → firewall_setup.bat을 관리자 권한으로 실행

2. 내 IP 주소를 모르겠음
   → check_ip.bat 실행

3. IP 주소가 자주 변경됨
   → setup_static_ip.bat으로 고정 IP 설정 (권장)

4. 키오스크 IP가 변경됨
   → update_instance_ip.bat 실행 후 관리자 UI에서 수정

5. 포트가 이미 사용 중
   → stop_steel_qr.bat으로 기존 프로세스 종료

4. templates 폴더가 없다는 오류
   → dist 폴더 전체를 복사했는지 확인

========================================

## 💡 팁

- 고정 IP 설정 권장 (공유기 설정에서)
- 각 키오스크의 IP를 라벨로 표시 (예: "1층-192.168.0.101")
- config.yaml에서 스캐너 경로, NAS 경로 등 설정

========================================
"""
    with open(src_readme, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"      ✓ README.txt 생성 완료")
    
    print("\n모든 파일 복사 완료!")

if __name__ == "__main__":
    build_windows_exe()

