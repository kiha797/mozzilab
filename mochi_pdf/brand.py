"""모찌PDF 브랜드 정보"""
import os

BRAND_NAME = "모찌LAB."
BRAND_NAME_EN = "MozziLab"
APP_NAME = "모찌PDF"
APP_ID = "MochiPDF"
APP_SLUG = "pdf"               # 서버에 등록된 제품 코드
APP_VERSION = "1.0.0"
SERVER_URL = os.environ.get("MOCHI_SERVER", "https://mozzilab.labelpos.com").rstrip("/")

# 프로그램 아이콘 (민트색 모찌 + PDF)
APP_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs><linearGradient id="gpdf" x1="0" y'
           '1="0" x2="1" y2="1"><stop offset="0" stop-color="#FF6B5B"/><stop offset="1" stop-color="#E2352B"/></'
           'linearGradient><linearGradient id="gpdfh" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#'
           'fff" stop-opacity=".22"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient></d'
           'efs><rect width="64" height="64" rx="15" fill="url(#gpdf)"/><rect width="64" height="64" rx="15" fil'
           'l="url(#gpdfh)"/><path d="M22 13h13.5L46 23.5V48a3 3 0 0 1-3 3H22a3 3 0 0 1-3-3V16a3 3 0 0 1 3-3Z" f'
           'ill="#fff"/><path d="M35 13v8.5a2 2 0 0 0 2 2H46" fill="none" stroke="#F5A49C" stroke-width="2.4" st'
           'roke-linejoin="round"/><text x="32.5" y="43" font-family="Arial, Helvetica, sans-serif" font-weight='
           '"900" font-size="10.5" fill="#E2352B" text-anchor="middle">PDF</text></svg>')
