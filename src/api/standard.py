"""
표준 API 엔드포인트
모든 인스턴스(kiosk/admin) 공통
"""

import time
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ..auth import get_current_user
from ..audit import audit_log

# 라우터 생성
router = APIRouter(prefix="/api", tags=["standard"])

# 전역 변수 (processor에서 설정)
_processor = None
_start_time = time.time()
_version = "2.0.0"  # 버전 정보


def init_standard_api(processor):
    """표준 API 초기화"""
    global _processor
    _processor = processor
    logger.info("표준 API 초기화 완료")


class CommandRequest(BaseModel):
    """명령 요청"""
    type: str  # RUN_BATCH, PAUSE, RESUME, RESCAN_ERROR, UPDATE_CONFIG, RESTART_SERVICE
    payload: Optional[Dict[str, Any]] = None


@router.get("/status")
async def get_status(username: str = Depends(get_current_user)) -> Dict[str, Any]:
    """
    인스턴스 상태 조회
    
    Returns:
        {
            "uptimeSec": int,
            "queue": {
                "new": 0,
                "pendingMerge": 0,
                "pendingUpload": 0,
                "uploaded": 0,
                "error": 0,
                "total": 0
            },
            "diskFreeMB": int,
            "lastBatchAt": str,
            "version": str
        }
    """
    if not _processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="프로세서가 초기화되지 않았습니다"
        )
    
    # 업타임 계산
    uptime_sec = int(time.time() - _start_time)
    
    # 큐 상태 (파일 시스템 기반)
    config = _processor.config
    
    def count_pdfs(path: Path) -> int:
        """폴더의 PDF 개수"""
        if not path.exists():
            return 0
        return len(list(path.rglob("*.pdf")))
    
    queue = {
        "new": count_pdfs(config.paths.scanner_output),
        "pendingMerge": count_pdfs(config.paths.pending),
        "pendingUpload": count_pdfs(config.paths.merged),
        "uploaded": count_pdfs(config.paths.uploaded),
        "error": count_pdfs(config.paths.error),
    }
    queue["total"] = sum(queue.values())
    
    # 디스크 여유 공간 (MB)
    try:
        disk_usage = psutil.disk_usage(str(config.paths.data_root))
        disk_free_mb = disk_usage.free // (1024 * 1024)
    except Exception:
        disk_free_mb = 0
    
    # 마지막 배치 시간
    last_batch_at = None
    if hasattr(_processor, 'last_batch_time') and _processor.last_batch_time:
        last_batch_at = _processor.last_batch_time.isoformat()
    
    return {
        "uptimeSec": uptime_sec,
        "queue": queue,
        "diskFreeMB": disk_free_mb,
        "lastBatchAt": last_batch_at,
        "version": _version
    }


@router.post("/command")
async def execute_command(
    request: CommandRequest,
    username: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    원격 명령 실행
    
    지원 명령:
    - RUN_BATCH: 배치 즉시 실행
    - PAUSE: 배치 처리 일시정지
    - RESUME: 배치 처리 재개
    - RESCAN_ERROR: 에러 폴더 재스캔
    - UPDATE_CONFIG: 설정 리로드
    - RESTART_SERVICE: 서비스 재시작 (미구현)
    """
    if not _processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="프로세서가 초기화되지 않았습니다"
        )
    
    command_type = request.type
    payload = request.payload or {}
    
    logger.info(f"원격 명령 수신: {command_type}")
    
    # 감사 로그 기록
    audit_log(
        user=username,
        action=f"REMOTE_COMMAND_{command_type}",
        payload=payload
    )
    
    try:
        if command_type == "RUN_BATCH":
            # 배치 즉시 실행
            await _processor.run_batch()
            return {
                "success": True,
                "message": "배치 처리가 시작되었습니다"
            }
        
        elif command_type == "PAUSE":
            # 배치 일시정지
            _processor.paused = True
            logger.info("배치 처리 일시정지")
            return {
                "success": True,
                "message": "배치 처리가 일시정지되었습니다"
            }
        
        elif command_type == "RESUME":
            # 배치 재개
            _processor.paused = False
            logger.info("배치 처리 재개")
            return {
                "success": True,
                "message": "배치 처리가 재개되었습니다"
            }
        
        elif command_type == "RESCAN_ERROR":
            # 에러 폴더 재스캔
            error_path = _processor.config.paths.error
            error_files = list(error_path.glob("*.pdf"))
            
            logger.info(f"에러 폴더 재스캔: {len(error_files)}개 파일")
            
            return {
                "success": True,
                "message": f"에러 폴더 재스캔: {len(error_files)}개 파일 발견",
                "count": len(error_files)
            }
        
        elif command_type == "UPDATE_CONFIG":
            # 설정 리로드
            _processor.config_manager.load()
            logger.info("설정 리로드 완료")
            
            return {
                "success": True,
                "message": "설정이 리로드되었습니다"
            }
        
        elif command_type == "RESTART_SERVICE":
            # 서비스 재시작 (미구현)
            return {
                "success": False,
                "message": "서비스 재시작은 아직 구현되지 않았습니다"
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"지원하지 않는 명령: {command_type}"
            )
    
    except Exception as e:
        logger.error(f"명령 실행 오류: {e}")
        
        # 감사 로그 (실패)
        audit_log(
            user=username,
            action=f"REMOTE_COMMAND_{command_type}",
            payload=payload,
            result="ERROR",
            detail=str(e)
        )
        
        return {
            "success": False,
            "message": f"명령 실행 실패: {str(e)}"
        }


@router.get("/recent")
async def get_recent(
    limit: int = 50,
    username: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    최근 처리 내역 조회
    
    Args:
        limit: 최대 개수
    
    Returns:
        {
            "items": [
                {
                    "timestamp": str,
                    "transport_no": str,
                    "action": str,
                    "status": str,
                    "pages": int
                }
            ],
            "total": int
        }
    """
    if not _processor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="프로세서가 초기화되지 않았습니다"
        )
    
    # 로그에서 최근 처리 내역 추출
    # 간단한 구현: DB가 있다면 ProcessLog에서 조회
    # 파일 기반: 로그 파일 파싱
    
    items = []
    
    # 예시 데이터 (실제로는 DB 또는 로그 파싱)
    # TODO: 실제 구현 필요
    
    return {
        "items": items,
        "total": len(items)
    }


@router.post("/admin/password")
async def change_password(
    old_password: str,
    new_password: str,
    username: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    관리자 비밀번호 변경
    
    Args:
        old_password: 기존 비밀번호
        new_password: 새 비밀번호
    """
    from ..auth import auth_manager
    
    if not auth_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="인증 관리자가 초기화되지 않았습니다"
        )
    
    # 비밀번호 변경
    success = auth_manager.change_password(old_password, new_password)
    
    if success:
        # 감사 로그
        audit_log(
            user=username,
            action="PASSWORD_CHANGE",
            result="SUCCESS"
        )
        
        logger.info(f"비밀번호 변경 성공: {username}")
        
        # 설정 파일 업데이트 (암호화 저장)
        if _processor:
            _processor.config.system.admin_password = new_password
            _processor.config_manager.save()
        
        return {
            "success": True,
            "message": "비밀번호가 변경되었습니다"
        }
    else:
        # 감사 로그 (실패)
        audit_log(
            user=username,
            action="PASSWORD_CHANGE",
            result="FAILURE",
            detail="기존 비밀번호 불일치"
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="기존 비밀번호가 일치하지 않습니다"
        )

