# Run with: pyinstaller AutoAudioSwitcher.spec

from PyInstaller.utils.hooks import collect_data_files


block_cipher = None

datas = collect_data_files("customtkinter")
datas += [
    ("assets/app_icon.png", "assets"),
    ("assets/app_icon.ico", "assets"),
    ("assets/icons", "assets/icons"),
    ("config.json", "."),
    ("nircmd.exe", "."),
]

a = Analysis(
    ["UIaudio.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "pycaw",
        "pycaw.pycaw",
        "pycaw.constants",
        "comtypes",
        "comtypes.client",
        "pystray",
        "PIL",
        "win32gui",
        "win32process",
        "win32ui",
        "win32con",
    ],
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
    [],
    name="AutoAudioSwitcher",
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
    icon="assets/app_icon.ico",
    exclude_binaries=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AutoAudioSwitcher",
    contents_directory=".",
)
