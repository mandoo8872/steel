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
    
    print("\n[5/7] 실행 배치 파일 복사 중...")
    batch_files = ["run_kiosk.bat", "run_admin.bat"]
    for batch_file in batch_files:
        src_batch = Path(batch_file)
        if not src_batch.exists():
            # dist 폴더에 있는 파일을 사용
            src_batch = dist_dir / batch_file
        
        if src_batch.exists() and src_batch.parent != dist_dir:
            dst_batch = dist_dir / batch_file
            shutil.copy2(src_batch, dst_batch)
            print(f"      ✓ {batch_file}")
        elif (dist_dir / batch_file).exists():
            print(f"      ✓ {batch_file} (이미 존재)")
        else:
            print(f"      ⚠ {batch_file}을 찾을 수 없습니다")
    
    print("\n[6/7] 방화벽 배치 파일 복사 중...")
    firewall_files = ["firewall_setup.bat", "firewall_remove.bat"]
    for fw_file in firewall_files:
        src_fw = Path(fw_file)
        if src_fw.exists():
            dst_fw = dist_dir / fw_file
            shutil.copy2(src_fw, dst_fw)
            print(f"      ✓ {fw_file}")
        else:
            print(f"      ⚠ {fw_file}을 찾을 수 없습니다")
    
    print("\n[7/7] 종료 배치 파일 복사 중...")
    src_stop = Path("stop_steel_qr.bat")
    if src_stop.exists():
        dst_stop = dist_dir / "stop_steel_qr.bat"
        shutil.copy2(src_stop, dst_stop)
        print(f"      ✓ stop_steel_qr.bat")
    else:
        print(f"      ⚠ stop_steel_qr.bat을 찾을 수 없습니다")
    
    print("\n[8/9] IP 관리 배치 파일 복사 중...")
    ip_scripts = ["check_ip.bat", "setup_static_ip.bat", "update_instance_ip.bat"]
    for ip_script in ip_scripts:
        src_ip = Path(ip_script)
        if src_ip.exists():
            dst_ip = dist_dir / ip_script
            shutil.copy2(src_ip, dst_ip)
            print(f"      ✓ {ip_script}")
        else:
            print(f"      ⚠ {ip_script}을 찾을 수 없습니다")
    
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

