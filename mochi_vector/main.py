"""모찌벡터 - 일러스트레이터 · 벡터크래프트처럼 쓰는 벡터 디자인 프로그램
도형 · 펜(베지어 곡선) · 문자 · 그룹 · 정렬 · 패스파인더 · SVG/PDF/PNG"""
import json
import os
import sys

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
# 모찌랩 프로그램들이 함께 쓰는 코드(로그인·광고·디자인)는 ../shared 폴더에 있다
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared"))

from PySide6.QtCore import QMarginsF, QMimeData, QRectF, QSizeF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import (QAction, QColor, QFont, QImage, QKeySequence, QPageLayout, QPageSize,  # noqa: E402
                           QPainter, QPdfWriter)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,  # noqa: E402
                               QDoubleSpinBox, QFileDialog, QFontComboBox, QFormLayout, QGraphicsItem,
                               QGridLayout, QHBoxLayout, QInputDialog, QLabel, QListWidget,
                               QListWidgetItem, QMessageBox, QScrollArea, QSpinBox, QVBoxLayout, QWidget)

import brand  # noqa: E402
import svg_io  # noqa: E402
import winapi  # noqa: E402
from app_shell import MozziWindow  # noqa: E402
from editor_kit import (VECTOR_PRESETS, ColorButton, NewDocDialog, Panel, SliderSpin, StartPage,  # noqa: E402
                        ToolPalette, editor_qss, mini_button, push_recent, vsep)
from ui import px, stylesheet  # noqa: E402
from vector_items import (GroupItem, ImageItem, ShapeItem, TextItem, cstr,  # noqa: E402
                          item_from_dict, leaves, path_item_from_scene_path, to_path_item)
from view import VView  # noqa: E402

TOOLS = [
    ("select", "선택", "select", "V"), ("direct", "직접 선택 (점 편집)", "direct", "A"),
    ("pen", "펜 (클릭 = 직선, 드래그 = 곡선)", "penpath", "P"), ("pencil", "연필 (자유 곡선)", "pencil", "N"),
    ("text", "문자", "text", "T"), ("line", "선", "line", "\\"),
    None,
    ("rect", "사각형", "rect", "M"), ("roundrect", "둥근 사각형", "roundrect", "M"),
    ("ellipse", "타원", "ellipse", "L"), ("polygon", "다각형", "polygon", "Y"),
    ("star", "별", "star", "Y"), ("image", "이미지 넣기", "image", ""),
    None,
    ("eyedrop", "스포이드 (모양 복사)", "eyedrop", "I"), ("zoom", "돋보기", "zoom", "Z"),
    ("hand", "손 (화면 이동)", "hand", "H"),
]
HINTS = {
    "select": "클릭 = 선택 · Shift+클릭 = 여러 개 · 모서리 □ = 크기 · 위쪽 ● = 회전 (Shift = 15°)",
    "direct": "□ 점을 끌어서 모양 바꾸기 · ● 손잡이 = 곡선 (Alt = 한쪽만) · Delete = 점 삭제",
    "pen": "클릭 = 직선 점 · 드래그 = 곡선 점 · 첫 점 클릭 = 닫기 · Enter/Esc = 끝",
    "pencil": "누른 채 그리면 부드러운 곡선이 돼요 (시작점으로 돌아오면 닫힌 도형)",
    "text": "빈 곳 클릭 = 새 문자 · 문자 클릭 = 고치기 · Esc = 편집 끝",
    "line": "드래그해서 선 긋기 (Shift = 45° 단위)",
    "rect": "드래그 (Shift = 정사각형, Alt = 가운데부터) · 클릭 = 100×100",
    "roundrect": "드래그 (Shift = 정사각형) · 모서리 둥글기는 오른쪽 속성에서",
    "ellipse": "드래그 (Shift = 정원, Alt = 가운데부터)",
    "polygon": "드래그 · 변의 개수는 오른쪽 속성에서", "star": "드래그 · 꼭짓점 수/안쪽 비율은 오른쪽 속성에서",
    "eyedrop": "개체를 클릭하면 그 색·선 모양을 선택한 개체에 복사해요",
    "zoom": "클릭 = 확대 · Alt+클릭 = 축소", "hand": "드래그해서 화면 이동 (Space+드래그도 돼요)",
}


