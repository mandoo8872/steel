#!/usr/bin/env python3
"""
QR 스캔 관리 시스템 - 메인 실행 파일
다중 인스턴스 원격 관리 지원
"""
import sys
import argparse
from pathlib import Path
from loguru import logger

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.modes import run_kiosk_mode, run_admin_mode


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="QR 스캔 관리 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예:
  # 키오스크 모드 (파일 처리 엔진)
  python main.py --mode kiosk --port 8000
  
  # 관리자 모드 (중앙 관리 대시보드)
  python main.py --mode admin --port 8100 --registry http://intranet/instances.json
  
  # Windows 서비스 등록
  sc create kiosksvc binPath= "C:\\app.exe --mode kiosk --port 8000" start= auto
        """
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['kiosk', 'admin'],
        default='kiosk',
        help='실행 모드 (kiosk: 파일 처리, admin: 중앙 관리자)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='설정 파일 경로 (기본: config.yaml)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        help='웹 서버 포트 (기본: kiosk=8000, admin=8100)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='바인드 호스트 (기본: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--registry',
        type=str,
        help='인스턴스 레지스트리 URL (admin 모드 전용)'
    )
    
    return parser.parse_args()


def main():
    """메인 함수"""
    # CLI 인자 파싱
    args = parse_args()
    
    # 설정 파일 경로
    config_path = Path(args.config)
    
    if not config_path.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        logger.info("config.example.yaml을 복사하여 config.yaml을 생성하세요")
        sys.exit(1)
    
    # 포트 설정 (기본값: kiosk=8000, admin=8100)
    port = args.port
    if port is None:
        port = 8000 if args.mode == 'kiosk' else 8100
    
    try:
        # 모드에 따라 분기
        if args.mode == 'kiosk':
            logger.info("키오스크 모드로 시작")
            run_kiosk_mode(
                config_path=config_path,
                port=port,
                host=args.host
            )
        
        elif args.mode == 'admin':
            logger.info("관리자 모드로 시작")
            run_admin_mode(
                config_path=config_path,
                port=port,
                host=args.host,
                registry_url=args.registry
            )
        
        else:
            logger.error(f"알 수 없는 모드: {args.mode}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"실행 오류: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
