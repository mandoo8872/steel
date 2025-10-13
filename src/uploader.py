"""
업로드 모듈 - NAS 및 HTTP 업로드 지원
"""
import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple
import httpx
import asyncio
from datetime import datetime
from loguru import logger
import json
import platform


class BaseUploader:
    """업로더 기본 클래스"""
    
    def __init__(self, config):
        self.config = config
    
    async def upload(self, file_path: Path, transport_no: str) -> Dict:
        """업로드 수행"""
        raise NotImplementedError
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """파일 해시 계산"""
        hasher = hashlib.sha1()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def get_idempotency_key(self, transport_no: str, file_hash: str) -> str:
        """멱등성 키 생성"""
        return f"{transport_no}-{file_hash}"


class NASUploader(BaseUploader):
    """NAS 업로더"""
    
    def __init__(self, config):
        super().__init__(config)
        self.nas_path = Path(config.upload.nas.path)
        self.username = config.upload.nas.username
        self.password = config.upload.nas.password
    
    async def upload(self, file_path: Path, transport_no: str) -> Dict:
        """NAS로 파일 복사"""
        result = {
            'success': False,
            'message': '',
            'destination': None
        }
        
        try:
            # 대상 경로 생성 (날짜 폴더 없이 바로 저장)
            dest_dir = self.nas_path
            dest_file = dest_dir / f"{transport_no}.pdf"
            
            # Windows 네트워크 드라이브 연결 (필요한 경우)
            if platform.system() == 'Windows' and self.username:
                await self._connect_network_drive()
            
            # 디렉토리 생성
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # 파일 해시 계산
            file_hash = self.calculate_file_hash(file_path)
            
            # 기존 파일 확인 (멱등성)
            if dest_file.exists():
                existing_hash = self.calculate_file_hash(dest_file)
                if existing_hash == file_hash:
                    logger.info(f"동일한 파일이 이미 존재: {dest_file}")
                    result['success'] = True
                    result['message'] = '이미 업로드됨 (동일 파일)'
                    result['destination'] = str(dest_file)
                    return result
                else:
                    # 다른 파일인 경우 덮어쓰기
                    logger.warning(f"다른 내용의 파일 덮어쓰기: {dest_file}")
            
            # 파일 복사
            shutil.copy2(str(file_path), str(dest_file))
            
            # 검증
            if dest_file.exists() and dest_file.stat().st_size == file_path.stat().st_size:
                result['success'] = True
                result['message'] = '업로드 성공'
                result['destination'] = str(dest_file)
                logger.info(f"NAS 업로드 성공: {file_path} -> {dest_file}")
            else:
                raise Exception("파일 크기 불일치")
            
        except Exception as e:
            result['message'] = f"NAS 업로드 실패: {str(e)}"
            logger.error(f"NAS 업로드 오류: {file_path} - {e}")
        
        return result
    
    async def _connect_network_drive(self):
        """Windows 네트워크 드라이브 연결"""
        if not self.username or not self.password:
            return
        
        try:
            nas_unc = str(self.nas_path).replace('/', '\\')
            if nas_unc.startswith('\\\\'):
                cmd = f'net use "{nas_unc}" /user:{self.username} {self.password}'
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.wait()
        except Exception as e:
            logger.warning(f"네트워크 드라이브 연결 실패: {e}")


