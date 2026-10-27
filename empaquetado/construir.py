# Copyright 2026 CementoESP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Genera el ejecutable (PyInstaller) y el instalador (Inno Setup).

Uso, desde la carpeta del proyecto y con el entorno limpio (sin PyTorch):
    python -m venv .venv
    .venv\\Scripts\\python -m pip install -r empaquetado\\requirements-build.txt
    .venv\\Scripts\\python empaquetado\\construir.py

Resultado:
    empaquetado\\dist\\Folder2Collage\\                      la aplicacion (Folder2Collage.exe)
    empaquetado\\salida\\Folder2Collage-<version>-Setup.exe  el instalador
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
from rutas import APP_EDITOR, APP_NOMBRE, APP_URL, APP_VERSION  # noqa: E402

VERSION_INFO = """VSVersionInfo(
  ffi=FixedFileInfo(filevers={tupla}, prodvers={tupla}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{editor}'),
      StringStruct('FileDescription', '{nombre}'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', '{nombre}'),
      StringStruct('OriginalFilename', '{nombre}.exe'),
      StringStruct('ProductName', '{nombre}'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def buscar_iscc() -> Path:
    candidatos = [Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
                  Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
                  Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe"]
    for candidato in candidatos:
        if candidato.is_file():
            return candidato
    encontrado = shutil.which("ISCC")
    if encontrado:
        return Path(encontrado)
    sys.exit("No se encuentra Inno Setup 6 (winget install JRSoftware.InnoSetup)")


def main():
    import importlib.util
    if importlib.util.find_spec("torch"):
        print("Aviso: este entorno tiene PyTorch; usa el entorno limpio .venv para no inflar la aplicacion.")

    construccion = AQUI / "build"
    shutil.rmtree(construccion, ignore_errors=True)
    shutil.rmtree(AQUI / "dist", ignore_errors=True)
    construccion.mkdir()
    tupla = tuple(int(n) for n in APP_VERSION.split(".")) + (0,)
    (construccion / "version_info.txt").write_text(
        VERSION_INFO.format(tupla=tupla, nombre=APP_NOMBRE, editor=APP_EDITOR, version=APP_VERSION),
        encoding="utf-8")

    print(f"== PyInstaller: {APP_NOMBRE} {APP_VERSION}")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", str(AQUI / "dist"), "--workpath", str(construccion),
                    str(AQUI / "Folder2Collage.spec")], check=True)

    print("== Inno Setup")
    subprocess.run([str(buscar_iscc()), f"/DAppVersion={APP_VERSION}", f"/DAppEditor={APP_EDITOR}",
                    f"/DAppUrl={APP_URL}", str(AQUI / "instalador.iss")], check=True)
    instalador = AQUI / "salida" / f"{APP_NOMBRE}-{APP_VERSION}-Setup.exe"
    print(f"\nListo: {instalador} ({instalador.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
