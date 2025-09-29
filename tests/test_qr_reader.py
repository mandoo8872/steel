"""
QR 리더 테스트
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.qr_reader import QRReader, QRProcessor


class TestQRReader:
    """QR 리더 테스트"""
    
    def test_transport_no_validation(self):
        """운송번호 유효성 검사 테스트"""
        reader = QRReader()
        
        # 유효한 운송번호
        assert reader.validate_transport_no("20250929000001") == True
        assert reader.validate_transport_no("12345678901234") == True
        
        # 유효하지 않은 운송번호
        assert reader.validate_transport_no("2025092900000") == False  # 13자리
        assert reader.validate_transport_no("202509290000001") == False  # 15자리
        assert reader.validate_transport_no("2025092900000A") == False  # 문자 포함
        assert reader.validate_transport_no("") == False  # 빈 문자열
    
    def test_extract_date(self):
        """운송번호에서 날짜 추출 테스트"""
        reader = QRReader()
        
        assert reader.extract_date_from_transport_no("20250929000001") == "20250929"
        assert reader.extract_date_from_transport_no("20240101123456") == "20240101"
        assert reader.extract_date_from_transport_no("invalid") == None