class HTTPUploader(BaseUploader):
    """HTTP 업로더"""
    
    def __init__(self, config):
        super().__init__(config)
        self.endpoint = config.upload.http.endpoint
        self.token = config.upload.http.token
        self.timeout = config.upload.http.timeout
        self.max_file_size = config.upload.http.max_file_size * 1024 * 1024  # MB to bytes
    
    async def upload(self, file_path: Path, transport_no: str) -> Dict:
        """HTTP API로 파일 업로드"""
        result = {
            'success': False,
            'message': '',
            'response': None
        }
        
        try:
            # 파일 크기 확인
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                raise Exception(f"파일 크기 초과: {file_size / 1024 / 1024:.1f}MB > {self.max_file_size / 1024 / 1024}MB")
            
            # 파일 해시 계산
            file_hash = self.calculate_file_hash(file_path)
            idempotency_key = self.get_idempotency_key(transport_no, file_hash)
            
            # HTTP 클라이언트 생성
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # 헤더 설정
                headers = {
                    'Authorization': f'Bearer {self.token}',
                    'X-Idempotency-Key': idempotency_key,
                    'X-Transport-No': transport_no,
                    'X-File-Hash': file_hash
                }
                
                # 파일 업로드
                with open(file_path, 'rb') as f:
                    files = {'file': (f'{transport_no}.pdf', f, 'application/pdf')}
                    
                    response = await client.post(
                        self.endpoint,
                        files=files,
                        headers=headers
                    )
                
                # 응답 처리
                if response.status_code == 200:
                    result['success'] = True
                    result['message'] = '업로드 성공'
                    result['response'] = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    logger.info(f"HTTP 업로드 성공: {file_path} -> {self.endpoint}")
                
                elif response.status_code == 409:  # Conflict - 이미 존재
                    result['success'] = True
                    result['message'] = '이미 업로드됨 (멱등성)'
                    result['response'] = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                    logger.info(f"이미 업로드된 파일: {transport_no}")
                
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
            
        except httpx.TimeoutException:
            result['message'] = f"업로드 타임아웃 ({self.timeout}초)"
            logger.error(f"HTTP 업로드 타임아웃: {file_path}")
        
        except Exception as e:
            result['message'] = f"HTTP 업로드 실패: {str(e)}"
            logger.error(f"HTTP 업로드 오류: {file_path} - {e}")
        
        return result


class CombinedUploader(BaseUploader):
    """NAS + HTTP 복합 업로더"""
    
    def __init__(self, config):
        super().__init__(config)
        self.nas_uploader = NASUploader(config)
        self.http_uploader = HTTPUploader(config)
    
    async def upload(self, file_path: Path, transport_no: str) -> Dict:
        """NAS와 HTTP 모두 업로드"""
        result = {
            'success': False,
            'nas_result': None,
            'http_result': None,
            'message': ''
        }
        
        # 병렬 업로드
        nas_task = asyncio.create_task(self.nas_uploader.upload(file_path, transport_no))
        http_task = asyncio.create_task(self.http_uploader.upload(file_path, transport_no))
        
        nas_result, http_result = await asyncio.gather(nas_task, http_task, return_exceptions=True)
        
        # 결과 처리
        if isinstance(nas_result, Exception):
            nas_result = {'success': False, 'message': str(nas_result)}
        if isinstance(http_result, Exception):
            http_result = {'success': False, 'message': str(http_result)}
        
        result['nas_result'] = nas_result
        result['http_result'] = http_result
        
        # 전체 성공 여부 판단
        if nas_result.get('success') and http_result.get('success'):
            result['success'] = True
            result['message'] = 'NAS와 HTTP 모두 업로드 성공'
        elif nas_result.get('success') or http_result.get('success'):
            result['success'] = True
            result['message'] = '부분 업로드 성공'
        else:
            result['message'] = 'NAS와 HTTP 모두 업로드 실패'
        
        return result


class DummyUploader:
    """업로드 비활성화 시 사용하는 더미 업로더"""
    
    def __init__(self, config):
        self.config = config
    
    async def upload(self, file_path: Path, transport_no: str) -> Dict:
        """업로드 스킵 (즉시 성공 반환)"""
        return {
            'success': True,
            'message': '업로드 비활성화됨 (테스트 모드)',
            'destination': None
        }


class UploadManager:
    """업로드 관리자"""
    
    def __init__(self, config):
        self.config = config
        
        # 업로더 선택
        if config.upload.type == 'none':
            self.uploader = DummyUploader(config)
            logger.info("업로드 관리자 초기화 - 타입: none (업로드 비활성화)")
        elif config.upload.type == 'nas':
            self.uploader = NASUploader(config)
            logger.info(f"업로드 관리자 초기화 - 타입: {config.upload.type}")
        elif config.upload.type == 'http':
            self.uploader = HTTPUploader(config)
            logger.info(f"업로드 관리자 초기화 - 타입: {config.upload.type}")
        elif config.upload.type == 'both':
            self.uploader = CombinedUploader(config)
            logger.info(f"업로드 관리자 초기화 - 타입: {config.upload.type}")
        else:
            raise ValueError(f"지원하지 않는 업로드 타입: {config.upload.type}")
    
    async def upload_file(self, file_path: Path, transport_no: str) -> Dict:
        """파일 업로드"""
        return await self.uploader.upload(file_path, transport_no)
    
    def get_upload_path(self, transport_no: str) -> Path:
        """업로드 경로 생성 (날짜 폴더 없이)"""
        return self.config.paths.uploaded / f"{transport_no}.pdf"
