; Instalador de Inno Setup. No se usa directamente: lo compila construir.py.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef AppEditor
  #define AppEditor "CementoESP"
#endif
#ifndef AppUrl
  #define AppUrl "https://github.com/CementoESP/Folder2Collage"
#endif
#define AppNombre "Folder2Collage"
#define AppExe "Folder2Collage.exe"

[Setup]
AppId={{6B0C8F52-3E1D-4E9A-9C47-2F5D8A1B7E30}
AppName={#AppNombre}
AppVersion={#AppVersion}
AppVerName={#AppNombre} {#AppVersion}
AppPublisher={#AppEditor}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
DefaultDirName={autopf}\{#AppNombre}
DefaultGroupName={#AppNombre}
DisableProgramGroupPage=yes
; Se instala para el usuario actual sin pedir permisos de administrador (se puede elegir "todos los usuarios").
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=salida
OutputBaseFilename={#AppNombre}-{#AppVersion}-Setup
SetupIconFile=..\recursos\icono.ico
UninstallDisplayIcon={app}\{#AppExe}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ShowLanguageDialog=auto

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[CustomMessages]
en.BorrarDatos=Also delete the settings, the image analysis cache and the downloaded AI model?%n%nYour collages are not deleted.
es.BorrarDatos=¿Borrar también los ajustes, la caché de análisis de imágenes y el modelo de IA descargado?%n%nTus collages no se borran.
de.BorrarDatos=Auch die Einstellungen, den Bildanalyse-Cache und das heruntergeladene KI-Modell löschen?%n%nDeine Collagen werden nicht gelöscht.
fr.BorrarDatos=Supprimer aussi les paramètres, le cache d'analyse des images et le modèle d'IA téléchargé ?%n%nVos collages ne sont pas supprimés.
it.BorrarDatos=Eliminare anche le impostazioni, la cache di analisi delle immagini e il modello di IA scaricato?%n%nI tuoi collage non vengono eliminati.
pt.BorrarDatos=Apagar também as configurações, o cache de análise das imagens e o modelo de IA baixado?%n%nSuas colagens não são apagadas.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#AppNombre}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\AVISOS_TERCEROS.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppNombre}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppNombre}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppNombre}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Datos: String;
begin
  Datos := ExpandConstant('{localappdata}\{#AppNombre}');
  if (CurUninstallStep = usPostUninstall) and DirExists(Datos) and not UninstallSilent then
    if MsgBox(CustomMessage('BorrarDatos'), mbConfirmation, MB_YESNO) = IDYES then
      DelTree(Datos, True, True, True);
end;
