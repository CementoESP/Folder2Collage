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

"""Interfaz grafica para collage.py.

La vista previa dibuja la distribucion real del collage con bloques de colores,
sin mostrar el contenido de ninguna imagen. Al generar se usa exactamente esa
misma distribucion y la vista previa pasa a mostrar el collage generado, hasta
que se pide una nueva distribucion o se cambia algun parametro.

Los textos estan en idiomas/*.json (ver i18n.py).

Uso:
    python collage_gui.py      (o doble clic en Folder2Collage.pyw, sin consola)

    Folder2Collage.exe --descargar-ia   descarga el modelo de IA sin abrir la ventana

Atajos:
    Ctrl+Enter  generar collage
    F5          nueva distribucion
"""

import colorsys
import ctypes
import json
import os
import random
import sys
import threading
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import colorchooser, filedialog
from tkinter import font as tkfont

import customtkinter as ctk
from PIL import Image, ImageTk

import i18n
import rutas
import similitud
from collage import (
    ORIGEN_POR_DEFECTO,
    RESOLUCIONES,
    SALIDA_POR_DEFECTO,
    buscar_imagenes,
    filtrar_por_periodo,
    parsear_fecha,
    leer_tamano,
    nombre_destino,
    planificar,
    renderizar_collage,
)
from i18n import t, tn

CONFIG = rutas.CONFIG

# Colores como (tema claro, tema oscuro).
ACENTO = ("#4F5BD5", "#6C78FF")
ACENTO_HOVER = ("#3E49B8", "#5763E6")
FONDO_APP = ("#ECEEF4", "#0F1115")
TARJETA = ("#FFFFFF", "#181B22")
BORDE = ("#E0E3EB", "#262A34")
CAMPO = ("#F4F5F9", "#11141A")
SECUNDARIO = ("#E8EAF2", "#242834")
SECUNDARIO_HOVER = ("#DCDFEA", "#2D3240")
TEXTO = ("#1A1D26", "#E7E9EF")
TEXTO_SUAVE = ("#6B7181", "#8A91A2")
PELIGRO = ("#D64545", "#FF6B6B")
EXITO = ("#1F9D63", "#3DDC97")
SOMBRA = ("#D3D7E2", "#07080B")
TOOLTIP = ("#1E2130", "#EEF0F6")
TOOLTIP_TEXTO = ("#F2F3F7", "#1A1D26")

RESOLUCIONES_UI = {"1080p": "1080p", "2k": "2K", "4k": "4K"}
MODOS = ("filas", "original")
APARIENCIAS = ("light", "dark", "system")
PERIODOS = ("hoy", "semana", "siempre", "rango")
SIMILITUDES = ("no", "clip")
FONDOS_RAPIDOS = ["#000000", "#FFFFFF", "#1C1C1E", "#F3EEE6", "#24324A"]
LIMITES = {"parecido": (0, 100), "filas": (1, 12), "imagenes": (1, 500), "variedad": (0, 100), "separacion": (0, 40), "cantidad": (1, 50)}


def tono(par):
    """Elige el color del par segun el tema activo (para widgets de tkinter puro)."""
    return par[1] if ctk.get_appearance_mode() == "Dark" else par[0]


def acotar(valor, nombre):
    minimo, maximo = LIMITES[nombre]
    return max(minimo, min(maximo, valor))


def rect_redondeado(c: tk.Canvas, x0, y0, x1, y1, r, **kw):
    pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
           x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
    return c.create_polygon(pts, smooth=True, **kw)


