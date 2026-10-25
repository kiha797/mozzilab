"""스크롤 캡처: 선택한 영역을 자동으로 아래로 스크롤하면서 여러 장 찍고, 겹치는 부분을 찾아 한 장으로 이어 붙인다."""
import numpy as np
from PySide6.QtCore import QObject, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QLabel

import capture
import winapi
from ui import px

MAX_STEPS = 80
MAX_HEIGHT = 30000


def to_gray(img):
    g = img.convertToFormat(QImage.Format_Grayscale8)
    h, w, bpl = g.height(), g.width(), g.bytesPerLine()
    arr = np.frombuffer(g.constBits(), dtype=np.uint8, count=bpl * h).reshape(h, bpl)
    return arr[:, :w].astype(np.int16)


def find_offset(prev, cur):
    """prev 화면이 cur 화면에서 몇 픽셀 위로 올라갔는지 계산.
    0 = 움직이지 않음, -1 = 판단 불가"""
    h, w = prev.shape
    if h < 40 or w < 10:
        return -1
    cols = slice(0, max(1, w - px(20)), 3)        # 오른쪽 스크롤바는 비교에서 제외
    P, C = prev[:, cols], cur[:, cols]
    if np.abs(P - C).mean() < 0.3:
        return 0
    k = max(16, min(60, h // 6))
    # 이전 화면 아래쪽에서 무늬가 가장 많은 띠를 고른다
    best_t, best_std = None, -1.0
    for t in range(h // 3, h - k, max(1, k // 4)):
        s = float(P[t:t + k].std())
        if s > best_std:
            best_std, best_t = s, t
    if best_t is None or best_std < 2:
        return -1
    band = P[best_t:best_t + k]
    best_y, best_d = None, 1e18
    for y in range(0, best_t + 1):
        d = float(np.abs(C[y:y + k] - band).mean())
        if d < best_d:
            best_d, best_y = d, y
    if best_y is None or best_d > 12:
        return -1
    return best_t - best_y


class ScrollCapture(QObject):
    finished = Signal(QImage)

    def __init__(self, rect, delay_ms=450):
        super().__init__()
        self.rect = rect
        self.delay = int(delay_ms)
        self.parts = []
        self.prev = None
        self.total_h = 0
        self.steps = 0
        self.still = 0
        self.tip = QLabel("  스크롤 캡처 중…  ESC 키를 누르면 중지합니다  ")
        self.tip.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.tip.setAttribute(Qt.WA_ShowWithoutActivating)
        self.tip.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.tip.setStyleSheet("background:#ff6f91; color:white; padding:8px; font-size:10.5pt;")
        self.tip.adjustSize()
        self._place_tip()

    def _place_tip(self):
        sr = capture.screen_rect_containing(self.rect.center())
        size = self.tip.sizeHint()
        cands = [QRect(self.rect.left(), self.rect.top() - size.height() - px(6), size.width(), size.height()),
                 QRect(self.rect.left(), self.rect.bottom() + px(6), size.width(), size.height()),
                 QRect(sr.left() + px(10), sr.top() + px(10), size.width(), size.height()),
                 QRect(sr.right() - size.width() - px(10), sr.bottom() - size.height() - px(60),
                       size.width(), size.height())]
        self.tip_overlaps = True
        for c in cands:
            if sr.contains(c) and not c.intersects(self.rect):
                self.tip.setGeometry(c)
                self.tip_overlaps = False
                return
        self.tip.setGeometry(cands[2])

    def start(self):
        self.tip.show()
        QTimer.singleShot(200, self._step)

    def _grab(self):
        if self.tip_overlaps:
            self.tip.hide()
        img = capture.grab_rect(self.rect)
        if self.tip_overlaps:
            self.tip.show()
        return img

    def _step(self):
        if winapi.key_down(winapi.VK_ESCAPE):
            self._finish()
            return
        img = self._grab()
        cur = to_gray(img)
        if self.prev is None:
            self.parts.append(img)
            self.total_h = img.height()
        else:
            off = find_offset(self.prev, cur)
            if off == -1:
                self._finish()
                return
            if off == 0:
                self.still += 1
            else:
                self.still = 0
                self.parts.append(img.copy(0, img.height() - off, img.width(), off))
                self.total_h += off
        self.prev = cur
        self.steps += 1
        if self.still >= 2 or self.steps >= MAX_STEPS or self.total_h >= MAX_HEIGHT:
            self._finish()
            return
        c = self.rect.center()
        winapi.scroll_at(c.x(), c.y(), -3)
        QTimer.singleShot(self.delay, self._step)

    def _finish(self):
        self.tip.close()
        if not self.parts:
            self.finished.emit(QImage())
            return
        w = self.parts[0].width()
        out = QImage(w, self.total_h, QImage.Format_RGB32)
        out.fill(Qt.white)
        p = QPainter(out)
        y = 0
        for part in self.parts:
            p.drawImage(0, y, part)
            y += part.height()
        p.end()
        self.finished.emit(out)
