"""
설정 관리 모듈
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from cryptography.fernet import Fernet
import base64
from loguru import logger


@dataclass
class SystemConfig:
    """시스템 설정"""
    log_level: str = "INFO"
    worker_count: int = 3
    web_port: int = 8000
    admin_password: str = "1212"


@dataclass
class PathConfig:
    """경로 설정"""
    scanner_output: Path
    data_root: Path
    
    def __post_init__(self):
        self.scanner_output = Path(self.scanner_output)
        self.data_root = Path(self.data_root)
        
        # 하위 디렉토리 경로 설정
        self.pending = self.data_root / "pending"
        self.merged = self.data_root / "merged"
        self.uploaded = self.data_root / "uploaded"
        self.error = self.data_root / "error"
        self.logs = self.data_root / "logs"
    
    def create_directories(self):
        """필요한 디렉토리 생성"""
        for path in [self.pending, self.merged, self.uploaded, self.error, self.logs]:
            path.mkdir(parents=True, exist_ok=True)


@dataclass
class WatcherConfig:
    """폴더 감시 설정"""
    mode: str = "realtime"  # realtime or polling
    polling_interval: int = 30
    stability_wait: int = 3
    stability_checks: int = 3


@dataclass
class QREngineConfig:
    """QR 엔진별 설정"""
    enabled: bool = True
    timeout: int = 30  # 초
    options: dict = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}


@dataclass
class QRConfig:
    """QR 인식 설정"""
    pattern: str = r"^\d{14}$"
    multiple_qr_action: str = "manual"  # error or manual
    
    # 적응형 DPI 설정
    adaptive_dpi: bool = True  # 자동 DPI 조정 활성화
    fixed_dpi: int = 200  # 고정 DPI 사용 시 값
    dpi_candidates: list = None  # 시도할 DPI 목록
    
    # 다중 엔진 설정
    engine_order: list = None  # ["ZBAR", "ZXING", "PYZBAR_PREPROC"]
    save_failed_images: bool = True
    failed_images_path: str = "data/qr_debug"
    
    # 엔진별 상세 설정
    zbar: QREngineConfig = None
    zxing: QREngineConfig = None
    pyzbar_preproc: QREngineConfig = None
    
    def __post_init__(self):
        if self.dpi_candidates is None:
            self.dpi_candidates = [200, 150, 250, 180, 220, 120, 300]
        
        if self.engine_order is None:
            self.engine_order = ["ZBAR", "ZXING", "PYZBAR_PREPROC"]
        
        if self.zbar is None:
            self.zbar = QREngineConfig()
        
        if self.zxing is None:
            self.zxing = QREngineConfig(
                options={
                    "try_harder": True,
                    "formats": ["QR_CODE"]
                }
            )
        
        if self.pyzbar_preproc is None:
            self.pyzbar_preproc = QREngineConfig(
                options={
                    "adaptive_threshold": True,
                    "deskew": True,
                    "sharpen": True,
                    "blur_removal": True
                }
            )


@dataclass
class PDFConfig:
    """PDF 처리 설정"""
    normalize: bool = True
    pdf_a_convert: bool = False
    remove_duplicates: bool = True
    hash_algorithm: str = "sha1"  # md5 or sha1


@dataclass
class BatchConfig:
    """배치 처리 설정"""
    trigger_mode: str = "idle"  # idle or schedule
    idle_minutes: int = 5
    schedule: str = "*/30 * * * *"


@dataclass
class NASConfig:
    """NAS 업로드 설정"""
    path: str = ""
    username: str = ""
    password: str = ""


@dataclass
class HTTPConfig:
    """HTTP 업로드 설정"""
    endpoint: str = ""
    token: str = ""
    timeout: int = 60
    max_file_size: int = 100


@dataclass
class UploadConfig:
    """업로드 설정"""
    type: str = "nas"  # nas, http, or both
    nas: NASConfig = field(default_factory=NASConfig)
    http: HTTPConfig = field(default_factory=HTTPConfig)


@dataclass
class RetryConfig:
    """재시도 정책"""
    max_attempts: int = 5
    initial_delay: int = 60
    backoff_multiplier: int = 2
    max_delay: int = 3600


@dataclass
class RetentionConfig:
    """보관 정책"""
    uploaded_days: int = 60
    error_days: int = 90
    log_days: int = 30


class ConfigManager:
    """설정 관리자"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._encryption_key = self._get_or_create_key()
        self._fernet = Fernet(self._encryption_key)
        
        # 설정 로드
        self.system = SystemConfig()
        self.paths = None
        self.watcher = WatcherConfig()
        self.qr = QRConfig()
        self.pdf = PDFConfig()
        self.batch = BatchConfig()
        self.upload = None
        self.retry = RetryConfig()
        self.retention = RetentionConfig()
        
        self.load()
    
    def _get_or_create_key(self) -> bytes:
        """암호화 키 생성 또는 로드"""
        key_file = Path(".encryption_key")
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            return key
    
    def encrypt(self, value: str) -> str:
        """문자열 암호화"""
        if not value:
            return value
        return self._fernet.encrypt(value.encode()).decode()
    
    def decrypt(self, value: str) -> str:
        """문자열 복호화"""
        if not value:
            return value
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except:
            # 암호화되지 않은 값인 경우 그대로 반환
            return value
    
    def load(self) -> None:
        """설정 파일 로드"""
        if not os.path.exists(self.config_path):
            logger.warning(f"설정 파일을 찾을 수 없습니다: {self.config_path}")
            # 기본 설정 사용
            self.system = SystemConfig()
            self.paths = PathConfig(
                scanner_output="data/scanner_output",
                data_root="data"
            )
            self.watcher = WatcherConfig()
            self.qr = QRConfig()
            self.pdf = PDFConfig()
            self.batch = BatchConfig()
            self.upload = UploadConfig(
                type="nas",
                nas=NASConfig(),
                http=HTTPConfig()
            )
            self.retry = RetryConfig()
            self.retention = RetentionConfig()
            return
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 각 섹션 파싱
        if 'system' in config:
            self.system = SystemConfig(**config['system'])
        
        if 'paths' in config:
            self.paths = PathConfig(**config['paths'])
        
        if 'watcher' in config:
            self.watcher = WatcherConfig(**config['watcher'])
        
        if 'qr' in config:
            qr_cfg = config['qr'].copy()
            
            # 엔진 설정을 dataclass로 변환
            if 'zbar' in qr_cfg and isinstance(qr_cfg['zbar'], dict):
                qr_cfg['zbar'] = QREngineConfig(**qr_cfg['zbar'])
            
            if 'zxing' in qr_cfg and isinstance(qr_cfg['zxing'], dict):
                qr_cfg['zxing'] = QREngineConfig(**qr_cfg['zxing'])
            
            if 'pyzbar_preproc' in qr_cfg and isinstance(qr_cfg['pyzbar_preproc'], dict):
                qr_cfg['pyzbar_preproc'] = QREngineConfig(**qr_cfg['pyzbar_preproc'])
            
            self.qr = QRConfig(**qr_cfg)
        
        if 'pdf' in config:
            self.pdf = PDFConfig(**config['pdf'])
        
        if 'batch' in config:
            self.batch = BatchConfig(**config['batch'])
        
        if 'upload' in config:
            upload_config = config['upload']
            nas_config = NASConfig(**upload_config.get('nas', {}))
            http_config = HTTPConfig(**upload_config.get('http', {}))
            
            # 민감한 정보 복호화
            nas_config.password = self.decrypt(nas_config.password)
            http_config.token = self.decrypt(http_config.token)
            
            self.upload = UploadConfig(
                type=upload_config.get('type', 'nas'),
                nas=nas_config,
                http=http_config
            )
        
        if 'retry' in config:
            self.retry = RetryConfig(**config['retry'])
        
        if 'retention' in config:
            self.retention = RetentionConfig(**config['retention'])
        
        # 로거 설정
        logger.remove()
        logger.add("sys.stderr", level=self.system.log_level)
        if self.paths:
            log_file = self.paths.logs / "qr_system_{time}.log"
            logger.add(
                log_file,
                rotation="1 day",
                retention=f"{self.retention.log_days} days",
                level=self.system.log_level
            )
    
    def save(self) -> None:
        """설정 파일 저장"""
        config = {
            'system': {
                'log_level': self.system.log_level,
                'worker_count': self.system.worker_count,
                'web_port': self.system.web_port,
                'admin_password': self.system.admin_password
            },
            'paths': {
                'scanner_output': str(self.paths.scanner_output),
                'data_root': str(self.paths.data_root)
            },
            'watcher': {
                'mode': self.watcher.mode,
                'polling_interval': self.watcher.polling_interval,
                'stability_wait': self.watcher.stability_wait,
                'stability_checks': self.watcher.stability_checks
            },
            'qr': {
                'pattern': self.qr.pattern,
                'multiple_qr_action': self.qr.multiple_qr_action
            },
            'pdf': {
                'normalize': self.pdf.normalize,
                'pdf_a_convert': self.pdf.pdf_a_convert,
                'remove_duplicates': self.pdf.remove_duplicates,
                'hash_algorithm': self.pdf.hash_algorithm
            },
            'batch': {
                'trigger_mode': self.batch.trigger_mode,
                'idle_minutes': self.batch.idle_minutes,
                'schedule': self.batch.schedule
            },
            'upload': {
                'type': self.upload.type,
                'nas': {
                    'path': self.upload.nas.path,
                    'username': self.upload.nas.username,
                    'password': self.encrypt(self.upload.nas.password)
                },
                'http': {
                    'endpoint': self.upload.http.endpoint,
                    'token': self.encrypt(self.upload.http.token),
                    'timeout': self.upload.http.timeout,
                    'max_file_size': self.upload.http.max_file_size
                }
            },
            'retry': {
                'max_attempts': self.retry.max_attempts,
                'initial_delay': self.retry.initial_delay,
                'backoff_multiplier': self.retry.backoff_multiplier,
                'max_delay': self.retry.max_delay
            },
            'retention': {
                'uploaded_days': self.retention.uploaded_days,
                'error_days': self.retention.error_days,
                'log_days': self.retention.log_days
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"설정이 저장되었습니다: {self.config_path}")


# 전역 설정 인스턴스
config = ConfigManager()
