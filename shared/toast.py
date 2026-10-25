"""화면 오른쪽 아래에 잠깐 떴다 사라지는 안내창 (저장 완료 알림 등)"""
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

import winapi
from ui import px

_alive = []


class Toast(QWidget):
    def __init__(self, title, message, path=None, msec=4000):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setObjectName("toast")
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet("QWidget#toast { background: white; border: 1px solid #c9d3e3; border-radius: 6px; }"
                           "QLabel#toastTitle { font-weight: bold; color: #ff6f91; }")
        v = QVBoxLayout(self)
        v.setContentsMargins(px(16), px(12), px(16), px(12))
        t = QLabel(title)
        t.setObjectName("toastTitle")
        m = QLabel(message)
        m.setWordWrap(True)
        m.setMaximumWidth(px(340))
        v.addWidget(t)
        v.addWidget(m)
        if path:
            row = QHBoxLayout()
            row.addStretch(1)
            open_btn = QPushButton("폴더 열기")
            open_btn.clicked.connect(lambda: (winapi.open_folder(os.path.dirname(path)), self.close()))
            close_btn = QPushButton("닫기")
            close_btn.clicked.connect(self.close)
            row.addWidget(open_btn)
            row.addWidget(close_btn)
            v.addLayout(row)
        self.adjustSize()
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - px(16), area.bottom() - self.height() - px(16))
        QTimer.singleShot(msec, self.close)

    def closeEvent(self, e):
        if self in _alive:
            _alive.remove(self)
        super().closeEvent(e)


def show_toast(title, message, path=None, msec=4000):
    t = Toast(title, message, path, msec)
    _alive.append(t)
    t.show()
    return t
