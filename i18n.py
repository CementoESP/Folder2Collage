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

"""Traducciones de la interfaz: un archivo JSON por idioma en la carpeta idiomas/.

    usar("auto")              idioma de Windows (si no esta traducido, ingles)
    t("clave", n=3)           texto traducido, con sus {datos} rellenos
    tn("clave", n)            como t, pero elige "clave.1" o "clave.n" segun n

Si a un idioma le falta una clave se usa la inglesa, y si tampoco existe, la clave.
"""

import ctypes
import json
import locale

from rutas import RECURSOS

CARPETA = RECURSOS / "idiomas"
IDIOMAS = {"en": "English", "de": "Deutsch", "es": "Español", "fr": "Français", "it": "Italiano", "pt": "Português"}
RESERVA = "en"

idioma = RESERVA
_textos: dict[str, str] = {}
_reserva: dict[str, str] = {}


def idioma_sistema() -> str:
    """Codigo de dos letras del idioma de Windows, si esta entre los traducidos."""
    nombre = ""
    try:
        buffer = ctypes.create_unicode_buffer(85)
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        if ctypes.windll.kernel32.LCIDToLocaleName(lang_id, buffer, 85, 0):
            nombre = buffer.value  # p. ej. "es-ES"
    except Exception:
        nombre = locale.getlocale()[0] or ""
    codigo = nombre[:2].lower()
    return codigo if codigo in IDIOMAS else RESERVA


def _cargar(codigo: str) -> dict[str, str]:
    try:
        return json.loads((CARPETA / f"{codigo}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def usar(codigo: str):
    global idioma, _textos, _reserva
    idioma = codigo if codigo in IDIOMAS else idioma_sistema()
    _reserva = _cargar(RESERVA)
    _textos = _reserva if idioma == RESERVA else _cargar(idioma)


def t(clave: str, **datos) -> str:
    texto = _textos.get(clave) or _reserva.get(clave) or clave
    return texto.format(**datos) if datos else texto


def tn(clave: str, n: int, **datos) -> str:
    return t(f"{clave}.{'1' if n == 1 else 'n'}", n=n, **datos)
