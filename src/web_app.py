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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, username: str = Depends(verify_credentials)):
    """메인 대시보드"""
    # 통계 수집
    stats = {
        'total': processor.db_session.query(ScanDocument).count(),
        'pending': processor.db_session.query(ScanDocument).filter_by(status=ProcessStatus.PENDING).count(),
        'merged': processor.db_session.query(ScanDocument).filter_by(status=ProcessStatus.MERGED).count(),
        'uploaded': processor.db_session.query(ScanDocument).filter_by(status=ProcessStatus.UPLOADED).count(),
        'error': processor.db_session.query(ScanDocument).filter_by(status=ProcessStatus.ERROR).count(),
        'retry_queue': processor.db_session.query(UploadQueue).count()
    }
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": stats,
        "config": processor.config
    })


@app.get("/documents", response_class=HTMLResponse)
async def documents(request: Request, 
                   status: Optional[str] = None,
                   limit: int = 100,
                   username: str = Depends(verify_credentials)):
    """문서 목록"""
    query = processor.db_session.query(ScanDocument)
    
    if status:
        query = query.filter_by(status=status)
    
    docs = query.order_by(ScanDocument.created_at.desc()).limit(limit).all()
    
    return templates.TemplateResponse("documents.html", {
        "request": request,
        "documents": docs,
        "status_filter": status
    })


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, username: str = Depends(verify_credentials)):
    """설정 페이지"""
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "config": processor.config
    })


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
    """에러 문서 목록"""
    error_docs = processor.db_session.query(ScanDocument).filter_by(
        status=ProcessStatus.ERROR
    ).order_by(ScanDocument.created_at.desc()).all()
    
    # 에러 폴더의 파일들도 확인
    error_files = []
    for date_dir in processor.config.paths.error.iterdir():
        if date_dir.is_dir():
            for pdf_file in date_dir.glob("*.pdf"):
                error_info_file = pdf_file.with_suffix('.error.json')
                error_info = {}
                if error_info_file.exists():
                    with open(error_info_file, 'r', encoding='utf-8') as f:
                        error_info = json.load(f)
                
                error_files.append({
                    'path': pdf_file,
                    'name': pdf_file.name,
                    'error_message': error_info.get('error_message', ''),
                    'moved_at': error_info.get('moved_at', '')
                })
    
    return templates.TemplateResponse("errors.html", {
        "request": request,
        "error_docs": error_docs,
        "error_files": error_files
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
        
        # 운송번호 유효성 검사
        if not processor.qr_reader.validate_transport_no(transport_no):
            raise HTTPException(status_code=400, detail="유효하지 않은 운송번호입니다.")
        
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


@app.get("/logs", response_class=HTMLResponse)
async def logs(request: Request, 
              limit: int = 200,
              username: str = Depends(verify_credentials)):
    """처리 로그"""
    logs = processor.db_session.query(ProcessLog).order_by(
        ProcessLog.created_at.desc()
    ).limit(limit).all()
    
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "logs": logs
    })


@app.get("/api/stats")
async def api_stats(username: str = Depends(verify_credentials)):
    """통계 API"""
    # 오늘 통계
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    stats = {
        'today': {
            'scanned': processor.db_session.query(ScanDocument).filter(
                ScanDocument.created_at >= today_start
            ).count(),
            'uploaded': processor.db_session.query(ScanDocument).filter(
                ScanDocument.uploaded_at >= today_start
            ).count(),
            'errors': processor.db_session.query(ScanDocument).filter(
                ScanDocument.created_at >= today_start,
                ScanDocument.status == ProcessStatus.ERROR
            ).count()
        },
        'total': {
            'documents': processor.db_session.query(ScanDocument).count(),
            'pending': processor.db_session.query(ScanDocument).filter_by(status=ProcessStatus.PENDING).count(),
            'merged': processor.db_session.query(ScanDocument).filter_by(status=ProcessStatus.MERGED).count(),
            'uploaded': processor.db_session.query(ScanDocument).filter_by(status=ProcessStatus.UPLOADED).count(),
            'error': processor.db_session.query(ScanDocument).filter_by(status=ProcessStatus.ERROR).count()
        },
        'queue': {
            'upload': processor.db_session.query(UploadQueue).count(),
            'retry': processor.db_session.query(UploadQueue).filter(
                UploadQueue.retry_count > 0
            ).count()
        }
    }
    
    return stats


@app.get("/api/recent")
async def api_recent(limit: int = 10, username: str = Depends(verify_credentials)):
    """최근 문서 API"""
    docs = processor.db_session.query(ScanDocument).order_by(
        ScanDocument.created_at.desc()
    ).limit(limit).all()
    
    return [{
        'id': doc.id,
        'transport_no': doc.transport_no,
        'status': doc.status,
        'created_at': doc.created_at.isoformat() if doc.created_at else None,
        'error_message': doc.error_message
    } for doc in docs]
