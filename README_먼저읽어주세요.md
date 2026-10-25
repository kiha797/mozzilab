# 🍡 모찌랩 (MozziLab) — 전체 안내서

> **"말랑말랑, 누구나 쉬운 PC 도구"**
> 무료(광고형) PC 프로그램을 하나씩 늘려가고, 광고 없이 쓰고 싶은 사람은 **모찌 플러스(월 5,500원)** 를 구독합니다.
> 웹사이트 주소: **https://mozzilab.labelpos.com** (Cloudflare 에 배포)

---

## 1. 브랜드

| 항목 | 내용 |
|---|---|
| 브랜드 | **모찌랩** (MozziLab) — 말랑한 도구를 만드는 '연구소(Lab)' |
| 마스코트 | 하얗고 말랑한 찹쌀떡 **'모찌'** |
| 슬로건 | 말랑말랑, 누구나 쉬운 PC 도구 |
| 제품 | **모찌캡처**(지금) · 모찌PDF · 모찌압축 (출시 예정으로 사이트에 등록됨) |
| 구독 | **모찌 플러스** — 모든 모찌랩 PC 제품 광고 제거, 월 5,500원 |
| 색 | 핑크 `#FF6F91` · 크림 `#FFF8F1` · 팥색 `#3B2F2F` · 민트 `#7EC8A9` · 오렌지 `#FFB86B` |

> ⚠️ 키프리스(www.kipris.or.kr)에서 "모찌랩", "MozziLab", "모찌캡처" 상표를 꼭 검색해 보세요.

---

## 2. 폴더 구성 (GitHub 공개 저장소 `mozzilab` 하나에 모두 들어갑니다)

```
MozziLab/
├─ README_먼저읽어주세요.md    ← 지금 이 파일
├─ web/                       ← ① 웹사이트 (Cloudflare Workers + D1 데이터베이스)
│   ├─ wrangler.toml          ← Cloudflare 배포 설정 (도메인, DB, 매일 정기결제)
│   ├─ src/                   ← 사이트 프로그램 (TypeScript)
│   │   ├─ routes/site.tsx    사용자 사이트   ├─ routes/admin.tsx  관리자 사이트
│   │   ├─ routes/api.ts      PC 프로그램용   ├─ billing.ts        토스페이먼츠 정기결제
│   │   └─ views/             화면 디자인
│   └─ public/                ← 그림, CSS
└─ mochi_capture/             ← ② PC 캡처 프로그램 (모찌캡처, 파이썬)
```

**왜 웹사이트를 다시 만들었나요?** Cloudflare 는 파이썬(Flask) 서버를 그대로 실행하지 못합니다.
그래서 같은 화면·같은 기능을 Cloudflare 전용 방식(Workers + D1)으로 다시 만들었습니다.
- 서버 컴퓨터를 켜둘 필요가 없고, 전 세계 어디서나 빠르며, 작은 규모에서는 **무료**입니다.
- **GitHub 에 올리면 자동으로 배포**됩니다. (코드를 고쳐서 올리기만 하면 끝)
- PC 프로그램과 주고받는 방식은 예전과 똑같아서 모찌캡처는 그대로 연결됩니다.

---

## 3. Cloudflare 연결 (가장 쉬움 · 클릭 몇 번)

이미 준비된 것 ✅
- 데이터베이스 `mozzilab-db` (표 13개 + 관리자 계정 + 로그인 암호키) — Claude 가 Cloudflare 커넥터로 만들어 둠
- `web/wrangler.toml` 에 데이터베이스 ID 와 도메인(mozzilab.labelpos.com) 설정 완료
- **비밀값(Secret)은 넣지 않아도 됩니다** (암호키를 데이터베이스에서 읽음)

남은 일 — Cloudflare 화면에서 GitHub 연결 (처음 한 번)
1. https://dash.cloudflare.com → 왼쪽 **Workers 및 Pages** → **애플리케이션 생성(Create application)**
2. **저장소 가져오기(Import a repository)** → GitHub 계정 연결 → **kiha797 / mozzilab** 선택
3. 설정 화면에서
   - 프로젝트 이름: `mozzilab`
   - **고급 설정 → 루트 디렉터리(Root directory): `web`**  ← 가장 중요!
   - 빌드 명령: 비워두기 / 배포 명령: `npx wrangler deploy`
