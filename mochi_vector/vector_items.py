"""모찌벡터 개체(도형)들
모든 개체는 '상자(가로 w × 세로 h)' 안에 그려지고, 상자 가운데를 기준으로 회전한다.
- ShapeItem: 사각형 · 타원 · 다각형 · 별 · 패스(펜으로 그린 선/곡선)
- TextItem: 문자 / ImageItem: 그림 / GroupItem: 그룹"""
import base64
import copy
import math

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QLinearGradient, QPainterPath, QPen,
                           QPixmap, QTransform)
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsItemGroup, QGraphicsPathItem, QGraphicsTextItem,
                               QStyle)

DEFAULT_STYLE = {
    "fill": "#ffff6f91",     # #AARRGGBB, None = 채우기 없음
    "fill2": None,           # 그레이디언트 끝 색 (None 이면 단색)
    "grad_angle": 0,
    "stroke": "#ff3b2f2f",   # None = 선 없음
    "stroke_w": 2.0,
    "dash": 0,               # 0 실선 1 파선 2 점선
    "join": 0,               # 0 각지게 1 둥글게
    "opacity": 1.0,
}
DASHES = [None, [6, 4], [1, 3]]
KIND_NAMES = {"rect": "사각형", "ellipse": "타원", "polygon": "다각형", "star": "별", "path": "패스",
              "line": "선", "text": "문자", "image": "이미지", "group": "그룹"}


def qcolor(s):
    return None if s is None else QColor(s)


def cstr(c):
    return None if c is None else QColor(c).name(QColor.HexArgb)


LIVE = set()     # 파이썬 쪽 개체가 사라지지 않도록 붙잡아 둔다 (PySide 는 장면에 넣어도 놓아버릴 때가 있음)


def forget(item):
    """장면에서 지운 개체(와 그 안의 개체)를 놓아준다"""
    for k in item.childItems():
        forget(k)
    LIVE.discard(item)


class VMixin:
    """모든 개체가 함께 쓰는 기능 (이름 · 잠금 · 회전 · 저장/불러오기)"""
    kind = ""

    def init_v(self, name=None):
        LIVE.add(self)
        self.name = name or KIND_NAMES.get(self.kind, "개체")
        self.style = dict(DEFAULT_STYLE)
        self.angle = 0.0
        self.locked = False
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)

    # 위치 / 회전
    def center_scene(self):
        return self.mapToScene(QPointF(self.w / 2, self.h / 2))

    def set_center_scene(self, c):
        par = self.parentItem()
        local = par.mapFromScene(c) if par else c
        self.setPos(local - QPointF(self.w / 2, self.h / 2))

    def set_angle(self, a):
        a = (a + 180) % 360 - 180
        self.angle = 0.0 if abs(a) < 1e-6 else a
        self.setTransformOriginPoint(self.w / 2, self.h / 2)
        self.setRotation(self.angle)

    def set_locked(self, v):
        self.locked = v
        if isinstance(self.parentItem(), GroupItem):
            return
        self.setFlag(QGraphicsItem.ItemIsMovable, not v)
        self.setFlag(QGraphicsItem.ItemIsSelectable, not v)
        if v:
            self.setSelected(False)

    def base_dict(self):
        return {"type": self.kind, "name": self.name, "x": round(self.pos().x(), 3), "y": round(self.pos().y(), 3),
                "angle": round(self.angle, 4), "visible": self.isVisible(), "locked": self.locked,
                "style": dict(self.style)}

    def apply_base(self, d):
        self.name = d.get("name", self.name)
        self.style = {**DEFAULT_STYLE, **d.get("style", {})}
        self.setPos(d.get("x", 0), d.get("y", 0))
        self.setVisible(d.get("visible", True))
        self.rebuild()
        self.set_angle(d.get("angle", 0))
        self.set_locked(d.get("locked", False))

    def paint_clean(self, base_paint, painter, option, widget):
        """선택됐을 때 Qt 가 그리는 점선 테두리는 빼고 그린다 (손잡이는 화면에서 따로 그림)"""
        option.state &= ~QStyle.State_Selected
        option.state &= ~QStyle.State_HasFocus
        base_paint(self, painter, option, widget)

    def capture(self):
        return {"w": self.w, "h": self.h}

    def mirror(self, horizontal):
        pass


# ---------- 경로(패스) 도우미 ----------
def node(x, y):
    return [x, y, x, y, x, y]      # 기준점, 들어오는 손잡이, 나가는 손잡이


