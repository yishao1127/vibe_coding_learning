# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / 'run.py')],
    pathex=[str(ROOT), str(ROOT / 'src')],
    binaries=[],
    datas=[(str(ROOT / 'resources' / 'app_icon.png'), 'resources')],
    hiddenimports=['pythoncom', 'pywintypes', 'win32com.client', 'win32com.client.gencache'],
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
    name='English Learning Partner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / 'resources' / 'app_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='English Learning Partner',
)
