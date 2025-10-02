#!/usr/bin/env python3
"""
수동 재스캔 스크립트
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.processor import QRScanProcessor

async def manual_rescan():
    """수동 재스캔 실행"""
    processor = QRScanProcessor()
    
    try:
        print("=== 수동 재스캔 시작 ===")
        
        # 현재 상태 확인
        scanner_files = list(processor.config.paths.scanner_output.glob("*.pdf"))
        print(f"scanner_output 폴더: {len(scanner_files)}개 파일")
        
        if not scanner_files:
            print("처리할 파일이 없습니다.")
            return
        
        # 각 파일 처리
        processed = 0
        for file_path in scanner_files:
            try:
                print(f"처리 중: {file_path.name}")
                result = processor._process_qr_document(file_path)
                
                if result['valid_qr_codes']:
                    # 성공: pending으로 이동
                    transport_no = result['valid_qr_codes'][0]
                    await processor._move_to_pending(file_path, transport_no)
                    print(f"  → pending: {transport_no}")
                else:
                    # 실패: error로 이동
                    await processor._move_to_error(file_path, "QR 코드 인식 실패")
                    print(f"  → error: QR 인식 실패")
                
                processed += 1
                
            except Exception as e:
                print(f"  → 오류: {e}")
                try:
                    await processor._move_to_error(file_path, str(e))
                except:
                    pass
        
        print(f"\n=== 처리 완료: {processed}개 파일 ===")
        
        # 최종 상태 출력
        scanner_count = len(list(processor.config.paths.scanner_output.glob("*.pdf")))
        pending_count = len(list(processor.config.paths.pending.glob("*.pdf")))
        error_count = len(list(processor.config.paths.error.glob("*.pdf")))
        
        print(f"scanner_output: {scanner_count}개")
        print(f"pending: {pending_count}개")
        print(f"error: {error_count}개")
        
    except Exception as e:
        print(f"재스캔 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        processor.db_session.close()

if __name__ == "__main__":
    asyncio.run(manual_rescan())
