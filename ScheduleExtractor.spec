# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\Martin Baer\\Documents\\Work\\mySchedule.cloud\\get-schedule\\src\\schedule_extractor.py'],
    pathex=['C:\\Users\\Martin Baer\\Documents\\Work\\mySchedule.cloud\\get-schedule\\src'],
    binaries=[('C:\\Users\\Martin Baer\\Documents\\Work\\mySchedule.cloud\\get-schedule\\google\\chrome\\chromedriver-win64\\chromedriver.exe', 'google/chrome/chromedriver-win64/')],
    datas=[('C:\\Users\\Martin Baer\\Documents\\Work\\mySchedule.cloud\\get-schedule\\google\\chrome\\chrome-win64\\chrome.exe', 'google/chrome/chrome-win64/')],
    hiddenimports=['schedule_extractor_utils'],
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
    name='ScheduleExtractor',
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
