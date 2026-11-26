; Inno Setup script for Toolbox. build.py compiles it into dist\ToolboxSetup.exe:
;   ISCC.exe /DAppVersion=1.2.0 installer\Toolbox.iss
; Installs per user (no admin prompt), adds Toolbox to "Installed apps" with an uninstaller,
; and a newer ToolboxSetup.exe installs over the old version (same AppId).

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
; Never change AppId: Windows uses it to recognise updates and the uninstaller.
AppId={{6F1C2A4E-8B3D-4E7A-9C51-2D8E0B7F4A93}
AppName=Toolbox
AppVersion={#AppVersion}
AppVerName=Toolbox {#AppVersion}
AppPublisher=nonagon-X
AppPublisherURL=https://github.com/nonagon-X/image-toolbox
AppUpdatesURL=https://github.com/nonagon-X/image-toolbox/releases
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\Toolbox
DefaultGroupName=Toolbox
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=ToolboxSetup
SetupIconFile=..\assets\toolbox.ico
UninstallDisplayIcon={app}\Toolbox.exe
UninstallDisplayName=Toolbox
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\Toolbox.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Toolbox"; Filename: "{app}\Toolbox.exe"
Name: "{autodesktop}\Toolbox"; Filename: "{app}\Toolbox.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Toolbox.exe"; Description: "{cm:LaunchProgram,Toolbox}"; Flags: nowait postinstall skipifsilent
