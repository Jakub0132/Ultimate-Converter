#define AppVersion "1.0.1"
#define AppName "Ultimate Converter"

[Setup]
#ifdef InstallerTest
AppId=UltimateConverterIsolatedSmokeTest
CreateUninstallRegKey=no
UsePreviousAppDir=no
#else
AppId={{7D2A6A7C-9E29-4A42-B994-527579095C31}
#endif
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
DefaultDirName={localappdata}\Programs\Ultimate Converter
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
#ifdef InstallerTest
OutputDir=..\build
OutputBaseFilename=installer-smoke-setup
Compression=none
#else
OutputDir=..\release
OutputBaseFilename=Ultimate-Converter-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
#endif
WizardStyle=modern
UninstallDisplayIcon={app}\Ultimate Converter.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
VersionInfoVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional options:"; Flags: unchecked

[Files]
Source: "..\dist\updated\Ultimate Converter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\build\installer-extras\*"; DestDir: "{app}\Documentation"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
#ifndef InstallerTest
Name: "{group}\{#AppName}"; Filename: "{app}\Ultimate Converter.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall Ultimate Converter"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Ultimate Converter.exe"; WorkingDir: "{app}"; Tasks: desktopicon
#endif

[Run]
Filename: "{app}\Ultimate Converter.exe"; Description: "Launch Ultimate Converter"; Flags: nowait postinstall skipifsilent
