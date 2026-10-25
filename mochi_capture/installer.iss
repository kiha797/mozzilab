; 모찌캡처 설치 프로그램 만들기 (Inno Setup 6 용)
; 사용법: 3_build_exe.bat 실행 후, 이 파일을 Inno Setup 으로 열고 [Build] > [Compile]
#define MyAppName "모찌캡처"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "모찌랩 (MozziLab)"
#define MyAppExeName "MochiCapture.exe"

[Setup]
AppId={{6E2B1C3A-4D5F-4A8B-9C1D-MOCHICAPTURE01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\MochiCapture
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=MochiCapture_Setup_{#MyAppVersion}
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"
Name: "startup"; Description: "Windows 시작 시 자동 실행"; GroupDescription: "추가 작업:"

[Files]
Source: "dist\MochiCapture\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "MochiCapture"; ValueData: """{app}\{#MyAppExeName}"" --hidden"; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "모찌캡처 지금 실행"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"
