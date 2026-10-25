"""모찌포토 · 모찌벡터가 함께 쓰는 '편집 프로그램' 부품
- 포토샵/일러스트처럼 어두운 작업 화면 스타일
- 왼쪽 도구 상자(ToolPalette), 색 버튼(ColorButton), 숫자 슬라이더(SliderSpin)
- 패널(Panel), 새 문서 창(NewDocDialog), 시작 화면(StartPage)"""
import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QSlider, QSpinBox, QToolButton,
                               QVBoxLayout, QWidget)

import ui
from ui import ACCENT, px

# ---------- 편집 도구 아이콘 (24x24 선 아이콘) ----------
ui.ICONS.update({
    "move": '<path d="M12 3v18M3 12h18M12 3l-3 3M12 3l3 3M12 21l-3-3M12 21l3-3M3 12l3-3M3 12l3 3M21 12l-3-3M21 12l-3 3"/>',
    "marquee": '<path d="M4 7V4h3M10 4h4M17 4h3v3M20 10v4M20 17v3h-3M14 20h-4M7 20H4v-3M4 14v-4"/>',
    "ellipsesel": '<path d="M12 4a8 8 0 0 1 8 8M20 12a8 8 0 0 1-8 8M12 20a8 8 0 0 1-8-8M4 12a8 8 0 0 1 8-8" stroke-dasharray="3 2.4"/>',
    "lasso": '<path d="M7 17c-3-1.5-4-4-3-6.5C5.5 6 12 4 17 5.5s4.5 6 1 8.5-8 3-11 3z"/><path d="M7 17c-1 2 0 4 2 4"/>',
    "wand": '<path d="M4 20L15 9"/><path d="M15 9l2-2"/><path d="M18 2v3M21 5h-3M19.5 8.5l-1.5-1.5M14 4.5L15.5 6"/>',
    "brush": '<path d="M18.5 3.5l2 2-9 9-2-2z"/><path d="M9.5 12.5c-2 0-3.5 1.5-3.5 3.5 0 1.5-1 2.5-2.5 3 3 1.5 8 1 8.5-3.5"/>',
    "pencil": '<path d="M4 20l1-4L16 5l3 3L8 19z"/><path d="M5 16l3 3"/>',
    "eraser": '<path d="M8 20h12"/><path d="M4 15l9-10 7 7-8 8H8z"/><path d="M9 10l6 6"/>',
    "bucket": '<path d="M5 11l7-7 7 7-7 7z"/><path d="M5 11h14"/><path d="M20 15s2 2.5 2 4a2 2 0 0 1-4 0c0-1.5 2-4 2-4z"/>',
    "gradient": '<rect x="3" y="5" width="18" height="14" rx="1"/><path d="M7 5v14M11 5v14" stroke-dasharray="1.5 2"/>',
    "eyedrop": '<path d="M14 7l3 3"/><path d="M15 4a2.1 2.1 0 0 1 3 0l2 2a2.1 2.1 0 0 1 0 3l-2 2-5-5z"/><path d="M13 8l-8 8v3h3l8-8"/>',
    "stamp": '<path d="M9 13V9a3 3 0 1 1 6 0v4"/><path d="M4 13h16v4H4z"/><path d="M6 20h12"/>',
    "hand": '<path d="M8 13V5.5a1.5 1.5 0 0 1 3 0V11M11 10V4.5a1.5 1.5 0 0 1 3 0V11M14 10.5V6a1.5 1.5 0 0 1 3 0v7"/><path d="M17 11.5a1.5 1.5 0 0 1 3 0V15a7 7 0 0 1-7 7h-1c-2.5 0-4-1-5.5-3L4 15.5a1.5 1.5 0 0 1 2.3-2L8 15"/>',
    "zoom": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5L21 21M10.5 7.5v6M7.5 10.5h6"/>',
    "select": '<path d="M5 3l14 8-6 1.5L10 19z" fill="#333"/>',
    "direct": '<path d="M5 3l14 8-6 1.5L10 19z"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.8-4.5 4.2 1.1 6.1L12 16.8 6.6 19.7l1.1-6.1L3.2 9.4l6.1-.8z"/>',
    "polygon": '<path d="M12 3l8.5 6.2-3.2 10H6.7L3.5 9.2z"/>',
    "roundrect": '<rect x="3" y="6" width="18" height="12" rx="4"/>',
    "penpath": '<path d="M12 21v-4M8 13l4-10 4 10-4 4z"/><circle cx="12" cy="11" r="1.2"/><path d="M4 21h16"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="1"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/>',
    "group": '<rect x="3" y="3" width="18" height="18" rx="1" stroke-dasharray="2 2"/><rect x="6" y="6" width="6" height="6"/><rect x="12" y="12" width="6" height="6"/>',
    "ungroup": '<rect x="3" y="3" width="8" height="8"/><rect x="13" y="13" width="8" height="8"/>',
    "front": '<rect x="9" y="9" width="12" height="12" fill="#ff6f91" stroke="#ff6f91"/><path d="M3 15V3h12"/>',
    "back": '<rect x="9" y="9" width="12" height="12"/><path d="M3 15V3h12v6" /><rect x="3" y="3" width="12" height="12" fill="#ff6f91" stroke="#ff6f91" opacity=".35"/>',
    "alignl": '<path d="M4 3v18"/><rect x="7" y="6" width="12" height="4"/><rect x="7" y="14" width="7" height="4"/>',
    "alignc": '<path d="M12 3v18"/><rect x="5" y="6" width="14" height="4"/><rect x="8" y="14" width="8" height="4"/>',
    "alignr": '<path d="M20 3v18"/><rect x="5" y="6" width="12" height="4"/><rect x="10" y="14" width="7" height="4"/>',
    "alignt": '<path d="M3 4h18"/><rect x="6" y="7" width="4" height="12"/><rect x="14" y="7" width="4" height="7"/>',
    "alignm": '<path d="M3 12h18"/><rect x="6" y="5" width="4" height="14"/><rect x="14" y="8" width="4" height="8"/>',
    "alignb": '<path d="M3 20h18"/><rect x="6" y="5" width="4" height="12"/><rect x="14" y="10" width="4" height="7"/>',
    "disth": '<path d="M3 4v16M21 4v16"/><rect x="9" y="7" width="6" height="10"/>',
    "distv": '<path d="M4 3h16M4 21h16"/><rect x="7" y="9" width="10" height="6"/>',
    "union": '<path d="M4 4h10v6h6v10H10v-6H4z" fill="#ff6f91" fill-opacity=".35"/>',
    "subtract": '<path d="M4 4h10v6h-4v4H4z" fill="#ff6f91" fill-opacity=".35"/><path d="M10 10h10v10H10z" stroke-dasharray="2 2"/>',
    "intersect": '<path d="M4 4h10v10H4zM10 10h10v10H10z" stroke-dasharray="2 2"/><path d="M10 10h4v4h-4z" fill="#ff6f91" stroke="#ff6f91"/>',
    "exclude": '<path d="M4 4h10v6h-4v4H4zM14 10h6v10H10v-6h4z" fill="#ff6f91" fill-opacity=".35"/>',
    "fliph": '<path d="M12 3v18" stroke-dasharray="2 2"/><path d="M9 7L3 17h6zM15 7l6 10h-6z"/>',
    "flipv": '<path d="M3 12h18" stroke-dasharray="2 2"/><path d="M7 9L17 3v6zM7 15l10 6v-6z"/>',
    "duplicate": '<rect x="8" y="8" width="12" height="12" rx="1"/><path d="M16 8V4H4v12h4M14 11v6M11 14h6"/>',
    "export": '<path d="M12 15V3M7 8l5-5 5 5"/><path d="M5 13v7h14v-7"/>',
    "newdoc": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M12 11v6M9 14h6"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "adjust": '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18z" fill="#333"/>',
    "filter": '<path d="M4 4h16l-6 8v6l-4 2v-8z"/>',
    "resize": '<path d="M4 14v6h6M20 10V4h-6M4 20l7-7M20 4l-7 7"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
})


