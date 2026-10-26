# 모찌한글 — 한글(HWP) 문서 편집기

한컴오피스가 없어도 `.hwp` · `.hwpx` 문서를 열고, 고치고, 저장하는 무료 프로그램입니다 (광고 포함, 모찌 플러스 구독 시 광고 없음).

## 설치 (가장 쉬운 방법)
1. https://mozzilab.labelpos.com 에서 **모찌한글** 의 **[무료 다운로드]** 를 누릅니다.
2. 받은 `MochiHwp_Setup.exe` 를 두 번 누르고 **[다음] → [설치]**.
   - 파란 "Windows의 PC 보호" 창이 뜨면 **[추가 정보] → [실행]**.
   - 화면을 그리는 Microsoft Edge WebView2 가 없는 PC 에는 자동으로 함께 설치됩니다.
3. `.hwp` 파일에서 오른쪽 클릭 → **모찌한글로 열기**.
   - 한컴오피스가 없는 PC 에서는 `.hwp` 를 두 번 눌러도 바로 열립니다 (한컴오피스가 있으면 그대로 둡니다).

## 구성 (개발자용)
| 파일 | 내용 |
|---|---|
| `desk/` | 데스크톱 앱(Tauri 2): 창 · 파일 열기 · 모찌LAB. 로그인/광고/자동 업데이트 (`overlay.js` 가 화면, `mozzi_api.rs` 가 동작) |
| `installer.iss` | 설치 프로그램 (Inno Setup) |
| `../artcraft_kit/apply.py hwp` | 오픈소스 HWP 편집기(MIT) 원본을 모찌한글로 바꾸는 스크립트 |
| `../artcraft_kit/upstream.json` | 원본 버전(커밋)과 받을 폴더 목록 |

편집 엔진은 Rust → WebAssembly, 편집 화면은 TypeScript(Vite) 로 빌드되며 GitHub Actions 가 자동으로 만듭니다.
