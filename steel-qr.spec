# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('.venv/Lib/site-packages/pyzbar/libiconv.dll', 'pyzbar'), ('.venv/Lib/site-packages/pyzbar/libzbar-64.dll', 'pyzbar')],
    datas=[('templates', 'templates'), ('static', 'static'), ('config.example.yaml', '.'), ('instances.example.json', '.')],
    hiddenimports=['uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'fastapi', 'pydantic', 'sqlalchemy', 'watchdog', 'watchdog.observers', 'pyzbar', 'cv2', 'PIL', 'PyPDF2', 'pikepdf', 'cryptography', 'yaml', 'loguru', 'httpx', 'win32api', 'win32con', 'win32event', 'win32service', 'win32serviceutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='steel-qr',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