def build_subpaths(subpaths):
    path = QPainterPath()
    for sp in subpaths:
        ns = sp["nodes"]
        if not ns:
            continue
        path.moveTo(ns[0][0], ns[0][1])
        segs = list(zip(ns, ns[1:]))
        if sp.get("closed") and len(ns) > 1:
            segs.append((ns[-1], ns[0]))
        for a, b in segs:
            if a[4] == a[0] and a[5] == a[1] and b[2] == b[0] and b[3] == b[1]:
                path.lineTo(b[0], b[1])
            else:
                path.cubicTo(a[4], a[5], b[2], b[3], b[0], b[1])
        if sp.get("closed"):
            path.closeSubpath()
    return path


def path_to_subpaths(path):
    """QPainterPath → 편집할 수 있는 점 목록"""
    subs = []
    cur = None
    i = 0
    n = path.elementCount()
    while i < n:
        e = path.elementAt(i)
        if e.type == QPainterPath.MoveToElement:
            cur = {"nodes": [node(e.x, e.y)], "closed": False}
            subs.append(cur)
            i += 1
        elif e.type == QPainterPath.LineToElement:
            cur["nodes"].append(node(e.x, e.y))
            i += 1
        elif e.type == QPainterPath.CurveToElement:
            c1, c2, end = e, path.elementAt(i + 1), path.elementAt(i + 2)
            cur["nodes"][-1][4:6] = [c1.x, c1.y]
            cur["nodes"].append([end.x, end.y, c2.x, c2.y, end.x, end.y])
            i += 3
        else:
            i += 1
    for sp in subs:            # 처음과 끝이 같은 점이면 '닫힌 패스'
        ns = sp["nodes"]
        if len(ns) > 2 and abs(ns[0][0] - ns[-1][0]) < 1e-6 and abs(ns[0][1] - ns[-1][1]) < 1e-6:
            ns[0][2:4] = ns[-1][2:4]
            ns.pop()
            sp["closed"] = True
    return [sp for sp in subs if sp["nodes"]]


def regular_polygon(w, h, sides, inner=None, flipv=False):
    """정다각형 / 별 (inner = 안쪽 꼭짓점 비율) 을 w × h 상자에 꽉 차게"""
    n = sides * 2 if inner is not None else sides
    pts = []
    for i in range(n):
        a = -math.pi / 2 + i * 2 * math.pi / n
        r = inner if (inner is not None and i % 2) else 1.0
        y = math.sin(a) * r
        pts.append((math.cos(a) * r, -y if flipv else y))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    path = QPainterPath()
    for i, (x, y) in enumerate(pts):
        q = ((x - x0) / ((x1 - x0) or 1) * w, (y - y0) / ((y1 - y0) or 1) * h)
        (path.moveTo if i == 0 else path.lineTo)(*q)
    path.closeSubpath()
    return path


