"""
QR 엔진 기본 인터페이스
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Any
from pathlib import Path
import numpy as np
from PIL import Image


@dataclass
class QRResult:
    """QR 인식 결과"""
    success: bool
    codes: List[str]
    engine: str
    processing_time: float
    error_message: Optional[str] = None
    debug_info: Optional[dict] = None


class QREngine(ABC):
    """QR 엔진 기본 클래스"""
    
    def __init__(self, name: str, config = None):
        self.name = name
        self.config = config or {}
        
        # config가 dataclass인 경우와 dict인 경우 모두 처리
        if hasattr(config, 'enabled'):  # dataclass
            self.enabled = config.enabled
            self.timeout = config.timeout
            self.options = config.options if hasattr(config, 'options') else {}
        else:  # dict
            self.enabled = config.get('enabled', True) if config else True
            self.timeout = config.get('timeout', 30) if config else 30
            self.options = config.get('options', {}) if config else {}
    
    @abstractmethod
    def extract_from_image(self, image: Image.Image) -> QRResult:
        """
        이미지에서 QR 코드 추출
        
        Args:
            image: PIL Image 객체
            
        Returns:
            QRResult: 추출 결과
        """
        pass
    
    def extract_from_array(self, image_array: np.ndarray) -> QRResult:
        """
        numpy 배열에서 QR 코드 추출
        
        Args:
            image_array: numpy 이미지 배열
            
        Returns:
            QRResult: 추출 결과
        """
        try:
            # numpy 배열을 PIL Image로 변환
            if len(image_array.shape) == 3:
                # RGB/BGR 이미지
                if image_array.shape[2] == 3:
                    image = Image.fromarray(image_array, 'RGB')
                elif image_array.shape[2] == 4:
                    image = Image.fromarray(image_array, 'RGBA')
                else:
                    raise ValueError(f"지원하지 않는 채널 수: {image_array.shape[2]}")
            else:
                # 그레이스케일 이미지
                image = Image.fromarray(image_array, 'L')
            
            return self.extract_from_image(image)
            
        except Exception as e:
            return QRResult(
                success=False,
                codes=[],
                engine=self.name,
                processing_time=0.0,
                error_message=f"배열 변환 오류: {str(e)}"
            )
    
    def is_available(self) -> bool:
        """엔진 사용 가능 여부 확인"""
        return self.enabled
    
    def get_info(self) -> dict:
        """엔진 정보 반환"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'timeout': self.timeout,
            'options': self.options,
            'available': self.is_available()
        }
