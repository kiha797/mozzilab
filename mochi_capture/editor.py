"""알캡처 '결과창'과 같은 편집 화면: 저장/복사/이전/다시/초기화/도형/펜/더보기 + 최근 캡처 목록"""
import os

from PySide6.QtCore import QLineF, QPointF, QRect, QRectF, QSize, QSizeF, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QIcon, QImage, QKeySequence,
                           QPainter, QPen, QPixmap, QPolygonF, QShortcut)
from PySide6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QFileDialog, QFrame,
                               QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea,
                               QSizePolicy, QSpinBox, QToolButton, QVBoxLayout, QWidget)

import winapi
from ads import AdBlock, PopupAd
from config import APP_NAME
from toast import show_toast
from ui import ACCENT, app_icon, color_icon, icon, px

SHAPES = [("rect", "사각형"), ("ellipse", "원"), ("line", "직선"), ("arrow", "화살표")]
PENS = [("pen", "펜"), ("highlighter", "형광펜")]
EXTRA = [("text", "텍스트"), ("mosaic", "모자이크"), ("crop", "자르기")]
TOOL_NAMES = dict(SHAPES + PENS + EXTRA)
PALETTE = ["#ff3b30", "#ff9500", "#ffcc00", "#34c759", "#1a73e8", "#5856d6", "#000000", "#ffffff"]
UNDO_LIMIT = 40
SAVE_FILTERS = {"png": "PNG 이미지 (*.png)", "jpg": "JPG 이미지 (*.jpg)", "bmp": "BMP 이미지 (*.bmp)"}


def save_with_format(cfg, img, path):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    quality = int(cfg.get("jpg_quality", 100)) if ext in ("jpg", "jpeg") else -1
    return img.save(path, None, quality)


def save_image_dialog(parent, cfg, img):
    """[저장] 창을 띄워 이미지를 저장한다. 저장한 경로(취소하면 None)를 돌려준다."""
    fmt = cfg.get("save_format", "png")
    order = [fmt] + [k for k in SAVE_FILTERS if k != fmt]
    folder = cfg.get("last_dialog_dir") or cfg.save_dir()
    if not os.path.isdir(folder):
        folder = cfg.save_dir()
    path, chosen = QFileDialog.getSaveFileName(
        parent, "이미지 저장", os.path.join(folder, cfg.new_file_name(fmt, folder)),
        ";;".join(SAVE_FILTERS[k] for k in order))
    if not path:
        return None
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext not in ("png", "jpg", "jpeg", "bmp"):
        ext = next(k for k, v in SAVE_FILTERS.items() if v == chosen)
        path += "." + ext
    if not save_with_format(cfg, img, path):
        QMessageBox.warning(parent, APP_NAME, "저장하지 못했습니다. 폴더 권한을 확인해 주세요.")
        return None
    cfg["last_dialog_dir"] = os.path.dirname(path)
    cfg.save()
    if cfg.get("save_notice"):
        show_toast("저장 완료", path, path)
    return path


