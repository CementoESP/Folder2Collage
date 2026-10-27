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

"""Similitud entre imagenes para hacer collages de fotos parecidas.

Todo se calcula en local con el modelo de IA CLIP ViT-B/32 (pesos de OpenAI, version
ONNX cuantizada: vision a 4 bits y texto a 8 bits), que entiende el contenido: paisajes, rostros, animales, texto...
Cada imagen se resume en un vector (una "huella") y dos imagenes se parecen mas cuanto
mayor es el producto escalar de sus huellas. Tambien se puede buscar por texto.

El modelo no viene con la aplicacion: se descarga una sola vez cuando el usuario lo
pide (descargar_modelo). Es la unica conexion a internet de la aplicacion y solo
descarga; nunca se envia nada. Cada archivo se comprueba con su SHA-256.

Las huellas se guardan en la carpeta cache/ para no recalcularlas; si una imagen
cambia (fecha de modificacion o tamano del archivo) se vuelve a analizar.
"""

import hashlib
import html
import importlib.util
import json
import os
import random
import re
import sys
import threading
import unicodedata
import urllib.request
from functools import lru_cache
from pathlib import Path

from PIL import Image

from collage import abrir_orientada
from rutas import CACHE, DATOS

CACHE_DIR = CACHE
MODELO_DIR = DATOS / "modelo"

# Archivos del modelo en HuggingFace, fijados a una version concreta (no cambian aunque
# el repositorio se actualice). nombre local: (ruta remota, bytes, sha256)
_ORIGEN_MODELO = "https://huggingface.co/Xenova/clip-vit-base-patch32/resolve/d15189d7028b43f1d3e65039190477f6af591c2a/"
ARCHIVOS_MODELO = {
    "vision.onnx": ("onnx/vision_model_q4.onnx", 63642858,
                    "0769eb1d2f6f68927bbfa6e5330df4c4c3c112f89cd43eae28baafa9e6bd34b4"),
    "texto.onnx": ("onnx/text_model_quantized.onnx", 64504507,
                   "73baab855d406190da9faa498cfedf65f15cf309f4cc7385b7b032e6d08e5c3a"),
    "tokenizer.json": ("tokenizer.json", 2224119,
                       "f7f3b7af117d467b58374797691a6438d3e6b9e9cef800dfd5dced7f697a90cd"),
}
TAMANO_MODELO_MB = round(sum(b for _, b, _ in ARCHIVOS_MODELO.values()) / 1e6)


def ia_instalada() -> bool:
    """Estan las librerias para ejecutar el modelo (en la version empaquetada, siempre)."""
    return importlib.util.find_spec("onnxruntime") is not None and importlib.util.find_spec("numpy") is not None


def modelo_descargado() -> bool:
    return all((MODELO_DIR / n).is_file() and (MODELO_DIR / n).stat().st_size == b
               for n, (_, b, _) in ARCHIVOS_MODELO.items())


class Cancelado(Exception):
    pass


def descargar_modelo(progreso=None, cancelado=None):
    """Descarga los archivos que falten. progreso(bytes_hechos, bytes_totales); cancelado() -> bool."""
    MODELO_DIR.mkdir(parents=True, exist_ok=True)
    total = sum(b for _, b, _ in ARCHIVOS_MODELO.values())
    hechos = 0
    for nombre, (remoto, tamano, sha256) in ARCHIVOS_MODELO.items():
        destino = MODELO_DIR / nombre
        if destino.is_file() and destino.stat().st_size == tamano:
            hechos += tamano
            continue
        parcial = destino.with_name(nombre + ".part")
        resumen = hashlib.sha256()
        try:
            with urllib.request.urlopen(_ORIGEN_MODELO + remoto, timeout=30) as respuesta, open(parcial, "wb") as f:
                while bloque := respuesta.read(1 << 20):
                    if cancelado and cancelado():
                        raise Cancelado()
                    f.write(bloque)
                    resumen.update(bloque)
                    hechos += len(bloque)
                    if progreso:
                        progreso(hechos, total)
            if resumen.hexdigest() != sha256:
                raise ValueError(f"{nombre}: el archivo descargado no es correcto")
            parcial.replace(destino)
        finally:
            parcial.unlink(missing_ok=True)


def _producto(a, b):
    return sum(x * y for x, y in zip(a, b))


