"""
관리자 모드
중앙 관리자 대시보드 (원격 인스턴스 집계/제어)
"""

from pathlib import Path
from loguru import logger

from ..config import ConfigManager
from ..auth import init_auth
from ..audit import init_audit_logger
from ..registry import RegistryManager


def run_admin_mode(
    config_path: Path,
    port: int = 8100,
    host: str = "0.0.0.0",
    registry_url: str = None
):
    """
    관리자 모드 실행
    
    Args:
        config_path: 설정 파일 경로
        port: 웹 서버 포트
        host: 바인드 호스트
        registry_url: 인스턴스 레지스트리 URL
    """
    logger.info("=" * 60)
    logger.info("중앙 관리자 모드 시작")
    logger.info("=" * 60)
    
    # 설정 로드
    from ..config import ConfigManager
    config = ConfigManager(str(config_path))
    
    logger.info(f"설정 파일: {config_path}")
    logger.info(f"웹 서버: {host}:{port}")
    
    # 레지스트리 URL (CLI > config)
    if not registry_url:
        registry_url = config.system.instance_registry_url
    
    logger.info(f"레지스트리: {registry_url}")
    
    # 인증 초기화
    init_auth("basic", {"password": config.system.admin_password})
    logger.info("인증 시스템 초기화 완료")
    
    # 감사 로그 초기화
    audit_log_path = config.paths.data_root / "logs" / "admin_actions.log"
    init_audit_logger(audit_log_path)
    logger.info(f"감사 로그: {audit_log_path}")
    
    # 레지스트리 관리자 초기화
    registry_manager = RegistryManager(
        remote_url=registry_url,
        local_path=Path("instances.local.json")
    )
    
    if registry_manager.load():
        instances = registry_manager.list_instances()
        logger.info(f"레지스트리 로드: {len(instances)}개 인스턴스")
    else:
        logger.warning("레지스트리가 비어있습니다")
    
    # FastAPI 앱 생성 (관리자용)
    from ..api.admin_api import create_admin_app
    
    app = create_admin_app(config, registry_manager)
    
    # uvicorn 실행
    import uvicorn
    
    logger.info(f"관리자 UI: http://{host}:{port}")
    logger.info("관리자 모드 실행 중...")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

