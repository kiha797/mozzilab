"""모찌포토 핵심 기능 (화면과 상관없는 부분)
- 문서/레이어 구조, 혼합 모드 합성
- 필터·색 보정 (Pillow + numpy)
- 파일: 일반 이미지 열기/내보내기, PSD(포토샵) 레이어 읽기/쓰기, 모찌포토 프로젝트(.mphoto)"""
import io
import json
import os
import struct
import zipfile

import numpy as np
from PIL import Image, ImageFilter, ImageOps
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QTransform

FMT = QImage.Format_ARGB32_Premultiplied

# 혼합 모드: (화면 이름, Qt 합성 방식, PSD 코드)
BLEND_MODES = [
    ("normal", "표준", QPainter.CompositionMode_SourceOver, b"norm"),
    ("multiply", "곱하기", QPainter.CompositionMode_Multiply, b"mul "),
    ("screen", "스크린", QPainter.CompositionMode_Screen, b"scrn"),
    ("overlay", "오버레이", QPainter.CompositionMode_Overlay, b"over"),
    ("darken", "어둡게", QPainter.CompositionMode_Darken, b"dark"),
    ("lighten", "밝게", QPainter.CompositionMode_Lighten, b"lite"),
    ("dodge", "색상 닷지", QPainter.CompositionMode_ColorDodge, b"div "),
    ("burn", "색상 번", QPainter.CompositionMode_ColorBurn, b"idiv"),
    ("hardlight", "하드 라이트", QPainter.CompositionMode_HardLight, b"hLit"),
    ("softlight", "소프트 라이트", QPainter.CompositionMode_SoftLight, b"sLit"),
    ("difference", "차이", QPainter.CompositionMode_Difference, b"diff"),
    ("exclusion", "제외", QPainter.CompositionMode_Exclusion, b"smud"),
    ("add", "더하기", QPainter.CompositionMode_Plus, b"lddg"),
]
BLEND_QT = {k: q for k, _, q, _ in BLEND_MODES}
BLEND_PSD = {k: c for k, _, _, c in BLEND_MODES}
PSD_BLEND = {c: k for k, _, _, c in BLEND_MODES}

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff", ".psd", ".mphoto", ".ico")
OPEN_FILTER = ("모든 이미지 (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff *.psd *.mphoto *.ico);;"
               "모찌포토 프로젝트 (*.mphoto);;포토샵 (*.psd);;PNG (*.png);;JPG (*.jpg *.jpeg);;모든 파일 (*.*)")


class PhotoError(Exception):
    pass


# ---------- QImage <-> Pillow ----------
def new_image(w, h, color=None):
    img = QImage(w, h, FMT)
    img.fill(QColor(color) if color is not None else Qt.transparent)
    return img


def qimage_to_pil(img):
    img = img.convertToFormat(QImage.Format_RGBA8888)
    w, h = img.width(), img.height()
    data = bytes(img.constBits())[: img.sizeInBytes()]
    return Image.frombuffer("RGBA", (w, h), data, "raw", "RGBA", img.bytesPerLine(), 1).copy()


def pil_to_qimage(im):
    im = im.convert("RGBA")
    data = im.tobytes()
    q = QImage(data, im.width, im.height, im.width * 4, QImage.Format_RGBA8888)
    return q.convertToFormat(FMT)


def qimage_to_array(img):
    """(높이, 너비, 4) RGBA uint8 배열"""
    return np.asarray(qimage_to_pil(img))


def array_to_qimage(arr):
    return pil_to_qimage(Image.fromarray(np.ascontiguousarray(arr, dtype=np.uint8), "RGBA"))


# ---------- 문서 / 레이어 ----------
class Layer:
    def __init__(self, name, image, visible=True, opacity=1.0, blend="normal"):
        self.name = name
        self.image = image
        self.visible = visible
        self.opacity = opacity
        self.blend = blend

    def copy(self, name=None):
        return Layer(name or self.name, self.image.copy(), self.visible, self.opacity, self.blend)


