"""
인증 관련 모듈
AuthProvider 인터페이스 + 구현체 (BasicAuth, JWT, SSO 등)
"""

from .provider import AuthProvider, AuthResult, AuthProviderFactory
from .basic_auth import BasicAuthProvider, BasicAuthManager
from .rate_limit import RateLimiter
from fastapi import Request, HTTPException, status, Depends
from loguru import logger

# 전역 인증 Provider (모드 초기화 시 설정)
auth_provider: AuthProvider = None
auth_manager = None  # 하위 호환성


async def get_current_user(request: Request) -> AuthResult:
    """
    FastAPI Dependency: 현재 인증된 사용자 조회
    
    인증 성공 시 Request.state.user에 AuthResult 저장
    
    Returns:
        AuthResult: 인증 정보
        
    Raises:
        HTTPException: 인증 실패 시 401
    """
    if not auth_provider:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="인증 시스템이 초기화되지 않았습니다"
        )
    
    # 인증 검증
    auth_result = await auth_provider.verify(request)
    
    if not auth_result or not auth_result.authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Request Context에 사용자 정보 저장 (RBAC 확장 대비)
    request.state.user = auth_result
    
    logger.debug(f"인증 성공: {auth_result.username} ({auth_result.ip}) - roles: {auth_result.roles}")
    
    return auth_result


def require_role(role: str):
    """
    역할 기반 권한 검증 Dependency (향후 RBAC 확장)
    
    사용 예:
        @app.get("/admin/settings", dependencies=[Depends(require_role("admin"))])
    """
    async def _check_role(request: Request):
        auth_result = await get_current_user(request)
        
        if not auth_provider.has_role(auth_result, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"'{role}' 권한이 필요합니다"
            )
        return auth_result
    
    return _check_role


def init_auth(provider_type: str = "basic", config: dict = None):
    """
    인증 시스템 초기화
    
    Args:
        provider_type: "basic", "jwt", "sso" 등
        config: Provider 설정
    """
    global auth_provider, auth_manager
    
    if config is None:
        config = {"password": "1212"}
    
    auth_provider = AuthProviderFactory.create(provider_type, config)
    auth_manager = auth_provider  # 하위 호환성
    
    logger.info(f"인증 시스템 초기화: {auth_provider.get_provider_name()}")
    
    return auth_provider


__all__ = [
    'AuthProvider',
    'AuthResult',
    'AuthProviderFactory',
    'BasicAuthProvider',
    'BasicAuthManager',
    'RateLimiter',
    'get_current_user',
    'require_role',
    'auth_provider',
    'auth_manager',
    'init_auth'
]
