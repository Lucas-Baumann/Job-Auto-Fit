# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

# curriculum_base.json NUNCA deve entrar aqui: é dado pessoal real do usuário e ficaria
# gravado dentro do binário para sempre — quem rodasse o .exe (ou o extraísse) veria os
# dados de quem compilou. O código já lida bem com a ausência do arquivo (fica em branco).
datas = [('.env.example', '.'), ('logo.ico', '.')]
binaries = []
hiddenimports = ['google.generativeai','plyer','pypdf','docx','config','logutil','main','filters','notify','importer','profile_generator','ats_optimizer','collector','db','report','sender','exporters','geo','validator','stealth']

tmp = collect_all('ttkbootstrap')
datas += list(tmp[0]); binaries += list(tmp[1]); hiddenimports += list(tmp[2])
tmp = collect_all('reportlab')
datas += list(tmp[0]); binaries += list(tmp[1]); hiddenimports += list(tmp[2])

a = Analysis(
    ['gui.py'],
    pathex=['src'],
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
    icon='logo.ico' if sys.platform == 'win32' else None,  # .ico so existe pra Windows/macOS; no Linux nao ha icone embutido em ELF
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
