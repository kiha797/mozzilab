"""알캡처 '실행창'과 같은 캡처 도구 막대"""
from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMenu, QToolButton, QWidget

import capture
from config import APP_NAME
from ui import app_icon, icon, px

MODES = [
    ("region", "직접지정", "region"),
    ("window", "창", "window"),
    ("unit", "단위영역", "unit"),
    ("full", "전체화면", "full"),
    ("scroll", "스크롤", "scroll"),
    ("fixed", "크기지정", "fixed"),
]


class Launcher(QWidget):
    def __init__(self, controller):
        super().__init__(None, Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowTitleHint |
                         Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint)
        self.ctrl = controller
        self.setObjectName("launcher")
        self.setAttribute(Qt.WA_StyledBackground)
        self.setWindowTitle(f"{APP_NAME} 실행창")
        self.setWindowIcon(app_icon())
        self.buttons = {}

        h = QHBoxLayout(self)
        h.setContentsMargins(px(4), px(4), px(4), px(4))
        h.setSpacing(0)
        h.addWidget(self._button("취소", "cancel", self.hide, "실행창 닫기 (ESC)"))
        h.addWidget(self._sep())
        for mode, text, ic in MODES:
            b = self._button(text, ic, lambda _=False, m=mode: self.ctrl.start_capture(m))
            b.setCheckable(True)
            self.buttons[mode] = b
            h.addWidget(b)
        h.addWidget(self._sep())
        h.addWidget(self._button("캡처목록", "list", self.ctrl.show_editor, "최근 캡처 목록 / 결과창 열기"))

        menu_btn = self._button("메뉴", "menu", None, "설정")
        menu_btn.setPopupMode(QToolButton.InstantPopup)
        self.menu = QMenu(self)
        self.act_show = self.menu.addAction("캡처 실행창 보기")
        self.act_show.setCheckable(True)
        self.act_show.toggled.connect(self._toggle_show)
        self.menu.addSeparator()
        self.act_copy = self.menu.addAction("자동 복사")
        self.act_copy.setCheckable(True)
        self.act_copy.toggled.connect(lambda v: self._set("auto_copy", v))
        self.act_save = self.menu.addAction("자동 저장")
        self.act_save.setCheckable(True)
        self.act_save.toggled.connect(lambda v: self._set("auto_save", v))
        self.menu.addSeparator()
        self.act_account = self.menu.addAction("로그인")
        self.act_account.triggered.connect(self._account_action)
        self.act_noads = self.menu.addAction("광고 없이 쓰기 (모찌 플러스)")
        self.act_noads.triggered.connect(lambda: self.ctrl.account.open_pricing())
        self.menu.addSeparator()
        self.menu.addAction(icon("settings"), "환경설정", self.ctrl.show_settings)
        self.menu.addAction(icon("help"), "도움말", self.ctrl.show_help)
        self.menu.addAction(icon("reset"), "업데이트 확인", lambda: (self.hide(), self.ctrl.updater.check(manual=True)))
        self.menu.aboutToShow.connect(self.sync_menu)
        menu_btn.setMenu(self.menu)
        menu_btn.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0; }")
        h.addWidget(menu_btn)
        self.setFixedSize(self.sizeHint())
        self.update_tooltips()

    def _button(self, text, icon_name, slot, tip=""):
        b = QToolButton()
        b.setProperty("role", "launch")           # 알캡처처럼 작고 촘촘한 버튼
        b.setText(text)
        b.setIcon(icon(icon_name))
        b.setIconSize(QSize(px(28), px(28)))
        b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tip)
        if slot:
            b.clicked.connect(slot)
        return b

    @staticmethod
    def _sep():
        s = QFrame()
        s.setObjectName("vsep")
        s.setFixedHeight(px(56))
        return s

    # ---------- 메뉴 ----------
    def sync_menu(self):
        cfg = self.ctrl.cfg
        for act, value in ((self.act_show, not cfg.get("hide_launcher")),
                           (self.act_copy, cfg.get("auto_copy")),
                           (self.act_save, cfg.get("auto_save"))):
            act.blockSignals(True)
            act.setChecked(bool(value))
            act.blockSignals(False)
        acc = self.ctrl.account
        self.act_account.setText(f"로그아웃 ({acc.name})" if acc.logged_in else "로그인")
        self.act_noads.setVisible(not acc.premium)

    def _account_action(self):
        if self.ctrl.account.logged_in:
            self.ctrl.logout()
        else:
            self.ctrl.login()

    def _set(self, key, value):
        self.ctrl.cfg[key] = value
        self.ctrl.cfg.save()

    def _toggle_show(self, show):
        self._set("hide_launcher", not show)
        if not show:
            self.ctrl.tray.showMessage(APP_NAME, "실행창을 숨겼습니다. 트레이 아이콘을 클릭하면 캡처 메뉴가 나옵니다.",
                                       app_icon(), 4000)
            self.hide()

    def update_tooltips(self):
        from settings_dialog import hotkey_label
        hks = self.ctrl.cfg.get("hotkeys", {})
        for i, (mode, text, _) in enumerate(MODES, start=1):
            hk = hks.get(mode, {})
            key = hotkey_label(hk) if hk.get("on") else "단축키 없음"
            self.buttons[mode].setToolTip(f"{text} 캡처  (숫자키 {i} · {key})")

    # ---------- 표시 ----------
    def show_at(self):
        last = self.ctrl.cfg.get("last_mode")
        for m, b in self.buttons.items():
            b.setChecked(m == last)
        pos = self.ctrl.cfg.get("launcher_pos")
        if pos and capture.virtual_geometry().contains(QPoint(pos[0] + 20, pos[1] + 20)):
            self.move(pos[0], pos[1])
        else:
            sr = capture.screen_at_cursor().availableGeometry()
            self.move(sr.center().x() - self.width() // 2, sr.top() + px(60))
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def hideEvent(self, e):
        p = self.pos()
        self.ctrl.cfg["launcher_pos"] = [p.x(), p.y()]
        self.ctrl.cfg.save()
        super().hideEvent(e)

    def closeEvent(self, e):
        e.ignore()
        if self.ctrl.cfg.get("close_to_tray", True):
            self.hide()            # X 를 눌러도 프로그램은 트레이에 남아 있다
        else:
            self.ctrl.quit()       # '종료버튼 클릭 시 트레이로 최소화'를 끈 경우 완전히 종료

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Escape:
            self.hide()
        elif Qt.Key_1 <= k <= Qt.Key_6:
            self.ctrl.start_capture(MODES[k - Qt.Key_1][0])
        else:
            super().keyPressEvent(e)
