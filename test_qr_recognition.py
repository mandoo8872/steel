"""
QR 인식 테스트 스크립트
"""
from pathlib import Path
from loguru import logger
from src.config import ConfigManager
from src.qr_reader import QRReader

# 로깅 설정
logger.add("test_qr_recognition.log", rotation="10 MB")

def test_qr_recognition():
    """QR 인식 테스트"""
    print("=" * 60)
    print("QR 인식 테스트")
    print("=" * 60)
    
    # 설정 로드
    config = ConfigManager("config.yaml")
    print(f"\n✓ 설정 로드 완료")
    print(f"  QR 패턴: {config.qr.pattern}")
    print(f"  엔진 순서: {config.qr.engine_order}")
    
    # QR 리더 초기화
    qr_reader = QRReader(config=config.qr)
    print(f"\n✓ QR 리더 초기화 완료")
    
    # 엔진 상태 확인
    engine_status = qr_reader.get_engine_status()
    print(f"\n📊 엔진 상태:")
    for name, status in engine_status.items():
        available = "✓" if status['available'] else "✗"
        print(f"  {available} {name}: {status.get('error', '사용 가능')}")
    
    # 테스트 PDF 찾기
    test_pdfs = list(Path("data/scanner_output").glob("*.pdf"))
    
    if not test_pdfs:
        print(f"\n⚠ 테스트 PDF가 없습니다.")
        print(f"  경로: data/scanner_output/")
        print(f"\n테스트 PDF를 생성하려면:")
        print(f"  python generate_real_qr_pdfs.py")
        return
    
    print(f"\n📄 테스트 PDF: {len(test_pdfs)}개 발견")
    
    # 각 PDF 테스트
    for pdf_path in test_pdfs[:3]:  # 최대 3개만 테스트
        print(f"\n{'='*60}")
        print(f"테스트: {pdf_path.name}")
        print(f"{'='*60}")
        
        try:
            valid_codes, all_codes = qr_reader.read_from_pdf(pdf_path)
            
            print(f"✓ QR 인식 완료")
            print(f"  전체 QR: {len(all_codes)}개")
            print(f"  유효 QR: {len(valid_codes)}개")
            
            if all_codes:
                print(f"\n전체 QR 코드:")
                for code in all_codes[:10]:  # 최대 10개만 표시
                    print(f"  - {code}")
            
            if valid_codes:
                print(f"\n✓ 유효한 QR 코드:")
                for code in valid_codes:
                    print(f"  ✓ {code}")
            else:
                print(f"\n⚠ 유효한 QR 코드가 없습니다")
                print(f"  (패턴: {config.qr.pattern})")
                
        except Exception as e:
            print(f"✗ 에러 발생: {e}")
            logger.exception(f"QR 인식 실패: {pdf_path}")

if __name__ == "__main__":
    test_qr_recognition()

