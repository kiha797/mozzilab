"""캡처 영역 선택 화면 (직접지정 / 창 / 단위영역 / 스크롤 영역 선택).
화면 전체를 미리 찍어 둔 이미지를 꽉 채워 띄우고, 그 위에서 영역을 고르게 한다."""
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QImage, QPainter, QPen, QRegion
from PySide6.QtWidgets import QWidget

import capture
import winapi
from ui import ACCENT, px

GUIDE = {
    "region": "드래그해서 영역을 지정하세요  ·  클릭: 창 선택  ·  ESC/우클릭: 취소",
    "window": "캡처할 창을 클릭하세요  ·  ESC/우클릭: 취소",
    "unit": "캡처할 영역(버튼·패널 등)을 클릭하세요  ·  ESC/우클릭: 취소",
    "scroll": "스크롤할 창을 클릭하거나 영역을 드래그하세요  ·  ESC/우클릭: 취소",
}


def _to_qrect(r, origin):
    l, t, rt, b = r
    return QRect(QPoint(l, t) - origin, QPoint(rt - 1, b - 1) - origin)


class CaptureOverlay(QWidget):
    captured = Signal(QImage)        # 직접지정/창/단위영역 -> 잘라낸 이미지
    region_selected = Signal(QRect)  # 스크롤 -> 선택한 영역(절대 좌표)
    cancelled = Signal()

    def __init__(self, mode, shot, origin, windows, guide_color=ACCENT, dim=True):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.mode = mode
        self.guide = QColor(guide_color)
        self.dim = dim
        self.shot = shot
        self.origin = origin
        self.bounds = QRect(QPoint(0, 0), shot.size())
        self.windows = [(h, _to_qrect(r, origin)) for h, r in windows]
        self._children = {}
        self._press = None
        self._sel = QRect()
        self._hover = QRect()
        self._mouse = QPoint(-1000, -1000)
        self._done = False

        self.setGeometry(QRect(origin, shot.size()))
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

    # ---------- 표시 ----------
    def start(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        self._update_hover(self.mapFromGlobal(QCursor.pos()))

    # ---------- 마우스 아래 영역 찾기 ----------
    def _screen_rect(self, pt):
        return capture.screen_rect_containing(pt + self.origin).translated(-self.origin)

    def _element_rect(self, hwnd, win_rect, pt):
        if hwnd not in self._children:
            self._children[hwnd] = [_to_qrect(r, self.origin) for r in winapi.child_rects(hwnd)]
        best = win_rect
        for r in self._children[hwnd]:
            if r.contains(pt) and r.width() * r.height() < best.width() * best.height():
                best = r
        return best

    def _rect_under(self, pt):
        for hwnd, r in self.windows:
            if r.contains(pt):
                if self.mode == "unit":
                    r = self._element_rect(hwnd, r, pt)
                return r.intersected(self.bounds)
        return self._screen_rect(pt).intersected(self.bounds)

    def _update_hover(self, pt):
        self._mouse = pt
        self._hover = self._rect_under(pt)
        self.update()

    # ---------- 마우스/키보드 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.close()
            return
        if e.button() == Qt.LeftButton:
            self._press = e.position().toPoint()
            self._sel = QRect()

    def mouseMoveEvent(self, e):
        pt = e.position().toPoint()
        if self._press is not None and self.mode in ("region", "scroll"):
            self._mouse = pt
            if (pt - self._press).manhattanLength() > 4:
                self._sel = QRect(self._press, pt).normalized().intersected(self.bounds)
            self.update()
        else:
            self._update_hover(pt)

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.LeftButton or self._press is None:
            return
        self._press = None
        rect = self._sel if self._sel.width() > 3 and self._sel.height() > 3 else self._hover
        self._finish(rect)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._finish(self._sel if not self._sel.isEmpty() else self._hover)

    def _finish(self, rect):
        if rect.isEmpty():
            return
        self._done = True
        self.hide()
        if self.mode == "scroll":
            self.region_selected.emit(rect.translated(self.origin))
        else:
            self.captured.emit(self.shot.copy(rect))
        self.close()

    def closeEvent(self, e):
        if not self._done:
            self._done = True
            self.cancelled.emit()
        super().closeEvent(e)

    # ---------- 그리기 ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.drawImage(0, 0, self.shot)
        r = self._sel if not self._sel.isEmpty() else self._hover

        # 선택 영역 바깥은 어둡게
        p.save()
        region = QRegion(self.rect())
        if not r.isEmpty():
            region = region.subtracted(QRegion(r))
        p.setClipRegion(region)
        if self.dim:
            p.fillRect(self.rect(), QColor(0, 0, 0, 110))
        p.restore()

        if not r.isEmpty():
            p.setPen(QPen(self.guide, px(2)))
            p.setBrush(Qt.NoBrush)
            p.drawRect(r.adjusted(0, 0, -1, -1))
            self._draw_size_label(p, r)

        self._draw_guide(p)
        self._draw_magnifier(p)

    def _draw_size_label(self, p, r):
        text = f"{r.width()} x {r.height()}"
        f = QFont(self.font())
        f.setPointSizeF(9.5)
        p.setFont(f)
        fm = p.fontMetrics()
        w, h = fm.horizontalAdvance(text) + px(12), fm.height() + px(6)
        x, y = r.left(), r.top() - h - px(4)
        if y < 0:
            y = r.top() + px(4)
            x = r.left() + px(4)
        box = QRect(x, y, w, h)
        p.fillRect(box, self.guide)
        p.setPen(Qt.black if self.guide.lightness() > 170 else Qt.white)
        p.drawText(box, Qt.AlignCenter, text)

    def _draw_guide(self, p):
        text = GUIDE.get(self.mode, "")
        sr = self._screen_rect(self._mouse if self._mouse.x() > -1000 else QPoint(0, 0))
        f = QFont(self.font())
        f.setPointSizeF(10.5)
        p.setFont(f)
        fm = p.fontMetrics()
        w, h = fm.horizontalAdvance(text) + px(32), fm.height() + px(16)
        box = QRect(sr.center().x() - w // 2, sr.top() + px(24), w, h)
        if box.contains(self._mouse):        # 마우스와 겹치면 아래쪽으로
            box.moveBottom(sr.bottom() - px(24))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(20, 20, 20, 200))
        p.setRenderHint(QPainter.Antialiasing)
        p.drawRoundedRect(box, px(6), px(6))
        p.setPen(Qt.white)
        p.drawText(box, Qt.AlignCenter, text)
        p.setRenderHint(QPainter.Antialiasing, False)

    def _draw_magnifier(self, p):
        m = self._mouse
        if not self.bounds.contains(m):
            return
        n, zoom = 21, px(6)                  # 21x21 픽셀을 확대
        size = n * zoom
        src = self.shot.copy(QRect(m.x() - n // 2, m.y() - n // 2, n, n))
        big = src.scaled(size, size, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        info_h = px(40)
        x, y = m.x() + px(20), m.y() + px(24)
        sr = self._screen_rect(m)
        if x + size > sr.right():
            x = m.x() - px(20) - size
        if y + size + info_h > sr.bottom():
            y = m.y() - px(24) - size - info_h
        p.drawImage(x, y, big)
        p.setPen(QPen(self.guide, 1))
        c = x + (n // 2) * zoom
        d = y + (n // 2) * zoom
        p.drawLine(c + zoom // 2, y, c + zoom // 2, y + size)
        p.drawLine(x, d + zoom // 2, x + size, d + zoom // 2)
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.drawRect(x, y, size, size)

        color = self.shot.pixelColor(m)
        box = QRect(x, y + size, size + 1, info_h)
        p.fillRect(box, QColor(20, 20, 20, 220))
        f = QFont(self.font())
        f.setPointSizeF(8.5)
        p.setFont(f)
        p.setPen(Qt.white)
        gp = m + self.origin
        p.drawText(box, Qt.AlignCenter, f"좌표 {gp.x()}, {gp.y()}\n색상 {color.name().upper()}")
