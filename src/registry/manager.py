"""
인스턴스 레지스트리 관리
중앙 저장소(HTTP/SMB) + 로컬 오버라이드 지원
"""

import json
import requests
from pathlib import Path
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, asdict
from loguru import logger


@dataclass
class InstanceAuth:
    """
    인스턴스 인증 정보
    
    확장 가능한 auth 스키마 (type 필드로 분기)
    
    type="basic": username + password
    type="jwt": token + refresh_token
    type="token": token (Bearer)
    type="cert": cert_path + key_path
    type="sso": sso_provider + redirect_url
    """
    type: str = "basic"  # basic, jwt, token, cert, sso
    
    # Basic Auth
    username: str = ""
    password: str = ""
    
    # JWT / Token (향후 구현)
    token: str = ""
    refresh_token: str = ""
    
    # Certificate (향후 구현)
    cert_path: str = ""
    key_path: str = ""
    
    # SSO (향후 구현)
    sso_provider: str = ""
    redirect_url: str = ""
    
    # 추가 메타데이터
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_headers(self) -> Dict[str, str]:
        """
        인증 타입에 따른 HTTP 헤더 생성
        
        Returns:
            인증 헤더 딕셔너리
        """
        if self.type == "basic":
            import base64
            credentials = f"{self.username}:{self.password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        
        elif self.type == "jwt" or self.type == "token":
            return {"Authorization": f"Bearer {self.token}"}
        
        elif self.type == "cert":
            # 향후 구현: 클라이언트 인증서
            return {}
        
        elif self.type == "sso":
            # 향후 구현: SSO 토큰
            return {}
        
        else:
            return {}


@dataclass
class Instance:
    """인스턴스 정의"""
    id: str
    label: str
    baseUrl: str
    role: str  # kiosk, admin
    auth: InstanceAuth
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        data = asdict(self)
        data['auth'] = asdict(self.auth)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Instance':
        """딕셔너리에서 생성"""
        auth_data = data.get('auth', {})
        auth = InstanceAuth(**auth_data)
        
        return cls(
            id=data['id'],
            label=data['label'],
            baseUrl=data['baseUrl'],
            role=data['role'],
            auth=auth
        )


