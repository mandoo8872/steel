"""
인증 Provider 인터페이스
향후 Firebase, JWT, SSO 등으로 교체 가능한 추상화
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from dataclasses import dataclass
from fastapi import Request
from loguru import logger


@dataclass
class AuthResult:
    """인증 결과"""
    authenticated: bool
    user_id: str
    username: str
    roles: list  # ["admin", "user", "viewer"]
    ip: str
    method: str  # "basic", "jwt", "sso"
    metadata: Dict[str, Any] = None  # 추가 메타데이터
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AuthProvider(ABC):
    """
    인증 Provider 추상 인터페이스
    
    구현체:
    - BasicAuthProvider (현재)
    - JWTAuthProvider (향후)
    - SSOAuthProvider (향후)
    - FirebaseAuthProvider (향후)
    """
    
    @abstractmethod
    async def verify(self, request: Request) -> Optional[AuthResult]:
        """
        요청 인증 검증
        
        Args:
            request: FastAPI Request 객체
            
        Returns:
            AuthResult 또는 None (실패 시)
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Provider 이름 반환"""
        pass
    
    def is_admin(self, auth_result: AuthResult) -> bool:
        """관리자 권한 확인"""
        return "admin" in auth_result.roles
    
    def has_role(self, auth_result: AuthResult, role: str) -> bool:
        """특정 역할 확인"""
        return role in auth_result.roles


class AuthProviderFactory:
    """
    인증 Provider 팩토리
    설정에 따라 적절한 Provider 반환
    """
    
    _providers: Dict[str, AuthProvider] = {}
    
    @classmethod
    def register(cls, name: str, provider: AuthProvider):
        """Provider 등록"""
        cls._providers[name] = provider
        logger.info(f"인증 Provider 등록: {name}")
    
    @classmethod
    def get(cls, name: str) -> Optional[AuthProvider]:
        """Provider 조회"""
        return cls._providers.get(name)
    
    @classmethod
    def create(cls, provider_type: str, config: Dict[str, Any]) -> AuthProvider:
        """
        Provider 생성
        
        Args:
            provider_type: "basic", "jwt", "sso", "firebase"
            config: Provider 설정
            
        Returns:
            AuthProvider 인스턴스
        """
        if provider_type == "basic":
            from .basic_auth import BasicAuthProvider
            return BasicAuthProvider(config)
        
        elif provider_type == "jwt":
            # 향후 구현
            raise NotImplementedError("JWT Provider는 아직 구현되지 않았습니다")
        
        elif provider_type == "sso":
            # 향후 구현
            raise NotImplementedError("SSO Provider는 아직 구현되지 않았습니다")
        
        elif provider_type == "firebase":
            # 향후 구현
            raise NotImplementedError("Firebase Provider는 아직 구현되지 않았습니다")
        
        else:
            raise ValueError(f"지원하지 않는 Provider: {provider_type}")

