; 모찌벡터 설치 프로그램 (Inno Setup 6)
; 직접 만들 때: 3_build_exe.bat 실행 후 이 파일을 Inno Setup 으로 열고 [Build] > [Compile]
; (GitHub 에서는 .github/workflows/release.yml 이 자동으로 만듭니다)
#define MyAppName "모찌벡터"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "모찌랩 (MozziLab)"
#define MyAppExeName "MochiVector.exe"

[Setup]
AppId={{AD6F5071-8192-4ECF-B051-MOCHIVECTOR1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://mozzilab.labelpos.com
DefaultDirName={autopf}\MochiVector
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=MochiVector_Setup
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"

[Files]
Source: "dist\MochiVector\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.svg\shell\MochiVector"; ValueType: string; ValueName: ""; ValueData: "모찌벡터로 열기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.svg\shell\MochiVector"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.svg\shell\MochiVector\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
; .mvec 파일(이 프로그램 전용 저장 파일)을 두 번 누르면 바로 열리게
Root: HKA; Subkey: "Software\Classes\.mvec"; ValueType: string; ValueName: ""; ValueData: "MochiVector.Document"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\MochiVector.Document"; ValueType: string; ValueName: ""; ValueData: "모찌벡터 디자인"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\MochiVector.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\MochiVector.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "모찌벡터 지금 실행"; Flags: nowait postinstall skipifsilent
; 자동 업데이트(조용히 설치)가 끝나면 프로그램을 다시 켠다
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"
