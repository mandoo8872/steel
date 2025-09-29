# QR 기반 인수증/상차증 스캔 관리 시스템

PDF 스캔 파일을 자동으로 처리하여 QR 코드를 인식하고, 운송번호별로 분류/병합/업로드하는 시스템입니다.

## 주요 기능

- 폴더 감시를 통한 자동 PDF 수집
- QR 코드 인식 (14자리 운송번호)
- 운송번호별 자동 분류 및 병합
- NAS/HTTP 업로드 지원
- 웹 기반 관리자 UI
- Windows 서비스 지원

## 설치 방법

1. Python 3.8+ 설치
2. 의존성 설치: `pip install -r requirements.txt`
3. 설정 파일 복사: `cp config.example.yaml config.yaml`
4. 설정 파일 수정
5. 실행: `python main.py`

## 설정

`config.yaml` 파일에서 다음 항목들을 설정할 수 있습니다:

- 입력 폴더 경로
- 데이터 저장 경로
- 업로드 설정 (NAS/HTTP)
- 배치 처리 주기
- 재시도 정책

## 관리자 UI

http://localhost:8000 에서 웹 UI 접속 가능 (기본 비밀번호: 1212)

