"""SVG 파일 읽기/쓰기 (일러스트레이터 · 벡터크래프트 · 피그마와 주고받기)"""
import base64
import math
import re
import xml.etree.ElementTree as ET

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QPainterPath, QTransform

from vector_items import (DASHES, GroupItem, ImageItem, ShapeItem, TextItem, VMixin,
                          path_item_from_scene_path)

SVG_NS = "http://www.w3.org/2000/svg"
XLINK = "{http://www.w3.org/1999/xlink}href"


class SvgError(Exception):
    pass


# =============== 내보내기 ===============
def _f(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _rgb(c):
    c = QColor(c)
    return c.name(QColor.HexRgb), c.alphaF()


def path_d(path):
    out = []
    i, n = 0, path.elementCount()
    start = None
    while i < n:
        e = path.elementAt(i)
        if e.type == QPainterPath.MoveToElement:
            out.append(f"M{_f(e.x)} {_f(e.y)}")
            start = (e.x, e.y)
            i += 1
        elif e.type == QPainterPath.LineToElement:
            out.append(f"L{_f(e.x)} {_f(e.y)}")
            i += 1
        elif e.type == QPainterPath.CurveToElement:
            c2, end = path.elementAt(i + 1), path.elementAt(i + 2)
            out.append(f"C{_f(e.x)} {_f(e.y)} {_f(c2.x)} {_f(c2.y)} {_f(end.x)} {_f(end.y)}")
            i += 3
        else:
            i += 1
        if start and out and i < n and path.elementAt(i).type == QPainterPath.MoveToElement:
            pass
    return " ".join(out)


class _Writer:
    def __init__(self):
        self.defs = []
        self.gid = 0

    def style_attrs(self, it, w, h):
        s = it.style
        a = []
        if s.get("fill") is None or getattr(it, "kind", "") == "line":
            a.append('fill="none"')
        elif s.get("fill2"):
            self.gid += 1
            gid = f"grad{self.gid}"
            ang = math.radians(s.get("grad_angle", 0))
            x1, y1 = 0.5 - math.cos(ang) / 2, 0.5 - math.sin(ang) / 2
            c1, o1 = _rgb(s["fill"])
            c2, o2 = _rgb(s["fill2"])
            self.defs.append(
                f'<linearGradient id="{gid}" x1="{_f(x1)}" y1="{_f(y1)}" x2="{_f(1 - x1)}" y2="{_f(1 - y1)}">'
                f'<stop offset="0" stop-color="{c1}" stop-opacity="{_f(o1)}"/>'
                f'<stop offset="1" stop-color="{c2}" stop-opacity="{_f(o2)}"/></linearGradient>')
            a.append(f'fill="url(#{gid})"')
        else:
            c, o = _rgb(s["fill"])
            a.append(f'fill="{c}"' + (f' fill-opacity="{_f(o)}"' if o < 1 else ""))
        if s.get("stroke") is not None and s.get("stroke_w", 0) > 0 and not isinstance(it, (TextItem, ImageItem)):
            c, o = _rgb(s["stroke"])
            a.append(f'stroke="{c}" stroke-width="{_f(s["stroke_w"])}"' + (f' stroke-opacity="{_f(o)}"' if o < 1 else ""))
            if s.get("join"):
                a.append('stroke-linejoin="round" stroke-linecap="round"')
            if DASHES[s.get("dash", 0)]:
                a.append(f'stroke-dasharray="{" ".join(_f(v * s["stroke_w"]) for v in DASHES[s["dash"]])}"')
        if s.get("opacity", 1) < 1:
            a.append(f'opacity="{_f(s["opacity"])}"')
        return " ".join(a)

    def item(self, it, indent="  "):
        if not it.isVisible():
            return ""
        x, y = it.pos().x(), it.pos().y()
        tr = f"translate({_f(x)} {_f(y)})"
        if getattr(it, "angle", 0):
            tr += f" rotate({_f(it.angle)} {_f(it.w / 2)} {_f(it.h / 2)})"
        name = it.name.replace('"', "'").replace("&", "&amp;").replace("<", "")
        head = f'{indent}<g id="{name}" transform="{tr}"'
        if isinstance(it, GroupItem):
            kids = sorted([k for k in it.childItems() if isinstance(k, VMixin)], key=lambda k: k.zValue())
            body = "\n".join(self.item(k, indent + "  ") for k in kids)
            op = f' opacity="{_f(it.style.get("opacity", 1))}"' if it.style.get("opacity", 1) < 1 else ""
            return f"{head}{op}>\n{body}\n{indent}</g>"
        st = self.style_attrs(it, it.w, it.h)
        if isinstance(it, ShapeItem):
            if it.kind == "rect":
                rx = min(it.params["rx"], it.w / 2, it.h / 2)
                el = f'<rect width="{_f(it.w)}" height="{_f(it.h)}"' + (f' rx="{_f(rx)}"' if rx > 0 else "")
            elif it.kind == "ellipse":
                el = f'<ellipse cx="{_f(it.w / 2)}" cy="{_f(it.h / 2)}" rx="{_f(it.w / 2)}" ry="{_f(it.h / 2)}"'
            else:
                rule = ' fill-rule="evenodd"' if it.params.get("fill_rule") else ""
                el = f'<path d="{path_d(it.local_path())}"{rule}'
            return f"{head}>{el} {st}/></g>"
        if isinstance(it, TextItem):
            p = it.params
            fam = p["family"].replace('"', "")
            fw = ' font-weight="bold"' if p["bold"] else ""
            fs = ' font-style="italic"' if p["italic"] else ""
            from PySide6.QtGui import QFontMetricsF
            fm = QFontMetricsF(it.qfont())
            lines = []
            for i, ln in enumerate(p["text"].split("\n")):
                ln = ln.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                lines.append(ln if i == 0 else f'<tspan x="0" dy="{_f(fm.lineSpacing())}">{ln}</tspan>')
            return (f'{head}><text x="0" y="{_f(fm.ascent())}" font-family="{fam}" font-size="{_f(p["size"])}"{fw}{fs} {st} '
                    f'xml:space="preserve">{"".join(lines)}</text></g>')
        if isinstance(it, ImageItem):
            data = base64.b64encode(it.data).decode("ascii")
            flip = ""
            if it.fh or it.fv:
                flip = (f' transform="translate({_f(it.w if it.fh else 0)} {_f(it.h if it.fv else 0)}) '
                        f'scale({-1 if it.fh else 1} {-1 if it.fv else 1})"')
            return (f'{head}><image width="{_f(it.w)}" height="{_f(it.h)}" preserveAspectRatio="none"{flip} '
                    f'href="data:image/png;base64,{data}" {st}/></g>')
        return ""


def export_svg(items, width, height, path, background=None):
    w = _Writer()
    body = "\n".join(filter(None, (w.item(it) for it in items)))
    bg = ""
    if background is not None:
        c, o = _rgb(background)
        bg = f'  <rect width="{_f(width)}" height="{_f(height)}" fill="{c}"/>\n'
    defs = f"  <defs>{''.join(w.defs)}</defs>\n" if w.defs else ""
    svg = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<!-- 모찌벡터 (MozziLab) 에서 만든 파일 -->\n'
           f'<svg xmlns="{SVG_NS}" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" '
           f'width="{_f(width)}" height="{_f(height)}" viewBox="0 0 {_f(width)} {_f(height)}">\n'
           f"{defs}{bg}{body}\n</svg>\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)


# =============== 가져오기 ===============
_NUM = re.compile(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")


def _nums(s):
    return [float(v) for v in _NUM.findall(s or "")]


def _len(v, default=0.0, ref=100.0):
    if v is None:
        return default
    v = str(v).strip()
    m = _NUM.match(v)
    if not m:
        return default
    n = float(m.group(0))
    unit = v[m.end():].strip()
    return {"px": n, "pt": n * 4 / 3, "mm": n * 96 / 25.4, "cm": n * 96 / 2.54, "in": n * 96,
            "%": n / 100 * ref, "em": n * 16}.get(unit, n)


def parse_transform(s):
    t = QTransform()
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", s or ""):
        a = _nums(args)
        m = QTransform()
        if name == "matrix" and len(a) == 6:
            m = QTransform(a[0], a[1], a[2], a[3], a[4], a[5])
        elif name == "translate" and a:
            m = QTransform.fromTranslate(a[0], a[1] if len(a) > 1 else 0)
        elif name == "scale" and a:
            m = QTransform.fromScale(a[0], a[1] if len(a) > 1 else a[0])
        elif name == "rotate" and a:
            if len(a) >= 3:
                m = QTransform().translate(a[1], a[2]).rotate(a[0]).translate(-a[1], -a[2])
            else:
                m = QTransform().rotate(a[0])
        elif name == "skewX" and a:
            m = QTransform(1, 0, math.tan(math.radians(a[0])), 1, 0, 0)
        elif name == "skewY" and a:
            m = QTransform(1, math.tan(math.radians(a[0])), 0, 1, 0, 0)
        t = m * t      # 오른쪽부터 적용
    return t


def _arc(path, x0, y0, rx, ry, phi, large, sweep, x, y):
    """SVG 원호(A) → 베지어 곡선 몇 개"""
    if rx == 0 or ry == 0:
        path.lineTo(x, y)
        return
    rx, ry = abs(rx), abs(ry)
    cp, sp = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (x0 - x) / 2, (y0 - y) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = x1p ** 2 / rx ** 2 + y1p ** 2 / ry ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx ** 2 * ry ** 2 - rx ** 2 * y1p ** 2 - ry ** 2 * x1p ** 2
    den = rx ** 2 * y1p ** 2 + ry ** 2 * x1p ** 2
    co = math.sqrt(max(0, num / den)) if den else 0
    if large == sweep:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x0 + x) / 2
    cy = sp * cxp + cp * cyp + (y0 + y) / 2

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a
    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    segs = max(1, int(math.ceil(abs(dt) / (math.pi / 2))))
    d = dt / segs
    k = 4 / 3 * math.tan(d / 4)
    t = t1
    for _ in range(segs):
        c1, s1 = math.cos(t), math.sin(t)
        c2, s2 = math.cos(t + d), math.sin(t + d)
        p1 = (c1 - k * s1, s1 + k * c1)
        p2 = (c2 + k * s2, s2 - k * c2)
        p3 = (c2, s2)

        def mp(q):
            return QPointF(cx + rx * q[0] * cp - ry * q[1] * sp, cy + rx * q[0] * sp + ry * q[1] * cp)
        path.cubicTo(mp(p1), mp(p2), mp(p3))
        t += d


def parse_path_d(d):
    path = QPainterPath()
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|" + _NUM.pattern, d or "")
    i = 0
    cmd = None
    x = y = sx = sy = 0.0
    last_c = last_q = None
    while i < len(tokens):
        tk = tokens[i]
        if tk.isalpha():
            cmd = tk
            i += 1
            if cmd in "Zz":
                path.closeSubpath()
                x, y = sx, sy
                last_c = last_q = None
                continue
        if cmd is None:
            break

        def take(n):
            nonlocal i
            vals = [float(v) for v in tokens[i:i + n]]
            if len(vals) < n or any(isinstance(v, str) for v in vals):
                raise SvgError("path 해석 실패")
            i += n
            return vals
        try:
            rel = cmd.islower()
            c = cmd.upper()
            if c == "M":
                a, b = take(2)
                x, y = (x + a, y + b) if rel else (a, b)
                path.moveTo(x, y)
                sx, sy = x, y
                cmd = "l" if rel else "L"
                last_c = last_q = None
            elif c == "L":
                a, b = take(2)
                x, y = (x + a, y + b) if rel else (a, b)
                path.lineTo(x, y)
                last_c = last_q = None
            elif c == "H":
                a, = take(1)
                x = x + a if rel else a
                path.lineTo(x, y)
                last_c = last_q = None
            elif c == "V":
                b, = take(1)
                y = y + b if rel else b
                path.lineTo(x, y)
                last_c = last_q = None
            elif c == "C":
                v = take(6)
                if rel:
                    v = [v[0] + x, v[1] + y, v[2] + x, v[3] + y, v[4] + x, v[5] + y]
                path.cubicTo(v[0], v[1], v[2], v[3], v[4], v[5])
                last_c = (v[2], v[3])
                x, y = v[4], v[5]
                last_q = None
            elif c == "S":
                v = take(4)
                if rel:
                    v = [v[0] + x, v[1] + y, v[2] + x, v[3] + y]
                c1 = (2 * x - last_c[0], 2 * y - last_c[1]) if last_c else (x, y)
                path.cubicTo(c1[0], c1[1], v[0], v[1], v[2], v[3])
                last_c = (v[0], v[1])
                x, y = v[2], v[3]
                last_q = None
            elif c == "Q":
                v = take(4)
                if rel:
                    v = [v[0] + x, v[1] + y, v[2] + x, v[3] + y]
                path.quadTo(v[0], v[1], v[2], v[3])
                last_q = (v[0], v[1])
                x, y = v[2], v[3]
                last_c = None
            elif c == "T":
                v = take(2)
                if rel:
                    v = [v[0] + x, v[1] + y]
                q = (2 * x - last_q[0], 2 * y - last_q[1]) if last_q else (x, y)
                path.quadTo(q[0], q[1], v[0], v[1])
                last_q = q
                x, y = v[0], v[1]
                last_c = None
            elif c == "A":
                v = take(7)
                ex, ey = (x + v[5], y + v[6]) if rel else (v[5], v[6])
                _arc(path, x, y, v[0], v[1], v[2], int(v[3]), int(v[4]), ex, ey)
                x, y = ex, ey
                last_c = last_q = None
            else:
                i += 1
        except (ValueError, IndexError):
            break
    return path


def _parse_style(el, inherited):
    st = dict(inherited)
    for k in ("fill", "stroke", "stroke-width", "fill-opacity", "stroke-opacity", "opacity", "fill-rule",
              "stroke-dasharray", "stroke-linejoin", "font-size", "font-family", "font-weight", "font-style",
              "display", "visibility"):
        if el.get(k) is not None:
            st[k] = el.get(k).strip()
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            st[k.strip()] = v.strip()
    if el.get("class") and inherited.get("_classes"):
        for cls in el.get("class").split():
            st.update(inherited["_classes"].get(cls, {}))
    if "opacity" in inherited and el.get("opacity") is None and "opacity" not in (el.get("style") or ""):
        st["opacity"] = "1"   # 그룹 불투명도는 그룹에서 처리
    return st


def _color(v, grads):
    if v is None:
        return QColor("black")
    v = v.strip()
    if v in ("none", "transparent"):
        return None
    m = re.match(r"url\(#([^)]+)\)", v)
    if m:
        g = grads.get(m.group(1))
        return QColor(g[0]) if g else QColor("black")
    m = re.match(r"rgba?\(([^)]*)\)", v)
    if m:
        a = [float(x.strip().rstrip("%")) * (2.55 if "%" in x else 1) for x in m.group(1).split(",")]
        c = QColor(int(a[0]), int(a[1]), int(a[2]))
        if len(a) > 3:
            c.setAlphaF(min(1, a[3]))
        return c
    c = QColor(v)
    return c if c.isValid() else QColor("black")


class _Reader:
    def __init__(self, root):
        self.grads = {}
        self.classes = {}
        for el in root.iter():
            tag = el.tag.split("}")[-1]
            if tag in ("linearGradient", "radialGradient"):
                stops = [s for s in el if s.tag.split("}")[-1] == "stop"]
                cols = []
                for s in stops:
                    sst = _parse_style(s, {})
                    c = _color(sst.get("stop-color", "black"), {})
                    if c is not None:
                        c.setAlphaF(c.alphaF() * float(sst.get("stop-opacity", 1)))
                        cols.append(c.name(QColor.HexArgb))
                href = el.get(XLINK) or el.get("href")
                if not cols and href and href[1:] in self.grads:
                    cols = self.grads[href[1:]]
                if cols:
                    self.grads[el.get("id", "")] = cols
            elif tag == "style" and el.text:
                for sel, body in re.findall(r"\.([\w-]+)\s*\{([^}]*)\}", el.text):
                    d = {}
                    for part in body.split(";"):
                        if ":" in part:
                            k, v = part.split(":", 1)
                            d[k.strip()] = v.strip()
                    self.classes[sel] = d
        self.items = []

    def style_of(self, st, scale):
        fill = _color(st.get("fill", "black"), self.grads)
        stroke = _color(st.get("stroke", "none"), self.grads)
        fo, so = float(st.get("fill-opacity", 1)), float(st.get("stroke-opacity", 1))
        if fill is not None:
            fill.setAlphaF(fill.alphaF() * fo)
        if stroke is not None:
            stroke.setAlphaF(stroke.alphaF() * so)
        grad = re.match(r"url\(#([^)]+)\)", st.get("fill", ""))
        fill2 = None
        if grad and len(self.grads.get(grad.group(1), [])) > 1:
            fill2 = self.grads[grad.group(1)][-1]
        sw = _len(st.get("stroke-width"), 1.0) * scale
        dash = 1 if st.get("stroke-dasharray", "none") not in ("none", "") else 0
        return {"fill": fill.name(QColor.HexArgb) if fill is not None else None, "fill2": fill2, "grad_angle": 0,
                "stroke": stroke.name(QColor.HexArgb) if stroke is not None else None, "stroke_w": round(sw, 3),
                "dash": dash, "join": 1 if st.get("stroke-linejoin") == "round" else 0,
                "opacity": float(st.get("opacity", 1))}

    def walk(self, el, t, st, out):
        tag = el.tag.split("}")[-1]
        if tag in ("defs", "style", "title", "desc", "metadata", "clipPath", "mask", "symbol", "linearGradient",
                   "radialGradient", "pattern", "filter", "marker"):
            return
        st = _parse_style(el, {**st, "_classes": self.classes})
        if st.get("display") == "none" or st.get("visibility") == "hidden":
            return
        t = parse_transform(el.get("transform")) * t
        scale = math.sqrt(abs(t.determinant())) or 1
        if tag in ("g", "svg", "a", "switch"):
            kids = []
            for ch in el:
                self.walk(ch, t, {k: v for k, v in st.items() if k != "opacity"}, kids)
            if not kids:
                return
            if tag == "g" and len(kids) > 1:
                g = GroupItem(el.get("id") or "그룹")
                for k in kids:
                    g.add(k)
                g.style["opacity"] = float(st.get("opacity", 1))
                g.rebuild()
                out.append(g)
            else:
                out.extend(kids)
            return
        path = QPainterPath()
        if tag == "rect":
            x, y = _len(el.get("x")), _len(el.get("y"))
            w, h = _len(el.get("width")), _len(el.get("height"))
            rx = _len(el.get("rx"), _len(el.get("ry")))
            if w <= 0 or h <= 0:
                return
            if rx > 0:
                path.addRoundedRect(QRectF(x, y, w, h), rx, _len(el.get("ry"), rx))
            else:
                path.addRect(QRectF(x, y, w, h))
        elif tag == "circle":
            r = _len(el.get("r"))
            path.addEllipse(QPointF(_len(el.get("cx")), _len(el.get("cy"))), r, r)
        elif tag == "ellipse":
            path.addEllipse(QPointF(_len(el.get("cx")), _len(el.get("cy"))), _len(el.get("rx")), _len(el.get("ry")))
        elif tag == "line":
            path.moveTo(_len(el.get("x1")), _len(el.get("y1")))
            path.lineTo(_len(el.get("x2")), _len(el.get("y2")))
            st.setdefault("fill", "none")
            st["fill"] = "none"
        elif tag in ("polyline", "polygon"):
            v = _nums(el.get("points"))
            if len(v) < 4:
                return
            path.moveTo(v[0], v[1])
            for j in range(2, len(v) - 1, 2):
                path.lineTo(v[j], v[j + 1])
            if tag == "polygon":
                path.closeSubpath()
        elif tag == "path":
            path = parse_path_d(el.get("d"))
        elif tag == "text":
            self.text(el, t, st, out, scale)
            return
        elif tag == "image":
            href = el.get(XLINK) or el.get("href") or ""
            m = re.match(r"data:image/[\w+]+;base64,(.*)", href, re.S)
            if not m:
                return
            it = ImageItem(base64.b64decode(m.group(1)), _len(el.get("width"), 0) or None, _len(el.get("height"), 0) or None)
            x, y = _len(el.get("x")), _len(el.get("y"))
            self._place_box(it, t, x, y)
            out.append(it)
            return
        else:
            return
        if path.isEmpty():
            return
        scene = t.map(path)
        style = self.style_of(st, scale)
        it = path_item_from_scene_path(scene, style, el.get("id") or {"rect": "사각형", "circle": "원", "ellipse": "타원",
                                                                       "line": "선", "path": "패스"}.get(tag, tag),
                                       1 if st.get("fill-rule") == "evenodd" else 0)
        out.append(it)

    @staticmethod
    def _place_box(it, t, x, y):
        """크기/회전이 있는 변환을 '상자 + 회전'으로 나눠서 적용"""
        sx = math.hypot(t.m11(), t.m12())
        sy = math.hypot(t.m21(), t.m22())
        ang = math.degrees(math.atan2(t.m12(), t.m11()))
        it.resize_from(it.capture(), it.w * sx, it.h * sy)
        c = t.map(QPointF(x + it.w / sx / 2, y + it.h / sy / 2))
        it.set_angle(ang)
        it.set_center_scene(c)

    def text(self, el, t, st, out, scale):
        lines, first = [], None
        if el.text and el.text.strip():
            lines.append(el.text.strip())
        for ch in el:
            if ch.tag.split("}")[-1] == "tspan" and (ch.text or "").strip():
                lines.append(ch.text.strip())
                if first is None:
                    first = ch
            if ch.tail and ch.tail.strip():
                lines.append(ch.tail.strip())
        if not lines:
            return
        tst = _parse_style(first, st) if first is not None else st
        size = _len(tst.get("font-size"), 16)
        fam = (tst.get("font-family") or "Malgun Gothic").split(",")[0].strip("'\" ")
        it = TextItem("\n".join(lines), fam, size, tst.get("font-weight") in ("bold", "700", "800", "900"),
                      tst.get("font-style") == "italic")
        sty = self.style_of(tst, scale)
        it.style.update(fill=sty["fill"] or "#ff000000", opacity=sty["opacity"])
        it.rebuild()
        x = _len((first if first is not None and first.get("x") else el).get("x"))
        y = _len((first if first is not None and first.get("y") else el).get("y"))
        from PySide6.QtGui import QFontMetricsF
        asc = QFontMetricsF(it.qfont()).ascent()
        sx = math.hypot(t.m11(), t.m12())
        ang = math.degrees(math.atan2(t.m12(), t.m11()))
        it.params["size"] = size * sx
        it.rebuild()
        it.set_angle(ang)
        top_left = t.map(QPointF(x, y - asc))
        it.setPos(top_left)
        if ang:
            c = QTransform().rotate(ang).map(QPointF(it.w / 2, it.h / 2)) + top_left
            it.set_center_scene(c)
        out.append(it)


def import_svg(path):
    """SVG → (개체 목록, 가로, 세로)"""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as e:
        raise SvgError(f"SVG 파일을 읽을 수 없어요: {e}")
    vb = _nums(root.get("viewBox"))
    w = _len(root.get("width"), vb[2] if len(vb) == 4 else 800)
    h = _len(root.get("height"), vb[3] if len(vb) == 4 else 600)
    t = QTransform()
    if len(vb) == 4 and vb[2] > 0 and vb[3] > 0:
        t = QTransform.fromTranslate(-vb[0], -vb[1]) * QTransform.fromScale(w / vb[2], h / vb[3])
    r = _Reader(root)
    out = []
    for ch in root:
        r.walk(ch, t, {}, out)
    return out, w, h
