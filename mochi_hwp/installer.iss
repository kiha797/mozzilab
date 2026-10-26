; 모찌한글 설치 프로그램 (Inno Setup 6)
; GitHub 의 .github/workflows/release.yml 이 자동으로 만듭니다.
; (dist\MochiHwp.exe 는 아트크래프트 rhwp 소스를 artcraft_kit\apply.py 로 바꿔서 빌드한 결과)
#define MyAppName "모찌한글"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "모찌랩 (MozziLab)"
#define MyAppExeName "MochiHwp.exe"

[Setup]
AppId={{B7F06182-93A4-4F01-C162-MOCHIHWP0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://mozzilab.labelpos.com
DefaultDirName={autopf}\MochiHwp
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=MochiHwp_Setup
SetupIconFile=..\artcraft_kit\icons\hwp.ico
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
; 화면을 그리는 Microsoft Edge WebView2 런타임 (없는 PC 에만 설치)
Source: "dist\MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedsWebView2
Source: "dist\MochiHwp.exe"; DestDir: "{app}"; Flags: ignoreversion
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
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.hwp\shell\MochiHwp"; ValueType: string; ValueName: ""; ValueData: "모찌한글로 열기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.hwp\shell\MochiHwp"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.hwp\shell\MochiHwp\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.hwpx\shell\MochiHwp"; ValueType: string; ValueName: ""; ValueData: "모찌한글로 열기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.hwpx\shell\MochiHwp"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.hwpx\shell\MochiHwp\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.hml\shell\MochiHwp"; ValueType: string; ValueName: ""; ValueData: "모찌한글로 열기"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.hml\shell\MochiHwp"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Classes\SystemFileAssociations\.hml\shell\MochiHwp\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
; 한컴오피스가 없는 PC 에서는 .hwp · .hwpx 를 두 번 누르면 모찌한글로 열리게 (한컴오피스가 있으면 그대로 둔다)
Root: HKA; Subkey: "Software\Classes\.hwp"; ValueType: string; ValueName: ""; ValueData: "MochiHwp_hwp"; Flags: uninsdeletevalue; Check: NoOtherHwpApp('.hwp')
Root: HKA; Subkey: "Software\Classes\MochiHwp_hwp"; ValueType: string; ValueName: ""; ValueData: "한글 문서"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\MochiHwp_hwp\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\MochiHwp_hwp\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\.hwpx"; ValueType: string; ValueName: ""; ValueData: "MochiHwp_hwpx"; Flags: uninsdeletevalue; Check: NoOtherHwpApp('.hwpx')
Root: HKA; Subkey: "Software\Classes\MochiHwp_hwpx"; ValueType: string; ValueName: ""; ValueData: "한글 문서 (HWPX)"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\MochiHwp_hwpx\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\MochiHwp_hwpx\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Microsoft Edge WebView2 설치 중..."; Flags: waituntilterminated; Check: NeedsWebView2
Filename: "{app}\{#MyAppExeName}"; Description: "모찌한글 지금 실행"; Flags: nowait postinstall skipifsilent
; 자동 업데이트(조용히 설치)가 끝나면 프로그램을 다시 켠다
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: WizardSilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillApp"

[Code]
function NeedsWebView2: Boolean;
var v: String;
begin
  Result := not (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', v) and (v <> '') and (v <> '0.0.0.0'))
        and not (RegQueryStringValue(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}', 'pv', v) and (v <> '') and (v <> '0.0.0.0'));
end;

function NoOtherHwpApp(Ext: String): Boolean;
var cur: String;
begin
  Result := True;
  if RegQueryStringValue(HKCR, Ext, '', cur) then
    if (cur <> '') and (Pos('MochiHwp', cur) = 0) then Result := False;
end;