# ---------- 도형 ----------
class ShapeItem(QGraphicsPathItem, VMixin):
    def __init__(self, kind="rect", w=100, h=100, name=None, **params):
        super().__init__()
        self.kind = kind
        self.w, self.h = float(w), float(h)
        self.params = {"rx": 0.0, "sides": 6, "points": 5, "inner": 0.45, "flipv": False,
                       "subpaths": [], "fill_rule": 0}
        self.params.update(params)
        self.init_v(name)
        self.rebuild()

    def local_path(self):
        k, w, h, p = self.kind, self.w, self.h, self.params
        path = QPainterPath()
        if k == "rect":
            rx = min(p["rx"], w / 2, h / 2)
            if rx > 0:
                path.addRoundedRect(QRectF(0, 0, w, h), rx, rx)
            else:
                path.addRect(QRectF(0, 0, w, h))
        elif k == "ellipse":
            path.addEllipse(QRectF(0, 0, w, h))
        elif k == "polygon":
            path = regular_polygon(w, h, max(3, int(p["sides"])), None, p["flipv"])
        elif k == "star":
            path = regular_polygon(w, h, max(3, int(p["points"])), max(0.05, min(0.95, p["inner"])), p["flipv"])
        else:
            path = build_subpaths(p["subpaths"])
            path.setFillRule(Qt.OddEvenFill if p.get("fill_rule") else Qt.WindingFill)
        return path

    def is_open(self):
        return self.kind == "path" and all(not sp.get("closed") for sp in self.params["subpaths"])

    def rebuild(self):
        self.prepareGeometryChange()
        self.setPath(self.local_path())
        self.apply_style()
        self.setTransformOriginPoint(self.w / 2, self.h / 2)

    def apply_style(self):
        s = self.style
        if s["stroke"] is None or s["stroke_w"] <= 0:
            self.setPen(Qt.NoPen)
        else:
            pen = QPen(QColor(s["stroke"]), s["stroke_w"])
            pen.setJoinStyle(Qt.RoundJoin if s["join"] else Qt.MiterJoin)
            pen.setCapStyle(Qt.RoundCap if s["join"] else Qt.FlatCap)
            if DASHES[s["dash"]]:
                pen.setDashPattern(DASHES[s["dash"]])
            self.setPen(pen)
        if s["fill"] is None or self.kind == "line":
            self.setBrush(Qt.NoBrush)
        elif s["fill2"]:
            self.setBrush(QBrush(gradient(self.w, self.h, s)))
        else:
            self.setBrush(QColor(s["fill"]))
        self.setOpacity(s["opacity"])

    def paint(self, painter, option, widget=None):
        self.paint_clean(QGraphicsPathItem.paint, painter, option, widget)

    def capture(self):
        return {"w": self.w, "h": self.h, "subpaths": copy.deepcopy(self.params["subpaths"])}

    def resize_from(self, st, w, h):
        w, h = max(0.0, w), max(0.0, h)
        if self.kind in ("path", "line"):
            sx = w / st["w"] if st["w"] > 1e-6 else 1
            sy = h / st["h"] if st["h"] > 1e-6 else 1
            subs = copy.deepcopy(st["subpaths"])
            for sp in subs:
                for nd in sp["nodes"]:
                    for i in (0, 2, 4):
                        nd[i] *= sx
                        nd[i + 1] *= sy
            self.params["subpaths"] = subs
            if st["w"] <= 1e-6:
                w = st["w"]
            if st["h"] <= 1e-6:
                h = st["h"]
        self.w, self.h = max(w, 0.0), max(h, 0.0)
        self.rebuild()

    def mirror(self, horizontal):
        if self.kind in ("path", "line"):
            for sp in self.params["subpaths"]:
                for nd in sp["nodes"]:
                    for i in (0, 2, 4):
                        if horizontal:
                            nd[i] = self.w - nd[i]
                        else:
                            nd[i + 1] = self.h - nd[i + 1]
        elif self.kind in ("polygon", "star") and not horizontal:
            self.params["flipv"] = not self.params["flipv"]
        self.rebuild()

    def normalize(self):
        """패스의 점들이 상자 (0,0) 에서 시작하도록 맞춘다 (화면에 보이는 모양 · 위치는 그대로)"""
        if self.kind not in ("path", "line"):
            return
        r = build_subpaths(self.params["subpaths"]).boundingRect()
        tl = QPointF(r.x(), r.y())
        for sp in self.params["subpaths"]:
            for nd in sp["nodes"]:
                for i in (0, 2, 4):
                    nd[i] -= r.x()
                    nd[i + 1] -= r.y()
        c_old = QPointF(self.w / 2, self.h / 2)
        c_new = QPointF(r.width() / 2, r.height() / 2)
        new_pos = self.pos() + c_old - c_new + QTransform().rotate(self.angle).map(tl + c_new - c_old)
        self.w, self.h = r.width(), r.height()
        self.rebuild()
        self.setPos(new_pos)

    def to_dict(self):
        d = self.base_dict()
        d.update(w=round(self.w, 3), h=round(self.h, 3))
        if self.kind == "rect":
            d["rx"] = self.params["rx"]
        elif self.kind == "polygon":
            d.update(sides=self.params["sides"], flipv=self.params["flipv"])
        elif self.kind == "star":
            d.update(points=self.params["points"], inner=self.params["inner"], flipv=self.params["flipv"])
        elif self.kind in ("path", "line"):
            d.update(subpaths=[{"nodes": [[round(v, 3) for v in nd] for nd in sp["nodes"]],
                                "closed": sp.get("closed", False)} for sp in self.params["subpaths"]],
                     fill_rule=self.params.get("fill_rule", 0))
        return d

    def scene_shape(self):
        return self.sceneTransform().map(self.path())


def gradient(w, h, s):
    a = math.radians(s.get("grad_angle", 0))
    cx, cy = w / 2, h / 2
    r = (abs(math.cos(a)) * w + abs(math.sin(a)) * h) / 2
    g = QLinearGradient(cx - math.cos(a) * r, cy - math.sin(a) * r, cx + math.cos(a) * r, cy + math.sin(a) * r)
    g.setColorAt(0, QColor(s["fill"]))
    g.setColorAt(1, QColor(s["fill2"]))
    return g