def es_oscuro(color_hex: str) -> bool:
    r, g, b = (int(color_hex[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b < 140


class App(ctk.CTk):
    def __init__(self):
        config = self._cargar_config()
        self.idioma_config = config.get("idioma", "auto")
        i18n.usar(self.idioma_config)
        self.apariencia = config.get("apariencia", "system") if config.get("apariencia") in APARIENCIAS else "system"
        ctk.set_appearance_mode(self.apariencia)
        super().__init__(fg_color=FONDO_APP)
        self.title(rutas.APP_NOMBRE)
        try:
            self.iconbitmap(str(rutas.RECURSOS / "recursos" / "icono.ico"))
        except tk.TclError:
            pass
        self.geometry("1320x820")
        self.minsize(1060, 680)
        self.reiniciar = False  # al cambiar de idioma se vuelve a crear la ventana

        self.f_marca = ctk.CTkFont("Segoe UI", 26, "bold")
        self.f_titulo = ctk.CTkFont("Segoe UI", 20, "bold")
        self.f_seccion = ctk.CTkFont("Segoe UI", 11, "bold")
        self.f_normal = ctk.CTkFont("Segoe UI", 13)
        self.f_pequena = ctk.CTkFont("Segoe UI", 12)
        self.f_boton = ctk.CTkFont("Segoe UI", 15, "bold")
        # Fuentes del lienzo (tkinter puro, sin el escalado de customtkinter).
        self.f_lienzo = tkfont.Font(family="Segoe UI", size=9)
        self.f_lienzo_num = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.f_tooltip = tkfont.Font(family="Segoe UI", size=10)

        self.origen = tk.StringVar(value=config.get("origen", str(ORIGEN_POR_DEFECTO)))
        self.salida = tk.StringVar(value=config.get("salida", str(SALIDA_POR_DEFECTO)))
        self.res = tk.StringVar(value=config.get("res", "1080p") if config.get("res") in RESOLUCIONES else "1080p")
        self.modo = tk.StringVar(value=config.get("modo", "filas") if config.get("modo") in MODOS else "filas")
        self.filas = tk.IntVar(value=acotar(int(config.get("filas", 3)), "filas"))
        self.imagenes = tk.IntVar(value=acotar(int(config.get("imagenes", 12)), "imagenes"))
        self.variedad = tk.IntVar(value=acotar(int(config.get("variedad", 70)), "variedad"))
        self.separacion = tk.IntVar(value=acotar(int(config.get("separacion", 0)), "separacion"))
        self.cantidad = tk.IntVar(value=acotar(int(config.get("cantidad", 1)), "cantidad"))
        self.semilla = tk.StringVar(value=str(random.randrange(10**9)))
        self.periodo = config.get("periodo", "siempre") if config.get("periodo") in PERIODOS else "siempre"
        self.desde = tk.StringVar(value=self._fecha_guardada(config.get("desde"), date.today() - timedelta(days=30)))
        self.hasta = tk.StringVar(value=self._fecha_guardada(config.get("hasta"), date.today()))
        self._pendiente_fechas = None
        self.auto_semilla = tk.BooleanVar(value=bool(config.get("auto_semilla", True)))
        self.fondo = config.get("fondo", "#000000")
        self.metodo_sim = "clip" if config.get("similitud") in ("clip", "colores") else "no"  # "colores" ya no existe
        self.parecido = tk.IntVar(value=acotar(int(config.get("parecido", 60)), "parecido"))
        self.busqueda = tk.StringVar(value=config.get("busqueda", ""))
        self.indice_clip: similitud.IndiceClip | None = None
        self._analisis = None  # analisis de huellas en segundo plano
        self._descarga = None  # descarga del modelo de IA en segundo plano
        self._textos: dict[str, list[float]] = {}  # huellas CLIP de las busquedas por texto
        self._calculando_texto = None
        self.ancla = None  # imagen de referencia de la similitud

        self.todas_rutas: list[Path] = []  # todas las de la carpeta
        self.rutas: list[Path] = []  # las que pasan el filtro de fecha
        self.celdas = []
        self.hover = None
        self._geom = None
        self._pendiente = None
        self._generando = False
        self._ultimo_guardado: Path | None = None
        self.resultado: Image.Image | None = None  # miniatura del ultimo collage generado, mostrada en el lienzo
        self._conservar_resultado = False  # el cambio de semilla automatico tras generar no lo oculta
        self._foto = None  # (tamano, PhotoImage, origen) de la miniatura ya escalada al lienzo

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._construir_panel()
        self._construir_principal()

        for var in (self.res, self.modo, self.filas, self.imagenes, self.variedad, self.separacion, self.semilla,
                    self.parecido, self.busqueda):
            var.trace_add("write", lambda *_: self.programar_preview())
        self.bind("<Control-Return>", lambda _: self.generar())
        self.bind("<F5>", lambda _: self.nueva_semilla())
        self.protocol("WM_DELETE_WINDOW", self.cerrar)

        self.cambiar_modo(self.modo.get())
        self.cambiar_similitud(self.metodo_sim)
        self.recargar_origen()

    # ================= configuracion =================

    @staticmethod
    def _cargar_config() -> dict:
        try:
            return json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _fecha_guardada(texto, por_defecto: date) -> str:
        """Fecha de los ajustes en el formato del idioma actual (puede venir de otro idioma)."""
        if texto is None:
            return por_defecto.strftime(t("fecha.formato"))
        try:
            return parsear_fecha(texto).strftime(t("fecha.formato")) if texto.strip() else ""
        except ValueError:
            return texto

    def _guardar_config(self):
        datos = {"origen": self.origen.get(), "salida": self.salida.get(), "res": self.res.get(),
                 "modo": self.modo.get(), "fondo": self.fondo, "periodo": self.periodo,
                 "desde": self.desde.get(), "hasta": self.hasta.get(),
                 "auto_semilla": bool(self.auto_semilla.get()),
                 "similitud": self.metodo_sim, "busqueda": self.busqueda.get(),
                 "apariencia": self.apariencia, "idioma": self.idioma_config}
        for nombre in ("filas", "imagenes", "variedad", "separacion", "cantidad", "parecido"):
            try:
                datos[nombre] = int(getattr(self, nombre).get())
            except (tk.TclError, ValueError):
                pass
        try:
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            CONFIG.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def cerrar(self):
        for tarea in (self._analisis, self._descarga):
            if tarea:
                tarea["cancelar"].set()
        self._guardar_config()
        for tarea in self.tk.call("after", "info"):  # tareas pendientes (propias y de customtkinter)
            self.after_cancel(tarea)
        self.destroy()

    def cambiar_idioma(self, nombre):
        codigo = next(c for c, n in i18n.IDIOMAS.items() if n == nombre)
        if codigo == i18n.idioma:
            return
        self.idioma_config = codigo
        self.reiniciar = True
        self.cerrar()

    # ================= piezas de interfaz =================

    def _seccion(self, padre, titulo):
        tarjeta = ctk.CTkFrame(padre, fg_color=TARJETA, corner_radius=14, border_width=1, border_color=BORDE)
        tarjeta.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(tarjeta, text=titulo.upper(), font=self.f_seccion, text_color=TEXTO_SUAVE,
                     anchor="w", height=20).pack(fill="x", padx=16, pady=(12, 6))
        cuerpo = ctk.CTkFrame(tarjeta, fg_color="transparent")
        cuerpo.pack(fill="x", padx=16, pady=(0, 14))
        return cuerpo

    def _etiqueta(self, padre, texto, pady=(0, 4)):
        ctk.CTkLabel(padre, text=texto, font=self.f_pequena, text_color=TEXTO_SUAVE, anchor="w",
                     height=18).pack(fill="x", pady=pady)

    def _boton_secundario(self, padre, texto, comando, **kw):
        opciones = dict(fg_color=SECUNDARIO, hover_color=SECUNDARIO_HOVER, text_color=TEXTO,
                        font=self.f_normal, corner_radius=10, height=34)
        opciones.update(kw)
        return ctk.CTkButton(padre, text=texto, command=comando, **opciones)

    def _segmentado(self, padre, opciones, actual, al_elegir, **kw):
        """Boton segmentado. opciones: {valor: texto}; al_elegir recibe el valor.
        Para cambiarlo desde el codigo: boton.set(boton.opciones[valor])."""
        inversa = {texto: valor for valor, texto in opciones.items()}
        estilo = dict(font=self.f_normal, height=34, corner_radius=10, selected_color=ACENTO,
                      selected_hover_color=ACENTO_HOVER, unselected_color=SECUNDARIO,
                      unselected_hover_color=SECUNDARIO_HOVER, fg_color=SECUNDARIO, text_color=TEXTO)
        estilo.update(kw)
        boton = ctk.CTkSegmentedButton(padre, values=list(opciones.values()),
                                       command=lambda texto: al_elegir(inversa[texto]), **estilo)
        boton.opciones = opciones
        if actual in opciones:
            boton.set(opciones[actual])
        return boton

    def _entrada(self, padre, variable, **kw):
        return ctk.CTkEntry(padre, textvariable=variable, fg_color=CAMPO, border_color=BORDE, border_width=1,
                            text_color=TEXTO, font=self.f_normal, corner_radius=10, height=34, **kw)

    def _campo_carpeta(self, padre, titulo, variable, al_cambiar=None):
        self._etiqueta(padre, titulo)
        fila = ctk.CTkFrame(padre, fg_color="transparent")
        fila.pack(fill="x")
        entrada = self._entrada(fila, variable)
        entrada.pack(side="left", fill="x", expand=True)

        def elegir():
            carpeta = filedialog.askdirectory(initialdir=variable.get() or None, parent=self)
            if carpeta:
                variable.set(str(Path(carpeta)))
                if al_cambiar:
                    al_cambiar()

        self._boton_secundario(fila, "…", elegir, width=38).pack(side="left", padx=(6, 0))
        if al_cambiar:
            entrada.bind("<Return>", lambda _: al_cambiar())
            entrada.bind("<FocusOut>", lambda _: al_cambiar())

    def _slider(self, padre, titulo, variable, nombre, sufijo=""):
        minimo, maximo = LIMITES[nombre]
        cabecera = ctk.CTkFrame(padre, fg_color="transparent")
        cabecera.pack(fill="x")
        ctk.CTkLabel(cabecera, text=titulo, font=self.f_pequena, text_color=TEXTO_SUAVE, height=18).pack(side="left")
        valor = ctk.CTkLabel(cabecera, text="", font=self.f_seccion, text_color=TEXTO, height=18)
        valor.pack(side="right")

        def refrescar(*_):
            try:
                valor.configure(text=f"{variable.get()}{sufijo}")
            except tk.TclError:
                pass

        variable.trace_add("write", refrescar)
        refrescar()
        slider = ctk.CTkSlider(padre, from_=minimo, to=maximo, number_of_steps=maximo - minimo,
                               command=lambda v: variable.set(int(round(v))), progress_color=ACENTO,
                               button_color=ACENTO, button_hover_color=ACENTO_HOVER, fg_color=SECUNDARIO, height=18)
        slider.set(variable.get())
        slider.pack(fill="x", pady=(6, 12))

        def sincronizar(*_):  # si el valor cambia desde fuera (ajustes guardados, codigo), mover el deslizador
            try:
                if round(slider.get()) != variable.get():
                    slider.set(variable.get())
            except tk.TclError:
                pass

        variable.trace_add("write", sincronizar)
        return slider

    def _stepper(self, padre, titulo, variable, nombre):
        self._etiqueta(padre, titulo)
        fila = ctk.CTkFrame(padre, fg_color="transparent")
        fila.pack(fill="x", pady=(0, 12))

        def normalizar(*_):
            try:
                variable.set(acotar(int(variable.get()), nombre))
            except (tk.TclError, ValueError):
                variable.set(LIMITES[nombre][0])

        def sumar(delta):
            try:
                variable.set(acotar(int(variable.get()) + delta, nombre))
            except (tk.TclError, ValueError):
                normalizar()

        self._boton_secundario(fila, "−", lambda: sumar(-1), width=38).pack(side="left")
        entrada = self._entrada(fila, variable, width=80, justify="center")
        entrada.pack(side="left", padx=6)
        entrada.bind("<Return>", normalizar)
        entrada.bind("<FocusOut>", normalizar)
        self._boton_secundario(fila, "+", lambda: sumar(1), width=38).pack(side="left")

    # ================= panel lateral =================

    def _construir_panel(self):
        lateral = ctk.CTkFrame(self, fg_color="transparent", width=360)
        lateral.grid(row=0, column=0, sticky="ns", padx=(20, 16), pady=20)
        lateral.grid_propagate(False)
        lateral.grid_rowconfigure(1, weight=1)
        lateral.grid_columnconfigure(0, weight=1)

        marca = ctk.CTkFrame(lateral, fg_color="transparent")
        marca.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        ctk.CTkLabel(marca, text=rutas.APP_NOMBRE, font=self.f_marca, text_color=TEXTO, anchor="w",
                     height=34).pack(fill="x")
        ctk.CTkLabel(marca, text=t("app.subtitulo"), font=self.f_normal,
                     text_color=TEXTO_SUAVE, anchor="w", height=20).pack(fill="x")

        panel = ctk.CTkScrollableFrame(lateral, fg_color="transparent", scrollbar_button_color=SECUNDARIO,
                                       scrollbar_button_hover_color=SECUNDARIO_HOVER)
        panel.grid(row=1, column=0, sticky="nsew")

        # --- Carpetas ---
        cuerpo = self._seccion(panel, t("sec.carpetas"))
        self._campo_carpeta(cuerpo, t("carpetas.origen"), self.origen, self.recargar_origen)
        self._etiqueta(cuerpo, t("carpetas.usar"), pady=(10, 4))
        self.seg_periodo = self._segmentado(cuerpo, {p: t(f"periodo.{p}") for p in PERIODOS}, self.periodo,
                                            self.cambiar_periodo)
        self.seg_periodo.pack(fill="x")

        # El rango de fechas solo se muestra en modo "Rango" (se coloca antes del contador).
        self.marco_rango = ctk.CTkFrame(cuerpo, fg_color="transparent")
        self.marco_rango.grid_columnconfigure((0, 1), weight=1, uniform="fecha")
        self.entradas_fecha = []
        for col, (titulo, variable) in enumerate(((t("fecha.desde"), self.desde), (t("fecha.hasta"), self.hasta))):
            ctk.CTkLabel(self.marco_rango, text=titulo, font=self.f_pequena, text_color=TEXTO_SUAVE, anchor="w",
                         height=18).grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0))
            entrada = self._entrada(self.marco_rango, variable, placeholder_text=t("fecha.ayuda"))
            entrada.grid(row=1, column=col, sticky="ew", padx=(0 if col == 0 else 6, 0))
            variable.trace_add("write", lambda *_: self._programar_fechas())
            self.entradas_fecha.append(entrada)
        self.lbl_encontradas = ctk.CTkLabel(cuerpo, text="", font=self.f_pequena, text_color=TEXTO_SUAVE,
                                            anchor="w", justify="left", wraplength=290)
        self.lbl_encontradas.pack(fill="x", pady=(6, 10))
        if self.periodo == "rango":
            self.marco_rango.pack(fill="x", pady=(10, 0), before=self.lbl_encontradas)
        self._campo_carpeta(cuerpo, t("carpetas.salida"), self.salida)

        # --- Resolucion ---
        cuerpo = self._seccion(panel, t("sec.resolucion"))
        self._segmentado(cuerpo, RESOLUCIONES_UI, self.res.get(), self.res.set).pack(fill="x")
        self.lbl_res = ctk.CTkLabel(cuerpo, text="", font=self.f_pequena, text_color=TEXTO_SUAVE, anchor="w", height=18)
        self.lbl_res.pack(fill="x", pady=(6, 0))

        # --- Modo ---
        cuerpo = self._seccion(panel, t("sec.modo"))
        self.seg_modo = self._segmentado(cuerpo, {m: t(f"modo.{m}") for m in MODOS}, self.modo.get(),
                                         self.cambiar_modo)
        self.seg_modo.pack(fill="x")
        self.lbl_modo = ctk.CTkLabel(cuerpo, text="", font=self.f_pequena, text_color=TEXTO_SUAVE, anchor="w",
                                     justify="left", wraplength=290)
        self.lbl_modo.pack(fill="x", pady=(8, 12))

        self.opciones_modo = ctk.CTkFrame(cuerpo, fg_color="transparent")
        self.opciones_modo.pack(fill="x")
        self.marco_filas = ctk.CTkFrame(self.opciones_modo, fg_color="transparent")
        self._slider(self.marco_filas, t("ajuste.filas"), self.filas, "filas")
        self.marco_original = ctk.CTkFrame(self.opciones_modo, fg_color="transparent")
        self._stepper(self.marco_original, t("ajuste.imagenes"), self.imagenes, "imagenes")
        self._slider(self.marco_original, t("ajuste.variedad"), self.variedad, "variedad", "%")

        # --- Fotos parecidas ---
        cuerpo = self._seccion(panel, t("sec.similares"))
        self.seg_sim = self._segmentado(cuerpo, {s: t(f"sim.{s}") for s in SIMILITUDES}, self.metodo_sim,
                                        self.cambiar_similitud)
        self.seg_sim.pack(fill="x")
        self.lbl_sim = ctk.CTkLabel(cuerpo, text="", font=self.f_pequena, text_color=TEXTO_SUAVE, anchor="w",
                                    justify="left", wraplength=290)
        self.lbl_sim.pack(fill="x", pady=(8, 0))
        # Si falta el modelo de IA: explicacion y boton de descarga (solo se descarga si se pulsa).
        self.marco_descarga = ctk.CTkFrame(cuerpo, fg_color="transparent")
        self.lbl_descarga = ctk.CTkLabel(self.marco_descarga, text="", font=self.f_pequena, text_color=TEXTO,
                                         anchor="w", justify="left", wraplength=290)
        self.lbl_descarga.pack(fill="x", pady=(12, 10))
        self.progreso_descarga = ctk.CTkProgressBar(self.marco_descarga, progress_color=ACENTO, fg_color=SECUNDARIO,
                                                    height=6)
        fila = ctk.CTkFrame(self.marco_descarga, fg_color="transparent")
        fila.pack(fill="x")
        self.btn_descargar = ctk.CTkButton(fila, text=t("ia.descargar", mb=similitud.TAMANO_MODELO_MB),
                                           command=self.descargar_ia, height=34, corner_radius=10,
                                           font=self.f_normal, fg_color=ACENTO, hover_color=ACENTO_HOVER,
                                           text_color="#FFFFFF")
        self.btn_descargar.pack(side="left")
        self.btn_cancelar_descarga = self._boton_secundario(fila, t("ia.cancelar"), self._cancelar_descarga)
        self.marco_sim = ctk.CTkFrame(cuerpo, fg_color="transparent")
        ctk.CTkFrame(self.marco_sim, fg_color="transparent", height=12).pack(fill="x")
        self._slider(self.marco_sim, t("ajuste.parecido"), self.parecido, "parecido", "%")
        self._etiqueta(self.marco_sim, t("sim.buscar"))
        self._entrada(self.marco_sim, self.busqueda).pack(fill="x")
        ctk.CTkLabel(self.marco_sim, text=t("sim.buscar.ayuda"), font=self.f_pequena, text_color=TEXTO_SUAVE,
                     anchor="w", justify="left", wraplength=290).pack(fill="x", pady=(4, 10))
        self.lbl_sim_estado = ctk.CTkLabel(self.marco_sim, text="", font=self.f_pequena, text_color=TEXTO_SUAVE,
                                           anchor="w", height=18)
        self.lbl_sim_estado.pack(fill="x")
        self.progreso_sim = ctk.CTkProgressBar(self.marco_sim, progress_color=ACENTO, fg_color=SECUNDARIO, height=6)
        self.progreso_sim.set(0)

        # --- Estilo ---
        cuerpo = self._seccion(panel, t("sec.estilo"))
        self._slider(cuerpo, t("estilo.separacion"), self.separacion, "separacion", " px")
        self._etiqueta(cuerpo, t("estilo.fondo"))
        fila = ctk.CTkFrame(cuerpo, fg_color="transparent")
        fila.pack(fill="x")
        self.muestras = {}
        for color in FONDOS_RAPIDOS:
            b = ctk.CTkButton(fila, text="", width=30, height=30, corner_radius=15, fg_color=color, hover_color=color,
                              border_width=2, command=lambda c=color: self.elegir_fondo(c))
            b.pack(side="left", padx=(0, 8))
            self.muestras[color] = b
        self.muestra_propia = ctk.CTkButton(fila, text="", width=30, height=30, corner_radius=15, border_width=2,
                                            command=self.fondo_personalizado)
        self.muestra_propia.pack(side="left", padx=(0, 8))
        self._boton_secundario(fila, t("estilo.otro"), self.fondo_personalizado, width=60, height=30,
                               font=self.f_pequena).pack(side="left")
        self._refrescar_muestras()

        # --- Generacion ---
        cuerpo = self._seccion(panel, t("sec.generacion"))
        self._etiqueta(cuerpo, t("gen.semilla"))
        fila = ctk.CTkFrame(cuerpo, fg_color="transparent")
        fila.pack(fill="x", pady=(0, 12))
        self._entrada(fila, self.semilla).pack(side="left", fill="x", expand=True)
        self._boton_secundario(fila, "⚄", self.nueva_semilla, width=38,
                               font=ctk.CTkFont("Segoe UI Symbol", 18)).pack(side="left", padx=(6, 0))
        ctk.CTkSwitch(cuerpo, text=t("gen.auto"), variable=self.auto_semilla,
                      font=self.f_pequena, text_color=TEXTO, progress_color=ACENTO, button_color="#FFFFFF",
                      button_hover_color="#F0F0F5", fg_color=SECUNDARIO,
                      command=self._guardar_config).pack(fill="x", pady=(0, 14))
        self._stepper(cuerpo, t("gen.cantidad"), self.cantidad, "cantidad")

    # ================= zona principal =================

    def _construir_principal(self):
        principal = ctk.CTkFrame(self, fg_color="transparent")
        principal.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        principal.grid_columnconfigure(0, weight=1)
        principal.grid_rowconfigure(1, weight=1)

        cabecera = ctk.CTkFrame(principal, fg_color="transparent")
        cabecera.grid(row=0, column=0, sticky="ew", pady=(6, 14))
        ctk.CTkLabel(cabecera, text=t("vista.titulo"), font=self.f_titulo, text_color=TEXTO, height=30).pack(side="left")
        self.lbl_resumen = ctk.CTkLabel(cabecera, text="", font=self.f_normal, text_color=TEXTO_SUAVE, height=30)
        self.lbl_resumen.pack(side="left", padx=(14, 0))
        self._segmentado(cabecera, {a: t(f"apariencia.{a}") for a in APARIENCIAS}, self.apariencia,
                         self.cambiar_apariencia, font=self.f_pequena, height=30).pack(side="right")
        menu_idioma = ctk.CTkOptionMenu(cabecera, values=list(i18n.IDIOMAS.values()), command=self.cambiar_idioma,
                                        font=self.f_pequena, dropdown_font=self.f_pequena, height=30, width=118,
                                        corner_radius=10, fg_color=SECUNDARIO, button_color=SECUNDARIO,
                                        button_hover_color=SECUNDARIO_HOVER, text_color=TEXTO,
                                        dropdown_fg_color=TARJETA, dropdown_hover_color=SECUNDARIO,
                                        dropdown_text_color=TEXTO)
        menu_idioma.set(i18n.IDIOMAS[i18n.idioma])
        menu_idioma.pack(side="right", padx=(0, 10))

        tarjeta = ctk.CTkFrame(principal, fg_color=TARJETA, corner_radius=16, border_width=1, border_color=BORDE)
        tarjeta.grid(row=1, column=0, sticky="nsew")
        self.lienzo = tk.Canvas(tarjeta, highlightthickness=0, bd=0, bg=tono(TARJETA))
        self.lienzo.pack(fill="both", expand=True, padx=12, pady=12)
        self.lienzo.bind("<Configure>", lambda _: self.dibujar())
        self.lienzo.bind("<Motion>", self._mover_raton)
        self.lienzo.bind("<Leave>", lambda _: self._mover_raton(None))

        self.fila_chips = ctk.CTkFrame(principal, fg_color="transparent")
        self.fila_chips.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self._chips, self._ancho_chips = [], 0
        self.fila_chips.bind("<Configure>", self._reajustar_chips)

        barra = ctk.CTkFrame(principal, fg_color=TARJETA, corner_radius=16, border_width=1, border_color=BORDE)
        barra.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        barra.grid_columnconfigure(2, weight=1)
        self._boton_secundario(barra, t("boton.nueva"), self.nueva_semilla, height=40,
                               width=190).grid(row=0, column=0, padx=(14, 8), pady=14)
        self._boton_secundario(barra, t("boton.carpeta"), self.abrir_salida, height=40,
                               width=130).grid(row=0, column=1, padx=(0, 8), pady=14)

        estado = ctk.CTkFrame(barra, fg_color="transparent")
        estado.grid(row=0, column=2, sticky="ew", padx=8)
        estado.grid_columnconfigure(0, weight=1)
        self.lbl_estado = ctk.CTkLabel(estado, text=t("estado.atajos"),
                                       font=self.f_pequena, text_color=TEXTO_SUAVE, anchor="w", height=18)
        self.lbl_estado.grid(row=0, column=0, sticky="ew")
        self.progreso = ctk.CTkProgressBar(estado, progress_color=ACENTO, fg_color=SECUNDARIO, height=6)
        self.progreso.set(0)
        self.btn_abrir_imagen = self._boton_secundario(estado, t("boton.imagen"), self.abrir_ultimo, height=28,
                                                       width=110, font=self.f_pequena)

        self.btn_generar = ctk.CTkButton(barra, text=t("boton.generar"), command=self.generar, height=44, width=210,
                                         corner_radius=12, font=self.f_boton, fg_color=ACENTO,
                                         hover_color=ACENTO_HOVER, text_color="#FFFFFF")
        self.btn_generar.grid(row=0, column=3, padx=(8, 14), pady=14)

    # ================= acciones =================

    def cambiar_modo(self, modo):
        self.modo.set(modo)
        self.lbl_modo.configure(text=t(f"modo.{modo}.desc"))
        self.marco_filas.pack_forget()
        self.marco_original.pack_forget()
        (self.marco_original if modo == "original" else self.marco_filas).pack(fill="x")

    def cambiar_similitud(self, metodo):
        self.metodo_sim = metodo
        self.seg_sim.set(self.seg_sim.opciones[metodo])
        if metodo == "clip" and not similitud.ia_instalada():
            self.lbl_sim.configure(text=t("sim.no_instalado"), text_color=PELIGRO)
        else:
            self.lbl_sim.configure(text=t(f"sim.{metodo}.desc"), text_color=TEXTO_SUAVE)
        self._mostrar_opciones_ia()
        self.programar_preview()

    def _mostrar_opciones_ia(self):
        """Opciones de similitud si el modelo esta descargado; si no, el aviso de descarga."""
        self.marco_sim.pack_forget()
        self.marco_descarga.pack_forget()
        if self.metodo_sim == "no" or not similitud.ia_instalada():
            return
        if similitud.modelo_descargado():
            self.marco_sim.pack(fill="x")
        else:
            if not self._descargando():
                self.lbl_descarga.configure(text=t("ia.descargar.desc", mb=similitud.TAMANO_MODELO_MB),
                                            text_color=TEXTO)
            self.marco_descarga.pack(fill="x")

    # ---------- descarga del modelo de IA ----------

    def _descargando(self) -> bool:
        return bool(self._descarga and self._descarga["hilo"].is_alive())

    def descargar_ia(self):
        if self._descargando():
            return
        avance = {"hechos": 0, "total": 1, "error": None, "cancelado": False}
        cancelar = threading.Event()

        def trabajo():
            try:
                similitud.descargar_modelo(lambda h, tot: avance.update(hechos=h, total=tot), cancelar.is_set)
            except similitud.Cancelado:
                avance["cancelado"] = True
            except Exception as e:
                avance["error"] = str(e)

        hilo = threading.Thread(target=trabajo, daemon=True)
        self._descarga = {"hilo": hilo, "avance": avance, "cancelar": cancelar}
        hilo.start()
        self.btn_descargar.pack_forget()
        self.btn_cancelar_descarga.pack(side="left")
        self.progreso_descarga.set(0)
        self.progreso_descarga.pack(fill="x", pady=(0, 10), before=self.btn_cancelar_descarga.master)
        self._vigilar_descarga()

    def _cancelar_descarga(self):
        if self._descarga:
            self._descarga["cancelar"].set()

    def _vigilar_descarga(self):
        avance = self._descarga["avance"]
        if self._descarga["hilo"].is_alive():
            self.lbl_descarga.configure(text=t("ia.descargando", hecho=round(avance["hechos"] / 1e6),
                                               total=round(avance["total"] / 1e6)), text_color=TEXTO)
            self.progreso_descarga.set(avance["hechos"] / max(1, avance["total"]))
            self.after(200, self._vigilar_descarga)
            return
        self.progreso_descarga.pack_forget()
        self.btn_cancelar_descarga.pack_forget()
        self.btn_descargar.pack(side="left")
        if avance["error"]:
            self.lbl_descarga.configure(text=t("ia.error", error=avance["error"]), text_color=PELIGRO)
        else:
            self._mostrar_opciones_ia()  # descargado (o cancelado: vuelve al aviso)
            self.programar_preview()

    # ---------- similitud ----------

    def _indice(self):
        if self.metodo_sim == "no" or not similitud.ia_instalada() or not similitud.modelo_descargado():
            return None
        if self.indice_clip is None:
            self.indice_clip = similitud.IndiceClip()
        return self.indice_clip

    def _analizando(self) -> bool:
        return bool(self._analisis and self._analisis["hilo"].is_alive())

    def _iniciar_analisis(self, indice, rutas):
        if self._analizando():
            return
        avance = {"hechas": 0, "total": len(indice.faltan(rutas)), "error": None}
        cancelar = threading.Event()

        def trabajo():
            try:
                indice.analizar(rutas, progreso=lambda h, t: avance.update(hechas=h, total=t),
                                cancelado=cancelar.is_set)
            except Exception as e:
                avance["error"] = str(e)

        hilo = threading.Thread(target=trabajo, daemon=True)
        self._analisis = {"hilo": hilo, "avance": avance, "cancelar": cancelar}
        hilo.start()
        self.progreso_sim.set(0)
        self.progreso_sim.pack(fill="x", pady=(6, 0))
        self._vigilar_analisis()

    def _vigilar_analisis(self):
        analisis = self._analisis
        avance = analisis["avance"]
        if analisis["hilo"].is_alive():
            if avance["hechas"] == 0:
                texto = t("sim.cargando")
            else:
                texto = t("sim.analizando", hechas=avance["hechas"], total=avance["total"])
            self.lbl_sim_estado.configure(text=texto, text_color=TEXTO)
            self.progreso_sim.set(avance["hechas"] / max(1, avance["total"]))
            self.after(200, self._vigilar_analisis)
            return
        self.progreso_sim.pack_forget()
        if avance["error"]:
            self.lbl_sim_estado.configure(text=t("sim.error", error=avance["error"]), text_color=PELIGRO)
        self.programar_preview()

    def _vector_texto(self, consulta):
        """Huella CLIP de la busqueda; None mientras se calcula en segundo plano."""
        if consulta in self._textos:
            return self._textos[consulta]
        if self._calculando_texto is None:
            self._calculando_texto = consulta
            indice = self._indice()

            def trabajo():
                try:
                    self._textos[consulta] = indice.texto(consulta)
                except Exception:
                    self._textos[consulta] = None
                self._calculando_texto = None
                self.after(0, self.programar_preview)

            threading.Thread(target=trabajo, daemon=True).start()
        return None

    def _preparar_similitud(self, modo, filas, imagenes, semilla):
        """Devuelve (indice, referencia, estado). estado: 'no', 'listo', 'esperando' o un mensaje de error."""
        if self.metodo_sim == "no" or not self.rutas:
            return None, None, "no"
        if not similitud.ia_instalada():
            return None, None, t("sim.no_instalado")
        if not similitud.modelo_descargado():
            return None, None, t("chip.falta_modelo")
        indice = self._indice()
        if self._analizando():
            return indice, None, "esperando"
        if indice.faltan(self.rutas):
            self._iniciar_analisis(indice, list(self.rutas))
            return indice, None, "esperando"
        consulta = self.busqueda.get().strip()
        if not consulta:
            return indice, None, "listo"
        if consulta in self._textos and self._textos[consulta] is None:
            return indice, None, t("sim.error_busqueda")
        referencia = self._vector_texto(consulta)
        return indice, referencia, "listo" if referencia is not None else "esperando"

    def cambiar_apariencia(self, valor):
        self.apariencia = valor
        ctk.set_appearance_mode(valor)
        self.after(60, self.dibujar)

    def elegir_fondo(self, color):
        self.fondo = color
        self.resultado = None  # el collage mostrado ya no corresponde a los ajustes
        self._refrescar_muestras()
        self.dibujar()

    def fondo_personalizado(self):
        color = colorchooser.askcolor(color=self.fondo, title=t("estilo.fondo"), parent=self)[1]
        if color:
            self.elegir_fondo(color.upper())

    def _refrescar_muestras(self):
        propio = self.fondo.upper() not in FONDOS_RAPIDOS
        for color, boton in self.muestras.items():
            boton.configure(border_color=ACENTO if color == self.fondo.upper() else BORDE)
        self.muestra_propia.configure(fg_color=self.fondo if propio else SECUNDARIO,
                                      hover_color=self.fondo if propio else SECUNDARIO_HOVER,
                                      border_color=ACENTO if propio else BORDE)

    def nueva_semilla(self):
        self.semilla.set(str(random.randrange(10**9)))

    def abrir_salida(self):
        carpeta = Path(self.salida.get())
        carpeta.mkdir(parents=True, exist_ok=True)
        os.startfile(carpeta)

    def abrir_ultimo(self):
        if self._ultimo_guardado and self._ultimo_guardado.exists():
            os.startfile(self._ultimo_guardado)

    def recargar_origen(self):
        origen = Path(self.origen.get())
        self.todas_rutas = buscar_imagenes(origen) if origen.is_dir() else []
        self.aplicar_periodo()

    def cambiar_periodo(self, periodo):
        self.periodo = periodo
        self.seg_periodo.set(self.seg_periodo.opciones[periodo])
        if periodo == "rango":
            self.marco_rango.pack(fill="x", pady=(10, 0), before=self.lbl_encontradas)
        else:
            self.marco_rango.pack_forget()
        self.aplicar_periodo()

    def _programar_fechas(self):
        if self.periodo != "rango":
            return
        if self._pendiente_fechas:
            self.after_cancel(self._pendiente_fechas)
        self._pendiente_fechas = self.after(400, self.aplicar_periodo)

    def _leer_rango(self):
        """Devuelve (desde, hasta, error). Un campo vacio significa sin limite por ese lado."""
        fechas, error = [], None
        for variable, entrada in zip((self.desde, self.hasta), self.entradas_fecha):
            texto = variable.get().strip()
            try:
                fechas.append(parsear_fecha(texto) if texto else None)
                entrada.configure(border_color=BORDE)
            except ValueError:
                fechas.append(None)
                entrada.configure(border_color=PELIGRO)
                error = t("fecha.invalida", formato=t("fecha.ayuda"))
        desde, hasta = fechas
        if not error and desde and hasta and desde > hasta:
            error = t("fecha.al_reves")
        return desde, hasta, error

    def _descripcion_periodo(self, desde=None, hasta=None):
        """Complemento para "N imagenes ...", o "" si no hay filtro."""
        formato = t("fecha.formato")
        if self.periodo in ("hoy", "semana"):
            return t(f"periodo.desc.{self.periodo}")
        if self.periodo == "rango":
            if desde and hasta:
                return t("periodo.desc.rango", desde=desde.strftime(formato), hasta=hasta.strftime(formato))
            if desde:
                return t("periodo.desc.desde", desde=desde.strftime(formato))
            if hasta:
                return t("periodo.desc.hasta", hasta=hasta.strftime(formato))
        return ""

    def aplicar_periodo(self):
        self._pendiente_fechas = None
        desde = hasta = error = None
        if self.periodo == "rango":
            desde, hasta, error = self._leer_rango()
        self.rutas = [] if error else filtrar_por_periodo(self.todas_rutas, self.periodo, desde, hasta)
        total, usadas = len(self.todas_rutas), len(self.rutas)
        periodo = self._descripcion_periodo(desde, hasta)
        if not Path(self.origen.get()).is_dir():
            self.lbl_encontradas.configure(text=t("origen.no_existe"), text_color=PELIGRO)
        elif error:
            self.lbl_encontradas.configure(text=error, text_color=PELIGRO)
        elif not total:
            self.lbl_encontradas.configure(text=t("origen.vacia"), text_color=PELIGRO)
        elif not usadas:
            self.lbl_encontradas.configure(text=t("origen.ninguna", periodo=periodo, total=total), text_color=PELIGRO)
        elif not periodo:
            self.lbl_encontradas.configure(text=tn("origen.encontradas", total), text_color=TEXTO_SUAVE)
        else:
            self.lbl_encontradas.configure(text=tn("origen.filtradas", usadas, periodo=periodo, total=total),
                                           text_color=TEXTO_SUAVE)
        self.programar_preview()

    def _estado(self, texto, color=TEXTO_SUAVE):
        self.lbl_estado.configure(text=texto, text_color=color)

    # ================= parametros y vista previa =================

    def leer_parametros(self):
        try:
            filas = int(self.filas.get())
            imagenes = int(self.imagenes.get())
            separacion = int(self.separacion.get())
            semilla = int(self.semilla.get())
        except (tk.TclError, ValueError):
            return None
        if filas < 1 or imagenes < 1 or separacion < 0:
            return None
        ancho, alto = RESOLUCIONES[self.res.get()]
        return self.modo.get(), ancho, alto, filas, imagenes, separacion, semilla, self.variedad.get() / 100

    def programar_preview(self):
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(180, self.actualizar_preview)

    def actualizar_preview(self):
        self._pendiente = None
        if self._conservar_resultado:  # semilla nueva automatica: se sigue viendo el collage generado
            self._conservar_resultado = False
            return
        self.resultado = None
        self.celdas = []
        self.hover = None
        params = self.leer_parametros()
        ancho, alto = RESOLUCIONES[self.res.get()]
        self.lbl_res.configure(text=t("res.pixeles", ancho=ancho, alto=alto))
        self.lbl_resumen.configure(text=f"{ancho} × {alto}  ·  {t(f'modo.{self.modo.get()}')}")

        chips = []
        self.ancla = None
        if params is None:
            chips.append((t("chip.semilla_mal"), PELIGRO))
        elif self.rutas:
            modo, ancho, alto, filas, imagenes, separacion, semilla, variedad = params
            usadas, chip_sim = self.rutas, None
            indice, referencia, estado = self._preparar_similitud(modo, filas, imagenes, semilla)
            if estado == "listo":
                minimo = similitud.minimo_parecidas(modo, filas, imagenes)
                self.ancla, usadas = similitud.seleccionar_parecidas(self.rutas, indice, semilla,
                                                                     self.parecido.get() / 100, minimo, referencia)
                consulta = self.busqueda.get().strip()
                chip_sim = (t("chip.parecidas_texto", texto=consulta) if referencia is not None
                            else t("chip.parecidas_imagen"), ACENTO)
                self.lbl_sim_estado.configure(text=t("sim.candidatas", n=len(usadas), total=len(self.rutas)),
                                              text_color=TEXTO_SUAVE)
            elif estado == "esperando":
                chip_sim = (t("chip.preparando"), TEXTO_SUAVE)
                if not self._analizando():
                    self.lbl_sim_estado.configure(text=t("sim.preparando"), text_color=TEXTO)
            elif estado != "no":
                chip_sim = (estado, PELIGRO)
            try:
                self.celdas = planificar(modo, usadas, ancho, alto, filas, imagenes, separacion,
                                         random.Random(semilla), variedad)
            except Exception as e:
                chips.append((t("error", error=e), PELIGRO))
            if self.celdas:
                chips.append((tn("chip.imagenes", len(self.celdas)), TEXTO))
                if modo == "original":
                    huecos = sum(1 for c in self.celdas if self._area_visible(c) < c[3] * c[4])
                    usado = sum(self._area_visible(c) for c in self.celdas)
                    total = sum(leer_tamano(c[0])[0] * leer_tamano(c[0])[1] for c in self.celdas)
                    chips.append((t("chip.visible", p=round(100 * usado / total)), TEXTO))
                    if huecos:
                        chips.append((tn("chip.huecos", huecos), PELIGRO))
                    else:
                        chips.append((t("chip.sin_huecos"), EXITO))
                else:
                    chips.append((tn("chip.filas", filas), TEXTO))
                if chip_sim:
                    chips.append(chip_sim)
                chips.append((t("chip.semilla", semilla=semilla), TEXTO_SUAVE))
        self._pintar_chips(chips)
        self.dibujar()

    def _pintar_chips(self, chips=None):
        """Etiquetas bajo la vista previa; si no caben en una linea, pasan a la siguiente."""
        if chips is not None:
            self._chips = chips
        for hijo in self.fila_chips.winfo_children():
            hijo.destroy()
        self._ancho_chips = disponible = self.fila_chips.winfo_width()
        escala = ctk.ScalingTracker.get_widget_scaling(self)
        fila, usado = None, 0
        for texto, color in self._chips:
            ancho = self.f_pequena.measure(texto) * escala + 2 * 10 + 16 * escala + 8
            if fila is None or (disponible > 1 and usado + ancho > disponible):
                primera = fila is None
                fila = ctk.CTkFrame(self.fila_chips, fg_color="transparent")
                fila.pack(fill="x", pady=(0 if primera else 6, 0))
                usado = 0
            ctk.CTkLabel(fila, text=texto, font=self.f_pequena, text_color=color, fg_color=SECUNDARIO,
                         corner_radius=8, height=28).pack(side="left", padx=(0, 8), ipadx=10)
            usado += ancho

    def _reajustar_chips(self, _evento=None):
        if abs(self.fila_chips.winfo_width() - self._ancho_chips) > 4:
            self._pintar_chips()

    @staticmethod
    def _area_visible(celda) -> int:
        """Pixeles del hueco cubiertos por la imagen (en modo tamano original puede no cubrirlo entero)."""
        ruta, x, y, w, h, posicion = celda
        if posicion is None:
            return w * h
        iw, ih = leer_tamano(ruta)
        return min(w, iw) * min(h, ih)

    def _color_celda(self, i):
        oscuro = ctk.get_appearance_mode() == "Dark"
        s, v = (0.40, 0.80) if oscuro else (0.30, 0.97)
        tono_h = (i * 0.618034 + 0.58) % 1
        relleno = colorsys.hsv_to_rgb(tono_h, s, v)
        borde = colorsys.hsv_to_rgb(tono_h, min(1, s + 0.15), v * 0.78)
        a_hex = lambda rgb: "#" + "".join(f"{int(c * 255):02x}" for c in rgb)
        return a_hex(relleno), a_hex(borde)

    def dibujar(self):
        c = self.lienzo
        c.delete("all")
        c.configure(bg=tono(TARJETA))
        cw, ch = c.winfo_width(), c.winfo_height()
        if cw < 50 or ch < 50:
            return
        ancho, alto = RESOLUCIONES[self.res.get()]
        margen, pie = 20, 26
        escala = min((cw - 2 * margen) / ancho, (ch - 2 * margen - pie) / alto)
        ox = (cw - ancho * escala) / 2
        oy = (ch - pie - alto * escala) / 2
        self._geom = (ox, oy, escala)
        x1, y1 = ox + ancho * escala, oy + alto * escala

        for d, factor in ((10, 0.35), (6, 0.6), (3, 1.0)):  # sombra suave escalonada
            rect_redondeado(c, ox - d / 2, oy + d / 2, x1 + d / 2, y1 + d * 1.2, 12, fill=self._mezcla_sombra(factor))
        c.create_rectangle(ox, oy, x1, y1, fill=self.fondo, outline="")

        if self.resultado is not None:
            self._dibujar_resultado(ox, oy, x1, y1)
            return
        if not self.celdas:
            if self.todas_rutas and not self.rutas:
                texto = t("lienzo.sin_periodo")
            else:
                texto = t("lienzo.sin_origen") if not self.rutas else t("lienzo.sin_vista")
            claro = "#E7E9EF" if es_oscuro(self.fondo) else "#3A3F4E"
            c.create_text((ox + x1) / 2, (oy + y1) / 2, text=texto, fill=claro, font=self.f_titulo)
            return

        for i, celda in enumerate(self.celdas):
            ruta, x, y, w, h, posicion = celda
            relleno, borde = self._color_celda(i)
            cx0, cy0 = ox + x * escala, oy + y * escala
            cx1, cy1 = cx0 + w * escala, cy0 + h * escala
            if posicion is not None and self._area_visible(celda) < w * h:
                iw, ih = leer_tamano(ruta)
                vx0, vy0 = max(x, posicion[0]), max(y, posicion[1])
                vx1, vy1 = min(x + w, posicion[0] + iw), min(y + h, posicion[1] + ih)
                c.create_rectangle(ox + vx0 * escala, oy + vy0 * escala, ox + vx1 * escala, oy + vy1 * escala,
                                   fill=relleno, outline="")
                c.create_rectangle(cx0 + 1, cy0 + 1, cx1 - 1, cy1 - 1, outline=tono(PELIGRO), width=2)
            else:
                c.create_rectangle(cx0, cy0, cx1, cy1, fill=relleno, outline=borde)
            if ruta == self.ancla:  # imagen de referencia de la similitud
                c.create_rectangle(cx0 + 1, cy0 + 1, cx1 - 1, cy1 - 1, outline=tono(ACENTO), width=3)
                c.create_text(cx0 + 6, cy0 + 4, anchor="nw", text="★", fill=tono(ACENTO),
                              font=("Segoe UI Symbol", 14, "bold"))
            if cx1 - cx0 > 34 and cy1 - cy0 > 22:
                if cx1 - cx0 > 80 and cy1 - cy0 > 44:
                    c.create_text((cx0 + cx1) / 2, (cy0 + cy1) / 2 - 8, text=str(i + 1), fill="#1E2130",
                                  font=self.f_lienzo_num)
                    c.create_text((cx0 + cx1) / 2, (cy0 + cy1) / 2 + 9, text=f"{w} × {h}", fill="#3A3F52",
                                  font=self.f_lienzo)
                else:
                    c.create_text((cx0 + cx1) / 2, (cy0 + cy1) / 2, text=str(i + 1), fill="#1E2130",
                                  font=self.f_lienzo_num)

        c.create_text(ox, y1 + 16, anchor="w", fill=tono(TEXTO_SUAVE), font=self.f_lienzo,
                      text=t("lienzo.ayuda"))
        c.create_text(x1, y1 + 16, anchor="e", fill=tono(TEXTO_SUAVE), font=self.f_lienzo,
                      text=f"{ancho} × {alto} px")
        self._dibujar_hover(None)

    def _dibujar_resultado(self, ox, oy, x1, y1):
        """Muestra el collage generado (escalado al lienzo) en lugar de los bloques."""
        c = self.lienzo
        tamano = (max(1, round(x1 - ox)), max(1, round(y1 - oy)))
        if self._foto is None or self._foto[0] != tamano or self._foto[2] is not self.resultado:
            imagen = self.resultado.resize(tamano, Image.LANCZOS)
            self._foto = (tamano, ImageTk.PhotoImage(imagen), self.resultado)
        c.create_image(ox, oy, anchor="nw", image=self._foto[1])
        c.create_text(ox, y1 + 16, anchor="w", fill=tono(TEXTO_SUAVE), font=self.f_lienzo,
                      text=t("lienzo.generado"))
        ancho, alto = RESOLUCIONES[self.res.get()]
        c.create_text(x1, y1 + 16, anchor="e", fill=tono(TEXTO_SUAVE), font=self.f_lienzo,
                      text=f"{ancho} × {alto} px")

    def _mezcla_sombra(self, factor):
        """Mezcla entre el color de la tarjeta y el de la sombra (simula transparencia)."""
        a, b = tono(TARJETA), tono(SOMBRA)
        mezcla = [round(int(a[i:i + 2], 16) * (1 - factor) + int(b[i:i + 2], 16) * factor) for i in (1, 3, 5)]
        return "#" + "".join(f"{v:02x}" for v in mezcla)

    def _celda_en(self, px, py):
        if not self._geom or not self.celdas or self.resultado is not None:
            return None
        ox, oy, escala = self._geom
        x, y = (px - ox) / escala, (py - oy) / escala
        for i, (_, cx, cy, w, h, _) in enumerate(self.celdas):
            if cx <= x < cx + w and cy <= y < cy + h:
                return i
        return None

    def _mover_raton(self, evento):
        self.hover = None if evento is None else self._celda_en(evento.x, evento.y)
        self._dibujar_hover(evento)

    def _dibujar_hover(self, evento):
        c = self.lienzo
        c.delete("hover")
        if self.hover is None or evento is None or not self._geom:
            return
        ox, oy, escala = self._geom
        ruta, x, y, w, h, posicion = self.celdas[self.hover]
        c.create_rectangle(ox + x * escala, oy + y * escala, ox + (x + w) * escala, oy + (y + h) * escala,
                           outline=tono(ACENTO), width=3, tags="hover")

        lineas = [t("tip.imagen", n=self.hover + 1) + ("  " + t("tip.referencia") if ruta == self.ancla else ""),
                  t("tip.hueco", w=w, h=h)]
        if posicion is not None:
            iw, ih = leer_tamano(ruta)
            lineas.append(t("tip.original", w=iw, h=ih))
            if iw < w or ih < h:
                lineas.append(t("tip.pequena"))
            else:
                lineas.append(t("tip.visible", p=round(100 * w * h / (iw * ih))))
        else:
            lineas.append(t("tip.escalada"))

        alto_linea = self.f_tooltip.metrics("linespace")
        tw = max(self.f_tooltip.measure(l) for l in lineas) + 24
        th = alto_linea * len(lineas) + 16
        tx, ty = evento.x + 16, evento.y + 16
        if tx + tw > c.winfo_width() - 4:
            tx = evento.x - tw - 12
        if ty + th > c.winfo_height() - 4:
            ty = evento.y - th - 12
        rect_redondeado(c, tx, ty, tx + tw, ty + th, 10, fill=tono(TOOLTIP), tags="hover")
        for n, linea in enumerate(lineas):
            fuente = self.f_lienzo_num if n == 0 else self.f_tooltip
            c.create_text(tx + 12, ty + 8 + n * alto_linea, anchor="nw", text=linea, fill=tono(TOOLTIP_TEXTO),
                          font=fuente, tags="hover")

    # ================= generacion =================

    def generar(self):
        if self._generando:
            return
        params = self.leer_parametros()
        if params is None:
            self._estado(t("gen.revisa"), PELIGRO)
            return
        if not self.rutas:
            self._estado(t("gen.sin_imagenes"), PELIGRO)
            return
        try:
            cantidad = acotar(int(self.cantidad.get()), "cantidad")
        except (tk.TclError, ValueError):
            cantidad = 1
        modo, ancho, alto, filas, imagenes, separacion, semilla, variedad = params
        indice, referencia, estado = self._preparar_similitud(modo, filas, imagenes, semilla)
        if estado == "esperando":
            self._estado(t("gen.espera"), PELIGRO)
            return
        if estado not in ("listo", "no"):
            self._estado(estado, PELIGRO)
            return
        parecido, minimo = self.parecido.get() / 100, similitud.minimo_parecidas(modo, filas, imagenes)
        self._guardar_config()

        salida, res, fondo, rutas_usadas = Path(self.salida.get()), self.res.get(), self.fondo, list(self.rutas)
        marca = rutas.APP_NOMBRE  # la marca de agua siempre va puesta
        avance = {"collage": 0, "hechas": 0, "total": 1}
        resultado = {}

        def trabajo():
            try:
                salida.mkdir(parents=True, exist_ok=True)
                rng = random.Random(semilla)  # el primer collage coincide con la vista previa
                guardados = []
                for i in range(cantidad):
                    avance.update(collage=i, hechas=0, total=1)
                    usadas = rutas_usadas
                    if estado == "listo":  # cada collage con su propia referencia (el primero = vista previa)
                        _, usadas = similitud.seleccionar_parecidas(rutas_usadas, indice, semilla + i, parecido,
                                                                    minimo, referencia)
                    celdas = planificar(modo, usadas, ancho, alto, filas, imagenes, separacion, rng, variedad)
                    imagen = renderizar_collage(celdas, ancho, alto, fondo, marca_agua=marca,
                                                progreso=lambda h, t: avance.update(hechas=h, total=t))
                    destino = nombre_destino(salida, res, f"_{i + 1}" if cantidad > 1 else "")
                    imagen.save(destino)
                    guardados.append(destino)
                    if i == 0:  # el primero (el de la vista previa) se muestra en el lienzo
                        imagen.thumbnail((2048, 2048), Image.LANCZOS)
                        resultado["miniatura"] = imagen
                resultado["ok"] = guardados
            except Exception as e:
                resultado["error"] = str(e)

        self._generando = True
        self.btn_generar.configure(state="disabled", text=t("boton.generando"))
        self.btn_abrir_imagen.grid_remove()
        self.progreso.set(0)
        self.progreso.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self._estado(tn("gen.generando", cantidad), TEXTO)
        hilo = threading.Thread(target=trabajo, daemon=True)
        hilo.start()

        def comprobar():
            if hilo.is_alive():
                self.progreso.set((avance["collage"] + avance["hechas"] / max(1, avance["total"])) / cantidad)
                self.after(80, comprobar)
                return
            self._generando = False
            self.btn_generar.configure(state="normal", text=t("boton.generar"))
            self.progreso.grid_remove()
            if "error" in resultado:
                self._estado(t("error", error=resultado["error"]), PELIGRO)
                return
            guardados = resultado["ok"]
            self._ultimo_guardado = guardados[-1]
            self._estado(tn("gen.guardado", len(guardados)), EXITO)
            self.btn_abrir_imagen.grid(row=0, column=1, padx=(8, 0))
            self.resultado = resultado["miniatura"]
            self.hover = None
            chips = [(t("chip.generado"), EXITO), (t("chip.semilla", semilla=semilla), TEXTO_SUAVE)]
            if len(guardados) > 1:
                chips.insert(1, (t("chip.mostrando", n=len(guardados)), TEXTO))
            self._pintar_chips(chips)
            self.dibujar()
            if self.auto_semilla.get():
                self._conservar_resultado = True
                self.nueva_semilla()

        comprobar()


def main():
    if "--descargar-ia" in sys.argv:  # sin ventana: preinstala el modelo de IA (codigo de salida 0 = bien)
        try:
            similitud.descargar_modelo()
        except Exception:
            sys.exit(1)
        sys.exit(0)
    try:  # que la barra de tareas muestre el icono de la aplicacion (y no el de Python)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(rutas.APP_NOMBRE)
    except Exception:
        pass
    rutas.migrar_datos_antiguos()
    while True:  # cambiar de idioma cierra la ventana y la vuelve a crear con los textos nuevos
        app = App()
        app.mainloop()
        if not app.reiniciar:
            break


if __name__ == "__main__":
    main()
