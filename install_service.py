"""
Windows 서비스 설치 스크립트
steel-qr를 Windows 서비스로 등록하여 자동 시작
"""
import sys
import os
import subprocess
from pathlib import Path

def install_service(mode="kiosk", port=8000):
    """
    Windows 서비스로 등록
    
    Args:
        mode: kiosk 또는 admin
        port: 포트 번호
    """
    exe_path = Path("steel-qr.exe").absolute()
    
    if not exe_path.exists():
        print(f"❌ 실행파일을 찾을 수 없습니다: {exe_path}")
        print("먼저 build_windows.py를 실행하여 실행파일을 생성하세요.")
        return False
    
    service_name = f"SteelQR-{mode.capitalize()}"
    display_name = f"Steel QR Scan System ({mode})"
    
    # NSSM (Non-Sucking Service Manager) 사용 권장
    print("=" * 70)
    print("Windows 서비스 설치")
    print("=" * 70)
    print()
    print(f"서비스 이름: {service_name}")
    print(f"표시 이름: {display_name}")
    print(f"실행파일: {exe_path}")
    print(f"모드: {mode}")
    print(f"포트: {port}")
    print()
    print("설치 방법:")
    print()
    print("【방법 1】NSSM 사용 (권장)")
    print("-" * 70)
    print("1. NSSM 다운로드:")
    print("   https://nssm.cc/download")
    print()
    print("2. nssm.exe를 시스템 PATH에 추가")
    print()
    print("3. 관리자 권한으로 CMD 실행:")
    print(f'   nssm install {service_name} "{exe_path}"')
    print(f'   nssm set {service_name} AppParameters "--mode {mode} --port {port}"')
    print(f'   nssm set {service_name} AppDirectory "{exe_path.parent}"')
    print(f'   nssm set {service_name} DisplayName "{display_name}"')
    print(f'   nssm set {service_name} Description "QR 스캔 문서 관리 시스템"')
    print(f'   nssm set {service_name} Start SERVICE_AUTO_START')
    print()
    print("4. 서비스 시작:")
    print(f'   nssm start {service_name}')
    print()
    print("5. 서비스 중지:")
    print(f'   nssm stop {service_name}')
    print()
    print("6. 서비스 제거:")
    print(f'   nssm remove {service_name} confirm')
    print()
    print("【방법 2】sc 명령어 사용")
    print("-" * 70)
    print("관리자 권한으로 CMD 실행:")
    print(f'sc create {service_name} binPath= "{exe_path} --mode {mode} --port {port}" start= auto')
    print(f'sc description {service_name} "QR 스캔 문서 관리 시스템 ({mode} 모드)"')
    print(f'sc start {service_name}')
    print()
    print("서비스 제거:")
    print(f'sc stop {service_name}')
    print(f'sc delete {service_name}')
    print()
    print("【방법 3】작업 스케줄러 사용")
    print("-" * 70)
    print("1. 작업 스케줄러 열기 (taskschd.msc)")
    print("2. '기본 작업 만들기'")
    print(f"3. 이름: {service_name}")
    print("4. 트리거: 시스템 시작 시")
    print(f"5. 동작: 프로그램 시작 - {exe_path}")
    print(f"6. 인수: --mode {mode} --port {port}")
    print()
    print("=" * 70)
    print()
    print("⚠️  주의사항:")
    print("  - 관리자 권한이 필요합니다")
    print("  - config.yaml 파일이 실행파일과 같은 폴더에 있어야 합니다")
    print("  - 방화벽에서 포트를 열어야 할 수 있습니다")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    # 명령줄 인자 처리
    mode = sys.argv[1] if len(sys.argv) > 1 else "kiosk"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    
    if mode not in ["kiosk", "admin"]:
        print("❌ 모드는 'kiosk' 또는 'admin'이어야 합니다")
        sys.exit(1)
    
    install_service(mode, port)

