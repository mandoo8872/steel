#!/usr/bin/env python3
"""
QR 스캔 관리 시스템 - 데모 버전 (QR 없이 전체 기능 테스트)
"""
import sys
import asyncio
import uvicorn
from pathlib import Path
import shutil
import time

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from src.config import ConfigManager
from src.models import init_database, get_session, ScanDocument, ProcessStatus
from src.pdf_processor import PDFProcessor
from src.uploader import UploadManager

app = FastAPI(title="QR 스캔 관리 시스템 - 데모")

# 전역 설정
config = ConfigManager()
db_engine = None
db_session = None
pdf_processor = None
upload_manager = None

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 이벤트"""
    global db_engine, db_session, pdf_processor, upload_manager
    
    # 디렉토리 생성
    config.paths.create_directories()
    
    # 데이터베이스 초기화
    db_path = config.paths.data_root / "qr_demo.db"
    db_engine = init_database(db_path)
    db_session = get_session(db_engine)
    
    # 프로세서 초기화
    pdf_processor = PDFProcessor(config)
    upload_manager = UploadManager(config)
    
    print(f"🚀 QR 스캔 관리 시스템 데모 시작")
    print(f"📁 데이터 경로: {config.paths.data_root}")
    print(f"🌐 웹 UI: http://localhost:{config.system.web_port}")

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """대시보드"""
    # 통계 계산
    total = db_session.query(ScanDocument).count()
    pending = db_session.query(ScanDocument).filter_by(status=ProcessStatus.PENDING).count()
    uploaded = db_session.query(ScanDocument).filter_by(status=ProcessStatus.UPLOADED).count()
    error = db_session.query(ScanDocument).filter_by(status=ProcessStatus.ERROR).count()
    
    return f"""
    <html>
        <head>
            <title>QR 스캔 관리 시스템 - 데모</title>
            <meta charset="utf-8">
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <h1 class="mb-4">🚀 QR 스캔 관리 시스템 데모</h1>
                
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">전체 문서</h5>
                                <h2 class="text-primary">{total}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">대기중</h5>
                                <h2 class="text-warning">{pending}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">업로드됨</h5>
                                <h2 class="text-success">{uploaded}</h2>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card text-center">
                            <div class="card-body">
                                <h5 class="card-title">오류</h5>
                                <h2 class="text-danger">{error}</h2>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5>✅ 구현 완료된 기능</h5>
                            </div>
                            <div class="card-body">
                                <ul class="list-group list-group-flush">
                                    <li class="list-group-item">✅ 설정 관리 (암호화, YAML)</li>
                                    <li class="list-group-item">✅ PDF 처리 (병합, 정규화)</li>
                                    <li class="list-group-item">✅ 파일 감시 (실시간/폴링)</li>
                                    <li class="list-group-item">✅ 업로드 (NAS/HTTP)</li>
                                    <li class="list-group-item">✅ 배치 처리</li>
                                    <li class="list-group-item">✅ 데이터베이스 (SQLAlchemy)</li>
                                    <li class="list-group-item">✅ 웹 UI (FastAPI)</li>
                                    <li class="list-group-item">✅ Windows 서비스</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h5>🔧 테스트 기능</h5>
                            </div>
                            <div class="card-body">
                                <button class="btn btn-primary mb-2" onclick="testPdfMerge()">PDF 병합 테스트</button><br>
                                <button class="btn btn-success mb-2" onclick="testUpload()">업로드 테스트</button><br>
                                <button class="btn btn-info mb-2" onclick="addSampleData()">샘플 데이터 추가</button><br>
                                <button class="btn btn-secondary mb-2" onclick="location.href='/api/docs'">API 문서</button>
                                
                                <div id="testResult" class="mt-3"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="mt-4">
                    <h5>📊 최근 문서</h5>
                    <div id="recentDocs">
                        <p class="text-muted">문서를 불러오는 중...</p>
                    </div>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
            <script>
                function showResult(message, type = 'info') {{
                    document.getElementById('testResult').innerHTML = 
                        `<div class="alert alert-${{type}}">${{message}}</div>`;
                }}
                
                async function testPdfMerge() {{
                    try {{
                        const response = await fetch('/api/test/pdf-merge', {{ method: 'POST' }});
                        const result = await response.json();
                        showResult(result.message, result.success ? 'success' : 'danger');
                    }} catch (error) {{
                        showResult('PDF 병합 테스트 실패: ' + error.message, 'danger');
                    }}
                }}
                
                async function testUpload() {{
                    try {{
                        const response = await fetch('/api/test/upload', {{ method: 'POST' }});
                        const result = await response.json();
                        showResult(result.message, result.success ? 'success' : 'danger');
                    }} catch (error) {{
                        showResult('업로드 테스트 실패: ' + error.message, 'danger');
                    }}
                }}
                
                async function addSampleData() {{
                    try {{
                        const response = await fetch('/api/test/sample-data', {{ method: 'POST' }});
                        const result = await response.json();
                        showResult(result.message, 'success');
                        location.reload();
                    }} catch (error) {{
                        showResult('샘플 데이터 추가 실패: ' + error.message, 'danger');
                    }}
                }}
                
                // 최근 문서 로드
                async function loadRecentDocs() {{
                    try {{
                        const response = await fetch('/api/documents/recent');
                        const docs = await response.json();
                        
                        let html = '<table class="table table-sm"><thead><tr><th>ID</th><th>파일명</th><th>상태</th><th>생성일</th></tr></thead><tbody>';
                        docs.forEach(doc => {{
                            html += `<tr><td>${{doc.id}}</td><td>${{doc.original_filename}}</td><td><span class="badge bg-primary">${{doc.status}}</span></td><td>${{new Date(doc.created_at).toLocaleString()}}</td></tr>`;
                        }});
                        html += '</tbody></table>';
                        
                        document.getElementById('recentDocs').innerHTML = html;
                    }} catch (error) {{
                        document.getElementById('recentDocs').innerHTML = '<p class="text-danger">문서 로드 실패</p>';
                    }}
                }}
                
                loadRecentDocs();
                setInterval(loadRecentDocs, 10000); // 10초마다 새로고침
            </script>
        </body>
    </html>
    """

@app.post("/api/test/pdf-merge")
async def test_pdf_merge():
    """PDF 병합 테스트"""
    try:
        # 테스트 PDF 파일들 사용
        test_pdfs_dir = Path("tests/test_pdfs")
        if not test_pdfs_dir.exists():
            return {"success": False, "message": "테스트 PDF 폴더가 없습니다."}
        
        pdf_files = list(test_pdfs_dir.glob("merge_test_*.pdf"))
        if not pdf_files:
            return {"success": False, "message": "병합할 테스트 PDF가 없습니다."}
        
        output_path = config.paths.data_root / "test_merged.pdf"
        result = pdf_processor.merge_pdfs(pdf_files, output_path, remove_duplicates=False)
        
        if result['success']:
            return {"success": True, "message": f"PDF 병합 성공! {result['page_count']}페이지 생성"}
        else:
            return {"success": False, "message": f"PDF 병합 실패: {result['error']}"}
    
    except Exception as e:
        return {"success": False, "message": f"테스트 오류: {str(e)}"}

@app.post("/api/test/upload")
async def test_upload():
    """업로드 테스트"""
    try:
        test_file = config.paths.data_root / "test_merged.pdf"
        if not test_file.exists():
            return {"success": False, "message": "업로드할 파일이 없습니다. 먼저 PDF 병합을 실행하세요."}
        
        result = await upload_manager.upload_file(test_file, "20250930000001")
        
        if result['success']:
            return {"success": True, "message": "업로드 테스트 성공!"}
        else:
            return {"success": False, "message": f"업로드 실패: {result.get('message', '알 수 없는 오류')}"}
    
    except Exception as e:
        return {"success": False, "message": f"업로드 테스트 오류: {str(e)}"}

@app.post("/api/test/sample-data")
async def add_sample_data():
    """샘플 데이터 추가"""
    try:
        from datetime import datetime
        
        # 샘플 문서들 추가
        samples = [
            {"filename": "sample_001.pdf", "transport_no": "20250930000001", "status": ProcessStatus.UPLOADED},
            {"filename": "sample_002.pdf", "transport_no": "20250930000002", "status": ProcessStatus.PENDING},
            {"filename": "sample_003.pdf", "transport_no": "20250930000003", "status": ProcessStatus.ERROR},
            {"filename": "sample_004.pdf", "transport_no": "20250930000004", "status": ProcessStatus.MERGED},
        ]
        
        for sample in samples:
            doc = ScanDocument(
                file_path=f"data/samples/{sample['filename']}",
                original_filename=sample['filename'],
                transport_no=sample['transport_no'],
                status=sample['status'],
                file_size=1024,
                page_count=1,
                created_at=datetime.utcnow()
            )
            db_session.add(doc)
        
        db_session.commit()
        return {"success": True, "message": f"{len(samples)}개의 샘플 데이터가 추가되었습니다."}
    
    except Exception as e:
        return {"success": False, "message": f"샘플 데이터 추가 오류: {str(e)}"}

@app.get("/api/documents/recent")
async def get_recent_documents():
    """최근 문서 조회"""
    docs = db_session.query(ScanDocument).order_by(
        ScanDocument.created_at.desc()
    ).limit(10).all()
    
    return [{
        'id': doc.id,
        'original_filename': doc.original_filename,
        'transport_no': doc.transport_no,
        'status': doc.status,
        'created_at': doc.created_at.isoformat() if doc.created_at else None
    } for doc in docs]

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "QR 스캔 시스템 데모가 정상 작동 중입니다."}

def main():
    """메인 함수"""
    print(f"🚀 QR 스캔 관리 시스템 데모 시작")
    print(f"🌐 웹 UI: http://localhost:{config.system.web_port}")
    print(f"📝 API 문서: http://localhost:{config.system.web_port}/docs")
    
    uvicorn.run(app, host="0.0.0.0", port=config.system.web_port)

if __name__ == "__main__":
    main()
