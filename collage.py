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

"""Genera un collage aleatorio con las capturas de pantalla.

Uso:
    python collage.py                 # 1080p (1920x1080), modo filas
    python collage.py --res 2k        # 2K (2560x1440)
    python collage.py --res 2k --filas 4 --separacion 6 --cantidad 3
    python collage.py --modo original --imagenes 20
    python collage.py --periodo semana     # solo capturas de los ultimos 7 dias
    python collage.py --desde 01/10/2026 --hasta 15/10/2026
    python collage.py --similares                  # fotos parecidas (IA local CLIP)
    python collage.py --buscar "dogs"              # fotos que encajen con un texto

Modos:
  filas    Las imagenes se colocan en filas de altura fija; cada fila se ajusta
           al ancho exacto del lienzo recortando lo minimo posible del centro
           de cada imagen.
  original Se elige el numero de imagenes. Las imagenes salen a su tamano real
           en pixeles (nunca se amplian ni se reducen): el lienzo se divide en
           huecos y para cada uno se busca una imagen de tamano igual o algo
           mayor, recortando lo que sobra.
"""

import argparse
import bisect
import math
import random
import sys
from datetime import date, datetime, timedelta
from datetime import time as hora
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from rutas import APP_NOMBRE, ORIGEN_POR_DEFECTO, SALIDA_POR_DEFECTO

RESOLUCIONES = {
    "1080p": (1920, 1080),
    "2k": (2560, 1440),
    "1440p": (2560, 1440),
    "4k": (3840, 2160),
}

EXTENSIONES = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif", ".tif", ".tiff"}


def buscar_imagenes(origen: Path) -> list[Path]:
    return [p for p in origen.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONES]


PERIODOS = ("hoy", "semana", "siempre", "rango")


def parsear_fecha(texto: str) -> date:
    """Acepta dd/mm/aaaa, dd-mm-aaaa, dd.mm.aaaa o aaaa-mm-dd."""
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto.strip(), formato).date()
        except ValueError:
            pass
    raise ValueError(f"fecha no valida: {texto!r} (usa dd/mm/aaaa)")


def fecha_imagen(ruta: Path) -> float:
    """Fecha de la imagen: la mas antigua entre creacion y modificacion (al copiar un
    archivo la fecha de creacion cambia, pero la de modificacion se conserva)."""
    st = ruta.stat()
    return min(getattr(st, "st_birthtime", st.st_mtime), st.st_mtime)


def filtrar_por_periodo(rutas: list[Path], periodo: str, desde: date | None = None,
                        hasta: date | None = None) -> list[Path]:
    """periodo: 'hoy' (desde las 00:00), 'semana' (ultimos 7 dias), 'siempre' o
    'rango' (de desde a hasta, ambos dias incluidos; cualquiera de los dos puede faltar)."""
    if periodo == "siempre":
        return rutas
    inicio, fin = -math.inf, math.inf
    ahora = datetime.now()
    if periodo == "hoy":
        inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    elif periodo == "semana":
        inicio = (ahora - timedelta(days=7)).timestamp()
    else:
        if desde:
            inicio = datetime.combine(desde, hora.min).timestamp()
        if hasta:
            fin = datetime.combine(hasta + timedelta(days=1), hora.min).timestamp()
    resultado = []
    for ruta in rutas:
        try:
            if inicio <= fecha_imagen(ruta) < fin:
                resultado.append(ruta)
        except OSError:
            pass
    return resultado


def orientacion_exif(img: Image.Image) -> int:
    """Orientacion EXIF leyendo solo la cabecera. En PNG, img.getexif() obligaria a leer
    el archivo entero, asi que solo se mira el EXIF que aparece antes de los datos."""
    if img.format == "PNG":
        datos = img.info.get("exif")
        if not datos:
            return 1
        exif = Image.Exif()
        exif.load(datos)
        return exif.get(0x0112, 1)
    return img.getexif().get(0x0112, 1)


def abrir_orientada(img: Image.Image) -> Image.Image:
    """Aplica la orientacion EXIF de forma coherente con leer_tamano."""
    if orientacion_exif(img) != 1:
        img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


@lru_cache(maxsize=None)
def leer_tamano(ruta: Path) -> tuple[int, int] | None:
    """Lee solo la cabecera para obtener el tamano (con la orientacion EXIF aplicada)."""
    try:
        with Image.open(ruta) as img:
            ancho, alto = img.size
            if orientacion_exif(img) in (5, 6, 7, 8):
                ancho, alto = alto, ancho
            return ancho, alto
    except Exception:
        return None


