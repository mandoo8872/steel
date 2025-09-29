"""
메인 처리 엔진 - 파일 감시, QR 처리, 배치 관리를 통합
"""
import asyncio
from pathlib import Path
from datetime import datetime
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from loguru import logger

from .config import ConfigManager
from .models import init_database, get_session, ScanDocument, ProcessStatus, ProcessLog
from .file_watcher import FileWatcher
from .qr_reader import QRReader, QRProcessor
from .batch_processor import BatchProcessor


class QRScanProcessor:
    """QR 스캔 처리 메인 엔진"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = ConfigManager(config_path)
        self.config.paths.create_directories()
        
        # 데이터베이스 초기화
        db_path = self.config.paths.data_root / "qr_system.db"
        self.engine = init_database(db_path)
        self.db_session = get_session(self.engine)
        
        # 컴포넌트 초기화
        self.qr_reader = QRReader(self.config.qr.pattern)
        self.qr_processor = QRProcessor(self.qr_reader)
        self.batch_processor = BatchProcessor(self.config, self.db_session)
        self.file_watcher = FileWatcher(self.config, self._process_new_file)
        
        # 스레드 풀
        self.executor = ThreadPoolExecutor(max_workers=self.config.system.worker_count)
        
        # 실행 상태
        self._running = False
        self._batch_task = None
        
        logger.info("QR 스캔 프로세서 초기화 완료")
    
    async def start(self):
        """프로세서 시작"""
        if self._running:
            logger.warning("프로세서가 이미 실행 중입니다.")
            return
        
        self._running = True
        logger.info("QR 스캔 프로세서 시작")
        
        try:
            # 기존 파일 처리
            existing_files = self.file_watcher.scan_existing_files()
            for file_path in existing_files:
                await self._process_new_file_async(file_path)
            
            # 파일 감시 시작
            self.file_watcher.start()
            
            # 배치 처리 스케줄러 시작
            self._batch_task = asyncio.create_task(self._batch_scheduler())
            
            logger.info("모든 컴포넌트 시작 완료")
            
        except Exception as e:
            logger.error(f"프로세서 시작 오류: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """프로세서 중지"""
        if not self._running:
            return
        
        logger.info("QR 스캔 프로세서 중지 중...")
        self._running = False
        
        # 파일 감시 중지
        self.file_watcher.stop()
        
        # 배치 태스크 중지
        if self._batch_task:
            self._batch_task.cancel()
            try:
                await self._batch_task
            except asyncio.CancelledError:
                pass
        
        # 스레드 풀 종료
        self.executor.shutdown(wait=True)
        
        # 데이터베이스 세션 닫기
        self.db_session.close()
        
        logger.info("QR 스캔 프로세서 중지 완료")
    
    def _process_new_file(self, file_path: Path):
        """새 파일 처리 (동기)"""
        # 비동기 태스크로 위임
        asyncio.create_task(self._process_new_file_async(file_path))
    
    async def _process_new_file_async(self, file_path: Path):
        """새 파일 처리 (비동기)"""
        logger.info(f"새 PDF 처리 시작: {file_path}")
        
        try:
            # 1. DB에 문서 등록
            doc = ScanDocument(
                file_path=str(file_path),
                original_filename=file_path.name,
                file_size=file_path.stat().st_size,
                status=ProcessStatus.PROCESSING
            )
            self.db_session.add(doc)
            self.db_session.commit()
            
            # 2. QR 코드 처리
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.qr_processor.process_document,
                file_path
            )
            
            # 3. 결과에 따른 처리
            doc.qr_count = len(result['valid_qr_codes'])
            doc.qr_values = json.dumps(result['all_qr_codes'])
            
            if result['status'] == 'success':
                # 단일 QR 성공
                doc.transport_no = result['transport_no']
                doc.status = ProcessStatus.PENDING
                
                # pending 폴더로 이동
                await self._move_to_pending(file_path, doc.transport_no)
                
                logger.info(f"QR 인식 성공: {doc.transport_no}")
                
            elif result['status'] == 'multiple':
                # 다중 QR 검출
                if self.config.qr.multiple_qr_action == 'error':
                    # 에러 폴더로 이동
                    doc.status = ProcessStatus.ERROR
                    doc.error_message = result['error_message']
                    await self._move_to_error(file_path, result['error_message'])
                else:
                    # manual 모드 - 관리자 UI에서 선택하도록 대기
                    doc.status = ProcessStatus.ERROR
                    doc.error_message = f"다중 QR 검출 - 수동 선택 필요: {result['valid_qr_codes']}"
                    await self._move_to_error(file_path, doc.error_message)
                
                logger.warning(f"다중 QR 검출: {result['valid_qr_codes']}")
                
            else:
                # QR 인식 실패
                doc.status = ProcessStatus.ERROR
                doc.error_message = result.get('error_message', 'QR 코드를 찾을 수 없습니다.')
                await self._move_to_error(file_path, doc.error_message)
                
                logger.error(f"QR 인식 실패: {doc.error_message}")
            
            # 로그 기록
            log = ProcessLog(
                document_id=doc.id,
                action="QR_DETECT",
                status="SUCCESS" if result['status'] == 'success' else "FAILED",
                message=result.get('error_message', ''),
                details=json.dumps(result)
            )
            self.db_session.add(log)
            
            # DB 업데이트
            doc.processed_at = datetime.utcnow()
            self.db_session.commit()
            
            # 배치 프로세서 활동 업데이트
            self.batch_processor.update_activity()
            
        except Exception as e:
            logger.error(f"파일 처리 오류: {file_path} - {e}")
            
            # DB 업데이트
            if 'doc' in locals():
                doc.status = ProcessStatus.ERROR
                doc.error_message = str(e)
                self.db_session.commit()
            
            # 에러 폴더로 이동
            await self._move_to_error(file_path, str(e))
    
    async def _move_to_pending(self, file_path: Path, transport_no: str):
        """pending 폴더로 이동"""
        try:
            # 날짜 폴더 생성
            date_folder = transport_no[:8]
            dest_dir = self.config.paths.pending / date_folder
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # 대상 경로
            dest_path = dest_dir / f"{transport_no}.pdf"
            
            # 중복 파일명 처리
            if dest_path.exists():
                counter = 1
                while True:
                    dest_path = dest_dir / f"{transport_no}({counter}).pdf"
                    if not dest_path.exists():
                        break
                    counter += 1
            
            # 파일 이동
            shutil.move(str(file_path), str(dest_path))
            logger.debug(f"pending으로 이동: {file_path} -> {dest_path}")
            
        except Exception as e:
            logger.error(f"pending 이동 실패: {file_path} - {e}")
            raise
    
    async def _move_to_error(self, file_path: Path, error_message: str):
        """error 폴더로 이동"""
        try:
            # 날짜 폴더 생성
            date_str = datetime.now().strftime("%Y%m%d")
            error_dir = self.config.paths.error / date_str
            error_dir.mkdir(parents=True, exist_ok=True)
            
            # 파일 이동
            error_path = error_dir / file_path.name
            
            # 중복 파일명 처리
            if error_path.exists():
                counter = 1
                base_name = file_path.stem
                while True:
                    error_path = error_dir / f"{base_name}({counter}){file_path.suffix}"
                    if not error_path.exists():
                        break
                    counter += 1
            
            shutil.move(str(file_path), str(error_path))
            
            # 에러 정보 저장
            error_info = {
                'original_path': str(file_path),
                'error_message': error_message,
                'moved_at': datetime.now().isoformat()
            }
            
            info_path = error_path.with_suffix('.error.json')
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(error_info, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"error로 이동: {file_path} -> {error_path}")
            
        except Exception as e:
            logger.error(f"error 이동 실패: {file_path} - {e}")
            raise
    
    async def _batch_scheduler(self):
        """배치 처리 스케줄러"""
        logger.info(f"배치 스케줄러 시작 - 모드: {self.config.batch.trigger_mode}")
        
        while self._running:
            try:
                if self.config.batch.trigger_mode == 'idle':
                    # 유휴 시간 체크
                    if self.batch_processor.is_idle():
                        logger.info("유휴 시간 도달 - 배치 처리 시작")
                        await self.batch_processor.process_batch()
                    
                    # 1분마다 체크
                    await asyncio.sleep(60)
                    
                else:
                    # schedule 모드 - cron 표현식 파싱 필요
                    # 간단한 구현: N분마다 실행
                    interval_minutes = 30  # 기본값
                    
                    # cron 표현식에서 간격 추출 (간단한 파싱)
                    if '/' in self.config.batch.schedule:
                        try:
                            interval_minutes = int(self.config.batch.schedule.split('/')[1].split()[0])
                        except:
                            pass
                    
                    await asyncio.sleep(interval_minutes * 60)
                    
                    logger.info("스케줄 도달 - 배치 처리 시작")
                    await self.batch_processor.process_batch()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"배치 스케줄러 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
    
    async def force_batch_process(self):
        """강제 배치 처리 실행"""
        logger.info("강제 배치 처리 요청")
        await self.batch_processor.process_batch()
    
    async def reprocess_error_file(self, error_file_path: Path, transport_no: str):
        """에러 파일 재처리"""
        logger.info(f"에러 파일 재처리: {error_file_path} -> {transport_no}")
        
        try:
            # DB에서 기존 문서 조회 또는 새로 생성
            doc = self.db_session.query(ScanDocument).filter(
                ScanDocument.file_path == str(error_file_path)
            ).first()
            
            if not doc:
                doc = ScanDocument(
                    file_path=str(error_file_path),
                    original_filename=error_file_path.name,
                    file_size=error_file_path.stat().st_size
                )
                self.db_session.add(doc)
            
            # 운송번호 설정
            doc.transport_no = transport_no
            doc.manual_transport_no = transport_no
            doc.status = ProcessStatus.PENDING
            doc.error_message = None
            
            # pending으로 이동
            await self._move_to_pending(error_file_path, transport_no)
            
            # 에러 정보 파일 삭제
            error_info_path = error_file_path.with_suffix('.error.json')
            if error_info_path.exists():
                error_info_path.unlink()
            
            self.db_session.commit()
            
            logger.info(f"재처리 완료: {transport_no}")
            
        except Exception as e:
            logger.error(f"재처리 실패: {error_file_path} - {e}")
            raise