def editor_qss():
    """편집 화면(작업 영역 · 패널)을 포토샵처럼 어두운 회색으로"""
    return f"""
    QWidget#editor, QWidget#editor QWidget {{ color: #e8e6ea; }}
    QWidget#editor {{ background: #2b2a2e; }}
    QWidget#toolbox, QWidget#optbar, QWidget#sidebar {{ background: #3a393e; }}
    QWidget#optbar {{ border-bottom: 1px solid #222; }}
    QWidget#toolbox {{ border-right: 1px solid #222; }}
    QWidget#sidebar {{ border-left: 1px solid #222; }}
    QFrame#panel {{ background: #3a393e; border-bottom: 1px solid #262529; }}
    QLabel#panelHead {{ color: #bdb9c2; font-weight: bold; font-size: 9pt; padding: 2px 0; }}
    QWidget#editor QLabel {{ background: transparent; }}
    QToolButton[role="tool"] {{ border: none; border-radius: 4px; background: transparent; padding: 3px; }}
    QToolButton[role="tool"]:hover {{ background: #4a4950; }}
    QToolButton[role="tool"]:checked {{ background: #5b4650; border: 1px solid {ACCENT}; }}
    QToolButton[role="mini"] {{ border: none; border-radius: 3px; background: transparent; padding: 2px; }}
    QToolButton[role="mini"]:hover {{ background: #4a4950; }}
    QToolButton[role="mini"]:checked {{ background: #5b4650; }}
    QWidget#editor QSpinBox, QWidget#editor QDoubleSpinBox, QWidget#editor QComboBox,
    QWidget#editor QLineEdit, QWidget#editor QFontComboBox {{
        background: #26252a; border: 1px solid #55535a; border-radius: 3px; padding: 2px 4px;
        color: #f0eef2; selection-background-color: {ACCENT};
    }}
    QWidget#editor QComboBox QAbstractItemView {{ background: #2e2d32; color: #eee; selection-background-color: {ACCENT}; }}
    QWidget#editor QPushButton {{ background: #4a4950; border: 1px solid #5c5a62; border-radius: 3px; padding: 3px 10px; }}
    QWidget#editor QPushButton:hover {{ background: #56545c; }}
    QWidget#editor QPushButton:checked {{ background: #5b4650; border-color: {ACCENT}; }}
    QWidget#editor QCheckBox {{ spacing: 5px; }}
    QWidget#editor QListWidget {{ background: #2e2d32; border: 1px solid #222; outline: 0; }}
    QWidget#editor QListWidget::item {{ padding: 3px; border-bottom: 1px solid #38373c; }}
    QWidget#editor QListWidget::item:selected {{ background: #5b4650; color: white; }}
    QWidget#editor QSlider::groove:horizontal {{ height: 4px; background: #222; border-radius: 2px; }}
    QWidget#editor QSlider::handle:horizontal {{ width: 12px; margin: -5px 0; border-radius: 6px; background: #ddd; }}
    QWidget#editor QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
    QWidget#editor QScrollBar {{ background: #2b2a2e; }}
    QWidget#editor QTabBar::tab {{ background: #333237; color: #bbb; padding: 5px 14px; border: none; }}
    QWidget#editor QTabBar::tab:selected {{ background: #45444a; color: white; border-bottom: 2px solid {ACCENT}; }}
    QWidget#editor QFrame#vsep2 {{ background: #55535a; min-width: 1px; max-width: 1px; }}
    """