class Bolsa:
    """Entrega imagenes aleatorias sin repetir hasta agotar todas."""

    def __init__(self, rutas: list[Path], rng: random.Random):
        self.rutas = rutas
        self.rng = rng
        self.cola: list[Path] = []

    def siguiente(self) -> tuple[Path, tuple[int, int]]:
        for _ in range(len(self.rutas) * 2 + 1):
            if not self.cola:
                self.cola = self.rutas[:]
                self.rng.shuffle(self.cola)
            ruta = self.cola.pop()
            tamano = leer_tamano(ruta)
            if tamano and tamano[0] > 0 and tamano[1] > 0:
                return ruta, tamano
        raise RuntimeError("No hay imagenes legibles en la carpeta de origen.")


def alturas_de_filas(alto: int, filas: int, separacion: int) -> list[int]:
    util = alto - separacion * (filas - 1)
    base, resto = divmod(util, filas)
    return [base + (1 if i < resto else 0) for i in range(filas)]


def planificar_fila(bolsa: Bolsa, ancho: int, alto_fila: int, separacion: int):
    """Elige imagenes hasta que su ancho (a la altura de la fila) se acerque lo mas posible al lienzo."""
    elegidas: list[tuple[Path, float]] = []
    suma = 0.0
    while True:
        ruta, (w, h) = bolsa.siguiente()
        w_fila = alto_fila * w / h
        disponible = ancho - separacion * len(elegidas)
        if elegidas and abs(suma + w_fila - disponible) > abs(suma - (ancho - separacion * (len(elegidas) - 1))):
            # Anadirla empeoraria el ajuste: la devolvemos a la cola y cerramos la fila.
            bolsa.cola.append(ruta)
            break
        elegidas.append((ruta, w_fila))
        suma += w_fila
        if suma >= ancho - separacion * (len(elegidas) - 1):
            break

    util = ancho - separacion * (len(elegidas) - 1)
    factor = util / suma
    anchos = [max(1, round(w * factor)) for _, w in elegidas]
    anchos[-1] += util - sum(anchos)
    return [(ruta, a) for (ruta, _), a in zip(elegidas, anchos)]


def planificar_collage(rutas, ancho, alto, filas, separacion, rng):
    """Modo filas. Devuelve la distribucion como lista de (ruta, x, y, ancho, alto, encuadre)
    sin abrir el contenido de las imagenes. encuadre=None significa recorte centrado."""
    bolsa = Bolsa(rutas, rng)
    celdas = []
    y = 0
    for alto_fila in alturas_de_filas(alto, filas, separacion):
        x = 0
        for ruta, ancho_celda in planificar_fila(bolsa, ancho, alto_fila, separacion):
            celdas.append((ruta, x, y, ancho_celda, alto_fila, None))
            x += ancho_celda + separacion
        y += alto_fila + separacion
    return celdas


# ---------- modo tamano original (sin escalar, solo recortar) ----------

class Catalogo:
    """Tamanos reales de todas las imagenes, ordenados para buscar rapido las que encajan en un hueco."""

    def __init__(self, rutas: list[Path]):
        items = []
        for ruta in rutas:
            tamano = leer_tamano(ruta)
            if tamano and tamano[0] > 0 and tamano[1] > 0:
                items.append((tamano[0] * tamano[1], tamano[0], tamano[1], ruta))
        if not items:
            raise RuntimeError("No hay imagenes legibles en la carpeta de origen.")
        items.sort(key=lambda it: it[0])
        self.items = items
        self.areas = [it[0] for it in items]
        self.anchos = sorted(it[1] for it in items)
        self.altos = sorted(it[2] for it in items)
        self.aspecto_tipico = math.exp(sum(math.log(it[1] / it[2]) for it in items) / len(items))


