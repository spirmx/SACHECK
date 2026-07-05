#define MyAppVersion "2.0.7"
#define MyAppPublisher "HOYTURBRO"
#define MyAppExeName "SACHECK.exe"

#ifdef QA
  #define MyAppName "SA CHECK QA"
  #define MyAppId "{{7C5B8D91-768D-43E6-B7E8-2C1035185D09}"
  #define MyDefaultDirName "{tmp}\SACHECK-QA"
  #define MyOutputBaseFilename "SA_CHECK_Installer_QA"
  #define MyPrivileges "lowest"
#else
  #define MyAppName "SA CHECK"
  #define MyAppId "{{B613A092-3E4C-4D2B-A8B4-72D7E2A9A80C}"
  #define MyDefaultDirName "C:\SACHECK"
  #define MyOutputBaseFilename "SA_CHECK_Installer"
  #define MyPrivileges "admin"
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} version {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/spirmx
AppSupportURL=https://github.com/spirmx/SACHECK
AppUpdatesURL=https://github.com/spirmx/SACHECK
DefaultDirName={#MyDefaultDirName}
DefaultGroupName=SA CHECK
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename={#MyOutputBaseFilename}
SetupIconFile=..\assets\app\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired={#MyPrivileges}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousTasks=yes
VersionInfoVersion=2.0.7.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=SA CHECK Desktop Work Board Installer
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion=2.0.7.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Files]
Source: "..\build\windows_2.0.7\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Open SA CHECK"; Flags: nowait postinstall skipifsilent
