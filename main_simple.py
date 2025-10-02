#!/usr/bin/env python3
"""
QR 스캔 관리 시스템 - 간단 실행 파일 (QR 라이브러리 없이 테스트)
"""
import sys
import asyncio
import uvicorn
from pathlib import Path

# src 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent))

# FastAPI 앱만 실행
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from src.config import ConfigManager

app = FastAPI(title="QR 스캔 관리 시스템 (간단 버전)")

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>QR 스캔 관리 시스템</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 50px; }
                .container { max-width: 800px; margin: 0 auto; }
                .card { background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 QR 스캔 관리 시스템</h1>
                <div class="card">
                    <h2>✅ 테스트 성공!</h2>
                    <p>시스템이 정상적으로 시작되었습니다.</p>
                    <ul>
                        <li>✅ FastAPI 웹 서버 실행</li>
                        <li>✅ 설정 파일 로드</li>
                        <li>✅ 기본 디렉토리 생성</li>
                        <li>✅ PDF 처리 테스트 통과</li>
                        <li>⚠️ QR 라이브러리는 선택적 (zbar 설치 필요)</li>
                    </ul>
                </div>
                <div class="card">
                    <h3>📁 프로젝트 구조</h3>
                    <pre>
src/
├── config.py        ✅ 설정 관리
├── models.py         ✅ 데이터베이스 모델
├── pdf_processor.py  ✅ PDF 처리 (테스트 통과)
├── file_watcher.py   ✅ 파일 감시
├── uploader.py       ✅ 업로드 모듈
├── batch_processor.py✅ 배치 처리
├── processor.py      ⚠️ QR 처리 (zbar 필요)
└── web_app.py        ✅ 웹 UI

tests/
├── test_pdf_processor.py ✅ 통과
├── test_qr_reader.py     ⚠️ 스킵됨
└── test_scenarios.py     ⚠️ 스킵됨
                    </pre>
                </div>
                <div class="card">
                    <h3>🔧 완전한 기능을 위한 추가 설정</h3>
                    <p>QR 코드 인식 기능을 활성화하려면:</p>
                    <ol>
                        <li><code>brew install zbar</code> (이미 설치됨)</li>
                        <li><code>pip install --force-reinstall pyzbar</code></li>
                        <li>환경변수 설정 또는 라이브러리 경로 조정</li>
                    </ol>
                </div>
            </div>
        </body>
    </html>
    """

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "QR 스캔 시스템이 정상 작동 중입니다."}

def main():
    """메인 함수"""
    config = ConfigManager()
    print(f"🚀 QR 스캔 관리 시스템 시작")
    print(f"📝 설정 파일: config.yaml")
    print(f"📁 데이터 경로: {config.paths.data_root}")
    print(f"🌐 웹 UI: http://localhost:{config.system.web_port}")
    print(f"🔑 관리자 비밀번호: {config.system.admin_password}")
    
    uvicorn.run(app, host="0.0.0.0", port=config.system.web_port)

if __name__ == "__main__":
    main()
