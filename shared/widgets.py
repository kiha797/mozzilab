"""모찌랩 프로그램들이 함께 쓰는 화면 부품 (끌어다 놓는 파일 목록, 파일 고르기, 도구 카드 등)"""
import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton, QToolButton, QVBoxLayout, QWidget)

from ui import ACCENT, icon, mochi_pixmap, px


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def title_label(text, sub=""):
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, px(6))
    v.setSpacing(px(2))
    t = QLabel(text)
    t.setStyleSheet("font-size: 17pt; font-weight: bold; color: #3b2f2f;")
    v.addWidget(t)
    if sub:
        s = QLabel(sub)
        s.setWordWrap(True)
        s.setStyleSheet("color: #8a7c7e; font-size: 10.5pt;")
        v.addWidget(s)
    return w


def primary_button(text):
    b = QPushButton(text)
    b.setCursor(Qt.PointingHandCursor)
    b.setMinimumHeight(px(44))
    b.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: white; border: none; border-radius: {px(10)}px;"
                    f" font-size: 12pt; font-weight: bold; padding: 0 {px(28)}px; }}"
                    "QPushButton:hover { background: #e8557a; } QPushButton:disabled { background: #f3b9c8; }")
    return b


def card():
    f = QFrame()
    f.setObjectName("card")
    f.setStyleSheet(f"QFrame#card {{ background: white; border: 1px solid #efe6e3; border-radius: {px(14)}px; }}")
    return f