class PropsPanel(QWidget):
    """오른쪽 '속성' : 위치/크기, 칠/선, 도형 옵션, 글꼴"""

    def __init__(self, ed):
        super().__init__()
        self.ed = ed
        self._busy = False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(px(6))

        g = QGridLayout()
        g.setSpacing(px(4))
        self.x, self.y, self.w, self.h = (self._dspin(-100000, 100000) for _ in range(4))
        self.rot = self._dspin(-360, 360, " °")
        for i, (lab, wd) in enumerate((("X", self.x), ("Y", self.y), ("W", self.w), ("H", self.h))):
            g.addWidget(QLabel(lab), i // 2, (i % 2) * 2)
            g.addWidget(wd, i // 2, (i % 2) * 2 + 1)
            wd.editingFinished.connect(self._geometry_edited)
        g.addWidget(QLabel("회전"), 2, 0)
        g.addWidget(self.rot, 2, 1)
        self.rot.editingFinished.connect(self._rotation_edited)
        self.keep = QCheckBox("비율 유지")
        g.addWidget(self.keep, 2, 2, 1, 2)
        v.addLayout(g)

        f = QFormLayout()
        f.setSpacing(px(4))
        row = QHBoxLayout()
        self.fill = ColorButton("#ff6f91", none_ok=True, tip="칠 (안쪽 색) · '색 없음' 가능")
        self.grad = QCheckBox("그레이디언트")
        self.fill2 = ColorButton("#7c6cf0", tip="그레이디언트 끝 색")
        self.grad_angle = QSpinBox()
        self.grad_angle.setRange(-180, 180)
        self.grad_angle.setSuffix("°")
        self.grad_angle.setToolTip("그레이디언트 방향")
        for wd in (self.fill, self.grad, self.fill2, self.grad_angle):
            row.addWidget(wd)
        row.addStretch(1)
        f.addRow("칠", row)
        row = QHBoxLayout()
        self.stroke = ColorButton("#3b2f2f", none_ok=True, tip="선 색 · '색 없음' 가능")
        self.stroke_w = QDoubleSpinBox()
        self.stroke_w.setRange(0, 500)
        self.stroke_w.setDecimals(1)
        self.stroke_w.setValue(2)
        self.stroke_w.setSuffix(" pt")
        self.dash = QComboBox()
        self.dash.addItems(["실선", "파선", "점선"])
        self.join = QComboBox()
        self.join.addItems(["각진 끝", "둥근 끝"])
        for wd in (self.stroke, self.stroke_w):
            row.addWidget(wd)
        row.addStretch(1)
        f.addRow("선", row)
        row = QHBoxLayout()
        row.addWidget(self.dash)
        row.addWidget(self.join)
        f.addRow("", row)
        self.opacity = SliderSpin("", 0, 100, 100, " %", 110)
        f.addRow("불투명도", self.opacity)
        v.addLayout(f)

        self.shape_box = QWidget()
        sf = QFormLayout(self.shape_box)
        sf.setContentsMargins(0, 0, 0, 0)
        self.rx = self._dspin(0, 10000)
        self.sides = QSpinBox()
        self.sides.setRange(3, 60)
        self.sides.setValue(6)
        self.points = QSpinBox()
        self.points.setRange(3, 60)
        self.points.setValue(5)
        self.inner = QSpinBox()
        self.inner.setRange(5, 95)
        self.inner.setValue(45)
        self.inner.setSuffix(" %")
        self.lbl_rx, self.lbl_sides, self.lbl_points, self.lbl_inner = (QLabel(t) for t in
                                                                         ("모서리 둥글기", "변의 개수", "꼭짓점 수", "안쪽 비율"))
        sf.addRow(self.lbl_rx, self.rx)
        sf.addRow(self.lbl_sides, self.sides)
        sf.addRow(self.lbl_points, self.points)
        sf.addRow(self.lbl_inner, self.inner)
        v.addWidget(self.shape_box)

        self.text_box = QWidget()
        tf = QFormLayout(self.text_box)
        tf.setContentsMargins(0, 0, 0, 0)
        self.font = QFontComboBox()
        self.font.setCurrentFont(QFont("Malgun Gothic"))
        self.size = self._dspin(1, 2000, " pt")
        self.size.setValue(36)
        self.bold = QCheckBox("굵게")
        self.italic = QCheckBox("기울임")
        tf.addRow("글꼴", self.font)
        row = QHBoxLayout()
        row.addWidget(self.size)
        row.addWidget(self.bold)
        row.addWidget(self.italic)
        tf.addRow("크기", row)
        v.addWidget(self.text_box)
        self.info = QLabel("")
        self.info.setStyleSheet("color:#a9a4ad;")
        self.info.setWordWrap(True)
        v.addWidget(self.info)

        for b in (self.fill, self.fill2, self.stroke):
            b.colorChanged.connect(lambda _c: self._style_edited())
        self.grad.toggled.connect(lambda _v: self._style_edited())
        self.grad_angle.valueChanged.connect(lambda _v: self._style_edited(later=True))
        self.stroke_w.valueChanged.connect(lambda _v: self._style_edited(later=True))
        self.dash.activated.connect(lambda _i: self._style_edited())
        self.join.activated.connect(lambda _i: self._style_edited())
        self.opacity.valueChanged.connect(lambda _v: self._style_edited(later=True))
        for wd in (self.rx, self.sides, self.points, self.inner, self.size):
            wd.valueChanged.connect(lambda _v: self._params_edited(later=True))
        self.font.currentFontChanged.connect(lambda _f: self._params_edited())
        self.bold.toggled.connect(lambda _v: self._params_edited())
        self.italic.toggled.connect(lambda _v: self._params_edited())
        self.commit_timer = QTimer(self, singleShot=True, interval=600)
        self.commit_timer.timeout.connect(lambda: self.ed.commit(self._pending or "속성"))
        self._pending = None
        self.refresh()

    def _dspin(self, lo, hi, suffix=""):
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setDecimals(1)
        s.setSuffix(suffix)
        s.setKeyboardTracking(False)
        return s

    # 기본 스타일 (선택이 없을 때 새 도형에 쓰는 값)
    def current_style(self):
        return {"fill": cstr(self.fill.color()), "fill2": cstr(self.fill2.color()) if self.grad.isChecked() else None,
                "grad_angle": self.grad_angle.value(), "stroke": cstr(self.stroke.color()),
                "stroke_w": self.stroke_w.value(), "dash": self.dash.currentIndex(),
                "join": self.join.currentIndex(), "opacity": self.opacity.value() / 100}

    def stroke_color(self):
        return self.stroke.color()

    def fill_open_paths(self):
        return False

    def default_rx(self):
        return self.rx.value() or 16

    def default_sides(self):
        return self.sides.value()

    def default_points(self):
        return self.points.value()

    # 선택 → 패널에 표시
    def refresh(self):
        self._busy = True
        sel = self.ed.view.selected() if hasattr(self.ed, "view") else []
        lf = None
        for it in sel:
            ls = leaves(it)
            if ls:
                lf = ls[0]
                break
        if lf is not None:
            s = lf.style
            self.fill.set_color(s.get("fill"))
            self.grad.setChecked(bool(s.get("fill2")))
            if s.get("fill2"):
                self.fill2.set_color(s["fill2"])
            self.grad_angle.setValue(int(s.get("grad_angle", 0)))
            self.stroke.set_color(s.get("stroke"))
            self.stroke_w.setValue(s.get("stroke_w", 0))
            self.dash.setCurrentIndex(s.get("dash", 0))
            self.join.setCurrentIndex(s.get("join", 0))
            self.opacity.setValue(round(s.get("opacity", 1) * 100))
        kind = lf.kind if lf is not None else None
        tool = self.ed.view.tool if hasattr(self.ed, "view") else ""
        show = {"rx": kind == "rect" or (lf is None and tool == "roundrect"),
                "sides": kind == "polygon" or (lf is None and tool == "polygon"),
                "star": kind == "star" or (lf is None and tool == "star")}
        for w in (self.lbl_rx, self.rx):
            w.setVisible(show["rx"])
        for w in (self.lbl_sides, self.sides):
            w.setVisible(show["sides"])
        for w in (self.lbl_points, self.points, self.lbl_inner, self.inner):
            w.setVisible(show["star"])
        self.shape_box.setVisible(any(show.values()))
        if isinstance(lf, ShapeItem):
            self.rx.setValue(lf.params["rx"])
            self.sides.setValue(int(lf.params["sides"]))
            self.points.setValue(int(lf.params["points"]))
            self.inner.setValue(round(lf.params["inner"] * 100))
        self.text_box.setVisible(isinstance(lf, TextItem) or (lf is None and tool == "text"))
        if isinstance(lf, TextItem):
            self.font.setCurrentFont(QFont(lf.params["family"]))
            self.size.setValue(lf.params["size"])
            self.bold.setChecked(lf.params["bold"])
            self.italic.setChecked(lf.params["italic"])
        for w in (self.x, self.y, self.w, self.h, self.rot):
            w.setEnabled(bool(sel))
        n = len(sel)
        if n == 0:
            self.info.setText("선택한 개체 없음 — 여기서 정한 색/선이 새로 그리는 도형에 쓰여요.")
        elif n == 1:
            it = sel[0]
            self.info.setText(f"{it.name}" + (f" · 개체 {len(leaves(it))}개" if isinstance(it, GroupItem) else ""))
        else:
            self.info.setText(f"{n}개 선택됨")
        self._busy = False
        self.update_geometry()

    def update_geometry(self):
        if not hasattr(self.ed, "view"):
            return
        sel = self.ed.view.selected()
        self._busy = True
        if sel:
            r = self.ed.view.selection_rect(sel)
            for wd, val in ((self.x, r.x()), (self.y, r.y()), (self.w, r.width()), (self.h, r.height())):
                wd.blockSignals(True)
                wd.setValue(val)
                wd.blockSignals(False)
            self.rot.setValue(leaves(sel[0])[0].angle if len(sel) == 1 and leaves(sel[0]) else 0)
        self._busy = False

    # 패널 → 선택한 개체
    def _schedule(self, name, later):
        self._pending = name
        if later:
            self.commit_timer.start()
        else:
            self.commit_timer.stop()
            self.ed.commit(name)

    def _style_edited(self, later=False):
        if self._busy:
            return
        st = self.current_style()
        sel = self.ed.view.selected()
        for it in sel:
            for lf in leaves(it):
                if isinstance(lf, TextItem):
                    lf.style.update(fill=st["fill"] or "#ff000000", opacity=st["opacity"])
                elif isinstance(lf, ImageItem):
                    lf.style["opacity"] = st["opacity"]
                else:
                    lf.style.update(st)
                lf.apply_style()
        if sel:
            self._schedule("칠 / 선", later)

    def _params_edited(self, later=False):
        if self._busy:
            return
        sel = self.ed.view.selected()
        changed = False
        for it in sel:
            for lf in leaves(it):
                if isinstance(lf, ShapeItem) and lf.kind in ("rect", "polygon", "star"):
                    lf.params.update(rx=self.rx.value(), sides=self.sides.value(), points=self.points.value(),
                                     inner=self.inner.value() / 100)
                    lf.rebuild()
                    changed = True
                elif isinstance(lf, TextItem):
                    c = lf.center_scene()
                    lf.params.update(family=self.font.currentFont().family(), size=self.size.value(),
                                     bold=self.bold.isChecked(), italic=self.italic.isChecked())
                    lf.rebuild()
                    lf.set_angle(lf.angle)
                    lf.set_center_scene(c)
                    changed = True
        if changed:
            self.ed.view.viewport().update()
            self._schedule("도형 옵션", later)

    def _geometry_edited(self):
        if self._busy or not self.ed.view.selected():
            return
        r = self.ed.view.selection_rect()
        w, h = self.w.value(), self.h.value()
        if self.keep.isChecked() and r.width() and r.height():
            if abs(w - r.width()) > 1e-6:
                h = r.height() * w / r.width()
            elif abs(h - r.height()) > 1e-6:
                w = r.width() * h / r.height()
        self.ed.view.apply_frame(QRectF(self.x.value(), self.y.value(), max(0.1, w), max(0.1, h)))
        self.ed.commit("위치 / 크기")

    def _rotation_edited(self):
        sel = self.ed.view.selected()
        if self._busy or not sel:
            return
        cur = leaves(sel[0])[0].angle if len(sel) == 1 and leaves(sel[0]) else 0
        self.ed.view.rotate_selection(self.rot.value() - cur)
        self.ed.commit("회전")


class ExportPngDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("PNG 로 내보내기")
        f = QFormLayout(self)
        self.scale = QComboBox()
        self.scale.addItems(["1배 (원래 크기)", "2배 (선명하게)", "3배", "4배 (아주 크게)"])
        self.scale.setCurrentIndex(1)
        self.transparent = QCheckBox("배경 투명하게")
        self.only_sel = QCheckBox("선택한 개체만")
        f.addRow("크기", self.scale)
        f.addRow("", self.transparent)
        f.addRow("", self.only_sel)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("내보내기")
        bb.button(QDialogButtonBox.Cancel).setText("취소")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        f.addRow(bb)


class VectorWindow(MozziWindow):
    def __init__(self):
        super().__init__({"recent": [], "tool": "select"})
        self.doc_w, self.doc_h = 595, 842
        self.doc_path = ""
        self.doc_title = "제목 없음"
        self.history = []
        self.hindex = -1
        self.modified = False
        self.has_doc = False
        self.setAcceptDrops(True)

        self.add_tool("새로 만들기", "newdoc", lambda: self.new_document(), tip="새 문서 (Ctrl+N)")
        self.add_tool("열기", "folder", lambda: self.open_file(), tip="열기 (Ctrl+O) · SVG 도 열려요")
        self.add_tool("저장", "save", self.save, tip="저장 (Ctrl+S)")
        self.add_tool("내보내기", "export", self.export, tip="SVG · PDF · PNG 로 내보내기 (Ctrl+Shift+E)")
        self.add_separator()
        self.add_tool("실행 취소", "undo", self.undo, tip="실행 취소 (Ctrl+Z)")
        self.add_tool("다시 실행", "redo", self.redo, tip="다시 실행 (Ctrl+Y)")
        self.add_separator()
        self.add_tool("그룹", "group", self.group, tip="묶기 (Ctrl+G)")
        self.add_tool("그룹 풀기", "ungroup", self.ungroup, tip="풀기 (Ctrl+Shift+G)")

        self.start = StartPage(brand.APP_NAME, "일러스트레이터처럼 로고 · 아이콘 · 포스터를 그려요 · SVG/PDF 저장",
                               VECTOR_PRESETS, "#2f9be8")
        self.start.newRequested.connect(lambda w, h: self.new_document(w, h))
        self.start.openRequested.connect(lambda: self.open_file())
        self.start.recentRequested.connect(self.open_file)
        self.start.set_recent(self.cfg.get("recent", []))
        self.body.addWidget(self.start)
        self.body.addWidget(self._build_editor())
        self._build_menus()
        self.set_tool(self.cfg.get("tool") or "select")
        self._update_enabled()

    # ---------- 화면 ----------
    def _build_editor(self):
        ed = QWidget()
        ed.setObjectName("editor")
        ed.setAttribute(Qt.WA_StyledBackground)
        ed.setStyleSheet(editor_qss())
        v = QVBoxLayout(ed)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        self.view = VView(self)
        opt = QWidget()
        opt.setObjectName("optbar")
        opt.setAttribute(Qt.WA_StyledBackground)
        oh = QHBoxLayout(opt)
        oh.setContentsMargins(px(10), px(5), px(10), px(5))
        self.tool_label = QLabel()
        self.tool_label.setStyleSheet("font-weight:bold; color:#7cc4ff;")
        self.hint = QLabel()
        self.hint.setStyleSheet("color:#a9a4ad;")
        oh.addWidget(self.tool_label)
        oh.addWidget(vsep())
        oh.addWidget(self.hint, 1)
        for ic, tip, fn in (("alignl", "왼쪽 맞춤", lambda: self.align("l")), ("alignc", "가로 가운데", lambda: self.align("c")),
                            ("alignr", "오른쪽 맞춤", lambda: self.align("r")), ("alignt", "위쪽 맞춤", lambda: self.align("t")),
                            ("alignm", "세로 가운데", lambda: self.align("m")), ("alignb", "아래쪽 맞춤", lambda: self.align("b")),
                            ("disth", "가로 간격 똑같이", lambda: self.distribute(True)),
                            ("distv", "세로 간격 똑같이", lambda: self.distribute(False))):
            oh.addWidget(mini_button(ic, tip + " (개체 1개면 대지 기준)", fn, size=20))
        v.addWidget(opt)
        row = QHBoxLayout()
        row.setSpacing(0)
        v.addLayout(row, 1)
        self.palette = ToolPalette(TOOLS)
        self.palette.changed.connect(self.set_tool)
        row.addWidget(self.palette)
        row.addWidget(self.view, 1)

        side = QWidget()
        side.setObjectName("sidebar")
        side.setAttribute(Qt.WA_StyledBackground)
        side.setFixedWidth(px(290))
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)
        self.props = PropsPanel(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(self.props)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        sv.addWidget(Panel("속성", scroll, stretch=True), 5)

        pf = QWidget()
        ph = QHBoxLayout(pf)
        ph.setContentsMargins(0, 0, 0, 0)
        for ic, tip, mode in (("union", "합치기", "union"), ("subtract", "앞 개체로 빼기", "minus"),
                              ("intersect", "겹친 부분만", "intersect"), ("exclude", "겹친 부분 빼기", "exclude")):
            ph.addWidget(mini_button(ic, f"패스파인더: {tip} (2개 이상 선택)", lambda m=mode: self.pathfinder(m), size=22))
        ph.addStretch(1)
        for ic, tip, fn in (("fliph", "좌우 뒤집기", lambda: self._transform(lambda: self.view.flip_selection(True), "좌우 뒤집기")),
                            ("flipv", "상하 뒤집기", lambda: self._transform(lambda: self.view.flip_selection(False), "상하 뒤집기")),
                            ("rotr", "90° 회전", lambda: self._transform(lambda: self.view.rotate_selection(90), "90° 회전"))):
            ph.addWidget(mini_button(ic, tip, fn, size=22))
        sv.addWidget(Panel("패스파인더 · 변형", pf))

        lw = QWidget()
        lv = QVBoxLayout(lw)
        lv.setContentsMargins(0, 0, 0, 0)
        self.obj_list = QListWidget()
        self.obj_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.obj_list.itemSelectionChanged.connect(self._list_selected)
        self.obj_list.itemChanged.connect(self._list_item_changed)
        self.obj_list.setToolTip("체크 = 보이기/숨기기 · 두 번 클릭 = 이름 바꾸기")
        lv.addWidget(self.obj_list, 1)
        bh = QHBoxLayout()
        for ic, tip, fn in (("up", "앞으로 (Ctrl+])", lambda: self.arrange("forward")),
                            ("down", "뒤로 (Ctrl+[)", lambda: self.arrange("backward")),
                            ("front", "맨 앞으로 (Ctrl+Shift+])", lambda: self.arrange("front")),
                            ("back", "맨 뒤로 (Ctrl+Shift+[)", lambda: self.arrange("back")),
                            ("lock", "잠금 / 풀기 (Ctrl+2)", self.toggle_lock),
                            ("duplicate", "복제 (Ctrl+D)", self.duplicate),
                            ("trash", "삭제 (Delete)", self.delete_selected)):
            bh.addWidget(mini_button(ic, tip, fn))
        bh.addStretch(1)
        lv.addLayout(bh)
        sv.addWidget(Panel("레이어 (개체)", lw, stretch=True), 4)
        row.addWidget(side)

        self.view.scene().selectionChanged.connect(self.selection_changed)
        self.pos_label = QLabel("")
        self.zoom_label = QLabel("")
        self.statusBar().addPermanentWidget(self.pos_label)
        self.statusBar().addPermanentWidget(self.zoom_label)
        self.view.cursorMoved.connect(lambda x, y: self.pos_label.setText(f"  X {x:.0f}  Y {y:.0f}  "))
        self.view.zoomChanged.connect(lambda z: self.zoom_label.setText(f"  {round(z * 100)}%  ·  대지 {self.doc_w:g} × {self.doc_h:g}  "))
        self.view.message.connect(lambda m: self.statusBar().showMessage(m, 4000))
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
        act(m, "열기… (모찌벡터 · SVG)", lambda: self.open_file(), "Ctrl+O", False)
        self.recent_menu = m.addMenu("최근 파일")
        self.recent_menu.aboutToShow.connect(self._fill_recent)
        act(m, "가져오기 (SVG · 이미지를 지금 문서에)…", self.import_into, "Ctrl+Shift+P")
        m.addSeparator()
        act(m, "저장", self.save, "Ctrl+S")
        act(m, "다른 이름으로 저장…", self.save_as, "Ctrl+Shift+S")
        act(m, "내보내기 (SVG · PDF · PNG)…", self.export, "Ctrl+Shift+E")
        m.addSeparator()
        act(m, "대지 크기…", self.artboard_size)
        act(m, "닫기", self.close_document, "Ctrl+W")
        act(m, "끝내기", self.close, "Ctrl+Q", False)

        m = mb.addMenu("편집(&E)")
        act(m, "실행 취소", self.undo, "Ctrl+Z")
        act(m, "다시 실행", self.redo, "Ctrl+Y")
        act(m, "다시 실행 ", self.redo, "Ctrl+Shift+Z")
        m.addSeparator()
        act(m, "잘라내기", self.cut, "Ctrl+X")
        act(m, "복사", self.copy, "Ctrl+C")
        act(m, "붙여넣기", self.paste, "Ctrl+V")
        act(m, "제자리에 붙여넣기", lambda: self.paste(in_place=True), "Ctrl+Shift+V")
        act(m, "복제", self.duplicate, "Ctrl+D")
        act(m, "삭제", self.delete_selected, None)
        m.addSeparator()
        act(m, "모두 선택", self.select_all, "Ctrl+A")
        act(m, "선택 해제", lambda: self.view.scene().clearSelection(), "Ctrl+Shift+A")

        m = mb.addMenu("개체(&O)")
        act(m, "그룹", self.group, "Ctrl+G")
        act(m, "그룹 풀기", self.ungroup, "Ctrl+Shift+G")
        m.addSeparator()
        sm = m.addMenu("정돈")
        act(sm, "맨 앞으로", lambda: self.arrange("front"), "Ctrl+Shift+]")
        act(sm, "앞으로", lambda: self.arrange("forward"), "Ctrl+]")
        act(sm, "뒤로", lambda: self.arrange("backward"), "Ctrl+[")
        act(sm, "맨 뒤로", lambda: self.arrange("back"), "Ctrl+Shift+[")
        am = m.addMenu("정렬")
        for k, t in (("l", "왼쪽"), ("c", "가로 가운데"), ("r", "오른쪽"), ("t", "위쪽"), ("m", "세로 가운데"), ("b", "아래쪽")):
            act(am, t, lambda k=k: self.align(k))
        am.addSeparator()
        act(am, "가로 간격 똑같이", lambda: self.distribute(True))
        act(am, "세로 간격 똑같이", lambda: self.distribute(False))
        tm = m.addMenu("변형")
        act(tm, "좌우 뒤집기", lambda: self._transform(lambda: self.view.flip_selection(True), "좌우 뒤집기"))
        act(tm, "상하 뒤집기", lambda: self._transform(lambda: self.view.flip_selection(False), "상하 뒤집기"))
        act(tm, "90° 회전", lambda: self._transform(lambda: self.view.rotate_selection(90), "90° 회전"))
        act(tm, "회전…", self.rotate_dialog, "Ctrl+Alt+R")
        m.addSeparator()
        act(m, "패스로 바꾸기 (점 편집 가능)", self.convert_to_path, "Ctrl+8")
        act(m, "윤곽선 만들기 (문자 → 도형)", self.convert_to_path, "Ctrl+Shift+O")
        pm = m.addMenu("패스파인더")
        for mode, t in (("union", "합치기"), ("minus", "앞 개체로 빼기"), ("intersect", "겹친 부분만"), ("exclude", "겹친 부분 빼기")):
            act(pm, t, lambda mode=mode: self.pathfinder(mode))
        m.addSeparator()
        act(m, "잠금 / 풀기", self.toggle_lock, "Ctrl+2")
        act(m, "모두 잠금 풀기", self.unlock_all, "Ctrl+Alt+2")
        act(m, "숨기기", self.hide_selected, "Ctrl+3")
        act(m, "모두 보이기", self.show_all, "Ctrl+Alt+3")

        m = mb.addMenu("보기(&V)")
        act(m, "확대", lambda: self.view.zoom_by(1.25), "Ctrl+=")
        act(m, "확대 ", lambda: self.view.zoom_by(1.25), "Ctrl++")
        act(m, "축소", lambda: self.view.zoom_by(0.8), "Ctrl+-")
        act(m, "대지에 맞추기", self.view.fit, "Ctrl+0")
        act(m, "실제 크기 (100%)", self.view.actual_size, "Ctrl+1")

        m = mb.addMenu("도움말(&H)")
        act(m, "단축키 안내", self.show_shortcuts, "F1", False)
        act(m, "업데이트 확인", lambda: self.updater.check(manual=True), None, False)
        act(m, f"{brand.APP_NAME} 정보", self.about, None, False)

    def _fill_recent(self):
        self.recent_menu.clear()
        for p in self.cfg.get("recent", []):
            if os.path.exists(p):
                self.recent_menu.addAction(os.path.basename(p), lambda p=p: self.open_file(p))
        if self.recent_menu.isEmpty():
            self.recent_menu.addAction("(없음)").setEnabled(False)

    def _update_enabled(self):
        for a in self.doc_actions:
            a.setEnabled(self.has_doc)

    # ---------- 도구 ----------
    def set_tool(self, key):
        names = {t[0]: t[1] for t in TOOLS if t}
        if key not in names:
            key = "select"
        if key == "image":
            self.palette.select(self.view.tool)
            self.import_into(images_only=True)
            return
        if key != "direct":                 # 직접 선택에서 고른 그룹 안 개체는 다시 그룹이 대신 선택되게
            for it in self.view.objects():
                if isinstance(it, GroupItem):
                    for lf in it.childItems():
                        lf.setSelected(False)
                        lf.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.palette.select(key)
        self.view.set_tool(key)
        self.tool_label.setText(names[key].split(" (")[0])
        self.hint.setText(HINTS.get(key, ""))
        self.cfg["tool"] = key
        self.props.refresh()

    def tool_shortcut(self, letter):
        k = self.palette.tool_for_key(letter, self.view.tool)
        if k:
            self.set_tool(k)

    def next_z(self):
        objs = self.view.objects()
        return (objs[-1].zValue() + 1) if objs else 1

    # ---------- 문서 ----------
    def _update_title(self):
        if self.has_doc:
            self.setWindowTitle(f"{self.doc_title}{' *' if self.modified else ''} - {brand.APP_NAME}")
        else:
            self.setWindowTitle(brand.APP_NAME)

    def maybe_save(self):
        if not self.has_doc or not self.modified:
            return True
        r = QMessageBox.question(self, brand.APP_NAME, f"'{self.doc_title}' 의 바뀐 내용을 저장할까요?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.save()
        return r == QMessageBox.Discard

    def doc_dict(self):
        return {"app": "MochiVector", "version": 1, "width": self.doc_w, "height": self.doc_h,
                "items": [it.to_dict() for it in self.view.objects()]}

    def load_dict(self, d):
        self.view.end_text_edit()
        self.view.pen_item = None
        self.view.clear_objects()
        self.doc_w, self.doc_h = d.get("width", 595), d.get("height", 842)
        if self.view.artboard is None or self.view.artboard.rect().size() != QSizeF(self.doc_w, self.doc_h):
            self.view.set_artboard(self.doc_w, self.doc_h)
        for i, idata in enumerate(d.get("items", [])):
            it = item_from_dict(idata)
            if it is not None:
                it.setZValue(i + 1)
                self.view.scene().addItem(it)
        self.view.zoomChanged.emit(self.view.zoom())

    def start_document(self, d, title, path=""):
        self.view.set_artboard(d.get("width", 595), d.get("height", 842))
        self.load_dict(d)
        self.doc_title, self.doc_path = title, path
        self.has_doc = True
        self.history = [("열기" if path else "새 문서", json.dumps(d))]
        self.hindex = 0
        self.modified = False
        self.body.setCurrentIndex(1)
        QTimer.singleShot(0, self.view.fit)
        self.view.fit()
        self.refresh_objects()
        self.props.refresh()
        self._update_enabled()
        self._update_title()
        self.view.setFocus()

    def new_document(self, w=0, h=0):
        if not self.maybe_save():
            return
        if not w:
            dlg = NewDocDialog(self, VECTOR_PRESETS, self.doc_w if self.has_doc else 595,
                               self.doc_h if self.has_doc else 842, with_background=False)
            if dlg.exec() != NewDocDialog.Accepted:
                return
            w, h, _ = dlg.values()
        self.start_document({"width": w, "height": h, "items": []}, "제목 없음")

    def open_file(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "열기", self.cfg.start_dir(),
                                                  "모찌벡터 · SVG (*.mvec *.svg);;모찌벡터 (*.mvec);;SVG (*.svg);;모든 파일 (*.*)")
            if not path:
                return
        if not self.maybe_save():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if path.lower().endswith(".svg"):
                items, w, h = svg_io.import_svg(path)
                d = {"width": round(w, 2), "height": round(h, 2), "items": [it.to_dict() for it in items]}
                save_path = ""
            else:
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if d.get("app") != "MochiVector":
                    raise ValueError("모찌벡터 파일이 아니에요.")
                save_path = path
        except Exception as e:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, brand.APP_NAME, f"파일을 열 수 없어요.\n\n{e}")
            return
        QApplication.restoreOverrideCursor()
        self.cfg.remember_dir(path)
        push_recent(self.cfg, path)
        self.start.set_recent(self.cfg.get("recent", []))
        self.start_document(d, os.path.basename(path), save_path)
        if path.lower().endswith(".svg"):
            self.statusBar().showMessage(f"SVG 에서 개체 {len(d['items'])}개를 불러왔어요. 저장하면 .mvec 로 저장돼요.", 8000)

    def import_into(self, images_only=False):
        if not self.has_doc:
            return
        flt = "이미지 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)" if images_only else \
            "SVG · 이미지 (*.svg *.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        paths, _ = QFileDialog.getOpenFileNames(self, "가져오기", self.cfg.start_dir(), flt)
        for p in paths:
            self.place_file(p)

    def place_file(self, path, at=None):
        try:
            if path.lower().endswith(".svg"):
                items, _, _ = svg_io.import_svg(path)
                if not items:
                    raise svg_io.SvgError("그릴 수 있는 개체가 없어요.")
                g = GroupItem(os.path.splitext(os.path.basename(path))[0]) if len(items) > 1 else None
                z = self.next_z()
                if g:
                    self.view.scene().addItem(g)
                    for it in items:
                        self.view.scene().addItem(it)
                        g.add(it)
                    g.setZValue(z)
                    new = [g]
                else:
                    items[0].setZValue(z)
                    self.view.scene().addItem(items[0])
                    new = items
            else:
                img = QImage(path)
                if img.isNull():
                    raise ValueError("이미지를 읽을 수 없어요.")
                if img.width() > self.doc_w or img.height() > self.doc_h:
                    img = img.scaled(int(self.doc_w), int(self.doc_h), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                it = ImageItem.from_qimage(img, os.path.splitext(os.path.basename(path))[0])
                it.setPos((self.doc_w - it.w) / 2, (self.doc_h - it.h) / 2)
                it.setZValue(self.next_z())
                self.view.scene().addItem(it)
                new = [it]
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, brand.APP_NAME, f"가져오지 못했어요.\n\n{e}")
            return
        self.cfg.remember_dir(path)
        self.view.scene().clearSelection()
        for it in new:
            it.setSelected(True)
        if at is not None:
            r = self.view.selection_rect()
            for it in new:
                it.moveBy(at.x() - r.center().x(), at.y() - r.center().y())
        self.set_tool("select")
        self.commit("가져오기")

    def close_document(self):
        if not self.maybe_save():
            return
        self.view.clear_objects()
        self.has_doc = False
        self.body.setCurrentIndex(0)
        self.start.set_recent(self.cfg.get("recent", []))
        self._update_enabled()
        self._update_title()

    def save(self):
        if not self.has_doc:
            return False
        if self.doc_path.lower().endswith(".mvec"):
            return self._save_to(self.doc_path)
        return self.save_as()

    def save_as(self):
        base = os.path.splitext(self.doc_title)[0] if self.doc_title != "제목 없음" else "디자인"
        path, _ = QFileDialog.getSaveFileName(self, "저장", os.path.join(self.cfg.start_dir(), base + ".mvec"),
                                              "모찌벡터 (*.mvec)")
        if not path:
            return False
        if not path.lower().endswith(".mvec"):
            path += ".mvec"
        return self._save_to(path)

    def _save_to(self, path):
        self.view.end_text_edit()
        try:
            with open(path + ".part", "w", encoding="utf-8") as f:
                json.dump(self.doc_dict(), f, ensure_ascii=False)
            os.replace(path + ".part", path)
        except OSError as e:
            QMessageBox.warning(self, brand.APP_NAME, f"저장하지 못했어요.\n\n{e}")
            return False
        self.doc_path = path
        self.doc_title = os.path.basename(path)
        self.modified = False
        self._update_title()
        self.cfg.remember_dir(path)
        push_recent(self.cfg, path)
        self.statusBar().showMessage(f"저장했어요: {path}", 5000)
        return True

    def artboard_size(self):
        dlg = NewDocDialog(self, VECTOR_PRESETS, int(self.doc_w), int(self.doc_h), with_background=False, title="대지 크기")
        if dlg.exec() == NewDocDialog.Accepted:
            w, h, _ = dlg.values()
            self.doc_w, self.doc_h = w, h
            self.view.set_artboard(w, h)
            self.view.fit()
            self.commit("대지 크기")

    # ---------- 내보내기 ----------
    def export(self):
        if not self.has_doc:
            return
        self.view.end_text_edit()
        base = os.path.splitext(self.doc_title)[0] if self.doc_title != "제목 없음" else "디자인"
        path, flt = QFileDialog.getSaveFileName(self, "내보내기", os.path.join(self.cfg.start_dir(), base + ".svg"),
                                                "SVG (*.svg);;PDF (*.pdf);;PNG (*.png);;JPG (*.jpg)")
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if not ext:
            ext = "." + flt.split("*.")[1].split(")")[0]
            path += ext
        try:
            if ext == ".svg":
                self.export_svg(path)
            elif ext == ".pdf":
                self.export_pdf(path)
            else:
                dlg = ExportPngDialog(self)
                dlg.transparent.setVisible(ext == ".png")
                if dlg.exec() != QDialog.Accepted:
                    return
                self.export_image(path, dlg.scale.currentIndex() + 1,
                                  dlg.transparent.isChecked() and ext == ".png", dlg.only_sel.isChecked())
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, brand.APP_NAME, f"내보내지 못했어요.\n\n{e}")
            return
        self.cfg.remember_dir(path)
        self.job_done("내보내기 완료", os.path.basename(path), path)

    def export_svg(self, path):
        svg_io.export_svg(self.view.objects(), self.doc_w, self.doc_h, path)

    def _render(self, painter, target, source):
        sc = self.view.scene()
        sel = sc.selectedItems()
        sc.clearSelection()
        self.view.artboard.setVisible(False)
        sc.render(painter, target, source)
        self.view.artboard.setVisible(True)
        for it in sel:
            it.setSelected(True)

    def export_pdf(self, path):
        w = QPdfWriter(path)
        w.setResolution(72)
        w.setPageSize(QPageSize(QSizeF(self.doc_w, self.doc_h), QPageSize.Point, "대지"))
        w.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Point)
        w.setTitle(self.doc_title)
        w.setCreator(f"{brand.APP_NAME} ({brand.BRAND_NAME_EN})")
        p = QPainter(w)
        p.fillRect(QRectF(0, 0, self.doc_w, self.doc_h), Qt.white)
        self._render(p, QRectF(0, 0, self.doc_w, self.doc_h), QRectF(0, 0, self.doc_w, self.doc_h))
        p.end()

    def export_image(self, path, scale=2, transparent=False, only_sel=False):
        src = QRectF(0, 0, self.doc_w, self.doc_h)
        hidden = []
        if only_sel and self.view.selected():
            src = self.view.selection_rect()
            keep = set(self.view.selected())
            for it in self.view.objects():
                if it not in keep and it.isVisible():
                    it.setVisible(False)
                    hidden.append(it)
        img = QImage(max(1, int(src.width() * scale)), max(1, int(src.height() * scale)), QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent if transparent else Qt.white)
        p = QPainter(img)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self._render(p, QRectF(0, 0, img.width(), img.height()), src)
        p.end()
        for it in hidden:
            it.setVisible(True)
        if not img.save(path, quality=-1 if path.lower().endswith(".png") else 95):
            raise OSError("이미지를 저장하지 못했어요.")

    # ---------- 실행 취소 ----------
    def commit(self, name):
        if not self.has_doc:
            return
        self.history = self.history[: self.hindex + 1]
        self.history.append((name, json.dumps(self.doc_dict())))
        if len(self.history) > 60:
            self.history.pop(0)
        self.hindex = len(self.history) - 1
        self.modified = True
        self._update_title()
        self.refresh_objects()
        self.props.refresh()
        self.view.viewport().update()

    def _restore(self, i):
        self.hindex = i
        d = json.loads(self.history[i][1])
        self.load_dict(d)
        self.view.set_artboard(self.doc_w, self.doc_h) if self.view.artboard.rect().size() != QSizeF(self.doc_w, self.doc_h) else None
        self.modified = True
        self._update_title()
        self.refresh_objects()
        self.props.refresh()
        self.statusBar().showMessage(f"되돌림: {self.history[i][0]}", 3000)

    def undo(self):
        self.view.end_text_edit()
        if self.view.pen_item is not None:
            self.view.finish_pen()
        if self.has_doc and self.hindex > 0:
            self._restore(self.hindex - 1)

    def redo(self):
        if self.has_doc and self.hindex < len(self.history) - 1:
            self._restore(self.hindex + 1)

    # ---------- 패널 ----------
    def selection_changed(self):
        self.props.refresh()
        self._sync_list_selection()
        self.view.viewport().update()

    def update_props_geometry(self):
        self.props.update_geometry()

    def refresh_objects(self):
        ol = self.obj_list
        ol.blockSignals(True)
        ol.clear()
        self._list_items = []
        for it in reversed(self.view.objects()):
            label = ("🔒 " if it.locked else "") + it.name + (f"  ({len(leaves(it))})" if isinstance(it, GroupItem) else "")
            li = QListWidgetItem(label)
            li.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            li.setCheckState(Qt.Checked if it.isVisible() else Qt.Unchecked)
            ol.addItem(li)
            self._list_items.append(it)
        ol.blockSignals(False)
        self._sync_list_selection()

    def _sync_list_selection(self):
        ol = self.obj_list
        ol.blockSignals(True)
        sel = set(self.view.selected())
        for i, it in enumerate(getattr(self, "_list_items", [])):
            ol.item(i).setSelected(it in sel)
        ol.blockSignals(False)

    def _list_selected(self):
        sc = self.view.scene()
        sc.blockSignals(True)
        sc.clearSelection()
        for i, it in enumerate(self._list_items):
            if self.obj_list.item(i).isSelected() and not it.locked and it.isVisible():
                it.setSelected(True)
        sc.blockSignals(False)
        self.props.refresh()
        self.view.viewport().update()

    def _list_item_changed(self, li):
        i = self.obj_list.row(li)
        it = self._list_items[i]
        vis = li.checkState() == Qt.Checked
        if vis != it.isVisible():
            it.setVisible(vis)
            if not vis:
                it.setSelected(False)
            self.commit("보이기" if vis else "숨기기")
            return
        name = li.text().replace("🔒 ", "").split("  (")[0].strip()
        if name and name != it.name:
            it.name = name
            self.commit("이름 바꾸기")

    # ---------- 편집 ----------
    def select_all(self):
        if self.view.tool not in ("select", "direct"):
            self.set_tool("select")
        for it in self.view.objects():
            if not it.locked and it.isVisible():
                it.setSelected(True)

    def delete_selected(self):
        sel = self.view.selected()
        if not sel:
            return
        for it in sel:
            par = it.parentItem()
            self.view.remove(it)
            if isinstance(par, GroupItem):
                par.refresh()
                if not par.childItems():
                    self.view.remove(par)
        self.commit("삭제")

    def nudge(self, dx, dy):
        sel = [it for it in self.view.selected() if it.parentItem() is None]
        if not sel:
            return
        for it in sel:
            it.moveBy(dx, dy)
        self.commit("이동")

    def copy(self):
        sel = [it for it in self.view.selected() if it.parentItem() is None]
        if not sel:
            return
        md = QMimeData()
        data = json.dumps({"app": "MochiVector", "items": [it.to_dict() for it in sel]})
        md.setData("application/x-mochivector", data.encode("utf-8"))
        tmp_items = sel
        import tempfile
        svg_path = os.path.join(tempfile.gettempdir(), "mochivector_clip.svg")
        r = self.view.selection_rect(tmp_items)
        svg_io.export_svg(tmp_items, r.right(), r.bottom(), svg_path)
        with open(svg_path, "r", encoding="utf-8") as f:
            md.setText(f.read())
        QApplication.clipboard().setMimeData(md)
        self.statusBar().showMessage(f"{len(sel)}개 복사했어요.", 3000)

    def cut(self):
        self.copy()
        self.delete_selected()

    def paste(self, in_place=False):
        md = QApplication.clipboard().mimeData()
        if md is None:
            return
        if md.hasFormat("application/x-mochivector"):
            d = json.loads(bytes(md.data("application/x-mochivector")).decode("utf-8"))
            self._add_dicts(d["items"], 0 if in_place else 12)
            self.commit("붙여넣기")
        elif md.hasImage():
            img = QImage(md.imageData())
            it = ImageItem.from_qimage(img, "붙여넣은 그림")
            it.setPos((self.doc_w - it.w) / 2, (self.doc_h - it.h) / 2)
            it.setZValue(self.next_z())
            self.view.scene().addItem(it)
            self.view.scene().clearSelection()
            it.setSelected(True)
            self.commit("붙여넣기")
        elif md.hasText() and md.text().lstrip().startswith(("<svg", "<?xml")):
            import tempfile
            p = os.path.join(tempfile.gettempdir(), "mochivector_paste.svg")
            with open(p, "w", encoding="utf-8") as f:
                f.write(md.text())
            self.place_file(p)

    def _add_dicts(self, dicts, offset):
        self.view.scene().clearSelection()
        z = self.next_z()
        for i, dd in enumerate(dicts):
            it = item_from_dict(dd)
            if it is None:
                continue
            it.moveBy(offset, offset)
            it.setZValue(z + i)
            self.view.scene().addItem(it)
            it.setSelected(True)

    def duplicate(self):
        sel = [it for it in self.view.selected() if it.parentItem() is None]
        if sel:
            self._add_dicts([it.to_dict() for it in sel], 12)
            self.commit("복제")

    def eyedrop(self, src):
        lf = leaves(src)[0] if leaves(src) else None
        if lf is None:
            return
        targets = [x for it in self.view.selected() for x in leaves(it) if it is not src]
        if not targets:       # 선택이 없으면 '기본 스타일'로 가져온다
            self.props._busy = True
            s = lf.style
            self.props.fill.set_color(s.get("fill"))
            self.props.stroke.set_color(s.get("stroke"))
            self.props.stroke_w.setValue(s.get("stroke_w", 0))
            self.props._busy = False
            self.statusBar().showMessage("색과 선을 가져왔어요. 다음에 그리는 도형에 쓰여요.", 4000)
            return
        for t in targets:
            if isinstance(t, TextItem):
                t.style.update(fill=lf.style.get("fill") or t.style["fill"])
            elif isinstance(t, ShapeItem):
                t.style.update({k: v for k, v in lf.style.items()})
            t.apply_style()
        self.commit("스포이드")

    def add_text(self, sp):
        p = self.props
        it = TextItem("문자를 입력하세요", p.font.currentFont().family(), p.size.value(), p.bold.isChecked(),
                      p.italic.isChecked())
        fill = p.fill.color() or QColor("#3b2f2f")
        it.style.update(fill=cstr(fill), opacity=p.opacity.value() / 100)
        it.rebuild()
        it.setPos(sp.x(), sp.y() - it.h / 2)
        it.setZValue(self.next_z())
        it.is_new = True
        self.view.scene().addItem(it)
        self.view.scene().clearSelection()
        it.setSelected(True)
        self.view.start_text_edit(it)
        c = it.textCursor()
        c.select(c.SelectionType.Document)
        it.setTextCursor(c)

    # ---------- 개체 ----------
    def group(self):
        sel = [it for it in self.view.selected() if it.parentItem() is None]
        if len(sel) < 2:
            self.statusBar().showMessage("2개 이상 선택해야 묶을 수 있어요.", 4000)
            return
        g = GroupItem("그룹")
        self.view.scene().addItem(g)
        g.setZValue(max(it.zValue() for it in sel))
        for i, it in enumerate(sel):
            it.setSelected(False)
            it.setZValue(i)
            g.add(it)
        self.view.scene().clearSelection()
        g.setSelected(True)
        self.commit("그룹")

    def ungroup(self):
        groups = [it for it in self.view.selected() if isinstance(it, GroupItem)]
        if not groups:
            return
        self.view.scene().clearSelection()
        for g in groups:
            z = g.zValue()
            kids = g.release()
            self.view.remove(g)
            for i, k in enumerate(kids):
                k.setZValue(z + i * 0.001)
                k.setSelected(True)
        self._renumber()
        self.commit("그룹 풀기")

    def _renumber(self):
        for i, it in enumerate(self.view.objects()):
            it.setZValue(i + 1)

    def arrange(self, how):
        objs = self.view.objects()
        sel = set(it for it in self.view.selected() if it.parentItem() is None)
        if not sel:
            return
        if how == "front":
            objs = [o for o in objs if o not in sel] + [o for o in objs if o in sel]
        elif how == "back":
            objs = [o for o in objs if o in sel] + [o for o in objs if o not in sel]
        elif how == "forward":
            for i in range(len(objs) - 2, -1, -1):
                if objs[i] in sel and objs[i + 1] not in sel:
                    objs[i], objs[i + 1] = objs[i + 1], objs[i]
        else:
            for i in range(1, len(objs)):
                if objs[i] in sel and objs[i - 1] not in sel:
                    objs[i], objs[i - 1] = objs[i - 1], objs[i]
        for i, o in enumerate(objs):
            o.setZValue(i + 1)
        self.commit("정돈")

    def _item_rect(self, it):
        return self.view.selection_rect([it])

    def align(self, how):
        sel = [it for it in self.view.selected() if it.parentItem() is None]
        if not sel:
            return
        ref = QRectF(0, 0, self.doc_w, self.doc_h) if len(sel) == 1 else self.view.selection_rect(sel)
        for it in sel:
            r = self._item_rect(it)
            dx = {"l": ref.left() - r.left(), "c": ref.center().x() - r.center().x(), "r": ref.right() - r.right()}.get(how, 0)
            dy = {"t": ref.top() - r.top(), "m": ref.center().y() - r.center().y(), "b": ref.bottom() - r.bottom()}.get(how, 0)
            it.moveBy(dx, dy)
        self.commit("정렬")

    def distribute(self, horizontal):
        sel = [it for it in self.view.selected() if it.parentItem() is None]
        if len(sel) < 3:
            self.statusBar().showMessage("간격을 맞추려면 3개 이상 선택하세요.", 4000)
            return
        rects = {it: self._item_rect(it) for it in sel}
        key = (lambda it: rects[it].center().x()) if horizontal else (lambda it: rects[it].center().y())
        order = sorted(sel, key=key)
        total = sum(rects[it].width() if horizontal else rects[it].height() for it in order)
        first, last = rects[order[0]], rects[order[-1]]
        span = (last.right() - first.left()) if horizontal else (last.bottom() - first.top())
        gap = (span - total) / (len(order) - 1)
        pos = first.left() if horizontal else first.top()
        for it in order:
            r = rects[it]
            if horizontal:
                it.moveBy(pos - r.left(), 0)
                pos += r.width() + gap
            else:
                it.moveBy(0, pos - r.top())
                pos += r.height() + gap
        self.commit("간격 맞춤")

    def _transform(self, fn, name):
        if self.view.selected():
            fn()
            self.commit(name)

    def rotate_dialog(self):
        if not self.view.selected():
            return
        a, ok = QInputDialog.getDouble(self, "회전", "각도 (시계 방향 +)", 45, -360, 360, 1)
        if ok:
            self._transform(lambda: self.view.rotate_selection(a), "회전")

    def convert_to_path(self):
        sel = [it for it in self.view.selected() if it.parentItem() is None]
        done = 0
        for it in sel:
            new = to_path_item(it)
            if new is None or new is it:
                continue
            self.view.remove(it)
            self.view.scene().addItem(new)
            new.setSelected(True)
            done += 1
        if done:
            self.commit("패스로 바꾸기")
            self.statusBar().showMessage("이제 직접 선택 도구(A)로 점을 편집할 수 있어요.", 5000)

    def pathfinder(self, mode):
        sel = [it for it in self.view.selected() if it.parentItem() is None]
        shapes = [it for it in sel if not isinstance(it, ImageItem)]
        if len(shapes) < 2:
            self.statusBar().showMessage("도형을 2개 이상 선택하세요.", 4000)
            return
        paths = [it.scene_shape() for it in shapes]       # 아래 → 위 순서
        if mode == "union":
            res = paths[0]
            for p in paths[1:]:
                res = res.united(p)
            style = shapes[-1].style if not isinstance(leaves(shapes[-1])[0], TextItem) else leaves(shapes[0])[0].style
        elif mode == "minus":
            res = paths[0]
            for p in paths[1:]:
                res = res.subtracted(p)
            style = leaves(shapes[0])[0].style
        elif mode == "intersect":
            res = paths[0]
            for p in paths[1:]:
                res = res.intersected(p)
            style = leaves(shapes[-1])[0].style
        else:
            res = paths[0]
            for p in paths[1:]:
                res = res.united(p).subtracted(res.intersected(p))
            style = leaves(shapes[-1])[0].style
        if res.isEmpty():
            self.statusBar().showMessage("결과가 비어 있어요 (겹치는 부분이 없어요).", 4000)
            return
        style = dict(style)
        if style.get("fill") is None:
            style["fill"] = "#ff6f91"
        z = max(it.zValue() for it in shapes)
        for it in shapes:
            self.view.remove(it)
        new = path_item_from_scene_path(res.simplified(), style, {"union": "합친 도형", "minus": "뺀 도형",
                                                                  "intersect": "교차 도형", "exclude": "제외 도형"}[mode], 1)
        new.setZValue(z)
        self.view.scene().addItem(new)
        self.view.scene().clearSelection()
        new.setSelected(True)
        self.commit("패스파인더")

    def toggle_lock(self):
        sel = [it for it in self.view.selected() if it.parentItem() is None]
        if sel:
            for it in sel:
                it.set_locked(True)
            self.commit("잠금")
        else:
            cur = self.obj_list.currentRow()
            if 0 <= cur < len(self._list_items):
                it = self._list_items[cur]
                it.set_locked(not it.locked)
                self.commit("잠금 풀기" if not it.locked else "잠금")

    def unlock_all(self):
        for it in self.view.objects():
            it.set_locked(False)
        self.commit("모두 잠금 풀기")

    def hide_selected(self):
        for it in self.view.selected():
            it.setVisible(False)
            it.setSelected(False)
        self.commit("숨기기")

    def show_all(self):
        for it in self.view.objects():
            it.setVisible(True)
        self.commit("모두 보이기")

    # ---------- 끌어다 놓기 ----------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls()]
        paths = [p for p in paths if p.lower().endswith((".mvec", ".svg", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"))]
        if not paths:
            return
        if paths[0].lower().endswith(".mvec") or not self.has_doc:
            if paths[0].lower().endswith((".mvec", ".svg")):
                self.open_file(paths[0])
            else:
                img = QImage(paths[0])
                self.start_document({"width": img.width() or 800, "height": img.height() or 600, "items": []},
                                    "제목 없음")
                self.place_file(paths[0])
            return
        for p in paths:
            self.place_file(p)

    # ---------- 도움말 ----------
    def show_shortcuts(self):
        QMessageBox.information(self, "단축키 안내", (
            "<b>도구</b><br>V 선택 · A 직접 선택 · P 펜 · N 연필 · T 문자 · \\ 선<br>"
            "M 사각형 · L 타원 · Y 다각형/별 · I 스포이드 · Z 돋보기 · H 손<br><br>"
            "<b>편집</b><br>Ctrl+G 그룹 · Ctrl+Shift+G 그룹 풀기 · Ctrl+D 복제<br>"
            "Ctrl+] 앞으로 · Ctrl+[ 뒤로 (Shift = 맨 앞/맨 뒤)<br>"
            "Ctrl+8 패스로 바꾸기 · Ctrl+Shift+O 윤곽선 만들기 · Ctrl+2 잠금<br>"
            "방향키 1pt 이동 (Shift = 10pt) · Delete 삭제<br><br>"
            "<b>화면</b><br>Space+드래그 이동 · Ctrl+휠 확대/축소 · Ctrl+0 대지에 맞추기"))

    def about(self):
        QMessageBox.about(self, brand.APP_NAME, f"<b>{brand.APP_NAME}</b> v{brand.APP_VERSION}<br>"
                          f"{brand.BRAND_NAME} ({brand.BRAND_NAME_EN})<br><br>"
                          "SVG(일러스트레이터 · 피그마 호환) · PDF · PNG 로 내보낼 수 있어요.<br>"
                          "<a href='https://mozzilab.labelpos.com'>mozzilab.labelpos.com</a>")

    def closeEvent(self, e):
        self.view.end_text_edit()
        if not self.maybe_save():
            e.ignore()
            return
        super().closeEvent(e)


def selftest():
    """설치파일이 제대로 만들어졌는지 점검 (GitHub 자동 빌드에서 사용): 성공하면 0"""
    import tempfile
    d = tempfile.mkdtemp()
    _app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841
    w = VectorWindow()
    w.start_document({"width": 400, "height": 300, "items": []}, "test")
    a = ShapeItem("rect", 120, 80)
    b = ShapeItem("ellipse", 100, 100)
    b.setPos(60, 40)
    for i, it in enumerate((a, b)):
        it.setZValue(i + 1)
        w.view.scene().addItem(it)
        it.setSelected(True)
    w.commit("도형")
    w.pathfinder("union")
    assert len(w.view.objects()) == 1
    w.undo()
    assert len(w.view.objects()) == 2
    for ext in ("svg", "pdf", "png"):
        p = os.path.join(d, "t." + ext)
        {"svg": w.export_svg, "pdf": w.export_pdf, "png": w.export_image}[ext](p)
        assert os.path.getsize(p) > 0
    items, _, _ = svg_io.import_svg(os.path.join(d, "t.svg"))
    assert len(items) == 2
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
    win = VectorWindow()
    win.show()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and os.path.isfile(args[0]):
        win.open_file(args[0])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
