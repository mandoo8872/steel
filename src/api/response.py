"""
표준 API 응답 스키마
향후 서명/암호화 확장 대비
"""

from typing import Any, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class SecureResponse(BaseModel):
    """
    보안 확장 가능한 표준 응답
    
    signature 필드: 향후 HMAC/RSA 서명 추가 시 사용
    encrypted: 향후 페이로드 암호화 시 true로 설정
    """
    
    success: bool = Field(..., description="성공 여부")
    data: Any = Field(None, description="응답 데이터")
    message: Optional[str] = Field(None, description="메시지")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # 보안 확장 필드 (현재는 None, 향후 사용)
    signature: Optional[str] = Field(None, description="HMAC/RSA 서명 (향후 구현)")
    encrypted: bool = Field(False, description="페이로드 암호화 여부")
    
    # 메타데이터
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"key": "value"},
                "message": "처리 완료",
                "timestamp": "2025-10-10T12:00:00Z",
                "signature": None,
                "encrypted": False,
                "metadata": {"request_id": "abc123"}
            }
        }


class ErrorResponse(BaseModel):
    """
    에러 응답
    """
    
    code: str = Field(..., description="에러 코드")
    message: str = Field(..., description="에러 메시지")
    detail: Optional[str] = Field(None, description="상세 정보")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # 보안 확장 필드
    signature: Optional[str] = Field(None, description="응답 서명")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "AUTH_FAILED",
                "message": "인증 실패",
                "detail": "비밀번호가 일치하지 않습니다",
                "timestamp": "2025-10-10T12:00:00Z",
                "signature": None
            }
        }


class StatusResponse(SecureResponse):
    """
    /api/status 응답
    """
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "uptimeSec": 3600,
                    "queue": {
                        "new": 10,
                        "pendingMerge": 5,
                        "pendingUpload": 3,
                        "uploaded": 100,
                        "error": 2,
                        "total": 120
                    },
                    "diskFreeMB": 50000,
                    "lastBatchAt": "2025-10-10T11:50:00Z",
                    "version": "2.0.0"
                },
                "timestamp": "2025-10-10T12:00:00Z",
                "signature": None  # 향후 HMAC 추가
            }
        }


class CommandResponse(SecureResponse):
    """
    /api/command 응답
    """
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "command": "RUN_BATCH",
                    "status": "started"
                },
                "message": "배치 처리가 시작되었습니다",
                "timestamp": "2025-10-10T12:00:00Z",
                "signature": None
            }
        }


def create_response(
    success: bool,
    data: Any = None,
    message: str = None,
    sign: bool = False,
    encrypt: bool = False
) -> Dict[str, Any]:
    """
    표준 응답 생성 헬퍼
    
    Args:
        success: 성공 여부
        data: 응답 데이터
        message: 메시지
        sign: 서명 여부 (향후 구현)
        encrypt: 암호화 여부 (향후 구현)
        
    Returns:
        응답 딕셔너리
    """
    response = SecureResponse(
        success=success,
        data=data,
        message=message,
        encrypted=encrypt
    )
    
    # 서명 생성 (향후 구현)
    if sign:
        # TODO: HMAC 또는 RSA 서명 추가
        # response.signature = generate_signature(response.data)
        pass
    
    # 암호화 (향후 구현)
    if encrypt:
        # TODO: 페이로드 암호화
        # response.data = encrypt_data(response.data)
        pass
    
    return response.model_dump()


def create_error(
    code: str,
    message: str,
    detail: str = None,
    sign: bool = False
) -> Dict[str, Any]:
    """
    에러 응답 생성 헬퍼
    
    Args:
        code: 에러 코드
        message: 에러 메시지
        detail: 상세 정보
        sign: 서명 여부
        
    Returns:
        에러 응답 딕셔너리
    """
    response = ErrorResponse(
        code=code,
        message=message,
        detail=detail
    )
    
    if sign:
        # TODO: 서명 추가
        pass
    
    return response.model_dump()

