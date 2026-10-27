# Folder2Collage

[English](README.md) · **Español** · [Deutsch](README.de.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português](README.pt.md)

Crea collages aleatorios con las imágenes de una carpeta — por ejemplo tus capturas
de pantalla de Windows. Eliges la resolución, el modo y cuántas imágenes, y
Folder2Collage las coloca en un collage. Todo se ejecuta en tu PC; **nunca se envía
nada por internet.**

*La app está en inglés, español, alemán, francés, italiano y portugués, y detecta el
idioma de tu Windows — puedes cambiarlo cuando quieras.*

![Folder2Collage](docs/captura.png)

## Funciones

- **Dos modos:** *Filas* (las imágenes se escalan y se recortan un poco para rellenar
  filas) y *Tamaño original* (cada imagen a su tamaño real en píxeles, sin escalar;
  solo se recorta lo que sobra).
- **Vista previa** de la distribución exacta antes de generar, con bloques de colores,
  así el contenido de tus imágenes no se muestra hasta que decides generar.
- **Filtro por fecha:** hoy, últimos 7 días, siempre o un rango personalizado.
- **Fotos parecidas (opcional, IA local):** agrupa paisajes, caras, animales, texto…
  por su contenido, o busca por texto — con un modelo CLIP que se ejecuta en tu PC.
- **Resoluciones** hasta 4K, separación ajustable, color de fondo, marca de agua con
  el nombre, semillas para reproducir un collage y generación por lotes.

## Privacidad

Folder2Collage mantiene tus imágenes privadas. Sin analítica, sin telemetría, sin
cuentas. Tus capturas, collages y búsquedas nunca salen de tu ordenador. La única
conexión a internet es la descarga opcional y única del modelo de IA, y ni siquiera
entonces se suben tus imágenes. Consulta [PRIVACIDAD.md](PRIVACIDAD.md) para la
declaración completa en seis idiomas.

## Instalación (Windows)

1. Descarga `Folder2Collage-x.y.z-Setup.exe` desde la página de
   [Releases](https://github.com/CementoESP/Folder2Collage/releases).
2. Ejecútalo. Se instala para el usuario actual y no necesita permisos de
   administrador.

Folder2Collage no está firmado digitalmente, así que Windows SmartScreen puede mostrar
"Windows protegió su PC" la primera vez. Pulsa **Más información → Ejecutar de todas
formas**.

## IA opcional (fotos parecidas)

La función de "fotos parecidas" usa un modelo CLIP local. El modelo **no** viene con el
instalador: la primera vez que activas la función, la app pide permiso para descargarlo
(unos 130 MB, una sola vez). Después funciona totalmente sin conexión. También puedes
preinstalarlo sin abrir la ventana:

```
Folder2Collage.exe --descargar-ia
```

## Compilar desde el código

Requiere Python 3.12+ en Windows.

```
python -m venv .venv
.venv\Scripts\python -m pip install -r empaquetado\requirements-build.txt
.venv\Scripts\python empaquetado\construir.py
```

Esto genera la app en `empaquetado\dist\Folder2Collage\` y el instalador en
`empaquetado\salida\`. Compilar el instalador necesita además
[Inno Setup 6](https://jrsoftware.org/isinfo.php)
(`winget install JRSoftware.InnoSetup`).

Para ejecutarla directamente sin compilar, instala las dependencias de
`requirements.txt` y abre `Folder2Collage.pyw`.

## Licencia

Consulta [LICENSE](LICENSE). Los componentes de terceros y sus licencias están en
[AVISOS_TERCEROS.txt](AVISOS_TERCEROS.txt).

---

Hecho por CementoESP.
