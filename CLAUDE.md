# 모찌LAB. 저장소 작업 규칙

## 대화
- 사용자는 개발자가 아닌 PM(동원약품 전략기획실)이다. **모든 설명은 한국어로**, 초보자도 따라 할 수 있게 하나하나 자세히 쓴다.
- 브랜드명은 **모찌LAB.** (영문 MozziLab). 화면 · 문서에 '모찌랩'이라고 쓰지 않는다.

## 업데이트는 무조건 자동 배포
- 프로그램 코드(`mochi_*/`, `shared/`, `artcraft_kit/`)를 고치면 **반드시 커밋하고 main 에 푸시**한다.
  푸시하면 `.github/workflows/release.yml` 이 버전 끝자리를 자동으로 +1 해서 설치파일 5개를 만들고 Releases 에 올린다.
- 설치된 프로그램은 켤 때 · 로그인할 때 · 3시간마다 새 버전을 확인해서 **묻지 않고** 받아 설치한다
  (작업 중이거나 저장 안 된 문서가 있으면 끝날 때까지 기다림). 관련 코드: `shared/updater.py`, `artcraft_kit/mozzi.rs`.
- 배포가 끝나면 빌드 결과(성공/실패)를 확인해서 사용자에게 한국어로 알린다. 홈페이지 버전 표시는 `web/src/db.ts` 의 `syncVersions` 가 자동으로 맞춘다.
- 홈페이지(`web/`)만 바꾼 경우는 Cloudflare 가 자동 배포하고 설치파일은 새로 만들지 않는다.

## 구성
- `mochi_capture`, `mochi_pdf`, `mochi_zip`: 파이썬(PySide6) 프로그램, 공통 코드는 `shared/`
- `mochi_photo`, `mochi_vector`: 오픈소스 PhotoCraft · VectorCraft(MIT/Apache-2.0)를 `artcraft_kit/apply.py` 로 바꿔서 Rust 로 빌드.
  화면에는 원본 이름 · 출처를 표시하지 않는다(사용자 요청). 단, 라이선스 파일은 설치 폴더 `licenses` 에 꼭 넣는다(라이선스 의무).
- `web/`: 홈페이지 (Cloudflare Workers + D1 `mozzilab-db`)
- 커밋 작성자: Claude <noreply@anthropic.com>