def mini_button(icon_name, tip, slot=None, checkable=False, size=18):
    b = QToolButton()
    b.setProperty("role", "mini")
    b.setIcon(ui.icon(icon_name, "#e8e6ea"))
    b.setIconSize(QSize(px(size), px(size)))
    b.setToolTip(tip)
    b.setCheckable(checkable)
    b.setCursor(Qt.PointingHandCursor)
    if slot:
        b.clicked.connect(slot)
    return b


def vsep():
    s = QFrame()
    s.setObjectName("vsep2")
    s.setFixedHeight(px(20))
    return s


class ToolPalette(QWidget):
    """왼쪽 세로 도구 상자. tools = [(키, 이름, 아이콘, 단축키), ...] / None 은 구분선"""
    changed = Signal(str)

    def __init__(self, tools, columns=2):
        super().__init__()
        self.setObjectName("toolbox")
        self.setAttribute(Qt.WA_StyledBackground)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}
        self.shortcuts = {}
        v = QVBoxLayout(self)
        v.setContentsMargins(px(4), px(6), px(4), px(6))
        v.setSpacing(px(2))
        grid = QGridLayout()
        grid.setSpacing(px(2))
        r = c = 0
        for t in tools:
            if t is None:
                if c:
                    r += 1
                    c = 0
                line = QFrame()
                line.setFixedHeight(1)
                line.setStyleSheet("background:#55535a;")
                grid.addWidget(line, r, 0, 1, columns)
                r += 1
                continue
            key, name, ic, sc = t
            b = QToolButton()
            b.setProperty("role", "tool")
            b.setCheckable(True)
            b.setIcon(ui.icon(ic, "#ecebef"))
            b.setIconSize(QSize(px(22), px(22)))
            b.setToolTip(f"{name}  ({sc})" if sc else name)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            self.group.addButton(b)
            self.buttons[key] = b
            if sc:
                self.shortcuts.setdefault(sc.upper(), []).append(key)
            grid.addWidget(b, r, c)
            c += 1
            if c >= columns:
                c = 0
                r += 1
        v.addLayout(grid)
        v.addStretch(1)
        self.extra = v       # 아래쪽에 색 버튼 등을 붙일 자리

    def select(self, key):
        if key in self.buttons:
            self.buttons[key].setChecked(True)

    def tool_for_key(self, letter, current):
        """단축키 글자를 누르면 해당 도구 (같은 글자 도구가 여럿이면 차례로 바꾼다)"""
        keys = self.shortcuts.get(letter.upper())
        if not keys:
            return None
        if current in keys:
            return keys[(keys.index(current) + 1) % len(keys)]
        return keys[0]


