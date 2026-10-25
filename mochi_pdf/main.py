"""모찌PDF - PDF 합치기 · 나누기 · 페이지 편집 · 이미지↔PDF · 용량 줄이기 · 암호"""
import os
import sys

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
# 모찌랩 프로그램들이 함께 쓰는 코드(로그인·광고·디자인)는 ../shared 폴더에 있다
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared"))

from PySide6.QtCore import QSize, Qt  # noqa: E402
from PySide6.QtGui import QImage, QPixmap, QTransform  # noqa: E402
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QComboBox, QFileDialog,  # noqa: E402
                               QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QRadioButton, QSpinBox, QVBoxLayout, QWidget)

import brand  # noqa: E402
import pdf_tools as T  # noqa: E402
import winapi  # noqa: E402
from app_shell import MozziWindow  # noqa: E402
from ui import icon, px, stylesheet  # noqa: E402
from widgets import (DropFileList, FilePicker, FolderPicker, ToolCard, human_size,  # noqa: E402
                     list_buttons, primary_button, title_label)

PDF_FILTER = "PDF 파일 (*.pdf)"
IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff")
IMG_FILTER = "이미지 (*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tif *.tiff)"

TOOLS = [  # (키, 버튼 이름, 아이콘, 카드 설명, 색)
    ("merge", "합치기", "merge", "여러 PDF를 하나로", "#ff6f91"),
    ("split", "나누기", "split", "쪽별·범위별로 나누기", "#ffb86b"),
    ("pages", "페이지 편집", "pages", "회전 · 삭제 · 순서 바꾸기", "#7ec8a9"),
    ("img2pdf", "이미지→PDF", "img2pdf", "사진·스캔 이미지를 PDF로", "#5a8dee"),
    ("pdf2img", "PDF→이미지", "pdf2img", "쪽마다 PNG·JPG로 저장", "#a66cff"),
    ("compress", "용량 줄이기", "compress", "메일로 보내기 좋게 작게", "#ff8f5a"),
    ("lock", "암호", "lock", "암호 걸기 · 풀기", "#6b5d5d"),
]


