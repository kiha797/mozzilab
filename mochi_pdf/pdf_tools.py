"""PDF 작업 모음 (화면과 분리해서 따로 시험할 수 있게 만듦)
모든 함수의 첫 번째 인자 report(퍼센트, 메시지)는 진행 상황을 알리는 함수다."""
import os

import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader, PdfWriter

A4 = (595.28, 841.89)      # A4 크기 (pt, 1pt = 1/72 인치)


class PdfError(Exception):
    pass


def _noop(*_):
    pass


def open_reader(path, password=""):
    try:
        r = PdfReader(path)
    except Exception as e:     # noqa: BLE001
        raise PdfError(f"PDF 파일을 열 수 없습니다: {os.path.basename(path)}\n({e})")
    if r.is_encrypted:
        if not r.decrypt(password or ""):
            raise PdfError(f"암호가 걸린 PDF입니다: {os.path.basename(path)}\n'암호' 도구에서 먼저 암호를 풀어 주세요.")
    return r


def page_count(path, password=""):
    return len(open_reader(path, password).pages)


def parse_ranges(text, total):
    """'1-3, 5, 8-' 같은 쪽 범위를 [[0,1,2],[4],[7,8,...]] (0부터 시작) 으로 바꾼다. 빈 칸이면 전체."""
    text = (text or "").replace(" ", "").replace("~", "-")
    if not text:
        return [list(range(total))]
    out = []
    for part in text.split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start = int(a) if a else 1
            end = int(b) if b else total
        else:
            start = end = int(part)
        if start < 1 or end > total or start > end:
            raise PdfError(f"쪽 범위가 맞지 않습니다: '{part}' (이 PDF는 1~{total}쪽)")
        out.append(list(range(start - 1, end)))
    if not out:
        raise PdfError("쪽 범위를 입력해 주세요. 예: 1-3, 5, 8-")
    return out


def _write(writer, out):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        writer.write(f)


def merge(report, inputs, out):
    """여러 PDF를 순서대로 한 파일로 합친다."""
    if len(inputs) < 1:
        raise PdfError("합칠 PDF를 추가해 주세요.")
    w = PdfWriter()
    for i, path in enumerate(inputs):
        report(i * 100 / len(inputs), f"합치는 중: {os.path.basename(path)}")
        r = open_reader(path)
        for p in r.pages:
            w.add_page(p)
    report(95, "저장하는 중…")
    _write(w, out)
    return out


def split(report, src, out_dir, mode="each", ranges_text="", every=1):
    """나누기. mode: each(한 쪽씩) / every(N쪽씩) / ranges(범위마다 한 파일) / pick(고른 쪽만 한 파일)"""
    r = open_reader(src)
    total = len(r.pages)
    stem = os.path.splitext(os.path.basename(src))[0]
    if mode == "each":
        groups = [[i] for i in range(total)]
    elif mode == "every":
        n = max(1, int(every))
        groups = [list(range(i, min(i + n, total))) for i in range(0, total, n)]
    elif mode == "pick":
        groups = [sum(parse_ranges(ranges_text, total), [])]
    else:
        groups = parse_ranges(ranges_text, total)
    os.makedirs(out_dir, exist_ok=True)
    outputs = []
    for gi, pages in enumerate(groups):
        report(gi * 100 / len(groups), f"{gi + 1}/{len(groups)} 만드는 중…")
        w = PdfWriter()
        for p in pages:
            w.add_page(r.pages[p])
        label = f"{pages[0] + 1}" if len(pages) == 1 else f"{pages[0] + 1}-{pages[-1] + 1}"
        name = f"{stem}_선택한쪽.pdf" if mode == "pick" else f"{stem}_{label}쪽.pdf"
        path = os.path.join(out_dir, name)
        _write(w, path)
        outputs.append(path)
    return outputs


def edit_pages(report, src, out, order):
    """페이지 편집 결과 저장. order = [(원래 쪽 번호(0부터), 추가 회전각), ...] 화면에 보이는 순서대로"""
    if not order:
        raise PdfError("남은 쪽이 없습니다. 적어도 한 쪽은 남겨 주세요.")
    r = open_reader(src)
    w = PdfWriter()
    for i, (idx, rot) in enumerate(order):
        report(i * 100 / len(order), "쪽 정리하는 중…")
        page = w.add_page(r.pages[idx])
        if rot % 360:
            page.rotate(rot % 360)
    report(95, "저장하는 중…")
    _write(w, out)
    return out


