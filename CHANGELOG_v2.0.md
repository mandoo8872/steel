# 🚀 Steel QR Management System v2.0 변경사항

## 📅 릴리스 날짜: 2025-10-10

---

## 🎯 주요 변경사항

### 1️⃣ **다중 인스턴스 원격 관리 시스템**
- **Kiosk 모드**: 파일 감시/처리 엔진 + 로컬 관리 UI
- **Admin 모드**: 중앙 관리자 대시보드 (다중 인스턴스 집계/제어)
- **CLI 인자**: `--mode kiosk|admin --port 8000 --registry http://...`

### 2️⃣ **보안 확장성 대비 아키텍처**
- **AuthProvider 인터페이스**: Basic → JWT/SSO 교체 가능
- **Request Context**: `request.state.user`에 인증 정보 저장 (RBAC 대비)
- **API 응답 서명**: `signature` 필드 슬롯 확보 (HMAC/RSA 추가 가능)
- **레지스트리 auth**: `type` 필드로 Basic/JWT/Token/Cert/SSO 분기

### 3️⃣ **인증 & 권한 시스템**
- BasicAuth Provider 구현
- Rate Limiting (5회/15분 잠금)
- 감사 로그 (50MB 롤링)
- 비밀번호 변경 API

### 4️⃣ **표준 API 엔드포인트**
- `GET /api/status` - 인스턴스 상태 조회
- `POST /api/command` - 원격 명령 실행
- `GET /api/recent` - 최근 처리 내역
- `POST /api/admin/password` - 비밀번호 변경
- `GET/PUT /api/admin/instances` - 레지스트리 관리

---

## 📦 신규 모듈 (2,314 라인)

### 인증 시스템 (`src/auth/`)
- **`provider.py`** (139 lines): AuthProvider 인터페이스
  - `AuthProvider` 추상 클래스
  - `AuthResult` 표준 구조
  - `AuthProviderFactory` (basic/jwt/sso/firebase)

- **`basic_auth.py`** (186 lines): BasicAuth 구현
  - `BasicAuthProvider` (AuthProvider 구현)
  - SHA256 비밀번호 해싱
  - Rate Limit 통합

- **`rate_limit.py`** (81 lines): 레이트 리밋
  - 5회 실패 → 15분 잠금
  - IP 기반 추적

- **`__init__.py`** (106 lines): 통합 인터페이스
  - `get_current_user` Dependency
  - `require_role` (RBAC 대비)
  - `init_auth` 초기화

### API 시스템 (`src/api/`)
- **`standard.py`** (277 lines): 표준 API
  - 상태 조회, 원격 명령, 최근 내역
  - psutil 통합 (디스크/메모리)

- **`admin_api.py`** (319 lines): 관리자 API
  - 레지스트리 편집, 헬스체크
  - 원격 명령 전송
  - 인스턴스 전환

- **`response.py`** (213 lines): 표준 응답
  - `SecureResponse` (signature/encrypted 필드)
  - `ErrorResponse`
  - `create_response` 헬퍼

### 레지스트리 (`src/registry/`)
- **`manager.py`** (282 lines): 레지스트리 관리
  - `InstanceAuth` (basic/jwt/token/cert/sso)
  - `Instance` 정의
  - 중앙/로컬 병합 로드

- **`client.py`** (194 lines): 원격 클라이언트
  - HTTP 헬스체크
  - 원격 명령 전송
  - 인증 헤더 자동 생성

### 감사 로그 (`src/audit/`)
- **`logger.py`** (95 lines): 감사 로거
  - 관리자 작업 기록
  - 50MB 롤링, 30일 보관
  - payload 해시 (민감 정보 보호)

### 모드 분기 (`src/modes/`)
- **`kiosk.py`** (90 lines): 키오스크 모드
  - 파일 감시/처리 엔진
  - 로컬 관리 UI

- **`admin.py`** (104 lines): 관리자 모드
  - 중앙 대시보드
  - 다중 인스턴스 제어

---

## 🔄 수정된 파일

### `main.py`
- CLI 인자 파싱 (`argparse`)
- 모드 분기 (kiosk/admin)
- 설정 파일 검증

**Before:**
```python
def main():
    service = QRScanService()
    asyncio.run(service.start())
```

**After:**
```python
def main():
    args = parse_args()
    if args.mode == 'kiosk':
        run_kiosk_mode(...)
    elif args.mode == 'admin':
        run_admin_mode(...)
```

### `src/config.py`
- `SystemConfig`에 `mode`, `instance_registry_url` 추가

