"""
ZBar 기반 QR 엔진 (기존 방식, 빠름)
"""
import time
from typing import List
from PIL import Image
import cv2
import numpy as np
from loguru import logger

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    logger.warning("pyzbar를 사용할 수 없습니다. ZBar 엔진이 비활성화됩니다.")

from .base import QREngine, QRResult


class ZBarEngine(QREngine):
    """ZBar 기반 QR 엔진"""
    
    def __init__(self, config: dict = None):
        super().__init__("ZBAR", config)
    
    def is_available(self) -> bool:
        """ZBar 엔진 사용 가능 여부"""
        return self.enabled and PYZBAR_AVAILABLE
    
    def extract_from_image(self, image: Image.Image) -> QRResult:
        """이미지에서 QR 코드 추출 (ZBar)"""
        start_time = time.time()
        
        if not self.is_available():
            return QRResult(
                success=False,
                codes=[],
                engine=self.name,
                processing_time=0.0,
                error_message="ZBar 엔진을 사용할 수 없습니다"
            )
        
        try:
            # PIL Image를 OpenCV 형식으로 변환
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # 그레이스케일 변환
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # ZBar로 QR 코드 디코딩
            decoded_objects = pyzbar.decode(gray)
            
            codes = []
            for obj in decoded_objects:
                if obj.type == 'QRCODE':
                    try:
                        code_text = obj.data.decode('utf-8')
                        codes.append(code_text)
                        logger.debug(f"ZBar QR 코드 발견: {code_text}")
                    except UnicodeDecodeError:
                        logger.warning("ZBar QR 코드 디코딩 실패 (UTF-8)")
            
            processing_time = time.time() - start_time
            
            return QRResult(
                success=len(codes) > 0,
                codes=codes,
                engine=self.name,
                processing_time=processing_time,
                debug_info={
                    'total_objects': len(decoded_objects),
                    'qr_objects': len([obj for obj in decoded_objects if obj.type == 'QRCODE'])
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"ZBar QR 추출 오류: {e}")
            
            return QRResult(
                success=False,
                codes=[],
                engine=self.name,
                processing_time=processing_time,
                error_message=str(e)
            )
