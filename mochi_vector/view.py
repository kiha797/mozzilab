"""모찌벡터 작업 화면 (대지 + 개체 + 선택 손잡이 + 각 도구의 마우스 동작)"""
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView

from vector_items import (GroupItem, ShapeItem, TextItem, VMixin, build_subpaths, forget, leaves, node,
                          to_path_item)

HANDLE = 8          # 손잡이 크기 (화면 픽셀)
SHAPE_TOOLS = ("rect", "roundrect", "ellipse", "polygon", "star", "line")


class Artboard(QGraphicsRectItem):
    """흰 종이(대지)"""

    def __init__(self, w, h):
        super().__init__(0, 0, w, h)
        self.setBrush(Qt.white)
        self.setPen(Qt.NoPen)
        self.setZValue(-1e9)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setAcceptedMouseButtons(Qt.NoButton)


def rotate_point(p, c, deg):
    a = math.radians(deg)
    dx, dy = p.x() - c.x(), p.y() - c.y()
    return QPointF(c.x() + dx * math.cos(a) - dy * math.sin(a), c.y() + dx * math.sin(a) + dy * math.cos(a))


def simplify(pts, eps):
    """연필로 그린 점들을 줄이기 (더글라스-포이커)"""
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dx, dy = b.x() - a.x(), b.y() - a.y()
    ln = math.hypot(dx, dy) or 1e-9
    best, idx = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i].x() - dx * pts[i].y() + b.x() * a.y() - b.y() * a.x()) / ln
        if d > best:
            best, idx = d, i
    if best > eps:
        return simplify(pts[:idx + 1], eps)[:-1] + simplify(pts[idx:], eps)
    return [a, b]


def smooth_nodes(pts):
    """점들을 지나는 부드러운 곡선(캣멀-롬 → 베지어) 기준점 목록"""
    ns = [node(p.x(), p.y()) for p in pts]
    for i in range(len(pts)):
        p0 = pts[max(0, i - 1)]
        p2 = pts[min(len(pts) - 1, i + 1)]
        tx, ty = (p2.x() - p0.x()) / 6, (p2.y() - p0.y()) / 6
        if 0 < i < len(pts) - 1:
            ns[i][2:4] = [pts[i].x() - tx, pts[i].y() - ty]
            ns[i][4:6] = [pts[i].x() + tx, pts[i].y() + ty]
        elif i == 0 and len(pts) > 1:
            ns[i][4:6] = [pts[i].x() + tx, pts[i].y() + ty]
        elif len(pts) > 1:
            ns[i][2:4] = [pts[i].x() - tx, pts[i].y() - ty]
    return ns


