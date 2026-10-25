"""아이콘(SVG), 화면 배율, 스타일시트 등 화면 꾸미기 관련 공통 코드"""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ACCENT = "#ff6f91"
TEXT = "#333333"
DISABLED = "#b8b8b8"

_scale = None


def scale():
    """윈도우 '디스플레이 배율'(100%, 125%, 150% ...)에 맞춘 크기 배율"""
    global _scale
    if _scale is None:
        s = QGuiApplication.primaryScreen()
        _scale = max(1.0, s.logicalDotsPerInch() / 96.0) if s else 1.0
    return _scale


def px(v):
    return int(round(v * scale()))


# 24x24 크기 기준으로 그린 선(stroke) 아이콘들
ICONS = {
    "cancel": '<circle cx="12" cy="12" r="9"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "region": '<path d="M19 11V5H5v14h6"/><path d="M17 14v7M13.5 17.5h7"/>',
    "window": '<rect x="4" y="4" width="16" height="16" rx="1"/><path d="M4 9h16"/>',
    "unit": '<rect x="4" y="4" width="6" height="16"/><rect x="14" y="4" width="6" height="6"/>'
            '<rect x="14" y="14" width="6" height="6"/>',
    "full": '<rect x="3" y="3" width="18" height="18" rx="1"/>'
            '<path d="M7 11V7h4M13 7h4v4M17 13v4h-4M11 17H7v-4"/>',
    "scroll": '<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M9 10l3-3 3 3M9 14l3 3 3-3"/>',
    "fixed": '<path d="M4 8V4h4M16 4h4v4M20 16v4h-4M8 20H4v-4"/><path d="M11 4h2M11 20h2M4 11v2M20 11v2"/>',
    "list": '<path d="M4 4v16M20 4v16"/><rect x="8" y="7" width="8" height="10"/>',
    "menu": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4.5 6h.01M4.5 12h.01M4.5 18h.01" stroke-width="3"/>',
    "newcap": '<path d="M6 2v16h16"/><path d="M2 6h16v16"/><path d="M12 9v6M9 12h6"/>',
    "save": '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    "copy": '<rect x="9" y="9" width="11" height="11"/><path d="M15 9V4H4v11h5"/>',
    "undo": '<path d="M9 14L4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
    "redo": '<path d="M15 14l5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h3"/>',
    "reset": '<path d="M20 11a8 8 0 0 0-14.9-3M4 13a8 8 0 0 0 14.9 3"/><path d="M4 3v5h5M20 21v-5h-5"/>',
    "shape": '<circle cx="9" cy="9" r="6"/><rect x="11" y="11" width="10" height="10" fill="white"/>',
    "rect": '<rect x="4" y="6" width="16" height="12"/>',
    "ellipse": '<ellipse cx="12" cy="12" rx="9" ry="7"/>',
    "line": '<path d="M5 19L19 5"/>',
    "arrow": '<path d="M5 19L19 5M10 5h9v9"/>',
    "pen": '<path d="M4 20l1-5L16 4l4 4L9 19z"/><path d="M14 6l4 4"/>',
    "highlighter": '<path d="M9 14l-4 4v2h6l2-2"/><path d="M9 14l7-10 5 4-8 10z"/>',
    "text": '<path d="M5 7V4h14v3M12 4v16M9 20h6"/>',
    "mosaic": '<rect x="4" y="4" width="16" height="16"/><path d="M4 9.3h16M4 14.6h16M9.3 4v16M14.6 4v16"/>',
    "crop": '<path d="M6 2v14a2 2 0 0 0 2 2h14"/><path d="M18 22V8a2 2 0 0 0-2-2H2"/>',
    "more": '<path d="M5 12h.01M12 12h.01M19 12h.01" stroke-width="3.2"/>',
    "print": '<path d="M7 9V3h10v6"/><rect x="3" y="9" width="18" height="8" rx="1"/><path d="M7 14h10v7H7z"/>',
    "folder": '<path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>',
    "open": '<rect x="3" y="4" width="18" height="16" rx="1"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3'
                'M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
    "sliders": '<path d="M3 7h8M15 7h6M3 17h4M11 17h10"/><circle cx="13" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
    "hotkey": '<rect x="4" y="4" width="16" height="16"/><path d="M9 15l6-6M10 9h5v5"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01" stroke-width="2.2"/>',
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>',
    "add": '<path d="M12 5v14M5 12h14"/>',
    "trash": '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
    "up": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "down": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "sort": '<path d="M7 4v16M3 16l4 4 4-4M14 6h7M14 12h5M14 18h3"/>',
    "home": '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    "merge": '<rect x="3" y="3" width="8" height="10" rx="1"/><rect x="13" y="3" width="8" height="10" rx="1"/><path d="M7 13v3h10v-3M12 16v5M9 19l3 2 3-2"/>',
    "split": '<rect x="7" y="3" width="10" height="8" rx="1"/><path d="M12 11v3M7 14h10M7 14v3M17 14v3"/><rect x="3" y="17" width="8" height="4" rx="1"/><rect x="13" y="17" width="8" height="4" rx="1"/>',
    "pages": '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="9" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "img2pdf": '<rect x="3" y="4" width="10" height="9" rx="1"/><circle cx="6.5" cy="7.5" r="1.2"/><path d="M13 11l-3-3-5 5"/><path d="M15 9h2l4 4v8H11v-5"/><path d="M14 17h4"/>',
    "pdf2img": '<path d="M4 3h7l3 3v9H4z"/><path d="M7 9h4M7 12h3"/><rect x="12" y="13" width="9" height="8" rx="1"/><path d="M21 19l-3-3-4 4"/>',
    "compress": '<path d="M6 3h8l4 4v14H6z"/><path d="M12 8v4M9.5 10.5L12 13l2.5-2.5M12 18v-3M9.5 15.5L12 13"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/><path d="M12 15v2"/>',
    "rotl": '<path d="M4 4v5h5"/><path d="M4.5 9A8 8 0 1 1 6 17"/>',
    "rotr": '<path d="M20 4v5h-5"/><path d="M19.5 9A8 8 0 1 0 18 17"/>',
    "zipnew": '<path d="M6 3h12v18H6z"/><path d="M11 3v2h2v2h-2v2h2v2h-2"/><rect x="10" y="13" width="4" height="4" rx="1"/>',
    "zipopen": '<path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M12 10v2h1v2h-1v2"/>',
    "extract": '<path d="M5 3h10l4 4v6"/><path d="M5 3v18h7"/><path d="M18 15v6M15 18l3 3 3-3"/>',
    "folderadd": '<path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M12 10v6M9 13h6"/>',
    "exit": '<path d="M10 4H5v16h5M15 8l4 4-4 4M19 12H9"/>',
}


