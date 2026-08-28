# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('curriculum_base.json', '.'), ('.env.example', '.'), ('logo.ico', '.'), ('skills_ia', 'skills_ia'), ('docs', 'docs')]
binaries = []
hiddenimports = ['google.generativeai','plyer','pypdf','docx','filters','notify','importer','github_optimizer','ats_optimizer','collector','db','report','sender']

tmp = collect_all('ttkbootstrap')
datas += list(tmp[0]); binaries += list(tmp[1]); hiddenimports += list(tmp[2])
tmp = collect_all('reportlab')
datas += list(tmp[0]); binaries += list(tmp[1]); hiddenimports += list(tmp[2])

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='JobAutoFit_v2',
    icon='logo.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
