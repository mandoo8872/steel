"""
감사 로그 모듈
"""

from .logger import AuditLogger, audit_log

# 전역 감사 로거
_audit_logger = None


def init_audit_logger(log_path=None):
    """감사 로거 초기화"""
    global _audit_logger
    _audit_logger = AuditLogger(log_path)
    return _audit_logger


def get_audit_logger():
    """감사 로거 조회"""
    return _audit_logger


__all__ = ['AuditLogger', 'audit_log', 'init_audit_logger', 'get_audit_logger']

