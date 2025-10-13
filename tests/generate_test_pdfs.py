"""
테스트용 PDF 파일 생성 스크립트
"""
import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_qr_pdf(transport_no: str, output_path: Path, page_count: int = 1):
    """QR 코드가 포함된 PDF 생성"""
    # QR 코드 생성
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(transport_no)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # 임시 이미지 파일로 저장
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        qr_img.save(tmp.name)
        qr_img_path = tmp.name
    
    # PDF 생성
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    
    for page_num in range(page_count):
        # 제목
        c.setFont("Helvetica-Bold", 20)
        c.drawString(100, height - 100, f"Transport Document - Page {page_num + 1}")
        
        # QR 코드 삽입
        c.drawImage(qr_img_path, 100, height - 300, width=200, height=200)
        
        # 운송번호 텍스트
        c.setFont("Helvetica", 14)
        c.drawString(100, height - 350, f"Transport No: {transport_no}")
        
        # 페이지 정보
        c.setFont("Helvetica", 10)
        c.drawString(100, height - 400, f"Page {page_num + 1} of {page_count}")
        
        if page_num < page_count - 1:
            c.showPage()
    
    c.save()
    
    # 임시 파일 삭제
    Path(qr_img_path).unlink()


def create_multi_qr_pdf(transport_nos: list, output_path: Path):
    """여러 QR 코드가 포함된 PDF 생성"""
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    
    # 제목
    c.setFont("Helvetica-Bold", 20)
    c.drawString(100, height - 100, "Multiple QR Codes Document")
    
    # 여러 QR 코드 생성
    y_position = height - 200
    for i, transport_no in enumerate(transport_nos):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr.add_data(transport_no)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            qr_img.save(tmp.name)
            c.drawImage(tmp.name, 100 + (i * 150), y_position, width=100, height=100)
            Path(tmp.name).unlink()
        
        c.setFont("Helvetica", 10)
        c.drawString(100 + (i * 150), y_position - 20, transport_no)
    
    c.save()


def create_no_qr_pdf(output_path: Path):
    """QR 코드가 없는 PDF 생성"""
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    
    # 제목
    c.setFont("Helvetica-Bold", 20)
    c.drawString(100, height - 100, "Document Without QR Code")
    
    # 내용
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 150, "This document does not contain any QR code.")
    c.drawString(100, height - 180, "It should be moved to error folder.")
    
    # 1D 바코드 시뮬레이션 (선으로 표현)
    c.setLineWidth(1)
    for i in range(50):
        if i % 2 == 0:
            c.line(100 + i * 3, height - 250, 100 + i * 3, height - 300)
    
    c.save()


def generate_all_test_pdfs():
    """모든 테스트 PDF 생성"""
    test_dir = Path(__file__).parent / "test_pdfs"
    test_dir.mkdir(exist_ok=True)
    
    print("테스트 PDF 생성 중...")
    
    # 1. 정상 QR 코드 PDF (단일 페이지)
    create_qr_pdf("20250929000001", test_dir / "normal_single_page.pdf", 1)
    print("✓ normal_single_page.pdf")
    
    # 2. 정상 QR 코드 PDF (여러 페이지)
    create_qr_pdf("20250929000002", test_dir / "normal_multi_page.pdf", 3)
    print("✓ normal_multi_page.pdf")
    
    # 3. 다중 QR 코드 PDF
    create_multi_qr_pdf(
        ["20250929000003", "20250929000004"],
        test_dir / "multiple_qr.pdf"
    )
    print("✓ multiple_qr.pdf")
    
    # 4. QR 코드 없는 PDF
    create_no_qr_pdf(test_dir / "no_qr.pdf")
    print("✓ no_qr.pdf")
    
    # 5. 잘못된 QR 코드 PDF (13자리)
    create_qr_pdf("2025092900000", test_dir / "invalid_qr_13.pdf", 1)
    print("✓ invalid_qr_13.pdf")
    
    # 6. 잘못된 QR 코드 PDF (문자 포함)
    create_qr_pdf("2025092900000A", test_dir / "invalid_qr_alpha.pdf", 1)
    print("✓ invalid_qr_alpha.pdf")
    
    # 7. 동일 운송번호 여러 파일 (병합 테스트용)
    for i in range(3):
        create_qr_pdf("20250929000005", test_dir / f"merge_test_{i+1}.pdf", 1)
    print("✓ merge_test_1.pdf, merge_test_2.pdf, merge_test_3.pdf")
    
    print(f"\n모든 테스트 PDF가 생성되었습니다: {test_dir}")


if __name__ == "__main__":
    # reportlab 설치 확인
    try:
        import reportlab
    except ImportError:
        print("reportlab이 설치되어 있지 않습니다.")
        print("pip install reportlab qrcode[pil] 명령으로 설치해주세요.")
        sys.exit(1)
    
    generate_all_test_pdfs()