def _render(svg, size):
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    renderer.render(p, QRectF(0, 0, size, size))
    p.end()
    return pm


def _svg(body, color, width=1.7):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
            f'stroke-linejoin="round">{body}</svg>')


def icon(name, color=TEXT):
    body = ICONS[name]
    if name == "cancel":
        color = "#e5484d"
    ic = QIcon()
    for size in (24, 48, 96):
        ic.addPixmap(_render(_svg(body, color), size), QIcon.Normal)
        ic.addPixmap(_render(_svg(body, DISABLED), size), QIcon.Disabled)
    return ic


APP_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
           '<rect width="64" height="64" rx="16" fill="#ff6f91"/>'
           '<path d="M7 41c0-15 11-25 25-25s25 10 25 25c0 9-10 12-25 12S7 50 7 41Z" fill="#fff"/>'
           '<circle cx="24" cy="38" r="3.2" fill="#3b2f2f"/><circle cx="40" cy="38" r="3.2" fill="#3b2f2f"/>'
           '<ellipse cx="17.5" cy="44" rx="4.2" ry="2.5" fill="#ffb3c6"/>'
           '<ellipse cx="46.5" cy="44" rx="4.2" ry="2.5" fill="#ffb3c6"/>'
           '<path d="M29 43q3 3.2 6 0" fill="none" stroke="#3b2f2f" stroke-width="2.3" stroke-linecap="round"/>'
           '<path d="M8 8h8M8 8v8M56 8h-8M56 8v8" stroke="#fff" stroke-width="3.5" stroke-linecap="round"/></svg>')

# 모찌 캐릭터 (광고·로그인 창 등에 사용)
MOCHI_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 100">'
             '<path d="M8 66C8 34 32 16 60 16s52 18 52 50c0 20-22 24-52 24S8 86 8 66Z" fill="#fff" '
             'stroke="#3b2f2f" stroke-width="4"/>'
             '<circle cx="44" cy="56" r="5" fill="#3b2f2f"/><circle cx="76" cy="56" r="5" fill="#3b2f2f"/>'
             '<ellipse cx="33" cy="67" rx="8" ry="4.5" fill="#ffb3c6"/>'
             '<ellipse cx="87" cy="67" rx="8" ry="4.5" fill="#ffb3c6"/>'
             '<path d="M54 64q6 6 12 0" fill="none" stroke="#3b2f2f" stroke-width="3.4" stroke-linecap="round"/></svg>')


