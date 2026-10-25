"""브랜드 정보와 서버 주소. 웹사이트를 실제 인터넷 주소에 올리면 SERVER_URL 만 바꾸면 된다."""
import os

BRAND_NAME = "모찌랩"
BRAND_NAME_EN = "MozziLab"
APP_NAME = "모찌캡처"
APP_ID = "MochiCapture"
APP_SLUG = "capture"            # 서버에 등록된 제품 코드
APP_VERSION = "1.0.0"

# 모찌랩 웹사이트 주소 (로그인·구독·광고) - Cloudflare 에 배포한 주소
# 환경변수 MOCHI_SERVER 가 있으면 그 값을 쓴다 (테스트용).
SERVER_URL = os.environ.get("MOCHI_SERVER", "https://mozzilab.labelpos.com").rstrip("/")

PINK = "#ff6f91"
PINK_DARK = "#e8557a"
PINK_SOFT = "#fff0f4"
PINK_LIGHT = "#ffe3eb"
INK = "#3b2f2f"