class Document:
    def __init__(self, w, h, background=QColor("white")):
        self.width, self.height = w, h
        self.layers = [Layer("배경", new_image(w, h, background))]
        self.active = 0
        self.selection = QPainterPath()      # 비어 있으면 '선택 없음'
        self.path = ""                        # 저장한 파일 경로
        self._cache = None

    # 크기
    def rect(self):
        return QRect(0, 0, self.width, self.height)

    @property
    def layer(self):
        return self.layers[self.active]

    def has_selection(self):
        return not self.selection.isEmpty()

    # 합성 (화면에 보이는 그림)
    def composite(self, region=None, hide_index=None):
        """모든 레이어를 혼합 모드대로 합친 그림. region 을 주면 그 부분만 다시 그린다."""
        if self._cache is None or self._cache.size() != self.rect().size():
            self._cache = new_image(self.width, self.height)
            region = None
        r = self.rect() if region is None else region.intersected(self.rect())
        if r.isEmpty():
            return self._cache
        p = QPainter(self._cache)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(r, Qt.transparent)
        for i, ly in enumerate(self.layers):
            if not ly.visible or i == hide_index:
                continue
            p.setOpacity(ly.opacity)
            p.setCompositionMode(BLEND_QT.get(ly.blend, QPainter.CompositionMode_SourceOver))
            p.drawImage(r, ly.image, r)
        p.end()
        return self._cache

    def invalidate(self):
        self._cache = None

    def flattened(self, background=None):
        out = new_image(self.width, self.height, background)
        p = QPainter(out)
        p.drawImage(0, 0, self.composite())
        p.end()
        return out

    # 실행취소용 상태 저장/복원 (QImage 는 바뀔 때만 실제로 복사되므로 가볍다)
    def snapshot(self):
        return {"w": self.width, "h": self.height, "active": self.active, "sel": QPainterPath(self.selection),
                "layers": [(ly.name, QImage(ly.image), ly.visible, ly.opacity, ly.blend) for ly in self.layers]}

    def restore(self, s):
        self.width, self.height, self.active = s["w"], s["h"], s["active"]
        self.selection = QPainterPath(s["sel"])
        self.layers = [Layer(n, QImage(img), v, o, b) for n, img, v, o, b in s["layers"]]
        self.invalidate()

    # 레이어 관리
    def add_layer(self, name=None, image=None, index=None):
        name = name or f"레이어 {len(self.layers)}"
        ly = Layer(name, image if image is not None else new_image(self.width, self.height))
        index = self.active + 1 if index is None else index
        self.layers.insert(index, ly)
        self.active = index
        self.invalidate()
        return ly

    def duplicate_layer(self):
        ly = self.layer.copy(self.layer.name + " 복사")
        self.layers.insert(self.active + 1, ly)
        self.active += 1
        self.invalidate()

    def delete_layer(self):
        if len(self.layers) <= 1:
            raise PhotoError("레이어가 하나뿐이라 지울 수 없어요.")
        del self.layers[self.active]
        self.active = max(0, self.active - 1)
        self.invalidate()

    def move_layer(self, step):
        j = self.active + step
        if 0 <= j < len(self.layers):
            self.layers[self.active], self.layers[j] = self.layers[j], self.layers[self.active]
            self.active = j
            self.invalidate()

    def merge_down(self):
        if self.active == 0:
            raise PhotoError("맨 아래 레이어는 아래로 병합할 수 없어요.")
        top, below = self.layers[self.active], self.layers[self.active - 1]
        img = QImage(below.image)
        p = QPainter(img)
        p.setOpacity(top.opacity)
        p.setCompositionMode(BLEND_QT.get(top.blend))
        if top.visible:
            p.drawImage(0, 0, top.image)
        p.end()
        below.image = img
        del self.layers[self.active]
        self.active -= 1
        self.invalidate()

    def merge_visible(self):
        vis = [ly for ly in self.layers if ly.visible]
        if len(vis) < 2:
            return
        img = self.composite().copy()
        idx = self.layers.index(vis[0])
        self.layers = [ly for ly in self.layers if not ly.visible]
        self.layers.insert(min(idx, len(self.layers)), Layer("병합됨", img))
        self.active = min(idx, len(self.layers) - 1)
        self.invalidate()

    def flatten(self):
        self.layers = [Layer("배경", self.flattened(QColor("white")))]
        self.active = 0
        self.invalidate()

    # 이미지 전체 변형
    def transform_all(self, fn, new_size=None):
        for ly in self.layers:
            ly.image = fn(ly.image)
        if new_size:
            self.width, self.height = new_size
        else:
            self.width, self.height = self.layers[0].image.width(), self.layers[0].image.height()
        self.selection = QPainterPath()
        self.invalidate()

    def resize_image(self, w, h, smooth=True):
        mode = Qt.SmoothTransformation if smooth else Qt.FastTransformation
        self.transform_all(lambda im: im.scaled(w, h, Qt.IgnoreAspectRatio, mode).convertToFormat(FMT), (w, h))

    def resize_canvas(self, w, h, anchor=(0.5, 0.5), fill=None):
        dx = int(round((w - self.width) * anchor[0]))
        dy = int(round((h - self.height) * anchor[1]))

        def fn(im):
            out = new_image(w, h)
            p = QPainter(out)
            p.drawImage(dx, dy, im)
            p.end()
            return out
        self.transform_all(fn, (w, h))
        if fill is not None:     # 배경 레이어의 새로 생긴 부분을 채운다
            bg = self.layers[0].image
            p = QPainter(bg)
            p.setCompositionMode(QPainter.CompositionMode_DestinationOver)
            p.fillRect(bg.rect(), fill)
            p.end()

    def crop(self, r):
        r = r.intersected(self.rect())
        if r.width() < 1 or r.height() < 1:
            raise PhotoError("자를 영역이 너무 작아요.")
        self.transform_all(lambda im: im.copy(r), (r.width(), r.height()))

    def rotate(self, deg):
        t = QTransform().rotate(deg)
        self.transform_all(lambda im: im.transformed(t, Qt.SmoothTransformation).convertToFormat(FMT))

    def flip(self, horizontal=True):
        self.transform_all(lambda im: im.mirrored(horizontal, not horizontal))