def mochi_pixmap(width):
    """모찌 캐릭터 그림 (가로 width 픽셀)"""
    h = int(width * 100 / 120)
    renderer = QSvgRenderer(QByteArray(MOCHI_SVG.encode("utf-8")))
    pm = QPixmap(width, h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    renderer.render(p, QRectF(0, 0, width, h))
    p.end()
    return pm


def app_icon():
    """프로그램 아이콘. 각 프로그램의 brand.py 에 APP_SVG 가 있으면 그것을 쓴다."""
    try:
        import brand
        svg = getattr(brand, "APP_SVG", None) or APP_SVG
    except ImportError:
        svg = APP_SVG
    ic = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        ic.addPixmap(_render(svg, size))
    return ic


def color_icon(color, size=18):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.gray)
    p.setBrush(color)
    p.drawEllipse(1, 1, size - 2, size - 2)
    p.end()
    return QIcon(pm)


def stylesheet():
    return f"""
    * {{ font-family: 'Malgun Gothic', '맑은 고딕', 'Segoe UI', sans-serif; font-size: 10pt; color: {TEXT}; }}
    QWidget#launcher, QWidget#toolbar, QWidget#historyPanel, QWidget#optionBar {{ background: #ffffff; }}
    QWidget#toolbar {{ border-bottom: 1px solid #e3e5ea; }}
    QWidget#optionBar {{ border-bottom: 1px solid #e3e5ea; }}
    QWidget#historyPanel {{ border-left: 1px solid #e3e5ea; }}
    QToolButton[role="big"] {{
        border: none; border-radius: 6px; background: transparent;
        padding: {px(6)}px {px(8)}px; min-width: {px(62)}px; font-size: 10.5pt; color: #555;
    }}
    QToolButton[role="big"]:hover {{ background: #fff0f4; }}
    QToolButton[role="big"]:checked {{ background: #ffe3eb; color: {ACCENT}; }}
    QToolButton[role="big"]:disabled {{ color: {DISABLED}; }}
    QToolButton[role="big"]::menu-button {{ border: none; background: transparent; width: {px(14)}px; }}
    QToolButton[role="big"]::menu-button:hover {{ background: #ffd3de; border-radius: 4px; }}
    QListWidget#historyList::item:selected:!active {{ border: 3px solid {ACCENT}; background: transparent; }}
    QToolButton[role="launch"] {{
        border: none; border-radius: 5px; background: transparent;
        padding: {px(8)}px {px(4)}px {px(6)}px {px(4)}px; min-width: {px(58)}px; font-size: 9.5pt; color: #555;
    }}
    QToolButton[role="launch"]:hover {{ background: #fff0f4; }}
    QToolButton[role="launch"]:checked {{ background: #ffe3eb; color: {ACCENT}; }}
    QToolButton[role="launch"]::menu-indicator {{ image: none; width: 0; }}
    QToolButton[role="big"]::menu-indicator {{ subcontrol-position: bottom center; subcontrol-origin: padding; bottom: -2px; }}
    QFrame#vsep {{ background: #e3e5ea; min-width: 1px; max-width: 1px; }}
    QScrollArea#canvasArea {{ background: #e8ebf2; border: none; }}
    QScrollArea#canvasArea > QWidget > QWidget {{ background: #e8ebf2; }}
    QLabel#panelTitle {{ font-size: 12.5pt; }}
    QLabel#panelCount {{ color: #888; }}
    QPushButton[role="link"] {{ border: none; color: {ACCENT}; font-size: 11pt; padding: 6px; background: transparent; }}
    QPushButton[role="link"]:hover {{ text-decoration: underline; }}
    QListWidget#historyList {{ border: none; background: #ffffff; outline: 0; }}
    QListWidget#historyList::item {{ border: 2px solid transparent; margin: 4px; }}
    QListWidget#historyList::item:selected {{ border: 3px solid {ACCENT}; background: transparent; }}
    QStatusBar {{ background: #f6f7f9; border-top: 1px solid #e3e5ea; }}
    QPushButton#primary {{ background: {ACCENT}; color: white; border: none; border-radius: 4px; padding: 5px 14px; }}
    QPushButton#primary:hover {{ background: #e8557a; }}
    QFrame#fixedBar {{ background: #ffffff; border: 1px solid #c9d3e3; border-radius: 6px; }}
    QMenu {{ background: white; border: 1px solid #d9dce3; padding: 4px; }}
    QMenu::item {{ padding: 6px 24px 6px 12px; }}
    QMenu::item:selected {{ background: #fff0f4; color: {ACCENT}; }}
    """
