# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec for GestureVLC.
Builds a Windows-distributable app folder used by Inno Setup installer.
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH).resolve().parent

hiddenimports = []
hiddenimports += collect_submodules("sklearn")
hiddenimports += collect_submodules("mediapipe")
hiddenimports += collect_submodules("yt_dlp")
hiddenimports += collect_submodules("onnxruntime")

# Package data from third-party libs that rely on non-Python assets.
datas = []
datas += collect_data_files("mediapipe")
datas += collect_data_files("yt_dlp")
datas += collect_data_files("onnxruntime")

# Project runtime assets.
datas += [
    (str(project_root / "app" / "models" / "air_writing_cnn.onnx"), "app/models"),
    (str(project_root / "app" / "models" / "cnn_model.json"), "app/models"),
    (str(project_root / "app" / "models" / "cnn_model_weights.h5"), "app/models"),
    (str(project_root / "gesture" / "gesture_model.pkl"), "gesture"),
    (str(project_root / "gesture" / "gesture_scaler.pkl"), "gesture"),
    (str(project_root / "gesture" / "class_map.json"), "gesture"),
    (str(project_root / "gesture" / "gesture_settings.json"), "gesture"),
    (str(project_root / "assets"), "assets"),
]

# hand_landmarker.task is intentionally not bundled because it can be updated
# independently and is downloaded by the installer if missing.

block_cipher = None


a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tensorflow", "tf2onnx"],
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
    name="GestureVLC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "assets" / "GestureVLC.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GestureVLC",
)
