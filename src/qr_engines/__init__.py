"""
QR 엔진 모듈
"""
from .base import QREngine, QRResult
from .zxing_engine import ZXingEngine

# Windows에서 DLL 의존성 문제로 인해 선택적 import
__all__ = [
    'QREngine', 
    'QRResult',
    'ZXingEngine'
]

# pyzbar 기반 엔진들은 선택적으로 로드
try:
    from .zbar_engine import ZBarEngine
    __all__.append('ZBarEngine')
except (ImportError, FileNotFoundError, OSError) as e:
    ZBarEngine = None
    print(f"[경고] ZBarEngine을 로드할 수 없습니다: {e}")

try:
    from .pyzbar_preproc_engine import PyzbarPreprocEngine
    __all__.append('PyzbarPreprocEngine')
except (ImportError, FileNotFoundError, OSError) as e:
    PyzbarPreprocEngine = None
    print(f"[경고] PyzbarPreprocEngine을 로드할 수 없습니다: {e}")
