; 모찌압축 설치 프로그램 (Inno Setup 6)
; 직접 만들 때: 3_build_exe.bat 실행 후 이 파일을 Inno Setup 으로 열고 [Build] > [Compile]
; (GitHub 에서는 .github/workflows/release.yml 이 자동으로 만듭니다)
#define MyAppName "모찌압축"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "모찌랩 (MozziLab)"
#define MyAppExeName "MochiZip.exe"

[Setup]
AppId={{8B4D3E5C-6F70-4CAD-9E3F-MOCHIZIP0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://mozzilab.labelpos.com
DefaultDirName={autopf}\MochiZip
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=MochiZip_Setup
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
Source: "dist\MochiZip\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} 제거"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\MochiZipExtract"; ValueType: string; ValueName: ""; ValueData: "모찌압축으로 여기에 풀기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\MochiZipExtract"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\MochiZipExtract\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" --extract-here ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\MochiZipOpen"; ValueType: string; ValueName: ""; ValueData: "모찌압축으로 열기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\MochiZipOpen"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.zip\shell\MochiZipOpen\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.7z\shell\MochiZipExtract"; ValueType: string; ValueName: ""; ValueData: "모찌압축으로 여기에 풀기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.7z\shell\MochiZipExtract"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.7z\shell\MochiZipExtract\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" --extract-here ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.7z\shell\MochiZipOpen"; ValueType: string; ValueName: ""; ValueData: "모찌압축으로 열기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.7z\shell\MochiZipOpen"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.7z\shell\MochiZipOpen\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\*\shell\MochiZipCompress"; ValueType: string; ValueName: ""; ValueData: "모찌압축으로 압축하기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\*\shell\MochiZipCompress"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\*\shell\MochiZipCompress\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" --compress ""%1"""
Root: HKA; Subkey: "Software\Classes\Directory\shell\MochiZipCompress"; ValueType: string; ValueName: ""; ValueData: "모찌압축으로 압축하기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Directory\shell\MochiZipCompress"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\Directory\shell\MochiZipCompress\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" --compress ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "모찌압축 지금 실행"; Flags: nowait postinstall skipifsilent
; 자동 업데이트(조용히 설치)가 끝나면 프로그램을 다시 켠다
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"
