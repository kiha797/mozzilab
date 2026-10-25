"""모찌포토 - 포토샵 · 포토피아처럼 쓰는 사진/그림 편집 프로그램
레이어 · 브러시 · 선택 · 필터 · 색 보정 · PSD 열기/저장"""
import os
import sys

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
# 모찌랩 프로그램들이 함께 쓰는 코드(로그인·광고·디자인)는 ../shared 폴더에 있다
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared"))

from PySide6.QtCore import QPointF, QRectF, QSize, Qt  # noqa: E402
from PySide6.QtGui import (QAction, QColor, QIcon, QImage, QKeySequence, QPainter, QPainterPath,  # noqa: E402
                           QPixmap, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,  # noqa: E402
                               QGridLayout, QHBoxLayout, QInputDialog, QLabel, QListWidget,
                               QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QToolButton,
                               QVBoxLayout, QWidget)

import brand  # noqa: E402
import photo_core as C  # noqa: E402
import winapi  # noqa: E402
from app_shell import MozziWindow  # noqa: E402
from canvas import Canvas  # noqa: E402
from dialogs import AdjustDialog, CanvasSizeDialog, ImageSizeDialog, TextDialog, TransformDialog  # noqa: E402
from editor_kit import (PHOTO_PRESETS, ColorButton, NewDocDialog, Panel, SliderSpin, StartPage,  # noqa: E402
                        ToolPalette, checker_brush_pixmap, editor_qss, mini_button, push_recent, vsep)
from ui import px, stylesheet  # noqa: E402

TOOLS = [
    ("move", "이동", "move", "V"), ("marquee", "사각형 선택", "marquee", "M"),
    ("ellipsesel", "원형 선택", "ellipsesel", "M"), ("lasso", "올가미 선택", "lasso", "L"),
    ("wand", "자동 선택 (마술봉)", "wand", "W"), ("crop", "자르기", "crop", "C"),
    None,
    ("brush", "브러시", "brush", "B"), ("pencil", "연필", "pencil", "B"),
    ("eraser", "지우개", "eraser", "E"), ("stamp", "복제 도장", "stamp", "S"),
    ("bucket", "페인트 통", "bucket", "G"), ("gradient", "그레이디언트", "gradient", "G"),
    None,
    ("text", "문자", "text", "T"), ("shape", "도형", "shape", "U"),
    ("eyedrop", "스포이드", "eyedrop", "I"), ("zoom", "돋보기", "zoom", "Z"),
    ("hand", "손 (화면 이동)", "hand", "H"),
]

TOOL_OPTS = {
    "move": ["hint"], "crop": ["crop_apply", "crop_cancel", "hint"],
    "marquee": ["selmode", "hint"], "ellipsesel": ["selmode", "hint"], "lasso": ["selmode", "hint"],
    "wand": ["selmode", "tolerance", "contiguous", "all_layers"],
    "brush": ["size", "hardness", "opacity"], "pencil": ["size", "opacity"],
    "eraser": ["size", "hardness", "opacity"], "stamp": ["size", "hardness", "opacity", "hint"],
    "bucket": ["tolerance", "contiguous", "all_layers", "opacity"],
    "gradient": ["grad_type", "grad_transparent", "opacity", "hint"],
    "text": ["hint"], "shape": ["shape_type", "fill", "stroke", "stroke_w", "new_layer", "hint"],
    "eyedrop": ["hint"], "zoom": ["hint"], "hand": ["hint"],
}
HINTS = {
    "move": "드래그해서 레이어(또는 선택한 부분)를 옮겨요 · 방향키로 1픽셀씩",
    "crop": "남길 부분을 드래그한 뒤 Enter 또는 두 번 클릭",
    "marquee": "Shift = 정사각형/추가, Alt = 빼기", "ellipsesel": "Shift = 정원/추가, Alt = 빼기",
    "lasso": "마우스를 누른 채 자유롭게 그려서 선택",
    "stamp": "Alt+클릭 = 복제할 곳 지정, 그다음 드래그",
    "gradient": "드래그해서 방향과 길이를 정해요 (Shift = 45° 단위)",
    "text": "글자를 넣을 곳을 클릭하세요 (새 레이어로 들어가요)",
    "shape": "채우기 = 전경색, 테두리 = 배경색 · Shift = 정사각형/정원",
    "eyedrop": "클릭 = 전경색, Alt+클릭 = 배경색", "zoom": "클릭 = 확대, Alt+클릭 = 축소",
    "hand": "드래그해서 화면 이동 (어느 도구든 Space 를 누른 채 드래그해도 돼요)",
}
SWATCHES = ["#000000", "#ffffff", "#7f7f7f", "#c3c3c3", "#e5484d", "#ff6f91", "#ff9f43", "#ffd93d",
            "#6bcb77", "#2ec4b6", "#4d96ff", "#3a3fbf", "#9b5de5", "#f15bb5", "#8d5524", "#c68642",
            "#ffdbac", "#264653", "#e9c46a", "#f4a261"]