# ---------- 선택 영역 도우미 ----------
def path_from_mask(mask):
    """True/False 배열 → 선택 경로"""
    h, w = mask.shape
    m = QImage(np.ascontiguousarray(mask.astype(np.uint8) * 255).data, w, h, w, QImage.Format_Grayscale8).copy()
    from PySide6.QtGui import QBitmap, QRegion
    bmp = QBitmap.fromImage(m.createMaskFromColor(QColor(255, 255, 255).rgb(), Qt.MaskOutColor))
    path = QPainterPath()
    path.addRegion(QRegion(bmp))
    return path.simplified()


def color_mask(img, x, y, tolerance=32, contiguous=True):
    """(x, y) 와 비슷한 색의 영역 (마술봉 · 페인트통)"""
    arr = qimage_to_array(img).astype(np.int16)
    h, w = arr.shape[:2]
    if not (0 <= x < w and 0 <= y < h):
        return np.zeros((h, w), bool)
    seed = arr[y, x]
    diff = np.abs(arr - seed).max(axis=2)
    sim = diff <= tolerance
    if not contiguous:
        return sim
    return connected_region(sim, x, y)


def connected_region(sim, x, y):
    """sim(참/거짓 배열)에서 (x, y)와 이어진 부분만. 줄마다 '연속 구간'으로 묶어서 빠르게 찾는다."""
    import bisect
    h, w = sim.shape
    pad = np.zeros((h, w + 2), np.int8)
    pad[:, 1:-1] = sim
    d = np.diff(pad, axis=1)
    sy, sx = np.nonzero(d == 1)
    ey, ex = np.nonzero(d == -1)
    rows = [[] for _ in range(h)]           # 줄마다 [(시작, 끝), ...]
    for r, a, b in zip(sy.tolist(), sx.tolist(), ex.tolist()):
        rows[r].append((a, b))
    starts = [[a for a, _ in rw] for rw in rows]
    i = bisect.bisect_right(starts[y], x) - 1
    if i < 0 or rows[y][i][1] <= x:
        return np.zeros((h, w), bool)
    out = np.zeros((h, w), bool)
    seen = {(y, i)}
    stack = [(y, i)]
    while stack:
        r, k = stack.pop()
        a, b = rows[r][k]
        out[r, a:b] = True
        for nr in (r - 1, r + 1):
            if 0 <= nr < h and rows[nr]:
                j = max(0, bisect.bisect_right(starts[nr], a) - 1)
                while j < len(rows[nr]) and rows[nr][j][0] < b:
                    if rows[nr][j][1] > a and (nr, j) not in seen:
                        seen.add((nr, j))
                        stack.append((nr, j))
                    j += 1
    return out


# ---------- 필터 · 보정 (Pillow RGBA → RGBA) ----------
def _rgb_alpha(im):
    im = im.convert("RGBA")
    return im.convert("RGB"), im.getchannel("A")


def _join(rgb, a):
    out = rgb.convert("RGB")
    out.putalpha(a)
    return out


