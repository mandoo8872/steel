#!/usr/bin/env python3
"""
테스트 환경 생성 스크립트
"""
import os
import sys
import shutil
from pathlib import Path

def create_test_environment():
    """테스트 환경 생성"""
    base_dir = Path(__file__).parent.parent
    
    print("테스트 환경을 생성합니다...")
    
    # 1. 설정 파일 생성
    if not (base_dir / "config.yaml").exists():
        shutil.copy(base_dir / "config.example.yaml", base_dir / "config.yaml")
        print("✓ config.yaml 생성됨")
    else:
        print("- config.yaml 이미 존재")
    
    # 2. 테스트 디렉토리 생성
    test_dirs = [
        "data/scanner_output",
        "data/pending",
        "data/merged",
        "data/uploaded",
        "data/error",
        "data/logs",
        "data/nas",  # 테스트용 NAS 디렉토리
    ]
    
    for dir_path in test_dirs:
        full_path = base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ {dir_path} 디렉토리 생성됨")
    
    # 3. 테스트 PDF 생성
    test_pdf_script = base_dir / "tests" / "generate_test_pdfs.py"
    if test_pdf_script.exists():
        print("\n테스트 PDF 생성 중...")
        os.system(f"{sys.executable} {test_pdf_script}")
    
    print("\n테스트 환경 생성 완료!")
    print("\n다음 명령으로 시스템을 시작할 수 있습니다:")
    print(f"  python {base_dir}/main.py")
    print("\n웹 UI 접속: http://localhost:8000")
    print("기본 비밀번호: 1212")

if __name__ == "__main__":
    create_test_environment()