# ---------- 문자 ----------
class TextItem(QGraphicsTextItem, VMixin):
    kind = "text"

    def __init__(self, text="문자", family="Malgun Gothic", size=36, bold=False, italic=False, name=None):
        super().__init__()
        self.params = {"text": text, "family": family, "size": float(size), "bold": bold, "italic": italic}
        self.init_v(name)
        self.style.update(fill="#ff3b2f2f", stroke=None)
        self.document().setDocumentMargin(0)
        self.rebuild()

    @property
    def w(self):
        return self.boundingRect().width()

    @property
    def h(self):
        return self.boundingRect().height()

    def qfont(self):
        f = QFont(self.params["family"])
        f.setPixelSize(max(1, int(round(self.params["size"]))))
        f.setBold(self.params["bold"])
        f.setItalic(self.params["italic"])
        return f

    def rebuild(self):
        self.prepareGeometryChange()
        self.setFont(self.qfont())
        if self.toPlainText() != self.params["text"]:
            self.setPlainText(self.params["text"])
        self.setDefaultTextColor(QColor(self.style["fill"] or "#00000000"))
        self.setOpacity(self.style["opacity"])
        self.setTransformOriginPoint(self.w / 2, self.h / 2)

    def apply_style(self):
        self.rebuild()

    def sync_text(self):
        self.params["text"] = self.toPlainText()
        self.setTransformOriginPoint(self.w / 2, self.h / 2)

    def paint(self, painter, option, widget=None):
        self.paint_clean(QGraphicsTextItem.paint, painter, option, widget)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        cb = getattr(self, "on_edit_end", None)
        if cb and self.textInteractionFlags() != Qt.NoTextInteraction:
            cb(self)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.clearFocus()
            return
        super().keyPressEvent(e)
        self.setTransformOriginPoint(self.w / 2, self.h / 2)

    def capture(self):
        return {"w": self.w, "h": self.h, "size": self.params["size"]}

    def resize_from(self, st, w, h):
        k = h / st["h"] if st["h"] > 0 else 1
        self.params["size"] = max(1.0, st["size"] * k)
        self.rebuild()

    def outline_path(self):
        """글자 모양을 패스로 (윤곽선 만들기 · 패스파인더용, 상자 좌표)"""
        path = QPainterPath()
        f = self.qfont()
        fm = QFontMetricsF(f)
        layout = self.document().documentLayout()
        y = 0.0
        for i, line in enumerate(self.params["text"].split("\n")):
            block = self.document().findBlockByNumber(i)
            if block.isValid():
                y = layout.blockBoundingRect(block).top()
            path.addText(QPointF(0, y + fm.ascent()), f, line)
        return path

    def scene_shape(self):
        return self.sceneTransform().map(self.outline_path())

    def to_dict(self):
        d = self.base_dict()
        d.update(self.params)
        return d


# ---------- 이미지 ----------
class ImageItem(QGraphicsItem, VMixin):
    kind = "image"

    def __init__(self, data=b"", w=None, h=None, name=None):
        super().__init__()
        self.data = data
        self.pix = QPixmap()
        self.pix.loadFromData(data)
        self.w = float(w if w else max(1, self.pix.width()))
        self.h = float(h if h else max(1, self.pix.height()))
        self.fh = self.fv = False
        self.init_v(name)
        self.style.update(fill=None, stroke=None)
        self.rebuild()

    @staticmethod
    def from_qimage(img, name="이미지"):
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        img.save(buf, "PNG")
        return ImageItem(bytes(ba), img.width(), img.height(), name)

    def boundingRect(self):
        return QRectF(0, 0, self.w, self.h)

    def rebuild(self):
        self.prepareGeometryChange()
        self.setOpacity(self.style["opacity"])
        self.setTransformOriginPoint(self.w / 2, self.h / 2)

    def apply_style(self):
        self.rebuild()

    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setRenderHint(painter.RenderHint.SmoothPixmapTransform)
        if self.fh or self.fv:
            painter.translate(self.w if self.fh else 0, self.h if self.fv else 0)
            painter.scale(-1 if self.fh else 1, -1 if self.fv else 1)
        painter.drawPixmap(QRectF(0, 0, self.w, self.h), self.pix, QRectF(self.pix.rect()))
        painter.restore()

    def resize_from(self, st, w, h):
        self.w, self.h = max(1.0, w), max(1.0, h)
        self.rebuild()

    def mirror(self, horizontal):
        if horizontal:
            self.fh = not self.fh
        else:
            self.fv = not self.fv
        self.update()

    def scene_shape(self):
        p = QPainterPath()
        p.addRect(self.boundingRect())
        return self.sceneTransform().map(p)

    def to_dict(self):
        d = self.base_dict()
        d.update(w=self.w, h=self.h, fh=self.fh, fv=self.fv, data=base64.b64encode(self.data).decode("ascii"))
        return d


