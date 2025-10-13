#!/usr/bin/env python3
"""
웹 서버만 실행하는 스크립트
"""
import uvicorn
from src.web_app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