def checker_brush_pixmap(cell=8):
    pm = QPixmap(cell * 2, cell * 2)
    pm.fill(QColor("#ffffff"))
    p = QPainter(pm)
    p.fillRect(0, 0, cell, cell, QColor("#d9d9d9"))
    p.fillRect(cell, cell, cell, cell, QColor("#d9d9d9"))
    p.end()
    return pm


class ColorButton(QToolButton):
    """눌러서 색을 고르는 네모 버튼 (none_ok=True 면 '없음' 가능)"""
    colorChanged = Signal(object)

    def __init__(self, color="#000000", none_ok=False, size=26, tip="색 고르기"):
        super().__init__()
        self.none_ok = none_ok
        self._color = None if color is None else QColor(color)
        self.setFixedSize(px(size), px(size))
        self.setToolTip(tip)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self.pick)
        self.setStyleSheet("QToolButton { border: 1px solid #111; border-radius: 3px; background: transparent; }")

    def color(self):
        return self._color

    def set_color(self, c, emit=False):
        self._color = None if c is None else QColor(c)
        self.update()
        if emit:
            self.colorChanged.emit(self._color)

    def pick(self):
        dlg = QColorDialog(self._color or QColor("#000000"), self.window())
        dlg.setOption(QColorDialog.ShowAlphaChannel, True)
        dlg.setWindowTitle("색 고르기")
        if self.none_ok:
            none = QPushButton("색 없음")
            dlg.layout().addWidget(none)
            none.clicked.connect(lambda: (dlg.done(2)))
        r = dlg.exec()
        if r == 2:
            self.set_color(None, emit=True)
        elif r == QDialog.Accepted:
            self.set_color(dlg.currentColor(), emit=True)

    def paintEvent(self, e):
        p = QPainter(self)
        r = self.rect().adjusted(2, 2, -2, -2)
        p.drawTiledPixmap(r, checker_brush_pixmap(4))
        if self._color is None:
            p.fillRect(r, Qt.white)
            p.setPen(QColor("#e5484d"))
            p.drawLine(r.bottomLeft(), r.topRight())
        else:
            p.fillRect(r, self._color)
        p.setPen(QColor("#111"))
        p.drawRect(r.adjusted(0, 0, -1, -1))
        p.end()


