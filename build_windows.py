"""
Windows 실행파일 빌드 스크립트
PyInstaller를 사용하여 단일 실행파일 생성
"""
import PyInstaller.__main__
import shutil
from pathlib import Path

def build_windows_exe():
    """Windows .exe 파일 빌드"""
    
    # 기존 빌드 폴더 정리
    dist_dir = Path("dist")
    build_dir = Path("build")
    
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    
    print("=" * 70)
    print("Steel QR - Windows 실행파일 빌드")
    print("=" * 70)
    
    # PyInstaller 옵션
    pyinstaller_args = [
        'main.py',                      # 진입점
        '--name=steel-qr',              # 실행파일 이름
        '--onefile',                    # 단일 파일로 패키징
        '--windowed',                   # 콘솔 창 숨김 (백그라운드 실행)
        '--icon=NONE',                  # 아이콘 (나중에 추가 가능)
        
        # 데이터 파일 포함
        '--add-data=templates;templates',           # 템플릿
        '--add-data=static;static',                 # 정적 파일
        '--add-data=config.example.yaml;.',         # 설정 예제
        '--add-data=instances.example.json;.',      # 인스턴스 레지스트리 예제
        
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
        
        # 디버그 정보 제외 (크기 축소)
        '--strip',
        
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
    print("✅ 빌드 완료!")
    print("=" * 70)
    print(f"\n실행파일 위치: {dist_dir / 'steel-qr.exe'}")
    print("\n사용 방법:")
    print("  키오스크 모드: steel-qr.exe --mode kiosk --port 8000")
    print("  관리자 모드:   steel-qr.exe --mode admin --port 8100")
    print("\n필요한 파일:")
    print("  - config.yaml (설정 파일)")
    print("  - instances.json (인스턴스 레지스트리, 관리자 모드)")
    print("  - data/ 폴더 (작업 디렉토리)")
    print("=" * 70)

if __name__ == "__main__":
    build_windows_exe()

