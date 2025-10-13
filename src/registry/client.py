"""
원격 인스턴스 클라이언트
다른 인스턴스의 API를 호출하는 클라이언트
"""

import requests
from typing import Dict, Any, Optional
from loguru import logger

from .manager import Instance


class InstanceClient:
    """원격 인스턴스 클라이언트"""
    
    def __init__(self, instance: Instance, timeout: int = 10):
        """
        Args:
            instance: 대상 인스턴스
            timeout: 요청 타임아웃 (초)
        """
        self.instance = instance
        self.timeout = timeout
        self.base_url = instance.baseUrl.rstrip('/')
        
        # 인증 정보
        self.auth = (instance.auth.username, instance.auth.password)
    
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        HTTP 요청 수행
        
        Args:
            method: HTTP 메서드
            endpoint: API 엔드포인트
            **kwargs: requests 추가 파라미터
            
        Returns:
            응답 JSON 또는 None
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                timeout=self.timeout,
                **kwargs
            )
            
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"[{self.instance.id}] 타임아웃: {url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"[{self.instance.id}] 연결 실패: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"[{self.instance.id}] HTTP 오류: {e.response.status_code} - {url}")
            return None
        except Exception as e:
            logger.error(f"[{self.instance.id}] 요청 오류: {e}")
            return None
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        인스턴스 상태 조회
        
        Returns:
            {
                "uptimeSec": int,
                "queue": {"new": 0, "pendingMerge": 0, ...},
                "diskFreeMB": int,
                "lastBatchAt": str,
                "version": str
            }
        """
        return self._request('GET', '/api/status')
    
    def send_command(
        self,
        command_type: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        원격 명령 실행
        
        Args:
            command_type: 명령 타입 (RUN_BATCH, PAUSE, RESUME 등)
            payload: 명령 페이로드
            
        Returns:
            실행 결과
        """
        data = {
            "type": command_type,
            "payload": payload or {}
        }
        
        return self._request('POST', '/api/command', json=data)
    
    def get_recent(self, limit: int = 50) -> Optional[list]:
        """
        최근 처리 내역 조회
        
        Args:
            limit: 최대 개수
            
        Returns:
            처리 내역 리스트
        """
        result = self._request('GET', f'/api/recent?limit={limit}')
        
        if result:
            return result.get('items', [])
        
        return None
    
    def change_password(
        self,
        old_password: str,
        new_password: str
    ) -> Optional[Dict[str, Any]]:
        """
        비밀번호 변경
        
        Args:
            old_password: 기존 비밀번호
            new_password: 새 비밀번호
            
        Returns:
            변경 결과
        """
        data = {
            "old_password": old_password,
            "new_password": new_password
        }
        
        return self._request('POST', '/api/admin/password', json=data)
    
    def ping(self) -> bool:
        """
        연결 테스트
        
        Returns:
            연결 가능 여부
        """
        result = self.get_status()
        return result is not None
    
    def get_health(self) -> Dict[str, Any]:
        """
        헬스체크 (연결 상태 + 기본 정보)
        
        Returns:
            {
                "online": bool,
                "instance_id": str,
                "label": str,
                "baseUrl": str,
                "role": str,
                "status": dict or None
            }
        """
        status = self.get_status()
        
        return {
            "online": status is not None,
            "instance_id": self.instance.id,
            "label": self.instance.label,
            "baseUrl": self.instance.baseUrl,
            "role": self.instance.role,
            "status": status
        }

