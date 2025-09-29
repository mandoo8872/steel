"""
PDF 프로세서 테스트
"""
import pytest
from pathlib import Path
import tempfile
import sys
from PyPDF2 import PdfWriter

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_processor import PDFProcessor
from src.config import ConfigManager


class TestPDFProcessor:
    """PDF 프로세서 테스트"""
    
    @pytest.fixture
    def pdf_processor(self):
        """PDF 프로세서 픽스처"""
        config = ConfigManager()
        return PDFProcessor(config)
    
    @pytest.fixture
    def sample_pdf(self):
        """샘플 PDF 생성"""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            writer = PdfWriter()
            writer.add_blank_page(width=200, height=200)
            writer.write(tmp)
            return Path(tmp.name)
    
    def test_file_hash(self, pdf_processor, sample_pdf):
        """파일 해시 계산 테스트"""
        hash1 = pdf_processor.calculate_file_hash(sample_pdf)
        hash2 = pdf_processor.calculate_file_hash(sample_pdf)
        
        # 같은 파일은 같은 해시
        assert hash1 == hash2
        assert len(hash1) > 0
        
        # 정리
        sample_pdf.unlink()
    
    def test_pdf_info(self, pdf_processor, sample_pdf):
        """PDF 정보 추출 테스트"""
        info = pdf_processor.get_pdf_info(sample_pdf)
        
        assert info['is_valid'] == True
        assert info['page_count'] == 1
        assert info['file_size'] > 0
        assert info['error'] == None
        
        # 정리
        sample_pdf.unlink()
    
    def test_merge_pdfs(self, pdf_processor):
        """PDF 병합 테스트"""
        # 여러 개의 샘플 PDF 생성
        pdf_files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                writer = PdfWriter()
                writer.add_blank_page(width=200, height=200)
                writer.write(tmp)
                pdf_files.append(Path(tmp.name))
        
        # 병합
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as output:
            output_path = Path(output.name)
        
        result = pdf_processor.merge_pdfs(pdf_files, output_path)
        
        assert result['success'] == True
        assert result['page_count'] == 3
        assert output_path.exists()
        
        # 정리
        for pdf_file in pdf_files:
            pdf_file.unlink()
        output_path.unlink()
