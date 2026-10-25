"""모찌압축 - ZIP · 7Z 압축하기 / 열기 / 풀기 (암호, 한글 파일 이름 지원)
명령줄:  MochiZip.exe 파일.zip            → 압축 파일 열기
        MochiZip.exe --extract-here 파일  → 같은 폴더에 바로 풀기
        MochiZip.exe --compress 폴더…      → 바로 ZIP 으로 압축"""
import os
import sys

os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
# 모찌랩 프로그램들이 함께 쓰는 코드(로그인·광고·디자인)는 ../shared 폴더에 있다
sys.path.insert(1, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared"))

from PySide6.QtCore import Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFileDialog, QFormLayout,  # noqa: E402
                               QGridLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

import archive_tools as A  # noqa: E402
import brand  # noqa: E402
import winapi  # noqa: E402
from app_shell import MozziWindow  # noqa: E402
from ui import icon, px, stylesheet  # noqa: E402
from widgets import DropFileList, FilePicker, ToolCard, human_size, list_buttons, primary_button, title_label  # noqa: E402

FORMATS = [("ZIP (어디서나 열림, 추천)", "zip"), ("7Z (더 작게, 모찌압축·7-Zip 필요)", "7z")]
LEVELS = [("보통 (추천)", "normal"), ("빠르게", "fast"), ("최대한 작게 (느림)", "max")]


def page_wrap(*items, stretch=True):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(px(36), px(26), px(36), px(26))
    v.setSpacing(px(12))
    for x in items:
        if isinstance(x, QWidget):
            v.addWidget(x)
        else:
            v.addLayout(x)
    if stretch:
        v.addStretch(1)
    return w


class ZipWindow(MozziWindow):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.tools = {}
        self.pages = {}
        self.archive = None
        self.password = None
        self.tools["home"] = self.add_tool("처음", "home", lambda: self.show_page("home"), True)
        self.add_separator()
        self.tools["compress"] = self.add_tool("압축하기", "zipnew", lambda: self.show_page("compress"), True,
                                               "파일·폴더를 ZIP/7Z 로 묶기")
        self.tools["open"] = self.add_tool("압축 파일 열기", "zipopen", self.choose_archive, True, "안에 든 파일 보기")
        self.add_tool("바로 풀기", "extract", self.choose_and_extract, False, "고른 압축 파일을 같은 폴더에 풀기")
        self.pages["home"] = self._home()
        self.pages["compress"] = self._compress()
        self.pages["open"] = self._viewer()
        for w in self.pages.values():
            self.body.addWidget(w)
        self.show_page("home")

    def show_page(self, key):
        self.body.setCurrentWidget(self.pages[key])
        for k, b in self.tools.items():
            b.setChecked(k == key)

    def _start(self):
        return self.cfg.start_dir()

    def _remember(self, p):
        self.cfg.remember_dir(p)

    # ---------- 끌어다 놓기 ----------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        archives = [p for p in paths if p.lower().endswith(A.OPEN_EXTS)]
        if len(paths) == 1 and archives:
            self.open_archive(archives[0])
        else:
            self.show_page("compress")
            self.src_list.add_paths(paths)

    # ---------- 처음 ----------
    def _home(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(px(40), px(30), px(40), px(30))
        v.addWidget(title_label("무엇을 할까요? 🍡", "압축 파일을 이 창에 끌어다 놓으면 바로 열리고, 파일·폴더를 끌어다 놓으면 압축 준비가 돼요."))
        grid = QGridLayout()
        grid.setSpacing(px(16))
        cards = [("압축하기", "파일·폴더를 하나로 꾹!", "zipnew", "#ff6f91", lambda: self.show_page("compress")),
                 ("압축 파일 열기", "안에 무엇이 있는지 보고 골라서 풀기", "zipopen", "#7ec8a9", self.choose_archive),
                 ("바로 풀기", "같은 폴더에 바로 풀기", "extract", "#ffb86b", self.choose_and_extract)]
        for i, (t, d, ic, color, fn) in enumerate(cards):
            c = ToolCard(t, d, ic, color)
            c.setMinimumSize(px(300), px(180))
            c.clicked.connect(fn)
            grid.addWidget(c, 0, i)
        v.addLayout(grid)
        tip = QLabel("✔ ZIP · 7Z · TAR(GZ/BZ2/XZ) 열기   ✔ 암호 압축(AES-256)   ✔ 한글 파일 이름이 깨진 ZIP 도 올바르게")
        tip.setStyleSheet("color:#8a7c7e; margin-top: 12px;")
        v.addWidget(tip)
        v.addStretch(1)
        return w

    # ---------- 압축하기 ----------
    def _compress(self):
        self.src_list = DropFileList((), "압축할 파일·폴더를 여기에 끌어다 놓으세요", keep_dirs=True)
        btns = list_buttons(self.src_list, "모든 파일 (*.*)", self._start, self._remember)
        add_dir = QPushButton(" 폴더 추가")
        add_dir.setIcon(icon("folderadd"))
        add_dir.clicked.connect(self._add_folder)
        btns.insertWidget(1, add_dir)
        self.fmt = QComboBox()
        for t, k in FORMATS:
            self.fmt.addItem(t, k)
        self.level = QComboBox()
        for t, k in LEVELS:
            self.level.addItem(t, k)
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.Password)
        self.pw.setPlaceholderText("비워두면 암호 없이")
        form = QFormLayout()
        form.addRow("형식", self.fmt)
        form.addRow("압축 정도", self.level)
        form.addRow("암호 (선택)", self.pw)
        go = primary_button("압축하기")
        go.clicked.connect(lambda: self.compress_now())
        row = QHBoxLayout()
        row.addLayout(form)
        row.addStretch(1)
        row.addWidget(go, 0, Qt.AlignBottom)
        return page_wrap(title_label("압축하기", "여러 파일과 폴더를 하나의 압축 파일로 묶습니다."), btns, self.src_list, row,
                         stretch=False)

    def _add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "폴더 추가", self._start())
        if d:
            self._remember(d)
            self.src_list.add_paths([d])

    def compress_now(self, ask=True):
        srcs = self.src_list.paths()
        if not srcs:
            return self.statusBar().showMessage("압축할 파일이나 폴더를 추가해 주세요.", 4000)
        fmt = self.fmt.currentData()
        first = srcs[0].rstrip("/\\")
        base = os.path.basename(first) if len(srcs) == 1 else os.path.basename(os.path.dirname(first)) or "압축"
        if len(srcs) == 1 and os.path.isfile(first):
            base = os.path.splitext(base)[0]
        default = os.path.join(os.path.dirname(first), f"{base}.{fmt}")
        if ask:
            out, _ = QFileDialog.getSaveFileName(self, "압축 파일 저장", default, f"{fmt.upper()} 파일 (*.{fmt})")
            if not out:
                return
            if not out.lower().endswith("." + fmt):
                out += "." + fmt
        else:
            out, n = default, 2
            while os.path.exists(out):
                out = os.path.join(os.path.dirname(first), f"{base} ({n}).{fmt}")
                n += 1
        self._remember(out)
        pw = self.pw.text()

        def done(path):
            self.pw.clear()
            self.job_done("압축 완료", f"{os.path.basename(path)} · {human_size(os.path.getsize(path))}", path)

        self.run_task("압축", A.create, srcs, out, fmt, self.level.currentData(), pw, on_done=done)

    # ---------- 압축 파일 보기 ----------
    def _viewer(self):
        self.archive_picker = FilePicker(A.OPEN_EXTS, A.FILTER, self._start, self._remember, "압축 파일을 고르거나 끌어다 놓으세요")
        self.archive_picker.picked.connect(self.open_archive)
        self.info = QLabel("")
        self.info.setStyleSheet("color:#8a7c7e;")
        tree = QTreeWidget()
        tree.setHeaderLabels(["이름", "크기", "압축된 크기", "수정한 날짜"])
        tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        tree.setAlternatingRowColors(True)
        tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        tree.setStyleSheet(f"QTreeWidget {{ background: white; border: 1px solid #efe6e3; border-radius: {px(10)}px; font-size: 10.5pt; }}"
                           "QTreeWidget::item:selected { background: #ffe3eb; color: #3b2f2f; }")
        self.tree = tree
        row = QHBoxLayout()
        sel = QPushButton(" 고른 것만 풀기…")
        sel.setIcon(icon("extract"))
        sel.clicked.connect(lambda: self.extract_current(selected=True))
        row.addWidget(sel)
        row.addStretch(1)
        here = QPushButton("같은 폴더에 풀기")
        here.clicked.connect(lambda: self.extract_current(here=True))
        row.addWidget(here)
        allb = primary_button("모두 풀기…")
        allb.clicked.connect(lambda: self.extract_current())
        row.addWidget(allb)
        return page_wrap(title_label("압축 파일 열기", "안에 든 파일을 보고, 전부 또는 골라서 풀 수 있어요."),
                         self.archive_picker, self.info, tree, row, stretch=False)

    def choose_archive(self):
        self.show_page("open")
        if not self.archive:
            self.archive_picker.browse()

    def _ask_password(self, msg="암호가 걸린 압축 파일입니다. 암호를 입력하세요."):
        pw, ok = QInputDialog.getText(self, brand.APP_NAME, msg, QLineEdit.Password)
        return pw if ok and pw else None

    def open_archive(self, path):
        self.show_page("open")
        if self.archive_picker.path() != path:
            self.archive_picker.edit.setText(path)
        self.archive, self.password = path, None
        self.tree.clear()
        while True:
            try:
                entries = A.list_entries(path, self.password)
                break
            except A.NeedPassword as e:
                self.password = self._ask_password(str(e) + "\n암호를 입력하세요.")
                if self.password is None:
                    self.info.setText("암호를 입력하지 않아 목록을 볼 수 없습니다.")
                    return
            except A.ArchiveError as e:
                QMessageBox.warning(self, brand.APP_NAME, str(e))
                self.archive = None
                return
        nodes = {}

        def node(parts):
            key = "/".join(parts)
            if key in nodes:
                return nodes[key]
            parent = node(parts[:-1]) if len(parts) > 1 else None
            it = QTreeWidgetItem([parts[-1], "", "", ""])
            it.setIcon(0, icon("folder"))
            it.setData(0, Qt.UserRole, key)
            (parent.addChild(it) if parent else self.tree.addTopLevelItem(it))
            nodes[key] = it
            return it

        total = 0
        files = 0
        for e in sorted(entries, key=lambda x: (x.name.count("/"), x.name)):
            parts = [p for p in e.name.split("/") if p]
            if not parts:
                continue
            if e.is_dir:
                node(parts)
                continue
            parent = node(parts[:-1]) if len(parts) > 1 else None
            it = QTreeWidgetItem([parts[-1], human_size(e.size), human_size(e.packed),
                                  e.mtime.strftime("%Y-%m-%d %H:%M") if e.mtime else ""])
            it.setIcon(0, icon("lock") if e.encrypted else icon("file"))
            it.setData(0, Qt.UserRole, e.name)
            it.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            it.setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
            (parent.addChild(it) if parent else self.tree.addTopLevelItem(it))
            total += e.size
            files += 1
        if self.tree.topLevelItemCount() <= 3:
            self.tree.expandAll()
        self.tree.resizeColumnToContents(1)
        self.tree.resizeColumnToContents(2)
        self.tree.resizeColumnToContents(3)
        lock = " · 🔒 암호" if self.password else ""
        self.info.setText(f"파일 {files}개 · 풀면 {human_size(total)} · 압축 파일 {human_size(os.path.getsize(path))}{lock}")

    def extract_current(self, selected=False, here=False):
        if not self.archive:
            return self.statusBar().showMessage("먼저 압축 파일을 열어 주세요.", 4000)
        names = None
        if selected:
            names = [it.data(0, Qt.UserRole) for it in self.tree.selectedItems()]
            if not names:
                return self.statusBar().showMessage("풀 항목을 목록에서 골라 주세요. (Ctrl·Shift 로 여러 개)", 4000)
        if here:
            dest = A.default_extract_dir(self.archive)
        else:
            d = QFileDialog.getExistingDirectory(self, "풀 위치 고르기", os.path.dirname(self.archive))
            if not d:
                return
            dest = os.path.join(d, A.archive_stem(self.archive)) if not selected else d
        self.extract(self.archive, dest, names)

    def extract(self, path, dest, names=None):
        pw = self.password if path == self.archive else None
        if pw is None:
            try:
                if A.is_encrypted(path):
                    pw = self._ask_password()
                    if pw is None:
                        return
            except A.ArchiveError as e:
                return QMessageBox.warning(self, brand.APP_NAME, str(e))

        def done(count):
            self.job_done("압축 풀기 완료", f"{count}개 파일을 풀었습니다.\n{dest}", os.path.join(dest, "."))

        self.run_task("압축 풀기", A.extract, path, dest, names, pw, on_done=done)

    def choose_and_extract(self):
        p, _ = QFileDialog.getOpenFileName(self, "풀 압축 파일 고르기", self._start(), A.FILTER)
        if p:
            self._remember(p)
            self.extract(p, A.default_extract_dir(p))


