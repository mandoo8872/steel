"""
PDF 처리 모듈 - 병합, 중복 제거, 정규화
"""
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set
import pikepdf
from PyPDF2 import PdfReader, PdfWriter
from loguru import logger
import tempfile
import shutil


class PDFProcessor:
    """PDF 처리기"""
    
    def __init__(self, config):
        self.config = config
        self.hash_algorithm = config.pdf.hash_algorithm
        logger.info(f"PDF 프로세서 초기화 - 해시: {self.hash_algorithm}, 정규화: {config.pdf.normalize}")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """파일 해시 계산"""
        hasher = hashlib.sha1() if self.hash_algorithm == 'sha1' else hashlib.md5()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def calculate_page_hash(self, page_content: bytes) -> str:
        """페이지 내용 해시 계산"""
        hasher = hashlib.sha1() if self.hash_algorithm == 'sha1' else hashlib.md5()
        hasher.update(page_content)
        return hasher.hexdigest()
    
    def merge_pdfs(self, pdf_files: List[Path], output_path: Path, 
                   remove_duplicates: bool = True) -> Dict:
        """
        여러 PDF 파일을 하나로 병합
        
        Returns:
            {
                'success': bool,
                'page_count': int,
                'duplicate_count': int,
                'error': str | None
            }
        """
        result = {
            'success': False,
            'page_count': 0,
            'duplicate_count': 0,
            'error': None
        }
        
        if not pdf_files:
            result['error'] = "병합할 PDF 파일이 없습니다."
            return result
        
        try:
            writer = PdfWriter()
            page_hashes = set() if remove_duplicates else None
            duplicate_count = 0
            
            # 파일명 순으로 정렬 (운송번호(1).pdf, 운송번호(2).pdf 순서 보장)
            sorted_files = sorted(pdf_files, key=lambda x: x.name)
            
            for pdf_file in sorted_files:
                try:
                    reader = PdfReader(str(pdf_file))
                    
                    for page_num in range(len(reader.pages)):
                        page = reader.pages[page_num]
                        
                        # 중복 검사
                        if remove_duplicates and page_hashes is not None:
                            # 페이지 객체 전체를 직렬화하여 해시 계산 (이미지 PDF 포함)
                            try:
                                # 페이지의 원본 데이터 스트림을 사용
                                import io
                                from PyPDF2 import PdfWriter as TempWriter
                                
                                temp_writer = TempWriter()
                                temp_writer.add_page(page)
                                
                                # 메모리에 페이지 작성
                                temp_buffer = io.BytesIO()
                                temp_writer.write(temp_buffer)
                                page_content = temp_buffer.getvalue()
                                
                                page_hash = self.calculate_page_hash(page_content)
                                
                                if page_hash in page_hashes:
                                    duplicate_count += 1
                                    logger.debug(f"중복 페이지 발견: {pdf_file} - 페이지 {page_num + 1}")
                                    continue
                                
                                page_hashes.add(page_hash)
                            except Exception as e:
                                # 해시 계산 실패 시 페이지 추가 (안전 모드)
                                logger.warning(f"페이지 해시 계산 실패: {pdf_file} 페이지 {page_num + 1} - {e}")
                                pass
                        
                        writer.add_page(page)
                        result['page_count'] += 1
                    
                    logger.info(f"PDF 추가 완료: {pdf_file} - {len(reader.pages)}페이지")
                    
                except Exception as e:
                    logger.error(f"PDF 읽기 오류: {pdf_file} - {e}")
                    # 개별 파일 오류는 무시하고 계속 진행
            
            if result['page_count'] == 0:
                result['error'] = "병합할 유효한 페이지가 없습니다."
                return result
            
            # 병합된 PDF 저장
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            result['success'] = True
            result['duplicate_count'] = duplicate_count
            
            # PDF 정규화
            if self.config.pdf.normalize:
                self._normalize_pdf(output_path)
            
            logger.info(f"PDF 병합 완료: {output_path} - {result['page_count']}페이지 (중복 {duplicate_count}페이지 제거)")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"PDF 병합 오류: {e}")
        
        return result
    
    def _normalize_pdf(self, pdf_path: Path) -> bool:
        """PDF 정규화 (linearize)"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_path = Path(temp_file.name)
            
            # pikepdf로 열어서 정규화
            with pikepdf.open(pdf_path) as pdf:
                pdf.save(temp_path, linearize=True, compress_streams=True)
            
            # 원본 파일 교체
            shutil.move(str(temp_path), str(pdf_path))
            
            logger.debug(f"PDF 정규화 완료: {pdf_path}")
            return True
            
        except Exception as e:
            logger.error(f"PDF 정규화 실패: {pdf_path} - {e}")
            return False
    
    def convert_to_pdf_a(self, pdf_path: Path) -> bool:
        """PDF/A 변환"""
        if not self.config.pdf.pdf_a_convert:
            return True
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_path = Path(temp_file.name)
            
            # pikepdf로 PDF/A 변환
            with pikepdf.open(pdf_path) as pdf:
                # PDF/A-2b 메타데이터 추가
                pdf.docinfo['/Creator'] = 'QR Scan System'
                pdf.docinfo['/Producer'] = 'pikepdf'
                
                # PDF/A 호환 저장
                pdf.save(
                    temp_path,
                    linearize=True,
                    compress_streams=True,
                    preserve_pdfa=True
                )
            
            # 원본 파일 교체
            shutil.move(str(temp_path), str(pdf_path))
            
            logger.info(f"PDF/A 변환 완료: {pdf_path}")
            return True
            
        except Exception as e:
            logger.error(f"PDF/A 변환 실패: {pdf_path} - {e}")
            return False
    
    def get_pdf_info(self, pdf_path: Path) -> Dict:
        """PDF 정보 추출"""
        info = {
            'page_count': 0,
            'file_size': 0,
            'is_valid': False,
            'error': None
        }
        
        try:
            info['file_size'] = pdf_path.stat().st_size
            
            reader = PdfReader(str(pdf_path))
            info['page_count'] = len(reader.pages)
            info['is_valid'] = True
            
        except Exception as e:
            info['error'] = str(e)
            logger.error(f"PDF 정보 추출 오류: {pdf_path} - {e}")
        
        return info
    
    def split_pdf(self, pdf_path: Path, output_dir: Path) -> List[Path]:
        """PDF를 페이지별로 분할"""
        output_files = []
        
        try:
            reader = PdfReader(str(pdf_path))
            base_name = pdf_path.stem
            
            for i in range(len(reader.pages)):
                writer = PdfWriter()
                writer.add_page(reader.pages[i])
                
                output_path = output_dir / f"{base_name}_page_{i+1}.pdf"
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                
                output_files.append(output_path)
            
            logger.info(f"PDF 분할 완료: {pdf_path} -> {len(output_files)}개 파일")
            
        except Exception as e:
            logger.error(f"PDF 분할 오류: {pdf_path} - {e}")
        
        return output_files
