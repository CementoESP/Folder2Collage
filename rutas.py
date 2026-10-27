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

"""Nombre de la aplicacion y carpetas que usa.

  Origen por defecto  la carpeta de capturas de Windows del usuario
  Salida por defecto  Imagenes\\Collages
  Datos               %LOCALAPPDATA%\\<APP_NOMBRE>: ajustes, cache de huellas y modelo de IA

Se usan las carpetas especiales de Windows, asi que funciona aunque Imagenes este
redirigida (por ejemplo a OneDrive) o en otro idioma.
"""

import ctypes
import os
import shutil
import sys
import uuid
from pathlib import Path

APP_NOMBRE = "Folder2Collage"
APP_VERSION = "1.0.0"
APP_EDITOR = "CementoESP"
APP_URL = "https://github.com/CementoESP/Folder2Collage"

_CAPTURAS = "b7bede81-df94-4682-a7d8-57a52620b86f"  # FOLDERID_Screenshots
_IMAGENES = "33e28130-4e1e-4676-835a-98395c3bc3bb"  # FOLDERID_Pictures


def carpeta_conocida(guid: str) -> Path | None:
    """Ruta de una carpeta especial de Windows, o None si no existe."""
    try:
        identificador = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID(guid).bytes_le)
        ruta = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(identificador), 0, None, ctypes.byref(ruta)):
            return None
        try:
            return Path(ruta.value)
        finally:
            ctypes.windll.ole32.CoTaskMemFree(ruta)
    except Exception:
        return None


IMAGENES = carpeta_conocida(_IMAGENES) or Path.home() / "Pictures"
ORIGEN_POR_DEFECTO = carpeta_conocida(_CAPTURAS) or IMAGENES / "Screenshots"
SALIDA_POR_DEFECTO = IMAGENES / "Collages"

DATOS = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / APP_NOMBRE
CONFIG = DATOS / "config.json"
CACHE = DATOS / "cache"

# Donde estan los archivos de la propia aplicacion (dentro del ejecutable si esta empaquetada).
RECURSOS = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def migrar_datos_antiguos():
    """Las primeras versiones guardaban los ajustes junto al programa: se mueven a DATOS."""
    antiguo = Path(__file__).resolve().parent / "collage_config.json"
    if antiguo.is_file() and not CONFIG.exists():
        try:
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(antiguo, CONFIG)
        except OSError:
            pass