**추가된 필드:**
```python
@dataclass
class SystemConfig:
    mode: str = "kiosk"  # kiosk, admin
    instance_registry_url: str = ""  # 중앙 레지스트리 URL
```

---

## 📚 신규 문서

### `ARCHITECTURE.md`
- 전체 시스템 아키텍처
- 디렉토리 구조
- 주요 컴포넌트 설명
- 데이터 흐름도

### `docs/SECURITY_EXTENSIBILITY.md`
- 보안 확장성 가이드
- AuthProvider 인터페이스 사용법
- Request Context RBAC 예시
- API 서명 추가 방법
- 레지스트리 auth 확장 예시
- 확장 시나리오 (JWT, SSO, HMAC)

---

## 🧪 테스트 결과

### `tests/test_new_features.py`
- **7개 테스트, 100% 통과** ✅

| 테스트 | 상태 | 설명 |
|--------|------|------|
| AuthProvider 인터페이스 | ✅ | Factory 패턴, AuthResult 구조 |
| Request Context 구조화 | ✅ | request.state.user 저장 |
| API 응답 서명 필드 | ✅ | signature, encrypted 필드 |
| 레지스트리 auth 확장 | ✅ | type 분기, get_headers() |
| 모드 분기 및 CLI | ✅ | kiosk/admin 모드 |
| 표준 API 엔드포인트 | ✅ | /api/status, /api/command |
| 감사 로그 시스템 | ✅ | 로그 기록, 롤링 |

---

## 📊 통계

### 코드 추가
- **신규 모듈**: 15개 파일
- **신규 라인 수**: 2,314 lines
- **수정 파일**: 2개 (`main.py`, `src/config.py`)

### 의존성 추가
- `psutil` - 시스템 리소스 모니터링
- `requests` - HTTP 클라이언트

---

## 🔄 하위 호환성

### 기존 기능 유지
- ✅ QR 스캔/인식 (ZBar, ZXing, Pyzbar)
- ✅ 파일 감시/병합/업로드
- ✅ 웹 관리자 UI
- ✅ PDF 처리 (병합, 중복 제거)
- ✅ 에러 재처리

### 기존 코드 변경 없음
- `src/processor.py` - 파일 처리 로직 그대로
- `src/web_app.py` - 기존 엔드포인트 유지
- `templates/` - 기존 UI 템플릿 유지

### 기본 모드
- CLI 인자 없이 실행 시 **kiosk 모드** (기존 동작과 동일)

---

## 🚀 사용 예시

### 키오스크 모드 (기존과 동일)
```bash
python main.py
# 또는
python main.py --mode kiosk --port 8000
```

### 관리자 모드 (신규)
```bash
python main.py --mode admin --port 8100 --registry http://intranet/instances.json
```

### Windows 서비스 등록
```cmd
sc create kiosksvc binPath= "C:\app.exe --mode kiosk --port 8000" start= auto
```

---

## 🔜 다음 단계 (v2.1 계획)

1. **UI 구현** (40% 남음)
   - [ ] 인스턴스 선택 바
   - [ ] 중앙 관리자 대시보드
   - [ ] 레지스트리 편집기

2. **빌드/배포**
   - [ ] PyInstaller 단일 바이너리
   - [ ] Windows 서비스 스크립트

3. **보안 확장** (향후)
   - [ ] JWT Provider 구현
   - [ ] RBAC (역할 기반 권한)
   - [ ] API 응답 서명 (HMAC)

---

## 📝 마이그레이션 가이드

### v1.x → v2.0

#### 1. 설정 파일 업데이트
```yaml
# config.yaml에 추가
system:
  mode: kiosk  # 또는 admin
  instance_registry_url: ""  # 선택사항
```

#### 2. 의존성 설치
```bash
pip install psutil requests
```

#### 3. 기존 방식 유지 (변경 불필요)
```bash
# 기존 명령 그대로 사용 가능
python main.py
```

#### 4. 새 기능 활용 (선택)
```bash
# 관리자 모드로 실행
python main.py --mode admin --port 8100
```

---

## 🐛 알려진 이슈

- ✅ 모두 해결됨 (7/7 테스트 통과)

---

## 👥 기여자

- **Steel Dev Team**
- 보안 확장성 설계: 사용자 요구사항 반영

---

## 📞 지원

- GitHub Issues: https://github.com/mandoo8872/steel/issues
- 문서: `docs/` 디렉토리

---

**작성일**: 2025-10-10  
**버전**: 2.0.0  
**빌드**: Stable