class OptionsBar(QWidget):
    """위쪽 '도구 옵션' 줄. 도구마다 필요한 칸만 보인다."""

    def __init__(self, ed):
        super().__init__()
        self.setObjectName("optbar")
        self.setAttribute(Qt.WA_StyledBackground)
        h = QHBoxLayout(self)
        h.setContentsMargins(px(10), px(4), px(10), px(4))
        h.setSpacing(px(10))
        self.tool_name = QLabel()
        self.tool_name.setStyleSheet("font-weight:bold; color:#ff8fab;")
        h.addWidget(self.tool_name)
        h.addWidget(vsep())
        self.w = {}

        def add(key, widget):
            self.w[key] = widget
            h.addWidget(widget)
            return widget
        self.size = add("size", SliderSpin("크기", 1, 1000, 24, " px"))
        self.hardness = add("hardness", SliderSpin("경도", 0, 100, 80, " %", 70))
        self.opacity = add("opacity", SliderSpin("불투명도", 1, 100, 100, " %", 70))
        self.selmode = QComboBox()
        self.selmode.addItems(["새 선택", "선택에 추가", "선택에서 빼기", "교차 영역"])
        add("selmode", self.selmode)
        self.tolerance = add("tolerance", SliderSpin("허용치", 0, 255, 32, "", 70))
        self.contiguous = add("contiguous", QCheckBox("인접한 곳만"))
        self.contiguous.setChecked(True)
        self.all_layers = add("all_layers", QCheckBox("모든 레이어 기준"))
        self.grad_type = QComboBox()
        self.grad_type.addItems(["선형", "원형"])
        add("grad_type", self.grad_type)
        self.grad_transparent = add("grad_transparent", QCheckBox("전경색 → 투명"))
        self.shape_type = QComboBox()
        self.shape_type.addItems(["사각형", "둥근 사각형", "타원", "선", "화살표"])
        add("shape_type", self.shape_type)
        self.fill = add("fill", QCheckBox("채우기"))
        self.fill.setChecked(True)
        self.stroke = add("stroke", QCheckBox("테두리"))
        sw = QWidget()
        sh = QHBoxLayout(sw)
        sh.setContentsMargins(0, 0, 0, 0)
        sh.addWidget(QLabel("두께"))
        self.stroke_w = QSpinBox()
        self.stroke_w.setRange(1, 200)
        self.stroke_w.setValue(4)
        self.stroke_w.setSuffix(" px")
        sh.addWidget(self.stroke_w)
        add("stroke_w", sw)
        self.new_layer = add("new_layer", QCheckBox("새 레이어에 그리기"))
        self.new_layer.setChecked(True)
        self.crop_apply = add("crop_apply", QPushButton("✔ 자르기"))
        self.crop_apply.clicked.connect(ed.apply_crop)
        self.crop_cancel = add("crop_cancel", QPushButton("취소"))
        self.crop_cancel.clicked.connect(lambda: (setattr(ed.canvas, "crop_rect", None), ed.canvas.update()))
        self.hint = add("hint", QLabel())
        self.hint.setStyleSheet("color:#a9a4ad;")
        h.addStretch(1)
        self.size.valueChanged.connect(lambda _: ed.canvas.update())

    def show_for(self, tool, title):
        self.tool_name.setText(title)
        keys = TOOL_OPTS.get(tool, [])
        for k, w in self.w.items():
            w.setVisible(k in keys)
        self.hint.setText(HINTS.get(tool, ""))


class History:
    """작업 내역 (실행 취소 / 다시 실행)"""

    def __init__(self, limit=40):
        self.items = []
        self.index = -1
        self.limit = limit

    def reset(self, name, snap):
        self.items = [(name, snap)]
        self.index = 0

    def push(self, name, snap):
        del self.items[self.index + 1:]
        self.items.append((name, snap))
        if len(self.items) > self.limit:
            self.items.pop(0)
        self.index = len(self.items) - 1


def layer_thumb(img, size=34):
    pm = QPixmap(size, size)
    pm.fill(QColor("#2e2d32"))
    p = QPainter(pm)
    s = img.size().scaled(QSize(size - 4, size - 4), Qt.KeepAspectRatio)
    r = QRectF((size - s.width()) / 2, (size - s.height()) / 2, s.width(), s.height())
    p.setBrushOrigin(r.topLeft())
    p.fillRect(r, checker_brush_pixmap(3))
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.drawImage(r, img)
    p.setPen(QColor("#111"))
    p.drawRect(r)
    p.end()
    return QIcon(pm)


