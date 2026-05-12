# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for SlideScribe.

Build (from repo root):
    pyinstaller build/slidescribe.spec --clean --noconfirm

Output:
    dist/SlideScribe/SlideScribe.exe   (+ supporting files)
"""

import os
import site
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


# ── Paths (SPECPATH is build/, repo root is parent) ─────────────────
ROOT = Path(SPECPATH).resolve().parent
os.chdir(ROOT)


# ── NVIDIA CUDA DLLs (cublas / cudnn / cuda_runtime via pip) ────────
def _collect_nvidia_dlls():
    dlls = []
    for sp in site.getsitepackages():
        nvidia_root = Path(sp) / "nvidia"
        if not nvidia_root.is_dir():
            continue
        for pkg in nvidia_root.iterdir():
            bin_dir = pkg / "bin"
            if not bin_dir.is_dir():
                continue
            for dll in bin_dir.glob("*.dll"):
                dlls.append((str(dll), "."))
    return dlls


# ── Hidden imports (PyInstaller can't always trace these) ───────────
hidden_imports = []
hidden_imports += collect_submodules("uvicorn")
hidden_imports += collect_submodules("fastapi")
hidden_imports += collect_submodules("starlette")
hidden_imports += collect_submodules("faster_whisper")
hidden_imports += collect_submodules("ctranslate2")
hidden_imports += [
    "multipart",            # python-multipart
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]


# ── Data files (frontend, config, stages package) ───────────────────
datas = [
    ("web", "web"),
    ("config.yaml", "."),
    ("stages", "stages"),
]
datas += collect_data_files("faster_whisper")
datas += collect_data_files("ctranslate2")


# ── Binaries: CUDA DLLs + optional bundled ffmpeg ───────────────────
binaries = _collect_nvidia_dlls()
ffmpeg_bundle = ROOT / "build" / "bin" / "ffmpeg.exe"
if ffmpeg_bundle.is_file():
    binaries.append((str(ffmpeg_bundle), "bin"))


# ── Excludes: drop huge unused deps to keep installer reasonable ────
# PyKoSpacing drags in TensorFlow (~500MB+). Without it, Whisper still
# transcribes Korean fine — only the post-processing spacing fix is missed.
excludes = [
    "tensorflow", "tensorflow.python", "tensorflow_intel",
    "keras",
    "h5py",
    "pykospacing",
    "matplotlib", "pandas",
    "jupyter", "IPython", "notebook", "ipykernel",
    "pytest", "sphinx",
]


a = Analysis(
    ["launcher.py"],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

icon_path = ROOT / "build" / "icon.ico"
exe_icon = str(icon_path) if icon_path.is_file() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SlideScribe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,           # show terminal — close window to quit app
    disable_windowed_traceback=False,
    icon=exe_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SlideScribe",
)
