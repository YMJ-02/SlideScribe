; ────────────────────────────────────────────────────────────────────
;  SlideScribe — Inno Setup 6 installer script
;
;  Build the program first:
;      pyinstaller build/slidescribe.spec --clean --noconfirm
;  Then compile the installer:
;      iscc build/installer.iss
;  Output:
;      dist/installer/SlideScribe-Setup.exe
; ────────────────────────────────────────────────────────────────────

#define MyAppName       "SlideScribe"
#define MyAppVersion    "0.3.0"
#define MyAppPublisher  "YMJ-02"
#define MyAppURL        "https://github.com/YMJ-02/SlideScribe"
#define MyAppExeName    "SlideScribe.exe"

[Setup]
AppId={{B7C2A4DE-3F1E-4D2B-9F2A-9F1D2B3C4D5E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=..\dist\installer
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
SetupIconFile=icon.ico

Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "korean";  MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller one-dir output is at ..\dist\SlideScribe\
Source: "..\dist\SlideScribe\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";                          Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}";    Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Intentionally do NOT delete %LOCALAPPDATA%\SlideScribe — user data lives there
