# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for URL Collector"""

import sys
from pathlib import Path

# CustomTkinter 경로 찾기
import customtkinter
ctk_path = Path(customtkinter.__file__).parent

# 플랫폼별 아이콘 경로
if sys.platform == 'darwin':
    icon_path = 'assets/icon.icns'
elif sys.platform == 'win32':
    icon_path = 'assets/icon.ico'
else:
    icon_path = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # CustomTkinter 테마/에셋 포함
        (str(ctk_path), 'customtkinter'),
        # Pretendard 폰트
        ('url_collector/fonts', 'fonts'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
    ],
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
    name='URLCollector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 앱이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)