# ======================================================================
#  그림판(캔버스)
# ======================================================================
class Canvas(QWidget):
    changed = Signal()
    zoomChanged = Signal(float)

    def __init__(self, area):
        super().__init__()
        self.area = area
        self.image = QImage()
        self.original = QImage()
        self.undo_stack, self.redo_stack = [], []
        self.dirty = False
        self.zoom = 1.0
        self.tool = None
        self.color = QColor(PALETTE[0])
        self.pen_width = 3
        self.fill = False
        self._start = self._cur = None
        self._points = []
        self._pan = None
        self.setMouseTracking(True)
        self._update_cursor()

    # ---------- 이미지 ----------
    def load(self, img):
        self.original = QImage(img)
        self.image = QImage(img)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.dirty = False
        self._apply_size()
        self.changed.emit()

    def commit(self, new_img):
        self.undo_stack.append(self.image)
        if len(self.undo_stack) > UNDO_LIMIT:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        self.image = new_img
        self.dirty = True
        self._apply_size()
        self.changed.emit()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.image)
            self.image = self.undo_stack.pop()
            self.dirty = True
            self._apply_size()
            self.changed.emit()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.image)
            self.image = self.redo_stack.pop()
            self.dirty = True
            self._apply_size()
            self.changed.emit()

    def reset(self):
        if not self.original.isNull() and self.image != self.original:
            self.commit(QImage(self.original))

    # ---------- 확대/축소 ----------
    def _apply_size(self):
        if self.image.isNull():
            self.setFixedSize(1, 1)
        else:
            self.setFixedSize(max(1, int(self.image.width() * self.zoom)),
                              max(1, int(self.image.height() * self.zoom)))
        self.update()

    def set_zoom(self, z):
        self.zoom = max(0.1, min(8.0, z))
        self._apply_size()
        self.zoomChanged.emit(self.zoom)

    def fit_zoom(self):
        if self.image.isNull():
            return
        vp = self.area.viewport().size()
        z = min(1.0, (vp.width() - 40) / self.image.width(), (vp.height() - 40) / self.image.height())
        self.set_zoom(max(0.1, z))

    # ---------- 도구 ----------
    def set_tool(self, tool):
        self.tool = tool
        self._start = None
        self._update_cursor()
        self.update()

    def _update_cursor(self):
        if self.tool is None:
            self.setCursor(Qt.OpenHandCursor)
        elif self.tool == "text":
            self.setCursor(Qt.IBeamCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def _img_pt(self, pos):
        return QPointF(pos.x() / self.zoom, pos.y() / self.zoom)

    def _constrain(self, a, b, shift):
        """Shift 키: 정사각형/정원, 직선은 45도 단위"""
        if not shift:
            return b
        dx, dy = b.x() - a.x(), b.y() - a.y()
        if self.tool in ("rect", "ellipse", "mosaic", "crop"):
            s = max(abs(dx), abs(dy))
            return QPointF(a.x() + (s if dx >= 0 else -s), a.y() + (s if dy >= 0 else -s))
        if self.tool in ("line", "arrow"):
            if abs(dx) > 2 * abs(dy):
                return QPointF(b.x(), a.y())
            if abs(dy) > 2 * abs(dx):
                return QPointF(a.x(), b.y())
            s = max(abs(dx), abs(dy))
            return QPointF(a.x() + (s if dx >= 0 else -s), a.y() + (s if dy >= 0 else -s))
        return b

    # ---------- 마우스 ----------
    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or self.image.isNull():
            return
        if self.tool is None:
            self._pan = (e.globalPosition().toPoint(), self.area.horizontalScrollBar().value(),
                         self.area.verticalScrollBar().value())
            self.setCursor(Qt.ClosedHandCursor)
            return
        pt = self._img_pt(e.position())
        if self.tool == "text":
            self._add_text(pt)
            return
        self._start = self._cur = pt
        self._points = [pt]

    def mouseMoveEvent(self, e):
        if self._pan:
            start, h0, v0 = self._pan
            d = e.globalPosition().toPoint() - start
            self.area.horizontalScrollBar().setValue(h0 - d.x())
            self.area.verticalScrollBar().setValue(v0 - d.y())
        elif self._start is not None:
            pt = self._img_pt(e.position())
            self._cur = self._constrain(self._start, pt, e.modifiers() & Qt.ShiftModifier)
            if self.tool in ("pen", "highlighter"):
                self._points.append(pt)
            self.update()

    def mouseReleaseEvent(self, e):
        if self._pan:
            self._pan = None
            self._update_cursor()
            return
        if self._start is None:
            return
        a, b, tool = self._start, self._cur, self.tool
        self._start = None
        r = QRectF(a, b).normalized()
        if tool == "crop":
            rr = r.toAlignedRect().intersected(self.image.rect())
            if rr.width() > 2 and rr.height() > 2:
                self.commit(self.image.copy(rr))
            self.update()
            return
        if tool in ("rect", "ellipse", "line", "arrow", "mosaic") and QLineF(a, b).length() < 3:
            self.update()
            return
        if tool in ("pen", "highlighter") and len(self._points) < 2:
            self._points.append(a + QPointF(0.5, 0.5))
        img = QImage(self.image)
        p = QPainter(img)
        self._paint_tool(p, tool, a, b, self._points, img)
        p.end()
        self.commit(img)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.set_zoom(self.zoom * (1.1 if e.angleDelta().y() > 0 else 1 / 1.1))
            e.accept()
        else:
            e.ignore()

    def _add_text(self, pt):
        text, ok = QInputDialog.getMultiLineText(self, "텍스트 입력", "넣을 글자를 입력하세요:")
        if not ok or not text.strip():
            return
        img = QImage(self.image)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        f = QFont("Malgun Gothic")
        f.setPixelSize(max(12, self.pen_width * 6))
        f.setBold(True)
        p.setFont(f)
        p.setPen(self.color)
        p.drawText(QRectF(pt, QSizeF(20000, 20000)), Qt.AlignLeft | Qt.AlignTop, text)
        p.end()
        self.commit(img)

    # ---------- 그리기 ----------
    def _paint_tool(self, p, tool, a, b, pts, base):
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(self.color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        r = QRectF(a, b).normalized()
        if tool in ("rect", "ellipse"):
            p.setPen(pen)
            p.setBrush(self.color if self.fill else Qt.NoBrush)
            if tool == "rect":
                pen.setJoinStyle(Qt.MiterJoin)
                p.setPen(pen)
                p.drawRect(r)
            else:
                p.drawEllipse(r)
        elif tool == "line":
            p.setPen(pen)
            p.drawLine(a, b)
        elif tool == "arrow":
            line = QLineF(a, b)
            length = line.length()
            if length < 1:
                return
            head = max(12.0, self.pen_width * 4.0)
            ux, uy = (b.x() - a.x()) / length, (b.y() - a.y()) / length
            base_pt = QPointF(b.x() - ux * head, b.y() - uy * head)
            nx, ny = -uy * head * 0.55, ux * head * 0.55
            p.setPen(pen)
            p.drawLine(a, base_pt)
            p.setPen(Qt.NoPen)
            p.setBrush(self.color)
            p.drawPolygon(QPolygonF([b, QPointF(base_pt.x() + nx, base_pt.y() + ny),
                                     QPointF(base_pt.x() - nx, base_pt.y() - ny)]))
        elif tool == "pen":
            p.setPen(pen)
            p.drawPolyline(QPolygonF(pts))
        elif tool == "highlighter":
            c = QColor(self.color)
            c.setAlpha(90)
            p.setPen(QPen(c, self.pen_width * 5, Qt.SolidLine, Qt.FlatCap, Qt.RoundJoin))
            p.drawPolyline(QPolygonF(pts))
        elif tool == "mosaic":
            rr = r.toAlignedRect().intersected(base.rect())
            if rr.width() < 2 or rr.height() < 2:
                return
            block = max(6, self.pen_width * 3)
            small = base.copy(rr).scaled(max(1, rr.width() // block), max(1, rr.height() // block),
                                         Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            p.drawImage(rr.topLeft(), small.scaled(rr.size(), Qt.IgnoreAspectRatio, Qt.FastTransformation))

    def paintEvent(self, _):
        if self.image.isNull():
            return
        p = QPainter(self)
        p.scale(self.zoom, self.zoom)
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.zoom < 1)
        p.drawImage(0, 0, self.image)
        if self._start is None:
            return
        if self.tool == "crop":
            r = QRectF(self._start, self._cur).normalized()
            full = QRectF(self.image.rect())
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 120))
            for part in (QRectF(full.left(), full.top(), full.width(), r.top()),
                         QRectF(full.left(), r.bottom(), full.width(), full.bottom() - r.bottom()),
                         QRectF(full.left(), r.top(), r.left(), r.height()),
                         QRectF(r.right(), r.top(), full.right() - r.right(), r.height())):
                p.drawRect(part)
            dash = QPen(QColor(ACCENT), 1.5 / self.zoom, Qt.DashLine)
            p.setPen(dash)
            p.setBrush(Qt.NoBrush)
            p.drawRect(r)
        else:
            self._paint_tool(p, self.tool, self._start, self._cur, self._points, self.image)


# ======================================================================
#  최근 캡처 목록
# ======================================================================
class HistoryPanel(QWidget):
    picked = Signal(str)

    def __init__(self, window):
        super().__init__()
        self.win = window
        self.setObjectName("historyPanel")
        self.setAttribute(Qt.WA_StyledBackground)
        self.setFixedWidth(px(230))
        self._thumbs = {}
        v = QVBoxLayout(self)
        v.setContentsMargins(0, px(12), 0, 0)
        v.setSpacing(0)

        head = QHBoxLayout()
        head.setContentsMargins(px(14), 0, px(8), 0)
        self.title = QLabel("최근 캡처 목록")
        self.title.setObjectName("panelTitle")
        head.addWidget(self.title)
        head.addStretch(1)
        self.select_btn = QPushButton("선택")
        self.select_btn.setProperty("role", "link")
        self.select_btn.setCheckable(True)
        self.select_btn.toggled.connect(self._toggle_select)
        head.addWidget(self.select_btn)
        v.addLayout(head)
        self.count = QLabel("")
        self.count.setObjectName("panelCount")
        self.count.setContentsMargins(px(14), px(2), 0, px(8))
        v.addWidget(self.count)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:#e3e5ea;")
        v.addWidget(line)

        self.list = QListWidget()
        self.list.setObjectName("historyList")
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setFlow(QListWidget.TopToBottom)
        self.list.setWrapping(False)
        self.list.setMovement(QListWidget.Static)
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setIconSize(QSize(px(160), px(160)))
        self.list.setGridSize(QSize(px(200), px(180)))
        self.list.setSpacing(px(4))
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.list.itemClicked.connect(self._clicked)
        v.addWidget(self.list, 1)

        foot = QHBoxLayout()
        foot.setContentsMargins(px(8), px(6), px(8), px(10))
        self.save_all = QPushButton("모두 저장")
        self.del_all = QPushButton("모두 삭제")
        for b in (self.save_all, self.del_all):
            b.setProperty("role", "link")
            b.setCursor(Qt.PointingHandCursor)
        sep = QLabel("|")
        sep.setStyleSheet("color:#cccccc;")
        foot.addWidget(self.save_all, 1)
        foot.addWidget(sep)
        foot.addWidget(self.del_all, 1)
        v.addLayout(foot)
        self.save_all.clicked.connect(self.win.save_all)
        self.del_all.clicked.connect(self.win.delete_all)

    def _thumb(self, path):
        key = (path, os.path.getmtime(path) if os.path.exists(path) else 0)
        if key not in self._thumbs:
            img = QImage(path)
            size = px(160)
            canvas = QPixmap(size, size)
            canvas.fill(QColor("#f1f3f6"))
            if not img.isNull():
                t = img.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                p = QPainter(canvas)
                p.drawImage((size - t.width()) // 2, (size - t.height()) // 2, t)
                p.end()
            self._thumbs[key] = QIcon(canvas)
        return self._thumbs[key]

    def refresh(self, current=None):
        files = self.win.history.files()
        self.list.blockSignals(True)
        self.list.clear()
        for f in files:
            item = QListWidgetItem(self._thumb(f), "")
            item.setData(Qt.UserRole, f)
            item.setToolTip(os.path.basename(f))
            self.list.addItem(item)
            if f == current:
                item.setSelected(True)
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        self.count.setText(f"[{len(files)}장/{self.win.history.limit}장]")

    def update_thumb(self, path):
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.UserRole) == path:
                item.setIcon(self._thumb(path))

    def _clicked(self, item):
        if self.select_btn.isChecked():
            return
        self.picked.emit(item.data(Qt.UserRole))

    def _toggle_select(self, on):
        self.select_btn.setText("완료" if on else "선택")
        self.list.setSelectionMode(QListWidget.MultiSelection if on else QListWidget.SingleSelection)
        self.save_all.setText("선택 저장" if on else "모두 저장")
        self.del_all.setText("선택 삭제" if on else "모두 삭제")
        if not on:
            self.refresh(self.win.current_path)

    def selected_paths(self):
        return [it.data(Qt.UserRole) for it in self.list.selectedItems()]

    def _context_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.UserRole)
        m = QMenu(self)
        a_open = m.addAction("열기")
        a_save = m.addAction("다른 이름으로 저장…")
        a_copy = m.addAction("클립보드에 복사")
        m.addSeparator()
        a_del = m.addAction("삭제")
        act = m.exec(self.list.mapToGlobal(pos))
        if act == a_open:
            self.picked.emit(path)
        elif act == a_save:
            self.win.save_image_as(QImage(path))
        elif act == a_copy:
            QApplication.clipboard().setImage(QImage(path))
        elif act == a_del:
            if self.win.cfg.get("confirm_delete", True) and QMessageBox.question(
                    self, APP_NAME, "이 이미지를 목록에서 삭제할까요?") != QMessageBox.Yes:
                return
            self.win.delete_paths([path])


