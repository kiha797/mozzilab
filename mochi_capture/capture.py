"""화면을 찍는(grab) 기능. mss 라이브러리를 우선 사용하고, 없으면 Qt 기능으로 대신한다."""
from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QImage, QPainter, QPen, QPolygonF

import winapi

try:
    import mss
except ImportError:          # mss 가 없으면 Qt 로 대신 캡처
    mss = None


def virtual_geometry():
    """모니터 여러 대를 합친 전체 화면 영역"""
    rect = QRect()
    for s in QGuiApplication.screens():
        rect = rect.united(s.geometry())
    return rect


def _mss_grab(left, top, width, height):
    with mss.mss() as sct:
        raw = sct.grab({"left": left, "top": top, "width": width, "height": height})
        return QImage(raw.bgra, raw.width, raw.height, raw.width * 4, QImage.Format_RGB32).copy()


def _qt_grab(rect):
    img = QImage(rect.size(), QImage.Format_RGB32)
    img.fill(Qt.black)
    p = QPainter(img)
    for s in QGuiApplication.screens():
        g = s.geometry()
        part = g.intersected(rect)
        if part.isEmpty():
            continue
        pm = s.grabWindow(0)
        src = part.translated(-g.topLeft())
        p.drawPixmap(part.translated(-rect.topLeft()), pm, src)
    p.end()
    return img


def grab_rect(rect, cursor=False):
    """화면의 rect(절대 좌표) 영역을 QImage 로 돌려준다. cursor=True 면 마우스 커서도 그려 넣는다."""
    rect = rect.intersected(virtual_geometry())
    if rect.isEmpty():
        return QImage()
    img = None
    if mss is not None:
        try:
            img = _mss_grab(rect.x(), rect.y(), rect.width(), rect.height())
        except Exception:
            img = None
    if img is None:
        img = _qt_grab(rect)
    if cursor:
        add_cursor(img, rect.topLeft())
    return img


def grab_virtual(cursor=False):
    """모든 모니터 전체를 캡처. (이미지, 왼쪽 위 좌표) 를 돌려준다."""
    vg = virtual_geometry()
    return grab_rect(vg, cursor), vg.topLeft()


def _cursor_qimage():
    """Windows 의 실제 커서 모양을 투명 배경 이미지로 만든다."""
    data = winapi.cursor_bitmaps()
    if not data:
        return None
    import numpy as np
    black, white, size, hot, pos = data
    b = np.frombuffer(black, np.uint8).reshape(size, size, 4)[:, :, :3].astype(np.int32)
    w = np.frombuffer(white, np.uint8).reshape(size, size, 4)[:, :, :3].astype(np.int32)
    # 검은 배경과 흰 배경 결과의 차이로 투명도를 계산
    alpha = np.clip(255 - (w - b).mean(axis=2), 0, 255)
    inverted = (w - b).mean(axis=2) < -16           # 반전 커서(글자 입력 I 모양 등) -> 검정으로
    alpha[inverted] = 255
    safe = np.maximum(alpha, 1)[:, :, None]
    color = np.clip(b * 255 / safe, 0, 255)
    color[inverted] = 0
    out = np.zeros((size, size, 4), np.uint8)
    out[:, :, :3] = color
    out[:, :, 3] = alpha
    img = QImage(out.tobytes(), size, size, size * 4, QImage.Format_ARGB32).copy()
    return img, QPoint(*hot), QPoint(*pos)


def add_cursor(img, top_left):
    """img(화면의 top_left 위치에서 찍은 이미지)에 마우스 커서를 그린다."""
    cur = None
    try:
        cur = _cursor_qimage()
    except Exception:
        cur = None
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    if cur:
        cimg, hot, pos = cur
        p.drawImage(pos - hot - top_left, cimg)
    else:                                    # 커서를 못 읽으면 기본 화살표 모양
        pt = QCursor.pos() - top_left
        x, y = pt.x(), pt.y()
        arrow = QPolygonF([QPointF(x + dx, y + dy) for dx, dy in
                           ((0, 0), (0, 17), (4, 13), (7, 20), (10, 19), (7, 12), (12, 12))])
        p.setPen(QPen(Qt.white, 1.5))
        p.setBrush(Qt.black)
        p.drawPolygon(arrow)
    p.end()


def draw_guide(img, color, width=2):
    """'선택 영역 표시선 유지' - 이미지 가장자리에 표시선을 그린다."""
    if img.isNull():
        return img
    out = img.convertToFormat(QImage.Format_RGB32)
    p = QPainter(out)
    pen = QPen(QColor(color), width)
    pen.setJoinStyle(Qt.MiterJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    half = width / 2
    p.drawRect(QRect(0, 0, out.width(), out.height()).toRectF().adjusted(half, half, -half, -half))
    p.end()
    return out


def screen_at_cursor():
    pos = QCursor.pos()
    return QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()


def grab_screen_at_cursor(cursor=False):
    """마우스가 있는 모니터 한 대를 통째로 캡처 (전체화면)"""
    return grab_rect(screen_at_cursor().geometry(), cursor)


def screen_rect_containing(point: QPoint):
    s = QGuiApplication.screenAt(point) or QGuiApplication.primaryScreen()
    return s.geometry()
