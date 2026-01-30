# -*- mode: python ; coding: utf-8 -*-


import os
import sys

# venv의 site-packages 경로 찾기
venv_path = os.path.join(os.path.dirname(os.path.abspath(SPEC)), '.venv')
site_packages = os.path.join(venv_path, 'lib', 'python3.13', 'site-packages')
customtkinter_path = os.path.join(site_packages, 'customtkinter')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[(customtkinter_path, 'customtkinter'), ('url_collector/fonts', 'fonts')],
    hiddenimports=['customtkinter', 'PIL', 'PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='URLCollector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='URLCollector',
)
app = BUNDLE(
    coll,
    name='URLCollector.app',
    icon=None,
    bundle_identifier=None,
)
