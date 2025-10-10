# 다중 인스턴스 원격 관리 시스템 아키텍처

## 개요
파일 감시/QR 처리/병합/업로드 자동화 SW에 대한 중앙 집중식 원격 관리 시스템

## 핵심 요구사항
- **A안 (사내 VPN/터널)** 원격 운영
- **다수 인스턴스** (키오스크/관리자 PC) 선택·제어
- **Windows 단일 실행파일** (app.exe) 배포
- **두 가지 모드**: kiosk (처리 엔진) / admin (중앙 관리)

## 시스템 구성

### 1. 앱 모드 분기
```
app.exe --mode=kiosk   → 파일 처리 엔진 + 로컬 관리 UI
app.exe --mode=admin   → 중앙 관리자 대시보드 (원격 인스턴스 제어)
```

### 2. 인스턴스 레지스트리
**중앙 저장소**: `instances.json` (HTTP URL 또는 SMB/NAS)
**로컬 오버라이드**: `instances.local.json` (우선순위 높음)

스키마:
```json
{
  "version": 1,
  "instances": [
    {
      "id": "kiosk-01",
      "label": "키오스크1",
      "baseUrl": "http://10.0.1.21:8000",
      "auth": {"type": "basic", "username": "admin", "password": "******"},
      "role": "kiosk"
    }
  ]
}
```

### 3. 인증/권한
- **BasicAuth** 단일 비밀번호
- 로그인 실패 5회 → 15분 잠금
- 관리자 UI에서 비밀번호 변경 가능

### 4. 표준 API 엔드포인트
모든 인스턴스 공통:
- `GET /api/status` - 상태 조회
- `POST /api/command` - 명령 실행
- `GET /api/recent` - 최근 처리 내역
- `POST /api/admin/password` - 비밀번호 변경
- `GET/PUT /api/admin/instances` - 레지스트리 관리

## 디렉토리 구조
```
steel/
├── main.py                    # 엔트리포인트 (모드 분기)
├── src/
│   ├── modes/
│   │   ├── __init__.py
│   │   ├── kiosk.py          # 키오스크 모드
│   │   └── admin.py          # 관리자 모드
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── manager.py        # 레지스트리 관리
│   │   └── client.py         # 원격 인스턴스 클라이언트
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── basic_auth.py     # BasicAuth 구현
│   │   └── rate_limit.py     # 레이트 리밋
│   ├── api/
│   │   ├── __init__.py
│   │   ├── standard.py       # 표준 API
│   │   └── admin_api.py      # 관리자 API
│   └── audit/
│       ├── __init__.py
│       └── logger.py         # 감사 로그
├── templates/
│   ├── admin/                # 중앙 관리자 UI
│   │   ├── dashboard.html
│   │   ├── instances.html
│   │   └── registry_editor.html
│   └── common/
│       └── instance_selector.html
├── static/
│   └── css/
│       └── admin.css
└── scripts/
    ├── build.bat             # PyInstaller 빌드
    └── install_service.bat   # Windows 서비스 등록
```

## UI 원칙
- ❌ 아이콘 사용 금지
- ❌ 큰 글씨 사용 금지
- ✅ **Bold만 허용** (강조용)

## 빌드/배포
```bash
# 빌드
pyinstaller --name app --onefile --noconsole main.py

# 키오스크 설치
app.exe --mode=kiosk --port=8000

# 관리자 PC
app.exe --mode=admin --port=8100 --registry=https://intranet/instances.json

# Windows 서비스 등록
sc create kiosksvc binPath= "C:\path\app.exe --mode=kiosk --port=8000" start= auto
```

## 테스트 시나리오
1. ✅ 3대 키오스크 /api/status 안정성
2. ✅ 중앙 관리자에서 인스턴스 전환
3. ✅ 레지스트리 편집/저장/공유
4. ✅ 비밀번호 변경 즉시 반영
5. ✅ 로그인 실패 5회 잠금
6. ✅ exe 오프라인 동작
7. ✅ 서비스 크래시 자동 재시작
