# Folder2Collage

[English](README.md) · [Español](README.es.md) · [Deutsch](README.de.md) · **Français** · [Italiano](README.it.md) · [Português](README.pt.md)

Crée des collages aléatoires à partir des images d'un dossier — par exemple vos
captures d'écran Windows. Choisissez une résolution, une disposition et le nombre
d'images, et Folder2Collage les assemble en un collage. Tout s'exécute sur votre PC ;
**rien n'est jamais envoyé en ligne.**

*L'application est en anglais, espagnol, allemand, français, italien et portugais, et
détecte la langue de votre Windows — vous pouvez en changer à tout moment.*

![Folder2Collage](docs/captura.png)

## Fonctionnalités

- **Deux dispositions :** *Rangées* (les images sont redimensionnées et légèrement
  recadrées pour remplir des rangées) et *Taille d'origine* (chaque image à sa taille
  réelle en pixels, sans redimensionnement — seul l'excédent est recadré).
- **Aperçu en direct** de la disposition exacte avant de générer, avec des blocs de
  couleur, pour que le contenu de vos images ne soit jamais montré avant que vous ne
  choisissiez de générer.
- **Filtre par date :** aujourd'hui, 7 derniers jours, toujours, ou une période
  personnalisée.
- **Photos similaires (facultatif, IA locale) :** regroupez paysages, visages, animaux,
  texte… par contenu, ou recherchez par texte — grâce à un modèle CLIP qui s'exécute sur
  votre PC.
- **Résolutions** jusqu'à 4K, espacement réglable, couleur de fond, filigrane avec le
  nom, graines pour reproduire un collage et génération par lots.

## Confidentialité

Folder2Collage garde vos images privées. Pas d'analyse, pas de télémétrie, pas de
comptes. Vos captures, collages et recherches ne quittent jamais votre ordinateur. La
seule connexion internet est le téléchargement facultatif et unique du modèle d'IA, et
même alors vos images ne sont jamais envoyées. Voir [PRIVACIDAD.md](PRIVACIDAD.md) pour
la déclaration complète en six langues.

## Installation (Windows)

1. Téléchargez `Folder2Collage-x.y.z-Setup.exe` depuis la page
   [Releases](https://github.com/CementoESP/Folder2Collage/releases).
2. Exécutez-le. Il s'installe pour l'utilisateur actuel et ne nécessite aucun droit
   d'administrateur.

Folder2Collage n'est pas signé numériquement, donc Windows SmartScreen peut afficher
« Windows a protégé votre ordinateur » la première fois. Cliquez sur
**Informations complémentaires → Exécuter quand même**.

## IA facultative (photos similaires)

La fonction « photos similaires » utilise un modèle CLIP local. Le modèle n'est **pas**
inclus dans l'installateur : la première fois que vous activez la fonction, l'application
demande l'autorisation de le télécharger (environ 130 Mo, une seule fois). Ensuite, tout
fonctionne hors ligne. Vous pouvez aussi le préinstaller sans ouvrir la fenêtre :

```
Folder2Collage.exe --descargar-ia
```

## Compiler depuis les sources

Nécessite Python 3.12+ sous Windows.

```
python -m venv .venv
.venv\Scripts\python -m pip install -r empaquetado\requirements-build.txt
.venv\Scripts\python empaquetado\construir.py
```

Cela produit l'application dans `empaquetado\dist\Folder2Collage\` et l'installateur dans
`empaquetado\salida\`. Compiler l'installateur nécessite aussi
[Inno Setup 6](https://jrsoftware.org/isinfo.php)
(`winget install JRSoftware.InnoSetup`).

Pour l'exécuter directement sans compiler, installez les dépendances d'exécution de
`requirements.txt` et lancez `Folder2Collage.pyw`.

## Licence

Voir [LICENSE](LICENSE). Les composants tiers et leurs licences sont listés dans
[AVISOS_TERCEROS.txt](AVISOS_TERCEROS.txt).

---

Réalisé par CementoESP.
