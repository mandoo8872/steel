"""
다중 엔진 QR 코드 리더
"""
import re
import time
import os
import platform
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path
from loguru import logger
import tempfile
import json
from datetime import datetime

from .qr_engines import QREngine, QRResult, ZBarEngine, ZXingEngine, PyzbarPreprocEngine


class MultiQRReader:
    """다중 엔진 QR 코드 리더"""
    
    def __init__(self, config):
        """
        Args:
            config: QRConfig 객체
        """
        self.config = config
        self.pattern = re.compile(config.pattern)
        
        # Poppler 경로 자동 감지 (Windows)
        self.poppler_path = self._find_poppler_path()
        if self.poppler_path:
            logger.info(f"Poppler 경로 감지: {self.poppler_path}")
        
        # 엔진 초기화
        self.engines = self._initialize_engines()
        
        # 실패 이미지 저장 경로
        self.failed_images_path = Path(config.failed_images_path)
        if config.save_failed_images:
            self.failed_images_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"다중 QR 리더 초기화 완료 - 패턴: {config.pattern}")
        logger.info(f"엔진 순서: {config.engine_order}")
        logger.info(f"사용 가능한 엔진: {[name for name, engine in self.engines.items() if engine.is_available()]}")
    
    def _find_poppler_path(self) -> Optional[str]:
        """Poppler 경로 자동 감지"""
        if platform.system() == 'Windows':
            # Windows에서 일반적인 Poppler 설치 경로
            common_paths = [
                r"C:\Program Files\poppler\Library\bin",
                r"C:\Program Files (x86)\poppler\Library\bin",
                r"C:\poppler\Library\bin",
            ]
            
            for path in common_paths:
                if os.path.exists(path) and os.path.exists(os.path.join(path, "pdftoppm.exe")):
                    return path
        
        # PATH에서 찾기
        try:
            if platform.system() == 'Windows':
                import shutil
                if shutil.which("pdftoppm.exe"):
                    return None  # PATH에 있으면 None 반환 (pdf2image가 자동으로 찾음)
        except:
            pass
        
        return None
    
    def _initialize_engines(self) -> Dict[str, QREngine]:
        """QR 엔진들 초기화"""
        engines = {}
        
        # ZBar 엔진
        if 'ZBAR' in self.config.engine_order:
            zbar_config = self.config.zbar if hasattr(self.config.zbar, '__dict__') else self.config.zbar
            engines['ZBAR'] = ZBarEngine(zbar_config)
        
        # ZXing 엔진
        if 'ZXING' in self.config.engine_order:
            zxing_config = self.config.zxing if hasattr(self.config.zxing, '__dict__') else self.config.zxing
            engines['ZXING'] = ZXingEngine(zxing_config)
        
        # Pyzbar Preproc 엔진
        if 'PYZBAR_PREPROC' in self.config.engine_order:
            pp_config = self.config.pyzbar_preproc if hasattr(self.config.pyzbar_preproc, '__dict__') else self.config.pyzbar_preproc
            engines['PYZBAR_PREPROC'] = PyzbarPreprocEngine(pp_config)
        
        return engines
    
    def _extract_from_image_multi_engine(self, image: Image.Image, page_num: int = 0) -> Tuple[List[str], str, Dict]:
        """
        다중 엔진으로 이미지에서 QR 코드 추출
        
        Args:
            image: PIL Image 객체
            page_num: 페이지 번호 (로깅용)
            
        Returns:
            (codes, successful_engine, debug_info)
        """
        all_results = []
        
        # 설정된 순서대로 엔진 시도
        for engine_name in self.config.engine_order:
            if engine_name not in self.engines:
                logger.warning(f"알 수 없는 엔진: {engine_name}")
                continue
            
            engine = self.engines[engine_name]
            
            if not engine.is_available():
                logger.debug(f"엔진 {engine_name} 사용 불가능")
                continue
            
            logger.debug(f"페이지 {page_num}: {engine_name} 엔진으로 QR 추출 시도")
            
            try:
                result = engine.extract_from_image(image)
                all_results.append(result)
                
                if result.success and result.codes:
                    logger.info(f"페이지 {page_num}: {engine_name} 엔진에서 QR 코드 발견 - {result.codes}")
                    return result.codes, engine_name, {
                        'successful_engine': engine_name,
                        'processing_time': result.processing_time,
                        'all_attempts': all_results,
                        'debug_info': result.debug_info
                    }
                else:
                    logger.debug(f"페이지 {page_num}: {engine_name} 엔진에서 QR 코드 없음")
            
            except Exception as e:
                logger.error(f"페이지 {page_num}: {engine_name} 엔진 오류 - {e}")
                all_results.append(QRResult(
                    success=False,
                    codes=[],
                    engine=engine_name,
                    processing_time=0.0,
                    error_message=str(e)
                ))
        
        # 모든 엔진 실패
        logger.warning(f"페이지 {page_num}: 모든 QR 엔진에서 코드를 찾지 못했습니다")
        
        # 실패 이미지 저장
        if self.config.save_failed_images:
            self._save_failed_image(image, page_num, all_results)
        
        return [], "FAIL", {
            'successful_engine': None,
            'all_attempts': all_results,
            'total_engines_tried': len([r for r in all_results if r.engine in self.config.engine_order])
        }
    
    def _save_failed_image(self, image: Image.Image, page_num: int, results: List[QRResult]):
        """실패한 이미지와 디버그 정보 저장"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"failed_qr_{timestamp}_page_{page_num}"
            
            # 이미지 저장
            image_path = self.failed_images_path / f"{base_name}.png"
            image.save(image_path, 'PNG')
            
            # 디버그 정보 저장
            debug_info = {
                'timestamp': timestamp,
                'page_number': page_num,
                'image_path': str(image_path),
                'engine_results': []
            }
            
            for result in results:
                debug_info['engine_results'].append({
                    'engine': result.engine,
                    'success': result.success,
                    'codes': result.codes,
                    'processing_time': result.processing_time,
                    'error_message': result.error_message,
                    'debug_info': result.debug_info
                })
            
            debug_path = self.failed_images_path / f"{base_name}.json"
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)
            
            logger.info(f"실패 이미지 저장: {image_path}")
            
        except Exception as e:
            logger.error(f"실패 이미지 저장 오류: {e}")
    
    def _find_optimal_dpi(self, pdf_path: Path, temp_dir: str) -> int:
        """
        QR 인식을 위한 최적 DPI 찾기 (첫 페이지 테스트)
        
        Returns:
            optimal_dpi - 최적 DPI 값
        """
        # 적응형 DPI가 비활성화된 경우 고정 DPI 반환
        if not self.config.adaptive_dpi:
            logger.debug(f"적응형 DPI 비활성화, 고정 DPI {self.config.fixed_dpi} 사용")
            return self.config.fixed_dpi
        
        # DPI 후보 목록 (설정에서 읽기)
        dpi_candidates = self.config.dpi_candidates
        
        for dpi in dpi_candidates:
            try:
                logger.debug(f"DPI {dpi}로 첫 페이지 테스트 중...")
                
                # 첫 페이지만 변환
                test_images = convert_from_path(
                    str(pdf_path),
                    dpi=dpi,
                    first_page=1,
                    last_page=1,
                    output_folder=temp_dir,
                    fmt='png',
                    poppler_path=self.poppler_path
                )
                
                if test_images:
                    # QR 인식 테스트
                    test_codes, _, _ = self._extract_from_image_multi_engine(test_images[0], 0)
                    
                    if test_codes:
                        logger.info(f"✓ 최적 DPI 발견: {dpi} (QR 인식 성공)")
                        return dpi
                    
            except Exception as e:
                logger.debug(f"DPI {dpi} 테스트 오류: {e}")
                continue
        
        # 기본값 반환 (설정의 fixed_dpi 또는 200)
        fallback_dpi = getattr(self.config, 'fixed_dpi', 200)
        logger.info(f"최적 DPI를 찾지 못함, 기본값 {fallback_dpi} 사용")
        return fallback_dpi
    
    def read_from_pdf(self, pdf_path: Path) -> Tuple[List[str], List[str], Dict]:
        """
        PDF에서 QR 코드 읽기 (다중 엔진, 적응형 DPI)
        
        Returns:
            (valid_codes, all_codes, processing_info) - 패턴 매칭된 코드, 전체 코드, 처리 정보
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
        
        all_codes = []
        valid_codes = []
        processing_info = {
            'total_pages': 0,
            'pages_with_qr': 0,
            'engine_success_count': {},
            'total_processing_time': 0.0,
            'page_results': [],
            'dpi_used': None
        }
        
        start_time = time.time()
        
        try:
            # 적응형 DPI로 PDF를 이미지로 변환
            with tempfile.TemporaryDirectory() as temp_dir:
                # 최적 DPI 찾기
                optimal_dpi = self._find_optimal_dpi(pdf_path, temp_dir)
                processing_info['dpi_used'] = optimal_dpi
                
                logger.debug(f"DPI {optimal_dpi}로 전체 PDF 변환 중: {pdf_path}")
                images = convert_from_path(
                    str(pdf_path),
                    dpi=optimal_dpi,
                    output_folder=temp_dir,
                    fmt='png',
                    poppler_path=self.poppler_path
                )
                
                processing_info['total_pages'] = len(images)
                
                # 각 페이지에서 QR 코드 검색
                for i, image in enumerate(images):
                    logger.debug(f"페이지 {i+1}/{len(images)} 처리 중")
                    
                    page_codes, successful_engine, page_debug = self._extract_from_image_multi_engine(image, i+1)
                    
                    page_result = {
                        'page_number': i+1,
                        'codes_found': page_codes,
                        'successful_engine': successful_engine,
                        'debug_info': page_debug
                    }
                    processing_info['page_results'].append(page_result)
                    
                    if page_codes:
                        processing_info['pages_with_qr'] += 1
                        
                        # 엔진 성공 카운트
                        if successful_engine != "FAIL":
                            processing_info['engine_success_count'][successful_engine] = \
                                processing_info['engine_success_count'].get(successful_engine, 0) + 1
                        
                        all_codes.extend(page_codes)
                        
                        # 패턴 매칭 검사
                        for code in page_codes:
                            if self.pattern.match(code):
                                valid_codes.append(code)
                                logger.info(f"유효한 QR 코드 발견 (페이지 {i+1}, {successful_engine}): {code}")
                            else:
                                logger.warning(f"패턴 불일치 QR 코드 (페이지 {i+1}, {successful_engine}): {code}")
        
        except Exception as e:
            logger.error(f"PDF QR 추출 오류: {e}")
            raise
        
        finally:
            processing_info['total_processing_time'] = time.time() - start_time
        
        logger.info(f"PDF QR 추출 완료: {pdf_path}")
        logger.info(f"총 {len(all_codes)}개 QR 코드 발견, {len(valid_codes)}개 유효")
        logger.info(f"엔진별 성공 횟수: {processing_info['engine_success_count']}")
        
        return valid_codes, all_codes, processing_info
    
    def get_engine_status(self) -> Dict[str, Dict]:
        """엔진 상태 정보 반환"""
        status = {}
        for name, engine in self.engines.items():
            status[name] = engine.get_info()
        return status
    
    def validate_qr_code(self, code: str) -> bool:
        """QR 코드 패턴 검증"""
        return bool(self.pattern.match(code))