def images_to_pdf(report, images, out, page_size="original", margin_mm=0):
    """이미지 여러 장을 한 PDF로. page_size: original / a4 / a4-landscape"""
    if not images:
        raise PdfError("이미지를 추가해 주세요.")
    pdf = pdfium.PdfDocument.new()
    margin = margin_mm * 72 / 25.4
    try:
        for i, path in enumerate(images):
            report(i * 100 / len(images), f"넣는 중: {os.path.basename(path)}")
            with Image.open(path) as im:
                im.load()
                if im.mode not in ("RGB", "L"):
                    bg = Image.new("RGB", im.size, "white")
                    rgba = im.convert("RGBA")
                    bg.paste(rgba, mask=rgba.split()[-1])
                    im = bg
                iw, ih = im.size
                dpi = im.info.get("dpi", (96, 96))[0] or 96
                if page_size == "original":
                    pw, ph = iw * 72 / dpi + 2 * margin, ih * 72 / dpi + 2 * margin
                else:
                    pw, ph = A4 if page_size == "a4" else (A4[1], A4[0])
                page = pdf.new_page(pw, ph)
                scale = min((pw - 2 * margin) / iw, (ph - 2 * margin) / ih)
                w, h = iw * scale, ih * scale
                obj = pdfium.PdfImage.new(pdf)
                bitmap = pdfium.PdfBitmap.from_pil(im)
                obj.set_bitmap(bitmap)
                obj.set_matrix(pdfium.PdfMatrix().scale(w, h).translate((pw - w) / 2, (ph - h) / 2))
                page.insert_obj(obj)
                page.gen_content()
                bitmap.close()
                page.close()
        report(95, "저장하는 중…")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        pdf.save(out)
    finally:
        pdf.close()
    return out


def render_page(path, index, width=None, scale=None, password=""):
    """한 쪽을 그림(PIL)으로. width(픽셀) 또는 scale 중 하나"""
    pdf = pdfium.PdfDocument(path, password=password or None)
    try:
        page = pdf[index]
        if width:
            scale = width / page.get_width()
        img = page.render(scale=scale or 1).to_pil()
        page.close()
        return img
    finally:
        pdf.close()


def thumbnails(report, path, width=150):
    """모든 쪽의 작은 그림 목록"""
    pdf = pdfium.PdfDocument(path)
    try:
        n = len(pdf)
        out = []
        for i in range(n):
            report(i * 100 / max(1, n), f"미리보기 {i + 1}/{n}")
            page = pdf[i]
            out.append(page.render(scale=width / page.get_width()).to_pil().convert("RGB"))
            page.close()
        return out
    finally:
        pdf.close()


def pdf_to_images(report, src, out_dir, dpi=150, fmt="png", ranges_text=""):
    total = page_count(src)
    pages = sum(parse_ranges(ranges_text, total), [])
    stem = os.path.splitext(os.path.basename(src))[0]
    os.makedirs(out_dir, exist_ok=True)
    pdf = pdfium.PdfDocument(src)
    outputs = []
    try:
        for k, i in enumerate(pages):
            report(k * 100 / len(pages), f"{i + 1}쪽 그림으로 바꾸는 중…")
            page = pdf[i]
            img = page.render(scale=dpi / 72).to_pil()
            page.close()
            ext = "jpg" if fmt == "jpg" else "png"
            path = os.path.join(out_dir, f"{stem}_{i + 1:03d}.{ext}")
            if ext == "jpg":
                img.convert("RGB").save(path, "JPEG", quality=92)
            else:
                img.save(path, "PNG")
            outputs.append(path)
    finally:
        pdf.close()
    return outputs


COMPRESS_LEVELS = {            # (JPEG 품질, 그림 최대 크기 px)
    "low": (85, 2400),
    "medium": (70, 1800),
    "high": (50, 1200),
}


def compress(report, src, out, level="medium"):
    """용량 줄이기: 글자·도형 정보 압축 + 그림 화질/크기 줄이기. (원래 크기, 새 크기) 를 돌려준다."""
    quality, max_px = COMPRESS_LEVELS.get(level, COMPRESS_LEVELS["medium"])
    r = open_reader(src)
    w = PdfWriter(clone_from=r)
    n = len(w.pages)
    for i, page in enumerate(w.pages):
        report(i * 90 / max(1, n), f"{i + 1}/{n}쪽 줄이는 중…")
        try:
            for img in page.images:
                try:
                    pil = img.image
                    if pil.width * pil.height < 150 * 150:
                        continue
                    if max(pil.size) > max_px:
                        pil = pil.copy()
                        pil.thumbnail((max_px, max_px))
                    if pil.mode not in ("RGB", "L"):
                        pil = pil.convert("RGB")
                    img.replace(pil, quality=quality)
                except Exception:      # noqa: BLE001 - 바꿀 수 없는 그림은 그대로 둔다
                    continue
        except Exception:              # noqa: BLE001
            pass
        page.compress_content_streams(level=9)
    report(92, "중복 정리하는 중…")
    w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    _write(w, out)
    before, after = os.path.getsize(src), os.path.getsize(out)
    if after >= before:                # 더 커지면 원본 그대로 복사
        with open(src, "rb") as fi, open(out, "wb") as fo:
            fo.write(fi.read())
        after = before
    return before, after


def protect(report, src, out, password):
    if not password:
        raise PdfError("암호를 입력해 주세요.")
    report(10, "암호 거는 중…")
    w = PdfWriter(clone_from=open_reader(src))
    w.encrypt(user_password=password, owner_password=None, algorithm="AES-256")
    _write(w, out)
    return out


def unlock(report, src, out, password):
    report(10, "암호 푸는 중…")
    r = PdfReader(src)
    if r.is_encrypted and not r.decrypt(password or ""):
        raise PdfError("암호가 맞지 않습니다.")
    w = PdfWriter(clone_from=r)
    _write(w, out)
    return out


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"
