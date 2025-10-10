"""
앱 모드 모듈
kiosk: 파일 처리 엔진 + 로컬 관리 UI
admin: 중앙 관리자 대시보드
"""

from .kiosk import run_kiosk_mode
from .admin import run_admin_mode

__all__ = ['run_kiosk_mode', 'run_admin_mode']

