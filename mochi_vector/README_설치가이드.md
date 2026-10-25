# 모찌벡터 — 일러스트레이터 대체 프로그램

모찌벡터 는 오픈소스 **VectorCraft**(아트크래프트 ArtCraft 팀 · MIT/Apache-2.0)를 바탕으로 모찌랩이 만든 프로그램입니다.
화면 · 메뉴 · 도구 · 단축키가 일러스트레이터 와 거의 같고, 모찌랩 로그인 · 광고 · 자동 업데이트가 붙어 있어요.

## 설치 (가장 쉬운 방법)
1. https://mozzilab.labelpos.com 에서 **모찌벡터** 의 **[무료 다운로드]** 를 누릅니다.
2. 받은 `MochiVector_Setup.exe` 를 두 번 누르고 **[다음] → [설치]**.
   - 파란 "Windows의 PC 보호" 창이 뜨면 **[추가 정보] → [실행]**.
3. 바탕화면의 **모찌벡터** 아이콘으로 실행! 새 버전이 나오면 자동으로 알려 줍니다.

> PC 에 원본 VectorCraft 가 깔려 있어도 괜찮아요. 설정 폴더(`%APPDATA%\\MochiVector`)가 따로라 서로 섞이지 않습니다.

## 이 폴더에 있는 것
| 파일 | 내용 |
|---|---|
| `installer.iss` | 설치 프로그램(Inno Setup) 설정 |
| `../artcraft_kit/apply.py` | 원본 VectorCraft 소스를 모찌벡터 로 바꾸는 스크립트 (이름 · 아이콘 · 로그인 · 광고 · 업데이트) |
| `../artcraft_kit/mozzi.rs` | 모찌랩 로그인 · 광고 · 자동 업데이트 코드 (Rust) |
| `../artcraft_kit/upstream.json` | 어느 버전의 원본을 쓸지 (커밋 번호) |

## 원본이 새 버전을 내면? (업그레이드 방법)
1. `artcraft_kit/upstream.json` 의 `rev` 를 원본 저장소(https://github.com/storytold/vectorcraft)의 새 커밋 번호로 바꿉니다.
2. GitHub → Actions → "설치파일 만들기" → Run workflow.
3. 원본 코드가 많이 바뀌어 `apply.py` 가 고칠 곳을 못 찾으면 빌드가 멈추고 어느 파일인지 알려 줍니다. 그 부분만 고치면 돼요.

## 내 PC 에서 직접 빌드하기 (개발자용)
```
git clone https://github.com/storytold/vectorcraft src
cd src && git checkout <upstream.json 의 rev> && cd ..
python artcraft_kit/apply.py vector src 1.2.0
cd src && cargo build --release -p vectorcraft
```
(Rust 설치: https://rustup.rs — 첫 빌드는 20~40분 걸립니다)
