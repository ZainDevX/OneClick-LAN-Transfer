# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None
project_root = Path(SPECPATH).resolve()

datas = [
    (str(project_root / 'assets'), 'assets'),
]

hiddenimports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'cryptography',
    'cryptography.x509',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.asymmetric',
    'cryptography.hazmat.primitives.asymmetric.rsa',
    'cryptography.hazmat.primitives.serialization',
    'psutil',
    'app',
    'app.main_window',
    'app.host',
    'app.client',
    'app.network_manager',
    'app.adapter_detection',
    'app.authentication',
    'app.transfer_engine',
    'app.file_manager',
    'app.integrity',
    'app.firewall_manager',
    'app.permissions',
    'app.settings_manager',
    'app.error_handler',
    'ui',
    'ui.dashboard',
    'ui.host_view',
    'ui.client_view',
    'ui.settings_view',
    'ui.styles',
]

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'numpy',
        'pandas',
        'IPython',
        'jupyter',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtPdf',
        'PySide6.QtPdfWidgets',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OneClickLAN',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'assets' / 'app.ico'),
    # Double-click shows one UAC prompt before the process starts. Network
    # changes and restore-on-close then run in this process with no second prompt.
    uac_admin=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='OneClickLAN',
)
