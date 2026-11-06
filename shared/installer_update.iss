; 모찌LAB. 자동 업데이트 화면 (모든 설치파일이 #include 로 함께 씀)
; 프로그램이 새 버전을 받아 조용히 설치할 때(/SILENT 또는 /VERYSILENT)는
; 설치 마법사 대신 작은 "업데이트하고 있어요" 창만 보여 준다. 사용자가 직접 설치할 때는 평소 화면 그대로.

[Code]
var
  MozziForm: TForm;
  MozziText: TNewStaticText;
  MozziBar: TNewProgressBar;

procedure MozziHideWizard;
begin
  { /SILENT 로 실행되면 설치 진행 창이 뜨므로 화면 밖으로 치운다 (예전 버전 프로그램이 이렇게 부름) }
  if WizardSilent and (WizardForm <> nil) then
    WizardForm.Left := -32000;
end;

procedure MozziShowUpdate;
var
  Bar: TBitmapImage;
  Title: TNewStaticText;
begin
  if (not WizardSilent) or (MozziForm <> nil) then
    Exit;
  MozziForm := TForm.CreateNew(nil);
  MozziForm.ClientWidth := ScaleX(400);
  MozziForm.ClientHeight := ScaleY(150);
  MozziForm.BorderStyle := bsDialog;
  MozziForm.Caption := '{#MyAppName} 업데이트';
  MozziForm.Position := poScreenCenter;
  MozziForm.BorderIcons := [];
  MozziForm.Color := clWhite;

  { 위쪽 브랜드 색 띠 (인디고 블루 #4F5BFF) }
  Bar := TBitmapImage.Create(MozziForm);
  Bar.Parent := MozziForm;
  Bar.Left := 0;
  Bar.Top := 0;
  Bar.Width := MozziForm.ClientWidth;
  Bar.Height := ScaleY(6);
  Bar.BackColor := $FF5B4F;

  Title := TNewStaticText.Create(MozziForm);
  Title.Parent := MozziForm;
  Title.Left := ScaleX(24);
  Title.Top := ScaleY(26);
  Title.Font.Size := 12;
  Title.Font.Style := [fsBold];
  Title.Caption := '{#MyAppName}을(를) 새 버전으로 업데이트하고 있어요';

  MozziText := TNewStaticText.Create(MozziForm);
  MozziText.Parent := MozziForm;
  MozziText.Left := ScaleX(24);
  MozziText.Top := ScaleY(58);
  MozziText.Font.Color := $695547;
  MozziText.Caption := '버전 {#MyAppVersion} · 잠시 후 자동으로 다시 켜져요';

  MozziBar := TNewProgressBar.Create(MozziForm);
  MozziBar.Parent := MozziForm;
  MozziBar.Left := ScaleX(24);
  MozziBar.Top := ScaleY(96);
  MozziBar.Width := MozziForm.ClientWidth - ScaleX(48);
  MozziBar.Height := ScaleY(10);
  MozziBar.Min := 0;
  MozziBar.Max := 100;
  MozziBar.Position := 0;

  MozziForm.Show;
  MozziForm.Refresh;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  MozziHideWizard;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    MozziHideWizard;
    MozziShowUpdate;
  end;
  if (CurStep = ssPostInstall) and (MozziForm <> nil) then
  begin
    MozziBar.Position := 100;
    MozziText.Caption := '업데이트를 마쳤어요. 다시 켜는 중…';
    MozziForm.Refresh;
  end;
end;

procedure CurInstallProgressChanged(CurProgress, MaxProgress: Integer);
begin
  if (MozziForm <> nil) and (MaxProgress > 0) then
  begin
    MozziBar.Position := CurProgress * 100 div MaxProgress;
    MozziForm.Refresh;
  end;
end;

procedure DeinitializeSetup;
begin
  if MozziForm <> nil then
  begin
    MozziForm.Free;
    MozziForm := nil;
  end;
end;