# ======================================================================
#  결과창
# ======================================================================
class ResultWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.ctrl = controller
        self.cfg = controller.cfg
        self.history = controller.history
        self.current_path = None
        self.shape_tool = "rect"
        self.pen_tool = "pen"
        self.setWindowTitle(f"{APP_NAME} 결과창")
        self.setWindowIcon(app_icon())

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_option_bar())

        body = QHBoxLayout()
        body.setSpacing(0)
        self.area = QScrollArea()
        self.area.setObjectName("canvasArea")
        self.area.setAlignment(Qt.AlignCenter)
        self.area.setWidgetResizable(False)
        self.canvas = Canvas(self.area)
        self.area.setWidget(self.canvas)
        body.addWidget(self.area, 1)
        self.panel_toggle = QToolButton()
        self.panel_toggle.setText("▸")
        self.panel_toggle.setAutoRaise(True)
        self.panel_toggle.setFixedWidth(px(14))
        self.panel_toggle.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.panel_toggle.setStyleSheet("QToolButton{border:none;background:#f1f3f6;color:#999;}")
        self.panel_toggle.clicked.connect(self._toggle_panel)
        body.addWidget(self.panel_toggle)
        self.popup_ad = PopupAd(self.ctrl.ads, self.area)
        self.panel = HistoryPanel(self)
        self.panel.picked.connect(self.open_path)
        body.addWidget(self.panel)
        root.addLayout(body, 1)
        self.setCentralWidget(central)
        self._build_statusbar()
        self._build_shortcuts()

        self.canvas.changed.connect(self._on_changed)
        self.update_account()
        self.canvas.zoomChanged.connect(lambda z: self.zoom_label.setText(f"{round(z * 100)} %"))

        g = self.cfg.get("editor_geometry")
        if g and len(g) == 4:
            self.setGeometry(*g)
        else:
            self.resize(px(1100), px(760))
        self._on_changed()

    # ---------- 화면 구성 ----------
    def _big_button(self, text, icon_name, slot=None, checkable=False):
        b = QToolButton()
        b.setProperty("role", "big")
        b.setText(text)
        b.setIcon(icon(icon_name))
        b.setIconSize(QSize(px(30), px(30)))
        b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        b.setCheckable(checkable)
        b.setCursor(Qt.PointingHandCursor)
        if slot:
            b.clicked.connect(slot)
        return b

    @staticmethod
    def _vsep():
        s = QFrame()
        s.setObjectName("vsep")
        s.setFixedHeight(px(60))
        return s

    def _build_toolbar(self):
        bar = QWidget()
        bar.setObjectName("toolbar")
        bar.setAttribute(Qt.WA_StyledBackground)
        h = QHBoxLayout(bar)
        h.setContentsMargins(px(8), px(6), px(8), px(6))
        h.setSpacing(px(2))

        h.addWidget(self._big_button("새캡처", "newcap", self.ctrl.show_launcher))
        h.addWidget(self._vsep())
        h.addWidget(self._big_button("저장", "save", self.save))
        h.addWidget(self._big_button("복사", "copy", self.copy))
        self.undo_btn = self._big_button("이전", "undo", lambda: self.canvas.undo())
        self.redo_btn = self._big_button("다시", "redo", lambda: self.canvas.redo())
        self.reset_btn = self._big_button("초기화", "reset", lambda: self.canvas.reset())
        h.addWidget(self.undo_btn)
        h.addWidget(self.redo_btn)
        h.addWidget(self.reset_btn)
        h.addWidget(self._vsep())

        # 도형
        self.shape_btn = self._big_button("도형", "shape", lambda: self._tool_clicked(self.shape_tool), True)
        self.shape_btn.setPopupMode(QToolButton.MenuButtonPopup)
        shape_menu = QMenu(self)
        for key, name in SHAPES:
            a = shape_menu.addAction(icon(key), name)
            a.triggered.connect(lambda _=False, k=key: self._pick_shape(k))
        self.shape_btn.setMenu(shape_menu)
        h.addWidget(self.shape_btn)

        # 펜
        self.pen_btn = self._big_button("펜", "pen", lambda: self._tool_clicked(self.pen_tool), True)
        self.pen_btn.setPopupMode(QToolButton.MenuButtonPopup)
        pen_menu = QMenu(self)
        for key, name in PENS:
            a = pen_menu.addAction(icon(key), name)
            a.triggered.connect(lambda _=False, k=key: self._pick_pen(k))
        self.pen_btn.setMenu(pen_menu)
        h.addWidget(self.pen_btn)
        h.addWidget(self._vsep())

        # 더보기
        self.more_btn = self._big_button("더보기", "more", checkable=True)
        self.more_btn.setPopupMode(QToolButton.InstantPopup)
        more = QMenu(self)
        for key, name in EXTRA:
            a = more.addAction(icon(key), name)
            a.triggered.connect(lambda _=False, k=key: self.set_tool(k))
        more.addSeparator()
        more.addAction(icon("open"), "이미지 파일 열기…", self.open_file)
        more.addAction(icon("print"), "인쇄…", self.print_image)
        more.addAction(icon("folder"), "저장 폴더 열기", lambda: winapi.open_folder(self.cfg.save_dir()))
        more.addSeparator()
        more.addAction(icon("settings"), "환경설정…", self.ctrl.show_settings)
        self.more_btn.setMenu(more)
        h.addWidget(self.more_btn)
        h.addStretch(1)

        # 무료 사용자 광고 (알캡처처럼 툴바 오른쪽)
        self.ad_block = AdBlock(self.ctrl.ads)
        h.addWidget(self.ad_block)
        h.addSpacing(px(10))

        # 로그인 / 계정 버튼
        acc = QVBoxLayout()
        acc.setSpacing(px(4))
        self.account_btn = QToolButton()
        self.account_btn.setObjectName("accountBtn")
        self.account_btn.setCursor(Qt.PointingHandCursor)
        self.account_btn.setPopupMode(QToolButton.InstantPopup)
        self.account_btn.setStyleSheet(
            f"QToolButton#accountBtn {{ border: 1.5px solid {ACCENT}; color: {ACCENT}; border-radius: {px(6)}px;"
            f" padding: {px(5)}px {px(14)}px; font-weight: bold; background: white; }}"
            "QToolButton#accountBtn:hover { background: #fff0f4; }"
            "QToolButton#accountBtn::menu-indicator { image: none; width: 0; }")
        self.account_btn.clicked.connect(self._account_clicked)
        self.plan_label = QLabel("")
        self.plan_label.setAlignment(Qt.AlignCenter)
        self.plan_label.setStyleSheet(f"color:{ACCENT}; font-size:8.5pt;")
        acc.addWidget(self.account_btn)
        acc.addWidget(self.plan_label)
        acc.addStretch(1)
        h.addLayout(acc)
        return bar

    # ---------- 계정 / 광고 ----------
    def _account_clicked(self):
        if not self.ctrl.account.logged_in:
            self.ctrl.login(self)

    def update_account(self):
        account = self.ctrl.account
        if account.logged_in:
            name = account.name or "회원"
            self.account_btn.setText(("⭐ " if account.premium else "") + f"{name} 님 ▾")
            m = QMenu(self)
            if account.email:
                m.addAction(account.email).setEnabled(False)
            if account.premium and account.expires_at:
                m.addAction(f"광고 제거 이용 중 (~{account.expires_at:%Y-%m-%d})").setEnabled(False)
            m.addSeparator()
            m.addAction("마이페이지", account.open_mypage)
            if not account.premium:
                m.addAction("광고 없이 쓰기 (구독)", account.open_pricing)
            m.addAction("구독 상태 새로고침", lambda: account.refresh())
            m.addSeparator()
            m.addAction("로그아웃", self.ctrl.logout)
            self.account_btn.setMenu(m)
            self.plan_label.setText("광고 없이 이용 중" if account.premium else "무료 이용 중")
        else:
            self.account_btn.setText("로그인")
            self.account_btn.setMenu(None)
            self.plan_label.setText("")
        self.refresh_ads()

    def refresh_ads(self):
        show = self.ctrl.ads.show_ads
        self.ad_block.setVisible(show)
        if show and self.ad_block.card.ad is None:
            self.ad_block.rotate()
        if not show:
            self.popup_ad.hide()

    def _build_option_bar(self):
        bar = QWidget()
        bar.setObjectName("optionBar")
        bar.setAttribute(Qt.WA_StyledBackground)
        h = QHBoxLayout(bar)
        h.setContentsMargins(px(14), px(4), px(14), px(4))
        h.setSpacing(px(6))
        self.tool_label = QLabel("")
        self.tool_label.setStyleSheet(f"color:{ACCENT}; font-weight:bold;")
        h.addWidget(self.tool_label)
        h.addSpacing(px(12))
        h.addWidget(QLabel("색상"))
        for c in PALETTE:
            b = QToolButton()
            b.setIcon(color_icon(QColor(c), px(18)))
            b.setIconSize(QSize(px(18), px(18)))
            b.setAutoRaise(True)
            b.clicked.connect(lambda _=False, col=c: self._set_color(QColor(col)))
            h.addWidget(b)
        more_c = QToolButton()
        more_c.setText("…")
        more_c.setToolTip("다른 색 고르기")
        more_c.clicked.connect(self._pick_color)
        h.addWidget(more_c)
        self.cur_color = QLabel()
        h.addWidget(self.cur_color)
        h.addSpacing(px(12))
        h.addWidget(QLabel("두께"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 40)
        self.width_spin.setValue(3)
        self.width_spin.valueChanged.connect(lambda v: setattr(self.canvas, "pen_width", v))
        h.addWidget(self.width_spin)
        self.fill_chk = QCheckBox("채우기")
        self.fill_chk.toggled.connect(lambda v: setattr(self.canvas, "fill", v))
        h.addWidget(self.fill_chk)
        h.addStretch(1)
        h.addWidget(QLabel("Shift: 정사각형·직선 고정   ESC: 도구 해제"))
        bar.setVisible(False)
        self.option_bar = bar
        return bar

    def _build_statusbar(self):
        sb = self.statusBar()
        sb.setSizeGripEnabled(True)
        self.size_label = QLabel("")
        minus = QToolButton()
        minus.setText("－")
        minus.setAutoRaise(True)
        minus.clicked.connect(lambda: self.canvas.set_zoom(self.canvas.zoom / 1.25))
        plus = QToolButton()
        plus.setText("＋")
        plus.setAutoRaise(True)
        plus.clicked.connect(lambda: self.canvas.set_zoom(self.canvas.zoom * 1.25))
        self.zoom_label = QLabel("100 %")
        self.zoom_label.setMinimumWidth(px(52))
        self.zoom_label.setAlignment(Qt.AlignCenter)
        orig = QPushButton("원본크기")
        orig.clicked.connect(lambda: self.canvas.set_zoom(1.0))
        fit = QPushButton("창맞춤")
        fit.clicked.connect(self.canvas_fit)
        for w in (self.size_label, minus, self.zoom_label, plus, orig, fit):
            sb.addPermanentWidget(w)

    def canvas_fit(self):
        self.canvas.fit_zoom()

    def _build_shortcuts(self):
        keys = [
            (QKeySequence.Save, self.save),
            (QKeySequence.Copy, self.copy),
            (QKeySequence.Undo, lambda: self.canvas.undo()),
            (QKeySequence("Ctrl+Y"), lambda: self.canvas.redo()),
            (QKeySequence("Ctrl+Shift+Z"), lambda: self.canvas.redo()),
            (QKeySequence("Ctrl+N"), self.ctrl.show_launcher),
            (QKeySequence("Ctrl+0"), lambda: self.canvas.set_zoom(1.0)),
            (QKeySequence("Ctrl+="), lambda: self.canvas.set_zoom(self.canvas.zoom * 1.25)),
            (QKeySequence("Ctrl+-"), lambda: self.canvas.set_zoom(self.canvas.zoom / 1.25)),
            (QKeySequence("Ctrl+P"), self.print_image),
            (QKeySequence("Escape"), lambda: self.set_tool(None)),
        ]
        for seq, slot in keys:
            QShortcut(seq, self, activated=slot)

    # ---------- 도구 선택 ----------
    def _pick_shape(self, key):
        self.shape_tool = key
        self.shape_btn.setIcon(icon(key))
        self.set_tool(key)

    def _pick_pen(self, key):
        self.pen_tool = key
        self.pen_btn.setIcon(icon(key))
        self.set_tool(key)

    def _tool_clicked(self, key):
        self.set_tool(None if self.canvas.tool == key else key)

    def set_tool(self, tool):
        self.canvas.set_tool(tool)
        self.shape_btn.setChecked(tool in dict(SHAPES))
        self.pen_btn.setChecked(tool in dict(PENS))
        self.more_btn.setChecked(tool in dict(EXTRA))
        self.option_bar.setVisible(tool is not None and tool != "crop")
        self.fill_chk.setVisible(tool in ("rect", "ellipse"))
        self.tool_label.setText(TOOL_NAMES.get(tool, ""))
        if tool == "crop":
            self.statusBar().showMessage("자를 영역을 드래그하세요. (ESC: 취소)")
        else:
            self.statusBar().clearMessage()
        self._show_color()

    def _set_color(self, c):
        self.canvas.color = c
        self._show_color()

    def _pick_color(self):
        c = QColorDialog.getColor(self.canvas.color, self, "색상 선택")
        if c.isValid():
            self._set_color(c)

    def _show_color(self):
        self.cur_color.setPixmap(color_icon(self.canvas.color, px(22)).pixmap(px(22), px(22)))

    def _toggle_panel(self):
        vis = not self.panel.isVisible()
        self.panel.setVisible(vis)
        self.panel_toggle.setText("▸" if vis else "◂")

    # ---------- 상태 갱신 ----------
    def _on_changed(self):
        img = self.canvas.image
        has = not img.isNull()
        self.size_label.setText(f"이미지 사이즈 : {img.width()} x {img.height()}" if has else "")
        self.undo_btn.setEnabled(bool(self.canvas.undo_stack))
        self.redo_btn.setEnabled(bool(self.canvas.redo_stack))
        self.reset_btn.setEnabled(has and bool(self.canvas.undo_stack or self.canvas.redo_stack))

    # ---------- 이미지 열기 ----------
    def show_capture(self, path, new_capture=False):
        self.panel.refresh(path)
        self.open_path(path, force=True)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if new_capture and self.ctrl.ads.show_ads:
            self.ad_block.rotate()
            if self.ctrl.ads.should_popup():
                self.popup_ad.show_ad()

    def open_path(self, path, force=False):
        if path == self.current_path and not force:
            return
        self.flush()
        img = QImage(path)
        if img.isNull():
            return
        self.current_path = path
        self.canvas.load(img)
        vp = self.area.viewport().size()
        if img.width() > vp.width() or img.height() > vp.height():
            self.canvas.fit_zoom()
        else:
            self.canvas.set_zoom(1.0)
        self.panel.refresh(path)

    def flush(self):
        """편집한 내용을 최근 목록 파일에 반영"""
        if self.current_path and self.canvas.dirty and os.path.exists(self.current_path):
            self.canvas.image.save(self.current_path, "PNG")
            self.canvas.dirty = False
            self.panel.update_thumb(self.current_path)

    # ---------- 저장/복사 ----------
    def save(self):
        if not self.canvas.image.isNull():
            self.save_image_as(self.canvas.image)

    def save_image_as(self, img):
        path = save_image_dialog(self, self.cfg, img)
        if path:
            self.statusBar().showMessage(f"저장했습니다: {path}", 5000)

    def copy(self):
        if not self.canvas.image.isNull():
            QApplication.clipboard().setImage(self.canvas.image)
            self.statusBar().showMessage("클립보드에 복사했습니다. 원하는 곳에 Ctrl+V 로 붙여넣으세요.", 4000)

    def save_all(self):
        self.flush()
        paths = self.panel.selected_paths() if self.panel.select_btn.isChecked() else self.history.files()
        if not paths:
            return
        folder = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택", self.cfg.save_dir())
        if not folder:
            return
        count = self.history.export(paths, folder)
        self.statusBar().showMessage(f"{count}장을 저장했습니다: {folder}", 5000)
        if self.cfg.get("notice_save_all", True):
            box = QMessageBox(QMessageBox.Information, APP_NAME, f"{count}장을 모두 저장했습니다.\n{folder}",
                              QMessageBox.Ok, self)
            open_btn = box.addButton("폴더 열기", QMessageBox.ActionRole)
            box.exec()
            if box.clickedButton() == open_btn:
                winapi.open_folder(folder)

    def delete_all(self):
        if self.panel.select_btn.isChecked():
            paths = self.panel.selected_paths()
        else:
            paths = self.history.files()
        if not paths:
            return
        selecting = self.panel.select_btn.isChecked()
        ask = self.cfg.get("confirm_delete" if selecting else "confirm_clear", True)
        msg = (f"선택한 {len(paths)}장을 목록에서 삭제할까요?" if selecting
               else f"최근 캡처 목록을 모두 비울까요? ({len(paths)}장)")
        if ask and QMessageBox.question(self, APP_NAME, msg + "\n(따로 저장해 둔 파일은 지워지지 않습니다)") \
                != QMessageBox.Yes:
            return
        self.delete_paths(paths)
        if self.panel.select_btn.isChecked():
            self.panel.select_btn.setChecked(False)

    def delete_paths(self, paths):
        for p in paths:
            self.history.delete(p)
        if self.current_path in paths:
            self.current_path = None
            rest = self.history.files()
            if rest:
                self.open_path(rest[0], force=True)
            else:
                self.canvas.load(QImage())
        self.panel.refresh(self.current_path)

    # ---------- 기타 ----------
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "이미지 열기", self.cfg.save_dir(),
                                              "이미지 (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            img = QImage(path)
            if not img.isNull():
                self.ctrl.on_captured(img, copy=False)

    def print_image(self):
        if self.canvas.image.isNull():
            return
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        printer = QPrinter(QPrinter.HighResolution)
        if QPrintDialog(printer, self).exec():
            p = QPainter(printer)
            page = printer.pageRect(QPrinter.DevicePixel).toRect()
            img = self.canvas.image.scaled(page.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawImage(QRect(0, 0, img.width(), img.height()), img)
            p.end()

    def save_state(self):
        self.flush()
        g = self.geometry()
        self.cfg["editor_geometry"] = [g.x(), g.y(), g.width(), g.height()]
        self.cfg.save()
        self.set_tool(None)

    def closeEvent(self, e):
        self.save_state()
        super().closeEvent(e)
        if not self.cfg.get("close_to_tray", True):
            self.ctrl.quit()      # '종료버튼 클릭 시 트레이로 최소화'를 끈 경우 프로그램 종료
