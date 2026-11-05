"""모찌LAB. 브랜드 디자인 원본 — 색 · 로고 · 제품 아이콘을 여기서 한 번에 정하고 모든 곳에 뽑아낸다.

사용법 (저장소 맨 위에서):  python brand/make_brand.py
만드는 것:
  web/public/img/favicon.svg, mochi.svg, apps/<제품>.svg     (홈페이지)
  artcraft_kit/icons/<photo|vector|hwp>.svg/-1024.png/.ico (모찌포토 · 벡터 · 한글 설치파일 아이콘)
  mochi_<capture|pdf|zip>/assets/app.png/.ico               (모찌캡처 · PDF · 압축 아이콘)
색을 바꾸려면 아래 COLORS / APPS 만 고치고 다시 실행하면 된다.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- 색
COLORS = {
    "brand": "#4F5BFF",        # 기본 색 (인디고 블루)
    "brand_dark": "#3D48E6",   # 누를 때
    "brand_soft": "#EEF0FF",   # 옅은 배경
    "brand_light": "#E0E4FF",  # 선택된 배경
    "brand_line": "#C9CFFF",   # 옅은 테두리
    "ink": "#0F172A",          # 글자 (남색에 가까운 검정)
    "ink_2": "#475569",
    "ink_3": "#94A3B8",
    "line": "#E2E8F0",
    "surface": "#F6F7FB",      # 옅은 회색 배경
}

# 제품별: (그라데이션 시작, 끝, 흰색 그림)
APPS = {
    "capture": ("#6A75FF", "#3F46E0",
                # 캡처 프레임 네 귀퉁이 + 가운데 점
                '<path d="M18 27v-6a3 3 0 0 1 3-3h6M37 18h6a3 3 0 0 1 3 3v6M46 37v6a3 3 0 0 1-3 3h-6M27 46h-6a3 3 0 0 1-3-3v-6" '
                'fill="none" stroke="#fff" stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round"/>'
                '<circle cx="32" cy="32" r="5.2" fill="#fff"/>'),
    "pdf": ("#FF6B5B", "#E2352B",
            # 문서 + PDF 글자
            '<path d="M22 13h13.5L46 23.5V48a3 3 0 0 1-3 3H22a3 3 0 0 1-3-3V16a3 3 0 0 1 3-3Z" fill="#fff"/>'
            '<path d="M35 13v8.5a2 2 0 0 0 2 2H46" fill="none" stroke="#F5A49C" stroke-width="2.4" stroke-linejoin="round"/>'
            '<text x="32.5" y="43" font-family="Arial, Helvetica, sans-serif" font-weight="900" font-size="10.5" '
            'fill="#E2352B" text-anchor="middle">PDF</text>'),
    "zip": ("#FFBE2E", "#F28A00",
            # 상자 + 지퍼
            '<rect x="15" y="22" width="34" height="27" rx="4" fill="#fff"/>'
            '<path d="M13 18.5a3 3 0 0 1 3-3h32a3 3 0 0 1 3 3V23H13Z" fill="#fff" opacity=".85"/>'
            '<path d="M32 22v4m0 4v4m0 4v4" stroke="#F28A00" stroke-width="3.4" stroke-linecap="round"/>'),
    "photo": ("#2FC8F2", "#1477E0",
              # 사진 액자 + 산 + 해
              '<rect x="13" y="17" width="38" height="30" rx="5" fill="none" stroke="#fff" stroke-width="4.4"/>'
              '<path d="M17 43l9.5-10.5 7 7 4.5-4.5 9 8" fill="none" stroke="#fff" stroke-width="4.2" '
              'stroke-linecap="round" stroke-linejoin="round"/>'
              '<circle cx="40.5" cy="26.5" r="3.6" fill="#fff"/>'),
    "vector": ("#A374FF", "#6A35EA",
               # 펜촉 + 베지어 곡선 고정점
               '<path d="M32 12l11 19-7 15h-8l-7-15Z" fill="#fff"/>'
               '<path d="M32 22v11" stroke="#6A35EA" stroke-width="3" stroke-linecap="round"/>'
               '<circle cx="32" cy="35" r="2.6" fill="#6A35EA"/>'
               '<rect x="27" y="47" width="10" height="5" rx="1.5" fill="#fff"/>'),
    "hwp": ("#4C8DFF", "#2356D8",
            # 문서 + '한'
            '<rect x="16" y="12" width="32" height="40" rx="5" fill="#fff"/>'
            '<text x="32" y="41.5" font-family="\'Malgun Gothic\', \'NanumSquareRound\', \'Apple SD Gothic Neo\', sans-serif" '
            'font-weight="900" font-size="22" fill="#2356D8" text-anchor="middle">한</text>'),
}


def squircle(c1, c2, body, gid):
    """요즘 앱 아이콘 모양: 둥근 사각형 + 대각선 그라데이션 + 위쪽 은은한 빛"""
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient>'
            f'<linearGradient id="{gid}h" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/>'
            '<stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'
            f'<rect width="64" height="64" rx="15" fill="url(#{gid})"/>'
            f'<rect width="64" height="64" rx="15" fill="url(#{gid}h)"/>'
            f'{body}</svg>')


def app_svg(slug):
    c1, c2, body = APPS[slug]
    return squircle(c1, c2, body, "g" + slug)


# 브랜드 로고: 남색 사각형 안의 하얀 모찌 (눈만 있는 단순한 얼굴) + 인디고 점 (LAB. 의 점)
LOGO_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">'
            '<stop offset="0" stop-color="#1E293B"/><stop offset="1" stop-color="#0B1220"/></linearGradient></defs>'
            '<rect width="64" height="64" rx="15" fill="url(#lg)"/>'
            '<path d="M10 40.5C10 27 19.5 18 32 18s22 9 22 22.5c0 8-9 10.5-22 10.5S10 48.5 10 40.5Z" fill="#fff"/>'
            '<rect x="23" y="33" width="4.6" height="7" rx="2.3" fill="#0F172A"/>'
            '<rect x="36.4" y="33" width="4.6" height="7" rx="2.3" fill="#0F172A"/>'
            f'<circle cx="52" cy="13" r="4.5" fill="{COLORS["brand"]}"/></svg>')

# 모찌 캐릭터 (홈페이지 · 프로그램의 로그인 창 · 광고 등): 볼 · 입 없이 눈만, 남색 테두리
MOCHI_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 100">'
             '<path d="M8 66C8 34 32 16 60 16s52 18 52 50c0 20-22 24-52 24S8 86 8 66Z" fill="#fff" '
             'stroke="#0F172A" stroke-width="4"/>'
             '<rect x="40" y="50" width="8" height="13" rx="4" fill="#0F172A"/>'
             '<rect x="72" y="50" width="8" height="13" rx="4" fill="#0F172A"/>'
             f'<circle cx="104" cy="22" r="7" fill="{COLORS["brand"]}"/></svg>')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def render(svg, size):
    """SVG → PNG (Qt 로 그림: 한글 글꼴도 그대로 나온다)"""
    from PySide6.QtCore import QByteArray, QRectF, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(p, QRectF(0, 0, size, size))
    p.end()
    import io
    from PIL import Image
    from PySide6.QtCore import QBuffer, QIODevice
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841 (글꼴을 쓰려면 필요)
    web = os.path.join(ROOT, "web", "public", "img")
    write(os.path.join(web, "favicon.svg"), LOGO_SVG)
    write(os.path.join(web, "mochi.svg"), MOCHI_SVG)
    for slug in APPS:
        write(os.path.join(web, "apps", f"{slug}.svg"), app_svg(slug))
    for slug in ("photo", "vector", "hwp"):
        d = os.path.join(ROOT, "artcraft_kit", "icons")
        write(os.path.join(d, f"{slug}.svg"), app_svg(slug))
        big = render(app_svg(slug), 1024)
        big.save(os.path.join(d, f"{slug}-1024.png"))
        render(app_svg(slug), 256).save(os.path.join(d, f"{slug}.ico"), sizes=ICO_SIZES)
    for slug in ("capture", "pdf", "zip"):
        d = os.path.join(ROOT, f"mochi_{slug}", "assets")
        img = render(app_svg(slug), 256)
        img.save(os.path.join(d, "app.png"))
        img.save(os.path.join(d, "app.ico"), sizes=ICO_SIZES)
    print("모찌LAB. 브랜드 파일을 모두 다시 만들었어요.")


if __name__ == "__main__":
    main()
