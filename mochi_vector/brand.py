"""모찌벡터 브랜드 정보"""
import os

BRAND_NAME = "모찌랩"
BRAND_NAME_EN = "MozziLab"
APP_NAME = "모찌벡터"
APP_ID = "MochiVector"
APP_SLUG = "vector"               # 서버에 등록된 제품 코드
APP_VERSION = "1.1.0"
SERVER_URL = os.environ.get("MOCHI_SERVER", "https://mozzilab.labelpos.com").rstrip("/")

# 프로그램 아이콘 (하늘색 모찌 + VECTOR)
APP_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
           '<rect width="64" height="64" rx="16" fill="#2f9be8"/>'
           '<path d="M7 41c0-15 11-25 25-25s25 10 25 25c0 9-10 12-25 12S7 50 7 41Z" fill="#fff"/>'
           '<circle cx="24" cy="38" r="3.2" fill="#3b2f2f"/><circle cx="40" cy="38" r="3.2" fill="#3b2f2f"/>'
           '<ellipse cx="17.5" cy="44" rx="4.2" ry="2.5" fill="#ffb3c6"/>'
           '<ellipse cx="46.5" cy="44" rx="4.2" ry="2.5" fill="#ffb3c6"/>'
           '<path d="M29 43q3 3.2 6 0" fill="none" stroke="#3b2f2f" stroke-width="2.3" stroke-linecap="round"/>'
           '<text x="32" y="14" font-family="Arial" font-weight="bold" font-size="9" fill="#fff" text-anchor="middle">VECTOR</text></svg>')
