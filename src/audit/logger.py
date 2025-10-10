"""
감사 로그 시스템
관리자 작업 기록 (비밀번호 변경, 레지스트리 수정, 원격 명령 등)
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger


class AuditLogger:
    """감사 로그 관리자"""
    
    def __init__(self, log_path: Path = None):
        """
        Args:
            log_path: 감사 로그 파일 경로 (기본: data/logs/admin_actions.log)
        """
        if log_path is None:
            log_path = Path("data/logs/admin_actions.log")
        
        self.log_path = log_path
        self.log_file = log_path  # 테스트 호환성
        self.max_bytes = 50 * 1024 * 1024  # 50MB
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 로그 순환 설정 (50MB 단위)
        logger.add(
            str(self.log_path),
            rotation="50 MB",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | AUDIT | {message}",
            level="INFO"
        )
    
    def log(
        self,
        user: str,
        action: str,
        target_instance_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        result: str = "SUCCESS",
        detail: Optional[str] = None
    ):
        """
        감사 로그 기록
        
        Args:
            user: 사용자 (admin)
            action: 작업 (PASSWORD_CHANGE, REGISTRY_UPDATE, REMOTE_COMMAND 등)
            target_instance_id: 대상 인스턴스 ID
            payload: 작업 데이터 (민감 정보는 해시 처리)
            result: 결과 (SUCCESS, FAILURE, ERROR)
            detail: 상세 정보
        """
        # payload 해시 (민감 정보 보호)
        payload_hash = None
        if payload:
            payload_str = json.dumps(payload, sort_keys=True)
            payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
        
        # 감사 로그 엔트리
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user": user,
            "action": action,
            "target_instance_id": target_instance_id,
            "payload_hash": payload_hash,
            "result": result,
            "detail": detail
        }
        
        # JSON 형식으로 기록
        log_message = json.dumps(entry, ensure_ascii=False)
        logger.bind(audit=True).info(log_message)
    
    def read_recent(self, limit: int = 100) -> list:
        """
        최근 감사 로그 조회
        
        Args:
            limit: 반환할 최대 개수
            
        Returns:
            감사 로그 엔트리 리스트
        """
        if not self.log_path.exists():
            return []
        
        entries = []
        
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # 마지막 N개 라인 읽기
                for line in lines[-limit:]:
                    if 'AUDIT' in line:
                        try:
                            # JSON 부분 추출
                            json_start = line.find('{')
                            if json_start >= 0:
                                entry = json.loads(line[json_start:])
                                entries.append(entry)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"감사 로그 읽기 오류: {e}")
        
        return entries


# 전역 인스턴스
audit_logger: Optional[AuditLogger] = None


def init_audit_logger(log_path: Path):
    """감사 로거 초기화"""
    global audit_logger
    audit_logger = AuditLogger(log_path)
    logger.info(f"감사 로거 초기화: {log_path}")


def audit_log(
    user: str,
    action: str,
    target_instance_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    result: str = "SUCCESS",
    detail: Optional[str] = None
):
    """
    감사 로그 기록 (편의 함수)
    """
    if audit_logger:
        audit_logger.log(user, action, target_instance_id, payload, result, detail)
    else:
        logger.warning("감사 로거가 초기화되지 않음")

