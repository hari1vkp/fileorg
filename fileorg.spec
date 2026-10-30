# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for the fileorg desktop app."""

import sys

icon = "app/assets/icons/icon.ico" if sys.platform == "win32" else None
version = "version_info.txt" if sys.platform == "win32" else None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("app/assets/icons/icon.png", "app/assets/icons")],
    hiddenimports=[],
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
    name="fileorg",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
    version=version,
)
