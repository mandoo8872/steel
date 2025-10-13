#!/usr/bin/env python3
"""
성능 최적화 설정 스크립트
"""
import yaml
from pathlib import Path

def optimize_config():
    """설정 최적화"""
    config_path = Path("config.yaml")
    
    # 기존 설정 읽기
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        print("config.yaml이 없습니다. config.example.yaml을 복사하세요.")
        return
    
    # 성능 최적화 설정
    print("=== 성능 최적화 설정 적용 ===")
    
    # 1. 워커 수 증가
    if 'system' not in config:
        config['system'] = {}
    config['system']['worker_count'] = 4
    print("✓ 워커 수: 2 → 4")
    
    # 2. QR 엔진 최적화
    if 'qr' not in config:
        config['qr'] = {}
    
    # 엔진 순서 최적화 (빠른 것부터)
    config['qr']['engine_order'] = ["ZBAR", "PYZBAR_PREPROC"]
    print("✓ 엔진 순서: ZBAR → PYZBAR_PREPROC (ZXing 제외)")
    
    # ZBar 타임아웃 단축
    if 'zbar' not in config['qr']:
        config['qr']['zbar'] = {}
    config['qr']['zbar']['timeout'] = 10
    print("✓ ZBAR 타임아웃: 30초 → 10초")
    
    # ZXing 비활성화 (Java 없음)
    if 'zxing' not in config['qr']:
        config['qr']['zxing'] = {}
    config['qr']['zxing']['enabled'] = False
    print("✓ ZXing: 비활성화 (Java 환경 없음)")
    
    # Pyzbar 타임아웃 단축
    if 'pyzbar_preproc' not in config['qr']:
        config['qr']['pyzbar_preproc'] = {}
    config['qr']['pyzbar_preproc']['timeout'] = 30
    config['qr']['pyzbar_preproc']['options'] = {
        'adaptive_threshold': True,
        'deskew': False,  # 속도를 위해 일부 전처리 비활성화
        'sharpen': True,
        'blur_removal': False
    }
    print("✓ PYZBAR_PREPROC 타임아웃: 90초 → 30초")
    print("✓ 전처리 옵션 최적화 (속도 우선)")
    
    # 3. 배치 처리 최적화
    if 'batch' not in config:
        config['batch'] = {}
    config['batch']['idle_minutes'] = 1  # 더 빠른 배치 처리
    print("✓ 배치 유휴 시간: 5분 → 1분")
    
    # 설정 저장
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print("\n=== 최적화 완료 ===")
    print("서버를 재시작하면 적용됩니다.")
    print("\n예상 효과:")
    print("- 병렬 처리로 4배 빠른 속도")
    print("- 불필요한 엔진 제거로 처리 시간 단축")
    print("- 타임아웃 단축으로 실패 케이스 빠른 처리")

if __name__ == "__main__":
    optimize_config()
