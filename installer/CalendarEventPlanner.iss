; Inno Setup script for Calendar Event Planner
; Build via: scripts\build_installer.ps1
; This installer installs per-user into %LOCALAPPDATA%\Programs\CalendarEventPlanner
; and does NOT require admin rights.

#ifndef AppVersion
  #define AppVersion "1.1.0"
#endif
#ifndef AppExe
  #define AppExe "run_calendar_planner.bat"
#endif
#ifndef OutputDir
  #define OutputDir "dist"
#endif
#ifndef OutputBaseName
  #define OutputBaseName "CalendarEventPlanner-Setup-v" + AppVersion
#endif
#ifndef StagingDir
  #define StagingDir "build\installer_stage"
#endif

#define MyAppName "Calendar Event Planner"
#define MyAppPublisher "Calendar Event Planner"

[Setup]
AppId={{8C0B2F1A-5E91-4C1B-9A9A-0001-0001}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\CalendarEventPlanner
DefaultGroupName=Calendar Event Planner
DisableProgramGroupPage=yes
OutputBaseFilename={#OutputBaseName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
PrivilegesRequired=lowest
UninstallDisplayName={#MyAppName}
SignedUninstaller=no
; Honest: installer is unsigned (no Authenticode cert yet).
[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "{#StagingDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; NOTE: .env, .venv, logs, runs, credentials excluded at staging time.

[Icons]
Name: "{group}\Calendar Event Planner"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"
Name: "{group}\Диагностика Calendar Event Planner"; Filename: "{app}\run_diagnostics.bat"; WorkingDir: "{app}"
Name: "{group}\Удалить Calendar Event Planner"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Calendar Event Planner"; Filename: "{app}\{#AppExe}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Запустить Calendar Event Planner"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove only program files. User data (%LOCALAPPDATA%\CalendarEventPlanner) and
; the Credential Manager entry are removed only on explicit user consent in the
; app's uninstall flow (kept intact here by design).
Type: filesandordirs; Name: "{app}"