class SliderSpin(QWidget):
    """이름 + 슬라이더 + 숫자칸 (값이 함께 움직인다)"""
    valueChanged = Signal(int)

    def __init__(self, label, lo, hi, value, suffix="", slider_width=90):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(px(4))
        if label:
            h.addWidget(QLabel(label))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(lo, hi)
        self.slider.setFixedWidth(px(slider_width))
        self.spin = QSpinBox()
        self.spin.setRange(lo, hi)
        self.spin.setSuffix(suffix)
        self.spin.setFixedWidth(px(64))
        self.slider.setValue(value)
        self.spin.setValue(value)
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        self.spin.valueChanged.connect(self.valueChanged)
        h.addWidget(self.slider)
        h.addWidget(self.spin)

    def value(self):
        return self.spin.value()

    def setValue(self, v):
        self.spin.setValue(int(v))


class Panel(QFrame):
    """오른쪽 패널 한 칸 (제목 + 내용)"""

    def __init__(self, title, widget=None, stretch=False):
        super().__init__()
        self.setObjectName("panel")
        v = QVBoxLayout(self)
        v.setContentsMargins(px(8), px(6), px(8), px(8))
        v.setSpacing(px(4))
        head = QLabel(title.upper())
        head.setObjectName("panelHead")
        v.addWidget(head)
        self.body = v
        if widget is not None:
            v.addWidget(widget, 1 if stretch else 0)


# ---------- 새 문서 ----------
PHOTO_PRESETS = [
    ("직접 입력", 0, 0),
    ("FHD 1920×1080", 1920, 1080),
    ("HD 1280×720", 1280, 720),
    ("4K 3840×2160", 3840, 2160),
    ("인스타그램 1080×1080", 1080, 1080),
    ("인스타 세로 1080×1350", 1080, 1350),
    ("유튜브 썸네일 1280×720", 1280, 720),
    ("A4 (300dpi) 2480×3508", 2480, 3508),
    ("A4 (150dpi) 1240×1754", 1240, 1754),
    ("명함 1050×600", 1050, 600),
    ("웹 배너 728×90", 728, 90),
]
VECTOR_PRESETS = [
    ("직접 입력", 0, 0),
    ("A4 세로 (595×842 pt)", 595, 842),
    ("A4 가로 (842×595 pt)", 842, 595),
    ("A3 세로 (842×1191 pt)", 842, 1191),
    ("명함 (255×156 pt)", 255, 156),
    ("FHD 1920×1080", 1920, 1080),
    ("인스타그램 1080×1080", 1080, 1080),
    ("로고 512×512", 512, 512),
    ("아이콘 128×128", 128, 128),
]


class NewDocDialog(QDialog):
    def __init__(self, parent, presets, w=1920, h=1080, with_background=True, title="새로 만들기"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.presets = presets
        f = QFormLayout(self)
        self.preset = QComboBox()
        for name, *_ in presets:
            self.preset.addItem(name)
        self.preset.currentIndexChanged.connect(self._preset)
        self.w = QSpinBox()
        self.w.setRange(1, 20000)
        self.w.setValue(w)
        self.h = QSpinBox()
        self.h.setRange(1, 20000)
        self.h.setValue(h)
        self.w.setSuffix(" px")
        self.h.setSuffix(" px")
        f.addRow("크기 고르기", self.preset)
        f.addRow("가로", self.w)
        f.addRow("세로", self.h)
        self.bg = QComboBox()
        self.bg.addItems(["흰색", "투명", "검정"])
        if with_background:
            f.addRow("배경", self.bg)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("만들기")
        bb.button(QDialogButtonBox.Cancel).setText("취소")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)

    def _preset(self, i):
        _, w, h = self.presets[i]
        if w:
            self.w.setValue(w)
            self.h.setValue(h)

    def values(self):
        bg = {0: QColor("white"), 1: None, 2: QColor("black")}[self.bg.currentIndex()]
        return self.w.value(), self.h.value(), bg