class VView(QGraphicsView):
    zoomChanged = Signal(float)
    cursorMoved = Signal(float, float)
    message = Signal(str)

    def __init__(self, ed):
        super().__init__()
        self.ed = ed
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setBackgroundBrush(QColor("#2b2a2e"))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setMouseTracking(True)
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)
        self.artboard = None
        self.tool = "select"
        self.drag = None
        self.space = False
        self.pen_item = None          # 펜 도구로 그리는 중인 패스
        self.mouse_scene = QPointF()
        self.editing_text = None

    # ---------- 대지 ----------
    def set_artboard(self, w, h):
        sc = self.scene()
        if self.artboard is not None and self.artboard.scene():
            sc.removeItem(self.artboard)
        self.artboard = Artboard(w, h)
        sc.addItem(self.artboard)
        m = max(w, h) * 2 + 400
        sc.setSceneRect(-m, -m, w + 2 * m, h + 2 * m)

    def objects(self):
        """대지 위의 맨 위 개체들 (아래 → 위 순서)"""
        return sorted([it for it in self.scene().items() if isinstance(it, VMixin) and it.parentItem() is None],
                      key=lambda it: it.zValue())

    def selected(self):
        return sorted([it for it in self.scene().selectedItems() if isinstance(it, VMixin)], key=lambda it: it.zValue())

    def clear_objects(self):
        for it in self.objects():
            self.remove(it)

    def remove(self, it):
        if it.scene() is self.scene():
            self.scene().removeItem(it)
        forget(it)

    # ---------- 확대 ----------
    def zoom(self):
        return self.transform().m11()

    def zoom_by(self, f, anchor_view=None):
        z = self.zoom()
        f = max(0.02 / z, min(64 / z, f))
        if anchor_view is None:
            self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.scale(f, f)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.zoomChanged.emit(self.zoom())

    def fit(self):
        if self.artboard:
            r = self.artboard.rect()
            m = max(r.width(), r.height()) * 0.06
            self.fitInView(r.adjusted(-m, -m, m, m), Qt.KeepAspectRatio)
            self.zoomChanged.emit(self.zoom())

    def actual_size(self):
        self.setTransform(QTransform())
        if self.artboard:
            self.centerOn(self.artboard.rect().center())
        self.zoomChanged.emit(1.0)

    def wheelEvent(self, e):
        if e.modifiers() & (Qt.ControlModifier | Qt.AltModifier):
            self.zoom_by(1.15 if e.angleDelta().y() > 0 else 1 / 1.15, e.position())
        else:
            super().wheelEvent(e)

    # ---------- 도구 ----------
    def set_tool(self, tool):
        self.finish_pen()
        self.end_text_edit()
        self.tool = tool
        self.setDragMode(QGraphicsView.RubberBandDrag if tool == "select" else QGraphicsView.NoDrag)
        self.update_cursor()
        self.viewport().update()

    def update_cursor(self):
        if self.space or self.tool == "hand":
            self.viewport().setCursor(Qt.OpenHandCursor)
        elif self.tool in ("select", "direct"):
            self.viewport().setCursor(Qt.ArrowCursor)
        elif self.tool == "text":
            self.viewport().setCursor(Qt.IBeamCursor)
        elif self.tool == "zoom":
            self.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.viewport().setCursor(Qt.CrossCursor)

    # ---------- 선택 상자 ----------
    def selection_rect(self, items=None):
        items = self.selected() if items is None else items
        r = QRectF()
        for it in items:
            for lf in leaves(it):
                br = lf.sceneBoundingRect() if not isinstance(lf, ShapeItem) else lf.sceneTransform().map(lf.path()).boundingRect()
                if isinstance(lf, ShapeItem) and lf.style.get("stroke") and lf.style["stroke_w"] > 0:
                    hw = lf.style["stroke_w"] / 2
                    br = br.adjusted(-hw, -hw, hw, hw)
                r = br if r.isNull() else r.united(br)
        return r

    def handle_points(self, r):
        s = 1 / self.zoom()
        pts = [r.topLeft(), QPointF(r.center().x(), r.top()), r.topRight(), QPointF(r.right(), r.center().y()),
               r.bottomRight(), QPointF(r.center().x(), r.bottom()), r.bottomLeft(), QPointF(r.left(), r.center().y())]
        pts.append(QPointF(r.center().x(), r.top() - 24 * s))      # 회전 손잡이
        return pts

    def hit_handle(self, view_pos):
        sel = self.selected()
        if not sel or self.tool != "select":
            return None
        r = self.selection_rect(sel)
        for i, p in enumerate(self.handle_points(r)):
            v = self.mapFromScene(p)
            if abs(v.x() - view_pos.x()) <= HANDLE and abs(v.y() - view_pos.y()) <= HANDLE:
                return i
        return None

    def drawForeground(self, p, rect):
        s = 1 / self.zoom()
        accent = QColor("#ff6f91")
        sel = self.selected()
        if sel and self.tool in ("select", "direct"):
            pen = QPen(QColor("#4d96ff"), 1)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            for it in sel:
                for lf in leaves(it):
                    if isinstance(lf, ShapeItem):
                        p.drawPath(lf.sceneTransform().map(lf.path()))
                    else:
                        p.drawPolygon(lf.mapToScene(lf.boundingRect()))
        if sel and self.tool == "select":
            r = self.selection_rect(sel)
            pen = QPen(accent, 1)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRect(r)
            hp = self.handle_points(r)
            p.drawLine(QPointF(r.center().x(), r.top()), hp[8])
            p.setBrush(Qt.white)
            hs = HANDLE * s
            for q in hp[:8]:
                p.drawRect(QRectF(q.x() - hs / 2, q.y() - hs / 2, hs, hs))
            p.setBrush(accent)
            p.drawEllipse(hp[8], hs / 1.6, hs / 1.6)
        if self.tool in ("direct", "pen"):
            target = self.pen_item if self.tool == "pen" else (sel[0] if len(sel) == 1 and isinstance(sel[0], ShapeItem)
                                                                 and sel[0].kind in ("path", "line") else None)
            if target is not None:
                self._draw_nodes(p, target, s)
        if self.tool == "pen" and self.pen_item is not None and not self.drag:
            ns = self.pen_item.params["subpaths"][0]["nodes"]
            last = self.pen_item.mapToScene(QPointF(ns[-1][4], ns[-1][5]))
            lastp = self.pen_item.mapToScene(QPointF(ns[-1][0], ns[-1][1]))
            path = QPainterPath(lastp)
            path.cubicTo(last, self.mouse_scene, self.mouse_scene)
            pen = QPen(accent, 1, Qt.DashLine)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)
        d = self.drag
        if d and d.get("pencil"):
            pen = QPen(QColor(self.ed.props.stroke_color() or QColor("#333")), max(1, self.ed.props.stroke_w.value()))
            p.setPen(pen)
            path = QPainterPath(d["pencil"][0])
            for q in d["pencil"][1:]:
                path.lineTo(q)
            p.setBrush(Qt.NoBrush)
            p.drawPath(path)

    def _draw_nodes(self, p, it, s):
        hs = 7 * s
        pen = QPen(QColor("#4d96ff"), 1)
        pen.setCosmetic(True)
        sel_node = self.drag.get("node") if self.drag else None
        for si, sp in enumerate(it.params["subpaths"]):
            for ni, nd in enumerate(sp["nodes"]):
                a = it.mapToScene(QPointF(nd[0], nd[1]))
                for hx, hy in ((nd[2], nd[3]), (nd[4], nd[5])):
                    if (hx, hy) != (nd[0], nd[1]):
                        h = it.mapToScene(QPointF(hx, hy))
                        p.setPen(pen)
                        p.drawLine(a, h)
                        p.setBrush(QColor("#4d96ff"))
                        p.drawEllipse(h, hs / 2.2, hs / 2.2)
                p.setPen(pen)
                p.setBrush(QColor("#4d96ff") if sel_node == (si, ni) else Qt.white)
                p.drawRect(QRectF(a.x() - hs / 2, a.y() - hs / 2, hs, hs))

    def hit_node(self, it, view_pos):
        """직접 선택: 기준점(0) 또는 손잡이(1: 들어오는, 2: 나가는)"""
        best = None
        for si, sp in enumerate(it.params["subpaths"]):
            for ni, nd in enumerate(sp["nodes"]):
                for part, (x, y) in ((0, (nd[0], nd[1])), (1, (nd[2], nd[3])), (2, (nd[4], nd[5]))):
                    if part and (x, y) == (nd[0], nd[1]):
                        continue
                    v = self.mapFromScene(it.mapToScene(QPointF(x, y)))
                    dist = math.hypot(v.x() - view_pos.x(), v.y() - view_pos.y())
                    if dist <= 7 and (best is None or dist < best[0] or (part == 0 and best[3] != 0)):
                        best = (dist, si, ni, part)
        return best[1:] if best else None

    def top_item_at(self, view_pos):
        for it in self.items(view_pos):
            while it.parentItem() is not None:
                it = it.parentItem()
            if isinstance(it, VMixin) and not it.locked:
                return it
        return None

    # ---------- 마우스 ----------
    def mousePressEvent(self, e):
        vp = e.position().toPoint()
        sp = self.mapToScene(vp)
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and (self.space or self.tool == "hand")):
            self.drag = {"kind": "pan", "start": e.position(), "h": self.horizontalScrollBar().value(),
                         "v": self.verticalScrollBar().value()}
            self.viewport().setCursor(Qt.ClosedHandCursor)
            return
        if e.button() != Qt.LeftButton:
            return super().mousePressEvent(e)
        if self.editing_text is not None:
            it = self.top_item_at(vp)
            if it is self.editing_text:
                return super().mousePressEvent(e)
            self.end_text_edit()
        t = self.tool
        mods = e.modifiers()
        if t == "zoom":
            self.zoom_by(1 / 1.5 if mods & Qt.AltModifier else 1.5, e.position())
            return
        if t == "select":
            h = self.hit_handle(vp)
            if h is not None:
                self.begin_transform(h, sp)
                return
            super().mousePressEvent(e)
            self.drag = {"kind": "move", "pos": {it: QPointF(it.pos()) for it in self.selected()}}
            return
        if t == "direct":
            sel = self.selected()
            if len(sel) == 1 and isinstance(sel[0], ShapeItem) and sel[0].kind in ("path", "line"):
                hit = self.hit_node(sel[0], vp)
                if hit:
                    si, ni, part = hit
                    it = sel[0]
                    self.last_node = (it, (si, ni))
                    self.drag = {"kind": "node", "item": it, "node": (si, ni), "part": part,
                                 "orig": [list(n) for n in it.params["subpaths"][si]["nodes"]], "start": sp,
                                 "alt": bool(mods & Qt.AltModifier)}
                    self.viewport().update()
                    return
            it = self.top_item_at(vp)
            self.scene().clearSelection()
            if it is not None:
                lf = it
                if isinstance(it, GroupItem):      # 그룹 안의 개체를 바로 고른다
                    for x in self.items(vp):
                        if isinstance(x, ShapeItem) and not isinstance(x, GroupItem):
                            lf = x
                            break
                if isinstance(lf, ShapeItem) and lf.kind not in ("path", "line"):
                    self.message.emit("이 도형은 [개체 > 패스로 바꾸기] 후에 점을 편집할 수 있어요.")
                if lf is not it:
                    lf.setFlag(QGraphicsItem.ItemIsSelectable, True)
                lf.setSelected(True)
            self.ed.selection_changed()
            self.viewport().update()
            return
        if t == "pen":
            self.pen_press(sp, mods)
            return
        if t == "pencil":
            self.drag = {"kind": "pencil", "pencil": [sp]}
            return
        if t in SHAPE_TOOLS:
            self.begin_shape(sp, mods)
            return
        if t == "text":
            it = self.top_item_at(vp)
            if isinstance(it, TextItem):
                self.start_text_edit(it)
                super().mousePressEvent(e)
            else:
                self.ed.add_text(sp)
            return
        if t == "eyedrop":
            it = self.top_item_at(vp)
            if it is not None:
                self.ed.eyedrop(it)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        sp = self.mapToScene(e.position().toPoint())
        self.mouse_scene = sp
        self.cursorMoved.emit(sp.x(), sp.y())
        d = self.drag
        if d is None:
            if self.tool == "pen":
                self.viewport().update()
            elif self.tool == "select":
                h = self.hit_handle(e.position().toPoint())
                if h is not None:
                    self.viewport().setCursor([Qt.SizeFDiagCursor, Qt.SizeVerCursor, Qt.SizeBDiagCursor,
                                               Qt.SizeHorCursor, Qt.SizeFDiagCursor, Qt.SizeVerCursor,
                                               Qt.SizeBDiagCursor, Qt.SizeHorCursor, Qt.CrossCursor][h])
                elif not self.space:
                    self.viewport().setCursor(Qt.ArrowCursor)
            return super().mouseMoveEvent(e)
        k = d["kind"]
        if k == "pan":
            delta = e.position() - d["start"]
            self.horizontalScrollBar().setValue(int(d["h"] - delta.x()))
            self.verticalScrollBar().setValue(int(d["v"] - delta.y()))
        elif k == "move":
            super().mouseMoveEvent(e)
            self.ed.update_props_geometry()
        elif k == "transform":
            self.continue_transform(sp, e.modifiers())
        elif k == "node":
            self.move_node(sp, e.modifiers())
        elif k == "pen":
            self.pen_drag(sp)
        elif k == "pencil":
            d["pencil"].append(sp)
            self.viewport().update()
        elif k == "shape":
            self.continue_shape(sp, e.modifiers())
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        d = self.drag
        self.drag = None
        if d is None:
            return super().mouseReleaseEvent(e)
        k = d["kind"]
        if k == "pan":
            self.update_cursor()
        elif k == "move":
            super().mouseReleaseEvent(e)
            moved = any(it.pos() != p for it, p in d["pos"].items() if it.scene())
            if moved:
                self.ed.commit("이동")
            self.ed.selection_changed()
        elif k == "transform":
            for it in self.selected():
                if isinstance(it, GroupItem):
                    it.refresh()
            self.ed.commit("회전" if d["handle"] == 8 else "크기 조절")
        elif k == "node":
            d["item"].normalize()
            self.ed.commit("점 편집")
        elif k == "pen":
            self.viewport().update()
        elif k == "pencil":
            self.finish_pencil(d["pencil"])
        elif k == "shape":
            self.finish_shape(d)
        self.viewport().update()

    def mouseDoubleClickEvent(self, e):
        it = self.top_item_at(e.position().toPoint())
        if self.tool == "pen":
            self.finish_pen()
            return
        if self.tool == "select" and isinstance(it, TextItem):
            self.start_text_edit(it)
            return super().mouseDoubleClickEvent(e)
        if self.tool == "select" and isinstance(it, ShapeItem) and it.kind in ("path", "line"):
            self.ed.set_tool("direct")
            it.setSelected(True)
            return
        super().mouseDoubleClickEvent(e)

    # ---------- 크기 조절 · 회전 ----------
    def begin_transform(self, h, sp):
        sel = self.selected()
        r = self.selection_rect(sel)
        info = []
        for it in sel:
            for lf in leaves(it):
                info.append((lf, lf.capture(), lf.center_scene(), lf.angle))
        self.drag = {"kind": "transform", "handle": h, "rect": r, "info": info, "start": sp,
                     "a0": math.degrees(math.atan2(sp.y() - r.center().y(), sp.x() - r.center().x()))}

    def continue_transform(self, sp, mods):
        d = self.drag
        r = d["rect"]
        h = d["handle"]
        if h == 8:
            c = r.center()
            delta = math.degrees(math.atan2(sp.y() - c.y(), sp.x() - c.x())) - d["a0"]
            if mods & Qt.ShiftModifier:
                delta = round(delta / 15) * 15
            for lf, cap, c0, a0 in d["info"]:
                lf.set_angle(a0 + delta)
                lf.set_center_scene(rotate_point(c0, c, delta))
            self.message.emit(f"회전 {round(delta, 1)}°")
        else:
            sx = sy = 1.0
            ax, ay = r.center().x(), r.center().y()
            if h in (2, 3, 4):
                ax = r.left()
                sx = (sp.x() - r.left()) / (r.width() or 1)
            elif h in (0, 6, 7):
                ax = r.right()
                sx = (r.right() - sp.x()) / (r.width() or 1)
            if h in (4, 5, 6):
                ay = r.top()
                sy = (sp.y() - r.top()) / (r.height() or 1)
            elif h in (0, 1, 2):
                ay = r.bottom()
                sy = (r.bottom() - sp.y()) / (r.height() or 1)
            if mods & Qt.AltModifier:        # 가운데를 기준으로
                ax, ay = r.center().x(), r.center().y()
                sx, sy = (sx * 2 - 1 if h not in (1, 5) else 1), (sy * 2 - 1 if h not in (3, 7) else 1)
            if h in (1, 5):
                sx = 1.0
            if h in (3, 7):
                sy = 1.0
            if mods & Qt.ShiftModifier or (len(d["info"]) == 1 and isinstance(d["info"][0][0], TextItem)):
                if h in (1, 5):
                    sx = sy
                elif h in (3, 7):
                    sy = sx
                else:
                    sx = sy = max(sx, sy)
            sx, sy = max(sx, 0.005), max(sy, 0.005)
            for lf, cap, c0, a0 in d["info"]:
                rad = math.radians(a0)
                lsx, lsy = (sy, sx) if abs(math.sin(rad)) > 0.7071 else (sx, sy)
                lf.resize_from(cap, cap["w"] * lsx, cap["h"] * lsy)
                lf.set_angle(a0)
                lf.set_center_scene(QPointF(ax + (c0.x() - ax) * sx, ay + (c0.y() - ay) * sy))
            self.message.emit(f"{round(r.width() * sx, 1)} × {round(r.height() * sy, 1)}")
        self.ed.update_props_geometry()
        self.viewport().update()

    def apply_frame(self, target):
        """선택 상자를 target 사각형으로 (속성 패널의 X · Y · W · H 입력)"""
        sel = self.selected()
        r = self.selection_rect(sel)
        if r.isNull():
            return
        sx = target.width() / (r.width() or 1)
        sy = target.height() / (r.height() or 1)
        for it in sel:
            for lf in leaves(it):
                cap, c0, a0 = lf.capture(), lf.center_scene(), lf.angle
                if abs(sx - 1) > 1e-9 or abs(sy - 1) > 1e-9:
                    lsx, lsy = (sy, sx) if abs(math.sin(math.radians(a0))) > 0.7071 else (sx, sy)
                    lf.resize_from(cap, cap["w"] * lsx, cap["h"] * lsy)
                    lf.set_angle(a0)
                lf.set_center_scene(QPointF(target.left() + (c0.x() - r.left()) * sx,
                                            target.top() + (c0.y() - r.top()) * sy))
            if isinstance(it, GroupItem):
                it.refresh()

    def rotate_selection(self, delta, center=None):
        sel = self.selected()
        c = center or self.selection_rect(sel).center()
        for it in sel:
            for lf in leaves(it):
                c0, a0 = lf.center_scene(), lf.angle
                lf.set_angle(a0 + delta)
                lf.set_center_scene(rotate_point(c0, c, delta))
            if isinstance(it, GroupItem):
                it.refresh()

    def flip_selection(self, horizontal):
        sel = self.selected()
        r = self.selection_rect(sel)
        c = r.center()
        for it in sel:
            for lf in leaves(it):
                c0 = lf.center_scene()
                lf.mirror(horizontal)
                lf.set_angle(-lf.angle)
                if horizontal:
                    lf.set_center_scene(QPointF(2 * c.x() - c0.x(), c0.y()))
                else:
                    lf.set_center_scene(QPointF(c0.x(), 2 * c.y() - c0.y()))
            if isinstance(it, GroupItem):
                it.refresh()

    # ---------- 점 편집 ----------
    def move_node(self, sp, mods):
        d = self.drag
        it = d["item"]
        si, ni = d["node"]
        nodes = it.params["subpaths"][si]["nodes"]
        orig = d["orig"][ni]
        lp = it.mapFromScene(sp)
        ls = it.mapFromScene(d["start"])
        dx, dy = lp.x() - ls.x(), lp.y() - ls.y()
        nd = nodes[ni]
        if d["part"] == 0:
            for i in (0, 2, 4):
                nd[i] = orig[i] + dx
                nd[i + 1] = orig[i + 1] + dy
        else:
            i = 2 if d["part"] == 1 else 4
            nd[i], nd[i + 1] = orig[i] + dx, orig[i + 1] + dy
            if not d["alt"] and not (mods & Qt.AltModifier):     # 반대쪽 손잡이도 대칭으로
                j = 4 if i == 2 else 2
                if (orig[j], orig[j + 1]) != (orig[0], orig[1]):
                    nd[j], nd[j + 1] = 2 * nd[0] - nd[i], 2 * nd[1] - nd[i + 1]
        it.rebuild()
        self.viewport().update()

    def delete_node(self):
        sel = self.selected()
        d = getattr(self, "last_node", None)
        if not (len(sel) == 1 and isinstance(sel[0], ShapeItem) and d and d[0] is sel[0]):
            return False
        it, (si, ni) = d
        sub = it.params["subpaths"][si]
        if len(sub["nodes"]) <= 2:
            return False
        del sub["nodes"][ni]
        it.rebuild()
        it.normalize()
        self.last_node = None
        self.ed.commit("점 삭제")
        return True

    # ---------- 펜 ----------
    def pen_press(self, sp, mods):
        it = self.pen_item
        if it is None:
            it = ShapeItem("path", 0, 0, "패스")
            it.params["subpaths"] = [{"nodes": [], "closed": False}]
            it.style = self.ed.props.current_style()
            it.setPos(0, 0)
            it.setZValue(self.ed.next_z())
            self.scene().addItem(it)
            self.pen_item = it
        nodes = it.params["subpaths"][0]["nodes"]
        lp = it.mapFromScene(sp)
        if len(nodes) > 2:
            first = self.mapFromScene(it.mapToScene(QPointF(nodes[0][0], nodes[0][1])))
            v = self.mapFromScene(sp)
            if math.hypot(first.x() - v.x(), first.y() - v.y()) < 9:       # 첫 점을 누르면 닫힌 도형
                it.params["subpaths"][0]["closed"] = True
                it.rebuild()
                self.finish_pen(closed=True)
                return
        if mods & Qt.ShiftModifier and nodes:            # 45도 단위
            a = QPointF(nodes[-1][0], nodes[-1][1])
            ang = round(math.atan2(lp.y() - a.y(), lp.x() - a.x()) / (math.pi / 4)) * (math.pi / 4)
            ln = math.hypot(lp.x() - a.x(), lp.y() - a.y())
            lp = QPointF(a.x() + ln * math.cos(ang), a.y() + ln * math.sin(ang))
        nodes.append(node(lp.x(), lp.y()))
        it.rebuild()
        self.drag = {"kind": "pen", "start": sp}
        self.viewport().update()

    def pen_drag(self, sp):
        it = self.pen_item
        nd = it.params["subpaths"][0]["nodes"][-1]
        lp = it.mapFromScene(sp)
        nd[4], nd[5] = lp.x(), lp.y()
        nd[2], nd[3] = 2 * nd[0] - lp.x(), 2 * nd[1] - lp.y()
        it.rebuild()
        self.viewport().update()

    def finish_pen(self, closed=False):
        it = self.pen_item
        if it is None:
            return
        self.pen_item = None
        nodes = it.params["subpaths"][0]["nodes"]
        if len(nodes) < 2:
            self.remove(it)
            self.viewport().update()
            return
        if not closed:
            it.style["fill"] = None if it.style.get("fill") and not self.ed.props.fill_open_paths() else it.style["fill"]
        it.rebuild()
        it.normalize()
        self.scene().clearSelection()
        it.setSelected(True)
        self.ed.commit("펜")

    # ---------- 연필 ----------
    def finish_pencil(self, pts):
        if len(pts) < 2:
            return
        pts = simplify(pts, 1.5 / self.zoom())
        it = ShapeItem("path", 0, 0, "연필")
        closed = len(pts) > 3 and math.hypot(pts[0].x() - pts[-1].x(), pts[0].y() - pts[-1].y()) < 8 / self.zoom()
        if closed:
            pts = pts[:-1]
        it.params["subpaths"] = [{"nodes": smooth_nodes(pts), "closed": closed}]
        it.style = self.ed.props.current_style()
        if not closed:
            it.style["fill"] = None
        if it.style.get("stroke") is None:
            it.style["stroke"] = "#ff3b2f2f"
        it.setZValue(self.ed.next_z())
        self.scene().addItem(it)
        it.rebuild()
        it.normalize()
        self.scene().clearSelection()
        it.setSelected(True)
        self.ed.commit("연필")

    # ---------- 도형 ----------
    def begin_shape(self, sp, mods):
        t = self.tool
        kind = {"roundrect": "rect"}.get(t, t)
        props = self.ed.props
        if t == "line":
            it = ShapeItem("line", 0, 0, "선")
            it.params["subpaths"] = [{"nodes": [node(0, 0), node(0, 0)], "closed": False}]
        else:
            it = ShapeItem(kind, 0, 0, None, rx=props.default_rx() if t == "roundrect" else 0,
                           sides=props.default_sides(), points=props.default_points())
        it.style = props.current_style()
        if t == "line" and it.style.get("stroke") is None:
            it.style["stroke"] = "#ff3b2f2f"
        it.setPos(sp)
        it.setZValue(self.ed.next_z())
        it.rebuild()
        self.scene().addItem(it)
        self.drag = {"kind": "shape", "item": it, "start": sp, "moved": False}

    def continue_shape(self, sp, mods):
        d = self.drag
        it = d["item"]
        a = d["start"]
        d["moved"] = True
        if it.kind == "line":
            b = sp
            if mods & Qt.ShiftModifier:
                ang = round(math.atan2(b.y() - a.y(), b.x() - a.x()) / (math.pi / 4)) * (math.pi / 4)
                ln = math.hypot(b.x() - a.x(), b.y() - a.y())
                b = QPointF(a.x() + ln * math.cos(ang), a.y() + ln * math.sin(ang))
            it.setPos(0, 0)
            it.params["subpaths"][0]["nodes"] = [node(a.x(), a.y()), node(b.x(), b.y())]
            it.w = it.h = 0
            it.rebuild()
            return
        dx, dy = sp.x() - a.x(), sp.y() - a.y()
        if mods & Qt.ShiftModifier:
            m = max(abs(dx), abs(dy))
            dx, dy = math.copysign(m, dx or 1), math.copysign(m, dy or 1)
        if mods & Qt.AltModifier:
            r = QRectF(a.x() - abs(dx), a.y() - abs(dy), abs(dx) * 2, abs(dy) * 2)
        else:
            r = QRectF(a, QPointF(a.x() + dx, a.y() + dy)).normalized()
        it.setPos(r.topLeft())
        it.w, it.h = r.width(), r.height()
        it.rebuild()
        self.message.emit(f"{round(r.width(), 1)} × {round(r.height(), 1)}")

    def finish_shape(self, d):
        it = d["item"]
        if it.kind == "line":
            if not d["moved"]:
                self.remove(it)
                return
            it.normalize()
        elif not d["moved"] or (it.w < 2 and it.h < 2):
            s = 100
            it.setPos(d["start"] - QPointF(s / 2, s / 2))
            it.w = it.h = s
            it.rebuild()
        self.scene().clearSelection()
        it.setSelected(True)
        self.ed.commit(it.name + " 그리기")

    # ---------- 문자 편집 ----------
    def start_text_edit(self, it):
        self.end_text_edit()
        self.editing_text = it
        it.setTextInteractionFlags(Qt.TextEditorInteraction)
        it.on_edit_end = self._text_done
        it.setFocus()

    def end_text_edit(self):
        it = self.editing_text
        if it is not None:
            it.clearFocus()
            self._text_done(it)

    def _text_done(self, it):
        if self.editing_text is not it:
            return
        self.editing_text = None
        it.setTextInteractionFlags(Qt.NoTextInteraction)
        c = it.textCursor()
        c.clearSelection()
        it.setTextCursor(c)
        old = it.params["text"]
        it.sync_text()
        if not it.params["text"].strip():
            self.remove(it)
            self.ed.commit("문자 삭제")
        elif old != it.params["text"] or getattr(it, "is_new", False):
            it.is_new = False
            it.name = "T " + it.params["text"].split("\n")[0][:14]
            self.ed.commit("문자")

    # ---------- 키보드 ----------
    def keyPressEvent(self, e):
        if self.editing_text is not None:
            return super().keyPressEvent(e)
        k = e.key()
        if k == Qt.Key_Space and not e.isAutoRepeat():
            self.space = True
            self.update_cursor()
            return
        if e.modifiers() & (Qt.ControlModifier | Qt.MetaModifier):
            return super().keyPressEvent(e)
        if k in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape) and self.pen_item is not None:
            self.finish_pen()
        elif k == Qt.Key_Escape:
            self.scene().clearSelection()
            self.ed.selection_changed()
        elif k in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.tool == "direct" and self.delete_node():
                return
            self.ed.delete_selected()
        elif k in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            step = 10 if e.modifiers() & Qt.ShiftModifier else 1
            dx = {Qt.Key_Left: -step, Qt.Key_Right: step}.get(k, 0)
            dy = {Qt.Key_Up: -step, Qt.Key_Down: step}.get(k, 0)
            self.ed.nudge(dx, dy)
        elif e.text() and (e.text().isalpha() or e.text() in "\\"):
            self.ed.tool_shortcut(e.text())
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Space and not e.isAutoRepeat() and self.space:
            self.space = False
            self.update_cursor()
            return
        super().keyReleaseEvent(e)

    def enterEvent(self, e):
        if self.editing_text is None:
            self.setFocus()
        super().enterEvent(e)


def node_count(item):
    return sum(len(sp["nodes"]) for sp in item.params["subpaths"])


__all__ = ["VView", "build_subpaths", "to_path_item", "node_count"]
