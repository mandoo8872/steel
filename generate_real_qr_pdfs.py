#!/usr/bin/env python3
"""
실제 14자리 QR 코드가 포함된 테스트 PDF 생성
"""
import os
import sys
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PIL import Image
import tempfile
from pathlib import Path
import random

def create_qr_pdf(transport_no: str, output_path: str, qr_position: str = "center"):
    """14자리 운송번호 QR 코드가 포함된 PDF 생성"""
    
    # QR 코드 생성
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(transport_no)
    qr.make(fit=True)
    
    # QR 이미지 생성
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # 임시 파일로 저장
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
        qr_img.save(temp_file.name)
        temp_path = temp_file.name
    
    try:
        # PDF 생성
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        
        # 제목
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "Shipping Document")
        
        # 운송번호 텍스트
        c.setFont("Helvetica", 14)
        c.drawString(50, height - 80, f"Transport No: {transport_no}")
        
        # QR 코드 위치 설정
        qr_size = 150  # QR 코드 크기
        
        if qr_position == "center":
            qr_x = (width - qr_size) / 2
            qr_y = (height - qr_size) / 2
        elif qr_position == "top-right":
            qr_x = width - qr_size - 50
            qr_y = height - qr_size - 100
        elif qr_position == "bottom-left":
            qr_x = 50
            qr_y = 50
        else:  # center
            qr_x = (width - qr_size) / 2
            qr_y = (height - qr_size) / 2
        
        # QR 코드 삽입
        c.drawImage(temp_path, qr_x, qr_y, qr_size, qr_size)
        
        # 추가 정보
        c.setFont("Helvetica", 10)
        c.drawString(50, 100, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(50, 80, f"Document Type: Standard Shipping Label")
        c.drawString(50, 60, f"QR Position: {qr_position}")
        
        # 페이지 저장
        c.save()
        
        print(f"✓ Generated: {output_path} (QR: {transport_no})")
        
    finally:
        # 임시 파일 삭제
        os.unlink(temp_path)


def generate_test_qr_pdfs(output_dir: str, count: int = 10):
    """테스트용 QR PDF 생성"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    positions = ["center", "top-right", "bottom-left"]
    
    print(f"Generating {count} QR test PDFs...")
    
    for i in range(count):
        # 14자리 운송번호 생성
        transport_no = f"{random.randint(10000000000000, 99999999999999)}"
        
        # 파일명
        position = positions[i % len(positions)]
        filename = f"qr_test_{i+1:03d}_{transport_no}.pdf"
        filepath = output_path / filename
        
        # PDF 생성
        create_qr_pdf(transport_no, str(filepath), position)
    
    # 특수 케이스 추가
    # 1. 다중 페이지 PDF (같은 QR)
    transport_no = "12345678901234"
    multi_page_path = output_path / f"qr_multi_page_{transport_no}.pdf"
    
    c = canvas.Canvas(str(multi_page_path), pagesize=A4)
    for page in range(3):
        width, height = A4
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"Page {page + 1} of 3")
        c.drawString(50, height - 80, f"Transport No: {transport_no}")
        
        # QR 코드 생성
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(transport_no)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            qr_img.save(temp_file.name)
            temp_path = temp_file.name
        
        c.drawImage(temp_path, (width - 150) / 2, (height - 150) / 2, 150, 150)
        os.unlink(temp_path)
        
        if page < 2:
            c.showPage()
    
    c.save()
    print(f"✓ Generated: {multi_page_path} (Multi-page, QR: {transport_no})")
    
    # 2. 다중 QR PDF (여러 QR)
    multi_qr_path = output_path / "qr_multiple_codes.pdf"
    c = canvas.Canvas(str(multi_qr_path), pagesize=A4)
    width, height = A4
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Multiple QR Codes Document")
    
    qr_codes = ["11111111111111", "22222222222222", "33333333333333"]
    positions = [(100, 500), (250, 500), (400, 500)]
    
    for i, (qr_data, (x, y)) in enumerate(zip(qr_codes, positions)):
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            qr_img.save(temp_file.name)
            temp_path = temp_file.name
        
        c.drawImage(temp_path, x, y, 100, 100)
        c.setFont("Helvetica", 10)
        c.drawString(x, y - 20, f"QR {i+1}: {qr_data}")
        os.unlink(temp_path)
    
    c.save()
    print(f"✓ Generated: {multi_qr_path} (Multiple QRs)")
    
    print(f"\nTotal {count + 2} test PDFs generated in: {output_dir}")
    print("\nQR 엔진 테스트 준비 완료!")
    print("- 모든 PDF에 유효한 14자리 QR 코드 포함")
    print("- 다양한 위치 (center, top-right, bottom-left)")
    print("- 특수 케이스: 다중 페이지, 다중 QR")


if __name__ == "__main__":
    from datetime import datetime
    
    if len(sys.argv) > 1:
        output_dir = sys.argv[1]
    else:
        output_dir = "data/scanner_output"
    
    if len(sys.argv) > 2:
        count = int(sys.argv[2])
    else:
        count = 10
    
    generate_test_qr_pdfs(output_dir, count)
