"""
BasicAuth 구현
단일 비밀번호 기반 인증 (AuthProvider 인터페이스 구현)
"""

import secrets
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from loguru import logger

from .rate_limit import RateLimiter
from .provider import AuthProvider, AuthResult


security = HTTPBasic()


class BasicAuthProvider(AuthProvider):
    """
    BasicAuth Provider 구현
    향후 JWT, SSO 등으로 교체 가능한 인터페이스 준수
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: {"password": "..."} 형태의 설정
        """
        password = config.get("password", "1212")
        self.password_hash = self._hash_password(password)
        self.rate_limiter = RateLimiter(max_attempts=5, lockout_minutes=15)
        logger.info("BasicAuth Provider 초기화")
    
    def get_provider_name(self) -> str:
        """Provider 이름"""
        return "basic"
    
    async def verify(self, request: Request) -> Optional[AuthResult]:
        """
        BasicAuth 검증 (AuthProvider 인터페이스 구현)
        
        Args:
            request: FastAPI Request
            
        Returns:
            AuthResult 또는 None
        """
        # HTTPBasic 인증 정보 추출
        try:
            from fastapi.security import HTTPBasicCredentials
            
            # Authorization 헤더 파싱
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Basic "):
                return None
            
            # Base64 디코딩
            import base64
            try:
                credentials_b64 = auth_header[6:]  # "Basic " 제거
                credentials_bytes = base64.b64decode(credentials_b64)
                credentials_str = credentials_bytes.decode('utf-8')
                username, password = credentials_str.split(':', 1)
            except Exception:
                return None
            
            # IP 추출
            ip = request.client.host
            
            # 레이트 리밋 확인
            is_locked, remaining = self.rate_limiter.is_locked(ip)
            if is_locked:
                logger.warning(f"레이트 리밋 잠금: {ip} - {remaining}초 남음")
                return None
            
            # 비밀번호 검증
            is_valid = self.verify_password(password)
            
            if not is_valid:
                self.rate_limiter.record_failure(ip)
                return None
            
            # 인증 성공
            self.rate_limiter.record_success(ip)
            
            return AuthResult(
                authenticated=True,
                user_id="admin",
                username=username or "admin",
                roles=["admin"],  # 현재는 모두 admin 역할
                ip=ip,
                method="basic",
                metadata={
                    "provider": "basic",
                    "authenticated_at": datetime.utcnow().isoformat()
                }
            )
        
        except Exception as e:
            logger.error(f"BasicAuth 검증 오류: {e}")
            return None
    
    def _hash_password(self, password: str) -> str:
        """비밀번호 해시"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """비밀번호 검증"""
        return secrets.compare_digest(
            self._hash_password(password),
            self.password_hash
        )
    
    def change_password(self, old_password: str, new_password: str) -> bool:
        """비밀번호 변경"""
        if not self.verify_password(old_password):
            logger.warning("비밀번호 변경 실패: 기존 비밀번호 불일치")
            return False
        
        self.password_hash = self._hash_password(new_password)
        logger.info("비밀번호 변경 완료")
        return True


# 하위 호환성을 위한 별칭
class BasicAuthManager(BasicAuthProvider):
    """BasicAuth 관리자"""
    
    def __init__(self, password: str):
        """
        Args:
            password: 관리자 비밀번호 (해시 저장)
        """
        self.password_hash = self._hash_password(password)
        self.rate_limiter = RateLimiter(max_attempts=5, lockout_minutes=15)
    
    def _hash_password(self, password: str) -> str:
        """비밀번호 해시"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """비밀번호 검증"""
        return secrets.compare_digest(
            self._hash_password(password),
            self.password_hash
        )
    
    def change_password(self, old_password: str, new_password: str) -> bool:
        """
        비밀번호 변경
        
        Returns:
            성공 여부
        """
        if not self.verify_password(old_password):
            logger.warning("비밀번호 변경 실패: 기존 비밀번호 불일치")
            return False
        
        self.password_hash = self._hash_password(new_password)
        logger.info("비밀번호 변경 완료")
        return True
    
    def authenticate(self, credentials: HTTPBasicCredentials, ip: str) -> bool:
        """
        인증 수행
        
        Args:
            credentials: HTTP Basic 인증 정보
            ip: 클라이언트 IP
            
        Returns:
            인증 성공 여부
            
        Raises:
            HTTPException: 레이트 리밋 또는 인증 실패
        """
        # 레이트 리밋 확인
        is_locked, remaining = self.rate_limiter.is_locked(ip)
        if is_locked:
            logger.warning(f"레이트 리밋 잠금 상태: {ip} - {remaining}초 남음")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"너무 많은 로그인 시도. {remaining}초 후 다시 시도하세요.",
                headers={"Retry-After": str(remaining)}
            )
        
        # 비밀번호 검증
        is_valid = self.verify_password(credentials.password)
        
        if not is_valid:
            attempts, is_now_locked = self.rate_limiter.record_failure(ip)
            
            if is_now_locked:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"로그인 실패 {attempts}회. 15분간 잠금되었습니다.",
                )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"인증 실패 ({attempts}/5회)",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        # 인증 성공
        self.rate_limiter.record_success(ip)
        logger.debug(f"인증 성공: {ip}")
        return True


# 전역 인스턴스 (config에서 초기화)
auth_manager: Optional[BasicAuthManager] = None


def init_auth(password: str):
    """인증 관리자 초기화"""
    global auth_manager
    auth_manager = BasicAuthManager(password)
    logger.info("인증 관리자 초기화 완료")


def get_current_user(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(security)
) -> str:
    """
    현재 사용자 확인 (의존성 주입용)
    
    Returns:
        사용자명 (항상 'admin')
    """
    if auth_manager is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="인증 시스템이 초기화되지 않았습니다."
        )
    
    # 클라이언트 IP 추출
    ip = request.client.host
    
    # 인증 수행
    auth_manager.authenticate(credentials, ip)
    
    return "admin"