class DropFileList(QListWidget):
    """파일을 끌어다 놓거나 [추가]로 넣고, 끌어서 순서를 바꿀 수 있는 목록"""
    changed = Signal()

    def __init__(self, exts, hint="파일을 여기에 끌어다 놓으세요", info=None, keep_dirs=False):
        super().__init__()
        self.exts = tuple(e.lower() for e in exts)      # () 이면 모든 파일
        self.keep_dirs = keep_dirs                       # True 면 폴더를 통째로 한 줄로 넣음
        self.hint = hint
        self.info = info                       # 파일 경로 -> 오른쪽에 보일 설명 글자
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setIconSize(QSize(px(22), px(22)))
        self.setStyleSheet(f"QListWidget {{ background: white; border: 2px dashed #f3c6d3; border-radius: {px(12)}px;"
                           f" padding: {px(6)}px; font-size: 10.5pt; }}"
                           f"QListWidget::item {{ padding: {px(6)}px; border-radius: {px(6)}px; }}"
                           "QListWidget::item:selected { background: #ffe3eb; color: #3b2f2f; }")
        self.model().rowsMoved.connect(lambda *_: self.changed.emit())

    def paths(self):
        return [self.item(i).data(Qt.UserRole) for i in range(self.count())]

    def add_paths(self, paths):
        have = set(self.paths())
        for p in paths:
            if os.path.isdir(p) and not self.keep_dirs:
                for root, _, files in os.walk(p):
                    self.add_paths(sorted(os.path.join(root, f) for f in files))
                continue
            if p in have or (self.exts and not os.path.isdir(p) and not p.lower().endswith(self.exts)):
                continue
            if os.path.isdir(p):
                n = sum(len(fs) for _, _, fs in os.walk(p))
                it = QListWidgetItem(icon("folder"), f"{os.path.basename(p.rstrip(os.sep)) or p}    ·  폴더 (파일 {n}개)")
            else:
                extra = self.info(p) if self.info else human_size(os.path.getsize(p))
                it = QListWidgetItem(icon("file"), f"{os.path.basename(p)}    ·  {extra}")
            it.setData(Qt.UserRole, p)
            it.setToolTip(p)
            self.addItem(it)
            have.add(p)
        self.changed.emit()

    def remove_selected(self):
        for it in self.selectedItems():
            self.takeItem(self.row(it))
        self.changed.emit()

    def move_selected(self, step):
        rows = sorted(self.row(i) for i in self.selectedItems())
        if not rows:
            return
        if step < 0 and rows[0] == 0 or step > 0 and rows[-1] == self.count() - 1:
            return
        for r in (rows if step < 0 else reversed(rows)):
            it = self.takeItem(r)
            self.insertItem(r + step, it)
            it.setSelected(True)
        self.changed.emit()

    def sort_by_name(self):
        ps = sorted(self.paths(), key=lambda p: os.path.basename(p).lower())
        self.clear()
        self.add_paths(ps)

    # 끌어다 놓기
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self.add_paths([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])
            e.acceptProposedAction()
        else:
            super().dropEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.count() == 0:
            p = QPainter(self.viewport())
            m = mochi_pixmap(px(90))
            r = self.viewport().rect()
            p.setOpacity(0.55)
            p.drawPixmap(r.center().x() - m.width() // 2, r.center().y() - m.height() - px(6), m)
            p.setOpacity(1)
            p.setPen(QColor("#a3979a"))
            p.drawText(r.adjusted(0, m.height() // 2 + px(30), 0, 0), Qt.AlignHCenter | Qt.AlignTop, self.hint)
            p.end()


def list_buttons(lst, filter_text, start_dir_fn, remember_fn):
    """목록 옆 버튼 줄: 추가 · 삭제 · 위로 · 아래로 · 이름순 · 모두 지우기"""
    row = QHBoxLayout()
    add = QPushButton(" 파일 추가")
    add.setIcon(icon("add"))
    add.setCursor(Qt.PointingHandCursor)

    def do_add():
        files, _ = QFileDialog.getOpenFileNames(lst, "파일 추가", start_dir_fn(), filter_text)
        if files:
            remember_fn(files[0])
            lst.add_paths(files)

    add.clicked.connect(do_add)
    row.addWidget(add)
    for text, ic, fn in (("삭제", "trash", lst.remove_selected), ("위로", "up", lambda: lst.move_selected(-1)),
                         ("아래로", "down", lambda: lst.move_selected(1)), ("이름순", "sort", lst.sort_by_name)):
        b = QPushButton(" " + text)
        b.setIcon(icon(ic))
        b.clicked.connect(fn)
        row.addWidget(b)
    row.addStretch(1)
    clear = QPushButton("모두 지우기")
    clear.clicked.connect(lambda: (lst.clear(), lst.changed.emit()))
    row.addWidget(clear)
    return row


class FilePicker(QWidget):
    """파일 하나 고르기 (입력칸 + [찾기] + 끌어다 놓기)"""
    picked = Signal(str)

    def __init__(self, exts, filter_text, start_dir_fn, remember_fn, placeholder="파일을 고르거나 끌어다 놓으세요"):
        super().__init__()
        self.exts = tuple(e.lower() for e in exts)
        self.filter_text = filter_text
        self.start_dir_fn = start_dir_fn
        self.remember_fn = remember_fn
        self.setAcceptDrops(True)
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setReadOnly(True)
        self.edit.setMinimumHeight(px(36))
        btn = QPushButton("찾기…")
        btn.setMinimumHeight(px(36))
        btn.clicked.connect(self.browse)
        h.addWidget(self.edit, 1)
        h.addWidget(btn)

    def path(self):
        return self.edit.text()

    def set_path(self, p):
        self.edit.setText(p)
        self.remember_fn(p)
        self.picked.emit(p)

    def browse(self):
        p, _ = QFileDialog.getOpenFileName(self, "파일 고르기", self.start_dir_fn(), self.filter_text)
        if p:
            self.set_path(p)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            p = u.toLocalFile()
            if p.lower().endswith(self.exts):
                self.set_path(p)
                break


class FolderPicker(QWidget):
    def __init__(self, start_dir_fn, placeholder="저장할 폴더 (비우면 원본과 같은 폴더)"):
        super().__init__()
        self.start_dir_fn = start_dir_fn
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setMinimumHeight(px(36))
        btn = QPushButton("폴더…")
        btn.setMinimumHeight(px(36))
        btn.clicked.connect(self.browse)
        h.addWidget(self.edit, 1)
        h.addWidget(btn)

    def path(self):
        return self.edit.text().strip()

    def browse(self):
        d = QFileDialog.getExistingDirectory(self, "폴더 고르기", self.path() or self.start_dir_fn())
        if d:
            self.edit.setText(d)


class ToolCard(QToolButton):
    """첫 화면의 큰 도구 카드"""

    def __init__(self, title, desc, icon_name, color):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(px(230), px(150))
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIcon(icon(icon_name, color))
        self.setIconSize(QSize(px(40), px(40)))
        self.setText(f"{title}\n{desc}")
        self.setStyleSheet(f"QToolButton {{ background: white; border: 1px solid #efe6e3; border-radius: {px(16)}px;"
                           f" padding: {px(16)}px; font-size: 11pt; color: #3b2f2f; text-align: center; }}"
                           f"QToolButton:hover {{ border: 2px solid {color}; background: #fffafb; }}")
