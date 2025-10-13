"""
데이터베이스 모델 정의
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

Base = declarative_base()


class ProcessStatus(str, Enum):
    """처리 상태"""
    PENDING = "PENDING"        # 대기중
    PROCESSING = "PROCESSING"  # 처리중
    MERGED = "MERGED"         # 병합완료
    UPLOADING = "UPLOADING"   # 업로드중
    UPLOADED = "UPLOADED"     # 업로드완료
    ERROR = "ERROR"           # 오류
    RETRY = "RETRY"           # 재시도대기


class ScanDocument(Base):
    """스캔 문서 정보"""
    __tablename__ = "scan_documents"
    
    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    transport_no = Column(String(14))  # 운송번호 (QR에서 추출)
    status = Column(String(20), default=ProcessStatus.PENDING)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    file_hash = Column(String(64))  # 파일 해시값
    page_count = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    uploaded_at = Column(DateTime)
    last_retry_at = Column(DateTime)
    
    # QR 관련
    qr_count = Column(Integer, default=0)  # 검출된 QR 개수
    qr_values = Column(Text)  # 검출된 모든 QR 값 (JSON)
    manual_transport_no = Column(String(14))  # 수동 지정 운송번호
    
    # 병합 관련
    is_merged = Column(Boolean, default=False)
    merged_file_path = Column(String(500))
    merge_group_id = Column(String(14))  # 병합 그룹 (운송번호)
    
    def __repr__(self):
        return f"<ScanDocument(id={self.id}, transport_no={self.transport_no}, status={self.status})>"


class ProcessLog(Base):
    """처리 로그"""
    __tablename__ = "process_logs"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer)
    action = Column(String(50))  # SCAN, QR_DETECT, MERGE, UPLOAD, ERROR
    status = Column(String(20))  # SUCCESS, FAILED
    message = Column(Text)
    details = Column(Text)  # JSON 형식의 상세 정보
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ProcessLog(id={self.id}, action={self.action}, status={self.status})>"


class UploadQueue(Base):
    """업로드 큐"""
    __tablename__ = "upload_queue"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer)
    file_path = Column(String(500))
    transport_no = Column(String(14))
    upload_type = Column(String(10))  # NAS, HTTP
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<UploadQueue(id={self.id}, transport_no={self.transport_no}, retry_count={self.retry_count})>"


class SystemStatus(Base):
    """시스템 상태"""
    __tablename__ = "system_status"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(50), unique=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# 데이터베이스 초기화
def init_database(db_path: Path):
    """데이터베이스 초기화"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """세션 생성"""
    Session = sessionmaker(bind=engine)
    return Session()
