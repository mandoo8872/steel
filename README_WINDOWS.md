# Steel QR - Windows 실행파일 빌드 및 배포 가이드

## 📦 빌드 방법

### 1. 사전 준비

#### 필수 설치 항목
- **Python 3.11 이상**
- **Visual C++ Redistributable** (OpenCV, pikepdf 등)
- **Poppler for Windows** (PDF → 이미지 변환)

#### Poppler 설치
1. https://github.com/oschwartz10612/poppler-windows/releases 에서 다운로드
2. `poppler-xx.xx.x` 폴더를 `C:\Program Files\poppler` 에 압축 해제
3. 시스템 환경변수 PATH에 `C:\Program Files\poppler\Library\bin` 추가

### 2. 빌드 의존성 설치

```bash
# 가상환경 생성 (권장)
python -m venv .venv
.venv\Scripts\activate

# 런타임 의존성 설치
pip install -r requirements.txt

# 빌드 의존성 설치
pip install -r requirements-build.txt
```

### 3. 실행파일 빌드

```bash
python build_windows.py
```

빌드가 완료되면 `dist/steel-qr.exe` 파일이 생성됩니다.

**예상 빌드 시간:** 3-5분  
**예상 파일 크기:** 100-150MB (모든 의존성 포함)

---

## 🚀 배포

### 배포 파일 구성

```
steel-qr-package/
├── steel-qr.exe              # 실행파일
├── config.example.yaml       # 설정 예제
├── instances.example.json    # 인스턴스 레지스트리 예제
├── README.txt                # 사용 설명서
└── install_service.py        # 서비스 설치 스크립트 (선택)
```

### 배포 패키지 생성

```bash
# 배포 폴더 생성
mkdir steel-qr-package
copy dist\steel-qr.exe steel-qr-package\
copy config.example.yaml steel-qr-package\
copy instances.example.json steel-qr-package\
copy README_WINDOWS.md steel-qr-package\README.txt
copy install_service.py steel-qr-package\

# ZIP으로 압축
powershell Compress-Archive -Path steel-qr-package -DestinationPath steel-qr-windows.zip
```

---

## ⚙️ 설정

### 1. 설정 파일 준비

`config.example.yaml`을 `config.yaml`로 복사하고 편집:

```yaml
system:
  web_port: 8000
  admin_password: "1212"
  mode: "kiosk"  # 또는 "admin"

paths:
  scanner_output: "data/scanner_output"
  data_root: "data"
  logs: "logs"

qr:
  engines:
    zbar:
      enabled: true
    zxing:
      enabled: true
    pyzbar_preproc:
      enabled: true

upload:
  type: "nas"  # 또는 "http", "none"
  # ... 기타 설정
```

### 2. 데이터 폴더 생성

```bash
mkdir data
mkdir data\scanner_output
mkdir data\pending
mkdir data\merged
mkdir data\uploaded
mkdir data\error
mkdir logs
```

---

## 🖥️ 실행 방법

### 키오스크 모드 (스캔 및 처리)

```bash
steel-qr.exe --mode kiosk --port 8000
```

브라우저에서 `http://localhost:8000` 접속

### 관리자 모드 (중앙 관리)

```bash
steel-qr.exe --mode admin --port 8100
```

브라우저에서 `http://localhost:8100` 접속

**기본 로그인:**
- 사용자명: `admin`
- 비밀번호: `1212` (config.yaml에서 변경 가능)

---

## 🔧 Windows 서비스로 등록

### 방법 1: NSSM 사용 (권장)

#### 1. NSSM 다운로드
https://nssm.cc/download

#### 2. 서비스 설치
```cmd
# 관리자 권한 CMD
nssm install SteelQR-Kiosk "C:\path\to\steel-qr.exe"
nssm set SteelQR-Kiosk AppParameters "--mode kiosk --port 8000"
nssm set SteelQR-Kiosk AppDirectory "C:\path\to"
nssm set SteelQR-Kiosk DisplayName "Steel QR Scan System (Kiosk)"
nssm set SteelQR-Kiosk Description "QR 스캔 문서 관리 시스템"
nssm set SteelQR-Kiosk Start SERVICE_AUTO_START
```

#### 3. 서비스 시작
```cmd
nssm start SteelQR-Kiosk
```

#### 4. 서비스 상태 확인
```cmd
nssm status SteelQR-Kiosk
```

#### 5. 서비스 중지
```cmd
nssm stop SteelQR-Kiosk
```

#### 6. 서비스 제거
```cmd
nssm remove SteelQR-Kiosk confirm
```

### 방법 2: sc 명령어 사용

