"""모찌압축 브랜드 정보"""
import os

BRAND_NAME = "모찌LAB."
BRAND_NAME_EN = "MozziLab"
APP_NAME = "모찌압축"
APP_ID = "MochiZip"
APP_SLUG = "zip"               # 서버에 등록된 제품 코드
APP_VERSION = "1.0.0"
SERVER_URL = os.environ.get("MOCHI_SERVER", "https://mozzilab.labelpos.com").rstrip("/")

# 프로그램 아이콘 (고구마색 모찌 + 지퍼)
APP_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs><linearGradient id="gzip" x1="0" y'
           '1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFBE2E"/><stop offset="1" stop-color="#F28A00"/></'
           'linearGradient><linearGradient id="gziph" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#'
           'fff" stop-opacity=".22"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient></d'
           'efs><rect width="64" height="64" rx="15" fill="url(#gzip)"/><rect width="64" height="64" rx="15" fil'
           'l="url(#gziph)"/><rect x="15" y="22" width="34" height="27" rx="4" fill="#fff"/><path d="M13 18.5a3 '
           '3 0 0 1 3-3h32a3 3 0 0 1 3 3V23H13Z" fill="#fff" opacity=".85"/><path d="M32 22v4m0 4v4m0 4v4" strok'
           'e="#F28A00" stroke-width="3.4" stroke-linecap="round"/></svg>')
