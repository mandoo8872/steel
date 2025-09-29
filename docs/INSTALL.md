# QR 스캔 관리 시스템 설치 가이드

## 시스템 요구사항

### 최소 사양
- OS: Windows 10/11, Windows Server 2016 이상
- CPU: 2코어 이상
- RAM: 4GB 이상
- 디스크: 10GB 이상 여유 공간
- Python: 3.8 이상

### 필수 소프트웨어
- Python 3.8+ (3.10 권장)
- Poppler (PDF 이미지 변환용)
- Visual C++ Redistributable (Windows)

## 설치 절차

### 1. Python 설치

1. [Python 공식 사이트](https://www.python.org/downloads/)에서 Python 3.10 다운로드
2. 설치 시 "Add Python to PATH" 체크
3. 설치 완료 후 명령 프롬프트에서 확인:
   ```bash
   python --version
   ```

### 2. Poppler 설치 (Windows)

1. [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) 다운로드
2. C:\Program Files\poppler 에 압축 해제
3. 시스템 환경변수 PATH에 `C:\Program Files\poppler\Library\bin` 추가

### 3. 프로젝트 설치

1. 프로젝트 파일 압축 해제
   ```bash
   cd C:\QRScanSystem
   ```

2. 가상환경 생성 및 활성화
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. 의존성 설치
   ```bash
   pip install -r requirements.txt
   ```

4. Windows 서비스용 추가 패키지 설치
   ```bash
   pip install pywin32
   ```

### 4. 초기 설정

1. 설정 파일 복사
   ```bash
   copy config.example.yaml config.yaml
   ```

2. config.yaml 편집하여 환경에 맞게 수정:
   - `scanner_output`: 스캐너 출력 폴더 경로
   - `data_root`: 데이터 저장 폴더 경로
   - `nas.path`: NAS 경로 (사용 시)
   - `http.endpoint`: API 엔드포인트 (사용 시)

3. 필요한 디렉토리 생성
   ```bash
   mkdir data\pending data\merged data\uploaded data\error data\logs
   ```

### 5. 테스트 실행

1. 개발 모드로 실행
   ```bash
   python main.py
   ```

2. 웹 브라우저에서 http://localhost:8000 접속
3. 비밀번호: 1212

### 6. Windows 서비스 설치

1. 관리자 권한으로 명령 프롬프트 실행
2. 서비스 설치 스크립트 실행
   ```bash
   cd scripts
   install_service.bat
   ```

3. 서비스 상태 확인
   ```bash
   sc query QRScanService
   ```

## 설치 확인

1. 서비스 실행 상태 확인
2. 웹 UI 접속 가능 여부 확인
3. 테스트 PDF 처리 확인:
   ```bash
   python tests\generate_test_pdfs.py
   ```

## 문제 해결

### Python 명령을 찾을 수 없음
- Python이 PATH에 추가되었는지 확인
- 시스템 재시작 후 재시도

### Poppler 관련 오류
- poppler/bin 경로가 PATH에 있는지 확인
- pdf2image 재설치: `pip install --force-reinstall pdf2image`

### 서비스 시작 실패
- 로그 확인: `data\logs` 폴더
- 권한 확인: 서비스 계정이 폴더 접근 권한 있는지 확인

### 포트 충돌
- config.yaml에서 web_port 변경
- 방화벽에서 해당 포트 허용

## 업데이트

1. 서비스 중지
   ```bash
   net stop QRScanService
   ```

2. 백업 생성
   - config.yaml
   - data 폴더
   - 데이터베이스 파일

3. 새 버전 파일 복사

4. 의존성 업데이트
   ```bash
   pip install -r requirements.txt --upgrade
   ```

5. 서비스 재시작
   ```bash
   net start QRScanService
   ```
