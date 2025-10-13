"""
관리자 웹 UI - FastAPI 애플리케이션
"""
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pathlib import Path
from typing import Optional, Dict, List
import secrets
from datetime import datetime, timedelta
import json
from loguru import logger
import yaml

from .config import ConfigManager
from .models import ScanDocument, ProcessLog, UploadQueue, ProcessStatus
from .processor import QRScanProcessor

app = FastAPI(title="QR 스캔 관리 시스템")
security = HTTPBasic()

# 전역 프로세서 인스턴스
processor: Optional[QRScanProcessor] = None


def init_processor(proc: QRScanProcessor):
    """프로세서 초기화 (모드별 호출)"""
    global processor
    processor = proc
    logger.info("프로세서 전역 설정 완료")


# 템플릿 설정
templates_dir = Path(__file__).parent.parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# 정적 파일 설정
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """인증 확인"""
    if processor and secrets.compare_digest(credentials.password, processor.config.system.admin_password):
        return credentials.username
    raise HTTPException(status_code=401, detail="인증 실패")


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 이벤트"""
    global processor
    processor = QRScanProcessor()
    await processor.start()
    logger.info("웹 애플리케이션 시작")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 이벤트"""
    if processor:
        await processor.stop()
    logger.info("웹 애플리케이션 종료")


@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request):
    """로그아웃 - 자바스크립트로 인증 초기화"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>로그아웃 중...</title>
        <style>
            body {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: #f5f5f5;
            }
            .logout-box {
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .spinner {
                border: 3px solid #f3f3f3;
                border-top: 3px solid #3498db;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="logout-box">
            <div class="spinner"></div>
            <h3>로그아웃 중...</h3>
            <p>잠시만 기다려주세요</p>
        </div>
        <script>
            // 잘못된 인증 정보로 요청하여 브라우저의 인증 캐시 초기화
            setTimeout(function() {
                fetch('/', {
                    headers: {
                        'Authorization': 'Basic ' + btoa('logout:logout')
                    }
                }).then(function() {
                    // 로그인 페이지로 리다이렉트
                    window.location.href = '/';
                }).catch(function() {
                    // 실패해도 로그인 페이지로
                    window.location.href = '/';
                });
            }, 500);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, username: str = Depends(verify_credentials)):
    """메인 대시보드 - 파일 시스템 기반"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        from pathlib import Path
        
        # 각 폴더의 PDF 파일 수 계산
        def count_pdfs(path: Path) -> int:
            if not path.exists():
                return 0
            return len(list(path.rglob("*.pdf")))
        
        # 신규 문서 (scanner_output 폴더)
        scanner_count = count_pdfs(processor.config.paths.scanner_output)
        
        # 병합 대기 (pending 폴더)
        pending_count = count_pdfs(processor.config.paths.pending)
        
        # 업로드 대기 (merged 폴더)
        merged_count = count_pdfs(processor.config.paths.merged)
        
        # 업로드 완료 (uploaded 폴더)
        uploaded_count = count_pdfs(processor.config.paths.uploaded)
        
        # 오류 (error 폴더)
        error_count = count_pdfs(processor.config.paths.error)
        
        # 전체 문서 수
        total_count = scanner_count + pending_count + merged_count + uploaded_count + error_count
        
        # 통계 수집 (파일 기반)
        stats = {
            'total': total_count,
            'scanner': scanner_count,      # 신규 문서
            'pending': pending_count,      # 병합 대기
            'merged': merged_count,        # 업로드 대기
            'uploaded': uploaded_count,    # 업로드 완료
            'error': error_count,          # 오류
            'retry_queue': 0  # 파일 기반에서는 미사용
        }
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "stats": stats,
            "config": processor.config
        })
    except Exception as e:
        logger.error(f"대시보드 로딩 오류: {e}")
        # 기본 통계로 페이지 렌더링
        stats = {'total': 0, 'scanner': 0, 'pending': 0, 'merged': 0, 'uploaded': 0, 'error': 0, 'retry_queue': 0}
        return templates.TemplateResponse("index.html", {
            "request": request,
            "stats": stats,
            "config": processor.config if processor else None,
            "error_message": f"파일 시스템 오류: {str(e)}"
        })


