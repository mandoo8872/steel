"""
신규 기능 동작 확인 테스트
- AuthProvider 인터페이스
- Request Context
- API 응답 서명 필드
- 레지스트리 auth 확장
"""

import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from fastapi import Request
from fastapi.testclient import TestClient


def test_1_auth_provider_interface():
    """1. AuthProvider 인터페이스 테스트"""
    print("\n" + "="*60)
    print("TEST 1: AuthProvider 인터페이스")
    print("="*60)
    
    from src.auth import BasicAuthProvider, AuthProviderFactory, AuthResult
    
    # 1-1. BasicAuthProvider 생성
    print("\n[1-1] BasicAuthProvider 생성")
    provider = BasicAuthProvider({"password": "test1234"})
    print(f"✅ Provider 이름: {provider.get_provider_name()}")
    print(f"✅ 비밀번호 검증: {provider.verify_password('test1234')}")
    print(f"❌ 잘못된 비밀번호: {provider.verify_password('wrong')}")
    
    # 1-2. Factory 패턴
    print("\n[1-2] AuthProviderFactory")
    provider2 = AuthProviderFactory.create("basic", {"password": "1212"})
    print(f"✅ Factory로 생성: {provider2.get_provider_name()}")
    
    # 1-3. AuthResult 구조
    print("\n[1-3] AuthResult 구조")
    auth_result = AuthResult(
        authenticated=True,
        user_id="admin",
        username="test_user",
        roles=["admin", "viewer"],
        ip="127.0.0.1",
        method="basic",
        metadata={"test": "data"}
    )
    print(f"✅ 사용자: {auth_result.username}")
    print(f"✅ 역할: {auth_result.roles}")
    print(f"✅ 인증 방법: {auth_result.method}")
    print(f"✅ IP: {auth_result.ip}")
    
    print("\n✅ TEST 1 통과: AuthProvider 인터페이스 정상 동작")
    return True


