"""
QR 코드 인식 모듈
"""
import re
from typing import List, Tuple, Optional
from pathlib import Path
import cv2
import numpy as np
from pyzbar import pyzbar
from pdf2image import convert_from_path
from PIL import Image
from loguru import logger
import tempfile
import json


class QRReader:
    """QR 코드 리더"""
    
    def __init__(self, pattern: str = r"^\d{14}$"):
        self.pattern = re.compile(pattern)
        logger.info(f"QR 리더 초기화 - 패턴: {pattern}")
    
    def read_from_pdf(self, pdf_path: Path) -> Tuple[List[str], List[str]]:
        """
        PDF에서 QR 코드 읽기
        
        Returns:
            (valid_codes, all_codes) - 패턴 매칭된 코드와 전체 코드
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        all_codes = []
        valid_codes = []
        
        try:
            # PDF를 이미지로 변환
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.debug(f"PDF를 이미지로 변환 중: {pdf_path}")
                images = convert_from_path(
                    str(pdf_path),
                    dpi=300,
                    output_folder=temp_dir,
                    fmt='png'
                )
                
                # 각 페이지에서 QR 코드 검색
                for i, image in enumerate(images):
                    logger.debug(f"페이지 {i+1}/{len(images)} 처리 중")
                    page_codes = self._read_from_image(image)
                    all_codes.extend(page_codes)
                
                # 중복 제거
                all_codes = list(set(all_codes))
                
                # 패턴 매칭
                for code in all_codes:
                    if self.pattern.match(code):
                        valid_codes.append(code)
                        logger.info(f"유효한 QR 코드 발견: {code}")
                    else:
                        logger.debug(f"패턴 불일치 QR 코드: {code}")
                
                # 유효한 코드도 중복 제거
                valid_codes = list(set(valid_codes))
                
                logger.info(f"QR 인식 완료 - 전체: {len(all_codes)}, 유효: {len(valid_codes)}")
                return valid_codes, all_codes
                
        except Exception as e:
            logger.error(f"PDF QR 인식 오류: {e}")
            raise
    
    def _read_from_image(self, image: Image.Image) -> List[str]:
        """이미지에서 QR 코드 읽기"""
        codes = []
        
        try:
            # PIL 이미지를 OpenCV 형식으로 변환
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # QR 코드 검출
            decoded_objects = pyzbar.decode(cv_image)
            
            for obj in decoded_objects:
                # QR 코드만 처리 (1D 바코드 무시)
                if obj.type == 'QRCODE':
                    code_data = obj.data.decode('utf-8')
                    codes.append(code_data)
                    logger.debug(f"QR 코드 검출: {code_data}")
                else:
                    logger.debug(f"무시된 바코드 타입: {obj.type}")
            
            # 검출 실패 시 이미지 전처리 후 재시도
            if not codes:
                codes.extend(self._read_with_preprocessing(cv_image))
            
        except Exception as e:
            logger.error(f"이미지 QR 인식 오류: {e}")
        
        return codes
    
    def _read_with_preprocessing(self, image: np.ndarray) -> List[str]:
        """이미지 전처리 후 QR 코드 읽기"""
        codes = []
        
        try:
            # 그레이스케일 변환
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 적응형 임계값 처리
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 노이즈 제거
            denoised = cv2.medianBlur(thresh, 3)
            
            # QR 코드 재검출
            decoded_objects = pyzbar.decode(denoised)
            
            for obj in decoded_objects:
                if obj.type == 'QRCODE':
                    code_data = obj.data.decode('utf-8')
                    codes.append(code_data)
                    logger.debug(f"전처리 후 QR 코드 검출: {code_data}")
            
        except Exception as e:
            logger.error(f"이미지 전처리 QR 인식 오류: {e}")
        
        return codes
    
    def validate_transport_no(self, code: str) -> bool:
        """운송번호 유효성 검사"""
        return bool(self.pattern.match(code))
    
    def extract_date_from_transport_no(self, transport_no: str) -> Optional[str]:
        """
        운송번호에서 날짜 추출 (앞 8자리)
        
        Returns:
            YYYYMMDD 형식의 날짜 문자열
        """
        if self.validate_transport_no(transport_no):
            return transport_no[:8]
        return None


class QRProcessor:
    """QR 처리 프로세서"""
    
    def __init__(self, reader: QRReader):
        self.reader = reader
    
    def process_document(self, pdf_path: Path) -> dict:
        """
        문서 처리 및 QR 정보 추출
        
        Returns:
            {
                'status': 'success' | 'error' | 'multiple',
                'transport_no': str | None,
                'all_qr_codes': List[str],
                'valid_qr_codes': List[str],
                'error_message': str | None
            }
        """
        result = {
            'status': 'error',
            'transport_no': None,
            'all_qr_codes': [],
            'valid_qr_codes': [],
            'error_message': None
        }
        
        try:
            # QR 코드 읽기
            valid_codes, all_codes = self.reader.read_from_pdf(pdf_path)
            
            result['all_qr_codes'] = all_codes
            result['valid_qr_codes'] = valid_codes
            
            # 유효한 QR 코드가 없는 경우
            if not valid_codes:
                result['status'] = 'error'
                result['error_message'] = 'QR 코드를 찾을 수 없거나 패턴이 일치하지 않습니다.'
                logger.warning(f"유효한 QR 미검출: {pdf_path}")
            
            # 단일 QR 코드
            elif len(valid_codes) == 1:
                result['status'] = 'success'
                result['transport_no'] = valid_codes[0]
                logger.info(f"운송번호 추출 성공: {valid_codes[0]}")
            
            # 다중 QR 코드
            else:
                result['status'] = 'multiple'
                result['error_message'] = f'다중 QR 코드 검출: {", ".join(valid_codes)}'
                logger.warning(f"다중 QR 검출: {pdf_path} - {valid_codes}")
        
        except Exception as e:
            result['status'] = 'error'
            result['error_message'] = str(e)
            logger.error(f"QR 처리 오류: {pdf_path} - {e}")
        
        return result
