; 모찌포토 설치 프로그램 (Inno Setup 6)
; GitHub 의 .github/workflows/release.yml 이 자동으로 만듭니다.
; (dist\MochiPhoto.exe 는 아트크래프트 photocraft 소스를 artcraft_kit\apply.py 로 바꿔서 빌드한 결과)
#define MyAppName "모찌포토"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "모찌랩 (MozziLab)"
#define MyAppExeName "MochiPhoto.exe"

[Setup]
AppId={{9C5E4F6D-7081-4DBE-AF40-MOCHIPHOTO01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://mozzilab.labelpos.com
DefaultDirName={autopf}\MochiPhoto
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=MochiPhoto_Setup
SetupIconFile=..\artcraft_kit\icons\photo.ico
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
Source: "dist\MochiPhoto.exe"; DestDir: "{app}"; Flags: ignoreversion
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
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.psd\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.psd\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.psd\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.psb\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.psb\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.psb\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.png\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpg\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.jpeg\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.webp\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tif\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.tiff\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.bmp\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.gif\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xcf\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xcf\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.xcf\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.kra\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.kra\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.kra\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ora\shell\MochiPhoto"; ValueType: string; ValueName: ""; ValueData: "모찌포토로 편집"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ora\shell\MochiPhoto"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.ora\shell\MochiPhoto\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
; .pcraft 파일(작업 파일)을 두 번 누르면 바로 열리게
Root: HKA; Subkey: "Software\Classes\.pcraft"; ValueType: string; ValueName: ""; ValueData: "MochiPhoto.Document"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\MochiPhoto.Document"; ValueType: string; ValueName: ""; ValueData: "모찌포토 작업 파일"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\MochiPhoto.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\MochiPhoto.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "모찌포토 지금 실행"; Flags: nowait postinstall skipifsilent
; 자동 업데이트(조용히 설치)가 끝나면 프로그램을 다시 켠다
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"