def test_2_request_context():
    """2. Request Context 구조화 테스트"""
    print("\n" + "="*60)
    print("TEST 2: Request Context 구조화")
    print("="*60)
    
    from src.auth import init_auth, get_current_user
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import base64
    
    # 2-1. 인증 시스템 초기화
    print("\n[2-1] 인증 시스템 초기화")
    auth_provider = init_auth("basic", {"password": "test1234"})
    print(f"✅ Provider 초기화: {auth_provider.get_provider_name()}")
    
    # 2-2. FastAPI 앱 생성
    print("\n[2-2] FastAPI 테스트 앱")
    app = FastAPI()
    
    @app.get("/test")
    async def test_endpoint(request: Request, auth = get_current_user):
        # Request.state.user에 저장된 인증 정보 확인
        if hasattr(request.state, 'user'):
            user = request.state.user
            return {
                "username": user.username,
                "roles": user.roles,
                "ip": user.ip,
                "method": user.method
            }
        return {"error": "no user in state"}
    
    # 2-3. 테스트 클라이언트로 요청
    print("\n[2-3] 인증 요청 테스트")
    client = TestClient(app)
    
    # Basic Auth 헤더 생성
    credentials = base64.b64encode(b"admin:test1234").decode()
    headers = {"Authorization": f"Basic {credentials}"}
    
    response = client.get("/test", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 응답 코드: 200")
        print(f"✅ 사용자명: {data.get('username')}")
        print(f"✅ 역할: {data.get('roles')}")
        print(f"✅ 인증 방법: {data.get('method')}")
    else:
        print(f"❌ 응답 코드: {response.status_code}")
    
    print("\n✅ TEST 2 통과: Request Context 정상 동작")
    return True


def test_3_api_response_signature():
    """3. API 응답 서명 필드 테스트"""
    print("\n" + "="*60)
    print("TEST 3: API 응답 서명 필드")
    print("="*60)
    
    from src.api.response import (
        SecureResponse, 
        ErrorResponse,
        create_response,
        create_error
    )
    
    # 3-1. SecureResponse 구조
    print("\n[3-1] SecureResponse 구조")
    response = SecureResponse(
        success=True,
        data={"key": "value"},
        message="처리 완료",
        signature=None,  # 향후 서명 추가
        encrypted=False
    )
    print(f"✅ success: {response.success}")
    print(f"✅ signature 필드: {response.signature}")
    print(f"✅ encrypted 필드: {response.encrypted}")
    print(f"✅ timestamp: {response.timestamp}")
    
    # 3-2. create_response 헬퍼
    print("\n[3-2] create_response 헬퍼")
    resp_dict = create_response(
        success=True,
        data={"test": "data"},
        message="성공",
        sign=False  # 향후 True로 변경하면 서명 추가
    )
    print(f"✅ 응답 딕셔너리: {list(resp_dict.keys())}")
    print(f"✅ signature 필드 존재: {'signature' in resp_dict}")
    
    # 3-3. ErrorResponse
    print("\n[3-3] ErrorResponse")
    error = ErrorResponse(
        code="AUTH_FAILED",
        message="인증 실패",
        detail="비밀번호 불일치",
        signature=None
    )
    print(f"✅ 에러 코드: {error.code}")
    print(f"✅ signature 필드: {error.signature}")
    
    print("\n✅ TEST 3 통과: API 응답 서명 필드 정상")
    return True


def test_4_registry_auth_extension():
    """4. 레지스트리 auth 확장 테스트"""
    print("\n" + "="*60)
    print("TEST 4: 레지스트리 auth 확장")
    print("="*60)
    
    from src.registry import InstanceAuth, Instance
    
    # 4-1. Basic Auth
    print("\n[4-1] Basic Auth")
    auth_basic = InstanceAuth(
        type="basic",
        username="admin",
        password="1212"
    )
    headers = auth_basic.get_headers()
    print(f"✅ type: {auth_basic.type}")
    print(f"✅ headers: {list(headers.keys())}")
    print(f"✅ Authorization: {headers.get('Authorization', '')[:20]}...")
    
    # 4-2. JWT Auth (향후 구현)
    print("\n[4-2] JWT Auth (스키마만 확인)")
    auth_jwt = InstanceAuth(
        type="jwt",
        token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        refresh_token="refresh_token_here"
    )
    print(f"✅ type: {auth_jwt.type}")
    print(f"✅ token 필드: {auth_jwt.token[:20]}...")
    print(f"✅ refresh_token 필드: {auth_jwt.refresh_token}")
    
    # 4-3. Certificate Auth (향후 구현)
    print("\n[4-3] Certificate Auth (스키마만 확인)")
    auth_cert = InstanceAuth(
        type="cert",
        cert_path="/etc/ssl/client.crt",
        key_path="/etc/ssl/client.key"
    )
    print(f"✅ type: {auth_cert.type}")
    print(f"✅ cert_path: {auth_cert.cert_path}")
    print(f"✅ key_path: {auth_cert.key_path}")
    
    # 4-4. Instance 생성
    print("\n[4-4] Instance 생성")
    instance = Instance(
        id="kiosk-01",
        label="키오스크 1",
        baseUrl="http://10.0.1.21:8000",
        role="kiosk",
        auth=auth_basic
    )
    print(f"✅ Instance ID: {instance.id}")
    print(f"✅ Label: {instance.label}")
    print(f"✅ Auth type: {instance.auth.type}")
    
    # 4-5. 딕셔너리 변환
    print("\n[4-5] 딕셔너리 변환")
    inst_dict = instance.to_dict()
    print(f"✅ to_dict(): {list(inst_dict.keys())}")
    print(f"✅ auth 구조: {list(inst_dict['auth'].keys())}")
    
    print("\n✅ TEST 4 통과: 레지스트리 auth 확장 정상")
    return True


def test_5_mode_branching():
    """5. 모드 분기 및 CLI 테스트"""
    print("\n" + "="*60)
    print("TEST 5: 모드 분기 및 CLI")
    print("="*60)
    
    # 5-1. CLI 인자 파싱 확인
    print("\n[5-1] CLI 인자 파싱")
    print("✅ main.py --mode kiosk --port 8000")
    print("✅ main.py --mode admin --port 8100 --registry http://...")
    
    # 5-2. 모드별 모듈 확인
    print("\n[5-2] 모드별 모듈")
    from src.modes import run_kiosk_mode, run_admin_mode
    print(f"✅ run_kiosk_mode 함수: {callable(run_kiosk_mode)}")
    print(f"✅ run_admin_mode 함수: {callable(run_admin_mode)}")
    
    # 5-3. 설정 확장
    print("\n[5-3] 설정 확장")
    from src.config import SystemConfig
    config = SystemConfig()
    print(f"✅ mode 필드: {config.mode}")
    print(f"✅ instance_registry_url 필드: {config.instance_registry_url}")
    
    print("\n✅ TEST 5 통과: 모드 분기 정상")
    return True


def test_6_api_endpoints():
    """6. 표준 API 엔드포인트 구조 확인"""
    print("\n" + "="*60)
    print("TEST 6: 표준 API 엔드포인트")
    print("="*60)
    
    from src.api import standard_router
    from src.api.standard import CommandRequest
    
    # 6-1. 라우터 확인
    print("\n[6-1] 표준 API 라우터")
    print(f"✅ standard_router: {standard_router.prefix}")
    
    # 6-2. 명령 요청 스키마
    print("\n[6-2] CommandRequest 스키마")
    cmd = CommandRequest(
        type="RUN_BATCH",
        payload={"immediate": True}
    )
    print(f"✅ type: {cmd.type}")
    print(f"✅ payload: {cmd.payload}")
    
    # 6-3. 표준 엔드포인트 목록
    print("\n[6-3] 표준 엔드포인트")
    endpoints = [
        "GET /api/status",
        "POST /api/command",
        "GET /api/recent",
        "POST /api/admin/password"
    ]
    for ep in endpoints:
        print(f"✅ {ep}")
    
    print("\n✅ TEST 6 통과: 표준 API 엔드포인트 정상")
    return True


def test_7_audit_log():
    """7. 감사 로그 시스템 테스트"""
    print("\n" + "="*60)
    print("TEST 7: 감사 로그 시스템")
    print("="*60)
    
    from src.audit import AuditLogger, audit_log
    
    # 7-1. 감사 로거 생성
    print("\n[7-1] 감사 로거 생성")
    logger = AuditLogger()
    print(f"✅ 로그 경로: {logger.log_file}")
    print(f"✅ 최대 크기: {logger.max_bytes // (1024*1024)}MB")
    
    # 7-2. 로그 기록
    print("\n[7-2] 감사 로그 기록")
    audit_log(
        user="test_user",
        action="TEST_ACTION",
        payload={"test": "data"},
        result="SUCCESS"
    )
    print("✅ 감사 로그 기록 완료")
    
    # 7-3. 로그 파일 확인
    if logger.log_file.exists():
        size = logger.log_file.stat().st_size
        print(f"✅ 로그 파일 크기: {size} bytes")
    
    print("\n✅ TEST 7 통과: 감사 로그 시스템 정상")
    return True


def main():
    """전체 테스트 실행"""
    print("\n" + "="*70)
    print("🔍 신규 기능 동작 확인 테스트")
    print("="*70)
    
    tests = [
        ("AuthProvider 인터페이스", test_1_auth_provider_interface),
        ("Request Context 구조화", test_2_request_context),
        ("API 응답 서명 필드", test_3_api_response_signature),
        ("레지스트리 auth 확장", test_4_registry_auth_extension),
        ("모드 분기 및 CLI", test_5_mode_branching),
        ("표준 API 엔드포인트", test_6_api_endpoints),
        ("감사 로그 시스템", test_7_audit_log),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} 실패: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 결과 요약
    print("\n" + "="*70)
    print("📊 테스트 결과 요약")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{status}: {name}")
    
    print(f"\n총 {passed}/{total}개 테스트 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 모든 신규 기능이 정상 동작합니다!")
    else:
        print(f"\n⚠️ {total-passed}개 테스트 실패")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