def pil_to_pixmap(img):
    img = img.convert("RGBA")
    q = QImage(img.tobytes(), img.width, img.height, img.width * 4, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(q)


def pdf_info(path):
    try:
        return f"{T.page_count(path)}쪽 · {human_size(os.path.getsize(path))}"
    except T.PdfError:
        return "🔒 암호/손상 · " + human_size(os.path.getsize(path))


def page_wrap(*widgets, stretch=True):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(px(36), px(26), px(36), px(26))
    v.setSpacing(px(12))
    for x in widgets:
        if isinstance(x, QWidget):
            v.addWidget(x)
        elif x == "stretch":
            v.addStretch(1)
        else:
            v.addLayout(x)
    if stretch:
        v.addStretch(1)
    return w


def same_dir_or(folder_picker, src):
    return folder_picker.path() or os.path.dirname(os.path.abspath(src))


class PdfWindow(MozziWindow):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.tool_buttons = {}
        self.pages = {}
        b = self.add_tool("처음", "home", lambda: self.show_tool("home"), True)
        self.tool_buttons["home"] = b
        self.add_separator()
        for key, name, ic, desc, _ in TOOLS:
            self.tool_buttons[key] = self.add_tool(name, ic, lambda _=False, k=key: self.show_tool(k), True, desc)

        self._add_page("home", self._home())
        self._add_page("merge", self._merge())
        self._add_page("split", self._split())
        self._add_page("pages", self._pages())
        self._add_page("img2pdf", self._img2pdf())
        self._add_page("pdf2img", self._pdf2img())
        self._add_page("compress", self._compress())
        self._add_page("lock", self._lock())
        self.show_tool("home")

    # ---------- 공통 ----------
    def _add_page(self, key, w):
        self.pages[key] = w
        self.body.addWidget(w)

    def show_tool(self, key):
        self.body.setCurrentWidget(self.pages[key])
        for k, b in self.tool_buttons.items():
            b.setChecked(k == key)

    def _start(self):
        return self.cfg.start_dir()

    def _remember(self, p):
        self.cfg.remember_dir(p)

    def _picker(self):
        return FilePicker((".pdf",), PDF_FILTER, self._start, self._remember)

    def _save_as(self, default_name):
        path, _ = QFileDialog.getSaveFileName(self, "저장", os.path.join(self._start(), default_name), PDF_FILTER)
        if path and not path.lower().endswith(".pdf"):
            path += ".pdf"
        if path:
            self._remember(path)
        return path

    def _done_file(self, title, path):
        self.job_done(title, path, path)

    def _done_folder(self, title, paths):
        if paths:
            self.job_done(title, f"{len(paths)}개 파일을 만들었습니다.\n{os.path.dirname(paths[0])}", paths[0])

    def open_pdf(self, path):
        """파일을 끌어다 놓거나 'PDF로 열기' 했을 때: 페이지 편집으로 연다"""
        self.show_tool("pages")
        self.pages_picker.set_path(path)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        files = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        pdfs = [f for f in files if f.lower().endswith(".pdf")]
        imgs = [f for f in files if f.lower().endswith(IMG_EXTS)]
        if imgs and not pdfs:
            self.show_tool("img2pdf")
            self.img_list.add_paths(imgs)
        elif len(pdfs) > 1:
            self.show_tool("merge")
            self.merge_list.add_paths(pdfs)
        elif pdfs:
            self.open_pdf(pdfs[0])

    # ---------- 처음 화면 ----------
    def _home(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(px(40), px(30), px(40), px(30))
        v.addWidget(title_label("무엇을 할까요? 🍡", "도구를 누르거나, PDF·이미지 파일을 이 창에 끌어다 놓으세요."))
        grid = QGridLayout()
        grid.setSpacing(px(16))
        for i, (key, name, ic, desc, color) in enumerate(TOOLS):
            c = ToolCard(name, desc, ic, color)
            c.clicked.connect(lambda _=False, k=key: self.show_tool(k))
            grid.addWidget(c, i // 4, i % 4)
        v.addLayout(grid)
        v.addStretch(1)
        return w

    # ---------- 합치기 ----------
    def _merge(self):
        self.merge_list = DropFileList((".pdf",), "PDF 파일들을 여기에 끌어다 놓으세요 (위→아래 순서로 합쳐요)", pdf_info)
        btns = list_buttons(self.merge_list, PDF_FILTER, self._start, self._remember)
        go = primary_button("PDF 합치기")

        def run():
            files = self.merge_list.paths()
            if len(files) < 2:
                return self.statusBar().showMessage("PDF를 2개 이상 추가해 주세요.", 4000)
            out = self._save_as("합친문서.pdf")
            if out:
                self.run_task("합치기", T.merge, files, out, on_done=lambda p: self._done_file("합치기 완료", p))

        go.clicked.connect(run)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(go)
        w = page_wrap(title_label("PDF 합치기", "여러 PDF를 순서대로 한 파일로 합칩니다. 끌어서 순서를 바꿀 수 있어요."),
                      btns, self.merge_list, row, stretch=False)
        return w

    # ---------- 나누기 ----------
    def _split(self):
        picker = self._picker()
        info = QLabel("")
        info.setStyleSheet("color:#8a7c7e;")
        picker.picked.connect(lambda p: info.setText(pdf_info(p)))
        group = QButtonGroup(self)
        r_each = QRadioButton("한 쪽씩 모두 나누기")
        r_every = QRadioButton("몇 쪽씩 나누기")
        r_ranges = QRadioButton("범위마다 한 파일로")
        r_pick = QRadioButton("고른 쪽만 뽑아서 한 파일로")
        r_each.setChecked(True)
        for i, r in enumerate((r_each, r_every, r_ranges, r_pick)):
            group.addButton(r, i)
        every = QSpinBox()
        every.setRange(1, 9999)
        every.setValue(2)
        every.setSuffix(" 쪽씩")
        ranges = QLineEdit()
        ranges.setPlaceholderText("예: 1-3, 5, 8-  (8쪽부터 끝까지)")
        out = FolderPicker(self._start)
        form = QFormLayout()
        form.addRow("PDF 파일", picker)
        form.addRow("", info)
        modes = QVBoxLayout()
        line = QHBoxLayout()
        line.addWidget(r_every)
        line.addWidget(every)
        line.addStretch(1)
        modes.addWidget(r_each)
        modes.addLayout(line)
        modes.addWidget(r_ranges)
        modes.addWidget(r_pick)
        form.addRow("나누는 방법", modes)
        form.addRow("쪽 범위", ranges)
        form.addRow("저장 폴더", out)
        go = primary_button("나누기")

        def run():
            src = picker.path()
            if not src:
                return self.statusBar().showMessage("PDF 파일을 골라 주세요.", 4000)
            mode = ["each", "every", "ranges", "pick"][group.checkedId()]
            folder = same_dir_or(out, src)
            self.run_task("나누기", T.split, src, folder, mode, ranges.text(), every.value(),
                          on_done=lambda ps: self._done_folder("나누기 완료", ps))

        go.clicked.connect(run)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(go)
        return page_wrap(title_label("PDF 나누기", "한 파일을 여러 파일로 나누거나, 필요한 쪽만 뽑아냅니다."), form, row)

    # ---------- 페이지 편집 ----------
    def _pages(self):
        self.pages_picker = self._picker()
        grid = QListWidget()
        grid.setViewMode(QListWidget.IconMode)
        grid.setIconSize(QSize(px(150), px(200)))
        grid.setGridSize(QSize(px(176), px(240)))
        grid.setResizeMode(QListWidget.Adjust)
        grid.setMovement(QListWidget.Snap)
        grid.setDragDropMode(QAbstractItemView.InternalMove)
        grid.setSelectionMode(QAbstractItemView.ExtendedSelection)
        grid.setSpacing(px(8))
        grid.setStyleSheet(f"QListWidget {{ background: #f3eeec; border: none; border-radius: {px(12)}px; padding: {px(10)}px; }}"
                           "QListWidget::item { color: #3b2f2f; }"
                           "QListWidget::item:selected { background: #ffe3eb; border-radius: 8px; }")
        self.page_grid = grid
        self._thumbs = []

        def label(it):
            idx, rot = it.data(Qt.UserRole)
            return f"{idx + 1}쪽" + (f" ↻{rot % 360}°" if rot % 360 else "")

        def set_icon(it):
            idx, rot = it.data(Qt.UserRole)
            pm = self._thumbs[idx]
            if rot % 360:
                pm = pm.transformed(QTransform().rotate(rot % 360))
            it.setIcon(pm)
            it.setText(label(it))

        def load(path):
            grid.clear()
            self.run_task("미리보기", T.thumbnails, path, px(150), on_done=show)

        def show(thumbs):
            self._thumbs = [pil_to_pixmap(t) for t in thumbs]
            grid.clear()
            for i in range(len(self._thumbs)):
                it = QListWidgetItem()
                it.setData(Qt.UserRole, (i, 0))
                set_icon(it)
                grid.addItem(it)
            self.statusBar().showMessage(f"{len(thumbs)}쪽을 불러왔습니다. 끌어서 순서를 바꾸고, 골라서 회전·삭제하세요.", 6000)

        def rotate(deg):
            for it in grid.selectedItems():
                idx, rot = it.data(Qt.UserRole)
                it.setData(Qt.UserRole, (idx, rot + deg))
                set_icon(it)

        def delete():
            for it in grid.selectedItems():
                grid.takeItem(grid.row(it))

        def save():
            src = self.pages_picker.path()
            if not src or grid.count() == 0:
                return self.statusBar().showMessage("먼저 PDF를 열어 주세요.", 4000)
            order = [grid.item(i).data(Qt.UserRole) for i in range(grid.count())]
            outp = self._save_as(os.path.splitext(os.path.basename(src))[0] + "_편집.pdf")
            if outp:
                self.run_task("저장", T.edit_pages, src, outp, order, on_done=lambda p: self._done_file("페이지 편집 완료", p))

        self.pages_picker.picked.connect(load)
        bar = QHBoxLayout()
        for text, ic, fn in (("왼쪽으로 돌리기", "rotl", lambda: rotate(-90)), ("오른쪽으로 돌리기", "rotr", lambda: rotate(90)),
                             ("삭제", "trash", delete), ("모두 선택", "pages", grid.selectAll),
                             ("처음 상태로", "reset", lambda: self.pages_picker.path() and load(self.pages_picker.path()))):
            b = QPushButton(" " + text)
            b.setIcon(icon(ic))
            b.clicked.connect(fn)
            bar.addWidget(b)
        bar.addStretch(1)
        go = primary_button("다른 이름으로 저장")
        go.clicked.connect(save)
        bar.addWidget(go)
        return page_wrap(title_label("페이지 편집", "쪽을 끌어서 순서를 바꾸고, 골라서 돌리거나 지운 뒤 저장하세요."),
                         self.pages_picker, bar, grid, stretch=False)

    # ---------- 이미지 → PDF ----------
    def _img2pdf(self):
        self.img_list = DropFileList(IMG_EXTS, "사진·스캔 이미지를 여기에 끌어다 놓으세요")
        btns = list_buttons(self.img_list, IMG_FILTER, self._start, self._remember)
        size = QComboBox()
        size.addItem("이미지 크기 그대로", "original")
        size.addItem("A4 세로", "a4")
        size.addItem("A4 가로", "a4-landscape")
        margin = QSpinBox()
        margin.setRange(0, 50)
        margin.setSuffix(" mm")
        opt = QHBoxLayout()
        opt.addWidget(QLabel("쪽 크기"))
        opt.addWidget(size)
        opt.addSpacing(px(16))
        opt.addWidget(QLabel("여백"))
        opt.addWidget(margin)
        opt.addStretch(1)
        go = primary_button("PDF 만들기")
        opt.addWidget(go)

        def run():
            files = self.img_list.paths()
            if not files:
                return self.statusBar().showMessage("이미지를 추가해 주세요.", 4000)
            out = self._save_as("이미지모음.pdf")
            if out:
                self.run_task("PDF 만들기", T.images_to_pdf, files, out, size.currentData(), margin.value(),
                              on_done=lambda p: self._done_file("PDF 만들기 완료", p))

        go.clicked.connect(run)
        return page_wrap(title_label("이미지 → PDF", "여러 장의 사진을 순서대로 한 PDF로 만듭니다."), btns, self.img_list, opt,
                         stretch=False)

    # ---------- PDF → 이미지 ----------
    def _pdf2img(self):
        picker = self._picker()
        dpi = QComboBox()
        for label, v in (("보통 (150dpi)", 150), ("화면용 (96dpi)", 96), ("인쇄용 고화질 (300dpi)", 300)):
            dpi.addItem(label, v)
        fmt = QComboBox()
        fmt.addItem("PNG (선명)", "png")
        fmt.addItem("JPG (작은 용량)", "jpg")
        ranges = QLineEdit()
        ranges.setPlaceholderText("비우면 모든 쪽. 예: 1-3, 7")
        out = FolderPicker(self._start)
        form = QFormLayout()
        form.addRow("PDF 파일", picker)
        form.addRow("화질", dpi)
        form.addRow("그림 형식", fmt)
        form.addRow("쪽 범위", ranges)
        form.addRow("저장 폴더", out)
        go = primary_button("이미지로 저장")

        def run():
            src = picker.path()
            if not src:
                return self.statusBar().showMessage("PDF 파일을 골라 주세요.", 4000)
            folder = os.path.join(same_dir_or(out, src), os.path.splitext(os.path.basename(src))[0] + "_이미지")
            self.run_task("이미지로 바꾸기", T.pdf_to_images, src, folder, dpi.currentData(), fmt.currentData(), ranges.text(),
                          on_done=lambda ps: self._done_folder("이미지 저장 완료", ps))

        go.clicked.connect(run)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(go)
        return page_wrap(title_label("PDF → 이미지", "PDF의 각 쪽을 그림 파일로 저장합니다."), form, row)

    # ---------- 용량 줄이기 ----------
    def _compress(self):
        picker = self._picker()
        info = QLabel("")
        info.setStyleSheet("color:#8a7c7e;")
        picker.picked.connect(lambda p: info.setText(f"지금 크기: {human_size(os.path.getsize(p))}"))
        group = QButtonGroup(self)
        opts = QVBoxLayout()
        for i, (key, text) in enumerate((("low", "조금 줄이기 — 화질 거의 그대로"),
                                         ("medium", "보통 — 추천"),
                                         ("high", "많이 줄이기 — 메일·카톡 전송용"))):
            r = QRadioButton(text)
            r.setProperty("level", key)
            group.addButton(r, i)
            opts.addWidget(r)
            if key == "medium":
                r.setChecked(True)
        result = QLabel("")
        result.setStyleSheet("font-size: 13pt; font-weight: bold; color: #e8557a;")
        form = QFormLayout()
        form.addRow("PDF 파일", picker)
        form.addRow("", info)
        form.addRow("줄이는 정도", opts)
        go = primary_button("용량 줄이기")

        def run():
            src = picker.path()
            if not src:
                return self.statusBar().showMessage("PDF 파일을 골라 주세요.", 4000)
            out = self._save_as(os.path.splitext(os.path.basename(src))[0] + "_작게.pdf")
            if not out:
                return
            level = group.checkedButton().property("level")

            def done(sizes):
                before, after = sizes
                pct = round((1 - after / before) * 100) if before else 0
                result.setText(f"{human_size(before)} → {human_size(after)}  ({pct}% 줄었어요)" if pct > 0
                               else "이미 충분히 작은 파일이라 더 줄이지 못했어요.")
                self._done_file("용량 줄이기 완료", out)

            self.run_task("용량 줄이기", T.compress, src, out, level, on_done=done)

        go.clicked.connect(run)
        row = QHBoxLayout()
        row.addWidget(result)
        row.addStretch(1)
        row.addWidget(go)
        return page_wrap(title_label("PDF 용량 줄이기", "그림 화질과 크기를 줄여 파일을 작게 만듭니다. 원본은 그대로 남아요."), form, row)

    # ---------- 암호 ----------
    def _lock(self):
        picker = self._picker()
        group = QButtonGroup(self)
        r_lock = QRadioButton("암호 걸기 (열 때 암호를 묻게)")
        r_unlock = QRadioButton("암호 풀기 (암호 없는 PDF로 저장)")
        r_lock.setChecked(True)
        group.addButton(r_lock, 0)
        group.addButton(r_unlock, 1)
        pw = QLineEdit()
        pw.setEchoMode(QLineEdit.Password)
        pw2 = QLineEdit()
        pw2.setEchoMode(QLineEdit.Password)
        form = QFormLayout()
        form.addRow("PDF 파일", picker)
        modes = QVBoxLayout()
        modes.addWidget(r_lock)
        modes.addWidget(r_unlock)
        form.addRow("작업", modes)
        form.addRow("암호", pw)
        pw2_label = QLabel("암호 확인")
        form.addRow(pw2_label, pw2)
        r_unlock.toggled.connect(lambda on: (pw2.setVisible(not on), pw2_label.setVisible(not on)))
        go = primary_button("저장")

        def run():
            src = picker.path()
            if not src:
                return self.statusBar().showMessage("PDF 파일을 골라 주세요.", 4000)
            if r_lock.isChecked():
                if len(pw.text()) < 4:
                    return self.statusBar().showMessage("암호는 4자 이상으로 정해 주세요.", 4000)
                if pw.text() != pw2.text():
                    return self.statusBar().showMessage("암호 확인이 일치하지 않습니다.", 4000)
            stem = os.path.splitext(os.path.basename(src))[0]
            out = self._save_as(stem + ("_암호.pdf" if r_lock.isChecked() else "_암호해제.pdf"))
            if not out:
                return
            fn = T.protect if r_lock.isChecked() else T.unlock
            self.run_task("암호 처리", fn, src, out, pw.text(),
                          on_done=lambda p: (pw.clear(), pw2.clear(), self._done_file("암호 처리 완료", p)))

        go.clicked.connect(run)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(go)
        return page_wrap(title_label("PDF 암호", "중요한 문서에 암호를 걸거나, 아는 암호를 풀어서 저장합니다."), form, row)


def selftest():
    """설치파일이 제대로 만들어졌는지 점검 (GitHub 자동 빌드에서 사용): 성공하면 0"""
    import tempfile
    from PIL import Image
    d = tempfile.mkdtemp()
    img = os.path.join(d, "a.png")
    Image.new("RGB", (300, 200), "#ff6f91").save(img)
    noop = lambda *_: None  # noqa: E731
    a = T.images_to_pdf(noop, [img, img], os.path.join(d, "a.pdf"))
    m = T.merge(noop, [a, a], os.path.join(d, "m.pdf"))
    assert T.page_count(m) == 4
    assert len(T.thumbnails(noop, m, 50)) == 4
    T.compress(noop, m, os.path.join(d, "c.pdf"))
    app = QApplication.instance() or QApplication(sys.argv)
    PdfWindow()
    return 0


def main():
    if "--selftest" in sys.argv:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        return selftest()
    winapi.set_app_id(brand.APP_ID)
    app = QApplication(sys.argv)
    app.setApplicationName(brand.APP_NAME)
    app.setStyleSheet(stylesheet())
    win = PdfWindow()
    win.show()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args and os.path.isfile(args[0]):
        win.open_pdf(args[0]) if args[0].lower().endswith(".pdf") else None
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
