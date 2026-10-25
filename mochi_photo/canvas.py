"""모찌포토 캔버스: 그림을 보여주고 마우스로 도구를 쓰는 곳"""
import math

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QImage, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPolygonF, QRadialGradient, QTransform)
from PySide6.QtWidgets import QWidget

import photo_core as C
from editor_kit import checker_brush_pixmap

PAINT_TOOLS = ("brush", "pencil", "eraser", "stamp")
SELECT_TOOLS = ("marquee", "ellipsesel", "lasso", "wand")


class Canvas(QWidget):
    cursorMoved = Signal(int, int)
    zoomChanged = Signal(float)
    message = Signal(str)

    def __init__(self, ed):
        super().__init__()
        self.ed = ed
        self.doc = None
        self.zoom = 1.0
        self.off = QPointF(0, 0)
        self.tool = "brush"
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.checker = checker_brush_pixmap(8)
        self.mouse = QPointF(-100, -100)
        self.drag = None          # 진행 중인 마우스 작업 정보
        self.space = False
        self.crop_rect = None
        self.clone_src = None
        self.clone_offset = None
        self.ants = 0
        self.ant_timer = QTimer(self, interval=180)
        self.ant_timer.timeout.connect(self._ants)
        self.ant_timer.start()

    # ---------- 좌표 ----------
    def to_doc(self, p):
        return QPointF((p.x() - self.off.x()) / self.zoom, (p.y() - self.off.y()) / self.zoom)

    def to_view_rect(self, r):
        return QRectF(r.x() * self.zoom + self.off.x(), r.y() * self.zoom + self.off.y(),
                      r.width() * self.zoom, r.height() * self.zoom).toAlignedRect().adjusted(-2, -2, 2, 2)

    def set_document(self, doc):
        self.doc = doc
        self.drag = None
        self.crop_rect = None
        self.clone_src = self.clone_offset = None
        self.fit()

    def fit(self):
        if not self.doc:
            return
        w, h = max(1, self.width() - 40), max(1, self.height() - 40)
        self.zoom = min(w / self.doc.width, h / self.doc.height, 1.0 if max(self.doc.width, self.doc.height) > 64 else 16)
        self._center()

    def actual_size(self):
        self.zoom = 1.0
        self._center()

    def _center(self):
        self.off = QPointF((self.width() - self.doc.width * self.zoom) / 2,
                           (self.height() - self.doc.height * self.zoom) / 2)
        self.zoomChanged.emit(self.zoom)
        self.update()

    def zoom_by(self, factor, anchor=None):
        if not self.doc:
            return
        anchor = anchor or QPointF(self.width() / 2, self.height() / 2)
        d = self.to_doc(anchor)
        self.zoom = max(0.02, min(64.0, self.zoom * factor))
        self.off = QPointF(anchor.x() - d.x() * self.zoom, anchor.y() - d.y() * self.zoom)
        self.zoomChanged.emit(self.zoom)
        self.update()

    def resizeEvent(self, e):
        if self.doc and e.oldSize().width() > 0:
            dx = (e.size().width() - e.oldSize().width()) / 2
            dy = (e.size().height() - e.oldSize().height()) / 2
            self.off += QPointF(dx, dy)
        elif self.doc:
            self.fit()
        super().resizeEvent(e)

    def _ants(self):
        if self.doc and self.doc.has_selection():
            self.ants = (self.ants + 1) % 16
            self.update()

    # ---------- 그리기 ----------
    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#232227"))
        if not self.doc:
            return
        doc = self.doc
        target = QRectF(self.off.x(), self.off.y(), doc.width * self.zoom, doc.height * self.zoom)
        p.fillRect(target.adjusted(3, 3, 3, 3), QColor(0, 0, 0, 90))
        p.save()
        p.setClipRect(target)
        p.setBrushOrigin(target.topLeft())
        p.fillRect(target, QBrush(self.checker))
        p.restore()
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.zoom < 1)
        p.drawImage(target, doc.composite())
        t = QTransform(self.zoom, 0, 0, self.zoom, self.off.x(), self.off.y())

        if self.zoom >= 12:      # 아주 크게 보면 픽셀 격자
            p.setPen(QPen(QColor(128, 128, 128, 70), 0))
            vis = QRectF(self.to_doc(QPointF(0, 0)), self.to_doc(QPointF(self.width(), self.height())))
            x0, x1 = max(0, int(vis.left())), min(doc.width, int(vis.right()) + 1)
            y0, y1 = max(0, int(vis.top())), min(doc.height, int(vis.bottom()) + 1)
            for x in range(x0, x1 + 1):
                vx = x * self.zoom + self.off.x()
                p.drawLine(QPointF(vx, target.top()), QPointF(vx, target.bottom()))
            for y in range(y0, y1 + 1):
                vy = y * self.zoom + self.off.y()
                p.drawLine(QPointF(target.left(), vy), QPointF(target.right(), vy))

        # 선택 영역 (개미 행렬)
        if doc.has_selection():
            path = t.map(doc.selection)
            p.setRenderHint(QPainter.Antialiasing, False)
            p.setPen(QPen(Qt.black, 1))
            p.drawPath(path)
            pen = QPen(Qt.white, 1, Qt.CustomDashLine)
            pen.setDashPattern([4, 4])
            pen.setDashOffset(self.ants)
            p.setPen(pen)
            p.drawPath(path)

        d = self.drag
        p.setRenderHint(QPainter.Antialiasing)
        if d and d.get("preview") is not None:
            prev = t.map(d["preview"])
            pen = QPen(QColor("#ff6f91"), 1.5, Qt.DashLine)
            p.setPen(pen)
            p.setBrush(QColor(255, 111, 145, 40))
            p.drawPath(prev)
        if d and d.get("line"):
            a, b = d["line"]
            p.setPen(QPen(Qt.white, 3))
            p.drawLine(t.map(a), t.map(b))
            p.setPen(QPen(QColor("#ff6f91"), 1.5))
            p.drawLine(t.map(a), t.map(b))
            for q in (a, b):
                p.drawEllipse(t.map(q), 4, 4)
        if self.crop_rect is not None:
            cr = t.mapRect(QRectF(self.crop_rect))
            outside = QPainterPath()
            outside.addRect(target)
            inner = QPainterPath()
            inner.addRect(cr)
            p.fillPath(outside.subtracted(inner), QColor(0, 0, 0, 140))
            p.setPen(QPen(Qt.white, 1))
            p.setBrush(Qt.NoBrush)
            p.drawRect(cr)
            p.setPen(QPen(QColor(255, 255, 255, 110), 1))
            for i in (1, 2):
                p.drawLine(QPointF(cr.left() + cr.width() * i / 3, cr.top()), QPointF(cr.left() + cr.width() * i / 3, cr.bottom()))
                p.drawLine(QPointF(cr.left(), cr.top() + cr.height() * i / 3), QPointF(cr.right(), cr.top() + cr.height() * i / 3))
            p.setPen(Qt.white)
            p.drawText(cr.adjusted(4, 4, 0, 0), Qt.AlignLeft | Qt.AlignTop,
                       f"{self.crop_rect.width()} × {self.crop_rect.height()}  ·  Enter = 자르기, Esc = 취소")
        if self.clone_src is not None and self.tool == "stamp":
            src = self.clone_src
            if d and d.get("kind") == "stroke":       # 칠하는 동안 복제 원본 위치도 함께 움직인다
                src = src + (d["pos"] - d["start"])
            c = t.map(src)
            p.setPen(QPen(Qt.white, 1))
            p.drawLine(c + QPointF(-7, 0), c + QPointF(7, 0))
            p.drawLine(c + QPointF(0, -7), c + QPointF(0, 7))

        # 브러시 크기 원
        if self.tool in PAINT_TOOLS and self.underMouse() and not self.space:
            r = max(1.5, self.ed.opts.size.value() * self.zoom / 2)
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(0, 0, 0, 160), 1))
            p.drawEllipse(self.mouse, r + 1, r + 1)
            p.setPen(QPen(QColor(255, 255, 255, 220), 1))
            p.drawEllipse(self.mouse, r, r)
        p.end()

    # ---------- 커서 ----------
    def update_cursor(self):
        if self.space or self.tool == "hand":
            self.setCursor(Qt.ClosedHandCursor if self.drag and self.drag.get("kind") == "pan" else Qt.OpenHandCursor)
        elif self.tool in PAINT_TOOLS:
            self.setCursor(Qt.CrossCursor if self.ed.opts.size.value() * self.zoom < 6 else Qt.BlankCursor)
        elif self.tool == "move":
            self.setCursor(Qt.SizeAllCursor)
        elif self.tool == "text":
            self.setCursor(Qt.IBeamCursor)
        elif self.tool == "zoom":
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def set_tool(self, tool):
        if self.crop_rect is not None and tool != "crop":
            self.crop_rect = None
        self.tool = tool
        self.update_cursor()
        self.update()

    # ---------- 마우스 ----------
    def enterEvent(self, e):
        self.setFocus()
        self.update_cursor()

    def leaveEvent(self, e):
        self.mouse = QPointF(-100, -100)
        self.update()

    def wheelEvent(self, e):
        if not self.doc:
            return
        dy = e.angleDelta().y()
        if e.modifiers() & (Qt.ControlModifier | Qt.AltModifier):
            self.zoom_by(1.15 if dy > 0 else 1 / 1.15, e.position())
        elif e.modifiers() & Qt.ShiftModifier:
            self.off += QPointF(dy / 2, 0)
            self.update()
        else:
            self.off += QPointF(e.angleDelta().x() / 2, dy / 2)
            self.update()

    def mousePressEvent(self, e):
        if not self.doc:
            return
        pos = self.to_doc(e.position())
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and (self.space or self.tool == "hand")):
            self.drag = {"kind": "pan", "start": e.position(), "off": QPointF(self.off)}
            self.update_cursor()
            return
        if e.button() != Qt.LeftButton:
            return
        mods = e.modifiers()
        t = self.tool
        if t == "zoom":
            self.zoom_by(1 / 1.6 if mods & Qt.AltModifier else 1.6, e.position())
        elif t == "eyedrop":
            self.pick_color(pos, bg=bool(mods & Qt.AltModifier))
            self.drag = {"kind": "eyedrop"}
        elif t in PAINT_TOOLS:
            if t == "stamp" and mods & Qt.AltModifier:
                self.clone_src = QPointF(pos)
                self.clone_offset = None
                self.message.emit("복제할 위치를 정했어요. 이제 칠할 곳을 드래그하세요.")
                self.update()
                return
            if t == "stamp" and self.clone_src is None:
                self.message.emit("Alt 키를 누른 채 클릭해서 복제할 위치를 먼저 정하세요.")
                return
            self.begin_stroke(pos)
        elif t in ("marquee", "ellipsesel"):
            self.drag = {"kind": "rectsel", "start": pos, "pos": pos, "preview": QPainterPath(), "mods": mods}
        elif t == "lasso":
            self.drag = {"kind": "lasso", "pts": [pos], "preview": QPainterPath(), "mods": mods}
        elif t == "wand":
            self.magic_wand(pos, mods)
        elif t == "crop":
            self.drag = {"kind": "crop", "start": pos}
            self.crop_rect = QRect(pos.toPoint(), pos.toPoint())
        elif t == "move":
            self.begin_move(pos)
        elif t == "bucket":
            self.bucket(pos)
        elif t == "gradient":
            self.drag = {"kind": "gradient", "line": (pos, pos)}
        elif t == "shape":
            self.drag = {"kind": "shape", "start": pos, "pos": pos, "preview": QPainterPath(), "mods": mods}
        elif t == "text":
            self.ed.add_text(pos)

    def mouseMoveEvent(self, e):
        self.mouse = e.position()
        if not self.doc:
            return
        pos = self.to_doc(e.position())
        if 0 <= pos.x() < self.doc.width and 0 <= pos.y() < self.doc.height:
            self.cursorMoved.emit(int(pos.x()), int(pos.y()))
        d = self.drag
        if not d:
            if self.tool in PAINT_TOOLS:
                self.update()
            return
        k = d["kind"]
        if k == "pan":
            self.off = d["off"] + (e.position() - d["start"])
            self.update()
        elif k == "eyedrop":
            self.pick_color(pos, bg=bool(e.modifiers() & Qt.AltModifier))
        elif k == "stroke":
            self.continue_stroke(pos, e.modifiers())
        elif k in ("rectsel", "shape"):
            d["pos"] = pos
            r = self._drag_rect(d["start"], pos, e.modifiers())
            path = QPainterPath()
            if k == "shape" and self.ed.opts.shape_type.currentIndex() in (3, 4):
                path.moveTo(d["start"])
                path.lineTo(pos)
            elif (k == "rectsel" and self.tool == "ellipsesel") or (k == "shape" and self.ed.opts.shape_type.currentIndex() == 2):
                path.addEllipse(r)
            elif k == "shape" and self.ed.opts.shape_type.currentIndex() == 1:
                rad = min(r.width(), r.height()) * 0.18
                path.addRoundedRect(r, rad, rad)
            else:
                path.addRect(r)
            d["preview"] = path
            d["rect"] = r
            self.update()
        elif k == "lasso":
            d["pts"].append(pos)
            path = QPainterPath()
            path.addPolygon(QPolygonF(d["pts"]))
            d["preview"] = path
            self.update()
        elif k == "crop":
            self.crop_rect = QRect(d["start"].toPoint(), pos.toPoint()).normalized().intersected(self.doc.rect())
            self.update()
        elif k == "move":
            self.continue_move(pos)
        elif k == "gradient":
            end = pos
            if e.modifiers() & Qt.ShiftModifier:      # 45도 단위로 맞추기
                a = d["line"][0]
                ang = round(math.atan2(pos.y() - a.y(), pos.x() - a.x()) / (math.pi / 4)) * (math.pi / 4)
                ln = math.hypot(pos.x() - a.x(), pos.y() - a.y())
                end = QPointF(a.x() + ln * math.cos(ang), a.y() + ln * math.sin(ang))
            d["line"] = (d["line"][0], end)
            self.update()

    def mouseReleaseEvent(self, e):
        d = self.drag
        if not d or not self.doc:
            return
        self.drag = None
        k = d["kind"]
        if k == "pan":
            self.update_cursor()
        elif k == "stroke":
            self.ed.commit({"brush": "브러시", "pencil": "연필", "eraser": "지우개", "stamp": "복제 도장"}[self.tool])
        elif k == "rectsel":
            r = d.get("rect")
            path = QPainterPath()
            if r is not None and r.width() >= 1 and r.height() >= 1:
                (path.addEllipse if self.tool == "ellipsesel" else path.addRect)(r)
            self.apply_selection(path, d["mods"])
        elif k == "lasso":
            path = QPainterPath()
            if len(d["pts"]) > 2:
                path.addPolygon(QPolygonF(d["pts"]))
                path.closeSubpath()
            self.apply_selection(path, d["mods"])
        elif k == "crop":
            if self.crop_rect is not None and (self.crop_rect.width() < 2 or self.crop_rect.height() < 2):
                self.crop_rect = None
            self.update()
        elif k == "move":
            if d.get("moved"):
                self.ed.commit("이동")
        elif k == "gradient":
            a, b = d["line"]
            if (b - a).manhattanLength() > 2:
                self.draw_gradient(a, b)
            self.update()
        elif k == "shape":
            if "rect" in d and (d["rect"].width() > 1 or d["rect"].height() > 1):
                self.draw_shape(d["start"], d["pos"], d["rect"])
            self.update()
        self.update()

    def mouseDoubleClickEvent(self, e):
        if self.tool == "crop" and self.crop_rect is not None:
            self.ed.apply_crop()

    @staticmethod
    def _drag_rect(a, b, mods):
        x0, y0, x1, y1 = a.x(), a.y(), b.x(), b.y()
        if mods & Qt.ShiftModifier:           # 정사각형 · 정원
            s = max(abs(x1 - x0), abs(y1 - y0))
            x1 = x0 + math.copysign(s, x1 - x0 or 1)
            y1 = y0 + math.copysign(s, y1 - y0 or 1)
        return QRectF(QPointF(x0, y0), QPointF(x1, y1)).normalized()

    # ---------- 키보드 ----------
    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Space and not e.isAutoRepeat():
            self.space = True
            self.update_cursor()
            return
        if e.modifiers() & (Qt.ControlModifier | Qt.MetaModifier):
            return super().keyPressEvent(e)
        if k in (Qt.Key_Return, Qt.Key_Enter) and self.crop_rect is not None:
            self.ed.apply_crop()
        elif k == Qt.Key_Escape:
            if self.crop_rect is not None:
                self.crop_rect = None
                self.update()
            elif self.drag:
                self.drag = None
                self.update()
        elif k in (Qt.Key_Delete, Qt.Key_Backspace):
            self.ed.clear_selection_pixels()
        elif k == Qt.Key_BracketLeft:
            s = self.ed.opts.size
            s.setValue(max(1, int(s.value() / 1.2) if s.value() > 10 else s.value() - 1))
            self.update()
        elif k == Qt.Key_BracketRight:
            s = self.ed.opts.size
            s.setValue(int(s.value() * 1.2) + 1 if s.value() > 10 else s.value() + 1)
            self.update()
        elif k == Qt.Key_X:
            self.ed.swap_colors()
        elif k == Qt.Key_D:
            self.ed.default_colors()
        elif e.text() and e.text().isalpha():
            self.ed.tool_shortcut(e.text())
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self.space = False
            self.update_cursor()
        super().keyReleaseEvent(e)

    # ---------- 색 ----------
    def pick_color(self, pos, bg=False):
        x, y = int(pos.x()), int(pos.y())
        if 0 <= x < self.doc.width and 0 <= y < self.doc.height:
            c = self.doc.composite().pixelColor(x, y)
            c.setAlpha(255)
            (self.ed.bg_btn if bg else self.ed.fg_btn).set_color(c)

    # ---------- 붓질 (브러시 · 연필 · 지우개 · 복제 도장) ----------
    def begin_stroke(self, pos):
        doc = self.doc
        ly = doc.layer
        if not ly.visible:
            self.message.emit("숨겨진 레이어에는 그릴 수 없어요. 레이어의 눈(체크)을 켜 주세요.")
            return
        d = {"kind": "stroke", "base": QImage(ly.image), "stroke": C.new_image(doc.width, doc.height),
             "last": pos, "start": QPointF(pos), "pos": pos, "rest": 0.0}
        if self.tool == "stamp":
            if self.clone_offset is None:
                self.clone_offset = pos - self.clone_src
            d["kind_src"] = QImage(ly.image)
        self.drag = d
        self.drag["kind"] = "stroke"
        self._dab(pos, pos, first=True)

    def continue_stroke(self, pos, mods):
        self.drag["pos"] = pos
        self._dab(self.drag["last"], pos)
        self.drag["last"] = pos

    def _brush_color(self):
        if self.tool == "eraser":
            return QColor(0, 0, 0)
        if self.tool == "stamp":
            return QColor(255, 255, 255)
        c = QColor(self.ed.fg_btn.color())
        c.setAlpha(255)
        return c

    def _dab(self, a, b, first=False):
        d = self.drag
        opts = self.ed.opts
        size = max(1, opts.size.value())
        r = size / 2
        hard = opts.hardness.value() / 100 if self.tool != "pencil" else 1.0
        color = self._brush_color()
        sp = QPainter(d["stroke"])
        if self.tool != "pencil":
            sp.setRenderHint(QPainter.Antialiasing)
        sp.setPen(Qt.NoPen)
        dist = math.hypot(b.x() - a.x(), b.y() - a.y())
        step = max(1.0, size * 0.12)
        pts = [a] if first else []
        if dist > 0:
            t = (step - d["rest"]) if not first else step
            while t <= dist:
                pts.append(QPointF(a.x() + (b.x() - a.x()) * t / dist, a.y() + (b.y() - a.y()) * t / dist))
                t += step
            d["rest"] = dist - (t - step)
        for q in pts:
            if self.tool == "pencil":
                if size <= 1:
                    sp.fillRect(QRectF(math.floor(q.x()), math.floor(q.y()), 1, 1), color)
                else:
                    sp.setBrush(color)
                    sp.drawEllipse(QPointF(math.floor(q.x()) + 0.5, math.floor(q.y()) + 0.5), r, r)
            elif hard >= 0.99:
                sp.setBrush(color)
                sp.drawEllipse(q, r, r)
            else:
                g = QRadialGradient(q, r)
                g.setColorAt(0, color)
                g.setColorAt(hard, color)
                c2 = QColor(color)
                c2.setAlpha(0)
                g.setColorAt(1, c2)
                sp.setBrush(QBrush(g))
                sp.drawEllipse(q, r, r)
        sp.end()
        dirty = QRectF(a, b).normalized().adjusted(-r - 2, -r - 2, r + 2, r + 2).toAlignedRect()
        self._apply_stroke(dirty.intersected(self.doc.rect()))

    def _apply_stroke(self, r):
        if r.isEmpty():
            return
        d = self.drag
        doc = self.doc
        ly = doc.layer
        opacity = self.ed.opts.opacity.value() / 100
        if self.tool in ("brush",):
            opacity *= self.ed.fg_btn.color().alphaF()
        p = QPainter(ly.image)
        if doc.has_selection():
            p.setClipPath(doc.selection)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.drawImage(r, d["base"], r)
        p.setOpacity(opacity)
        if self.tool == "eraser":
            p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            p.drawImage(r, d["stroke"], r)
        elif self.tool == "stamp":
            tmp = C.new_image(r.width(), r.height())
            tp = QPainter(tmp)
            src = r.translated(-self.clone_offset.toPoint())
            tp.drawImage(QPoint(0, 0), d["kind_src"], src)
            tp.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            tp.drawImage(QPoint(0, 0), d["stroke"], r)
            tp.end()
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.drawImage(r.topLeft(), tmp)
        else:
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.drawImage(r, d["stroke"], r)
        p.end()
        doc.composite(r)
        self.update(self.to_view_rect(r))
        if self.tool == "stamp":
            self.update()

    # ---------- 선택 ----------
    def apply_selection(self, path, mods):
        doc = self.doc
        mode = self.ed.opts.selmode.currentIndex()       # 0 새로 1 추가 2 빼기 3 교차
        if mods & Qt.ShiftModifier and mods & Qt.AltModifier:
            mode = 3
        elif mods & Qt.ShiftModifier:
            mode = 1
        elif mods & Qt.AltModifier:
            mode = 2
        bound = QPainterPath()
        bound.addRect(QRectF(doc.rect()))
        path = path.intersected(bound) if not path.isEmpty() else path
        if mode == 0:
            doc.selection = path
        elif mode == 1:
            doc.selection = doc.selection.united(path)
        elif mode == 2:
            doc.selection = doc.selection.subtracted(path)
        else:
            doc.selection = doc.selection.intersected(path)
        self.ed.commit("선택" if not doc.selection.isEmpty() else "선택 해제")

    def _sample_image(self):
        return self.doc.composite() if self.ed.opts.all_layers.isChecked() else self.doc.layer.image

    def magic_wand(self, pos, mods):
        o = self.ed.opts
        self.setCursor(Qt.WaitCursor)
        try:
            m = C.color_mask(self._sample_image(), int(pos.x()), int(pos.y()), o.tolerance.value(), o.contiguous.isChecked())
            path = C.path_from_mask(m) if m.any() else QPainterPath()
        finally:
            self.update_cursor()
        self.apply_selection(path, mods)

    # ---------- 이동 ----------
    def begin_move(self, pos):
        doc = self.doc
        base = QImage(doc.layer.image)
        d = {"kind": "move", "start": pos, "base": base, "moved": False}
        if doc.has_selection():
            sel = doc.selection
            fl = C.new_image(doc.width, doc.height)
            p = QPainter(fl)
            p.setClipPath(sel)
            p.drawImage(0, 0, base)
            p.end()
            cut = QImage(base)
            p = QPainter(cut)
            p.setClipPath(sel)
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.fillRect(cut.rect(), Qt.transparent)
            p.end()
            d.update(float=fl, cut=cut, sel=QPainterPath(sel))
        self.drag = d

    def continue_move(self, pos):
        d = self.drag
        doc = self.doc
        dx, dy = int(round(pos.x() - d["start"].x())), int(round(pos.y() - d["start"].y()))
        d["moved"] = d["moved"] or dx or dy
        img = C.new_image(doc.width, doc.height)
        p = QPainter(img)
        if "float" in d:
            p.drawImage(0, 0, d["cut"])
            p.drawImage(dx, dy, d["float"])
            doc.selection = d["sel"].translated(dx, dy)
        else:
            p.drawImage(dx, dy, d["base"])
        p.end()
        doc.layer.image = img
        doc.composite()
        self.update()

    def nudge(self, dx, dy):
        self.begin_move(QPointF(0, 0))
        self.continue_move(QPointF(dx, dy))
        self.drag = None
        self.ed.commit("이동")

    # ---------- 페인트 통 ----------
    def bucket(self, pos):
        doc = self.doc
        o = self.ed.opts
        x, y = int(pos.x()), int(pos.y())
        if not (0 <= x < doc.width and 0 <= y < doc.height):
            return
        self.setCursor(Qt.WaitCursor)
        try:
            m = C.color_mask(self._sample_image(), x, y, o.tolerance.value(), o.contiguous.isChecked())
            c = self.ed.fg_btn.color()
            arr = np.zeros(m.shape + (4,), np.uint8)
            arr[..., 0], arr[..., 1], arr[..., 2] = c.red(), c.green(), c.blue()
            arr[..., 3] = m * 255
            fill = C.array_to_qimage(arr)
            p = QPainter(doc.layer.image)
            if doc.has_selection():
                p.setClipPath(doc.selection)
            p.setOpacity(o.opacity.value() / 100 * c.alphaF())
            p.drawImage(0, 0, fill)
            p.end()
        finally:
            self.update_cursor()
        self.ed.commit("페인트 통")

    # ---------- 그레이디언트 ----------
    def draw_gradient(self, a, b):
        doc = self.doc
        o = self.ed.opts
        c1 = QColor(self.ed.fg_btn.color())
        c2 = QColor(c1) if o.grad_transparent.isChecked() else QColor(self.ed.bg_btn.color())
        if o.grad_transparent.isChecked():
            c2.setAlpha(0)
        if o.grad_type.currentIndex() == 0:
            g = QLinearGradient(a, b)
        else:
            g = QRadialGradient(a, math.hypot(b.x() - a.x(), b.y() - a.y()))
        g.setColorAt(0, c1)
        g.setColorAt(1, c2)
        p = QPainter(doc.layer.image)
        if doc.has_selection():
            p.setClipPath(doc.selection)
        p.setOpacity(o.opacity.value() / 100)
        p.fillRect(doc.rect(), QBrush(g))
        p.end()
        self.ed.commit("그레이디언트")

    # ---------- 도형 ----------
    def draw_shape(self, a, b, rect):
        doc = self.doc
        o = self.ed.opts
        kind = o.shape_type.currentIndex()       # 0 사각형 1 둥근 사각형 2 타원 3 선 4 화살표
        names = ["사각형", "둥근 사각형", "타원", "선", "화살표"]
        if o.new_layer.isChecked():
            doc.add_layer(names[kind])
        p = QPainter(doc.layer.image)
        p.setRenderHint(QPainter.Antialiasing)
        fg, bg = self.ed.fg_btn.color(), self.ed.bg_btn.color()
        w = o.stroke_w.value()
        if kind >= 3:
            pen = QPen(fg, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(pen)
            p.drawLine(a, b)
            if kind == 4:
                ang = math.atan2(b.y() - a.y(), b.x() - a.x())
                ln = max(10, w * 4)
                pts = [b, QPointF(b.x() - ln * math.cos(ang - 0.45), b.y() - ln * math.sin(ang - 0.45)),
                       QPointF(b.x() - ln * math.cos(ang + 0.45), b.y() - ln * math.sin(ang + 0.45))]
                p.setBrush(fg)
                p.drawPolygon(QPolygonF(pts))
        else:
            p.setPen(QPen(bg, w, Qt.SolidLine, Qt.SquareCap if kind == 0 else Qt.RoundCap, Qt.MiterJoin)
                     if o.stroke.isChecked() else Qt.NoPen)
            p.setBrush(fg if o.fill.isChecked() else Qt.NoBrush)
            if kind == 0:
                p.drawRect(rect)
            elif kind == 1:
                rad = min(rect.width(), rect.height()) * 0.18
                p.drawRoundedRect(rect, rad, rad)
            else:
                p.drawEllipse(rect)
        p.end()
        self.ed.commit(names[kind])
