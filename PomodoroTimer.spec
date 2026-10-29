# -*- mode: python ; coding: utf-8 -*-

import os
import runpy
import sys
from pathlib import Path
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable,
    VarFileInfo, VarStruct, VSVersionInfo,
)

release = runpy.run_path(str(Path(SPECPATH) / 'app_info.py'))
version = release['APP_VERSION']
version_tuple = tuple(int(part) for part in version.split('.'))
version_tuple += (0,) * (4 - len(version_tuple))
version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=version_tuple, prodvers=version_tuple,
        mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0),
    ),
    kids=[
        StringFileInfo([StringTable('040904B0', [
            StringStruct('FileDescription', release['APP_NAME']),
            StringStruct('ProductName', release['APP_NAME']),
            StringStruct('FileVersion', version),
            StringStruct('ProductVersion', version),
            StringStruct('InternalName', 'PomodoroTimer'),
            StringStruct('OriginalFilename', release['EXE_NAME'] + '.exe'),
        ])]),
        VarFileInfo([VarStruct('Translation', [0x0409, 1200])]),
    ],
)

# Native tools on PATH can supply an incompatible ICU or CRT with the same
# DLL filename as Windows. Only search the app's Python and Windows runtimes;
# PyInstaller's Qt hooks add the PySide6/Shiboken directories themselves.
if sys.platform == 'win32':
    windows = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    os.environ['PATH'] = os.pathsep.join(str(path) for path in (
        Path(sys.executable).parent, Path(sys.base_prefix), windows / 'System32', windows,
    ))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    name=release['EXE_NAME'],
    version=version_info,
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