def selftest():
    """설치파일이 제대로 만들어졌는지 점검 (GitHub 자동 빌드에서 사용): 성공하면 0"""
    import tempfile
    d = tempfile.mkdtemp()
    src = os.path.join(d, "한글폴더")
    os.makedirs(src)
    with open(os.path.join(src, "문서.txt"), "w", encoding="utf-8") as f:
        f.write("모찌" * 100)
    noop = lambda *_: None  # noqa: E731
    for fmt in ("zip", "7z"):
        out = A.create(noop, [src], os.path.join(d, f"t.{fmt}"), fmt, "normal", "1234")
        assert A.extract(noop, out, os.path.join(d, fmt), None, "1234") >= 1
    app = QApplication.instance() or QApplication(sys.argv)
    ZipWindow()
    return 0


def main():
    if "--selftest" in sys.argv:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        return selftest()
    winapi.set_app_id(brand.APP_ID)
    app = QApplication(sys.argv)
    app.setApplicationName(brand.APP_NAME)
    app.setStyleSheet(stylesheet())
    win = ZipWindow()
    win.show()
    args = sys.argv[1:]
    if args[:1] == ["--extract-here"] and len(args) > 1:
        QTimer.singleShot(300, lambda: win.extract(args[1], A.default_extract_dir(args[1])))
    elif args[:1] == ["--compress"] and len(args) > 1:
        def go():
            win.show_page("compress")
            win.src_list.add_paths(args[1:])
            win.compress_now(ask=False)
        QTimer.singleShot(300, go)
    elif args and os.path.isfile(args[0]):
        QTimer.singleShot(200, lambda: win.open_archive(args[0]))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