4. **저장 및 배포(Save and Deploy)** → 1~2분 뒤 https://mozzilab.labelpos.com
5. 관리자: https://mozzilab.labelpos.com/admin  (처음 받은 비밀번호로 로그인 후 마이페이지에서 비밀번호 변경)

이후에는 GitHub `main` 이 바뀔 때마다 Cloudflare 가 자동으로 다시 배포합니다.

---

## 3-0. (다른 방법) GitHub Actions 로 배포 · 토큰 필요

GitHub 에 코드가 올라가면 **GitHub 이 알아서 Cloudflare 에 배포**합니다 (`.github/workflows/deploy.yml`).
데이터베이스 만들기, 배포, 도메인 연결, 관리자 계정 만들기까지 자동입니다. **열쇠 4개만 넣어 주세요.**

### 3-A. Cloudflare 에서 열쇠(API 토큰) 만들기
1. https://dash.cloudflare.com/profile/api-tokens 접속 → **토큰 생성(Create Token)**
2. **"Cloudflare Workers 편집(Edit Cloudflare Workers)"** 템플릿 옆 **템플릿 사용(Use template)**
3. **권한(Permissions)** 에서 **+ 추가(Add more)** 를 눌러 아래 2줄을 더 넣기
   - `계정(Account)` · `D1` · `편집(Edit)`
   - `영역(Zone)` · `DNS` · `편집(Edit)`
4. **계정 리소스(Account Resources)**: 내 계정 선택 / **영역 리소스(Zone Resources)**: `특정 영역(Specific zone)` → `labelpos.com`
5. **요약 보기(Continue to summary)** → **토큰 생성(Create Token)** → 나온 긴 글자를 **복사** (이 화면을 닫으면 다시 볼 수 없어요!)

### 3-B. Cloudflare 계정 ID 복사
https://dash.cloudflare.com → 왼쪽 **Workers 및 Pages(Workers & Pages)** → 오른쪽 아래 **계정 ID(Account ID)** 옆 복사 버튼

### 3-C. GitHub 에 열쇠 넣기
1. https://github.com/kiha797/mozzilab/settings/secrets/actions 접속
   (저장소 → **Settings(설정)** → 왼쪽 **Secrets and variables(비밀값과 변수)** → **Actions**)
2. 초록 버튼 **New repository secret(새 비밀값)** 을 눌러 아래 4개를 하나씩 추가

   | Name (이름) — 그대로 복사 | Secret (값) |
   |---|---|
   | `CLOUDFLARE_API_TOKEN` | 3-A 에서 복사한 토큰 |
   | `CLOUDFLARE_ACCOUNT_ID` | 3-B 에서 복사한 계정 ID |
   | `ADMIN_EMAIL` | 관리자로 쓸 내 이메일 |
   | `ADMIN_PASSWORD` | 관리자 비밀번호 (8자 이상) |

   (나중에 결제·소셜 로그인을 붙일 때 `TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY`, `NAVER_CLIENT_ID` … 도 같은 곳에 넣으면 됩니다)

### 3-D. 배포 실행
1. https://github.com/kiha797/mozzilab/actions 접속 → 왼쪽 **Cloudflare 배포** → 오른쪽 **Run workflow(실행)** → 초록 **Run workflow**
2. 1~2분 뒤 초록 ✅ 가 뜨면 완료 → https://mozzilab.labelpos.com
   - 빨간 ❌ 가 뜨면 눌러서 내용을 캡처해 보내 주세요. (또는 Claude 에게 "배포 확인해줘")
3. 이후에는 `web` 폴더가 바뀔 때마다 **자동으로** 다시 배포됩니다.

> **준비 조건**: labelpos.com 이 같은 Cloudflare 계정에 **활성(Active)** 상태로 등록되어 있어야 합니다.

---

## 3-1. (다른 방법) Cloudflare 화면에서 직접 연결하기


### 준비물
- GitHub 계정 · Cloudflare 계정
- **labelpos.com 이 Cloudflare 에 등록**되어 있어야 합니다
  (Cloudflare 대시보드 첫 화면의 도메인 목록에 `labelpos.com` 이 '활성'으로 보이면 OK)