```cmd
# 관리자 권한 CMD
sc create SteelQR-Kiosk binPath= "C:\path\to\steel-qr.exe --mode kiosk --port 8000" start= auto
sc description SteelQR-Kiosk "QR 스캔 문서 관리 시스템"
sc start SteelQR-Kiosk

# 제거
sc stop SteelQR-Kiosk
sc delete SteelQR-Kiosk
```

### 방법 3: 작업 스케줄러 사용

1. `Win + R` → `taskschd.msc`
2. 작업 스케줄러 라이브러리 → 기본 작업 만들기
3. 이름: `SteelQR-Kiosk`
4. 트리거: **시스템 시작 시**
5. 동작: **프로그램 시작**
   - 프로그램: `C:\path\to\steel-qr.exe`
   - 인수: `--mode kiosk --port 8000`
   - 시작 위치: `C:\path\to`

---

## 🔥 방화벽 설정

Windows 방화벽에서 포트 열기:

```powershell
# 관리자 권한 PowerShell
New-NetFirewallRule -DisplayName "Steel QR Kiosk" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
New-NetFirewallRule -DisplayName "Steel QR Admin" -Direction Inbound -Protocol TCP -LocalPort 8100 -Action Allow
```

---

## 📊 다중 인스턴스 구성 (관리자 모드)

### 1. 인스턴스 레지스트리 생성

`instances.json`:

```json
{
  "version": 1,
  "instances": [
    {
      "id": "kiosk-1",
      "label": "스캔 키오스크 1",
      "baseUrl": "http://192.168.1.10:8000",
      "role": "kiosk",
      "auth": {
        "type": "basic",
        "username": "admin",
        "password": "1212"
      }
    },
    {
      "id": "kiosk-2",
      "label": "스캔 키오스크 2",
      "baseUrl": "http://192.168.1.11:8000",
      "role": "kiosk",
      "auth": {
        "type": "basic",
        "username": "admin",
        "password": "1212"
      }
    }
  ]
}
```

### 2. 관리자 서버 실행

```bash
steel-qr.exe --mode admin --port 8100 --registry file://C:\path\to\instances.json
```

---

## 🐛 트러블슈팅

### 실행파일이 시작되지 않음

1. **Visual C++ Redistributable 확인**
   - https://aka.ms/vs/17/release/vc_redist.x64.exe 설치

2. **Poppler 경로 확인**
   - 환경변수 PATH에 Poppler bin 폴더 추가

3. **로그 확인**
   ```bash
   steel-qr.exe --mode kiosk --port 8000 > output.log 2>&1
   ```

### 포트가 이미 사용 중

```bash
# 다른 포트 사용
steel-qr.exe --mode kiosk --port 8001
```

### QR 인식률이 낮음

`config.yaml`에서 QR 엔진 설정 조정:

```yaml
qr:
  adaptive_dpi: true
  fixed_dpi: 300
  dpi_candidates: [150, 200, 300, 400]
  engines:
    zbar:
      enabled: true
    zxing:
      enabled: true
    pyzbar_preproc:
      enabled: true
```

### 서비스가 시작되지 않음

1. **관리자 권한 확인**
2. **작업 폴더 경로 확인**
3. **config.yaml 존재 여부 확인**
4. **이벤트 뷰어**에서 오류 로그 확인
   - `Win + R` → `eventvwr.msc`
   - Windows 로그 → 애플리케이션

---

## 📝 업데이트

### 새 버전 배포

1. 기존 서비스 중지
2. `steel-qr.exe` 파일 교체
3. 서비스 재시작

```cmd
nssm stop SteelQR-Kiosk
copy /Y new-steel-qr.exe steel-qr.exe
nssm start SteelQR-Kiosk
```

---

## ⚠️ 주의사항

### 보안
- 기본 비밀번호(`1212`)를 반드시 변경하세요
- HTTPS를 사용하려면 리버스 프록시(nginx, IIS) 필요
- 방화벽에서 필요한 포트만 개방

### 성능
- SSD 사용 권장 (PDF 병합 성능)
- 최소 4GB RAM (다중 인스턴스는 8GB+)
- 동시 처리 파일 수: config.yaml의 `workers` 설정 조정

### 백업
- `data/` 폴더 정기 백업
- `config.yaml` 백업
- `instances.json` 백업 (관리자 모드)

---

## 📞 지원

문제 발생 시:
1. 로그 파일 확인 (`logs/` 폴더)
2. 이벤트 뷰어 확인
3. GitHub Issues: https://github.com/mandoo8872/steel

---

## 📄 라이선스

이 프로젝트는 내부용으로 개발되었습니다.

---

**버전:** 2.0.0  
**최종 수정:** 2025-10-10

