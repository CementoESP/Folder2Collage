# Folder2Collage

[English](README.md) · [Español](README.es.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · **Italiano** · [Português](README.pt.md)

Crea collage casuali con le immagini di una cartella — per esempio i tuoi screenshot di
Windows. Scegli una risoluzione, una modalità e quante immagini, e Folder2Collage le
dispone in un collage. Tutto viene eseguito sul tuo PC; **non viene mai inviato nulla
online.**

*L'app è in inglese, spagnolo, tedesco, francese, italiano e portoghese, e rileva la
lingua del tuo Windows — puoi cambiarla quando vuoi.*

![Folder2Collage](docs/captura.png)

## Funzioni

- **Due modalità:** *Righe* (le immagini vengono ridimensionate e ritagliate leggermente
  per riempire le righe) e *Dimensione originale* (ogni immagine alla sua dimensione
  reale in pixel, senza ridimensionamento — si ritaglia solo l'eccesso).
- **Anteprima dal vivo** della disposizione esatta prima di generare, con blocchi
  colorati, così il contenuto delle tue immagini non viene mostrato finché non scegli di
  generare.
- **Filtro per data:** oggi, ultimi 7 giorni, sempre o un intervallo personalizzato.
- **Foto simili (facoltativo, IA locale):** raggruppa paesaggi, volti, animali, testo…
  per contenuto, o cerca per testo — grazie a un modello CLIP che gira sul tuo PC.
- **Risoluzioni** fino a 4K, spaziatura regolabile, colore di sfondo, filigrana con il
  nome, semi per riprodurre un collage e generazione in serie.

## Privacy

Folder2Collage mantiene private le tue immagini. Nessuna analisi, nessuna telemetria,
nessun account. I tuoi screenshot, collage e ricerche non lasciano mai il tuo computer.
L'unica connessione a internet è il download facoltativo e una tantum del modello di IA,
e nemmeno allora le tue immagini vengono caricate. Vedi [PRIVACIDAD.md](PRIVACIDAD.md)
per la dichiarazione completa in sei lingue.

## Installazione (Windows)

1. Scarica `Folder2Collage-x.y.z-Setup.exe` dalla pagina
   [Releases](https://github.com/CementoESP/Folder2Collage/releases).
2. Eseguilo. Si installa per l'utente corrente e non richiede diritti di amministratore.

Folder2Collage non è firmato digitalmente, quindi Windows SmartScreen potrebbe mostrare
"Windows ha protetto il PC" la prima volta. Fai clic su **Ulteriori informazioni →
Esegui comunque**.

## IA facoltativa (foto simili)

La funzione "foto simili" usa un modello CLIP locale. Il modello **non** è incluso
nell'installer: la prima volta che attivi la funzione, l'app chiede il permesso di
scaricarlo (circa 130 MB, una sola volta). Dopodiché funziona completamente offline.
Puoi anche preinstallarlo senza aprire la finestra:

```
Folder2Collage.exe --descargar-ia
```

## Compilare dai sorgenti

Richiede Python 3.12+ su Windows.

```
python -m venv .venv
.venv\Scripts\python -m pip install -r empaquetado\requirements-build.txt
.venv\Scripts\python empaquetado\construir.py
```

Questo produce l'app in `empaquetado\dist\Folder2Collage\` e l'installer in
`empaquetado\salida\`. Per compilare l'installer serve anche
[Inno Setup 6](https://jrsoftware.org/isinfo.php)
(`winget install JRSoftware.InnoSetup`).

Per eseguirla direttamente senza compilare, installa le dipendenze di runtime da
`requirements.txt` e avvia `Folder2Collage.pyw`.

## Licenza

Vedi [LICENSE](LICENSE). I componenti di terze parti e le loro licenze sono elencati in
[AVISOS_TERCEROS.txt](AVISOS_TERCEROS.txt).

---

Realizzato da CementoESP.
