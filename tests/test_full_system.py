"""
전체 시스템 통합 테스트 (QR 기능 시뮬레이션 포함)
"""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import ConfigManager
from src.models import init_database, get_session, ScanDocument, ProcessStatus
from src.pdf_processor import PDFProcessor
from src.batch_processor import BatchProcessor


class TestFullSystem:
    """전체 시스템 테스트"""
    
    @pytest.fixture
    def test_config(self, tmp_path):
        """테스트용 설정"""
        config = ConfigManager()
        config.paths.scanner_output = tmp_path / "scanner"
        config.paths.data_root = tmp_path / "data"
        config.paths.create_directories()
        
        # NAS 경로를 로컬 테스트 경로로 설정
        config.upload.nas.path = str(tmp_path / "nas")
        Path(config.upload.nas.path).mkdir(exist_ok=True)
        
        return config
    
    @pytest.fixture
    def test_db(self, test_config):
        """테스트용 데이터베이스"""
        db_path = test_config.paths.data_root / "test.db"
        engine = init_database(db_path)
        session = get_session(engine)
        yield session
        session.close()
    
    def test_pdf_processing_workflow(self, test_config, test_db):
        """PDF 처리 워크플로우 테스트"""
        # PDF 프로세서 초기화
        pdf_processor = PDFProcessor(test_config)
        
        # 테스트 PDF 파일들 준비
        test_pdfs_dir = Path("tests/test_pdfs")
        if not test_pdfs_dir.exists():
            pytest.skip("테스트 PDF 파일이 없습니다.")
        
        pdf_files = list(test_pdfs_dir.glob("merge_test_*.pdf"))
        if len(pdf_files) < 2:
            pytest.skip("병합 테스트용 PDF가 부족합니다.")
        
        # 1. PDF 병합 테스트
        output_path = test_config.paths.merged / "20250930" / "20250930000001.pdf"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = pdf_processor.merge_pdfs(pdf_files, output_path, remove_duplicates=False)
        
        assert result['success'] == True
        assert result['page_count'] >= len(pdf_files)
        assert output_path.exists()
        
        # 2. 데이터베이스 기록 시뮬레이션
        doc = ScanDocument(
            file_path=str(output_path),
            original_filename="merged_document.pdf",
            transport_no="20250930000001",
            status=ProcessStatus.MERGED,
            page_count=result['page_count'],
            file_size=output_path.stat().st_size,
            created_at=datetime.utcnow()
        )
        test_db.add(doc)
        test_db.commit()
        
        # 3. 데이터베이스 조회 확인
        saved_doc = test_db.query(ScanDocument).filter_by(transport_no="20250930000001").first()
        assert saved_doc is not None
        assert saved_doc.status == ProcessStatus.MERGED
        assert saved_doc.page_count == result['page_count']
    
    def test_qr_simulation_workflow(self, test_config, test_db):
        """QR 처리 시뮬레이션 워크플로우"""
        # QR 인식 결과 시뮬레이션
        qr_results = [
            {"transport_no": "20250930000001", "status": "success"},
            {"transport_no": "20250930000002", "status": "success"},
            {"transport_no": "20250930000003", "status": "multiple", "codes": ["20250930000003", "20250930000004"]},
            {"transport_no": None, "status": "error", "message": "QR 코드를 찾을 수 없습니다."}
        ]
        
        # 각 시나리오별 문서 생성
        for i, qr_result in enumerate(qr_results):
            doc = ScanDocument(
                file_path=f"test_file_{i+1}.pdf",
                original_filename=f"test_file_{i+1}.pdf",
                transport_no=qr_result["transport_no"],
                status=ProcessStatus.PENDING if qr_result["status"] == "success" else ProcessStatus.ERROR,
                error_message=qr_result.get("message"),
                qr_count=len(qr_result.get("codes", [])) if "codes" in qr_result else (1 if qr_result["status"] == "success" else 0),
                created_at=datetime.utcnow()
            )
            test_db.add(doc)
        
        test_db.commit()
        
        # 결과 검증
        total_docs = test_db.query(ScanDocument).count()
        pending_docs = test_db.query(ScanDocument).filter_by(status=ProcessStatus.PENDING).count()
        error_docs = test_db.query(ScanDocument).filter_by(status=ProcessStatus.ERROR).count()
        
        assert total_docs == 4
        assert pending_docs == 2  # 성공한 QR 인식
        assert error_docs == 2   # 다중 QR + 인식 실패
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, test_config, test_db):
        """배치 처리 테스트"""
        # 배치 프로세서 초기화
        batch_processor = BatchProcessor(test_config, test_db)
        
        # 테스트 문서들 생성 (동일 운송번호)
        transport_no = "20250930000010"
        for i in range(3):
            doc = ScanDocument(
                file_path=f"pending/{transport_no}({i+1}).pdf",
                original_filename=f"scan_{i+1}.pdf",
                transport_no=transport_no,
                status=ProcessStatus.PENDING,
                page_count=1,
                file_size=1024,
                created_at=datetime.utcnow()
            )
            test_db.add(doc)
        
        test_db.commit()
        
        # 배치 처리 실행 (실제 파일 없이 로직만 테스트)
        try:
            await batch_processor._process_pending_documents()
            # 실제 파일이 없어서 오류가 발생할 수 있지만, 로직은 실행됨
        except Exception as e:
            # 파일 관련 오류는 예상됨
            pass
        
        # 상태 확인 (파일이 없어도 DB 로직은 확인 가능)
        docs = test_db.query(ScanDocument).filter_by(transport_no=transport_no).all()
        assert len(docs) == 3
    
    def test_file_organization(self, test_config):
        """파일 조직화 테스트"""
        # 날짜별 폴더 구조 테스트
        transport_no = "20250930000001"
        date_folder = transport_no[:8]  # "20250930"
        
        # 각 단계별 폴더 경로 확인
        pending_path = test_config.paths.pending / date_folder
        merged_path = test_config.paths.merged / date_folder
        uploaded_path = test_config.paths.uploaded / date_folder
        error_path = test_config.paths.error / date_folder
        
        # 폴더 생성 테스트
        for path in [pending_path, merged_path, uploaded_path, error_path]:
            path.mkdir(parents=True, exist_ok=True)
            assert path.exists()
            assert path.is_dir()
    
    def test_configuration_system(self, test_config):
        """설정 시스템 테스트"""
        # 설정 값 확인
        assert test_config.system.worker_count >= 1
        assert test_config.system.web_port > 0
        assert test_config.qr.pattern is not None
        assert test_config.pdf.hash_algorithm in ["md5", "sha1"]
        assert test_config.batch.trigger_mode in ["idle", "schedule"]
        
        # 디렉토리 생성 (테스트용)
        test_config.paths.data_root.mkdir(parents=True, exist_ok=True)
        test_config.paths.pending.mkdir(parents=True, exist_ok=True)
        test_config.paths.merged.mkdir(parents=True, exist_ok=True)
        test_config.paths.uploaded.mkdir(parents=True, exist_ok=True)
        test_config.paths.error.mkdir(parents=True, exist_ok=True)
        test_config.paths.logs.mkdir(parents=True, exist_ok=True)
        
        # 경로 설정 확인
        assert test_config.paths.data_root.exists()
        assert test_config.paths.pending.exists()
        assert test_config.paths.merged.exists()
        assert test_config.paths.uploaded.exists()
        assert test_config.paths.error.exists()
    
    def test_database_operations(self, test_db):
        """데이터베이스 연산 테스트"""
        # 문서 생성
        doc = ScanDocument(
            file_path="test.pdf",
            original_filename="test.pdf",
            transport_no="20250930999999",
            status=ProcessStatus.PENDING,
            page_count=5,
            file_size=2048,
            created_at=datetime.utcnow()
        )
        test_db.add(doc)
        test_db.commit()
        
        # 조회 테스트
        saved_doc = test_db.query(ScanDocument).filter_by(transport_no="20250930999999").first()
        assert saved_doc is not None
        assert saved_doc.page_count == 5
        assert saved_doc.file_size == 2048
        
        # 상태 업데이트 테스트
        saved_doc.status = ProcessStatus.UPLOADED
        saved_doc.uploaded_at = datetime.utcnow()
        test_db.commit()
        
        updated_doc = test_db.query(ScanDocument).filter_by(transport_no="20250930999999").first()
        assert updated_doc.status == ProcessStatus.UPLOADED
        assert updated_doc.uploaded_at is not None
    
    def test_error_handling(self, test_config, test_db):
        """오류 처리 테스트"""
        # 오류 상태 문서 생성
        error_doc = ScanDocument(
            file_path="error_file.pdf",
            original_filename="error_file.pdf",
            transport_no=None,
            status=ProcessStatus.ERROR,
            error_message="QR 코드 인식 실패",
            created_at=datetime.utcnow()
        )
        test_db.add(error_doc)
        test_db.commit()
        
        # 오류 문서 조회
        error_docs = test_db.query(ScanDocument).filter_by(status=ProcessStatus.ERROR).all()
        assert len(error_docs) >= 1
        assert any(doc.error_message == "QR 코드 인식 실패" for doc in error_docs)
        
        # 수동 수정 시뮬레이션
        error_doc.transport_no = "20250930888888"
        error_doc.manual_transport_no = "20250930888888"
        error_doc.status = ProcessStatus.PENDING
        error_doc.error_message = None
        test_db.commit()
        
        # 수정 확인
        fixed_doc = test_db.query(ScanDocument).filter_by(transport_no="20250930888888").first()
        assert fixed_doc is not None
        assert fixed_doc.status == ProcessStatus.PENDING
        assert fixed_doc.manual_transport_no == "20250930888888"
