"""
관리자 모드 전용 API 및 애플리케이션
중앙 관리자 대시보드
"""

from pathlib import Path
from typing import Dict, List, Any
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from loguru import logger

from ..auth import get_current_user
from ..audit import audit_log
from ..registry import RegistryManager, Instance, InstanceClient


def create_admin_app(config, registry_manager: RegistryManager) -> FastAPI:
    """
    관리자 모드 FastAPI 애플리케이션 생성
    
    Args:
        config: 설정 객체
        registry_manager: 레지스트리 관리자
        
    Returns:
        FastAPI 앱
    """
    app = FastAPI(title="Steel - 중앙 관리자", version="2.0.0")
    
    # 템플릿 설정
    templates = Jinja2Templates(directory="templates")
    
    # 정적 파일
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    # 전역 변수
    app.state.config = config
    app.state.registry = registry_manager
    
    # 시작 시간 기록
    import time
    app.state._start_time = time.time()
    
    # ===== HTML 페이지 =====
    
    @app.get("/logout", response_class=HTMLResponse)
    async def logout(request: Request):
        """로그아웃 - 자바스크립트로 인증 초기화"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>로그아웃 중...</title>
            <style>
                body {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    background: #2c3e50;
                }
                .logout-box {
                    text-align: center;
                    padding: 40px;
                    background: #34495e;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                    color: #ecf0f1;
                }
                .spinner {
                    border: 3px solid #4a5f7f;
                    border-top: 3px solid #5dade2;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 20px;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            </style>
        </head>
        <body>
            <div class="logout-box">
                <div class="spinner"></div>
                <h3>로그아웃 중...</h3>
                <p>잠시만 기다려주세요</p>
            </div>
            <script>
                // 잘못된 인증 정보로 요청하여 브라우저의 인증 캐시 초기화
                setTimeout(function() {
                    fetch('/', {
                        headers: {
                            'Authorization': 'Basic ' + btoa('logout:logout')
                        }
                    }).then(function() {
                        // 로그인 페이지로 리다이렉트
                        window.location.href = '/';
                    }).catch(function() {
                        // 실패해도 로그인 페이지로
                        window.location.href = '/';
                    });
                }, 500);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    @app.get("/", response_class=HTMLResponse)
    async def admin_dashboard(request: Request, username: str = Depends(get_current_user)):
        """중앙 관리자 대시보드"""
        return templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "config": config
        })
    
    @app.get("/instances", response_class=HTMLResponse)
    async def instances_page(request: Request, username: str = Depends(get_current_user)):
        """인스턴스 목록 페이지"""
        return templates.TemplateResponse("admin/instances.html", {
            "request": request,
            "config": config
        })
    
    @app.get("/registry", response_class=HTMLResponse)
    async def registry_editor(request: Request, username: str = Depends(get_current_user)):
        """레지스트리 편집 페이지"""
        return templates.TemplateResponse("admin/registry_editor.html", {
            "request": request,
            "config": config
        })
    
    # ===== API 엔드포인트 =====
    
    @app.get("/api/status")
    async def api_status(username: str = Depends(get_current_user)) -> Dict[str, Any]:
        """
        관리자 모드 상태 API
        (키오스크 모드와 동일한 형식으로 응답, 단 레지스트리 통계)
        """
        try:
            import time
            
            # 레지스트리 통계
            instances = registry_manager.list_instances()
            kiosk_count = sum(1 for inst in instances if inst.role == "kiosk")
            admin_count = sum(1 for inst in instances if inst.role == "admin")
            
            # 간단한 업타임 (앱 시작 시간 기준)
            uptime_sec = int(time.time() - getattr(app.state, '_start_time', time.time()))
            
            return {
                "uptimeSec": uptime_sec,
                "queue": {
                    "new": 0,
                    "pendingMerge": 0,
                    "pendingUpload": 0,
                    "uploaded": 0,
                    "error": 0,
                    "total": 0
                },
                "diskFreeMB": 0,
                "lastBatchAt": None,
                "version": "2.0.0",
                "mode": "admin",
                "registry": {
                    "totalInstances": len(instances),
                    "kioskInstances": kiosk_count,
                    "adminInstances": admin_count
                }
            }
        except Exception as e:
            logger.error(f"관리자 상태 조회 오류: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/admin/instances")
    async def get_instances(username: str = Depends(get_current_user)) -> List[Dict]:
        """
        인스턴스 레지스트리 조회
        
        Returns:
            인스턴스 목록
        """
        instances = registry_manager.list_instances()
        
        return [inst.to_dict() for inst in instances]
    
    @app.put("/api/admin/instances")
    async def update_instances(
        instances: List[Dict],
        target: str = "local",
        username: str = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """
        인스턴스 레지스트리 업데이트
        
        Args:
            instances: 인스턴스 목록
            target: 저장 대상 (local/remote)
        """
        try:
            # 기존 인스턴스 초기화
            registry_manager._instances.clear()
            
            # 새 인스턴스 추가
            for inst_data in instances:
                instance = Instance.from_dict(inst_data)
                registry_manager.add_instance(instance)
            
            # 저장
            success = registry_manager.save(target=target)
            
            if success:
                # 감사 로그
                audit_log(
                    user=username,
                    action="REGISTRY_UPDATE",
                    payload={"target": target, "count": len(instances)},
                    result="SUCCESS"
                )
                
                logger.info(f"레지스트리 업데이트: {len(instances)}개 인스턴스 ({target})")
                
                return {
                    "success": True,
                    "message": f"레지스트리가 {target}에 저장되었습니다",
                    "count": len(instances)
                }
            else:
                raise Exception(f"{target} 저장 실패")
        
        except Exception as e:
            logger.error(f"레지스트리 업데이트 실패: {e}")
            
            # 감사 로그 (실패)
            audit_log(
                user=username,
                action="REGISTRY_UPDATE",
                result="ERROR",
                detail=str(e)
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"레지스트리 업데이트 실패: {str(e)}"
            )
    
    @app.post("/api/admin/test-instance")
    async def test_instance_connection(
        instance_data: Dict[str, Any],
        username: str = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """
        인스턴스 연결 테스트 (프록시)
        
        Args:
            instance_data: 인스턴스 정보 (baseUrl, auth)
        """
        base_url = None
        try:
            import httpx
            
            base_url = instance_data.get('baseUrl', '').rstrip('/')
            auth = instance_data.get('auth', {})
            username_auth = auth.get('username', 'admin')
            password_auth = auth.get('password', '1212')
            
            if not base_url:
                return {
                    "success": False,
                    "message": "Base URL이 비어있습니다"
                }
            
            logger.info(f"인스턴스 테스트 시작: {base_url}")
            
            # httpx로 요청
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{base_url}/api/status",
                    auth=(username_auth, password_auth)
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"인스턴스 테스트 성공: {base_url}")
                    return {
                        "success": True,
                        "message": "연결 성공",
                        "status": data
                    }
                elif response.status_code == 401:
                    return {
                        "success": False,
                        "message": "인증 실패 (아이디 또는 비밀번호 오류)"
                    }
                elif response.status_code == 404:
                    return {
                        "success": False,
                        "message": "/api/status 엔드포인트를 찾을 수 없습니다"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"HTTP {response.status_code} 오류"
                    }
        
        except httpx.ConnectError as e:
            logger.warning(f"인스턴스 연결 실패: {base_url} - {e}")
            return {
                "success": False,
                "message": "서버에 연결할 수 없습니다 (연결 거부 또는 서버 중지)"
            }
        except httpx.TimeoutException as e:
            logger.warning(f"인스턴스 타임아웃: {base_url} - {e}")
            return {
                "success": False,
                "message": "연결 시간 초과 (5초) - 서버가 응답하지 않습니다"
            }
        except Exception as e:
            logger.error(f"인스턴스 테스트 오류: {base_url} - {e}")
            error_msg = str(e)
            if not error_msg:
                error_msg = "알 수 없는 오류"
            return {
                "success": False,
                "message": f"연결 실패: {error_msg}"
            }
    
    @app.get("/api/admin/instances/{instance_id}/status")
    async def get_instance_status(
        instance_id: str,
        username: str = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """
        특정 인스턴스의 상태 조회
        
        Args:
            instance_id: 인스턴스 ID
        """
        instance = registry_manager.get_instance(instance_id)
        
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"인스턴스를 찾을 수 없습니다: {instance_id}"
            )
        
        # 원격 클라이언트로 상태 조회
        client = InstanceClient(instance)
        health = client.get_health()
        
        # 인스턴스 기본 정보 추가
        health['instance'] = {
            'id': instance.id,
            'label': instance.label,
            'baseUrl': instance.baseUrl,
            'role': instance.role
        }
        
        return health
    
    @app.get("/api/admin/instances/health")
    async def get_all_instances_health(
        reload: bool = False,
        username: str = Depends(get_current_user)
    ) -> List[Dict]:
        """
        모든 인스턴스의 헬스체크
        
        Args:
            reload: 레지스트리 리로드 여부
        
        Returns:
            [
                {
                    "online": bool,
                    "instance_id": str,
                    "label": str,
                    "status": {...}
                }
            ]
        """
        # 레지스트리 리로드 요청 시
        if reload:
            logger.info("레지스트리 리로드 요청")
            registry_manager.load()
        
        instances = registry_manager.list_instances()
        
        health_list = []
        
        for instance in instances:
            client = InstanceClient(instance, timeout=5)
            health = client.get_health()
            health_list.append(health)
        
        return health_list
    
    @app.post("/api/admin/instances/{instance_id}/command")
    async def send_instance_command(
        instance_id: str,
        command_type: str,
        payload: Dict = None,
        username: str = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """
        인스턴스에 원격 명령 전송
        
        Args:
            instance_id: 대상 인스턴스 ID
            command_type: 명령 타입
            payload: 명령 페이로드
        """
        instance = registry_manager.get_instance(instance_id)
        
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"인스턴스를 찾을 수 없습니다: {instance_id}"
            )
        
        # 감사 로그
        audit_log(
            user=username,
            action="REMOTE_COMMAND",
            target_instance_id=instance_id,
            payload={"command_type": command_type, "payload": payload}
        )
        
        # 원격 명령 전송
        client = InstanceClient(instance)
        result = client.send_command(command_type, payload)
        
        if result:
            return result
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"인스턴스 연결 실패: {instance_id}"
            )
    
    @app.get("/api/admin/instances/{instance_id}/recent")
    async def get_instance_recent(
        instance_id: str,
        limit: int = 50,
        username: str = Depends(get_current_user)
    ) -> List[Dict]:
        """
        인스턴스의 최근 처리 내역 조회
        
        Args:
            instance_id: 인스턴스 ID
            limit: 최대 개수
        """
        instance = registry_manager.get_instance(instance_id)
        
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"인스턴스를 찾을 수 없습니다: {instance_id}"
            )
        
        # 원격 조회
        client = InstanceClient(instance)
        items = client.get_recent(limit)
        
        if items is not None:
            return items
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"인스턴스 연결 실패: {instance_id}"
            )
    
    @app.get("/api/admin/instances/export")
    async def export_registry(username: str = Depends(get_current_user)) -> JSONResponse:
        """
        레지스트리를 JSON 파일로 내보내기 (다운로드)
        """
        json_str = registry_manager.export_json()
        
        return JSONResponse(
            content=json_str,
            media_type="application/json",
            headers={
                "Content-Disposition": "attachment; filename=instances.json"
            }
        )
    
    @app.post("/api/admin/password")
    async def change_admin_password(
        old_password: str,
        new_password: str,
        username: str = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """관리자 비밀번호 변경"""
        from ..auth import auth_manager
        
        if not auth_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="인증 관리자가 초기화되지 않았습니다"
            )
        
        success = auth_manager.change_password(old_password, new_password)
        
        if success:
            audit_log(
                user=username,
                action="PASSWORD_CHANGE",
                result="SUCCESS"
            )
            
            # 설정 파일 업데이트
            config.system.admin_password = new_password
            
            return {
                "success": True,
                "message": "비밀번호가 변경되었습니다"
            }
        else:
            audit_log(
                user=username,
                action="PASSWORD_CHANGE",
                result="FAILURE"
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="기존 비밀번호가 일치하지 않습니다"
            )
    
    return app