def brightness_contrast(im, brightness=0, contrast=0):
    arr = np.asarray(im.convert("RGBA")).astype(np.float32)
    c = contrast * 2.55
    f = (259 * (c + 255)) / (255 * (259 - c))
    rgb = (arr[..., :3] - 128) * f + 128 + brightness * 1.5
    arr[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def hue_saturation(im, hue=0, saturation=0, lightness=0):
    rgb, a = _rgb_alpha(im)
    hsv = np.asarray(rgb.convert("HSV")).astype(np.int32)
    hsv[..., 0] = (hsv[..., 0] + int(round(hue / 360 * 256))) % 256
    hsv[..., 1] = np.clip(hsv[..., 1] * (1 + saturation / 100), 0, 255)
    out = np.asarray(Image.fromarray(hsv.astype(np.uint8), "HSV").convert("RGB")).astype(np.float32)
    if lightness > 0:
        out = out + (255 - out) * (lightness / 100)
    elif lightness < 0:
        out = out * (1 + lightness / 100)
    return _join(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB"), a)


def color_balance(im, red=0, green=0, blue=0):
    arr = np.asarray(im.convert("RGBA")).astype(np.float32)
    for i, v in enumerate((red, green, blue)):
        arr[..., i] = np.clip(arr[..., i] + v * 1.2, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def levels(im, black=0, white=255, gamma=100):
    arr = np.asarray(im.convert("RGBA")).astype(np.float32)
    lo, hi = min(black, white - 1), max(white, black + 1)
    x = np.clip((arr[..., :3] - lo) / (hi - lo), 0, 1)
    arr[..., :3] = np.power(x, 100.0 / max(gamma, 1)) * 255
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def grayscale(im):
    rgb, a = _rgb_alpha(im)
    return _join(rgb.convert("L"), a)


def invert(im):
    rgb, a = _rgb_alpha(im)
    return _join(ImageOps.invert(rgb), a)


def sepia(im):
    rgb, a = _rgb_alpha(im)
    g = np.asarray(rgb.convert("L")).astype(np.float32)
    out = np.stack([g * 1.07 + 20, g * 0.95 + 8, g * 0.75], axis=2)
    return _join(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB"), a)


def posterize(im, levels_=4):
    rgb, a = _rgb_alpha(im)
    arr = np.asarray(rgb).astype(np.float32)
    n = max(2, int(levels_))
    arr = np.round(arr / 255 * (n - 1)) / (n - 1) * 255
    return _join(Image.fromarray(arr.astype(np.uint8), "RGB"), a)


def threshold(im, level=128):
    rgb, a = _rgb_alpha(im)
    return _join(rgb.convert("L").point(lambda v: 255 if v >= level else 0), a)


def auto_contrast(im):
    rgb, a = _rgb_alpha(im)
    return _join(ImageOps.autocontrast(rgb, cutoff=0.5), a)


def auto_color(im):
    rgb, a = _rgb_alpha(im)
    return _join(ImageOps.equalize(rgb), a)


def gaussian_blur(im, radius=4):
    return im.convert("RGBA").filter(ImageFilter.GaussianBlur(radius))


def box_blur(im, radius=4):
    return im.convert("RGBA").filter(ImageFilter.BoxBlur(radius))


def sharpen(im, amount=100, radius=2):
    rgb, a = _rgb_alpha(im)
    return _join(rgb.filter(ImageFilter.UnsharpMask(radius=radius, percent=int(amount), threshold=2)), a)


def add_noise(im, amount=20):
    arr = np.asarray(im.convert("RGBA")).astype(np.int16)
    noise = np.random.default_rng(1).normal(0, amount, arr.shape[:2] + (1,))
    arr[..., :3] = np.clip(arr[..., :3] + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def pixelate(im, size=12):
    im = im.convert("RGBA")
    s = max(2, int(size))
    small = im.resize((max(1, im.width // s), max(1, im.height // s)), Image.BILINEAR)
    return small.resize(im.size, Image.NEAREST)


def emboss(im):
    rgb, a = _rgb_alpha(im)
    return _join(rgb.filter(ImageFilter.EMBOSS), a)


def find_edges(im):
    rgb, a = _rgb_alpha(im)
    return _join(ImageOps.invert(rgb.filter(ImageFilter.FIND_EDGES)), a)


def vignette(im, strength=50):
    arr = np.asarray(im.convert("RGBA")).astype(np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / 1.4142
    k = 1 - np.clip(d, 0, 1) ** 2 * (strength / 100)
    arr[..., :3] *= k[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")


def oil_paint(im, size=5):
    rgb, a = _rgb_alpha(im)
    s = max(3, int(size) | 1)
    return _join(rgb.filter(ImageFilter.ModeFilter(s)), a)


# ---------- 파일 열기 ----------
def load_document(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".mphoto":
        doc = load_project(path)
    elif ext == ".psd":
        doc = load_psd(path)
    else:
        try:
            im = Image.open(path)
            im = ImageOps.exif_transpose(im)
            im.load()
        except Exception as e:  # noqa: BLE001
            raise PhotoError(f"이미지를 열 수 없어요: {e}")
        doc = Document(im.width, im.height, None)
        doc.layers = [Layer("배경", pil_to_qimage(im))]
        doc.invalidate()
    doc.path = path if ext in (".mphoto",) else ""
    return doc


def open_as_image(path):
    """'레이어로 가져오기' 용: 그림 한 장(QImage)"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".psd", ".mphoto"):
        return load_document(path).flattened()
    im = ImageOps.exif_transpose(Image.open(path))
    return pil_to_qimage(im)


# ---------- 모찌포토 프로젝트 (.mphoto = zip 안에 레이어 PNG + 정보 JSON) ----------
def save_project(doc, path):
    tmp = path + ".part"
    info = {"app": "MochiPhoto", "version": 1, "width": doc.width, "height": doc.height,
            "active": doc.active, "layers": []}
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for i, ly in enumerate(doc.layers):
            name = f"layers/{i:03d}.png"
            buf = io.BytesIO()
            qimage_to_pil(ly.image).save(buf, "PNG")
            z.writestr(name, buf.getvalue())
            info["layers"].append({"name": ly.name, "file": name, "visible": ly.visible,
                                   "opacity": ly.opacity, "blend": ly.blend})
        prev = io.BytesIO()
        th = qimage_to_pil(doc.flattened())
        th.thumbnail((512, 512))
        th.save(prev, "PNG")
        z.writestr("preview.png", prev.getvalue())
        z.writestr("document.json", json.dumps(info, ensure_ascii=False, indent=1))
    os.replace(tmp, path)
    doc.path = path


def load_project(path):
    try:
        with zipfile.ZipFile(path) as z:
            info = json.loads(z.read("document.json").decode("utf-8"))
            doc = Document(info["width"], info["height"], None)
            doc.layers = []
            for li in info["layers"]:
                im = Image.open(io.BytesIO(z.read(li["file"])))
                doc.layers.append(Layer(li["name"], pil_to_qimage(im), li.get("visible", True),
                                        float(li.get("opacity", 1)), li.get("blend", "normal")))
            doc.active = min(int(info.get("active", 0)), len(doc.layers) - 1)
    except (KeyError, ValueError, zipfile.BadZipFile) as e:
        raise PhotoError(f"모찌포토 파일이 손상되었어요: {e}")
    if not doc.layers:
        raise PhotoError("레이어가 없는 파일이에요.")
    doc.invalidate()
    return doc


# ---------- 내보내기 ----------
def export_image(doc, path, quality=92):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".psd":
        return save_psd(doc, path)
    if ext == ".mphoto":
        return save_project(doc, path)
    im = qimage_to_pil(doc.flattened())
    if ext in (".jpg", ".jpeg", ".bmp"):
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.getchannel("A"))
        im = bg
    kw = {}
    if ext in (".jpg", ".jpeg"):
        kw = {"quality": int(quality), "optimize": True}
    elif ext == ".webp":
        kw = {"quality": int(quality)}
    elif ext == ".png":
        kw = {"optimize": True}
    tmp = path + ".part"
    im.save(tmp, format={".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP", ".bmp": "BMP",
                         ".gif": "GIF", ".tif": "TIFF", ".tiff": "TIFF"}.get(ext, "PNG"), **kw)
    os.replace(tmp, path)


# ---------- PSD (포토샵 파일) ----------
def _pascal(name, pad=4):
    raw = name.encode("cp949", "replace")[:255]
    data = bytes([len(raw)]) + raw
    while len(data) % pad:
        data += b"\0"
    return data


def _luni(name):
    u = name.encode("utf-16-be")
    body = struct.pack(">I", len(u) // 2) + u
    while len(body) % 4:
        body += b"\0"
    return b"8BIM" + b"luni" + struct.pack(">I", len(body)) + body


def save_psd(doc, path):
    """레이어가 살아 있는 PSD 저장 (포토샵 · 포토피아 · 포토크래프트에서 열 수 있다)"""
    w, h = doc.width, doc.height
    records, channel_data = b"", b""
    for ly in doc.layers:
        im = qimage_to_pil(ly.image)
        bbox = im.getchannel("A").getbbox()
        if bbox:
            x0, y0, x1, y1 = bbox
            part = im.crop(bbox)
            planes = [part.getchannel(c).tobytes() for c in ("A", "R", "G", "B")]
        else:
            x0 = y0 = x1 = y1 = 0
            planes = [b"", b"", b"", b""]
        rec = struct.pack(">iiiiH", y0, x0, y1, x1, 4)
        for cid, pl in zip((-1, 0, 1, 2), planes):
            rec += struct.pack(">hI", cid, len(pl) + 2)
            channel_data += struct.pack(">H", 0) + pl
        flags = 0x08 | (0x02 if not ly.visible else 0)
        rec += b"8BIM" + BLEND_PSD.get(ly.blend, b"norm")
        rec += struct.pack(">BBBB", int(round(ly.opacity * 255)), 0, flags, 0)
        extra = struct.pack(">I", 0) + struct.pack(">I", 0) + _pascal(ly.name) + _luni(ly.name)
        rec += struct.pack(">I", len(extra)) + extra
        records += rec
    layer_info = struct.pack(">h", len(doc.layers)) + records + channel_data
    if len(layer_info) % 2:
        layer_info += b"\0"
    layer_section = struct.pack(">I", len(layer_info)) + layer_info + struct.pack(">I", 0)
    merged = qimage_to_pil(doc.flattened())
    with open(path + ".part", "wb") as f:
        f.write(b"8BPS" + struct.pack(">H6xHIIHH", 1, 4, h, w, 8, 3))
        f.write(struct.pack(">I", 0))                       # 색상 모드 데이터
        f.write(struct.pack(">I", 0))                       # 이미지 리소스
        f.write(struct.pack(">I", len(layer_section)) + layer_section)
        f.write(struct.pack(">H", 0))                       # 합쳐진 그림: 압축 안 함
        for c in ("R", "G", "B", "A"):
            f.write(merged.getchannel(c).tobytes())
    os.replace(path + ".part", path)


def _decode_channel(data, comp, w, h):
    if w <= 0 or h <= 0:
        return None
    if comp == 0:
        return Image.frombytes("L", (w, h), data[: w * h])
    if comp == 1:
        return Image.frombytes("L", (w, h), data[h * 2:], "packbits", "L")
    if comp in (2, 3):
        import zlib
        raw = bytearray(zlib.decompress(data))
        if comp == 3:              # 예측(가로 차분) 풀기
            a = np.frombuffer(bytes(raw), np.uint8).reshape(h, w)
            raw = np.cumsum(a, axis=1, dtype=np.uint8).tobytes()
        return Image.frombytes("L", (w, h), bytes(raw))
    raise PhotoError("지원하지 않는 PSD 압축 방식이에요.")


def load_psd(path):
    """PSD 의 레이어(이름 · 보이기 · 불투명도 · 혼합 모드)를 살려서 연다.
    8비트 RGB 가 아니거나 해석이 안 되면 합쳐진 그림 한 장으로 연다."""
    try:
        return _load_psd_layers(path)
    except Exception:  # noqa: BLE001
        try:
            im = Image.open(path)
            im.seek(0)
            im = im.convert("RGBA")
        except Exception as e:  # noqa: BLE001
            raise PhotoError(f"PSD 파일을 열 수 없어요: {e}")
        doc = Document(im.width, im.height, None)
        doc.layers = [Layer("배경", pil_to_qimage(im))]
        doc.invalidate()
        return doc


def _load_psd_layers(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"8BPS":
        raise PhotoError("PSD 파일이 아니에요.")
    ver, channels, h, w, depth, mode = struct.unpack(">H6xHIIHH", data[4:26])
    if ver != 1 or depth != 8 or mode != 3:
        raise PhotoError("8비트 RGB PSD 만 레이어로 열 수 있어요.")
    pos = 26
    pos += 4 + struct.unpack(">I", data[pos:pos + 4])[0]     # 색상 모드
    pos += 4 + struct.unpack(">I", data[pos:pos + 4])[0]     # 리소스
    lm_len = struct.unpack(">I", data[pos:pos + 4])[0]
    pos += 4
    if lm_len == 0:
        raise PhotoError("레이어 정보 없음")
    li_len = struct.unpack(">I", data[pos:pos + 4])[0]
    pos += 4
    if li_len == 0:
        raise PhotoError("레이어 정보 없음")
    count = abs(struct.unpack(">h", data[pos:pos + 2])[0])
    pos += 2
    recs = []
    for _ in range(count):
        t, l, b, r, nch = struct.unpack(">iiiiH", data[pos:pos + 18])
        pos += 18
        chans = []
        for _ in range(nch):
            cid, ln = struct.unpack(">hI", data[pos:pos + 6])
            chans.append((cid, ln))
            pos += 6
        blend = data[pos + 4:pos + 8]
        opacity, flags = data[pos + 8], data[pos + 10]
        pos += 12
        extra_len = struct.unpack(">I", data[pos:pos + 4])[0]
        pos += 4
        extra = data[pos:pos + extra_len]
        pos += extra_len
        e = 0
        e += 4 + struct.unpack(">I", extra[e:e + 4])[0]    # 마스크
        e += 4 + struct.unpack(">I", extra[e:e + 4])[0]    # 혼합 범위
        nlen = extra[e]
        raw = extra[e + 1:e + 1 + nlen]
        try:
            name = raw.decode("cp949")
        except UnicodeDecodeError:
            name = raw.decode("latin-1")
        e += ((nlen + 1 + 3) // 4) * 4
        divider = 0
        while e + 12 <= len(extra) and extra[e:e + 4] in (b"8BIM", b"8B64"):
            key = extra[e + 4:e + 8]
            ln = struct.unpack(">I", extra[e + 8:e + 12])[0]
            body = extra[e + 12:e + 12 + ln]
            if key == b"luni" and len(body) >= 4:
                n = struct.unpack(">I", body[:4])[0]
                name = body[4:4 + n * 2].decode("utf-16-be", "replace").rstrip("\0")
            elif key in (b"lsct", b"lsdk") and len(body) >= 4:
                divider = struct.unpack(">I", body[:4])[0]
            e += 12 + ln
        recs.append(dict(rect=(l, t, r, b), chans=chans, blend=blend, opacity=opacity / 255,
                         visible=not (flags & 0x02), name=name, divider=divider))
    layers = []
    for rec in recs:
        l, t, r, b = rec["rect"]
        lw, lh = r - l, b - t
        planes = {}
        for cid, ln in rec["chans"]:
            comp = struct.unpack(">H", data[pos:pos + 2])[0]
            body = data[pos + 2:pos + ln]
            pos += ln
            if cid in (-1, 0, 1, 2):
                planes[cid] = _decode_channel(body, comp, lw, lh)
        if rec["divider"] in (1, 2, 3):        # 그룹(폴더) 표시용 레이어는 건너뜀
            continue
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if lw > 0 and lh > 0 and all(planes.get(c) is not None for c in (0, 1, 2)):
            a = planes.get(-1)
            a = a if a is not None else Image.new("L", (lw, lh), 255)
            part = Image.merge("RGBA", (planes[0], planes[1], planes[2], a))
            canvas.paste(part, (l, t))
        layers.append(Layer(rec["name"] or "레이어", pil_to_qimage(canvas), rec["visible"], rec["opacity"],
                            PSD_BLEND.get(rec["blend"], "normal")))
    if not layers:
        raise PhotoError("레이어 없음")
    doc = Document(w, h, None)
    doc.layers = layers
    doc.active = len(layers) - 1
    doc.invalidate()
    return doc


def apply_pil(img, fn, selection=None, **kw):
    """레이어 그림(QImage)에 필터를 적용. 선택 영역이 있으면 그 안에만."""
    out = pil_to_qimage(fn(qimage_to_pil(img), **kw))
    if selection is None or selection.isEmpty():
        return out
    res = QImage(img)
    p = QPainter(res)
    p.setClipPath(selection)
    p.setCompositionMode(QPainter.CompositionMode_Source)
    p.drawImage(0, 0, out)
    p.end()
    return res


def bounding(path, limit):
    return path.boundingRect().toAlignedRect().intersected(limit)


def translate_path(path, dx, dy):
    return path.translated(QPoint(dx, dy).toPointF())
