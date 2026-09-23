# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all
from PyInstaller.building.splash import Splash

# curriculum_base.json NUNCA deve entrar aqui: é dado pessoal real do usuário e ficaria
# gravado dentro do binário para sempre — quem rodasse o .exe (ou o extraísse) veria os
# dados de quem compilou. O código já lida bem com a ausência do arquivo (fica em branco).
datas = [('.env.example', '.'), ('icon.ico', '.'), ('icon_taskbar.ico', '.')]
binaries = []
hiddenimports = ['google.generativeai','plyer','pypdf','docx','config','logutil','main','filters','notify','importer','profile_generator','ats_optimizer','collector','db','report','sender','geo','validator','stealth','browser_auth',
                 # plyer resolve o backend de notificação por import dinâmico em runtime
                 # (__import__ de string montada) — o PyInstaller não enxerga isso, então sem
                 # listar aqui o notify_desktop() falha só dentro do .exe.
                 'plyer.platforms.win.notification', 'plyer.platforms.win.libs.balloontip',
                 'plyer.platforms.linux.notification']

tmp = collect_all('ttkbootstrap')
datas += list(tmp[0]); binaries += list(tmp[1]); hiddenimports += list(tmp[2])
tmp = collect_all('reportlab')
datas += list(tmp[0]); binaries += list(tmp[1]); hiddenimports += list(tmp[2])
# Inclui o driver do Playwright E o Chromium baixado (o build roda 'playwright install
# chromium' com PLAYWRIGHT_BROWSERS_PATH=0 antes, gravando o navegador dentro do pacote,
# de onde collect_all pega junto).
tmp = collect_all('playwright')
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
# Tela de abertura (splash) com a logo do projeto, mostrada ANTES do Python terminar de
# inicializar — o onefile precisa reextrair ~300MB (Chromium bundlado) toda vez que abre,
# o que leva uns 8s; sem isso, a janela demora a aparecer e parece que o app travou.
# Sem text_pos de propósito: se definido, o bootloader escreve nele o nome de cada arquivo
# sendo extraído (centenas, do Chromium bundlado) — poluição visual tipo "texto rodando".
# PyInstaller não suporta uma barra de progresso gráfica nativa (só texto ou imagem
# estática), então a opção sem ruído é não mostrar texto nenhum, só a logo.
splash = Splash(
    'splash.png',
    binaries=a.binaries,
    datas=a.datas,
)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    splash,
    splash.binaries,
    [],
    name='VampHunter',
    icon='icon.ico' if sys.platform == 'win32' else None,  # .ico so existe pra Windows/macOS; no Linux nao ha icone embutido em ELF
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
