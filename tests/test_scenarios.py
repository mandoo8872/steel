"""
시나리오 기반 통합 테스트
"""
import pytest
import asyncio
from pathlib import Path
import shutil
import time
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processor import QRScanProcessor
from src.models import ScanDocument, ProcessStatus


class TestScenarios:
    """시나리오 테스트"""
    
    @pytest.fixture
    async def processor(self, tmp_path):
        """테스트용 프로세서 생성"""
        # 테스트 설정 생성
        config_content = f"""
system:
  log_level: DEBUG
  worker_count: 2
  web_port: 8001
  admin_password: "test"

paths:
  scanner_output: "{tmp_path / 'scanner'}"
  data_root: "{tmp_path / 'data'}"

watcher:
  mode: "polling"
  polling_interval: 1
  stability_wait: 1
  stability_checks: 2

qr:
  pattern: "^\\\\d{{14}}$"
  multiple_qr_action: "manual"

pdf:
  normalize: false
  pdf_a_convert: false
  remove_duplicates: true
  hash_algorithm: "sha1"

batch:
  trigger_mode: "idle"
  idle_minutes: 1

upload:
  type: "nas"
  nas:
    path: "{tmp_path / 'nas'}"

retry:
  max_attempts: 3
  initial_delay: 1
  backoff_multiplier: 2
  max_delay: 10

retention:
  uploaded_days: 7
  error_days: 7
  log_days: 7
"""
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text(config_content)
        
        # 프로세서 생성
        processor = QRScanProcessor(str(config_path))
        await processor.start()
        
        yield processor
        
        # 정리
        await processor.stop()
    
    @pytest.mark.asyncio
    async def test_normal_flow(self, processor, tmp_path):
        """정상 처리 플로우 테스트"""
        # 테스트 PDF 복사
        test_pdf = Path(__file__).parent / "test_pdfs" / "normal_single_page.pdf"
        if test_pdf.exists():
            scanner_dir = tmp_path / "scanner"
            scanner_dir.mkdir(exist_ok=True)
            shutil.copy(test_pdf, scanner_dir / "test1.pdf")
            
            # 파일 처리 대기
            await asyncio.sleep(3)
            
            # DB 확인
            doc = processor.db_session.query(ScanDocument).filter_by(
                original_filename="test1.pdf"
            ).first()
            
            assert doc is not None
            assert doc.transport_no == "20250929000001"
            assert doc.status in [ProcessStatus.PENDING, ProcessStatus.MERGED, ProcessStatus.UPLOADED]
    
    @pytest.mark.asyncio
    async def test_multiple_qr_flow(self, processor, tmp_path):
        """다중 QR 처리 플로우 테스트"""
        test_pdf = Path(__file__).parent / "test_pdfs" / "multiple_qr.pdf"
        if test_pdf.exists():
            scanner_dir = tmp_path / "scanner"
            scanner_dir.mkdir(exist_ok=True)
            shutil.copy(test_pdf, scanner_dir / "test2.pdf")
            
            # 파일 처리 대기
            await asyncio.sleep(3)
            
            # DB 확인
            doc = processor.db_session.query(ScanDocument).filter_by(
                original_filename="test2.pdf"
            ).first()
            
            assert doc is not None
            assert doc.status == ProcessStatus.ERROR
            assert doc.qr_count == 2
    
    @pytest.mark.asyncio
    async def test_batch_merge(self, processor, tmp_path):
        """배치 병합 테스트"""
        # 여러 파일 복사
        for i in range(3):
            test_pdf = Path(__file__).parent / "test_pdfs" / f"merge_test_{i+1}.pdf"
            if test_pdf.exists():
                scanner_dir = tmp_path / "scanner"
                scanner_dir.mkdir(exist_ok=True)
                shutil.copy(test_pdf, scanner_dir / f"merge_{i+1}.pdf")
                await asyncio.sleep(1)
        
        # 파일 처리 대기
        await asyncio.sleep(3)
        
        # 강제 배치 처리
        await processor.force_batch_process()
        
        # 병합 확인
        merged_dir = processor.config.paths.merged / "20250929"
        if merged_dir.exists():
            merged_files = list(merged_dir.glob("20250929000005.pdf"))
            assert len(merged_files) == 1