# ---------- 그룹 ----------
class GroupItem(QGraphicsItemGroup, VMixin):
    kind = "group"

    def __init__(self, name=None):
        super().__init__()
        self.init_v(name)

    def boundingRect(self):
        return self.childrenBoundingRect()

    def refresh(self):
        self.prepareGeometryChange()
        self.update()

    def add(self, item):
        """회전이 있는 개체도 모양 그대로 그룹에 넣는다 (Qt 기본 addToGroup 은 회전을 변환행렬로 바꿔 버림)"""
        c = item.center_scene()
        item.setParentItem(self)
        item.set_center_scene(c)
        item.setFlag(QGraphicsItem.ItemIsSelectable, False)
        item.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.refresh()

    def release(self):
        """그룹 풀기: 안의 개체들을 장면으로 꺼낸다"""
        kids = sorted([k for k in self.childItems() if isinstance(k, VMixin)], key=lambda k: k.zValue())
        for k in kids:
            c = k.center_scene()
            k.setParentItem(None)
            k.set_center_scene(c)
            k.set_locked(k.locked)
        return kids

    @property
    def w(self):
        return self.childrenBoundingRect().width()

    @property
    def h(self):
        return self.childrenBoundingRect().height()

    def rebuild(self):
        self.setOpacity(self.style.get("opacity", 1.0))

    def apply_style(self):
        pass

    def set_angle(self, a):
        self.angle = 0.0

    def paint(self, painter, option, widget=None):
        pass

    def to_dict(self):
        d = self.base_dict()
        kids = sorted(self.childItems(), key=lambda it: it.zValue())
        d["children"] = [k.to_dict() for k in kids if isinstance(k, VMixin)]
        return d

    def scene_shape(self):
        p = QPainterPath()
        for k in self.childItems():
            if isinstance(k, VMixin):
                p = p.united(k.scene_shape())
        return p


def leaves(item):
    if isinstance(item, GroupItem):
        out = []
        for k in item.childItems():
            out.extend(leaves(k))
        return out
    return [item] if isinstance(item, VMixin) else []


def item_from_dict(d):
    t = d.get("type")
    if t in ("rect", "ellipse", "polygon", "star", "path", "line"):
        it = ShapeItem(t, d.get("w", 100), d.get("h", 100))
        for k in ("rx", "sides", "points", "inner", "flipv", "fill_rule"):
            if k in d:
                it.params[k] = d[k]
        if "subpaths" in d:
            it.params["subpaths"] = copy.deepcopy(d["subpaths"])
    elif t == "text":
        it = TextItem(d.get("text", ""), d.get("family", "Malgun Gothic"), d.get("size", 36),
                      d.get("bold", False), d.get("italic", False))
    elif t == "image":
        it = ImageItem(base64.b64decode(d.get("data", "")), d.get("w"), d.get("h"))
        it.fh, it.fv = d.get("fh", False), d.get("fv", False)
    elif t == "group":
        it = GroupItem()
        for i, cd in enumerate(d.get("children", [])):
            k = item_from_dict(cd)
            if k is not None:
                k.setZValue(i)
                k.setParentItem(it)
                k.setFlag(QGraphicsItem.ItemIsSelectable, False)
                k.setFlag(QGraphicsItem.ItemIsMovable, False)
    else:
        return None
    it.apply_base(d)
    return it


def to_path_item(item):
    """사각형 · 타원 · 별 · 문자를 '패스'로 바꾼다 (점 편집 · 윤곽선 만들기)"""
    if isinstance(item, ShapeItem) and item.kind in ("path", "line"):
        return item
    if isinstance(item, ShapeItem):
        local = item.local_path()
    elif isinstance(item, TextItem):
        local = item.outline_path()
    else:
        return None
    new = ShapeItem("path", item.w, item.h, item.name)
    new.params["subpaths"] = path_to_subpaths(local)
    new.params["fill_rule"] = 1 if isinstance(item, TextItem) else 0
    new.style = dict(item.style)
    if isinstance(item, TextItem):
        new.style["stroke"] = None
    new.rebuild()
    new.setPos(item.pos())
    new.set_angle(item.angle)
    new.setZValue(item.zValue())
    return new


def path_item_from_scene_path(path, style, name="패스", fill_rule=0):
    """화면(장면) 좌표의 QPainterPath 로 새 패스 개체 만들기"""
    r = path.boundingRect()
    local = path.translated(-r.x(), -r.y())
    it = ShapeItem("path", r.width(), r.height(), name)
    it.params["subpaths"] = path_to_subpaths(local)
    it.params["fill_rule"] = fill_rule
    it.style = dict(style)
    it.rebuild()
    it.setPos(r.x(), r.y())
    return it
