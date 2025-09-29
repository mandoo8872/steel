#!/usr/bin/env python3
"""
QR 스캔 관리 시스템 - 메인 실행 파일
"""
import sys
import asyncio
import signal
import platform
from pathlib import Path
import uvicorn
from loguru import logger

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from src.web_app import app
from src.config import ConfigManager


class QRScanService:
    """QR 스캔 서비스"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.server = None
        self._shutdown = False
        
    async def start(self):
        """서비스 시작"""
        logger.info("QR 스캔 관리 시스템 시작")
        
        # 디렉토리 생성
        self.config.paths.create_directories()
        
        # 웹 서버 설정
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=self.config.system.web_port,
            log_level=self.config.system.log_level.lower()
        )
        
        self.server = uvicorn.Server(config)
        
        # 시그널 핸들러 설정
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._signal_handler)
        
        # 서버 시작
        await self.server.serve()
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        if not self._shutdown:
            self._shutdown = True
            logger.info(f"종료 시그널 수신: {signum}")
            if self.server:
                self.server.should_exit = True


def main():
    """메인 함수"""
    service = QRScanService()
    
    try:
        # Windows에서 이벤트 루프 정책 설정
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # 서비스 실행
        asyncio.run(service.start())
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
    except Exception as e:
        logger.error(f"서비스 실행 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
