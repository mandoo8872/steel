"""
다중 QR 엔진 테스트용 샘플 PDF 생성
다양한 QR 코드 유형 (정상, 기울어진, 흐린, 대비 낮은) 생성
"""
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import numpy as np
import cv2
import tempfile
import random
import math


def create_normal_qr(data: str, size: int = 200) -> Image.Image:
    """정상적인 QR 코드 생성"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    return qr_img.resize((size, size), Image.LANCZOS)


def create_rotated_qr(data: str, angle: float, size: int = 200) -> Image.Image:
    """기울어진 QR 코드 생성"""
    qr_img = create_normal_qr(data, size)
    
    # 회전을 위해 더 큰 캔버스 생성
    canvas_size = int(size * 1.5)
    canvas_img = Image.new('RGB', (canvas_size, canvas_size), 'white')
    
    # QR 코드를 캔버스 중앙에 배치
    offset = (canvas_size - size) // 2
    canvas_img.paste(qr_img, (offset, offset))
    
    # 회전 적용
    rotated = canvas_img.rotate(angle, expand=False, fillcolor='white')
    
    # 원래 크기로 자르기
    crop_offset = (canvas_size - size) // 2
    cropped = rotated.crop((crop_offset, crop_offset, crop_offset + size, crop_offset + size))
    
    return cropped


def create_blurred_qr(data: str, blur_radius: float = 1.5, size: int = 200) -> Image.Image:
    """흐린 QR 코드 생성"""
    qr_img = create_normal_qr(data, size)
    
    # RGB 모드로 변환 (필터 적용을 위해)
    if qr_img.mode != 'RGB':
        qr_img = qr_img.convert('RGB')
    
    # 가우시안 블러 적용
    blurred = qr_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    return blurred


def create_low_contrast_qr(data: str, contrast_factor: float = 0.3, size: int = 200) -> Image.Image:
    """대비가 낮은 QR 코드 생성"""
    qr_img = create_normal_qr(data, size)
    
    # RGB 모드로 변환
    if qr_img.mode != 'RGB':
        qr_img = qr_img.convert('RGB')
    
    # PIL을 numpy 배열로 변환
    img_array = np.array(qr_img)
    
    # 대비 조정 (0=회색, 1=원본)
    # 회색값 (128)에서 원본값으로의 보간
    gray_value = 128
    adjusted = gray_value + (img_array - gray_value) * contrast_factor
    adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)
    
    return Image.fromarray(adjusted)


def create_noisy_qr(data: str, noise_level: float = 0.1, size: int = 200) -> Image.Image:
    """노이즈가 있는 QR 코드 생성"""
    qr_img = create_normal_qr(data, size)
    
    # RGB 모드로 변환
    if qr_img.mode != 'RGB':
        qr_img = qr_img.convert('RGB')
    
    # PIL을 numpy 배열로 변환
    img_array = np.array(qr_img)
    
    # 랜덤 노이즈 추가
    noise = np.random.normal(0, noise_level * 255, img_array.shape)
    noisy = img_array + noise
    noisy = np.clip(noisy, 0, 255).astype(np.uint8)
    
    return Image.fromarray(noisy)


def create_damaged_qr(data: str, damage_level: float = 0.05, size: int = 200) -> Image.Image:
    """손상된 QR 코드 생성 (일부 영역을 흰색으로)"""
    qr_img = create_normal_qr(data, size)
    
    # RGB 모드로 변환
    if qr_img.mode != 'RGB':
        qr_img = qr_img.convert('RGB')
    
    # PIL을 numpy 배열로 변환
    img_array = np.array(qr_img)
    
    # 랜덤하게 일부 픽셀을 흰색으로 변경
    mask = np.random.random(img_array.shape[:2]) < damage_level
    img_array[mask] = 255
    
    return Image.fromarray(img_array)


def create_pdf_with_qr(qr_image: Image.Image, transport_no: str, qr_type: str, output_path: Path):
    """QR 코드가 포함된 PDF 생성"""
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    
    # 제목
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, f"운송번호: {transport_no}")
    
    # QR 타입 설명
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"QR 타입: {qr_type}")
    
    # QR 코드를 임시 파일로 저장
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
        qr_image.save(temp_file.name, 'PNG')
        temp_path = temp_file.name
    
    try:
        # QR 코드를 PDF에 삽입
        qr_x = 50
        qr_y = height - 300
        qr_size = 200
        
        c.drawImage(temp_path, qr_x, qr_y, qr_size, qr_size)
        
        # 추가 텍스트
        c.setFont("Helvetica", 10)
        c.drawString(50, qr_y - 30, f"생성일시: 2024-01-01 12:00:00")
        c.drawString(50, qr_y - 50, f"파일명: {output_path.name}")
        
        c.save()
        
    finally:
        # 임시 파일 삭제
        os.unlink(temp_path)


def generate_test_samples(output_dir: Path, count_per_type: int = 5):
    """다양한 QR 코드 테스트 샘플 생성"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    qr_types = [
        ("normal", "정상", create_normal_qr),
        ("rotated_15", "15도 회전", lambda data, size=200: create_rotated_qr(data, 15, size)),
        ("rotated_30", "30도 회전", lambda data, size=200: create_rotated_qr(data, 30, size)),
        ("rotated_45", "45도 회전", lambda data, size=200: create_rotated_qr(data, 45, size)),
        ("blurred_light", "약간 흐림", lambda data, size=200: create_blurred_qr(data, 1.0, size)),
        ("blurred_heavy", "심하게 흐림", lambda data, size=200: create_blurred_qr(data, 2.5, size)),
        ("low_contrast", "낮은 대비", lambda data, size=200: create_low_contrast_qr(data, 0.4, size)),
        ("very_low_contrast", "매우 낮은 대비", lambda data, size=200: create_low_contrast_qr(data, 0.2, size)),
        ("noisy", "노이즈", lambda data, size=200: create_noisy_qr(data, 0.05, size)),
        ("damaged_light", "약간 손상", lambda data, size=200: create_damaged_qr(data, 0.02, size)),
        ("damaged_heavy", "심하게 손상", lambda data, size=200: create_damaged_qr(data, 0.08, size)),
    ]
    
    sample_count = 0
    
    for type_code, type_name, create_func in qr_types:
        print(f"생성 중: {type_name} QR 코드...")
        
        for i in range(count_per_type):
            # 14자리 운송번호 생성
            transport_no = f"{random.randint(10000000000000, 99999999999999)}"
            
            # QR 코드 생성
            qr_image = create_func(transport_no)
            
            # PDF 파일명
            filename = f"qr_test_{type_code}_{i+1:02d}_{transport_no}.pdf"
            output_path = output_dir / filename
            
            # PDF 생성
            create_pdf_with_qr(qr_image, transport_no, type_name, output_path)
            
            sample_count += 1
            print(f"  생성됨: {filename}")
    
    print(f"\n총 {sample_count}개 테스트 샘플 생성 완료!")
    print(f"출력 폴더: {output_dir}")
    
    # 엔진별 예상 성공률 안내
    print("\n=== 엔진별 예상 성공률 ===")
    print("ZBAR: 정상(100%), 회전(50%), 흐림(30%), 낮은대비(20%), 노이즈(40%), 손상(60%)")
    print("ZXING: 정상(100%), 회전(90%), 흐림(60%), 낮은대비(40%), 노이즈(70%), 손상(80%)")
    print("PYZBAR_PREPROC: 정상(100%), 회전(95%), 흐림(80%), 낮은대비(70%), 노이즈(85%), 손상(75%)")


if __name__ == "__main__":
    # 출력 디렉토리 설정
    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
    else:
        output_dir = Path("data/scanner_output")
    
    # 샘플 개수 설정
    count_per_type = 3 if len(sys.argv) <= 2 else int(sys.argv[2])
    
    print("다중 QR 엔진 테스트 샘플 생성기")
    print(f"출력 폴더: {output_dir}")
    print(f"타입별 샘플 수: {count_per_type}")
    print()
    
    generate_test_samples(output_dir, count_per_type)
