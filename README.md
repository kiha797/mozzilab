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
| 모찌PDF | PDF 변환·합치기·나누기 | 🛠 준비 중 |
| 모찌압축 | 압축 프로그램 | 🛠 준비 중 |

모든 제품은 **무료**(광고 포함)이며, **모찌 플러스**(월 5,500원)를 구독하면 광고 없이 쓸 수 있습니다.

## 다운로드
👉 [Releases](../../releases) 에서 `MochiCapture_Setup_x.x.x.exe` 를 받으세요. (Windows 10 / 11)

## 폴더 구성
| 폴더 | 내용 |
|---|---|
| [`web/`](web) | 웹사이트 — Cloudflare Workers + D1 (회원·구독·결제·관리자·PC 프로그램용 API) |
| [`mochi_capture/`](mochi_capture) | 모찌캡처 PC 프로그램 (Python · PySide6) |

자세한 설치·배포 방법은 **[README_먼저읽어주세요.md](README_먼저읽어주세요.md)** 를 보세요.

## 보안 안내
결제 키·관리자 비밀번호 등 비밀 값은 이 저장소에 넣지 않고 **Cloudflare 대시보드의 Secret** 에만 저장합니다.
`web/.dev.vars.example` 의 비밀번호는 내 PC 테스트 전용 예시입니다.
