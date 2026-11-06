# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Gorillas game

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files from pygame_ce
pygame_datas = collect_data_files('pygame_ce')

a = Analysis(
    ['game.py'],
    pathex=[],
    binaries=[],
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
