#!/bin/bash
# 개발 모드 실행 스크립트 (macOS/Linux)

echo "QR 스캔 관리 시스템 개발 모드 시작..."

# 스크립트 디렉토리로 이동
cd "$(dirname "$0")/.."

# Python 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 설정 파일 확인
if [ ! -f "config.yaml" ]; then
    echo "설정 파일이 없습니다. 기본 설정을 복사합니다..."
    cp config.example.yaml config.yaml
fi

# 디렉토리 생성
mkdir -p data/pending data/merged data/uploaded data/error data/logs

# 메인 프로그램 실행
python main.py
