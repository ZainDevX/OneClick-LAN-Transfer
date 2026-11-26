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

# The widgets app never loads these. Import scan of a full build showed
# Qt6Core/Qt6Gui/Qt6Widgets/qwindows do not link them. They were about 23 MB
# of the 52 MB zip (opengl32sw.dll alone was 7.7 MB compressed).
_DROP_FILES = {
    'opengl32sw.dll',
    'libcrypto-3-x64.dll',
    'libssl-3-x64.dll',
    'qdirect2d.dll',
    'qminimal.dll',
    'qoffscreen.dll',
    'qpdf.dll',
    'qsvg.dll',
    'qsvgicon.dll',
    'qtuiotouchplugin.dll',
    'qnetworklistmanager.dll',
    'qcertonlybackend.dll',
    'qopensslbackend.dll',
    'qschannelbackend.dll',
    'qtvirtualkeyboardplugin.dll',
}
_DROP_PREFIXES = (
    'qt6network', 'qtnetwork',
    'qt6qml', 'qtqml',
    'qt6quick', 'qtquick',
    'qt6pdf', 'qtpdf',
    'qt6svg', 'qtsvg',
    'qt6opengl', 'qtopengl',
    'qt6virtualkeyboard', 'qtvirtualkeyboard',
)


def _ship(entry):
    blob = (entry[0] + '/' + entry[1]).replace('\\', '/').lower()
    if '/translations/' in blob:
        return False
    base = Path(entry[0]).name.lower()
    if base in _DROP_FILES:
        return False
    return not Path(base).stem.startswith(_DROP_PREFIXES)


_before = len(a.binaries) + len(a.datas)
a.binaries = [entry for entry in a.binaries if _ship(entry)]
a.datas = [entry for entry in a.datas if _ship(entry)]
print(f'OneClickLAN: left out {_before - len(a.binaries) - len(a.datas)} unused Qt files')

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
