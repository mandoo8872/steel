"""
QR 코드 인식 모듈 (다중 엔진 지원)
"""
import re
from typing import List, Tuple, Optional
from pathlib import Path
from loguru import logger

# 하위 호환성을 위한 기존 인터페이스 유지
from .multi_qr_reader import MultiQRReader


class QRReader:
    """QR 코드 리더 (다중 엔진 래퍼)"""
    
    def __init__(self, pattern: str = r"^\d{14}$", config=None):
        """
        Args:
            pattern: QR 코드 패턴 (하위 호환성용)
            config: QRConfig 객체 (새로운 다중 엔진 설정)
        """
        if config is not None:
            # 새로운 다중 엔진 모드
            self.multi_reader = MultiQRReader(config)
            self.pattern = re.compile(config.pattern)
        else:
            # 기존 단일 엔진 모드 (하위 호환성)
            from .config import QRConfig
            default_config = QRConfig()
            default_config.pattern = pattern
            default_config.engine_order = ["ZBAR"]  # 기존 방식만 사용
            
            self.multi_reader = MultiQRReader(default_config)
            self.pattern = re.compile(pattern)
        
        logger.info(f"QR 리더 초기화 - 패턴: {self.pattern.pattern}")
    
    def read_from_pdf(self, pdf_path: Path) -> Tuple[List[str], List[str]]:
        """
        PDF에서 QR 코드 읽기 (다중 엔진)
        
        Returns:
            (valid_codes, all_codes) - 패턴 매칭된 코드와 전체 코드
        """
        valid_codes, all_codes, processing_info = self.multi_reader.read_from_pdf(pdf_path)
        
        # 처리 정보 로깅
        if processing_info.get('engine_success_count'):
            logger.info(f"엔진별 성공 횟수: {processing_info['engine_success_count']}")
        
        return valid_codes, all_codes
    
    def get_engine_status(self) -> dict:
        """엔진 상태 정보 반환"""
        return self.multi_reader.get_engine_status()
    
    def validate_qr_code(self, code: str) -> bool:
        """QR 코드 패턴 검증"""
        return self.multi_reader.validate_qr_code(code)