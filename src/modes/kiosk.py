"""
키오스크 모드
파일 감시/처리 엔진 + 로컬 관리 UI
"""

import asyncio
from pathlib import Path
from loguru import logger

from ..config import ConfigManager
from ..processor import QRScanProcessor
from ..file_watcher import FileWatcher
from ..auth import init_auth
from ..audit import init_audit_logger


def run_kiosk_mode(
    config_path: Path,
    port: int = 8000,
    host: str = "0.0.0.0"
):
    """
    키오스크 모드 실행
    
    Args:
        config_path: 설정 파일 경로
        port: 웹 서버 포트
        host: 바인드 호스트
    """
    logger.info("=" * 60)
    logger.info("키오스크 모드 시작")
    logger.info("=" * 60)
    
    # 프로세서 초기화 (내부에서 설정 로드)
    processor = QRScanProcessor(str(config_path))
    config = processor.config
    
    logger.info(f"설정 파일: {config_path}")
    logger.info(f"웹 서버: {host}:{port}")
    logger.info(f"스캐너 출력 폴더: {config.paths.scanner_output}")
    
    # 인증 초기화
    init_auth("basic", {"password": config.system.admin_password})
    logger.info("인증 시스템 초기화 완료")
    
    # 감사 로그 초기화
    audit_log_path = config.paths.data_root / "logs" / "admin_actions.log"
    init_audit_logger(audit_log_path)
    logger.info(f"감사 로그: {audit_log_path}")
    
    # FastAPI 앱과 프로세서 연결
    from ..web_app import app, init_processor
    init_processor(processor)
    logger.info("파일 프로세서 초기화 완료")
    
    # 파일 감시자 시작
    watcher = FileWatcher(config, processor._process_new_file)
    
    async def startup():
        """애플리케이션 시작"""
        watcher.start()
        logger.info("파일 감시 시작")
    
    async def shutdown():
        """애플리케이션 종료"""
        watcher.stop()
        logger.info("파일 감시 중지")
    
    # 이벤트 핸들러 등록
    app.add_event_handler("startup", startup)
    app.add_event_handler("shutdown", shutdown)
    
    # uvicorn 실행
    import uvicorn
    
    logger.info(f"웹 UI: http://{host}:{port}")
    logger.info("키오스크 모드 실행 중...")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

