"""
ZXing 기반 QR 엔진 (구글 기반, 기울기·훼손 QR에 강함)
"""
import time
import subprocess
import tempfile
import json
from pathlib import Path
from PIL import Image
from loguru import logger

from .base import QREngine, QRResult


class ZXingEngine(QREngine):
    """ZXing 기반 QR 엔진"""
    
    def __init__(self, config: dict = None):
        super().__init__("ZXING", config)
        self.zxing_jar_path = self._find_zxing_jar()
    
    def _find_zxing_jar(self) -> str:
        """ZXing JAR 파일 경로 찾기"""
        # 일반적인 ZXing JAR 위치들
        possible_paths = [
            "/usr/local/lib/zxing/core.jar",
            "/opt/zxing/core.jar",
            "lib/zxing/core.jar",
            "zxing/core.jar"
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                return path
        
        # 시스템에서 찾기 시도
        try:
            result = subprocess.run(
                ["find", "/", "-name", "*zxing*.jar", "-type", "f"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                jar_files = result.stdout.strip().split('\n')
                if jar_files:
                    return jar_files[0]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        
        return None
    
    def is_available(self) -> bool:
        """ZXing 엔진 사용 가능 여부"""
        if not self.enabled:
            return False
        
        # Java 확인
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            java_available = result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            java_available = False
        
        # ZXing JAR 파일 확인
        zxing_available = self.zxing_jar_path is not None
        
        return java_available and zxing_available
    
    def extract_from_image(self, image: Image.Image) -> QRResult:
        """이미지에서 QR 코드 추출 (ZXing)"""
        start_time = time.time()
        
        if not self.is_available():
            return QRResult(
                success=False,
                codes=[],
                engine=self.name,
                processing_time=0.0,
                error_message="ZXing 엔진을 사용할 수 없습니다 (Java 또는 ZXing JAR 없음)"
            )
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                # 이미지를 임시 파일로 저장
                image.save(temp_file.name, 'PNG')
                temp_path = temp_file.name
            
            try:
                # ZXing 명령어 실행
                cmd = [
                    "java", "-cp", self.zxing_jar_path,
                    "com.google.zxing.client.j2se.CommandLineRunner",
                    temp_path
                ]
                
                # try_harder 옵션 추가
                if self.options.get('try_harder', True):
                    cmd.extend(["--try_harder"])
                
                # 포맷 지정
                formats = self.options.get('formats', ['QR_CODE'])
                if formats:
                    cmd.extend(["--possible_formats", ",".join(formats)])
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                
                codes = []
                if result.returncode == 0 and result.stdout.strip():
                    # ZXing 출력 파싱
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.startswith('Raw result:'):
                            # "Raw result:" 다음의 텍스트 추출
                            code_text = line.replace('Raw result:', '').strip()
                            if code_text:
                                codes.append(code_text)
                                logger.debug(f"ZXing QR 코드 발견: {code_text}")
                
                processing_time = time.time() - start_time
                
                return QRResult(
                    success=len(codes) > 0,
                    codes=codes,
                    engine=self.name,
                    processing_time=processing_time,
                    debug_info={
                        'command': ' '.join(cmd),
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'returncode': result.returncode
                    }
                )
                
            finally:
                # 임시 파일 삭제
                Path(temp_path).unlink(missing_ok=True)
            
        except subprocess.TimeoutExpired:
            processing_time = time.time() - start_time
            return QRResult(
                success=False,
                codes=[],
                engine=self.name,
                processing_time=processing_time,
                error_message=f"ZXing 처리 시간 초과 ({self.timeout}초)"
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"ZXing QR 추출 오류: {e}")
            
            return QRResult(
                success=False,
                codes=[],
                engine=self.name,
                processing_time=processing_time,
                error_message=str(e)
            )