class RegistryManager:
    """인스턴스 레지스트리 관리자"""
    
    def __init__(
        self,
        remote_url: Optional[str] = None,
        local_path: Optional[Path] = None
    ):
        """
        Args:
            remote_url: 중앙 레지스트리 URL (http:// 또는 file://)
            local_path: 로컬 오버라이드 파일 경로
        """
        self.remote_url = remote_url
        self.local_path = local_path or Path("instances.local.json")
        
        self._instances: Dict[str, Instance] = {}
        self._version: int = 1
    
    def load(self) -> bool:
        """
        레지스트리 로드 (remote → local 순서, local 우선)
        
        Returns:
            성공 여부
        """
        instances = {}
        
        # 1. 중앙 레지스트리 로드
        if self.remote_url:
            remote_instances = self._load_remote()
            if remote_instances:
                instances.update(remote_instances)
                logger.info(f"중앙 레지스트리 로드: {len(remote_instances)}개 인스턴스")
        
        # 2. 로컬 오버라이드 로드 (우선순위 높음)
        if self.local_path and self.local_path.exists():
            local_instances = self._load_local()
            if local_instances:
                instances.update(local_instances)
                logger.info(f"로컬 레지스트리 로드: {len(local_instances)}개 인스턴스 (오버라이드)")
        
        self._instances = instances
        
        if not instances:
            logger.warning("로드된 인스턴스가 없습니다")
            return False
        
        logger.info(f"총 {len(instances)}개 인스턴스 로드 완료")
        return True
    
    def _load_remote(self) -> Dict[str, Instance]:
        """중앙 레지스트리 로드"""
        if not self.remote_url:
            return {}
        
        try:
            if self.remote_url.startswith('http://') or self.remote_url.startswith('https://'):
                # HTTP 로드
                response = requests.get(self.remote_url, timeout=5)
                response.raise_for_status()
                data = response.json()
            elif self.remote_url.startswith('file://'):
                # 파일 로드
                file_path = Path(self.remote_url[7:])
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                logger.error(f"지원하지 않는 URL 형식: {self.remote_url}")
                return {}
            
            return self._parse_registry(data)
            
        except Exception as e:
            logger.error(f"중앙 레지스트리 로드 실패: {e}")
            return {}
    
    def _load_local(self) -> Dict[str, Instance]:
        """로컬 레지스트리 로드"""
        try:
            with open(self.local_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return self._parse_registry(data)
            
        except Exception as e:
            logger.error(f"로컬 레지스트리 로드 실패: {e}")
            return {}
    
    def _parse_registry(self, data: Dict) -> Dict[str, Instance]:
        """레지스트리 데이터 파싱"""
        instances = {}
        
        try:
            self._version = data.get('version', 1)
            
            for item in data.get('instances', []):
                instance = Instance.from_dict(item)
                instances[instance.id] = instance
            
            return instances
            
        except Exception as e:
            logger.error(f"레지스트리 파싱 오류: {e}")
            return {}
    
    def save(self, target: str = "local") -> bool:
        """
        레지스트리 저장
        
        Args:
            target: "local" 또는 "remote"
            
        Returns:
            성공 여부
        """
        data = {
            "version": self._version,
            "instances": [inst.to_dict() for inst in self._instances.values()]
        }
        
        if target == "local":
            return self._save_local(data)
        elif target == "remote":
            return self._save_remote(data)
        else:
            logger.error(f"잘못된 저장 대상: {target}")
            return False
    
    def _save_local(self, data: Dict) -> bool:
        """로컬에 저장"""
        try:
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.local_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"로컬 레지스트리 저장 완료: {self.local_path}")
            return True
            
        except Exception as e:
            logger.error(f"로컬 레지스트리 저장 실패: {e}")
            return False
    
    def _save_remote(self, data: Dict) -> bool:
        """중앙에 저장"""
        if not self.remote_url:
            logger.error("중앙 레지스트리 URL이 설정되지 않음")
            return False
        
        try:
            if self.remote_url.startswith('http://') or self.remote_url.startswith('https://'):
                # HTTP PUT
                response = requests.put(
                    self.remote_url,
                    json=data,
                    timeout=5
                )
                response.raise_for_status()
            elif self.remote_url.startswith('file://'):
                # 파일 저장
                file_path = Path(self.remote_url[7:])
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                logger.error(f"지원하지 않는 URL 형식: {self.remote_url}")
                return False
            
            logger.info(f"중앙 레지스트리 저장 완료: {self.remote_url}")
            return True
            
        except Exception as e:
            logger.error(f"중앙 레지스트리 저장 실패: {e}")
            return False
    
    def get_instance(self, instance_id: str) -> Optional[Instance]:
        """인스턴스 조회"""
        return self._instances.get(instance_id)
    
    def list_instances(self, role: Optional[str] = None) -> List[Instance]:
        """
        인스턴스 목록 조회
        
        Args:
            role: 필터링할 역할 (kiosk, admin)
            
        Returns:
            인스턴스 리스트
        """
        instances = list(self._instances.values())
        
        if role:
            instances = [inst for inst in instances if inst.role == role]
        
        return instances
    
    def add_instance(self, instance: Instance):
        """인스턴스 추가"""
        self._instances[instance.id] = instance
        logger.info(f"인스턴스 추가: {instance.id} ({instance.label})")
    
    def remove_instance(self, instance_id: str) -> bool:
        """인스턴스 제거"""
        if instance_id in self._instances:
            del self._instances[instance_id]
            logger.info(f"인스턴스 제거: {instance_id}")
            return True
        return False
    
    def update_instance(self, instance: Instance):
        """인스턴스 업데이트"""
        self._instances[instance.id] = instance
        logger.info(f"인스턴스 업데이트: {instance.id}")
    
    def export_json(self) -> str:
        """
        JSON 문자열로 내보내기 (다운로드용)
        
        Returns:
            JSON 문자열
        """
        data = {
            "version": self._version,
            "instances": [inst.to_dict() for inst in self._instances.values()]
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)