def _abrir_reducida(ruta: Path, lado: int) -> Image.Image:
    """Abre la imagen ya reducida (lo mas rapido posible) para analizarla."""
    with Image.open(ruta) as img:
        img.draft("RGB", (lado, lado))  # solo acelera JPEG
        img = abrir_orientada(img)
    factor = max(1, min(img.size) // lado)
    if factor > 1:
        img = img.reduce(factor)
    return img


class TokenizadorClip:
    """Tokenizador BPE de CLIP (el mismo que usa el modelo), sin dependencias externas."""

    INICIO, FIN, LONGITUD = 49406, 49407, 77
    # Equivale al patron original: [\p{L}]+ -> [^\W\d_]+, [\p{N}] -> \d, resto -> (?:[^\s\w]|_)+
    PATRON = re.compile(r"<\|startoftext\|>|<\|endoftext\|>|'s|'t|'re|'ve|'m|'ll|'d|[^\W\d_]+|\d|(?:[^\s\w]|_)+")

    def __init__(self, archivo: Path):
        datos = json.loads(archivo.read_text(encoding="utf-8"))["model"]
        self.vocabulario = datos["vocab"]
        uniones = [tuple(m.split(" ")) if isinstance(m, str) else tuple(m) for m in datos["merges"]]
        self.rangos = {par: i for i, par in enumerate(uniones)}
        self.bytes_a_letra = self._bytes_a_unicode()

    @staticmethod
    def _bytes_a_unicode():
        """Asigna a cada byte un caracter visible (el BPE trabaja sobre esos caracteres)."""
        visibles = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
        codigos, extra = visibles[:], 0
        for b in range(256):
            if b not in visibles:
                visibles.append(b)
                codigos.append(256 + extra)
                extra += 1
        return {b: chr(c) for b, c in zip(visibles, codigos)}

    @lru_cache(maxsize=4096)
    def _bpe(self, palabra: str) -> tuple[str, ...]:
        partes = list(palabra[:-1]) + [palabra[-1] + "</w>"]
        while len(partes) > 1:
            rango, i = min((self.rangos.get(par, float("inf")), i) for i, par in enumerate(zip(partes, partes[1:])))
            if rango == float("inf"):
                break
            partes[i:i + 2] = [partes[i] + partes[i + 1]]
        return tuple(partes)

    def codificar(self, texto: str) -> list[int]:
        texto = unicodedata.normalize("NFC", html.unescape(texto))
        texto = re.sub(r"\s+", " ", texto).strip().lower()
        ids = []
        for trozo in self.PATRON.findall(texto):
            letras = "".join(self.bytes_a_letra[b] for b in trozo.encode("utf-8"))
            ids.extend(self.vocabulario[t] for t in self._bpe(letras) if t in self.vocabulario)
        return [self.INICIO] + ids[:self.LONGITUD - 2] + [self.FIN]


class Indice:
    """Huellas de las imagenes con cache en disco. Subclases: IndiceClip."""

    archivo: str

    def __init__(self):
        self.huellas: dict[str, list[float]] = {}
        self._claves: dict[str, str] = {}
        self._cerrojo = threading.Lock()
        try:
            datos = json.loads((CACHE_DIR / self.archivo).read_text(encoding="utf-8"))
            self.huellas = datos.get("huellas", {})
        except Exception:
            pass

    @staticmethod
    def clave(ruta: Path) -> str:
        st = ruta.stat()
        return f"{ruta}|{st.st_mtime_ns}|{st.st_size}"

    def _clave(self, ruta: Path) -> str | None:
        try:
            return self.clave(ruta)
        except OSError:
            return None

    def vector(self, ruta: Path):
        clave = self._clave(ruta)
        return self.huellas.get(clave) if clave else None

    def faltan(self, rutas: list[Path]) -> list[Path]:
        return [r for r in rutas if (c := self._clave(r)) and c not in self.huellas]

    def guardar(self):
        with self._cerrojo:
            datos = json.dumps({"huellas": self.huellas}, separators=(",", ":"))
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        temporal = CACHE_DIR / (self.archivo + ".tmp")
        temporal.write_text(datos, encoding="utf-8")
        temporal.replace(CACHE_DIR / self.archivo)

    def analizar(self, rutas: list[Path], progreso=None, cancelado=None, lote: int = 16):
        """Calcula las huellas que falten. progreso(hechas, total); cancelado() -> bool."""
        pendientes = self.faltan(rutas)
        for inicio in range(0, len(pendientes), lote):
            if cancelado and cancelado():
                break
            grupo = pendientes[inicio:inicio + lote]
            imagenes, claves = [], []
            for ruta in grupo:
                try:
                    clave, imagen = self.clave(ruta), self._preparar(ruta)
                except Exception:
                    continue  # imagen ilegible: se omite
                claves.append(clave)
                imagenes.append(imagen)
            if imagenes:
                vectores = self._extraer(imagenes)
                with self._cerrojo:
                    for clave, vector in zip(claves, vectores):
                        self.huellas[clave] = [round(v, 5) for v in vector]
            if progreso:
                progreso(min(inicio + lote, len(pendientes)), len(pendientes))
            if (inicio // lote) % 20 == 19:
                self.guardar()
        if pendientes:
            self.guardar()

    def _preparar(self, ruta: Path):
        raise NotImplementedError

    def _extraer(self, imagenes) -> list[list[float]]:
        raise NotImplementedError


class IndiceClip(Indice):
    """Huellas del modelo CLIP ViT-B/32 con ONNX Runtime. El modelo se carga al primer uso."""

    archivo = "clip_vitb32_q4.json"
    LADO = 224
    MEDIA = (0.48145466, 0.4578275, 0.40821073)
    DESVIACION = (0.26862954, 0.26130258, 0.27577711)
    _modelo = None
    _cerrojo_modelo = threading.Lock()

    @classmethod
    def _cargar(cls):
        with cls._cerrojo_modelo:
            if cls._modelo is None:
                import numpy as np
                import onnxruntime as ort

                opciones = ort.SessionOptions()
                opciones.intra_op_num_threads = max(1, (os.cpu_count() or 2) - 1)  # deja un nucleo libre
                sesion = lambda n: ort.InferenceSession(str(MODELO_DIR / n), opciones,
                                                        providers=["CPUExecutionProvider"])
                cls._modelo = (sesion("vision.onnx"), sesion("texto.onnx"),
                               TokenizadorClip(MODELO_DIR / "tokenizer.json"), np)
        return cls._modelo

    def _preparar(self, ruta: Path):
        import numpy as np

        img = _abrir_reducida(ruta, 2 * self.LADO).convert("RGB")
        escala = self.LADO / min(img.size)
        img = img.resize((max(self.LADO, round(img.width * escala)), max(self.LADO, round(img.height * escala))),
                         Image.BICUBIC)
        izquierda, arriba = (img.width - self.LADO) // 2, (img.height - self.LADO) // 2
        img = img.crop((izquierda, arriba, izquierda + self.LADO, arriba + self.LADO))
        pixeles = (np.asarray(img, dtype=np.float32) / 255 - self.MEDIA) / self.DESVIACION
        return pixeles.transpose(2, 0, 1).astype(np.float32)

    def _extraer(self, imagenes):
        vision, _, _, np = self._cargar()
        vectores = vision.run(None, {"pixel_values": np.stack(imagenes)})[0]
        return (vectores / np.linalg.norm(vectores, axis=1, keepdims=True)).tolist()

    def texto(self, consulta: str) -> list[float]:
        """Huella de un texto, para buscar imagenes que encajen con el."""
        _, texto, tokenizador, np = self._cargar()
        ids = np.array([tokenizador.codificar(consulta)], dtype=np.int64)
        vector = texto.run(None, {"input_ids": ids})[0][0]
        return (vector / np.linalg.norm(vector)).tolist()


def minimo_parecidas(modo: str, filas: int, imagenes: int) -> int:
    """Cuantas imagenes parecidas hacen falta como minimo: algo mas de las que caben en el
    collage, para no repetir y (en modo tamano original) poder elegir tamanos que encajen."""
    return max(8, round(imagenes * 1.5)) if modo == "original" else max(12, filas * 5)


def seleccionar_parecidas(rutas, indice: Indice, semilla: int, parecido: float, minimo: int,
                          referencia=None):
    """Elige una imagen de referencia (o usa el vector `referencia`, p. ej. de un texto) y
    devuelve (ruta_referencia, subconjunto) con las imagenes mas parecidas, ordenadas.

    parecido (0-1): 0 = se queda con la mitad mas parecida; 1 = solo con las muy parecidas.
    minimo: tamano minimo del subconjunto (para no repetir imagenes en el collage)."""
    con_huella = [(r, v) for r in rutas if (v := indice.vector(r)) is not None]
    if not con_huella:
        return None, list(rutas)
    ancla = None
    if referencia is None:
        ancla, referencia = random.Random(semilla + 7919).choice(con_huella)
    puntuadas = sorted(con_huella, key=lambda rv: -_producto(rv[1], referencia))
    fraccion = 0.5 * (1 - parecido) + 0.03 * parecido
    k = min(len(puntuadas), max(minimo, round(len(puntuadas) * fraccion)))
    return ancla, [r for r, _ in puntuadas[:k]]


if __name__ == "__main__":
    if "--descargar" in sys.argv:
        print(f"Descargando el modelo de IA (unos {TAMANO_MODELO_MB} MB, solo la primera vez)...")
        descargar_modelo(lambda h, t: print(f"\r{h / 1e6:.0f}/{t / 1e6:.0f} MB", end="", flush=True))
        print("\nListo. A partir de ahora funciona sin conexion.")
    else:
        print("Uso: python similitud.py --descargar   (descarga el modelo de IA una sola vez)")