@app.get("/documents", response_class=HTMLResponse)
async def documents(request: Request, 
                   folder: Optional[str] = None,
                   limit: int = 100,
                   username: str = Depends(verify_credentials)):
    """문서 목록"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    # 강제로 로그 출력
    logger.error("=== 문서 목록 함수 호출됨 ===")
    
    try:
        # 먼저 전체 문서 수 확인
        total_count = processor.db_session.query(ScanDocument).count()
        logger.error(f"전체 문서 수: {total_count}")
        
        query = processor.db_session.query(ScanDocument)
        
        # 파일 기반으로 변경되어 DB 쿼리 불필요
        docs = []
        
        docs = query.order_by(ScanDocument.created_at.desc()).limit(limit).all()
        logger.error(f"HTML 문서 조회 결과: {len(docs)}개 문서 발견")
        
        # 디버깅: 첫 번째 문서 정보 출력
        if docs:
            first_doc = docs[0]
            logger.error(f"첫 번째 문서: id={first_doc.id}, status={first_doc.status}, filename={first_doc.original_filename}")
        
        return templates.TemplateResponse("documents.html", {
            "request": request,
            "documents": [],  # JavaScript에서 로드
            "folder_filter": folder
        })
    except Exception as e:
        logger.error(f"문서 목록 조회 오류: {e}")
        # 빈 목록으로 페이지 렌더링
        return templates.TemplateResponse("documents.html", {
            "request": request,
            "documents": [],
            "status_filter": None,
            "error_message": f"데이터베이스 오류: {str(e)}"
        })


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, username: str = Depends(verify_credentials)):
    """설정 페이지"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "config": processor.config
        })
    except Exception as e:
        logger.error(f"설정 페이지 로딩 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"설정 페이지 로딩 실패: {str(e)}")


@app.post("/settings")
async def update_settings(request: Request, username: str = Depends(verify_credentials)):
    """설정 업데이트"""
    form_data = await request.form()
    
    try:
        # 설정 업데이트
        config = processor.config
        
        # 시스템 설정
        config.system.log_level = form_data.get("log_level", config.system.log_level)
        config.system.worker_count = int(form_data.get("worker_count", config.system.worker_count))
        
        # 경로 설정
        config.paths.scanner_output = Path(form_data.get("scanner_output", config.paths.scanner_output))
        config.paths.data_root = Path(form_data.get("data_root", config.paths.data_root))
        
        # 감시 설정
        config.watcher.mode = form_data.get("watcher_mode", config.watcher.mode)
        config.watcher.polling_interval = int(form_data.get("polling_interval", config.watcher.polling_interval))
        
        # QR 설정
        config.qr.pattern = form_data.get("qr_pattern", config.qr.pattern)
        config.qr.multiple_qr_action = form_data.get("multiple_qr_action", config.qr.multiple_qr_action)
        
        # QR 엔진 순서
        engine_order_json = form_data.get("qr_engine_order", None)
        if engine_order_json:
            try:
                config.qr.engine_order = json.loads(engine_order_json)
            except json.JSONDecodeError:
                pass
        
        # QR 엔진 설정
        # ZBar
        config.qr.zbar.enabled = form_data.get("zbar_enabled") == "on"
        config.qr.zbar.timeout = int(form_data.get("zbar_timeout", config.qr.zbar.timeout))
        
        # ZXing
        config.qr.zxing.enabled = form_data.get("zxing_enabled") == "on"
        config.qr.zxing.timeout = int(form_data.get("zxing_timeout", config.qr.zxing.timeout))
        config.qr.zxing.options["try_harder"] = form_data.get("zxing_try_harder") == "on"
        
        # Pyzbar + OpenCV
        config.qr.pyzbar_preproc.enabled = form_data.get("pyzbar_preproc_enabled") == "on"
        config.qr.pyzbar_preproc.timeout = int(form_data.get("pyzbar_preproc_timeout", config.qr.pyzbar_preproc.timeout))
        config.qr.pyzbar_preproc.options["adaptive_threshold"] = form_data.get("pp_adaptive_threshold") == "on"
        config.qr.pyzbar_preproc.options["deskew"] = form_data.get("pp_deskew") == "on"
        config.qr.pyzbar_preproc.options["sharpen"] = form_data.get("pp_sharpen") == "on"
        config.qr.pyzbar_preproc.options["blur_removal"] = form_data.get("pp_blur_removal") == "on"
        
        # 실패 이미지 저장
        config.qr.save_failed_images = form_data.get("save_failed_images") == "on"
        config.qr.failed_images_path = form_data.get("failed_images_path", config.qr.failed_images_path)
        
        # PDF 설정
        config.pdf.normalize = form_data.get("pdf_normalize") == "on"
        config.pdf.remove_duplicates = form_data.get("remove_duplicates") == "on"
        
        # 배치 설정
        config.batch.trigger_mode = form_data.get("batch_trigger_mode", config.batch.trigger_mode)
        config.batch.idle_minutes = int(form_data.get("idle_minutes", config.batch.idle_minutes))
        
        # 업로드 설정
        config.upload.type = form_data.get("upload_type", config.upload.type)
        config.upload.nas.path = form_data.get("nas_path", config.upload.nas.path)
        config.upload.http.endpoint = form_data.get("http_endpoint", config.upload.http.endpoint)
        
        # 설정 저장
        config.save()
        
        return JSONResponse({"success": True, "message": "설정이 저장되었습니다."})
        
    except Exception as e:
        logger.error(f"설정 업데이트 오류: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.get("/errors", response_class=HTMLResponse)
async def errors(request: Request, username: str = Depends(verify_credentials)):
    """에러 문서 목록 (파일 기반)"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        return templates.TemplateResponse("errors.html", {
            "request": request,
            "error_docs": [],  # JavaScript에서 로드
            "error_files": []  # JavaScript에서 로드
        })
    except Exception as e:
        logger.error(f"에러 문서 목록 조회 오류: {e}")
        return templates.TemplateResponse("errors.html", {
            "request": request,
            "error_docs": [],
            "error_files": [],
            "error_message": f"데이터베이스 오류: {str(e)}"
        })


@app.post("/reprocess/{file_path:path}")
async def reprocess_file(file_path: str, 
                        transport_no: str = Form(...),
                        username: str = Depends(verify_credentials)):
    """에러 파일 재처리"""
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        # 운송번호 유효성 검사 (14자리 숫자)
        if not transport_no or len(transport_no) != 14 or not transport_no.isdigit():
            raise HTTPException(status_code=400, detail="유효하지 않은 운송번호입니다. (14자리 숫자 필요)")
        
        # 재처리 실행
        await processor.reprocess_error_file(file_path, transport_no)
        
        return JSONResponse({"success": True, "message": "재처리가 시작되었습니다."})
        
    except Exception as e:
        logger.error(f"재처리 오류: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.post("/batch/process")
async def trigger_batch(username: str = Depends(verify_credentials)):
    """강제 배치 처리"""
    try:
        await processor.force_batch_process()
        return JSONResponse({"success": True, "message": "배치 처리가 시작되었습니다."})
    except Exception as e:
        logger.error(f"배치 처리 오류: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.post("/rescan/files")
async def rescan_scanner_files(username: str = Depends(verify_credentials)):
    """scanner_output 폴더 재스캔"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        count = await processor.rescan_scanner_output()
        return JSONResponse({"success": True, "message": f"{count}개 파일을 재스캔했습니다."})
    except Exception as e:
        logger.error(f"파일 재스캔 오류: {e}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@app.get("/logs", response_class=HTMLResponse)
async def logs(request: Request, 
              limit: int = 200,
              username: str = Depends(verify_credentials)):
    """처리 로그"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        # 1. 데이터베이스 로그 조회
        db_logs = processor.db_session.query(ProcessLog).order_by(
            ProcessLog.created_at.desc()
        ).limit(limit).all()
        
        # 2. 파일 로그 조회
        file_logs = []
        log_dir = processor.config.paths.logs
        
        logger.info(f"로그 디렉토리 확인: {log_dir}, 존재: {log_dir.exists()}")
        
        if log_dir.exists():
            # 최근 로그 파일들 찾기 (최대 3개)
            log_files = sorted(log_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]
            logger.info(f"로그 파일 개수: {len(log_files)}")
            
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        logger.info(f"로그 파일 {log_file.name}: {len(lines)}줄")
                        
                        # 최근 20줄만 읽기
                        recent_lines = lines[-20:] if len(lines) > 20 else lines
                        
                        for line in recent_lines:
                            line = line.strip()
                            if line and ('INFO' in line or 'ERROR' in line or 'WARNING' in line):
                                try:
                                    # 간단한 파싱 (형식: 2025-09-30 17:02:45.508 | INFO | message)
                                    parts = line.split(' | ')
                                    if len(parts) >= 3:
                                        timestamp_str = parts[0]
                                        level = parts[1].strip()
                                        message = ' | '.join(parts[2:])
                                        
                                        # 타임스탬프 파싱
                                        from datetime import datetime
                                        try:
                                            # 밀리초 부분 제거
                                            if '.' in timestamp_str:
                                                timestamp_str = timestamp_str.split('.')[0]
                                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                        except:
                                            timestamp = datetime.now()
                                        
                                        file_logs.append({
                                            'timestamp': timestamp,
                                            'level': level,
                                            'message': message,
                                            'source': 'file',
                                            'filename': log_file.name
                                        })
                                except Exception as e:
                                    logger.error(f"로그 라인 파싱 오류: {line[:50]}... - {e}")
                                    continue
                except Exception as e:
                    logger.error(f"로그 파일 읽기 오류: {log_file} - {e}")
        
        # 3. 파일 로그를 시간순으로 정렬
        file_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        file_logs = file_logs[:limit]  # 제한
        
        logger.info(f"파싱된 파일 로그 개수: {len(file_logs)}")
        
        # 템플릿 함수 정의
        def get_action_color(action):
            colors = {
                'SCAN': 'primary',
                'QR_DETECT': 'info', 
                'MERGE': 'warning',
                'UPLOAD': 'success',
                'ERROR': 'danger'
            }
            return colors.get(action, 'secondary')
        
        return templates.TemplateResponse("logs.html", {
            "request": request,
            "logs": db_logs,
            "file_logs": file_logs,
            "total_logs": len(db_logs) + len(file_logs),
            "get_action_color": get_action_color
        })
    except Exception as e:
        logger.error(f"로그 조회 오류: {e}")
        return templates.TemplateResponse("logs.html", {
            "request": request,
            "logs": [],
            "file_logs": [],
            "error_message": f"로그 조회 오류: {str(e)}"
        })


@app.get("/api/status")
async def api_status(username: str = Depends(verify_credentials)):
    """인스턴스 상태 API (표준 API)"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        import time
        import psutil
        from pathlib import Path
        
        # 각 폴더의 PDF 파일 수 계산
        def count_pdfs(path: Path) -> int:
            if not path.exists():
                return 0
            return len(list(path.rglob("*.pdf")))
        
        # 큐 상태
        queue = {
            "new": count_pdfs(processor.config.paths.scanner_output),
            "pendingMerge": count_pdfs(processor.config.paths.pending),
            "pendingUpload": count_pdfs(processor.config.paths.merged),
            "uploaded": count_pdfs(processor.config.paths.uploaded),
            "error": count_pdfs(processor.config.paths.error),
        }
        queue["total"] = sum(queue.values())
        
        # 디스크 여유 공간 (MB)
        try:
            disk_usage = psutil.disk_usage(str(processor.config.paths.data_root))
            disk_free_mb = disk_usage.free // (1024 * 1024)
        except Exception:
            disk_free_mb = 0
        
        # 업타임 (프로세서 시작 시간 기준)
        uptime_sec = int(time.time() - getattr(processor, '_start_time', time.time()))
        
        # 마지막 배치 시간
        last_batch_at = None
        if hasattr(processor, 'last_batch_time') and processor.last_batch_time:
            last_batch_at = processor.last_batch_time.isoformat()
        
        return {
            "uptimeSec": uptime_sec,
            "queue": queue,
            "diskFreeMB": disk_free_mb,
            "lastBatchAt": last_batch_at,
            "version": "2.0.0"
        }
        
    except Exception as e:
        logger.error(f"상태 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def api_stats(username: str = Depends(verify_credentials)):
    """통계 API - 파일 시스템 기반"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        from pathlib import Path
        
        # 각 폴더의 PDF 파일 수 계산
        def count_pdfs(path: Path) -> int:
            if not path.exists():
                return 0
            return len(list(path.rglob("*.pdf")))
        
        # 신규 문서 (scanner_output 폴더)
        scanner_count = count_pdfs(processor.config.paths.scanner_output)
        
        # 병합 대기 (pending 폴더)
        pending_count = count_pdfs(processor.config.paths.pending)
        
        # 업로드 대기 (merged 폴더)
        merged_count = count_pdfs(processor.config.paths.merged)
        
        # 업로드 완료 (uploaded 폴더)
        uploaded_count = count_pdfs(processor.config.paths.uploaded)
        
        # 오류 (error 폴더)
        error_count = count_pdfs(processor.config.paths.error)
        
        # 전체 문서 수
        total_count = scanner_count + pending_count + merged_count + uploaded_count + error_count
        
        stats = {
            'total': {
                'documents': total_count,
                'scanner': scanner_count,      # 신규 문서
                'pending': pending_count,      # 병합 대기
                'merged': merged_count,        # 업로드 대기
                'uploaded': uploaded_count,    # 업로드 완료
                'error': error_count          # 오류
            },
            'folders': {
                'scanner_output': str(processor.config.paths.scanner_output),
                'pending': str(processor.config.paths.pending),
                'merged': str(processor.config.paths.merged),
                'uploaded': str(processor.config.paths.uploaded),
                'error': str(processor.config.paths.error)
            }
        }
        
        return stats
    except Exception as e:
        logger.error(f"통계 조회 오류: {e}")
        return {
            'total': {'documents': 0, 'scanner': 0, 'pending': 0, 'merged': 0, 'uploaded': 0, 'error': 0},
            'folders': {}
        }


@app.get("/api/qr-engines")
async def api_qr_engines(username: str = Depends(verify_credentials)):
    """QR 엔진 상태 정보 API"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        engine_status = processor.qr_reader.get_engine_status()
        
        return {
            "engines": engine_status,
            "engine_order": processor.config.qr.engine_order,
            "config": {
                "pattern": processor.config.qr.pattern,
                "save_failed_images": processor.config.qr.save_failed_images,
                "failed_images_path": processor.config.qr.failed_images_path
            }
        }
        
    except Exception as e:
        logger.error(f"QR 엔진 상태 조회 오류: {e}")
        return {
            "engines": {},
            "engine_order": [],
            "config": {},
            "error": str(e)
        }


@app.get("/api/recent")
async def api_recent(limit: int = 10, username: str = Depends(verify_credentials)):
    """최근 문서 API"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        docs = processor.db_session.query(ScanDocument).order_by(
            ScanDocument.created_at.desc()
        ).limit(limit).all()
        
        return [{
            'id': doc.id,
            'transport_no': doc.transport_no,
            'status': doc.status.value if doc.status else None,
            'created_at': doc.created_at.isoformat() if doc.created_at else None,
            'error_message': doc.error_message
        } for doc in docs]
    except Exception as e:
        logger.error(f"최근 문서 조회 오류: {e}")
        return []


@app.get("/api/documents")
async def api_documents(folder: Optional[str] = None, 
                       limit: int = 100,
                       username: str = Depends(verify_credentials)):
    """문서 목록 API (파일 기반)"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        from pathlib import Path
        import os
        from datetime import datetime
        
        result = []
        
        # 폴더별 파일 수집
        folders_to_scan = []
        
        if folder == "scanner":
            folders_to_scan = [("scanner", processor.config.paths.scanner_output)]
        elif folder == "pending":
            folders_to_scan = [("pending", processor.config.paths.pending)]
        elif folder == "merged":
            folders_to_scan = [("merged", processor.config.paths.merged)]
        elif folder == "uploaded":
            folders_to_scan = [("uploaded", processor.config.paths.uploaded)]
        elif folder == "error":
            folders_to_scan = [("error", processor.config.paths.error)]
        else:
            # 전체 폴더
            folders_to_scan = [
                ("scanner", processor.config.paths.scanner_output),
                ("pending", processor.config.paths.pending),
                ("merged", processor.config.paths.merged),
                ("uploaded", processor.config.paths.uploaded),
                ("error", processor.config.paths.error)
            ]
        
        # 각 폴더의 PDF 파일 수집
        for folder_name, folder_path in folders_to_scan:
            if not folder_path.exists():
                continue
                
            for pdf_file in folder_path.glob("*.pdf"):
                try:
                    stat = pdf_file.stat()
                    
                    # 운송번호 추출 (파일명에서)
                    transport_no = None
                    filename = pdf_file.stem
                    
                    # 괄호 제거 후 14자리 숫자 확인
                    if '(' in filename:
                        base_name = filename.split('(')[0]
                    else:
                        base_name = filename
                    
                    if len(base_name) == 14 and base_name.isdigit():
                        transport_no = base_name
                    
                    # 상태 결정
                    status_map = {
                        "scanner": "SCANNER",
                        "pending": "PENDING", 
                        "merged": "MERGED",
                        "uploaded": "UPLOADED",
                        "error": "ERROR"
                    }
                    
                    result.append({
                        "id": f"{folder_name}_{pdf_file.name}",  # 고유 ID
                        "transport_no": transport_no,
                        "original_filename": pdf_file.name,
                        "file_path": str(pdf_file),
                        "status": status_map[folder_name],
                        "folder": folder_name,
                        "file_size": stat.st_size,
                        "page_count": None,  # 파일 기반에서는 계산 생략
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "processed_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "uploaded_at": None,
                        "error_message": None,
                        "file_exists": True
                    })
                    
                except Exception as e:
                    logger.error(f"파일 정보 읽기 오류: {pdf_file} - {e}")
                    continue
        
        # 수정 시간 기준으로 정렬 (최신순)
        result.sort(key=lambda x: x["processed_at"], reverse=True)
        
        # 제한 적용
        if limit:
            result = result[:limit]
        
        logger.info(f"파일 기반 문서 조회: {len(result)}개 문서 반환 (폴더: {folder or '전체'})")
        return result
        
    except Exception as e:
        logger.error(f"파일 기반 문서 목록 조회 오류: {e}")
        return []


@app.get("/debug/docs")
async def debug_docs(username: str = Depends(verify_credentials)):
    """디버그용 문서 조회"""
    if processor is None:
        return {"error": "processor is None"}
    
    try:
        # SQLAlchemy text 사용
        from sqlalchemy import text
        session = processor.db_session
        result = session.execute(text("SELECT id, transport_no, original_filename, status FROM scan_documents LIMIT 5"))
        docs = result.fetchall()
        
        # SQLAlchemy ORM으로 조회
        orm_docs = session.query(ScanDocument).limit(5).all()
        
        return {
            "raw_sql_count": len(docs),
            "raw_sql_docs": [{"id": row[0], "transport_no": row[1], "filename": row[2], "status": row[3]} for row in docs],
            "orm_count": len(orm_docs),
            "orm_docs": [{"id": doc.id, "status": str(doc.status), "filename": doc.original_filename} for doc in orm_docs]
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/fix-error-paths")
async def fix_error_paths(username: str = Depends(verify_credentials)):
    """오류 문서들의 잘못된 경로 수정"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        from pathlib import Path
        
        # scanner_output 경로를 가진 ERROR 상태 문서들 찾기
        error_docs = processor.db_session.query(ScanDocument).filter(
            ScanDocument.status == "ERROR",
            ScanDocument.file_path.like("%scanner_output%")
        ).all()
        
        fixed_count = 0
        
        for doc in error_docs:
            # 실제 파일 위치 찾기
            filename = Path(doc.file_path).name
            error_folders = list(processor.config.paths.error.glob("*/"))
            
            actual_file = None
            for error_folder in error_folders:
                potential_file = error_folder / filename
                if potential_file.exists():
                    actual_file = potential_file
                    break
            
            if actual_file:
                # 경로 업데이트
                old_path = doc.file_path
                doc.file_path = str(actual_file)
                processor.db_session.commit()
                
                logger.info(f"경로 수정: {old_path} -> {actual_file}")
                fixed_count += 1
        
        return {
            "success": True,
            "message": f"{fixed_count}개의 오류 문서 경로를 수정했습니다.",
            "fixed_count": fixed_count
        }
        
    except Exception as e:
        logger.error(f"경로 수정 오류: {e}")
        return {"success": False, "message": str(e)}


@app.post("/cleanup-folders")
async def cleanup_folders(username: str = Depends(verify_credentials)):
    """날짜 폴더 구조를 평면 구조로 정리"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        from pathlib import Path
        import shutil
        
        moved_count = 0
        
        # pending 폴더 정리
        for date_dir in processor.config.paths.pending.iterdir():
            if date_dir.is_dir() and date_dir.name.isdigit():
                for pdf_file in date_dir.glob("*.pdf"):
                    dest_path = processor.config.paths.pending / pdf_file.name
                    
                    # 중복 파일명 처리
                    if dest_path.exists():
                        counter = 1
                        stem = pdf_file.stem
                        while True:
                            dest_path = processor.config.paths.pending / f"{stem}({counter}).pdf"
                            if not dest_path.exists():
                                break
                            counter += 1
                    
                    shutil.move(str(pdf_file), str(dest_path))
                    moved_count += 1
                    logger.info(f"파일 이동: {pdf_file} -> {dest_path}")
                
                # 빈 폴더 삭제
                if not list(date_dir.iterdir()):
                    date_dir.rmdir()
                    logger.info(f"빈 폴더 삭제: {date_dir}")
        
        # merged 폴더 정리
        for date_dir in processor.config.paths.merged.iterdir():
            if date_dir.is_dir() and date_dir.name.isdigit():
                for pdf_file in date_dir.glob("*.pdf"):
                    dest_path = processor.config.paths.merged / pdf_file.name
                    
                    # 중복 파일명 처리
                    if dest_path.exists():
                        counter = 1
                        stem = pdf_file.stem
                        while True:
                            dest_path = processor.config.paths.merged / f"{stem}({counter}).pdf"
                            if not dest_path.exists():
                                break
                            counter += 1
                    
                    shutil.move(str(pdf_file), str(dest_path))
                    moved_count += 1
                    logger.info(f"파일 이동: {pdf_file} -> {dest_path}")
                
                # 빈 폴더 삭제
                if not list(date_dir.iterdir()):
                    date_dir.rmdir()
                    logger.info(f"빈 폴더 삭제: {date_dir}")
        
        # error 폴더 정리
        for date_dir in processor.config.paths.error.iterdir():
            if date_dir.is_dir() and date_dir.name.isdigit():
                for pdf_file in date_dir.glob("*.pdf"):
                    dest_path = processor.config.paths.error / pdf_file.name
                    
                    # 중복 파일명 처리
                    if dest_path.exists():
                        counter = 1
                        stem = pdf_file.stem
                        while True:
                            dest_path = processor.config.paths.error / f"{stem}({counter}).pdf"
                            if not dest_path.exists():
                                break
                            counter += 1
                    
                    shutil.move(str(pdf_file), str(dest_path))
                    moved_count += 1
                    logger.info(f"파일 이동: {pdf_file} -> {dest_path}")
                
                # 빈 폴더 삭제
                if not list(date_dir.iterdir()):
                    date_dir.rmdir()
                    logger.info(f"빈 폴더 삭제: {date_dir}")
        
        return {
            "success": True,
            "message": f"{moved_count}개 파일을 평면 구조로 이동했습니다.",
            "moved_count": moved_count
        }
        
    except Exception as e:
        logger.error(f"폴더 정리 오류: {e}")
        return {"success": False, "message": str(e)}


@app.get("/api/logs")
async def api_logs(username: str = Depends(verify_credentials)):
    """로그 API (디버깅용)"""
    if processor is None:
        return {"error": "processor is None"}
    
    try:
        # 로그 디렉토리 확인
        log_dir = processor.config.paths.logs
        log_info = {
            "log_dir": str(log_dir),
            "log_dir_exists": log_dir.exists(),
            "log_files": []
        }
        
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            for log_file in log_files[:5]:  # 최대 5개
                try:
                    stat = log_file.stat()
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        sample_lines = lines[-3:] if len(lines) > 3 else lines
                    
                    log_info["log_files"].append({
                        "name": log_file.name,
                        "size": stat.st_size,
                        "total_lines": len(lines),
                        "sample_lines": [line.strip() for line in sample_lines]
                    })
                except Exception as e:
                    log_info["log_files"].append({
                        "name": log_file.name,
                        "error": str(e)
                    })
        
        return log_info
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/pdf-preview")
async def pdf_preview(file: str, username: str = Depends(verify_credentials)):
    """PDF 파일 미리보기"""
    import os
    from pathlib import Path
    from fastapi.responses import Response
    
    try:
        # 파일 경로 검증
        file_path = Path(file)
        
        # 보안을 위한 경로 검증
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
        
        if not file_path.suffix.lower() == '.pdf':
            raise HTTPException(status_code=400, detail="PDF 파일만 미리보기할 수 있습니다.")
        
        # PDF 파일 읽기
        with open(file_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={file_path.name}",
                "Cache-Control": "no-cache"
            }
        )
    except Exception as e:
        logger.error(f"PDF 미리보기 오류: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 로드 실패: {str(e)}")


@app.get("/api/errors")
async def api_errors(username: str = Depends(verify_credentials)):
    """오류 문서 API (파일 기반)"""
    if processor is None:
        raise HTTPException(status_code=503, detail="시스템이 초기화 중입니다.")
    
    try:
        from pathlib import Path
        from datetime import datetime
        
        result = []
        error_folder = processor.config.paths.error
        
        if not error_folder.exists():
            return []
        
        # error 폴더의 모든 PDF 파일 수집
        for pdf_file in error_folder.glob("*.pdf"):
            try:
                stat = pdf_file.stat()
                
                # 운송번호 추출 (파일명에서)
                transport_no = None
                filename = pdf_file.stem
                
                # 괄호 제거 후 14자리 숫자 확인
                if '(' in filename:
                    base_name = filename.split('(')[0]
                else:
                    base_name = filename
                
                if len(base_name) == 14 and base_name.isdigit():
                    transport_no = base_name
                
                # 오류 메시지 추정 (파일명 기반)
                error_message = None
                if 'invalid_qr' in filename:
                    error_message = "유효하지 않은 QR 코드"
                elif 'no_qr' in filename:
                    error_message = "QR 코드를 찾을 수 없음"
                elif 'multiple_qr' in filename:
                    error_message = "다중 QR 코드 검출"
                else:
                    error_message = "처리 오류"
                
                result.append({
                    'id': f"error_{pdf_file.name}",
                    'transport_no': transport_no,
                    'original_filename': pdf_file.name,
                    'error_message': error_message,
                    'file_path': str(pdf_file),
                    'file_size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'file_exists': True
                })
                
            except Exception as e:
                logger.error(f"오류 파일 정보 읽기 실패: {pdf_file} - {e}")
                continue
        
        # 수정 시간 기준으로 정렬 (최신순)
        result.sort(key=lambda x: x["modified_at"], reverse=True)
        
        logger.info(f"파일 기반 오류 문서 조회: {len(result)}개 문서 반환")
        return result
        
    except Exception as e:
        logger.error(f"파일 기반 오류 문서 조회 오류: {e}")
        return []
