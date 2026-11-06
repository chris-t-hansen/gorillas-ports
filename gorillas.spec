# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Gorillas game
# Cross-platform: Windows, macOS, Linux, BSD

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Detect platform
is_windows = sys.platform.startswith('win')
is_macos = sys.platform == 'darwin'
is_linux = sys.platform.startswith('linux')
is_bsd = any(sys.platform.startswith(x) for x in ['freebsd', 'openbsd', 'netbsd'])

# Collect all data files from pygame_ce
pygame_datas = collect_data_files('pygame_ce')

# Collect SDL2 libraries on all platforms
# pygame-ce bundles SDL2 on Windows, but we need to ensure they're included
binaries = []
if is_windows:
    # On Windows, pygame-ce includes SDL2 DLLs, collect them
    import pygame
    pygame_dir = os.path.dirname(pygame.__file__)
    # Add SDL2 DLLs from pygame directory
    for dll in ['SDL2.dll', 'SDL2_image.dll', 'SDL2_mixer.dll', 'SDL2_ttf.dll', 
                'libpng16-16.dll', 'libjpeg-9.dll', 'libwebp-7.dll', 'libfreetype-6.dll',
                'zlib1.dll', 'libFLAC-8.dll', 'libvorbis-0.dll', 'libvorbisfile-3.dll',
                'libogg-0.dll', 'libopus-0.dll', 'libopusfile-0.dll', 'libmpg123-0.dll']:
        dll_path = os.path.join(pygame_dir, dll)
        if os.path.exists(dll_path):
            binaries.append((dll_path, '.'))

a = Analysis(
    ['game.py'],
    pathex=[],
    binaries=binaries,
    datas=[
        # Include game assets
        ('assets/fonts/*.otb', 'assets/fonts'),
        ('assets/fonts/LICENSE.TXT', 'assets/fonts'),
        ('requirements.txt', '.'),
        ('README.md', '.'),
    ] + pygame_datas,
    hiddenimports=[
        'pygame_ce',
        'numpy',
        'qb_runtime',
    ] + collect_submodules('qb_runtime'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='gorillas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # disabled: UPX triggers AV false positives and hinders artifact inspection
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