def _cortar(total, deseado, medidas, rng, minimo):
    """Posicion de un corte. Suele ajustarse a una medida real de alguna imagen cercana a la deseada."""
    lo = bisect.bisect_left(medidas, deseado * 0.8)
    hi = bisect.bisect_right(medidas, deseado * 1.25)
    if hi > lo and rng.random() < 0.8:
        deseado = medidas[rng.randrange(lo, hi)]
    minimo = min(minimo, total // 2)
    return min(total - minimo, max(minimo, round(deseado)))


def _particionar(x, y, w, h, k, catalogo, rng, salida, variedad=0.0, minimo=16):
    """Divide el rectangulo en k huecos con cortes horizontales y verticales.
    Con variedad 0 cada lado recibe area proporcional a sus imagenes (tamanos parecidos);
    con variedad alta el reparto se desequilibra y salen huecos grandes junto a pequenos."""
    if k == 1 or (w < 2 and h < 2):
        salida.append((x, y, w, h))
        return
    if rng.random() < variedad:
        k1 = rng.randint(1, k - 1)
    else:
        k1 = min(k - 1, max(1, k // 2 + rng.randint(-(k // 5), k // 5)))
    fraccion = min(0.92, max(0.08, k1 / k * math.exp(rng.gauss(0, 0.9 * variedad))))
    mas_ancho = w / h > catalogo.aspecto_tipico
    if h < 2 or (w >= 2 and rng.random() < (0.85 if mas_ancho else 0.15)):
        c = _cortar(w, w * fraccion, catalogo.anchos, rng, minimo)
        _particionar(x, y, c, h, k1, catalogo, rng, salida, variedad, minimo)
        _particionar(x + c, y, w - c, h, k - k1, catalogo, rng, salida, variedad, minimo)
    else:
        c = _cortar(h, h * fraccion, catalogo.altos, rng, minimo)
        _particionar(x, y, w, c, k1, catalogo, rng, salida, variedad, minimo)
        _particionar(x, y + c, w, h - c, k - k1, catalogo, rng, salida, variedad, minimo)


def _separar(x, y, w, h, ancho, alto, separacion):
    """Aplica la separacion solo entre huecos, no contra los bordes del lienzo."""
    x0, y0, x1, y1 = x, y, x + w, y + h
    if x0 > 0:
        x0 += separacion // 2
    if x1 < ancho:
        x1 -= separacion - separacion // 2
    if y0 > 0:
        y0 += separacion // 2
    if y1 < alto:
        y1 -= separacion - separacion // 2
    return x0, y0, max(1, x1 - x0), max(1, y1 - y0)


def _asignar(huecos, catalogo, rng):
    """Para cada hueco elige una imagen igual o algo mayor (se recorta, nunca se escala).
    Devuelve (asignaciones, puntuacion); menor puntuacion = menos recorte."""
    usadas: set[int] = set()
    asignacion = [None] * len(huecos)
    puntos = 0.0
    items = catalogo.items
    # Primero los huecos grandes: tienen menos candidatas.
    for i in sorted(range(len(huecos)), key=lambda i: -huecos[i][2] * huecos[i][3]):
        x, y, w, h = huecos[i]
        if len(usadas) >= len(items):
            usadas.clear()  # se han usado todas: se permite repetir
        candidatas = []
        for j in range(bisect.bisect_left(catalogo.areas, w * h), len(items)):
            if j in usadas:
                continue
            _, iw, ih, _ = items[j]
            if iw >= w and ih >= h:
                candidatas.append(j)
                if len(candidatas) == 4:
                    break
        if candidatas:
            j = rng.choice(candidatas)
            puntos += math.log(items[j][0] / (w * h))
        else:
            # Ninguna imagen es lo bastante grande: la que mas cubra, sin ampliarla.
            j = max((j for j in range(len(items)) if j not in usadas),
                    key=lambda j: min(items[j][1], w) * min(items[j][2], h))
            cubierto = min(items[j][1], w) * min(items[j][2], h) / (w * h)
            puntos += 5 + 10 * (1 - cubierto)
        usadas.add(j)
        asignacion[i] = j
    return asignacion, puntos


def planificar_original(rutas, ancho, alto, imagenes, separacion, rng, variedad=0.7):
    """Modo tamano original. Prueba muchas divisiones del lienzo y se queda con la que
    encuentra imagenes de tamano mas parecido a sus huecos (menos recorte) y, segun
    la variedad (0-1), con mas mezcla de tamanos grandes y pequenos."""
    catalogo = Catalogo(rutas)
    intentos = max(30, min(1500, 4_000_000 // (imagenes * len(catalogo.items))))
    # Ningun hueco con un lado menor que ~1/3 del tamano medio: evita tiras finas.
    minimo = max(16, round(math.sqrt(ancho * alto / imagenes) * 0.35))
    mejor, mejor_puntos = None, math.inf
    for _ in range(intentos):
        particion = []
        _particionar(0, 0, ancho, alto, imagenes, catalogo, rng, particion, variedad, minimo)
        huecos = [_separar(*p, ancho, alto, separacion) for p in particion]
        asignacion, puntos = _asignar(huecos, catalogo, rng)
        log_areas = [math.log(w * h) for _, _, w, h in huecos]
        media = sum(log_areas) / len(log_areas)
        dispersion = math.sqrt(sum((a - media) ** 2 for a in log_areas) / len(log_areas))
        # Se premia la mezcla de tamanos, pero con tope para no buscar extremos absurdos.
        puntos = puntos / len(huecos) - variedad * min(dispersion, 0.4 + 0.8 * variedad)
        if puntos < mejor_puntos:
            mejor, mejor_puntos = (huecos, asignacion), puntos

    huecos, asignacion = mejor
    celdas = []
    for (x, y, w, h), j in zip(huecos, asignacion):
        _, iw, ih, ruta = catalogo.items[j]
        # Imagen centrada en el hueco a su tamano real; lo que sobresale se recorta.
        celdas.append((ruta, x, y, w, h, (x + (w - iw) // 2, y + (h - ih) // 2)))
    return celdas


def _fuente_marca(tamano: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for nombre in ("segoeuisb.ttf", "segoeui.ttf", "arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nombre, tamano)
        except OSError:
            pass
    return ImageFont.load_default()


def estampar_marca(lienzo: Image.Image, texto: str) -> Image.Image:
    """Escribe una marca de agua discreta en la esquina inferior derecha. Un contorno oscuro
    la hace legible tanto sobre zonas claras como oscuras. Si texto esta vacio, no hace nada."""
    if not texto:
        return lienzo
    ancho, alto = lienzo.size
    tamano = max(13, round(alto / 38))
    contorno = max(1, round(tamano / 11))
    fuente = _fuente_marca(tamano)
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(capa)
    izq, arr, der, aba = dibujo.textbbox((0, 0), texto, font=fuente, stroke_width=contorno)
    margen = round(tamano * 0.8)
    x, y = ancho - margen - (der - izq) - izq, alto - margen - (aba - arr) - arr
    dibujo.text((x, y), texto, font=fuente, fill=(255, 255, 255, 205),
                stroke_width=contorno, stroke_fill=(0, 0, 0, 130))
    return Image.alpha_composite(lienzo.convert("RGBA"), capa).convert("RGB")


def renderizar_collage(celdas, ancho, alto, fondo, progreso=None, marca_agua: str = APP_NOMBRE) -> Image.Image:
    """progreso, si se indica, se llama como progreso(hechas, total) tras cada imagen.
    marca_agua: texto de la marca de agua ("" para no ponerla)."""
    lienzo = Image.new("RGB", (ancho, alto), fondo)
    for n, (ruta, x, y, w, h, posicion) in enumerate(celdas, 1):
        if progreso:
            progreso(n - 1, len(celdas))
        with Image.open(ruta) as img:
            img = abrir_orientada(img)
            if posicion is None:
                lienzo.paste(ImageOps.fit(img, (w, h), Image.Resampling.LANCZOS), (x, y))
                continue
            # Tamano real: solo se recorta la parte de la imagen que cae dentro del hueco.
            fx, fy = posicion
            iw, ih = img.size
            x0, y0 = max(x, fx), max(y, fy)
            x1, y1 = min(x + w, fx + iw), min(y + h, fy + ih)
            if x1 > x0 and y1 > y0:
                lienzo.paste(img.crop((x0 - fx, y0 - fy, x1 - fx, y1 - fy)), (x0, y0))
    return estampar_marca(lienzo, marca_agua)


def planificar(modo, rutas, ancho, alto, filas, imagenes, separacion, rng, variedad=0.7):
    if modo == "original":
        return planificar_original(rutas, ancho, alto, imagenes, separacion, rng, variedad)
    return planificar_collage(rutas, ancho, alto, filas, separacion, rng)


def nombre_destino(salida: Path, res: str, sufijo: str = "") -> Path:
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = salida / f"collage_{res}_{marca}{sufijo}.png"
    n = 2
    while destino.exists():  # nunca sobrescribir un collage anterior
        destino = salida / f"collage_{res}_{marca}{sufijo}_{n}.png"
        n += 1
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera collages aleatorios de capturas de pantalla.")
    parser.add_argument("--res", choices=RESOLUCIONES, default="1080p", help="resolucion del collage (por defecto 1080p)")
    parser.add_argument("--modo", choices=["filas", "original"], default="filas", help="tipo de collage (por defecto filas)")
    parser.add_argument("--filas", type=int, default=3, help="modo filas: numero de filas (por defecto 3)")
    parser.add_argument("--imagenes", type=int, default=12, help="modo original: numero de imagenes (por defecto 12)")
    parser.add_argument("--variedad", type=int, default=70, help="modo original: variedad de tamanos 0-100 (por defecto 70)")
    parser.add_argument("--similares", action="store_true", help="usar fotos parecidas entre si (IA local CLIP)")
    parser.add_argument("--parecido", type=int, default=60, help="con --similares: cuanto se parecen, 0-100 (por defecto 60)")
    parser.add_argument("--buscar", help="texto a buscar en vez de una imagen de referencia (activa --similares)")
    parser.add_argument("--separacion", type=int, default=0, help="pixeles entre imagenes (por defecto 0)")
    parser.add_argument("--fondo", default="black", help="color de fondo/separacion (por defecto black)")
    parser.add_argument("--cantidad", type=int, default=1, help="cuantos collages generar (por defecto 1)")
    parser.add_argument("--semilla", type=int, help="semilla aleatoria para repetir un resultado")
    parser.add_argument("--origen", type=Path, default=ORIGEN_POR_DEFECTO, help="carpeta de imagenes")
    parser.add_argument("--periodo", choices=["hoy", "semana", "siempre"], default="siempre",
                        help="usar solo imagenes de hoy, de la ultima semana o de siempre (por defecto siempre)")
    parser.add_argument("--desde", type=parsear_fecha, help="solo imagenes desde esta fecha (dd/mm/aaaa)")
    parser.add_argument("--hasta", type=parsear_fecha, help="solo imagenes hasta esta fecha incluida (dd/mm/aaaa)")
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO, help="carpeta donde guardar los collages")
    args = parser.parse_args()

    if args.filas < 1 or args.imagenes < 1 or args.separacion < 0 or args.cantidad < 1:
        parser.error("--filas, --imagenes y --cantidad deben ser >= 1 y --separacion >= 0")
    if not 0 <= args.variedad <= 100:
        parser.error("--variedad debe estar entre 0 y 100")

    if not args.origen.is_dir():
        print(f"No existe la carpeta de origen: {args.origen}", file=sys.stderr)
        return 1
    if args.desde or args.hasta:
        args.periodo = "rango"
    rutas = filtrar_por_periodo(buscar_imagenes(args.origen), args.periodo, args.desde, args.hasta)
    if not rutas:
        print(f"No se encontraron imagenes en {args.origen} (periodo: {args.periodo})", file=sys.stderr)
        return 1

    ancho, alto = RESOLUCIONES[args.res]
    args.salida.mkdir(parents=True, exist_ok=True)
    semilla = args.semilla if args.semilla is not None else random.randrange(10**9)
    rng = random.Random(semilla)

    indice = referencia = None
    if args.similares or args.buscar:
        import similitud  # importacion diferida: similitud importa este modulo

        if not similitud.ia_instalada():
            print("Faltan librerias de la IA (pip install onnxruntime numpy)", file=sys.stderr)
            return 1
        if not similitud.modelo_descargado():
            print("Falta el modelo de IA: python similitud.py --descargar", file=sys.stderr)
            return 1
        indice = similitud.IndiceClip()
        if indice.faltan(rutas):
            indice.analizar(rutas, progreso=lambda h, t: print(f"\rAnalizando imagenes {h}/{t}", end="", flush=True))
            print()
        if args.buscar:
            referencia = indice.texto(args.buscar)

    for i in range(args.cantidad):
        usadas = rutas
        if indice:
            minimo = similitud.minimo_parecidas(args.modo, args.filas, args.imagenes)
            ancla, usadas = similitud.seleccionar_parecidas(rutas, indice, semilla + i, args.parecido / 100, minimo,
                                                            referencia)
        celdas = planificar(args.modo, usadas, ancho, alto, args.filas, args.imagenes, args.separacion, rng,
                            args.variedad / 100)
        collage = renderizar_collage(celdas, ancho, alto, args.fondo)
        sufijo = f"_{i + 1}" if args.cantidad > 1 else ""
        destino = nombre_destino(args.salida, args.res, sufijo)
        collage.save(destino)
        print(f"Guardado: {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
