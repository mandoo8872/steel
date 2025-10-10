# 🔐 보안 확장성 가이드

## 개요

현재 시스템은 **최소 보안 기능**(BasicAuth + Rate Limit)으로 시작하되,  
향후 **JWT, SSO, RBAC, 서명/암호화** 등으로 확장 가능하도록 설계되었습니다.

---

## ✅ 구현된 4가지 확장 대비 사항

### 1️⃣ **AuthProvider 인터페이스**

#### 현재 구조
```python
# src/auth/provider.py
class AuthProvider(ABC):
    @abstractmethod
    async def verify(self, request: Request) -> Optional[AuthResult]
    
    @abstractmethod
    def get_provider_name(self) -> str
```

#### 확장 방법
- **BasicAuth** (현재 구현)
  ```python
  from src.auth import BasicAuthProvider
  provider = BasicAuthProvider({"password": "1212"})
  ```

- **JWT** (향후 구현)
  ```python
  class JWTAuthProvider(AuthProvider):
      async def verify(self, request: Request):
          token = extract_jwt(request)
          payload = jwt.decode(token, secret_key)
          return AuthResult(...)
  ```

- **SSO** (향후 구현)
  ```python
  class SSOAuthProvider(AuthProvider):
      async def verify(self, request: Request):
          session = check_sso_session(request)
          return AuthResult(...)
  ```

#### 교체 방법
```python
# 기존 코드 변경 없이 init_auth만 수정
from src.auth import init_auth

# Basic → JWT로 교체
init_auth(
    provider_type="jwt",
    config={"secret": "...", "algorithm": "HS256"}
)
```

---

### 2️⃣ **Request Context 구조화**

#### 인증 정보 저장
```python
# src/auth/__init__.py - get_current_user
async def get_current_user(request: Request) -> AuthResult:
    auth_result = await auth_provider.verify(request)
    
    # Request.state에 사용자 정보 저장 (RBAC 확장 대비)
    request.state.user = auth_result
    
    return auth_result
```

#### AuthResult 구조
```python
@dataclass
class AuthResult:
    authenticated: bool
    user_id: str
    username: str
    roles: list          # ["admin", "user", "viewer"]
    ip: str
    method: str          # "basic", "jwt", "sso"
    metadata: Dict       # 추가 메타데이터
```

#### RBAC 확장 예시
```python
# 역할 기반 권한 검증
from src.auth import require_role

@app.get("/admin/settings", dependencies=[Depends(require_role("admin"))])
async def admin_settings():
    return {"message": "관리자 전용 페이지"}

@app.get("/viewer/reports", dependencies=[Depends(require_role("viewer"))])
async def view_reports():
    return {"message": "조회 전용 페이지"}
```

---

### 3️⃣ **API 응답 서명 필드**

#### 표준 응답 스키마
```python
# src/api/response.py
class SecureResponse(BaseModel):
    success: bool
    data: Any
    message: str
    timestamp: str
    
    # 보안 확장 필드 (현재는 None)
    signature: Optional[str] = None      # HMAC/RSA 서명
    encrypted: bool = False              # 페이로드 암호화 여부
    metadata: Optional[Dict] = None
```

#### 현재 응답 예시
```json
{
  "success": true,
  "data": { "uptimeSec": 3600, "queue": {...} },
  "timestamp": "2025-10-10T12:00:00Z",
  "signature": null,
  "encrypted": false
}
```

#### 향후 서명 추가
```python
# HMAC 서명 추가 (API 스펙 변경 없음)
import hmac
import hashlib

def create_response(success, data, sign=True):
    response = SecureResponse(success=success, data=data)
    
    if sign:
        payload = json.dumps(response.data, sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        response.signature = signature  # 필드만 채워넣기
    
    return response
```

#### 클라이언트 검증
```python
# 원격 API 호출 시 서명 검증
response = requests.get("http://kiosk/api/status")
data = response.json()

if data['signature']:
    verify_signature(data['data'], data['signature'])
```

---

### 4️⃣ **레지스트리 auth 확장**

#### 현재 스키마
```json
{
  "instances": [
    {
      "id": "kiosk-01",
      "auth": {
        "type": "basic",
        "username": "admin",
        "password": "******"
      }
    }
  ]
}
```

#### JWT 확장 예시
```json
{
  "instances": [
    {
      "id": "kiosk-02",
      "auth": {
        "type": "jwt",
        "token": "eyJhbGc...",
        "refresh_token": "..."
      }
    }
  ]
}
```

