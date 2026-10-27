# Folder2Collage

**English** · [Español](README.es.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [Italiano](README.it.md) · [Português](README.pt.md)

Make random collages from the images in a folder — for example your Windows
screenshots. Pick a resolution, a layout and how many images, and Folder2Collage
arranges them into a collage. Everything runs on your PC; **nothing is ever sent
online.**

*The app speaks English, Español, Deutsch, Français, Italiano and Português, and
auto-detects your Windows language — you can switch it at any time.*

![Folder2Collage](docs/captura.png)

## Features

- **Two layouts:** *Rows* (images scaled and lightly cropped to fill rows) and
  *Original size* (every image at its real pixel size, never scaled — only the
  excess is cropped).
- **Live preview** of the exact layout before you generate, with colored blocks,
  so the content of your images is never shown until you choose to generate.
- **Date filter:** today, last 7 days, all time, or a custom range.
- **Similar photos (optional, local AI):** group landscapes, faces, animals, text…
  by content, or search by text — powered by a CLIP model that runs on your PC.
- **Resolutions** up to 4K, adjustable spacing, background color, a name watermark,
  seeds to reproduce a collage, and batch generation.

## Privacy

Folder2Collage keeps your images private. No analytics, no telemetry, no accounts.
Your screenshots, collages and searches never leave your computer. The only
internet connection is the optional one-time download of the AI model, and even
then your images are never uploaded. See [PRIVACIDAD.md](PRIVACIDAD.md) for the
full statement in six languages.

## Install (Windows)

1. Download `Folder2Collage-x.y.z-Setup.exe` from the
   [Releases](https://github.com/CementoESP/Folder2Collage/releases) page.
2. Run it. It installs for the current user and needs no administrator rights.

Folder2Collage is not code-signed, so Windows SmartScreen may show
"Windows protected your PC" the first time. Click **More info → Run anyway**.

## Optional AI (similar photos)

The "similar photos" feature uses a local CLIP model. The model is **not** bundled
with the installer: the first time you turn the feature on, the app asks permission
to download it (about 130 MB, once). After that it works fully offline. You can
also pre-install it without opening the window:

```
Folder2Collage.exe --descargar-ia
```

## Build from source

Requires Python 3.12+ on Windows.

```
python -m venv .venv
.venv\Scripts\python -m pip install -r empaquetado\requirements-build.txt
.venv\Scripts\python empaquetado\construir.py
```

This produces the app in `empaquetado\dist\Folder2Collage\` and the installer in
`empaquetado\salida\`. Building the installer also needs
[Inno Setup 6](https://jrsoftware.org/isinfo.php)
(`winget install JRSoftware.InnoSetup`).

To run it directly without building, install the runtime dependencies from
`requirements.txt` and run `Folder2Collage.pyw`.

## License

See [LICENSE](LICENSE). Third-party components and their licenses are listed in
[AVISOS_TERCEROS.txt](AVISOS_TERCEROS.txt).

---

Made by CementoESP.
