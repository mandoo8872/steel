"""
OpenCV 전처리 + Pyzbar QR 엔진 (대비 낮은/번진 QR에 보강)
"""
import time
import math
from typing import List, Tuple
from PIL import Image
import cv2
import numpy as np
from loguru import logger

try:
    from pyzbar import pyzbar
    PYZBAR_AVAILABLE = True
except ImportError:
    PYZBAR_AVAILABLE = False
    logger.warning("pyzbar를 사용할 수 없습니다. Pyzbar Preproc 엔진이 비활성화됩니다.")

from .base import QREngine, QRResult


class PyzbarPreprocEngine(QREngine):
    """OpenCV 전처리 + Pyzbar QR 엔진"""
    
    def __init__(self, config: dict = None):
        super().__init__("PYZBAR_PREPROC", config)
    
    def is_available(self) -> bool:
        """Pyzbar Preproc 엔진 사용 가능 여부"""
        return self.enabled and PYZBAR_AVAILABLE
    
    def _adaptive_threshold(self, gray: np.ndarray) -> np.ndarray:
        """적응형 임계값 처리"""
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
    
    def _detect_skew_angle(self, gray: np.ndarray) -> float:
        """기울기 각도 검출"""
        try:
            # Canny 엣지 검출
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Hough 변환으로 직선 검출
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is None:
                return 0.0
            
            # 각도 계산
            angles = []
            for rho, theta in lines[:10]:  # 상위 10개 직선만 사용
                angle = theta * 180 / np.pi
                # 수직/수평에 가까운 각도만 고려
                if angle < 45 or angle > 135:
                    if angle > 90:
                        angle = angle - 180
                    angles.append(angle)
            
            if not angles:
                return 0.0
            
            # 중간값 사용 (노이즈 제거)
            return np.median(angles)
            
        except Exception as e:
            logger.debug(f"기울기 검출 실패: {e}")
            return 0.0
    
    def _deskew_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """이미지 기울기 보정"""
        if abs(angle) < 0.5:  # 0.5도 미만은 보정하지 않음
            return image
        
        try:
            h, w = image.shape[:2]
            center = (w // 2, h // 2)
            
            # 회전 행렬 생성
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # 회전 적용
            rotated = cv2.warpAffine(image, rotation_matrix, (w, h), 
                                   flags=cv2.INTER_CUBIC, 
                                   borderMode=cv2.BORDER_REPLICATE)
            
            logger.debug(f"이미지 기울기 보정: {angle:.2f}도")
            return rotated
            
        except Exception as e:
            logger.debug(f"기울기 보정 실패: {e}")
            return image
    
    def _sharpen_image(self, image: np.ndarray) -> np.ndarray:
        """이미지 선명화"""
        try:
            # 언샤프 마스킹 커널
            kernel = np.array([[-1,-1,-1],
                              [-1, 9,-1],
                              [-1,-1,-1]])
            
            sharpened = cv2.filter2D(image, -1, kernel)
            return sharpened
            
        except Exception as e:
            logger.debug(f"선명화 실패: {e}")
            return image
    
    def _remove_blur(self, image: np.ndarray) -> np.ndarray:
        """블러 제거 (디블러링)"""
        try:
            # 가우시안 블러 적용 후 원본과 차이 계산
            blurred = cv2.GaussianBlur(image, (0, 0), 1.0)
            unsharp_mask = cv2.addWeighted(image, 1.5, blurred, -0.5, 0)
            
            return unsharp_mask
            
        except Exception as e:
            logger.debug(f"블러 제거 실패: {e}")
            return image
    
    def _preprocess_image(self, image: Image.Image) -> List[np.ndarray]:
        """이미지 전처리 (여러 버전 생성)"""
        # PIL Image를 OpenCV 형식으로 변환
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        processed_images = []
        
        # 1. 원본 그레이스케일
        processed_images.append(("original", gray))
        
        # 2. 적응형 임계값
        if self.options.get('adaptive_threshold', True):
            adaptive = self._adaptive_threshold(gray)
            processed_images.append(("adaptive_threshold", adaptive))
        
        # 3. 기울기 보정
        if self.options.get('deskew', True):
            angle = self._detect_skew_angle(gray)
            if abs(angle) > 0.5:
                deskewed = self._deskew_image(gray, angle)
                processed_images.append(("deskewed", deskewed))
                
                # 기울기 보정 + 적응형 임계값
                if self.options.get('adaptive_threshold', True):
                    deskewed_adaptive = self._adaptive_threshold(deskewed)
                    processed_images.append(("deskewed_adaptive", deskewed_adaptive))
        
        # 4. 선명화
        if self.options.get('sharpen', True):
            sharpened = self._sharpen_image(gray)
            processed_images.append(("sharpened", sharpened))
        
        # 5. 블러 제거
        if self.options.get('blur_removal', True):
            deblurred = self._remove_blur(gray)
            processed_images.append(("deblurred", deblurred))
        
        # 6. 조합 처리 (선명화 + 적응형 임계값)
        if (self.options.get('sharpen', True) and 
            self.options.get('adaptive_threshold', True)):
            sharpened = self._sharpen_image(gray)
            sharp_adaptive = self._adaptive_threshold(sharpened)
            processed_images.append(("sharp_adaptive", sharp_adaptive))
        
        return processed_images
    
    def extract_from_image(self, image: Image.Image) -> QRResult:
        """이미지에서 QR 코드 추출 (전처리 + Pyzbar)"""
        start_time = time.time()
        
        if not self.is_available():
            return QRResult(
                success=False,
                codes=[],
                engine=self.name,
                processing_time=0.0,
                error_message="Pyzbar Preproc 엔진을 사용할 수 없습니다"
            )
        
        try:
            # 여러 전처리 버전 생성
            processed_images = self._preprocess_image(image)
            
            all_codes = []
            successful_methods = []
            
            # 각 전처리 버전에서 QR 코드 추출 시도
            for method_name, processed_img in processed_images:
                try:
                    decoded_objects = pyzbar.decode(processed_img)
                    
                    method_codes = []
                    for obj in decoded_objects:
                        if obj.type == 'QRCODE':
                            try:
                                code_text = obj.data.decode('utf-8')
                                method_codes.append(code_text)
                            except UnicodeDecodeError:
                                continue
                    
                    if method_codes:
                        all_codes.extend(method_codes)
                        successful_methods.append(method_name)
                        logger.debug(f"Pyzbar Preproc ({method_name}) QR 코드 발견: {method_codes}")
                
                except Exception as e:
                    logger.debug(f"전처리 방법 {method_name} 실패: {e}")
                    continue
            
            # 중복 제거
            unique_codes = list(set(all_codes))
            
            processing_time = time.time() - start_time
            
            return QRResult(
                success=len(unique_codes) > 0,
                codes=unique_codes,
                engine=self.name,
                processing_time=processing_time,
                debug_info={
                    'total_methods_tried': len(processed_images),
                    'successful_methods': successful_methods,
                    'total_codes_found': len(all_codes),
                    'unique_codes': len(unique_codes)
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Pyzbar Preproc QR 추출 오류: {e}")
            
            return QRResult(
                success=False,
                codes=[],
                engine=self.name,
                processing_time=processing_time,
                error_message=str(e)
            )