### ① GitHub 공개 저장소 만들기 (완료됨: kiha797/mozzilab)
1. github.com 로그인 → 오른쪽 위 **[+] → New repository**
2. Repository name: `mozzilab` / **Public** 선택 / README·.gitignore·license 는 **모두 체크하지 않기**(빈 저장소) → **Create repository**
   > 공개 저장소라도 결제 키·비밀번호는 저장소에 없고 Cloudflare Secret 에만 있으므로 안전합니다.
3. 이 코드를 올리는 방법은 둘 중 하나:
   - **(쉬움) Claude 에게 맡기기**: https://claude.ai/connect-github 에서 GitHub 을 연결하고, Claude GitHub App 을 `mozzilab` 저장소에 설치한 뒤 Claude 에게 "mozzilab 저장소에 올려줘"라고 말하기
   - **(직접)** GitHub Desktop 을 설치 → File → Add local repository → `MozziLab` 폴더 선택 → Publish

### 3-2. 데이터베이스(D1) 만들기
1. Cloudflare 대시보드 → 왼쪽 **Storage & Databases → D1 SQL Database → Create**
2. 이름: **`mozzilab-db`** → Create
3. 화면에 나온 **Database ID**(예: `3f2a9c1e-....`)를 복사
4. GitHub 저장소 → `web/wrangler.toml` 클릭 → 연필(✏️) 아이콘 → 아래 줄의 따옴표 안을 복사한 ID 로 바꾸기 → **Commit changes**
   ```toml
   database_id = "여기에-D1-Database-ID-를-붙여넣으세요"
   ```
   (Claude 에게 ID 를 알려주면 대신 바꿔서 올려 드립니다)

### 3-3. Cloudflare 에 GitHub 연결 (자동 배포)
1. Cloudflare 대시보드 → **Workers & Pages → Create → Workers 탭 → Import a repository**
2. **GitHub 연결** → `mozzilab` 저장소 선택
3. 설정:
   | 항목 | 값 |
   |---|---|
   | Project name | `mozzilab` |
   | **Root directory** (고급 설정) | **`web`** ← 꼭! |
   | Build command | (비워두기) |
   | Deploy command | `npx wrangler deploy` (기본값) |
4. **Save and Deploy** → 1~2분 후 배포 완료
5. `wrangler.toml` 에 적힌 대로 **mozzilab.labelpos.com** 도메인과 보안 인증서(HTTPS)가 자동으로 연결됩니다.
   (Workers → mozzilab → Settings → Domains & Routes 에서 확인. 처음엔 인증서 발급에 몇 분 걸릴 수 있어요)

### 3-4. 비밀 설정 넣기 (관리자 비밀번호 등)
Workers → **mozzilab → Settings → Variables and Secrets → Add** → 종류를 **Secret** 으로:

| 이름 | 값 | 필수 |
|---|---|---|
| `SECRET_KEY` | 아무 글자나 40자 이상 (로그인 쿠키 암호화) | ✅ |
| `ADMIN_EMAIL` | 관리자로 쓸 내 이메일 | ✅ |
| `ADMIN_PASSWORD` | 관리자 비밀번호 | ✅ |
| `TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY` | 토스페이먼츠 키 (없으면 테스트 모드) | 나중에 |
| `NAVER_CLIENT_ID/SECRET`, `KAKAO_CLIENT_ID/SECRET`, `GOOGLE_CLIENT_ID/SECRET` | 소셜 로그인 | 나중에 |

저장하면 바로 적용됩니다. 이제 **https://mozzilab.labelpos.com/admin** 에서 `ADMIN_EMAIL` / `ADMIN_PASSWORD` 로 로그인하세요.

> 💡 관리자를 바꾸고 싶으면 `ADMIN_EMAIL` 만 다른 회원 이메일로 바꾸면 그 회원이 관리자가 됩니다.

### 3-5. 확인
- [ ] https://mozzilab.labelpos.com 접속 → 모찌랩 홈페이지
- [ ] 회원가입 → 요금제 → 🧪 테스트 결제 → 마이페이지에 '광고 없이 이용 중'
- [ ] 관리자 사이트에서 회원·결제가 보임
- [ ] 모찌캡처 [로그인] → 연결 승인 → 광고 사라짐

### 이후 수정할 때
GitHub 에 코드를 올리면(커밋) Cloudflare 가 **자동으로 다시 배포**합니다. 따로 할 일이 없습니다.
배포 기록은 Workers → mozzilab → **Deployments** 에서 보고, 문제가 있으면 이전 버전으로 되돌릴 수 있습니다.