#### 인증서 확장 예시
```json
{
  "instances": [
    {
      "id": "secure-kiosk",
      "auth": {
        "type": "cert",
        "cert_path": "/etc/ssl/client.crt",
        "key_path": "/etc/ssl/client.key"
      }
    }
  ]
}
```

#### InstanceAuth 구현
```python
# src/registry/manager.py
@dataclass
class InstanceAuth:
    type: str = "basic"  # basic, jwt, token, cert, sso
    
    # Basic
    username: str = ""
    password: str = ""
    
    # JWT
    token: str = ""
    refresh_token: str = ""
    
    # Certificate
    cert_path: str = ""
    key_path: str = ""
    
    def get_headers(self) -> Dict[str, str]:
        """인증 타입에 따른 헤더 자동 생성"""
        if self.type == "basic":
            return {"Authorization": f"Basic {base64_encode}"}
        elif self.type == "jwt":
            return {"Authorization": f"Bearer {self.token}"}
        # ... 타입별 처리
```

---

## 📊 확장 우선순위 (향후 로드맵)

| 우선순위 | 기능 | 난이도 | 예상 시간 |
|---------|------|--------|----------|
| P1 | RBAC (역할 기반 권한) | 낮음 | 1-2시간 |
| P2 | JWT 인증 | 중간 | 2-3시간 |
| P3 | API 응답 서명 (HMAC) | 낮음 | 1시간 |
| P4 | 감사 로그 확장 (IP, 권한) | 낮음 | 30분 |
| P5 | SSO 통합 | 높음 | 1-2일 |
| P6 | 페이로드 암호화 | 중간 | 2-4시간 |
| P7 | 인증서 기반 인증 | 중간 | 2-3시간 |

---

## 🔄 확장 시나리오

### 시나리오 1: JWT로 전환
```python
# 1. JWT Provider 구현 (src/auth/jwt_auth.py)
class JWTAuthProvider(AuthProvider):
    def __init__(self, config):
        self.secret = config["secret"]
        self.algorithm = config.get("algorithm", "HS256")
    
    async def verify(self, request: Request):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
        return AuthResult(
            authenticated=True,
            user_id=payload["sub"],
            username=payload["username"],
            roles=payload.get("roles", ["user"]),
            ip=request.client.host,
            method="jwt"
        )

# 2. Factory 등록
AuthProviderFactory.register("jwt", JWTAuthProvider)

# 3. 초기화 변경 (모드별)
init_auth(
    provider_type="jwt",
    config={"secret": "my-secret-key", "algorithm": "HS256"}
)
```

### 시나리오 2: RBAC 추가
```python
# 엔드포인트별 권한 설정
@app.get("/api/status", dependencies=[Depends(require_role("viewer"))])
@app.post("/api/command", dependencies=[Depends(require_role("admin"))])
@app.delete("/api/documents/{id}", dependencies=[Depends(require_role("admin"))])
```

### 시나리오 3: 서명 활성화
```python
# API 응답에 서명 추가
@app.get("/api/status")
async def get_status():
    data = {...}
    return create_response(success=True, data=data, sign=True)  # 서명 활성화
```

---

## 🛡️ 보안 체크리스트

현재 구현된 보안 기능:
- [x] BasicAuth (비밀번호 해싱)
- [x] Rate Limiting (5회/15분)
- [x] 감사 로그 (관리자 작업 기록)
- [x] 인증 인터페이스 (확장 가능)
- [x] Request Context (사용자 정보 저장)
- [x] API 응답 서명 필드 (슬롯 확보)
- [x] 레지스트리 auth 확장 (type 분기)

향후 추가 권장 사항:
- [ ] JWT 인증 구현
- [ ] RBAC (역할 기반 권한)
- [ ] API 응답 서명 (HMAC/RSA)
- [ ] TLS/SSL (HTTPS)
- [ ] IP 화이트리스트
- [ ] 2FA (이중 인증)
- [ ] 세션 관리 (타임아웃)

---

## 📚 참고 자료

- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
- **JWT Best Practices**: https://tools.ietf.org/html/rfc7519
- **OWASP API Security**: https://owasp.org/www-project-api-security/
- **Python Cryptography**: https://cryptography.io/en/latest/

---

**작성일**: 2025-10-10  
**작성자**: Steel QR Management System  
**버전**: 2.0.0

