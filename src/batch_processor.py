"""
배치 처리 모듈 - 병합, 재병합, 업로드 관리
"""
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
from collections import defaultdict
import shutil
import json
from loguru import logger
from sqlalchemy.orm import Session

from .models import ScanDocument, ProcessStatus, ProcessLog, UploadQueue
from .pdf_processor import PDFProcessor
from .uploader import UploadManager
from .config import ConfigManager


class BatchProcessor:
    """배치 프로세서"""
    
    def __init__(self, config: ConfigManager, db_session: Session):
        self.config = config
        self.db_session = db_session
        self.pdf_processor = PDFProcessor(config)
        self.upload_manager = UploadManager(config)
        self._last_activity = datetime.now()
        self._processing = False
        logger.info("배치 프로세서 초기화 완료")
    
    def update_activity(self):
        """활동 시간 업데이트"""
        self._last_activity = datetime.now()
    
    def is_idle(self) -> bool:
        """유휴 상태 확인"""
        if self.config.batch.trigger_mode != 'idle':
            return False
        
        idle_duration = timedelta(minutes=self.config.batch.idle_minutes)
        return datetime.now() - self._last_activity > idle_duration
    
    async def process_batch(self):
        """배치 처리 실행"""
        if self._processing:
            logger.warning("배치 처리가 이미 진행 중입니다.")
            return
        
        self._processing = True
        try:
            logger.info("배치 처리 시작")
            
            # 1. PENDING 상태 문서 처리
            await self._process_pending_documents()
            
            # 2. 병합 처리
            await self._process_merges()
            
            # 3. 업로드 처리
            await self._process_uploads()
            
            # 4. 재시도 처리
            await self._process_retries()
            
            # 5. 정리 작업
            await self._cleanup_old_files()
            
            logger.info("배치 처리 완료")
            
        except Exception as e:
            logger.error(f"배치 처리 오류: {e}")
        finally:
            self._processing = False
    
    async def _process_pending_documents(self):
        """전체 data 폴더 스캔하여 운송번호별 재병합 처리 (파일 시스템 기반)"""
        # 모든 관련 폴더에서 PDF 파일 수집
        all_files = []
        folders_to_scan = [
            ('pending', self.config.paths.pending),
            ('merged', self.config.paths.merged),
            ('uploaded', self.config.paths.uploaded)
        ]
        
        for folder_name, folder_path in folders_to_scan:
            if folder_path.exists():
                pdf_files = list(folder_path.glob("*.pdf"))
                logger.debug(f"{folder_name} 폴더: {len(pdf_files)}개 파일")
                all_files.extend([(folder_name, f) for f in pdf_files])
        
        if not all_files:
            logger.debug("처리할 파일이 없습니다.")
            return
        
        logger.info(f"전체 {len(all_files)}개 파일 발견")
        
        # 운송번호별로 그룹화
        transport_groups = defaultdict(lambda: {'pending': [], 'merged': [], 'uploaded': []})
        
        for folder_name, file_path in all_files:
            try:
                # 파일명에서 운송번호 추출
                filename = file_path.stem
                # 괄호가 있으면 제거
                if '(' in filename:
                    transport_no = filename.split('(')[0]
                else:
                    transport_no = filename
                
                # 14자리 숫자 검증
                if len(transport_no) == 14 and transport_no.isdigit():
                    transport_groups[transport_no][folder_name].append(file_path)
                    logger.debug(f"파일 그룹화: {file_path.name} -> {transport_no} ({folder_name})")
                else:
                    logger.warning(f"유효하지 않은 운송번호 파일: {file_path}")
                    
            except Exception as e:
                logger.error(f"파일명 파싱 오류: {file_path} - {e}")
        
        # 각 운송번호 그룹을 병합 처리
        for transport_no, file_groups in transport_groups.items():
            try:
                # pending 파일이 있거나, 여러 폴더에 분산되어 있으면 재병합
                pending_files = file_groups['pending']
                merged_files = file_groups['merged']
                uploaded_files = file_groups['uploaded']
                
                total_files = len(pending_files) + len(merged_files) + len(uploaded_files)
                
                if pending_files or total_files > 1:
                    logger.info(f"운송번호 {transport_no}: pending({len(pending_files)}), merged({len(merged_files)}), uploaded({len(uploaded_files)}) - 재병합 필요")
                    await self._merge_transport_group_from_all_folders(transport_no, file_groups)
                else:
                    logger.debug(f"운송번호 {transport_no}: 재병합 불필요")
                    
            except Exception as e:
                logger.error(f"운송번호 {transport_no} 병합 오류: {e}")
    
    async def _merge_transport_group_from_all_folders(self, transport_no: str, file_groups: Dict[str, List[Path]]):
        """모든 폴더에서 같은 운송번호 파일 수집하여 재병합"""
        try:
            # 새 파일이 추가되었는지 확인
            has_new_files = len(file_groups['pending']) > 0
            was_uploaded = len(file_groups['uploaded']) > 0
            
            # 최종 목적지 결정
            # uploaded 폴더에 파일이 있었고 새 파일이 추가되면 → merged로 이동 (재업로드 대기)
            # uploaded 폴더에 파일이 있고 새 파일 없으면 → uploaded 유지
            # 그 외 → merged
            if was_uploaded and has_new_files:
                target_dir = self.config.paths.merged
                target_folder_name = 'merged'
                logger.info(f"운송번호 {transport_no}: uploaded에 새 페이지 추가 → merged로 이동하여 재업로드 대기")
            elif file_groups['uploaded']:
                target_dir = self.config.paths.uploaded
                target_folder_name = 'uploaded'
            else:
                target_dir = self.config.paths.merged
                target_folder_name = 'merged'
            
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / f"{transport_no}.pdf"
            
            # 모든 파일 수집
            all_pdf_files = []
            source_files_to_delete = []  # 병합 후 삭제할 원본 파일들
            
            # 모든 폴더에서 파일 수집
            for folder_name in ['pending', 'merged', 'uploaded']:
                for file_path in file_groups[folder_name]:
                    all_pdf_files.append(file_path)
                    
                    # uploaded 폴더에서 merged로 이동하는 경우, uploaded 파일도 삭제 대상
                    if was_uploaded and has_new_files and folder_name == 'uploaded':
                        source_files_to_delete.append(file_path)
                        logger.debug(f"재업로드 대상: {file_path} (uploaded → merged 이동)")
            
            # 파일 순서: uploaded → merged → pending (오래된 것부터 병합)
            all_pdf_files.sort(key=lambda f: (
                0 if 'uploaded' in str(f) else 1 if 'merged' in str(f) else 2,
                f.stat().st_mtime
            ))
            
            if not all_pdf_files:
                logger.warning(f"운송번호 {transport_no}: 병합할 파일 없음")
                return
            
            logger.info(f"운송번호 {transport_no}: {len(all_pdf_files)}개 파일 -> {target_folder_name} 폴더로 병합")
            
            # 병합 수행 (항상 병합, 단일 파일도 복사하여 중복 확인)
            pdf_processor = PDFProcessor(self.config)
            
            # 임시 파일로 병합
            temp_path = target_path.with_suffix('.tmp.pdf')
            result = pdf_processor.merge_pdfs(all_pdf_files, temp_path, remove_duplicates=True)
            
            if result['success']:
                # 임시 파일을 최종 파일로 이동 (덮어쓰기)
                shutil.move(str(temp_path), str(target_path))
                logger.debug(f"병합 파일 생성: {target_path}")
                
                # 원본 파일들 삭제 (최종 target_path는 제외!)
                for file_path in all_pdf_files:
                    # 최종 목적지 파일과 다른 경로의 파일만 삭제
                    if file_path.exists() and file_path.resolve() != target_path.resolve():
                        try:
                            file_path.unlink()
                            logger.debug(f"원본 파일 삭제: {file_path}")
                        except Exception as e:
                            logger.error(f"원본 삭제 실패: {file_path} - {e}")
                
                logger.info(f"병합 완료: {transport_no} -> {target_folder_name} ({result['page_count']}페이지, 중복제거: {result['duplicate_count']})")
            else:
                # 병합 실패 시 임시 파일 정리
                if temp_path.exists():
                    temp_path.unlink()
                raise Exception(f"PDF 병합 실패: {result['error']}")
                    
        except Exception as e:
            logger.error(f"운송번호 {transport_no} 재병합 오류: {e}")
            raise
    
    async def _merge_transport_group(self, transport_no: str, files: List[Path]):
        """운송번호별 파일 그룹 병합 (하위 호환성용)"""
        try:
            # merged 폴더에 직접 저장 (날짜 폴더 제거)
            merged_dir = self.config.paths.merged
            merged_dir.mkdir(parents=True, exist_ok=True)
            merged_path = merged_dir / f"{transport_no}.pdf"
            
            # 기존 병합 파일이 있으면 포함
            pdf_files = []
            if merged_path.exists():
                pdf_files.append(merged_path)
                logger.info(f"기존 병합 파일 발견: {merged_path}")
            
            # 새 파일들 추가
            pdf_files.extend(files)
            
            if len(pdf_files) == 1 and not merged_path.exists():
                # 단일 파일인 경우 그대로 이동
                shutil.move(str(pdf_files[0]), str(merged_path))
                logger.info(f"단일 파일 이동: {pdf_files[0]} -> {merged_path}")
            else:
                # 병합 수행
                from .pdf_processor import PDFProcessor
                pdf_processor = PDFProcessor(self.config)
                
                # 임시 파일로 병합
                temp_path = merged_path.with_suffix('.tmp.pdf')
                result = pdf_processor.merge_pdfs(pdf_files, temp_path, remove_duplicates=True)
                
                if result['success']:
                    # 기존 파일 삭제 후 임시 파일을 최종 파일로 이동
                    if merged_path.exists():
                        merged_path.unlink()
                    shutil.move(str(temp_path), str(merged_path))
                    
                    # 원본 파일들 삭제
                    for file_path in files:
                        if file_path.exists():
                            file_path.unlink()
                            logger.info(f"원본 파일 삭제: {file_path}")
                    
                    logger.info(f"병합 완료: {transport_no} ({result['page_count']}페이지, 중복제거: {result['duplicate_count']})")
                else:
                    # 병합 실패 시 임시 파일 정리
                    if temp_path.exists():
                        temp_path.unlink()
                    raise Exception(f"PDF 병합 실패: {result['error']}")
                    
        except Exception as e:
            logger.error(f"운송번호 {transport_no} 병합 처리 오류: {e}")
            raise
    
    async def _process_merges(self):
        """병합 처리"""
        # 운송번호별로 그룹화
        transport_groups = defaultdict(list)
        
        # PENDING 상태의 문서들을 운송번호별로 그룹화
        pending_docs = self.db_session.query(ScanDocument).filter(
            ScanDocument.status == ProcessStatus.PENDING,
            ScanDocument.transport_no.isnot(None)
        ).all()
        
        for doc in pending_docs:
            transport_groups[doc.transport_no].append(doc)
        
        # 각 그룹 처리
        for transport_no, docs in transport_groups.items():
            try:
                await self._merge_group(transport_no, docs)
            except Exception as e:
                logger.error(f"병합 오류 - 운송번호 {transport_no}: {e}")
    
    async def _merge_group(self, transport_no: str, docs: List[ScanDocument]):
        """운송번호 그룹 병합"""
        # 기존 병합 파일 확인
        merged_dir = self.config.paths.merged
        merged_dir.mkdir(parents=True, exist_ok=True)
        merged_path = merged_dir / f"{transport_no}.pdf"
        
        # 병합할 파일 목록
        pdf_files = []
        
        # 기존 병합 파일이 있으면 포함
        if merged_path.exists():
            pdf_files.append(merged_path)
            logger.info(f"기존 병합 파일 발견: {merged_path}")
        
        # 새 파일들 추가
        for doc in docs:
            file_path = Path(doc.file_path)
            if file_path.exists():
                pdf_files.append(file_path)
        
        result = None
        if len(pdf_files) <= 1 and not merged_path.exists():
            # 단일 파일인 경우 그대로 이동
            if pdf_files:
                shutil.move(str(pdf_files[0]), str(merged_path))
                logger.info(f"단일 파일 이동: {pdf_files[0]} -> {merged_path}")
                result = {'success': True, 'page_count': 1, 'duplicate_count': 0}
        else:
            # 병합 수행
            result = self.pdf_processor.merge_pdfs(
                pdf_files,
                merged_path,
                remove_duplicates=self.config.pdf.remove_duplicates
            )
            
            if not result['success']:
                raise Exception(result['error'])
            
            logger.info(f"병합 완료: {transport_no} - {result['page_count']}페이지")
        
        # 원본 파일 삭제
        for doc in docs:
            try:
                file_path = Path(doc.file_path)
                if file_path.exists() and file_path != merged_path:
                    file_path.unlink()
                    logger.debug(f"원본 삭제: {file_path}")
            except Exception as e:
                logger.error(f"원본 삭제 실패: {doc.file_path} - {e}")
        
        # DB 업데이트
        for doc in docs:
            doc.status = ProcessStatus.MERGED
            doc.is_merged = True
            doc.merged_file_path = str(merged_path)
            doc.merge_group_id = transport_no
            doc.processed_at = datetime.utcnow()
        
        # 로그 추가
        log = ProcessLog(
            document_id=docs[0].id if docs else None,
            action="MERGE",
            status="SUCCESS",
            message=f"병합 완료: {transport_no}",
            details=json.dumps({
                'file_count': len(pdf_files),
                'page_count': result.get('page_count', 0) if result else 0,
                'duplicate_count': result.get('duplicate_count', 0) if result else 0
            })
        )
        self.db_session.add(log)
        
        # 업로드 큐에 추가
        upload_queue = UploadQueue(
            document_id=docs[0].id if docs else None,
            file_path=str(merged_path),
            transport_no=transport_no,
            upload_type=self.config.upload.type
        )
        self.db_session.add(upload_queue)
        
        self.db_session.commit()
    
    async def _process_uploads(self):
        """업로드 처리"""
        # 업로드가 비활성화된 경우 스킵
        if self.config.upload.type == 'none':
            logger.debug("업로드 비활성화됨 - 업로드 처리 스킵")
            return
        
        # 업로드 대기 중인 항목 조회
        queue_items = self.db_session.query(UploadQueue).filter(
            UploadQueue.retry_count < self.config.retry.max_attempts
        ).all()
        
        for item in queue_items:
            try:
                file_path = Path(item.file_path)
                if not file_path.exists():
                    logger.error(f"업로드 파일 없음: {file_path}")
                    self.db_session.delete(item)
                    continue
                
                # 업로드 수행
                result = await self.upload_manager.upload_file(file_path, item.transport_no)
                
                if result['success']:
                    # 성공 시 uploaded 폴더로 이동
                    uploaded_dir = self.config.paths.uploaded
                    uploaded_dir.mkdir(parents=True, exist_ok=True)
                    uploaded_path = uploaded_dir / f"{item.transport_no}.pdf"
                    
                    shutil.move(str(file_path), str(uploaded_path))
                    
                    # DB 업데이트
                    if item.document_id:
                        doc = self.db_session.query(ScanDocument).get(item.document_id)
                        if doc:
                            doc.status = ProcessStatus.UPLOADED
                            doc.uploaded_at = datetime.utcnow()
                    
                    # 큐에서 삭제
                    self.db_session.delete(item)
                    
                    logger.info(f"업로드 성공: {item.transport_no}")
                    
                else:
                    # 실패 시 재시도 설정
                    item.retry_count += 1
                    
                    if item.retry_count >= self.config.retry.max_attempts:
                        # 최대 재시도 초과 - error 폴더로 이동
                        await self._move_to_error(file_path, f"업로드 실패: {result.get('message', '')}")
                        self.db_session.delete(item)
                    else:
                        # 다음 재시도 시간 계산
                        delay = min(
                            self.config.retry.initial_delay * (self.config.retry.backoff_multiplier ** item.retry_count),
                            self.config.retry.max_delay
                        )
                        item.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
                    
                    logger.warning(f"업로드 실패: {item.transport_no} - {result.get('message', '')}")
                
                self.db_session.commit()
                
            except Exception as e:
                logger.error(f"업로드 처리 오류: {item.transport_no} - {e}")
    
    async def _process_retries(self):
        """재시도 처리"""
        # 재시도 시간이 된 항목 조회
        retry_items = self.db_session.query(UploadQueue).filter(
            UploadQueue.next_retry_at <= datetime.utcnow(),
            UploadQueue.retry_count > 0,
            UploadQueue.retry_count < self.config.retry.max_attempts
        ).all()
        
        for item in retry_items:
            logger.info(f"재시도 처리: {item.transport_no} (시도 {item.retry_count + 1}/{self.config.retry.max_attempts})")
            # 업로드 큐 처리로 위임
    
    async def _move_to_error(self, file_path: Path, error_message: str):
        """파일을 에러 폴더로 이동 (날짜 폴더 없이)"""
        try:
            # 에러 폴더 생성
            error_dir = self.config.paths.error
            error_dir.mkdir(parents=True, exist_ok=True)
            
            # 파일 이동
            error_path = error_dir / file_path.name
            shutil.move(str(file_path), str(error_path))
            
            # 데이터베이스 파일 경로 업데이트
            from .models import ScanDocument, ProcessStatus
            doc = self.db_session.query(ScanDocument).filter(
                ScanDocument.file_path == str(file_path)
            ).first()
            
            if doc:
                doc.file_path = str(error_path)
                doc.status = ProcessStatus.ERROR
                doc.error_message = error_message
                doc.processed_at = datetime.now()
                self.db_session.commit()
                logger.info(f"DB 경로 업데이트: {file_path} -> {error_path}")
            
            # 에러 정보 저장
            error_info = {
                'original_path': str(file_path),
                'error_message': error_message,
                'moved_at': datetime.now().isoformat()
            }
            
            info_path = error_path.with_suffix('.error.json')
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(error_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"에러 폴더로 이동: {file_path} -> {error_path}")
            return error_path
            
        except Exception as e:
            logger.error(f"에러 폴더 이동 실패: {file_path} - {e}")
    
    async def _cleanup_old_files(self):
        """오래된 파일 정리"""
        try:
            now = datetime.now()
            
            # uploaded 폴더 정리
            if self.config.retention.uploaded_days > 0:
                cutoff_date = now - timedelta(days=self.config.retention.uploaded_days)
                await self._cleanup_directory(self.config.paths.uploaded, cutoff_date)
            
            # error 폴더 정리
            if self.config.retention.error_days > 0:
                cutoff_date = now - timedelta(days=self.config.retention.error_days)
                await self._cleanup_directory(self.config.paths.error, cutoff_date)
            
        except Exception as e:
            logger.error(f"파일 정리 오류: {e}")
    
    async def _cleanup_directory(self, base_dir: Path, cutoff_date: datetime):
        """디렉토리 정리"""
        for date_dir in base_dir.iterdir():
            if not date_dir.is_dir():
                continue
            
            try:
                # 디렉토리명에서 날짜 파싱
                dir_date = datetime.strptime(date_dir.name, "%Y%m%d")
                
                if dir_date < cutoff_date:
                    # 디렉토리 삭제
                    shutil.rmtree(date_dir)
                    logger.info(f"오래된 디렉토리 삭제: {date_dir}")
            
            except ValueError:
                # 날짜 형식이 아닌 디렉토리는 무시
                pass