---

## 4. 요금 (Cloudflare)
- **무료 플랜**: 하루 10만 요청, D1 5GB — 초기에는 충분합니다.
- 회원이 늘면 **Workers Paid (월 5달러)** 를 권장합니다. 요청 한도가 크게 늘고, 로그인 시 비밀번호 확인 같은 무거운 계산이 더 안정적입니다.

---

## 5. 결제·로그인 연동 (오픈 전)

### 토스페이먼츠 (정기결제)
1. tosspayments.com 가입 → 사업자 등록 → **자동결제(빌링) 계약 신청**
2. 개발자센터 → API 키 → 위 3-4 처럼 `TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY` 를 Secret 으로 추가
   (먼저 `test_` 키로 시험 → 문제 없으면 `live_` 키로 교체)
3. **매달 자동결제는 Cloudflare 가 매일 오전 9시에 자동 실행**합니다 (`wrangler.toml` 의 crons). 따로 할 일 없음.

### 소셜 로그인 — 콜백(Redirect) 주소
| 서비스 | 신청하는 곳 | 콜백 주소 |
|---|---|---|
| 네이버 | developers.naver.com | `https://mozzilab.labelpos.com/oauth/naver/callback` |
| 카카오 | developers.kakao.com (REST API 키 = CLIENT_ID) | `https://mozzilab.labelpos.com/oauth/kakao/callback` |
| 구글 | console.cloud.google.com → OAuth 클라이언트 | `https://mozzilab.labelpos.com/oauth/google/callback` |

### 사업 준비
- [ ] 사업자등록 + **통신판매업 신고**
- [ ] 이용약관·개인정보처리방침 법률 검토 (사이트의 약관은 예시)
- [ ] 사이트 바닥글의 회사명·이메일: `web/wrangler.toml` 의 `COMPANY_NAME`, `SUPPORT_EMAIL`

---

## 6. PC 프로그램 배포
1. `mochi_capture/brand.py` 의 주소가 `https://mozzilab.labelpos.com` 인지 확인 (이미 설정됨)
2. `3_build_exe.bat` → `installer.iss` 컴파일 → `MochiCapture_Setup_1.0.0.exe`
3. 설치파일 올리는 곳: GitHub `mozzilab` 저장소 → **Releases → Draft a new release**
   → Tag 에 `v1.0.0` 입력 → `MochiCapture_Setup_1.0.0.exe` 파일을 끌어다 놓기 → **Publish release**
   - 공개 저장소라 누구나 내려받을 수 있습니다.
   - 올린 파일 이름을 마우스 오른쪽 클릭 → **링크 주소 복사**
     (예: `https://github.com/kiha797/mozzilab/releases/download/v1.0.0/MochiCapture_Setup_1.0.0.exe`)
4. 관리자 → 제품 관리 → 모찌캡처 → **다운로드 주소**에 링크 붙여넣기 → 저장

---

## 7. 관리자 사이트 기능 (`/admin`)
대시보드(회원·유료 전환율·MRR·월별 그래프·광고 노출/클릭) · 회원 관리(이용권 부여/연장, 정지) · 구독 관리 ·
결제 내역/환불 · 라이선스(PC) 해제 · 광고 관리(이미지 업로드 1MB 이하, 기간, 비중, CTR) · 제품 관리 · 설정(요금, PC 대수, 팝업 빈도)

---

## 8. 내 PC에서 사이트 테스트하기 (개발자용)
```
cd web
npm install
copy .dev.vars.example .dev.vars
npx wrangler dev        →  http://127.0.0.1:8787  (관리자: admin@mozzilab.local / admin1234!)
```
모찌캡처를 이 테스트 서버에 연결하려면 실행 전에 `set MOCHI_SERVER=http://127.0.0.1:8787`

---

## 9. 다음 제품 (모찌PDF 등)
`mochi_capture` 의 `account.py`, `ads.py`, `brand.py`, `toast.py` 를 복사해 쓰고,
`brand.py` 에서 `APP_NAME="모찌PDF"`, `APP_ID="MochiPDF"`, `APP_SLUG="pdf"` 로 바꾸면
같은 계정·같은 구독으로 광고가 함께 사라집니다. (서버 API: `/api/device/start`, `/api/device/poll`, `/api/me`, `/api/ads?app=pdf`)
