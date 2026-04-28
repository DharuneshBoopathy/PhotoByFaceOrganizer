# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Photo by Face Organizer.

Build:
    py -3.13 -m PyInstaller PhotoByFaceOrganizer.spec --clean --noconfirm
or:
    build.bat
    build.bat installer    (also runs Inno Setup)

Output (folder mode):
    dist/PhotoByFaceOrganizer/PhotoByFaceOrganizer.exe + _internal/

Why folder mode?
  The InsightFace ONNX models alone are ~280 MB; one-file mode would
  unpack them into %TEMP% on every launch, costing a several-second
  cold-start and wasting disk. Folder mode launches in ~1 s.
"""
import os
import re
import sys
from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs,
)

block_cipher = None
ROOT = os.path.abspath(os.path.dirname(SPECPATH))


# ----------------------------------------------------------------------------
# Read version from src/version.py without importing it (PyInstaller may not
# have our project deps available during analysis)
# ----------------------------------------------------------------------------
def _read_version() -> str:
    p = os.path.join(ROOT, "src", "version.py")
    with open(p, "r", encoding="utf-8") as f:
        m = re.search(r'__version__\s*=\s*"([^"]+)"', f.read())
    return m.group(1) if m else "0.0.0"


VERSION = _read_version()


# ----------------------------------------------------------------------------
# Vendor packages with native bits / data
# ----------------------------------------------------------------------------
hidden = []
datas = []
binaries = []

# Heavy ML deps with their data + native libs
for pkg in (
    "onnxruntime",
    "insightface",
    "PIL",
    "skimage",
    "scipy",
    "sklearn",
    "imagehash",
    "cv2",
    "reverse_geocoder",
    "exifread",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hidden += h
    except Exception:
        pass

# Tk data
try:
    datas += collect_data_files("tkinter")
except Exception:
    pass

# All Pillow plugins (auto-loaded but PyInstaller often misses them)
hidden += collect_submodules("PIL")

# Our own packages — explicit list defends against renames missed by graph
hidden += [
    "src",
    "src.about_dialog",
    "src.burst_detector",
    "src.cli",
    "src.cluster_repair",
    "src.database",
    "src.error_handler",
    "src.face_engine",
    "src.folder_icon",
    "src.gui_app",
    "src.gui_log",
    "src.hasher",
    "src.identity",
    "src.incremental",
    "src.labeling",
    "src.labeling_ui",
    "src.main",
    "src.metadata",
    "src.organizer",
    "src.person_album",
    "src.preferences",
    "src.relationships",
    "src.report",
    "src.safety",
    "src.scanner",
    "src.search",
    "src.settings_window",
    "src.stranger_filter",
    "src.thumbnail",
    "src.timeline",
    "src.utils",
    "src.version",
    "src.welcome_wizard",
    "src.xmp_tags",
]


# ----------------------------------------------------------------------------
# Bundle everything in assets/, docs/ icons, license — keep folder layout
# ----------------------------------------------------------------------------
def _bundle_dir(rel_dir: str):
    abs_src = os.path.join(ROOT, rel_dir)
    if not os.path.isdir(abs_src):
        return
    for root, _, files in os.walk(abs_src):
        for f in files:
            full = os.path.join(root, f)
            target_dir = os.path.relpath(os.path.dirname(full), ROOT)
            datas.append((full, target_dir))


_bundle_dir("assets")

# Single-file extras at the project root
for fname in ("LICENSE", "README.md", "CHANGELOG.md"):
    p = os.path.join(ROOT, fname)
    if os.path.isfile(p):
        datas.append((p, "."))


# ----------------------------------------------------------------------------
# Versioned EXE metadata (Windows file properties)
# ----------------------------------------------------------------------------
def _write_version_resource() -> str:
    parts = [int(x) for x in VERSION.split(".")] + [0, 0, 0, 0]
    a, b, c, d = parts[:4]
    body = f"""# Auto-generated. See PhotoByFaceOrganizer.spec.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({a}, {b}, {c}, {d}),
    prodvers=({a}, {b}, {c}, {d}),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(u'040904B0', [
        StringStruct(u'CompanyName', u'Photo by Face Organizer Project'),
        StringStruct(u'FileDescription', u'Photo by Face Organizer'),
        StringStruct(u'FileVersion', u'{VERSION}'),
        StringStruct(u'InternalName', u'PhotoByFaceOrganizer'),
        StringStruct(u'LegalCopyright', u'(c) 2026 Photo by Face Organizer Project. MIT License.'),
        StringStruct(u'OriginalFilename', u'PhotoByFaceOrganizer.exe'),
        StringStruct(u'ProductName', u'Photo by Face Organizer'),
        StringStruct(u'ProductVersion', u'{VERSION}'),
      ])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    out = os.path.join(ROOT, "build", "_version_info.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(body)
    return out


VERSION_FILE = _write_version_resource()


# ----------------------------------------------------------------------------
# Analysis → PYZ → EXE → COLLECT
# ----------------------------------------------------------------------------
a = Analysis(
    ["app_main.py"],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Things sklearn/scipy *might* try to import but we don't ship
        "matplotlib", "matplotlib.pyplot",
        "pandas", "torch", "tensorflow",
        "dask", "dask.array", "cupy", "ndonnx",
        "pyamg", "pooch", "numpydoc",
        # Test runners we don't need at runtime
        "pytest", "IPython", "notebook", "jupyter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

ICON = os.path.join(ROOT, "assets", "app_icon.ico")
if not os.path.isfile(ICON):
    ICON = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PhotoByFaceOrganizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                        # UPX often breaks onnxruntime DLLs
    console=False,                    # GUI app: no black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    version=VERSION_FILE,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PhotoByFaceOrganizer",
)
