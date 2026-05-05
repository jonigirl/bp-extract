# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

base = Path(SPECPATH)

a = Analysis(
    ['launch.py'],
    pathex=[str(base)],
    binaries=[],
    datas=[
        (str(base / 'templates'), 'templates'),
        (str(base / 'static'), 'static'),
    ],
    hiddenimports=[
        'flask',
        'jinja2',
        'jinja2.ext',
        'werkzeug',
        'werkzeug.serving',
        'werkzeug.routing',
        'werkzeug.exceptions',
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
    [],
    exclude_binaries=True,
    name='BP Extract',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BP Extract',
)
