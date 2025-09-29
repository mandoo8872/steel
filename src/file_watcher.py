"""
파일 감시 모듈
"""
import os
import time
import asyncio
from pathlib import Path
from typing import Set, Optional, Callable, Dict
from datetime import datetime, timedelta
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
import threading


class FileStabilityChecker:
    """파일 안정성 검사기"""
    
    def __init__(self, stability_wait: int = 3, stability_checks: int = 3):
        self.stability_wait = stability_wait
        self.stability_checks = stability_checks
        self._file_sizes: Dict[Path, int] = {}
        self._check_counts: Dict[Path, int] = {}
    
    def is_file_stable(self, file_path: Path) -> bool:
        """파일이 안정적인지 확인 (크기 변화 없음)"""
        if not file_path.exists():
            return False
        
        try:
            current_size = file_path.stat().st_size
            
            # 첫 확인
            if file_path not in self._file_sizes:
                self._file_sizes[file_path] = current_size
                self._check_counts[file_path] = 1
                return False
            
            # 크기가 변경된 경우
            if self._file_sizes[file_path] != current_size:
                self._file_sizes[file_path] = current_size
                self._check_counts[file_path] = 1
                return False
            
            # 크기가 동일한 경우 카운트 증가
            self._check_counts[file_path] += 1
            
            # 충분한 횟수만큼 크기가 동일하면 안정적으로 판단
            if self._check_counts[file_path] >= self.stability_checks:
                # 파일 열기 테스트
                try:
                    with open(file_path, 'rb') as f:
                        f.read(1)  # 1바이트만 읽어서 테스트
                    
                    # 정리
                    del self._file_sizes[file_path]
                    del self._check_counts[file_path]
                    return True
                    
                except (IOError, OSError):
                    # 아직 파일이 잠겨있음
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"파일 안정성 검사 오류: {file_path} - {e}")
            return False
    
    def clear_file(self, file_path: Path):
        """파일 정보 제거"""
        self._file_sizes.pop(file_path, None)
        self._check_counts.pop(file_path, None)


class PDFEventHandler(FileSystemEventHandler):
    """PDF 파일 이벤트 핸들러"""
    
    def __init__(self, callback: Callable[[Path], None], stability_checker: FileStabilityChecker):
        self.callback = callback
        self.stability_checker = stability_checker
        self._pending_files: Set[Path] = set()
        self._lock = threading.Lock()
    
    def on_created(self, event: FileCreatedEvent):
        """파일 생성 이벤트"""
        if not event.is_directory and event.src_path.endswith('.pdf'):
            file_path = Path(event.src_path)
            logger.debug(f"새 PDF 감지: {file_path}")
            
            with self._lock:
                self._pending_files.add(file_path)
    
    def on_modified(self, event: FileModifiedEvent):
        """파일 수정 이벤트"""
        if not event.is_directory and event.src_path.endswith('.pdf'):
            file_path = Path(event.src_path)
            
            with self._lock:
                self._pending_files.add(file_path)
    
    def check_pending_files(self):
        """대기 중인 파일 확인"""
        with self._lock:
            files_to_check = list(self._pending_files)
        
        for file_path in files_to_check:
            if self.stability_checker.is_file_stable(file_path):
                logger.info(f"안정적인 PDF 확인: {file_path}")
                
                # 콜백 실행
                try:
                    self.callback(file_path)
                    with self._lock:
                        self._pending_files.discard(file_path)
                except Exception as e:
                    logger.error(f"PDF 처리 콜백 오류: {file_path} - {e}")


class FileWatcher:
    """파일 감시기"""
    
    def __init__(self, config, process_callback: Callable[[Path], None]):
        self.config = config
        self.process_callback = process_callback
        self.watch_path = config.paths.scanner_output
        self.stability_checker = FileStabilityChecker(
            config.watcher.stability_wait,
            config.watcher.stability_checks
        )
        self._observer = None
        self._polling_thread = None
        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=1)
    
    def start(self):
        """감시 시작"""
        if self.config.watcher.mode == "realtime":
            self._start_realtime_watcher()
        else:
            self._start_polling_watcher()
        
        logger.info(f"파일 감시 시작 - 모드: {self.config.watcher.mode}, 경로: {self.watch_path}")
    
    def stop(self):
        """감시 중지"""
        self._stop_event.set()
        
        if self._observer:
            self._observer.stop()
            self._observer.join()
        
        if self._polling_thread:
            self._polling_thread.join()
        
        self._executor.shutdown(wait=True)
        
        logger.info("파일 감시 중지")
    
    def _start_realtime_watcher(self):
        """실시간 감시 시작"""
        handler = PDFEventHandler(self._process_file, self.stability_checker)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.watch_path), recursive=True)
        self._observer.start()
        
        # 안정성 검사 스레드
        def stability_check_loop():
            while not self._stop_event.is_set():
                handler.check_pending_files()
                time.sleep(self.config.watcher.stability_wait)
        
        self._executor.submit(stability_check_loop)
    
    def _start_polling_watcher(self):
        """폴링 감시 시작"""
        def polling_loop():
            processed_files = set()
            
            while not self._stop_event.is_set():
                try:
                    # PDF 파일 검색
                    for pdf_file in Path(self.watch_path).rglob("*.pdf"):
                        if pdf_file in processed_files:
                            continue
                        
                        if self.stability_checker.is_file_stable(pdf_file):
                            logger.info(f"새 PDF 발견 (폴링): {pdf_file}")
                            self._process_file(pdf_file)
                            processed_files.add(pdf_file)
                    
                    # 처리된 파일 중 삭제된 것 정리
                    processed_files = {f for f in processed_files if f.exists()}
                    
                except Exception as e:
                    logger.error(f"폴링 오류: {e}")
                
                # 대기
                self._stop_event.wait(self.config.watcher.polling_interval)
        
        self._polling_thread = threading.Thread(target=polling_loop)
        self._polling_thread.start()
    
    def _process_file(self, file_path: Path):
        """파일 처리"""
        try:
            # 콜백 실행
            self.process_callback(file_path)
        except Exception as e:
            logger.error(f"파일 처리 오류: {file_path} - {e}")
    
    def scan_existing_files(self) -> List[Path]:
        """기존 파일 스캔"""
        existing_files = []
        
        try:
            for pdf_file in Path(self.watch_path).rglob("*.pdf"):
                if self.stability_checker.is_file_stable(pdf_file):
                    existing_files.append(pdf_file)
                    logger.info(f"기존 PDF 발견: {pdf_file}")
        
        except Exception as e:
            logger.error(f"기존 파일 스캔 오류: {e}")
        
        return existing_files
