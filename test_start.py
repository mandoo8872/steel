#!/usr/bin/env python3
"""서버 시작 테스트"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent))

print("=== 서버 시작 테스트 ===")
print("Step 1: Import modules")

try:
    from src.modes import run_kiosk_mode
    print("✓ Modules imported")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print("Step 2: Start server")
try:
    run_kiosk_mode(
        config_path=Path("config.yaml"),
        port=8000,
        host="0.0.0.0"
    )
except KeyboardInterrupt:
    print("\n✓ Server stopped by user")
except Exception as e:
    print(f"✗ Server failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

