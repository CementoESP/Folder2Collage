# Especificacion de PyInstaller. No se usa directamente: la llama construir.py.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

raiz = Path(SPECPATH).parent
icono = str(raiz / "recursos" / "icono.ico")

a = Analysis(
    [str(raiz / "Folder2Collage.pyw")],
    pathex=[str(raiz)],
    datas=[(str(raiz / "idiomas"), "idiomas"), (icono, "recursos")] + collect_data_files("customtkinter"),
    # Por si se construye fuera del entorno limpio: nada de PyTorch ni librerias que no se usan.
    excludes=["torch", "torchvision", "open_clip", "matplotlib", "scipy", "pandas", "IPython", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Folder2Collage",
    console=False,
    icon=icono,
    version=str(Path(SPECPATH) / "build" / "version_info.txt"),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="Folder2Collage", upx=False)
