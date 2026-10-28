# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['g:/محيط المعرفة/usb_dongle_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('g:/محيط المعرفة/محلي/installer_dist/KnowledgeOcean_Setup.exe', 'installer_dist')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='KnowledgeOcean_USB_Setup',
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
    icon=['g:/محيط المعرفة/محلي/static/app_icon.ico'],
)
