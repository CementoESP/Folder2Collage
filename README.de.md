# Folder2Collage

[English](README.md) · [Español](README.es.md) · **Deutsch** · [Français](README.fr.md) · [Italiano](README.it.md) · [Português](README.pt.md)

Erstelle zufällige Collagen aus den Bildern eines Ordners — zum Beispiel deinen
Windows-Screenshots. Wähle Auflösung, Layout und Anzahl der Bilder, und
Folder2Collage ordnet sie zu einer Collage an. Alles läuft auf deinem PC;
**es wird nie etwas online gesendet.**

*Die App gibt es auf Englisch, Spanisch, Deutsch, Französisch, Italienisch und
Portugiesisch und erkennt deine Windows-Sprache — du kannst sie jederzeit wechseln.*

![Folder2Collage](docs/captura.png)

## Funktionen

- **Zwei Layouts:** *Reihen* (Bilder werden skaliert und leicht zugeschnitten, um
  Reihen zu füllen) und *Originalgröße* (jedes Bild in seiner echten Pixelgröße, ohne
  Skalierung — nur der Überstand wird abgeschnitten).
- **Live-Vorschau** des genauen Layouts vor dem Erstellen, mit farbigen Blöcken, sodass
  der Inhalt deiner Bilder erst angezeigt wird, wenn du dich zum Erstellen entscheidest.
- **Datumsfilter:** heute, letzte 7 Tage, alle oder ein benutzerdefinierter Zeitraum.
- **Ähnliche Fotos (optional, lokale KI):** gruppiere Landschaften, Gesichter, Tiere,
  Text… nach Inhalt oder suche per Text — mit einem CLIP-Modell, das auf deinem PC läuft.
- **Auflösungen** bis 4K, einstellbarer Abstand, Hintergrundfarbe, Namens-Wasserzeichen,
  Seeds zum Reproduzieren einer Collage und Stapelerstellung.

## Datenschutz

Folder2Collage hält deine Bilder privat. Keine Analyse, keine Telemetrie, keine Konten.
Deine Screenshots, Collagen und Suchen verlassen nie deinen Computer. Die einzige
Internetverbindung ist der optionale einmalige Download des KI-Modells, und selbst dann
werden deine Bilder nie hochgeladen. Siehe [PRIVACIDAD.md](PRIVACIDAD.md) für die
vollständige Erklärung in sechs Sprachen.

## Installation (Windows)

1. Lade `Folder2Collage-x.y.z-Setup.exe` von der Seite
   [Releases](https://github.com/CementoESP/Folder2Collage/releases) herunter.
2. Führe die Datei aus. Sie wird für den aktuellen Benutzer installiert und benötigt
   keine Administratorrechte.

Folder2Collage ist nicht digital signiert, daher zeigt Windows SmartScreen beim ersten
Mal möglicherweise „Der Computer wurde durch Windows geschützt“. Klicke auf
**Weitere Informationen → Trotzdem ausführen**.

## Optionale KI (ähnliche Fotos)

Die Funktion „ähnliche Fotos“ nutzt ein lokales CLIP-Modell. Das Modell ist **nicht**
im Installer enthalten: Wenn du die Funktion zum ersten Mal aktivierst, fragt die App
um Erlaubnis, es herunterzuladen (etwa 130 MB, einmalig). Danach funktioniert es
vollständig offline. Du kannst es auch ohne Fenster vorab installieren:

```
Folder2Collage.exe --descargar-ia
```

## Aus dem Quellcode bauen

Erfordert Python 3.12+ unter Windows.

```
python -m venv .venv
.venv\Scripts\python -m pip install -r empaquetado\requirements-build.txt
.venv\Scripts\python empaquetado\construir.py
```

Das erzeugt die App in `empaquetado\dist\Folder2Collage\` und den Installer in
`empaquetado\salida\`. Für das Bauen des Installers wird außerdem
[Inno Setup 6](https://jrsoftware.org/isinfo.php)
(`winget install JRSoftware.InnoSetup`) benötigt.

Um sie ohne Bauen direkt auszuführen, installiere die Laufzeitabhängigkeiten aus
`requirements.txt` und starte `Folder2Collage.pyw`.

## Lizenz

Siehe [LICENSE](LICENSE). Drittanbieter-Komponenten und ihre Lizenzen sind in
[AVISOS_TERCEROS.txt](AVISOS_TERCEROS.txt) aufgeführt.

---

Erstellt von CementoESP.
