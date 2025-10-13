#!/bin/bash
# QR 스캔 관리 시스템 실행 스크립트 (환경변수 설정 포함)

echo "🚀 QR 스캔 관리 시스템 시작..."

# Homebrew 라이브러리 경로 설정
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
export PKG_CONFIG_PATH="/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"

# Python 경로 추가
export PATH="/Users/donghyun/Library/Python/3.9/bin:$PATH"

# 현재 디렉토리로 이동
cd "$(dirname "$0")"

# 설정 파일 확인
if [ ! -f "config.yaml" ]; then
    echo "⚠️ config.yaml이 없습니다. 기본 설정을 복사합니다..."
    cp config.example.yaml config.yaml
fi

# 데이터 디렉토리 생성
mkdir -p data/{pending,merged,uploaded,error,logs}

echo "📁 데이터 경로: $(pwd)/data"
echo "🌐 웹 UI: http://localhost:8000"
echo "🔑 관리자 비밀번호: 1212"
echo ""

# QR 라이브러리 테스트
echo "🔍 QR 라이브러리 테스트 중..."
if python3 -c "from pyzbar import pyzbar; print('✅ QR 기능 사용 가능')" 2>/dev/null; then
    echo "✅ 전체 기능으로 시작합니다."
    python3 main.py
else
    echo "⚠️ QR 라이브러리 문제로 데모 모드로 시작합니다."
    echo "   (PDF 처리, 웹 UI, 데이터베이스는 정상 작동)"
    python3 main_demo.py
fi
