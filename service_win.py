"""
Windows 서비스 구현
"""
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time
import subprocess
from pathlib import Path

# 서비스 이름과 표시 이름
SERVICE_NAME = "QRScanService"
SERVICE_DISPLAY_NAME = "QR Scan Management Service"
SERVICE_DESCRIPTION = "QR 기반 인수증/상차증 스캔 관리 서비스"


class QRScanWindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME
    _svc_description_ = SERVICE_DESCRIPTION
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.process = None
        self.working_directory = Path(__file__).parent
        
    def SvcStop(self):
        """서비스 중지"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        
        # 프로세스 종료
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=30)
    
    def SvcDoRun(self):
        """서비스 실행"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        self.main()
    
    def main(self):
        """메인 실행 루프"""
        # Python 실행 파일 경로
        python_exe = sys.executable
        main_script = self.working_directory / "main.py"
        
        # 환경 변수 설정
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.working_directory)
        
        # 로그 디렉토리 생성
        log_dir = self.working_directory / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # 서비스 실행
        while True:
            if win32event.WaitForSingleObject(self.hWaitStop, 0) == win32event.WAIT_OBJECT_0:
                break
            
            try:
                # 메인 스크립트 실행
                self.process = subprocess.Popen(
                    [python_exe, str(main_script)],
                    cwd=str(self.working_directory),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # 프로세스 모니터링
                while True:
                    if win32event.WaitForSingleObject(self.hWaitStop, 1000) == win32event.WAIT_OBJECT_0:
                        break
                    
                    # 프로세스 상태 확인
                    if self.process.poll() is not None:
                        # 프로세스가 종료됨
                        servicemanager.LogMsg(
                            servicemanager.EVENTLOG_ERROR_TYPE,
                            servicemanager.PYS_SERVICE_STOPPED,
                            (self._svc_name_, 'Process terminated unexpectedly')
                        )
                        # 5초 대기 후 재시작
                        time.sleep(5)
                        break
                
            except Exception as e:
                servicemanager.LogMsg(
                    servicemanager.EVENTLOG_ERROR_TYPE,
                    servicemanager.PYS_SERVICE_STOPPED,
                    (self._svc_name_, str(e))
                )
                time.sleep(5)


def install_service():
    """서비스 설치"""
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(QRScanWindowsService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(QRScanWindowsService)


if __name__ == '__main__':
    install_service()
