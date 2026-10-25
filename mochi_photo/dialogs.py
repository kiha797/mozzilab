"""모찌포토 대화상자: 색 보정(미리보기), 이미지 크기, 캔버스 크기, 문자 입력, 레이어 변형"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QDoubleSpinBox, QFontComboBox, QFormLayout, QGridLayout,
                               QHBoxLayout, QLabel, QPlainTextEdit, QRadioButton, QSpinBox, QVBoxLayout)

import photo_core as C
from editor_kit import ColorButton, SliderSpin
from ui import px


def buttons(dlg, ok="확인"):
    bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    bb.button(QDialogButtonBox.Ok).setText(ok)
    bb.button(QDialogButtonBox.Cancel).setText("취소")
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    return bb


class AdjustDialog(QDialog):
    """슬라이더를 움직이면 캔버스에 바로 미리보기되는 보정 창
    specs = [(이름표, 키, 최소, 최대, 기본값), ...]"""

    def __init__(self, ed, title, fn, specs):
        super().__init__(ed)
        self.setWindowTitle(title)
        self.ed, self.fn, self.specs = ed, fn, specs
        doc = ed.doc
        self.layer = doc.layer
        self.base = QImage(self.layer.image)
        self.sel = QPainterPathOrNone(doc)
        v = QVBoxLayout(self)
        f = QFormLayout()
        self.sliders = {}
        for label, key, lo, hi, val in specs:
            s = SliderSpin("", lo, hi, val, slider_width=220)
            s.valueChanged.connect(self.schedule)
            self.sliders[key] = s
            f.addRow(label, s)
        v.addLayout(f)
        self.preview = QCheckBox("미리 보기")
        self.preview.setChecked(True)
        self.preview.toggled.connect(self.schedule)
        v.addWidget(self.preview)
        v.addWidget(buttons(self))
        self.timer = QTimer(self, singleShot=True, interval=90)
        self.timer.timeout.connect(self.apply_preview)
        self.schedule()

    def values(self):
        return {k: s.value() for k, s in self.sliders.items()}

    def schedule(self, *_):
        self.timer.start()

    def apply_preview(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.preview.isChecked():
                self.layer.image = C.apply_pil(self.base, self.fn, self.sel, **self.values())
            else:
                self.layer.image = QImage(self.base)
        finally:
            QApplication.restoreOverrideCursor()
        self.ed.doc.composite()
        self.ed.canvas.update()

    def accept(self):
        self.timer.stop()
        self.preview.setChecked(True)
        self.apply_preview()
        super().accept()

    def reject(self):
        self.timer.stop()
        self.layer.image = self.base
        self.ed.doc.composite()
        self.ed.canvas.update()
        super().reject()


def QPainterPathOrNone(doc):
    return doc.selection if doc.has_selection() else None


class ImageSizeDialog(QDialog):
    def __init__(self, parent, w, h, title="이미지 크기"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.ratio = w / h
        f = QFormLayout(self)
        self.w = QSpinBox()
        self.h = QSpinBox()
        for s, val in ((self.w, w), (self.h, h)):
            s.setRange(1, 30000)
            s.setValue(val)
            s.setSuffix(" px")
        self.pct = QSpinBox()
        self.pct.setRange(1, 1000)
        self.pct.setValue(100)
        self.pct.setSuffix(" %")
        self.keep = QCheckBox("가로세로 비율 유지")
        self.keep.setChecked(True)
        self.quality = QComboBox()
        self.quality.addItems(["부드럽게 (사진)", "픽셀 그대로 (도트·아이콘)"])
        self.orig = (w, h)
        self.w.valueChanged.connect(self._w)
        self.h.valueChanged.connect(self._h)
        self.pct.valueChanged.connect(self._pct)
        f.addRow("비율", self.pct)
        f.addRow("가로", self.w)
        f.addRow("세로", self.h)
        f.addRow("", self.keep)
        f.addRow("방식", self.quality)
        f.addRow(buttons(self))
        self._busy = False

    def _w(self, v):
        if self.keep.isChecked() and not self._busy:
            self._busy = True
            self.h.setValue(max(1, round(v / self.ratio)))
            self._busy = False

    def _h(self, v):
        if self.keep.isChecked() and not self._busy:
            self._busy = True
            self.w.setValue(max(1, round(v * self.ratio)))
            self._busy = False

    def _pct(self, v):
        if not self._busy:
            self._busy = True
            self.w.setValue(max(1, round(self.orig[0] * v / 100)))
            self.h.setValue(max(1, round(self.orig[1] * v / 100)))
            self._busy = False

    def values(self):
        return self.w.value(), self.h.value(), self.quality.currentIndex() == 0


class CanvasSizeDialog(QDialog):
    def __init__(self, parent, w, h):
        super().__init__(parent)
        self.setWindowTitle("캔버스 크기")
        f = QFormLayout(self)
        self.w = QSpinBox()
        self.h = QSpinBox()
        for s, val in ((self.w, w), (self.h, h)):
            s.setRange(1, 30000)
            s.setValue(val)
            s.setSuffix(" px")
        f.addRow("가로", self.w)
        f.addRow("세로", self.h)
        grid = QGridLayout()
        grid.setSpacing(px(2))
        self.group = QButtonGroup(self)
        for i in range(9):
            b = QRadioButton()
            b.setToolTip("기존 그림을 이 위치에 둡니다")
            self.group.addButton(b, i)
            grid.addWidget(b, i // 3, i % 3)
        self.group.button(4).setChecked(True)
        f.addRow("기준 위치", grid)
        self.fill = QComboBox()
        self.fill.addItems(["흰색", "투명", "검정"])
        f.addRow("늘어난 곳 채우기", self.fill)
        f.addRow(buttons(self))

    def values(self):
        i = self.group.checkedId()
        anchor = ((i % 3) / 2, (i // 3) / 2)
        fill = {0: QColor("white"), 1: None, 2: QColor("black")}[self.fill.currentIndex()]
        return self.w.value(), self.h.value(), anchor, fill


class TextDialog(QDialog):
    def __init__(self, parent, font_family, size, color):
        super().__init__(parent)
        self.setWindowTitle("문자 입력")
        v = QVBoxLayout(self)
        row = QHBoxLayout()
        self.font = QFontComboBox()
        self.font.setCurrentFont(QFont(font_family))
        self.size = QSpinBox()
        self.size.setRange(4, 2000)
        self.size.setValue(size)
        self.size.setSuffix(" px")
        self.bold = QCheckBox("굵게")
        self.italic = QCheckBox("기울임")
        self.color = ColorButton(color, tip="글자 색")
        self.align = QComboBox()
        self.align.addItems(["왼쪽", "가운데", "오른쪽"])
        for w in (self.font, self.size, self.bold, self.italic, self.align, QLabel("색"), self.color):
            row.addWidget(w)
        v.addLayout(row)
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("여기에 글자를 입력하세요 (여러 줄 가능)")
        self.text.setMinimumSize(px(460), px(160))
        v.addWidget(self.text)
        v.addWidget(buttons(self, "넣기"))

    def values(self):
        f = QFont(self.font.currentFont())
        f.setPixelSize(self.size.value())
        f.setBold(self.bold.isChecked())
        f.setItalic(self.italic.isChecked())
        align = [Qt.AlignLeft, Qt.AlignHCenter, Qt.AlignRight][self.align.currentIndex()]
        return self.text.toPlainText(), f, self.color.color() or QColor("black"), align


class TransformDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("레이어 변형 (크기 · 회전)")
        f = QFormLayout(self)
        self.sx = QDoubleSpinBox()
        self.sy = QDoubleSpinBox()
        for s in (self.sx, self.sy):
            s.setRange(1, 2000)
            s.setValue(100)
            s.setSuffix(" %")
        self.keep = QCheckBox("비율 유지")
        self.keep.setChecked(True)
        self.sx.valueChanged.connect(lambda v: self.keep.isChecked() and self.sy.setValue(v))
        self.angle = QDoubleSpinBox()
        self.angle.setRange(-360, 360)
        self.angle.setSuffix(" °")
        f.addRow("가로 크기", self.sx)
        f.addRow("세로 크기", self.sy)
        f.addRow("", self.keep)
        f.addRow("회전", self.angle)
        f.addRow(QLabel("레이어의 가운데를 기준으로 바뀝니다."))
        f.addRow(buttons(self))

    def values(self):
        return self.sx.value() / 100, self.sy.value() / 100, self.angle.value()
