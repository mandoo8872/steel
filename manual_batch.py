#!/usr/bin/env python3
"""
수동 배치 처리 스크립트
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.batch_processor import BatchProcessor
from src.config import ConfigManager
from src.models import init_database, get_session

async def manual_batch():
    """수동 배치 처리 실행"""
    config = ConfigManager()
    
    # 데이터베이스 초기화
    db_path = config.paths.data_root / "qr_system.db"
    engine = init_database(db_path)
    db_session = get_session(engine)
    
    batch_processor = BatchProcessor(config, db_session)
    
    try:
        print("=== 수동 배치 처리 시작 ===")
        
        # 현재 상태 확인
        pending_files = list(config.paths.pending.glob("*.pdf"))
        merged_files = list(config.paths.merged.glob("*.pdf"))
        
        print(f"pending 폴더: {len(pending_files)}개 파일")
        print(f"merged 폴더: {len(merged_files)}개 파일")
        
        # 배치 처리 실행
        await batch_processor.process_batch()
        
        # 처리 후 상태 확인
        pending_files_after = list(config.paths.pending.glob("*.pdf"))
        merged_files_after = list(config.paths.merged.glob("*.pdf"))
        
        print(f"\n=== 배치 처리 완료 ===")
        print(f"pending 폴더: {len(pending_files_after)}개 파일")
        print(f"merged 폴더: {len(merged_files_after)}개 파일")
        
    except Exception as e:
        print(f"배치 처리 오류: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db_session.close()

if __name__ == "__main__":
    asyncio.run(manual_batch())