class PhotoWindow(MozziWindow):
    def __init__(self):
        super().__init__({"recent": [], "fg": "#000000", "bg": "#ffffff", "tool": "brush"})
        self.doc = None
        self.history = History()
        self.modified = False
        self.setAcceptDrops(True)

        self.add_tool("새로 만들기", "newdoc", lambda: self.new_document(), tip="새 그림 (Ctrl+N)")
        self.add_tool("열기", "folder", lambda: self.open_file(), tip="파일 열기 (Ctrl+O) · PSD 도 열려요")
        self.add_tool("저장", "save", self.save, tip="저장 (Ctrl+S) · 레이어가 유지돼요")
        self.add_tool("내보내기", "export", self.export, tip="PNG · JPG · WEBP 로 내보내기 (Ctrl+Shift+E)")
        self.add_separator()
        self.add_tool("실행 취소", "undo", self.undo, tip="실행 취소 (Ctrl+Z)")
        self.add_tool("다시 실행", "redo", self.redo, tip="다시 실행 (Ctrl+Y)")
        self.add_separator()
        self.add_tool("이미지 크기", "resize", self.image_size, tip="이미지 크기 바꾸기 (Ctrl+Alt+I)")
        self.add_tool("색 보정", "adjust", lambda: self.adjust("hs"), tip="색조 / 채도 (Ctrl+U)")

        self.start = StartPage(brand.APP_NAME, "포토샵처럼 레이어로 사진을 편집해요 · PSD 열기/저장 가능",
                               PHOTO_PRESETS, "#7c6cf0")
        self.start.newRequested.connect(lambda w, h: self.new_document(w, h))
        self.start.openRequested.connect(lambda: self.open_file())
        self.start.recentRequested.connect(self.open_file)
        self.start.set_recent(self.cfg.get("recent", []))
        self.body.addWidget(self.start)
        self.body.addWidget(self._build_editor())
        self._build_menus()
        self.set_tool(self.cfg.get("tool") or "brush")
        self._update_enabled()

    # ---------- 화면 구성 ----------
    def _build_editor(self):
        ed = QWidget()
        ed.setObjectName("editor")
        ed.setAttribute(Qt.WA_StyledBackground)
        ed.setStyleSheet(editor_qss())
        v = QVBoxLayout(ed)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.canvas = Canvas(self)
        self.opts = OptionsBar(self)
        v.addWidget(self.opts)
        row = QHBoxLayout()
        row.setSpacing(0)
        v.addLayout(row, 1)

        self.palette = ToolPalette(TOOLS)
        self.palette.changed.connect(self.set_tool)
        self.fg_btn = ColorButton(self.cfg.get("fg"), size=30, tip="전경색 (브러시 색) · 클릭해서 바꾸기")
        self.bg_btn = ColorButton(self.cfg.get("bg"), size=30, tip="배경색 · 클릭해서 바꾸기")
        cw = QWidget()
        cg = QGridLayout(cw)
        cg.setContentsMargins(0, px(6), 0, 0)
        cg.setSpacing(px(2))
        cg.addWidget(self.fg_btn, 0, 0)
        cg.addWidget(self.bg_btn, 1, 1)
        cg.addWidget(mini_button("reset", "전경색 ↔ 배경색 바꾸기 (X)", self.swap_colors, size=14), 0, 1)
        cg.addWidget(mini_button("cancel", "기본색 (검정/흰색) (D)", self.default_colors, size=14), 1, 0)
        self.palette.extra.addWidget(cw)
        row.addWidget(self.palette)
        row.addWidget(self.canvas, 1)

        side = QWidget()
        side.setObjectName("sidebar")
        side.setAttribute(Qt.WA_StyledBackground)
        side.setFixedWidth(px(270))
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)
        # 색상 견본
        sw = QWidget()
        sg = QGridLayout(sw)
        sg.setContentsMargins(0, 0, 0, 0)
        sg.setSpacing(px(3))
        for i, c in enumerate(SWATCHES):
            b = QToolButton()
            b.setFixedSize(px(20), px(20))
            b.setToolTip(f"{c}  (클릭 = 전경색, 오른쪽 클릭 = 배경색)")
            b.setStyleSheet(f"QToolButton {{ background:{c}; border:1px solid #111; border-radius:2px; }}")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=c: self.fg_btn.set_color(c))
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda _=None, c=c: self.bg_btn.set_color(c))
            sg.addWidget(b, i // 10, i % 10)
        sv.addWidget(Panel("색상 견본", sw))

        # 레이어
        lw = QWidget()
        lv = QVBoxLayout(lw)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(px(4))
        top = QHBoxLayout()
        self.blend = QComboBox()
        for _, name, *_ in C.BLEND_MODES:
            self.blend.addItem(name)
        self.blend.setToolTip("혼합 모드")
        self.blend.activated.connect(self._blend_changed)
        top.addWidget(self.blend, 1)
        lv.addLayout(top)
        self.layer_opacity = SliderSpin("불투명도", 0, 100, 100, " %", 80)
        self.layer_opacity.slider.sliderReleased.connect(lambda: self._opacity_changed(commit=True))
        self.layer_opacity.spin.editingFinished.connect(lambda: self._opacity_changed(commit=True))
        self.layer_opacity.valueChanged.connect(lambda _: self._opacity_changed(commit=False))
        lv.addWidget(self.layer_opacity)
        self.layer_list = QListWidget()
        self.layer_list.setIconSize(QSize(px(34), px(34)))
        self.layer_list.currentRowChanged.connect(self._layer_selected)
        self.layer_list.itemChanged.connect(self._layer_item_changed)
        self.layer_list.setToolTip("체크 = 보이기/숨기기 · 두 번 클릭 = 이름 바꾸기")
        lv.addWidget(self.layer_list, 1)
        bh = QHBoxLayout()
        bh.setSpacing(px(2))
        for ic, tip, fn in (("add", "새 레이어 (Ctrl+Shift+N)", self.new_layer),
                            ("duplicate", "레이어 복제 (Ctrl+J)", lambda: self._layer_op(self.doc.duplicate_layer, "레이어 복제")),
                            ("up", "위로", lambda: self._layer_op(lambda: self.doc.move_layer(1), "레이어 순서")),
                            ("down", "아래로", lambda: self._layer_op(lambda: self.doc.move_layer(-1), "레이어 순서")),
                            ("merge", "아래 레이어와 병합 (Ctrl+E)", lambda: self._layer_op(self.doc.merge_down, "아래로 병합")),
                            ("trash", "레이어 삭제", lambda: self._layer_op(self.doc.delete_layer, "레이어 삭제"))):
            bh.addWidget(mini_button(ic, tip, fn))
        bh.addStretch(1)
        lv.addLayout(bh)
        sv.addWidget(Panel("레이어", lw, stretch=True), 3)

        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(lambda it: self.goto_history(self.history_list.row(it)))
        sv.addWidget(Panel("작업 내역", self.history_list, stretch=True), 1)
        row.addWidget(side)

        self.pos_label = QLabel("")
        self.zoom_label = QLabel("")
        self.statusBar().addPermanentWidget(self.pos_label)
        self.statusBar().addPermanentWidget(self.zoom_label)
        self.canvas.cursorMoved.connect(lambda x, y: self.pos_label.setText(f"  X {x}  Y {y}  "))
        self.canvas.zoomChanged.connect(lambda z: self.zoom_label.setText(
            f"  {round(z * 100)}%  ·  {self.doc.width} × {self.doc.height} px  " if self.doc else ""))
        self.canvas.message.connect(lambda m: self.statusBar().showMessage(m, 6000))
        return ed

    def _build_menus(self):
        mb = self.menuBar()
        self.doc_actions = []

        def act(menu, text, slot, sc=None, needs_doc=True):
            a = QAction(text, self)
            if sc:
                a.setShortcut(QKeySequence(sc))
            a.triggered.connect(lambda _=False: slot())
            menu.addAction(a)
            if needs_doc:
                self.doc_actions.append(a)
            return a

        m = mb.addMenu("파일(&F)")
        act(m, "새로 만들기…", lambda: self.new_document(), "Ctrl+N", False)
        act(m, "열기…", lambda: self.open_file(), "Ctrl+O", False)
        self.recent_menu = m.addMenu("최근 파일")
        self.recent_menu.aboutToShow.connect(self._fill_recent)
        act(m, "이미지를 레이어로 가져오기…", self.place_image, "Ctrl+Shift+P")
        m.addSeparator()
        act(m, "저장", self.save, "Ctrl+S")
        act(m, "다른 이름으로 저장…", self.save_as, "Ctrl+Shift+S")
        act(m, "내보내기 (PNG · JPG · WEBP)…", self.export, "Ctrl+Shift+E")
        m.addSeparator()
        act(m, "닫기", self.close_document, "Ctrl+W")
        act(m, "끝내기", self.close, "Ctrl+Q", False)

        m = mb.addMenu("편집(&E)")
        act(m, "실행 취소", self.undo, "Ctrl+Z")
        act(m, "다시 실행", self.redo, "Ctrl+Y")
        act(m, "다시 실행 ", self.redo, "Ctrl+Shift+Z")
        m.addSeparator()
        act(m, "잘라내기", self.cut, "Ctrl+X")
        act(m, "복사", self.copy, "Ctrl+C")
        act(m, "병합하여 복사", lambda: self.copy(merged=True), "Ctrl+Shift+C")
        act(m, "붙여넣기 (새 레이어)", self.paste, "Ctrl+V", False)
        act(m, "지우기 (선택 영역)", self.clear_selection_pixels, None)
        act(m, "전경색으로 채우기", lambda: self.fill_color(self.fg_btn.color()), "Alt+Backspace")
        act(m, "배경색으로 채우기", lambda: self.fill_color(self.bg_btn.color()), "Ctrl+Backspace")
        m.addSeparator()
        act(m, "레이어 변형 (크기 · 회전)…", self.transform_layer, "Ctrl+T")

        m = mb.addMenu("이미지(&I)")
        am = m.addMenu("조정")
        for key, text, sc in (("bc", "밝기 / 대비…", None), ("levels", "레벨…", "Ctrl+L"), ("hs", "색조 / 채도…", "Ctrl+U"),
                              ("balance", "색상 균형…", "Ctrl+B"), ("posterize", "포스터화…", None),
                              ("threshold", "한계값…", None)):
            act(am, text, lambda k=key: self.adjust(k), sc)
        am.addSeparator()
        for fn, text, sc in ((C.grayscale, "흑백", "Ctrl+Shift+U"), (C.invert, "반전", "Ctrl+I"),
                             (C.sepia, "세피아 (옛날 사진)", None), (C.auto_contrast, "자동 대비", "Ctrl+Shift+L"),
                             (C.auto_color, "자동 색상 (평활화)", None)):
            act(am, text, lambda f=fn, t=text: self.apply_filter(f, t), sc)
        m.addSeparator()
        act(m, "이미지 크기…", self.image_size, "Ctrl+Alt+I")
        act(m, "캔버스 크기…", self.canvas_size, "Ctrl+Alt+C")
        rm = m.addMenu("이미지 회전")
        act(rm, "시계 방향 90°", lambda: self._doc_op(lambda: self.doc.rotate(90), "이미지 회전"))
        act(rm, "반시계 방향 90°", lambda: self._doc_op(lambda: self.doc.rotate(-90), "이미지 회전"))
        act(rm, "180°", lambda: self._doc_op(lambda: self.doc.rotate(180), "이미지 회전"))
        act(rm, "좌우 뒤집기", lambda: self._doc_op(lambda: self.doc.flip(True), "좌우 뒤집기"))
        act(rm, "상하 뒤집기", lambda: self._doc_op(lambda: self.doc.flip(False), "상하 뒤집기"))
        act(m, "선택 영역으로 자르기", self.crop_to_selection)
        act(m, "이미지 병합 (레이어 하나로)", lambda: self._doc_op(self.doc.flatten, "이미지 병합"))

        m = mb.addMenu("레이어(&L)")
        act(m, "새 레이어", self.new_layer, "Ctrl+Shift+N")
        act(m, "레이어 복제", lambda: self._layer_op(self.doc.duplicate_layer, "레이어 복제"), "Ctrl+J")
        act(m, "레이어 삭제", lambda: self._layer_op(self.doc.delete_layer, "레이어 삭제"))
        act(m, "레이어 이름 바꾸기…", self.rename_layer)
        m.addSeparator()
        act(m, "위로 올리기", lambda: self._layer_op(lambda: self.doc.move_layer(1), "레이어 순서"), "Ctrl+]")
        act(m, "아래로 내리기", lambda: self._layer_op(lambda: self.doc.move_layer(-1), "레이어 순서"), "Ctrl+[")
        m.addSeparator()
        act(m, "아래로 병합", lambda: self._layer_op(self.doc.merge_down, "아래로 병합"), "Ctrl+E")
        act(m, "보이는 레이어 병합", lambda: self._layer_op(self.doc.merge_visible, "보이는 레이어 병합"), "Ctrl+Shift+E")
        m.addSeparator()
        act(m, "레이어 좌우 뒤집기", lambda: self._layer_transform(QTransform().scale(-1, 1), "레이어 좌우 뒤집기"))
        act(m, "레이어 상하 뒤집기", lambda: self._layer_transform(QTransform().scale(1, -1), "레이어 상하 뒤집기"))

        m = mb.addMenu("선택(&S)")
        act(m, "모두 선택", self.select_all, "Ctrl+A")
        act(m, "선택 해제", self.deselect, "Ctrl+D")
        act(m, "선택 반전", self.invert_selection, "Ctrl+Shift+I")
        act(m, "레이어 내용 선택 (투명 아닌 곳)", self.select_layer_pixels)

        m = mb.addMenu("필터(&T)")
        for key, text in (("blur", "가우시안 흐림…"), ("boxblur", "상자 흐림…"), ("sharpen", "선명하게 (언샵 마스크)…"),
                          ("noise", "노이즈 추가…"), ("pixelate", "모자이크 (픽셀화)…"), ("vignette", "비네팅 (가장자리 어둡게)…"),
                          ("oil", "유화 효과…")):
            act(m, text, lambda k=key: self.adjust(k))
        m.addSeparator()
        act(m, "엠보스", lambda: self.apply_filter(C.emboss, "엠보스"))
        act(m, "윤곽선 찾기", lambda: self.apply_filter(C.find_edges, "윤곽선 찾기"))

        m = mb.addMenu("보기(&V)")
        act(m, "확대", lambda: self.canvas.zoom_by(1.25), "Ctrl+=")
        act(m, "확대 ", lambda: self.canvas.zoom_by(1.25), "Ctrl++")
        act(m, "축소", lambda: self.canvas.zoom_by(0.8), "Ctrl+-")
        act(m, "화면에 맞추기", self.canvas.fit, "Ctrl+0")
        act(m, "실제 크기 (100%)", self.canvas.actual_size, "Ctrl+1")

        m = mb.addMenu("도움말(&H)")
        act(m, "단축키 안내", self.show_shortcuts, "F1", False)
        act(m, "업데이트 확인", lambda: self.updater.check(manual=True), None, False)
        act(m, f"{brand.APP_NAME} 정보", self.about, None, False)

        for key, (dx, dy) in ((Qt.Key_Left, (-1, 0)), (Qt.Key_Right, (1, 0)), (Qt.Key_Up, (0, -1)), (Qt.Key_Down, (0, 1))):
            a = QAction(self)
            a.setShortcuts([QKeySequence(key), QKeySequence(Qt.SHIFT | key)])
            a.triggered.connect(lambda _=False, dx=dx, dy=dy: self._nudge(dx, dy))
            self.canvas.addAction(a)
            a.setShortcutContext(Qt.WidgetShortcut)

    def _fill_recent(self):
        self.recent_menu.clear()
        for p in self.cfg.get("recent", []):
            if os.path.exists(p):
                self.recent_menu.addAction(os.path.basename(p), lambda p=p: self.open_file(p))
        if self.recent_menu.isEmpty():
            self.recent_menu.addAction("(없음)").setEnabled(False)

    def _update_enabled(self):
        has = self.doc is not None
        for a in self.doc_actions:
            a.setEnabled(has)

    # ---------- 도구 / 색 ----------
    def set_tool(self, key):
        names = {t[0]: t[1] for t in TOOLS if t}
        if key not in names:
            key = "brush"
        self.palette.select(key)
        self.canvas.set_tool(key)
        self.opts.show_for(key, names[key])
        self.cfg["tool"] = key

    def tool_shortcut(self, letter):
        k = self.palette.tool_for_key(letter, self.canvas.tool)
        if k:
            self.set_tool(k)

    def swap_colors(self):
        a, b = self.fg_btn.color(), self.bg_btn.color()
        self.fg_btn.set_color(b)
        self.bg_btn.set_color(a)

    def default_colors(self):
        self.fg_btn.set_color("#000000")
        self.bg_btn.set_color("#ffffff")

    # ---------- 문서 ----------
    def set_document(self, doc, title):
        self.doc = doc
        self.doc_title = title
        self.history.reset(title, doc.snapshot())
        self.modified = False
        self.body.setCurrentIndex(1)
        self.canvas.set_document(doc)
        self.canvas.fit()
        self.refresh_panels()
        self._update_enabled()
        self._update_title()
        self.canvas.setFocus()

    def _update_title(self):
        if self.doc:
            self.setWindowTitle(f"{self.doc_title}{' *' if self.modified else ''} - {brand.APP_NAME}")
        else:
            self.setWindowTitle(brand.APP_NAME)

    def maybe_save(self):
        if not self.doc or not self.modified:
            return True
        r = QMessageBox.question(self, brand.APP_NAME, f"'{self.doc_title}' 의 바뀐 내용을 저장할까요?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.save()
        return r == QMessageBox.Discard

    def new_document(self, w=0, h=0, bg=QColor("white")):
        if not self.maybe_save():
            return
        if not w:
            cb = QApplication.clipboard().image()
            dw, dh = (cb.width(), cb.height()) if not cb.isNull() else (1920, 1080)
            dlg = NewDocDialog(self, PHOTO_PRESETS, dw, dh)
            if dlg.exec() != NewDocDialog.Accepted:
                return
            w, h, bg = dlg.values()
        self.set_document(C.Document(w, h, bg), "제목 없음")

    def open_file(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "열기", self.cfg.start_dir(), C.OPEN_FILTER)
            if not path:
                return
        if not self.maybe_save():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            doc = C.load_document(path)
        except Exception as e:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, brand.APP_NAME, f"파일을 열 수 없어요.\n\n{e}")
            return
        QApplication.restoreOverrideCursor()
        self.cfg.remember_dir(path)
        push_recent(self.cfg, path)
        self.start.set_recent(self.cfg.get("recent", []))
        self.set_document(doc, os.path.basename(path))
        if path.lower().endswith(".psd"):
            self.statusBar().showMessage(f"PSD 레이어 {len(doc.layers)}개를 불러왔어요.", 6000)

    def close_document(self):
        if not self.maybe_save():
            return
        self.doc = None
        self.canvas.doc = None
        self.body.setCurrentIndex(0)
        self.start.set_recent(self.cfg.get("recent", []))
        self._update_enabled()
        self._update_title()

    def save(self):
        if not self.doc:
            return False
        if self.doc.path and self.doc.path.lower().endswith((".mphoto", ".psd")):
            return self._save_to(self.doc.path)
        return self.save_as()

    def save_as(self):
        if not self.doc:
            return False
        base = os.path.splitext(self.doc_title)[0] if self.doc_title != "제목 없음" else "그림"
        path, flt = QFileDialog.getSaveFileName(
            self, "저장 (레이어 유지)", os.path.join(self.cfg.start_dir(), base + ".mphoto"),
            "모찌포토 프로젝트 (*.mphoto);;포토샵 PSD (*.psd)")
        if not path:
            return False
        if not path.lower().endswith((".mphoto", ".psd")):
            path += ".psd" if "psd" in flt.lower() else ".mphoto"
        return self._save_to(path)

    def _save_to(self, path):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if path.lower().endswith(".psd"):
                C.save_psd(self.doc, path)
            else:
                C.save_project(self.doc, path)
        except Exception as e:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, brand.APP_NAME, f"저장하지 못했어요.\n\n{e}")
            return False
        QApplication.restoreOverrideCursor()
        self.doc.path = path
        self.doc_title = os.path.basename(path)
        self.modified = False
        self._update_title()
        self.cfg.remember_dir(path)
        push_recent(self.cfg, path)
        self.statusBar().showMessage(f"저장했어요: {path}", 5000)
        return True

    def export(self):
        if not self.doc:
            return
        base = os.path.splitext(self.doc_title)[0] if self.doc_title != "제목 없음" else "그림"
        path, flt = QFileDialog.getSaveFileName(
            self, "내보내기", os.path.join(self.cfg.start_dir(), base + ".png"),
            "PNG (*.png);;JPG (*.jpg);;WEBP (*.webp);;BMP (*.bmp);;GIF (*.gif);;TIFF (*.tif);;포토샵 PSD (*.psd)")
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if not ext:
            ext = "." + flt.split("*.")[1].split(")")[0]
            path += ext
        q = 92
        if ext in (".jpg", ".jpeg", ".webp"):
            q, ok = QInputDialog.getInt(self, "화질", "화질 (1~100, 높을수록 선명하고 파일이 커요)", 92, 1, 100)
            if not ok:
                return
        try:
            C.export_image(self.doc, path, q)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, brand.APP_NAME, f"내보내지 못했어요.\n\n{e}")
            return
        self.cfg.remember_dir(path)
        self.job_done("내보내기 완료", os.path.basename(path), path)

    def place_image(self, path=None):
        if not self.doc:
            return
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "레이어로 가져올 이미지", self.cfg.start_dir(), C.OPEN_FILTER)
            if not path:
                return
        try:
            img = C.open_as_image(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, brand.APP_NAME, f"이미지를 열 수 없어요.\n\n{e}")
            return
        self._add_image_layer(img, os.path.splitext(os.path.basename(path))[0])

    def _add_image_layer(self, img, name):
        doc = self.doc
        if img.width() > doc.width or img.height() > doc.height:
            img = img.scaled(doc.width, doc.height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        layer = C.new_image(doc.width, doc.height)
        p = QPainter(layer)
        p.drawImage((doc.width - img.width()) // 2, (doc.height - img.height()) // 2, img)
        p.end()
        doc.add_layer(name, layer)
        self.commit("레이어 가져오기")
        self.set_tool("move")

    # ---------- 실행 취소 ----------
    def commit(self, name):
        """작업 하나가 끝날 때마다 호출: 작업 내역에 기록 + 화면 갱신"""
        if not self.doc:
            return
        self.doc.invalidate()
        self.history.push(name, self.doc.snapshot())
        self.modified = True
        self._update_title()
        self.refresh_panels()
        self.canvas.update()

    def goto_history(self, i):
        if not self.doc or not (0 <= i < len(self.history.items)):
            return
        self.history.index = i
        self.doc.restore(self.history.items[i][1])
        self.modified = True
        self._update_title()
        self.refresh_panels()
        self.canvas.zoomChanged.emit(self.canvas.zoom)
        self.canvas.update()

    def undo(self):
        if self.doc and self.history.index > 0:
            self.goto_history(self.history.index - 1)

    def redo(self):
        if self.doc and self.history.index < len(self.history.items) - 1:
            self.goto_history(self.history.index + 1)

    # ---------- 패널 ----------
    def refresh_panels(self):
        doc = self.doc
        if not doc:
            return
        ll = self.layer_list
        ll.blockSignals(True)
        ll.clear()
        for i in range(len(doc.layers) - 1, -1, -1):
            ly = doc.layers[i]
            it = QListWidgetItem(layer_thumb(ly.image), ly.name)
            it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            it.setCheckState(Qt.Checked if ly.visible else Qt.Unchecked)
            ll.addItem(it)
        ll.setCurrentRow(len(doc.layers) - 1 - doc.active)
        ll.blockSignals(False)
        self._sync_layer_props()
        hl = self.history_list
        hl.clear()
        for i, (name, _) in enumerate(self.history.items):
            it = QListWidgetItem(name)
            if i > self.history.index:
                it.setForeground(QColor("#77737b"))
            hl.addItem(it)
        hl.setCurrentRow(self.history.index)

    def _sync_layer_props(self):
        ly = self.doc.layer
        self.blend.setCurrentIndex([k for k, *_ in C.BLEND_MODES].index(ly.blend) if ly.blend in C.BLEND_QT else 0)
        self.layer_opacity.blockSignals(True)
        self.layer_opacity.setValue(round(ly.opacity * 100))
        self.layer_opacity.blockSignals(False)

    def _layer_selected(self, row):
        if self.doc and row >= 0:
            self.doc.active = len(self.doc.layers) - 1 - row
            self._sync_layer_props()

    def _layer_item_changed(self, it):
        doc = self.doc
        i = len(doc.layers) - 1 - self.layer_list.row(it)
        ly = doc.layers[i]
        vis = it.checkState() == Qt.Checked
        if vis != ly.visible:
            ly.visible = vis
            self.commit("레이어 보이기" if vis else "레이어 숨기기")
        elif it.text() and it.text() != ly.name:
            ly.name = it.text()
            self.commit("레이어 이름")

    def _blend_changed(self, i):
        if self.doc:
            self.doc.layer.blend = C.BLEND_MODES[i][0]
            self.commit("혼합 모드")

    def _opacity_changed(self, commit):
        if not self.doc:
            return
        v = self.layer_opacity.value() / 100
        if abs(self.doc.layer.opacity - v) > 1e-6 or commit:
            changed = abs(self.doc.layer.opacity - v) > 1e-6
            self.doc.layer.opacity = v
            self.doc.composite()
            self.canvas.update()
            if commit and (changed or self.history.items[self.history.index][1]["layers"][self.doc.active][3] != v):
                self.commit("불투명도")

    def _layer_op(self, fn, name):
        if not self.doc:
            return
        try:
            fn()
        except C.PhotoError as e:
            QMessageBox.information(self, brand.APP_NAME, str(e))
            return
        self.commit(name)

    def _doc_op(self, fn, name):
        if not self.doc:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            fn()
        except C.PhotoError as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, brand.APP_NAME, str(e))
            return
        QApplication.restoreOverrideCursor()
        self.commit(name)
        self.canvas.fit()

    def new_layer(self):
        if self.doc:
            self.doc.add_layer()
            self.commit("새 레이어")

    def rename_layer(self):
        name, ok = QInputDialog.getText(self, "레이어 이름", "새 이름", text=self.doc.layer.name)
        if ok and name.strip():
            self.doc.layer.name = name.strip()
            self.commit("레이어 이름")

    # ---------- 선택 ----------
    def select_all(self):
        p = QPainterPath()
        p.addRect(QRectF(self.doc.rect()))
        self.doc.selection = p
        self.commit("모두 선택")

    def deselect(self):
        if self.doc.has_selection():
            self.doc.selection = QPainterPath()
            self.commit("선택 해제")

    def invert_selection(self):
        full = QPainterPath()
        full.addRect(QRectF(self.doc.rect()))
        self.doc.selection = full.subtracted(self.doc.selection) if self.doc.has_selection() else QPainterPath()
        self.commit("선택 반전")

    def select_layer_pixels(self):
        arr = C.qimage_to_array(self.doc.layer.image)
        m = arr[..., 3] > 0
        self.doc.selection = C.path_from_mask(m) if m.any() else QPainterPath()
        self.commit("레이어 내용 선택")

    def clear_selection_pixels(self):
        doc = self.doc
        if not doc:
            return
        if not doc.has_selection():
            self.statusBar().showMessage("먼저 지울 곳을 선택하세요 (선택 도구 M · L · W)", 5000)
            return
        p = QPainter(doc.layer.image)
        p.setClipPath(doc.selection)
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.fillRect(doc.rect(), Qt.transparent)
        p.end()
        self.commit("지우기")

    def fill_color(self, color):
        doc = self.doc
        p = QPainter(doc.layer.image)
        if doc.has_selection():
            p.setClipPath(doc.selection)
        p.fillRect(doc.rect(), color)
        p.end()
        self.commit("채우기")

    def crop_to_selection(self):
        if not self.doc.has_selection():
            QMessageBox.information(self, brand.APP_NAME, "먼저 남길 부분을 선택하세요.")
            return
        r = self.doc.selection.boundingRect().toAlignedRect()
        self._doc_op(lambda: self.doc.crop(r), "자르기")

    def apply_crop(self):
        r = self.canvas.crop_rect
        if r is None:
            return
        self.canvas.crop_rect = None
        self._doc_op(lambda: self.doc.crop(r), "자르기")

    def _nudge(self, dx, dy):
        if self.doc and self.canvas.tool == "move":
            m = 10 if QApplication.keyboardModifiers() & Qt.ShiftModifier else 1
            self.canvas.nudge(dx * m, dy * m)

    # ---------- 복사 / 붙여넣기 ----------
    def copy(self, merged=False):
        doc = self.doc
        src = doc.composite() if merged else doc.layer.image
        if doc.has_selection():
            r = doc.selection.boundingRect().toAlignedRect().intersected(doc.rect())
            img = C.new_image(r.width(), r.height())
            p = QPainter(img)
            p.translate(-r.x(), -r.y())
            p.setClipPath(doc.selection)
            p.drawImage(0, 0, src)
            p.end()
        else:
            img = QImage(src)
        QApplication.clipboard().setImage(img)
        self.statusBar().showMessage("복사했어요.", 3000)

    def cut(self):
        self.copy()
        if self.doc.has_selection():
            self.clear_selection_pixels()

    def paste(self):
        img = QApplication.clipboard().image()
        if img.isNull():
            QMessageBox.information(self, brand.APP_NAME, "클립보드에 그림이 없어요.")
            return
        img = img.convertToFormat(C.FMT)
        if not self.doc:
            doc = C.Document(img.width(), img.height(), None)
            doc.layers[0].image = img
            doc.layers[0].name = "붙여넣은 그림"
            self.set_document(doc, "붙여넣기")
            return
        doc = self.doc
        layer = C.new_image(doc.width, doc.height)
        p = QPainter(layer)
        if doc.has_selection():
            r = doc.selection.boundingRect().toAlignedRect()
            p.drawImage(r.x(), r.y(), img)
        else:
            p.drawImage((doc.width - img.width()) // 2, (doc.height - img.height()) // 2, img)
        p.end()
        doc.add_layer("붙여넣기", layer)
        self.commit("붙여넣기")

    # ---------- 문자 ----------
    def add_text(self, pos):
        dlg = TextDialog(self, self.cfg.get("font", "Malgun Gothic"), self.cfg.get("font_size", 48), self.fg_btn.color())
        if dlg.exec() != TextDialog.Accepted:
            return
        text, font, color, align = dlg.values()
        if not text.strip():
            return
        self.cfg["font"] = font.family()
        self.cfg["font_size"] = font.pixelSize()
        doc = self.doc
        layer = C.new_image(doc.width, doc.height)
        p = QPainter(layer)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(font)
        p.setPen(color)
        fm = p.fontMetrics()
        lines = text.split("\n")
        width = max(fm.horizontalAdvance(ln) for ln in lines)
        r = QRectF(pos.x(), pos.y(), width + 4, fm.lineSpacing() * len(lines) + 4)
        if align == Qt.AlignHCenter:
            r.moveLeft(pos.x() - width / 2)
        elif align == Qt.AlignRight:
            r.moveRight(pos.x())
        p.drawText(r, align | Qt.AlignTop, text)
        p.end()
        doc.add_layer("T " + lines[0][:16], layer)
        self.commit("문자")

    # ---------- 보정 · 필터 ----------
    ADJUST = {
        "bc": ("밝기 / 대비", C.brightness_contrast, [("밝기", "brightness", -100, 100, 0), ("대비", "contrast", -100, 100, 0)]),
        "levels": ("레벨", C.levels, [("검정 기준", "black", 0, 254, 0), ("흰색 기준", "white", 1, 255, 255),
                                      ("감마 (중간톤 ×100)", "gamma", 10, 400, 100)]),
        "hs": ("색조 / 채도", C.hue_saturation, [("색조", "hue", -180, 180, 0), ("채도", "saturation", -100, 100, 0),
                                              ("밝기", "lightness", -100, 100, 0)]),
        "balance": ("색상 균형", C.color_balance, [("빨강", "red", -100, 100, 0), ("초록", "green", -100, 100, 0),
                                                ("파랑", "blue", -100, 100, 0)]),
        "posterize": ("포스터화", C.posterize, [("단계", "levels_", 2, 32, 4)]),
        "threshold": ("한계값", C.threshold, [("기준 밝기", "level", 1, 255, 128)]),
        "blur": ("가우시안 흐림", C.gaussian_blur, [("반경 (px)", "radius", 1, 100, 4)]),
        "boxblur": ("상자 흐림", C.box_blur, [("반경 (px)", "radius", 1, 100, 4)]),
        "sharpen": ("선명하게", C.sharpen, [("양 (%)", "amount", 10, 500, 120), ("반경 (px)", "radius", 1, 20, 2)]),
        "noise": ("노이즈 추가", C.add_noise, [("양", "amount", 1, 100, 20)]),
        "pixelate": ("모자이크", C.pixelate, [("칸 크기 (px)", "size", 2, 200, 12)]),
        "vignette": ("비네팅", C.vignette, [("세기 (%)", "strength", 0, 100, 50)]),
        "oil": ("유화 효과", C.oil_paint, [("붓 크기", "size", 3, 15, 5)]),
    }

    def adjust(self, key):
        if not self.doc:
            return
        title, fn, specs = self.ADJUST[key]
        if not self.doc.layer.visible:
            QMessageBox.information(self, brand.APP_NAME, "숨겨진 레이어예요. 레이어를 보이게 한 뒤 다시 해 주세요.")
            return
        dlg = AdjustDialog(self, title, fn, specs)
        if dlg.exec() == AdjustDialog.Accepted:
            self.commit(title)

    def apply_filter(self, fn, name):
        if not self.doc:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ly = self.doc.layer
            ly.image = C.apply_pil(ly.image, fn, self.doc.selection if self.doc.has_selection() else None)
        finally:
            QApplication.restoreOverrideCursor()
        self.commit(name)

    def image_size(self):
        if not self.doc:
            return
        dlg = ImageSizeDialog(self, self.doc.width, self.doc.height)
        if dlg.exec() == ImageSizeDialog.Accepted:
            w, h, smooth = dlg.values()
            self._doc_op(lambda: self.doc.resize_image(w, h, smooth), "이미지 크기")

    def canvas_size(self):
        dlg = CanvasSizeDialog(self, self.doc.width, self.doc.height)
        if dlg.exec() == CanvasSizeDialog.Accepted:
            w, h, anchor, fill = dlg.values()
            self._doc_op(lambda: self.doc.resize_canvas(w, h, anchor, fill), "캔버스 크기")

    def _layer_transform(self, t, name):
        doc = self.doc
        img = doc.layer.image
        c = QPointF(doc.width / 2, doc.height / 2)
        tt = QTransform().translate(c.x(), c.y())
        tt = t * tt
        tt = QTransform().translate(-c.x(), -c.y()) * tt
        out = C.new_image(doc.width, doc.height)
        p = QPainter(out)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setTransform(tt)
        p.drawImage(0, 0, img)
        p.end()
        doc.layer.image = out
        self.commit(name)

    def transform_layer(self):
        dlg = TransformDialog(self)
        if dlg.exec() == TransformDialog.Accepted:
            sx, sy, ang = dlg.values()
            self._layer_transform(QTransform().rotate(ang).scale(sx, sy), "레이어 변형")

    # ---------- 끌어다 놓기 ----------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() or e.mimeData().hasImage():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.toLocalFile().lower().endswith(C.IMAGE_EXTS)]
        if not paths:
            return
        if self.doc:
            box = QMessageBox(QMessageBox.Question, brand.APP_NAME, "끌어다 놓은 그림을 어떻게 할까요?", parent=self)
            as_layer = box.addButton("레이어로 넣기", QMessageBox.AcceptRole)
            box.addButton("새로 열기", QMessageBox.ActionRole)
            box.addButton("취소", QMessageBox.RejectRole)
            box.exec()
            role = box.buttonRole(box.clickedButton())
            if role == QMessageBox.RejectRole:
                return
            if box.clickedButton() is as_layer:
                for p in paths:
                    self.place_image(p)
                return
        self.open_file(paths[0])

    # ---------- 도움말 ----------
    def show_shortcuts(self):
        QMessageBox.information(self, "단축키 안내", (
            "<b>도구</b><br>V 이동 · M 선택 · L 올가미 · W 마술봉 · C 자르기<br>"
            "B 브러시/연필 · E 지우개 · S 복제 도장 · G 페인트통/그레이디언트<br>"
            "T 문자 · U 도형 · I 스포이드 · Z 돋보기 · H 손<br><br>"
            "<b>자주 쓰는 키</b><br>[ / ] 브러시 크기 · X 색 바꾸기 · D 기본색<br>"
            "Space+드래그 화면 이동 · Ctrl+휠 확대/축소 · Ctrl+0 화면에 맞추기<br>"
            "Ctrl+Z 실행취소 · Ctrl+J 레이어 복제 · Ctrl+T 변형 · Ctrl+D 선택 해제<br>"
            "Ctrl+U 색조/채도 · Ctrl+L 레벨 · Ctrl+I 반전 · Delete 선택 영역 지우기"))

    def about(self):
        QMessageBox.about(self, brand.APP_NAME, f"<b>{brand.APP_NAME}</b> v{brand.APP_VERSION}<br>"
                          f"{brand.BRAND_NAME} ({brand.BRAND_NAME_EN})<br><br>"
                          "PSD(포토샵) · PNG · JPG · WEBP 파일을 열고 저장할 수 있어요.<br>"
                          "<a href='https://mozzilab.labelpos.com'>mozzilab.labelpos.com</a>")

    def closeEvent(self, e):
        if not self.maybe_save():
            e.ignore()
            return
        self.cfg["fg"] = self.fg_btn.color().name()
        self.cfg["bg"] = self.bg_btn.color().name()
        super().closeEvent(e)


def selftest():
    """설치파일이 제대로 만들어졌는지 점검 (GitHub 자동 빌드에서 사용): 성공하면 0"""
    import tempfile
    d = tempfile.mkdtemp()
    _app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841
    w = PhotoWindow()
    w.set_document(C.Document(320, 240), "test")
    w.doc.add_layer("원")
    p = QPainter(w.doc.layer.image)
    p.setBrush(QColor("#ff6f91"))
    p.drawEllipse(40, 40, 160, 120)
    p.end()
    w.commit("원")
    w.apply_filter(C.grayscale, "흑백")
    w.undo()
    for ext in (".psd", ".mphoto", ".png", ".jpg"):
        C.export_image(w.doc, os.path.join(d, "t" + ext))
    assert len(C.load_document(os.path.join(d, "t.psd")).layers) == 2
    assert len(C.load_document(os.path.join(d, "t.mphoto")).layers) == 2
    w.modified = False
    return 0


def main():
    if "--selftest" in sys.argv:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        return selftest()
    winapi.set_app_id(brand.APP_ID)
    app = QApplication(sys.argv)
    app.setApplicationName(brand.APP_NAME)
    app.setStyleSheet(stylesheet())
    win = PhotoWindow()
    win.show()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and os.path.isfile(args[0]):
        win.open_file(args[0])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
