; GestureVLC Windows installer (Inno Setup)
; Compile with: ISCC installer\GestureVLC.iss

#define MyAppName "GestureVLC"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "GestureVLC"
#define MyAppExeName "GestureVLC.exe"
#define MyAppBuildDir "..\dist\GestureVLC"

[Setup]
AppId={{6E8EE570-A03D-4F8B-B7D7-9C42A238BC15}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableDirPage=no
OutputDir=..\dist-installer
OutputBaseFilename=GestureVLC-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
SetupIconFile=..\assets\GestureVLC.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#MyAppBuildDir}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\GestureVLC.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\GestureVLC.ico"; Tasks: desktopicon

[Run]
; Download MediaPipe hand model if it's missing.
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$model1='{app}\_internal\gesture\hand_landmarker.task'; $model2='{app}\gesture\hand_landmarker.task'; if (!(Test-Path -LiteralPath $model1)) {{ New-Item -ItemType Directory -Force -Path (Split-Path -Parent $model1) | Out-Null; Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task' -OutFile $model1 }}; if (!(Test-Path -LiteralPath $model2)) {{ New-Item -ItemType Directory -Force -Path (Split-Path -Parent $model2) | Out-Null; Copy-Item -LiteralPath $model1 -Destination $model2 -Force }}"""; \
    Flags: runhidden waituntilterminated

; Optionally install VLC (required for python-vlc backend).
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$pf=[Environment]::GetFolderPath('ProgramFiles'); $pf86=[Environment]::GetFolderPath('ProgramFilesX86'); $vlc1=Join-Path $pf 'VideoLAN\VLC\vlc.exe'; $vlc2=Join-Path $pf86 'VideoLAN\VLC\vlc.exe'; if (!(Test-Path $vlc1) -and !(Test-Path $vlc2)) {{ if (Get-Command winget -ErrorAction SilentlyContinue) {{ winget install --id VideoLAN.VLC -e --accept-package-agreements --accept-source-agreements }} }}"""; \
    Flags: waituntilterminated

Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  if not DirExists(ExpandConstant('{#MyAppBuildDir}')) then
  begin
    MsgBox(
      'Build output not found at "{#MyAppBuildDir}".' + #13#10 +
      'Run the PowerShell build script first:' + #13#10 +
      '  powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1',
      mbError,
      MB_OK
    );
    Result := False;
    exit;
  end;

  Result := True;
end;
