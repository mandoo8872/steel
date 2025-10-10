"""
레이트 리밋 구현
로그인 실패 5회 → 15분 잠금
"""

import time
from typing import Dict, Tuple
from datetime import datetime, timedelta
from loguru import logger


class RateLimiter:
    """레이트 리밋 관리자"""
    
    def __init__(self, max_attempts: int = 5, lockout_minutes: int = 15):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_minutes * 60
        
        # {ip: {'attempts': int, 'locked_until': timestamp, 'last_attempt': timestamp}}
        self._failures: Dict[str, Dict] = {}
    
    def is_locked(self, ip: str) -> Tuple[bool, int]:
        """
        IP가 잠겨있는지 확인
        
        Returns:
            (is_locked, seconds_remaining)
        """
        if ip not in self._failures:
            return False, 0
        
        record = self._failures[ip]
        locked_until = record.get('locked_until', 0)
        
        if locked_until > time.time():
            remaining = int(locked_until - time.time())
            return True, remaining
        
        # 잠금 기간 만료 시 초기화
        if locked_until > 0:
            logger.info(f"레이트 리밋 해제: {ip}")
            del self._failures[ip]
        
        return False, 0
    
    def record_failure(self, ip: str) -> Tuple[int, bool]:
        """
        로그인 실패 기록
        
        Returns:
            (attempts_count, is_now_locked)
        """
        now = time.time()
        
        if ip not in self._failures:
            self._failures[ip] = {
                'attempts': 0,
                'locked_until': 0,
                'last_attempt': now
            }
        
        record = self._failures[ip]
        record['attempts'] += 1
        record['last_attempt'] = now
        
        attempts = record['attempts']
        
        if attempts >= self.max_attempts:
            record['locked_until'] = now + self.lockout_seconds
            logger.warning(
                f"레이트 리밋 잠금: {ip} - {attempts}회 실패, "
                f"{self.lockout_seconds // 60}분 잠금"
            )
            return attempts, True
        
        logger.debug(f"로그인 실패 기록: {ip} - {attempts}/{self.max_attempts}회")
        return attempts, False
    
    def record_success(self, ip: str):
        """로그인 성공 시 기록 초기화"""
        if ip in self._failures:
            logger.debug(f"로그인 성공, 실패 기록 초기화: {ip}")
            del self._failures[ip]
    
    def unlock(self, ip: str):
        """관리자가 수동으로 잠금 해제"""
        if ip in self._failures:
            logger.info(f"관리자가 레이트 리밋 해제: {ip}")
            del self._failures[ip]
    
    def get_status(self, ip: str) -> Dict:
        """현재 상태 조회"""
        if ip not in self._failures:
            return {
                'attempts': 0,
                'locked': False,
                'remaining_seconds': 0
            }
        
        is_locked, remaining = self.is_locked(ip)
        record = self._failures[ip]
        
        return {
            'attempts': record['attempts'],
            'locked': is_locked,
            'remaining_seconds': remaining,
            'last_attempt': datetime.fromtimestamp(record['last_attempt']).isoformat()
        }
    
    def cleanup_expired(self):
        """만료된 기록 정리"""
        now = time.time()
        expired = []
        
        for ip, record in self._failures.items():
            locked_until = record.get('locked_until', 0)
            last_attempt = record.get('last_attempt', 0)
            
            # 잠금 해제 후 1시간 이상 경과한 기록 삭제
            if locked_until > 0 and locked_until < now - 3600:
                expired.append(ip)
            # 마지막 시도 후 24시간 이상 경과한 기록 삭제
            elif last_attempt < now - 86400:
                expired.append(ip)
        
        for ip in expired:
            del self._failures[ip]
        
        if expired:
            logger.debug(f"레이트 리밋 기록 정리: {len(expired)}개 IP")

