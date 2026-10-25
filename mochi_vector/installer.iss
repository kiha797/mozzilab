; 모찌벡터 설치 프로그램 (Inno Setup 6)
; GitHub 의 .github/workflows/release.yml 이 자동으로 만듭니다.
; (dist\MochiVector.exe 는 아트크래프트 vectorcraft 소스를 artcraft_kit\apply.py 로 바꿔서 빌드한 결과)
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
SetupIconFile=..\artcraft_kit\icons\vector.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=yes
CloseApplications=yes

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕화면에 바로가기 만들기"; GroupDescription: "추가 작업:"

[Files]
Source: "dist\MochiVector.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs

[InstallDelete]
; 예전(파이썬) 버전의 파일 정리
Type: filesandordirs; Name: "{app}\_internal"
Type: files; Name: "{app}\*.pyd"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.svg\shell\MochiVector"; ValueType: string; ValueName: ""; ValueData: "모찌벡터로 열기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.svg\shell\MochiVector"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.svg\shell\MochiVector\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ai\shell\MochiVector"; ValueType: string; ValueName: ""; ValueData: "모찌벡터로 열기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ai\shell\MochiVector"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ai\shell\MochiVector\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.eps\shell\MochiVector"; ValueType: string; ValueName: ""; ValueData: "모찌벡터로 열기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.eps\shell\MochiVector"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.eps\shell\MochiVector\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\MochiVector"; ValueType: string; ValueName: ""; ValueData: "모찌벡터로 열기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\MochiVector"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.pdf\shell\MochiVector\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
; .vectorcraft 파일(작업 파일)을 두 번 누르면 바로 열리게
Root: HKA; Subkey: "Software\Classes\.vectorcraft"; ValueType: string; ValueName: ""; ValueData: "MochiVector.Document"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\MochiVector.Document"; ValueType: string; ValueName: ""; ValueData: "모찌벡터 작업 파일"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\MochiVector.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\MochiVector.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "모찌벡터 지금 실행"; Flags: nowait postinstall skipifsilent
; 자동 업데이트(조용히 설치)가 끝나면 프로그램을 다시 켠다
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"