class StartPage(QWidget):
    """프로그램을 켰을 때 나오는 시작 화면 (새로 만들기 · 열기 · 최근 파일)"""
    newRequested = Signal(int, int)
    openRequested = Signal()
    recentRequested = Signal(str)

    def __init__(self, app_name, tagline, presets, color):
        super().__init__()
        self.setStyleSheet("background:#fbf8f6;")
        root = QHBoxLayout(self)
        root.setContentsMargins(px(48), px(36), px(48), px(36))
        root.setSpacing(px(40))
        left = QVBoxLayout()
        left.setSpacing(px(10))
        t = QLabel(f"<span style='font-size:24pt; font-weight:bold; color:{color}'>{app_name}</span>"
                   f"<br><span style='color:#7a6f72; font-size:11pt'>{tagline}</span>")
        left.addWidget(t)
        left.addSpacing(px(10))
        new = QPushButton("  새로 만들기")
        new.setIcon(ui.icon("newdoc", "white"))
        new.setIconSize(QSize(px(22), px(22)))
        new.setObjectName("primary")
        new.setMinimumHeight(px(42))
        new.setCursor(Qt.PointingHandCursor)
        new.setStyleSheet(f"QPushButton {{ background:{color}; color:white; border:none; border-radius:8px;"
                          " font-size:12pt; font-weight:bold; padding:0 18px; }")
        new.clicked.connect(lambda: self.newRequested.emit(0, 0))
        op = QPushButton("  파일 열기")
        op.setIcon(ui.icon("folder"))
        op.setIconSize(QSize(px(22), px(22)))
        op.setMinimumHeight(px(42))
        op.setCursor(Qt.PointingHandCursor)
        op.setStyleSheet("QPushButton { background:white; border:1px solid #e3dcd8; border-radius:8px;"
                         " font-size:12pt; padding:0 18px; } QPushButton:hover { background:#fff3f6; }")
        op.clicked.connect(self.openRequested)
        left.addWidget(new)
        left.addWidget(op)
        left.addSpacing(px(14))
        left.addWidget(QLabel("<b>빠른 시작</b>"))
        grid = QGridLayout()
        grid.setSpacing(px(8))
        for i, (name, w, h) in enumerate([p for p in presets if p[1]][:8]):
            b = QToolButton()
            b.setText(name.replace(" ", "\n", 1))
            b.setToolButtonStyle(Qt.ToolButtonTextOnly)
            b.setMinimumSize(px(130), px(52))
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("QToolButton { background:white; border:1px solid #e3dcd8; border-radius:8px; color:#555; }"
                            f"QToolButton:hover {{ border-color:{color}; color:{color}; }}")
            b.clicked.connect(lambda _=False, w=w, h=h: self.newRequested.emit(w, h))
            grid.addWidget(b, i // 2, i % 2)
        left.addLayout(grid)
        left.addStretch(1)
        root.addLayout(left, 0)

        right = QVBoxLayout()
        right.addWidget(QLabel("<b>최근 파일</b>  <span style='color:#999'>(두 번 누르면 열려요)</span>"))
        self.recent = QListWidget()
        self.recent.setStyleSheet("QListWidget { background:white; border:1px solid #e9e2de; border-radius:8px; }"
                                  "QListWidget::item { padding:8px; border-bottom:1px solid #f3eeeb; }"
                                  "QListWidget::item:hover { background:#fff3f6; }")
        self.recent.itemDoubleClicked.connect(lambda it: self.recentRequested.emit(it.data(Qt.UserRole)))
        right.addWidget(self.recent, 1)
        tip = QLabel("💡 파일을 이 창에 끌어다 놓아도 열립니다.")
        tip.setStyleSheet("color:#8a7f82;")
        right.addWidget(tip)
        root.addLayout(right, 1)

    def set_recent(self, paths):
        self.recent.clear()
        for p in paths:
            if os.path.exists(p):
                it = QListWidgetItem(QIcon(ui.icon("file")), f"{os.path.basename(p)}\n{os.path.dirname(p)}")
                it.setData(Qt.UserRole, p)
                self.recent.addItem(it)
        if not self.recent.count():
            it = QListWidgetItem("아직 연 파일이 없어요")
            it.setFlags(Qt.NoItemFlags)
            self.recent.addItem(it)


def push_recent(cfg, path, limit=12):
    lst = [p for p in cfg.get("recent", []) if p != path]
    cfg["recent"] = [path] + lst[:limit - 1]
    cfg.save()
