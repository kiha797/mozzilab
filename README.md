<p align="center">
  <img src="web/public/img/mochi.svg" width="140" alt="모찌">
</p>

<h1 align="center">🍡 모찌랩 (MozziLab)</h1>
<p align="center"><b>말랑말랑, 누구나 쉬운 PC 도구</b><br>
<a href="https://mozzilab.labelpos.com">mozzilab.labelpos.com</a></p>

---

## 제품

| 제품 | 설명 | 상태 |
|---|---|---|
| **모찌캡처** | 직접지정 · 창 · 단위영역 · 전체화면 · 스크롤 · 크기지정 캡처, 도형·펜·모자이크 편집 | ✅ v1.0.0 |
| **모찌PDF** | 합치기 · 나누기 · 페이지 편집 · 이미지↔PDF · 용량 줄이기 · 암호 | ✅ v1.0.0 |
| **모찌압축** | ZIP · 7Z 압축/풀기, TAR 풀기, 암호, 한글 이름 복구, 오른쪽 클릭 메뉴 | ✅ v1.0.0 |
| **모찌포토** | 포토샵 · 포토피아처럼 레이어 사진 편집 — 브러시, 선택, 복제 도장, 색 보정, 필터, PSD 열기/저장 | ✅ v1.1.0 |
| **모찌벡터** | 일러스트레이터 · 벡터크래프트처럼 벡터 디자인 — 펜, 도형, 문자, 정렬, 패스파인더, SVG/PDF/PNG | ✅ v1.1.0 |

모든 제품은 **무료**(광고 포함)이며, **모찌 플러스**(월 5,500원)를 구독하면 광고 없이 쓸 수 있습니다.

## 다운로드
👉 [Releases](../../releases/latest) 에서 받으세요. (Windows 10 / 11)

| 📸 [모찌캡처](../../releases/latest/download/MochiCapture_Setup.exe) | 📄 [모찌PDF](../../releases/latest/download/MochiPDF_Setup.exe) | 🗜️ [모찌압축](../../releases/latest/download/MochiZip_Setup.exe) | 🎨 [모찌포토](../../releases/latest/download/MochiPhoto_Setup.exe) | ✒️ [모찌벡터](../../releases/latest/download/MochiVector_Setup.exe) |
|---|---|---|---|---|

## 폴더 구성
| 폴더 | 내용 |
|---|---|
| [`web/`](web) | 웹사이트 — Cloudflare Workers + D1 (회원·구독·결제·관리자·PC 프로그램용 API) |
| [`mochi_capture/`](mochi_capture) | 모찌캡처 PC 프로그램 (Python · PySide6) |
| [`mochi_pdf/`](mochi_pdf) | 모찌PDF PC 프로그램 |
| [`mochi_zip/`](mochi_zip) | 모찌압축 PC 프로그램 |
| [`mochi_photo/`](mochi_photo) | 모찌포토 PC 프로그램 (사진 편집) |
| [`mochi_vector/`](mochi_vector) | 모찌벡터 PC 프로그램 (벡터 디자인) |
| [`shared/`](shared) | 모든 프로그램이 함께 쓰는 코드 (로그인 · 광고 · 디자인 · 창 틀) |

자세한 설치·배포 방법은 **[README_먼저읽어주세요.md](README_먼저읽어주세요.md)** 를 보세요.

## 보안 안내
결제 키·관리자 비밀번호 등 비밀 값은 이 저장소에 넣지 않고 **Cloudflare 대시보드의 Secret** 에만 저장합니다.
`web/.dev.vars.example` 의 비밀번호는 내 PC 테스트 전용 예시입니다.
