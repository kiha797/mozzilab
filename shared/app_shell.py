"""모찌랩 프로그램 공통 창 틀 (모찌PDF, 모찌압축 …)
- 위: 큰 도구 버튼 · 오른쪽 위 광고 + [로그인]
- 가운데: 각 프로그램 화면
- 아래: 진행 막대, 작업 완료 후 팝업 광고(무료 사용자)"""
import traceback

from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMainWindow, QMenu, QMessageBox,
                               QProgressBar, QPushButton, QStackedWidget, QToolButton, QVBoxLayout,
                               QWidget)

from account import Account, Api
from ads import AdBlock, AdManager, PopupAd
from appconfig import AppConfig
from toast import show_toast
from ui import ACCENT, app_icon, icon, px, stylesheet

import brand


class Cancelled(Exception):
    pass


class Worker(QThread):
    """오래 걸리는 작업을 화면이 멈추지 않게 따로 실행"""
    progress = Signal(int, str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self.fn = fn
        self.args = args
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def report(self, pct, msg=""):
        if self._cancel:
            raise Cancelled()
        self.progress.emit(int(pct), msg)

    def run(self):
        try:
            self.done.emit(self.fn(self.report, *self.args))
        except Cancelled:
            self.failed.emit("작업을 취소했습니다.")
        except Exception as e:          # noqa: BLE001 - 사용자에게 원인을 보여준다
            traceback.print_exc()
            self.failed.emit(str(e) or e.__class__.__name__)


class MozziWindow(QMainWindow):
    def __init__(self, defaults=None):
        super().__init__()
        self.cfg = AppConfig(brand.APP_ID, defaults)
        self.api = Api()
        self.account = Account(self.cfg, self.api)
        self.ads = AdManager(self.cfg, self.api, self.account)
        self.worker = None
        self.setWindowTitle(brand.APP_NAME)
        self.setWindowIcon(app_icon())
        self.setStyleSheet(stylesheet())

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        bar = QWidget()
        bar.setObjectName("toolbar")
        bar.setAttribute(Qt.WA_StyledBackground)
        self.tool_row = QHBoxLayout(bar)
        self.tool_row.setContentsMargins(px(8), px(6), px(8), px(6))
        self.tool_row.setSpacing(px(2))
        root.addWidget(bar)
        self._tool_insert = 0

        self.tool_row.addStretch(1)
        self.ad_block = AdBlock(self.ads)
        self.tool_row.addWidget(self.ad_block)
        self.tool_row.addSpacing(px(10))
        acc = QVBoxLayout()
        acc.setSpacing(px(4))
        self.account_btn = QToolButton()
        self.account_btn.setObjectName("accountBtn")
        self.account_btn.setCursor(Qt.PointingHandCursor)
        self.account_btn.setPopupMode(QToolButton.InstantPopup)
        self.account_btn.setStyleSheet(
            f"QToolButton#accountBtn {{ border: 1.5px solid {ACCENT}; color: {ACCENT}; border-radius: {px(6)}px;"
            f" padding: {px(5)}px {px(14)}px; font-weight: bold; background: white; }}"
            "QToolButton#accountBtn:hover { background: #fff0f4; }"
            "QToolButton#accountBtn::menu-indicator { image: none; width: 0; }")
        self.account_btn.clicked.connect(self._account_clicked)
        self.plan_label = QLabel("")
        self.plan_label.setAlignment(Qt.AlignCenter)
        self.plan_label.setStyleSheet(f"color:{ACCENT}; font-size:8.5pt;")
        acc.addWidget(self.account_btn)
        acc.addWidget(self.plan_label)
        acc.addStretch(1)
        self.tool_row.addLayout(acc)

        self.body = QStackedWidget()
        self.body.setObjectName("body")
        self.body.setStyleSheet("QStackedWidget#body { background: #fbf8f6; }")
        root.addWidget(self.body, 1)
        self.popup_ad = PopupAd(self.ads, self.body)
        self.body.currentChanged.connect(lambda _: self.popup_ad.isVisible() and self.popup_ad.raise_())
        self.setCentralWidget(central)

        sb = self.statusBar()
        self.progress = QProgressBar()
        self.progress.setFixedWidth(px(260))
        self.progress.setTextVisible(True)
        self.progress.hide()
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(lambda: self.worker and self.worker.cancel())
        sb.addPermanentWidget(self.progress)
        sb.addPermanentWidget(self.cancel_btn)

        self.account.changed.connect(self._account_changed)
        self.ads.changed.connect(self.refresh_ads)
        self.update_account()
        self.account.refresh()
        self.ads.fetch()
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(lambda: (self.account.refresh(), self.ads.fetch()))
        self.sync_timer.start(3 * 60 * 60 * 1000)

        g = self.cfg.get("geometry")
        if g and len(g) == 4:
            self.setGeometry(*g)
        else:
            self.resize(px(1180), px(780))

    # ---------- 도구 버튼 ----------
    def add_tool(self, text, icon_name, slot=None, checkable=False, tip=""):
        b = QToolButton()
        b.setProperty("role", "big")
        b.setText(text)
        b.setIcon(icon(icon_name))
        b.setIconSize(QSize(px(30), px(30)))
        b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        b.setCheckable(checkable)
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(tip)
        if slot:
            b.clicked.connect(slot)
        self.tool_row.insertWidget(self._tool_insert, b)
        self._tool_insert += 1
        return b

    def add_separator(self):
        s = QFrame()
        s.setObjectName("vsep")
        s.setFixedHeight(px(60))
        self.tool_row.insertWidget(self._tool_insert, s)
        self._tool_insert += 1

    # ---------- 계정 / 광고 ----------
    def _account_clicked(self):
        if not self.account.logged_in:
            self.login()

    def login(self):
        if self.account.login(self) and self.account.logged_in:
            msg = ("모찌 플러스 이용 중 — 광고 없이 쓸 수 있어요! ⭐" if self.account.premium
                   else "무료 회원으로 로그인했어요. 광고를 없애려면 모찌 플러스를 구독하세요.")
            show_toast("로그인 완료", f"{self.account.name} 님, {msg}", msec=5000)

    def logout(self):
        if QMessageBox.question(self, brand.APP_NAME, "로그아웃할까요?") == QMessageBox.Yes:
            self.account.logout()

    def _account_changed(self):
        self.ads.fetch()
        self.update_account()

    def update_account(self):
        a = self.account
        if a.logged_in:
            self.account_btn.setText(("⭐ " if a.premium else "") + f"{a.name or '회원'} 님 ▾")
            m = QMenu(self)
            if a.email:
                m.addAction(a.email).setEnabled(False)
            if a.premium and a.expires_at:
                m.addAction(f"광고 제거 이용 중 (~{a.expires_at:%Y-%m-%d})").setEnabled(False)
            m.addSeparator()
            m.addAction("마이페이지", a.open_mypage)
            if not a.premium:
                m.addAction("광고 없이 쓰기 (구독)", a.open_pricing)
            m.addAction("구독 상태 새로고침", lambda: a.refresh())
            m.addSeparator()
            m.addAction("로그아웃", self.logout)
            self.account_btn.setMenu(m)
            self.plan_label.setText("광고 없이 이용 중" if a.premium else "무료 이용 중")
        else:
            self.account_btn.setText("로그인")
            self.account_btn.setMenu(None)
            self.plan_label.setText("")
        self.refresh_ads()

    def refresh_ads(self):
        show = self.ads.show_ads
        self.ad_block.setVisible(show)
        if show and self.ad_block.card.ad is None:
            self.ad_block.rotate()
        if not show:
            self.popup_ad.hide()

    # ---------- 작업 실행 ----------
    def run_task(self, title, fn, *args, on_done=None):
        """fn(report, *args) 를 따로 실행. report(퍼센트, 메시지)로 진행 상황을 알린다."""
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, brand.APP_NAME, "다른 작업이 진행 중입니다. 끝난 뒤 다시 시도해 주세요.")
            return
        self.worker = Worker(fn, *args)
        self.progress.setValue(0)
        self.progress.setFormat(f"{title} %p%")
        self.progress.show()
        self.cancel_btn.show()
        self.statusBar().showMessage(f"{title} 중…")

        def prog(p, msg):
            self.progress.setValue(p)
            if msg:
                self.statusBar().showMessage(msg)

        def finish():
            self.progress.hide()
            self.cancel_btn.hide()

        def ok(result):
            finish()
            self.statusBar().showMessage(f"{title} 완료", 5000)
            if on_done:
                on_done(result)

        def bad(msg):
            finish()
            self.statusBar().clearMessage()
            QMessageBox.warning(self, brand.APP_NAME, f"{title}에 실패했습니다.\n\n{msg}")

        self.worker.progress.connect(prog)
        self.worker.done.connect(ok)
        self.worker.failed.connect(bad)
        self.worker.start()

    def job_done(self, title, message, path=None):
        """작업 완료 알림 + (무료 사용자) 팝업 광고"""
        show_toast(title, message, path, msec=5000)
        if self.ads.show_ads:
            self.ad_block.rotate()
            if self.ads.should_popup():
                self.popup_ad.show_ad()

    def closeEvent(self, e):
        if self.worker and self.worker.isRunning():
            if QMessageBox.question(self, brand.APP_NAME, "작업이 진행 중입니다. 그래도 종료할까요?") != QMessageBox.Yes:
                e.ignore()
                return
            self.worker.cancel()
            self.worker.wait(3000)
        g = self.geometry()
        self.cfg["geometry"] = [g.x(), g.y(), g.width(), g.height()]
        self.cfg.save()
        super().closeEvent(e)
