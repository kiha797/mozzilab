"""크기지정 캡처: 화면 위에 떠 있는 '캡처 준비창'.
위치와 크기를 기억해 두었다가 다음에 열 때도 같은 자리에 같은 크기로 열린다."""
from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSpinBox, QWidget)

import capture
from ui import ACCENT, px

BUILTIN_PRESETS = [
    ("640 x 480", (640, 480)),
    ("800 x 600", (800, 600)),
    ("1024 x 768", (1024, 768)),
    ("1280 x 720 (HD)", (1280, 720)),
    ("1366 x 768", (1366, 768)),
    ("1920 x 1080 (FHD)", (1920, 1080)),
    ("500 x 500 (정사각)", (500, 500)),
    ("1080 x 1350 (SNS 세로)", (1080, 1350)),
]

L, T, R, B = 1, 2, 4, 8


def preset_list(cfg):
    """환경설정에 등록한 프리셋(최대 6개) + 기본 크기 목록"""
    items = [("크기 선택", None)]
    for w, h in cfg.get("fixed_presets", [])[:6]:
        items.append((f"★ {w} x {h}", (int(w), int(h))))
    return items + BUILTIN_PRESETS
MIN_SIZE = 20


class FixedFrame(QWidget):
    captured = Signal(QImage)
    closed = Signal()

    def __init__(self, cfg):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.cfg = cfg
        self.guide = QColor(cfg.get("guide_color", ACCENT))
        self.presets = preset_list(cfg)
        self.border = max(2, px(2))
        self.bar_h = px(46)
        self.cw = self.ch = 0
        self._drag = None
        self._done = False

        # 아래쪽 조작 막대
        self.bar = QFrame(self)
        self.bar.setObjectName("fixedBar")
        lay = QHBoxLayout(self.bar)
        lay.setContentsMargins(px(8), px(4), px(8), px(4))
        lay.setSpacing(px(6))
        self.w_spin = QSpinBox()
        self.h_spin = QSpinBox()
        for s in (self.w_spin, self.h_spin):
            s.setRange(MIN_SIZE, 10000)
            s.setButtonSymbols(QSpinBox.NoButtons)
            s.setFixedWidth(px(56))
            s.setAlignment(Qt.AlignCenter)
            s.editingFinished.connect(self._spin_changed)
        self.preset = QComboBox()
        for name, _ in self.presets:
            self.preset.addItem(name)
        self.preset.activated.connect(self._preset_changed)
        cap_btn = QPushButton("캡처 (Enter)")
        cap_btn.setObjectName("primary")
        cap_btn.setCursor(Qt.PointingHandCursor)
        cap_btn.clicked.connect(self.do_capture)
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        lay.addWidget(QLabel("가로"))
        lay.addWidget(self.w_spin)
        lay.addWidget(QLabel("세로"))
        lay.addWidget(self.h_spin)
        lay.addWidget(self.preset)
        lay.addStretch(1)
        lay.addWidget(cap_btn)
        lay.addWidget(close_btn)

        saved = cfg.get("fixed_rect")
        if saved and len(saved) == 4:
            rect = QRect(*saved)
            if capture.virtual_geometry().intersected(rect).isEmpty():
                rect = self._default_rect()
        else:
            rect = self._default_rect()
        self.set_capture_rect(rect)

    def _default_rect(self):
        sr = capture.screen_at_cursor().availableGeometry()
        w, h = min(800, sr.width() - 100), min(500, sr.height() - 150)
        return QRect(sr.center().x() - w // 2, sr.center().y() - h // 2, w, h)

    # ---------- 위치/크기 ----------
    def capture_rect(self):
        """실제로 찍힐 영역 (파란 테두리 안쪽, 절대 좌표)"""
        return QRect(self.x() + self.border, self.y() + self.border, self.cw, self.ch)

    def _frame_rect(self):
        return QRect(0, 0, self.cw + 2 * self.border, self.ch + 2 * self.border)

    def set_capture_rect(self, r):
        self.cw = max(MIN_SIZE, r.width())
        self.ch = max(MIN_SIZE, r.height())
        bar_w = self.bar.sizeHint().width()
        fw = self.cw + 2 * self.border
        w = max(fw, bar_w)
        h = self.ch + 2 * self.border + px(6) + self.bar_h
        self.setGeometry(r.x() - self.border, r.y() - self.border, w, h)
        self.bar.setGeometry(0, self.ch + 2 * self.border + px(6), max(bar_w, min(fw, w)), self.bar_h)
        for spin, v in ((self.w_spin, self.cw), (self.h_spin, self.ch)):
            spin.blockSignals(True)
            spin.setValue(v)
            spin.blockSignals(False)
        self.update()

    def _remember(self):
        r = self.capture_rect()
        self.cfg["fixed_rect"] = [r.x(), r.y(), r.width(), r.height()]
        self.cfg.save()

    def _spin_changed(self):
        r = self.capture_rect()
        r.setSize(QRect(0, 0, self.w_spin.value(), self.h_spin.value()).size())
        self.set_capture_rect(r)
        self._remember()

    def _preset_changed(self, idx):
        size = self.presets[idx][1]
        if size:
            r = self.capture_rect()
            self.set_capture_rect(QRect(r.x(), r.y(), size[0], size[1]))
            self._remember()
        self.preset.setCurrentIndex(0)

    # ---------- 표시 ----------
    def start(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def do_capture(self):
        if self._done:
            return
        self._done = True
        self._remember()
        rect = self.capture_rect()
        self.hide()
        QTimer.singleShot(150, lambda: self._grab(rect))

    def _grab(self, rect):
        img = capture.grab_rect(rect, self.cfg.get("include_cursor", False))
        self.captured.emit(img)
        self.close()

    def closeEvent(self, e):
        self._remember()
        self.closed.emit()
        super().closeEvent(e)

    # ---------- 마우스로 이동/크기 조절 ----------
    def _edges_at(self, pos):
        fr = self._frame_rect()
        if not fr.contains(pos):
            return None
        m = px(8)
        e = 0
        if pos.x() < m:
            e |= L
        if pos.x() > fr.right() - m:
            e |= R
        if pos.y() < m:
            e |= T
        if pos.y() > fr.bottom() - m:
            e |= B
        return e

    def _cursor_for(self, e):
        if e in (L | T, R | B):
            return Qt.SizeFDiagCursor
        if e in (R | T, L | B):
            return Qt.SizeBDiagCursor
        if e in (L, R):
            return Qt.SizeHorCursor
        if e in (T, B):
            return Qt.SizeVerCursor
        return Qt.SizeAllCursor

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return
        edges = self._edges_at(e.position().toPoint())
        if edges is None:
            return
        self._drag = (e.globalPosition().toPoint(), self.capture_rect(), edges)

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()
        if self._drag is None:
            edges = self._edges_at(pos)
            self.setCursor(Qt.ArrowCursor if edges is None else self._cursor_for(edges))
            return
        start, r0, edges = self._drag
        d = e.globalPosition().toPoint() - start
        r = QRect(r0)
        if edges == 0:
            r.translate(d)
        else:
            if edges & L:
                r.setLeft(min(r0.left() + d.x(), r0.right() - MIN_SIZE))
            if edges & R:
                r.setRight(max(r0.right() + d.x(), r0.left() + MIN_SIZE))
            if edges & T:
                r.setTop(min(r0.top() + d.y(), r0.bottom() - MIN_SIZE))
            if edges & B:
                r.setBottom(max(r0.bottom() + d.y(), r0.top() + MIN_SIZE))
        self.set_capture_rect(r)

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None
            self._remember()

    def mouseDoubleClickEvent(self, e):
        if self._edges_at(e.position().toPoint()) == 0:
            self.do_capture()

    def keyPressEvent(self, e):
        k = e.key()
        step = 10 if e.modifiers() & Qt.ShiftModifier else 1
        moves = {Qt.Key_Left: QPoint(-step, 0), Qt.Key_Right: QPoint(step, 0),
                 Qt.Key_Up: QPoint(0, -step), Qt.Key_Down: QPoint(0, step)}
        if k in (Qt.Key_Return, Qt.Key_Enter):
            self.do_capture()
        elif k == Qt.Key_Escape:
            self.close()
        elif k in moves:
            self.set_capture_rect(self.capture_rect().translated(moves[k]))
            self._remember()

    # ---------- 그리기 ----------
    def paintEvent(self, _):
        p = QPainter(self)
        b = self.border
        inner = QRect(b, b, self.cw, self.ch)
        p.fillRect(inner, QColor(0, 0, 0, 1))        # 거의 투명 (마우스로 잡을 수 있게)
        pen = QPen(self.guide, b)
        pen.setJoinStyle(Qt.MiterJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRect(b // 2, b // 2, self.cw + b, self.ch + b))
        # 모서리 손잡이
        hs = px(8)
        p.setBrush(self.guide)
        p.setPen(Qt.NoPen)
        fr = self._frame_rect()
        for pt in (fr.topLeft(), fr.topRight(), fr.bottomLeft(), fr.bottomRight(),
                   QPoint(fr.center().x(), fr.top()), QPoint(fr.center().x(), fr.bottom()),
                   QPoint(fr.left(), fr.center().y()), QPoint(fr.right(), fr.center().y())):
            p.drawRect(QRect(pt.x() - hs // 2, pt.y() - hs // 2, hs, hs).intersected(fr))
        # 크기 표시
        text = f"{self.cw} x {self.ch}"
        f = QFont(self.font())
        f.setPointSizeF(9.5)
        p.setFont(f)
        fm = p.fontMetrics()
        box = QRect(b + px(6), b + px(6), fm.horizontalAdvance(text) + px(12), fm.height() + px(6))
        p.fillRect(box, self.guide)
        p.setPen(Qt.black if self.guide.lightness() > 170 else Qt.white)
        p.drawText(box, Qt.AlignCenter, text)
