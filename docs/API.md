# API 문서

## 인증

모든 API 엔드포인트는 Basic Authentication을 사용합니다.

- Username: 임의 (무시됨)
- Password: config.yaml의 admin_password (기본: 1212)

## 엔드포인트

### 웹 페이지

#### GET /
대시보드 페이지
- 전체 통계 표시
- 최근 처리 문서 목록
- 시스템 설정 요약

#### GET /documents
문서 목록 페이지
- Query Parameters:
  - `status`: 상태 필터 (PENDING, MERGED, UPLOADED, ERROR)
  - `limit`: 표시할 문서 수 (기본: 100)

#### GET /errors
오류 관리 페이지
- 오류 상태 문서 목록
- 오류 폴더 파일 목록
- 재처리 기능

#### GET /settings
설정 페이지
- 시스템 설정 표시 및 수정

#### GET /logs
처리 로그 페이지
- Query Parameters:
  - `limit`: 표시할 로그 수 (기본: 200)

### REST API

#### GET /api/stats
통계 정보 조회

**응답 예시:**
```json
{
  "today": {
    "scanned": 10,
    "uploaded": 8,
    "errors": 2
  },
  "total": {
    "documents": 150,
    "pending": 5,
    "merged": 20,
    "uploaded": 120,
    "error": 5
  },
  "queue": {
    "upload": 3,
    "retry": 1
  }
}
```

#### GET /api/recent
최근 문서 조회

**Query Parameters:**
- `limit`: 조회할 문서 수 (기본: 10)

**응답 예시:**
```json
[
  {
    "id": 1,
    "transport_no": "20250929000001",
    "status": "UPLOADED",
    "created_at": "2025-09-29T10:30:00",
    "error_message": null
  }
]
```

#### POST /settings
설정 업데이트

**요청 본문 (Form Data):**
- `log_level`: DEBUG | INFO | WARNING | ERROR
- `worker_count`: 1-10
- `scanner_output`: 스캐너 출력 경로
- `data_root`: 데이터 저장 경로
- 기타 설정 필드들

**응답:**
```json
{
  "success": true,
  "message": "설정이 저장되었습니다."
}
```

#### POST /reprocess/{file_path}
오류 파일 재처리

**경로 파라미터:**
- `file_path`: 재처리할 파일 경로

**요청 본문 (Form Data):**
- `transport_no`: 운송번호 (14자리)

**응답:**
```json
{
  "success": true,
  "message": "재처리가 시작되었습니다."
}
```

#### POST /batch/process
강제 배치 처리 실행

**응답:**
```json
{
  "success": true,
  "message": "배치 처리가 시작되었습니다."
}
```

## 업로드 API (외부 서버용)

시스템이 파일을 업로드할 때 사용하는 외부 API 규격입니다.

### POST {upload.http.endpoint}

**헤더:**
- `Authorization`: Bearer {token}
- `X-Idempotency-Key`: {transport_no}-{file_hash}
- `X-Transport-No`: 운송번호
- `X-File-Hash`: 파일 SHA1 해시

**본문:**
- Multipart/form-data
- `file`: PDF 파일

**성공 응답:**
- Status: 200 OK
- Body: JSON 또는 텍스트

**중복 응답 (멱등성):**
- Status: 409 Conflict
- Body: 오류 메시지

## 웹소켓 (계획)

실시간 업데이트를 위한 웹소켓 엔드포인트 (향후 구현 예정)

### WS /ws
- 실시간 문서 처리 상태
- 오류 알림
- 통계 업데이트

## 오류 코드

| 코드 | 설명 |
|------|------|
| 400 | 잘못된 요청 (파라미터 오류) |
| 401 | 인증 실패 |
| 404 | 리소스를 찾을 수 없음 |
| 409 | 충돌 (중복 업로드 등) |
| 500 | 서버 내부 오류 |

## 제한사항

- API 호출 제한: 없음 (내부용)
- 파일 크기 제한: config.yaml의 max_file_size 설정
- 동시 연결 제한: worker_count 설정에 따름

## 사용 예시

### cURL로 통계 조회
```bash
curl -u :1212 http://localhost:8000/api/stats
```

### Python으로 재처리 요청
```python
import requests
from requests.auth import HTTPBasicAuth

response = requests.post(
    'http://localhost:8000/reprocess/path/to/file.pdf',
    auth=HTTPBasicAuth('', '1212'),
    data={'transport_no': '20250929000001'}
)
print(response.json())
```

### JavaScript로 배치 실행
```javascript
fetch('/batch/process', {
    method: 'POST',
    headers: {
        'Authorization': 'Basic ' + btoa(':1212')
    }
})
.then(response => response.json())
.then(data => console.log(data));
```
