# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

base = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(base)],
    binaries=[],
    datas=[],
    hiddenimports=[
        'json',
        'platform',
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
    name='BP Extract CLI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
