"""모찌캡처 - 프로그램 시작 파일.
트레이(작업표시줄 오른쪽 아래)에 아이콘을 띄우고, 아이콘을 누르면 실행창이 열린다."""
import os
import sys

# 화면 배율(125%, 150%)에서도 캡처 좌표가 정확하도록 실제 픽셀 기준으로 동작
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, QTimer
from PySide6.QtGui import QCursor, QImage
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

import capture
import winapi
from account import Account, Api
from ads import AdManager
from brand import APP_VERSION, BRAND_NAME, SERVER_URL
from config import APP_ID, APP_NAME, HOTKEY_MODES, Config, History
from editor import ResultWindow, save_image_dialog, save_with_format
from fixed_frame import FixedFrame
from launcher import Launcher
from overlay import CaptureOverlay
from scroll_capture import ScrollCapture
from settings_dialog import SettingsDialog, hotkey_label, key_to_vk
from toast import show_toast
from ui import app_icon, icon, stylesheet

VK_PRINT = 0x2C
HK_PRINTSCREEN = 1
HK_MODE_IDS = {mode: i for i, mode in enumerate(HOTKEY_MODES, start=2)}
MODE_TITLES = {"launcher": "실행창 열기", "region": "직접지정", "window": "창", "unit": "단위영역",
               "full": "전체화면", "scroll": "스크롤", "fixed": "크기지정"}
HELP_TAIL = """
[실행창]  숫자키 1~6 : 각 캡처 / ESC : 닫기
[영역 선택 중]  드래그 : 영역 지정 · 클릭 : 창 선택 · ESC/우클릭 : 취소
[크기지정]  틀 안쪽 드래그 : 이동 · 테두리 드래그 : 크기 조절 · 방향키 : 1px 이동 · Enter : 캡처
[결과창]  Ctrl+S 저장 · Ctrl+C 복사 · Ctrl+Z 이전 · Ctrl+Y 다시
          Ctrl+휠 확대/축소 · Ctrl+0 원본크기"""


class HotkeyFilter(QAbstractNativeEventFilter):
    """Windows 가 보내는 '단축키 눌림(WM_HOTKEY)' 메시지를 받아서 처리"""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, event_type, message):
        if winapi.IS_WIN and bytes(event_type) == b"windows_generic_MSG":
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == winapi.WM_HOTKEY:
                QTimer.singleShot(0, lambda hk=int(msg.wParam): self.callback(hk))
                return True, 0
        return False, 0


class Controller(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.cfg = Config.load()
        self.history = History(self.cfg)
        self.editor = None
        self.busy = None              # 진행 중인 캡처 화면(오버레이/크기지정/스크롤)
        self._editor_was_visible = False
        # 로그인/라이선스와 광고
        self.api = Api()
        self.account = Account(self.cfg, self.api)
        self.ads = AdManager(self.cfg, self.api, self.account)
        self.account.changed.connect(self._account_changed)
        self.ads.changed.connect(lambda: self.editor and self.editor.refresh_ads())
        self.account.refresh()
        self.ads.fetch()
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(lambda: (self.account.refresh(), self.ads.fetch()))
        self.sync_timer.start(3 * 60 * 60 * 1000)      # 3시간마다 구독 상태·광고 새로 확인
        self.launcher = Launcher(self)
        self._setup_tray()
        self.hotkey_filter = HotkeyFilter(self._on_hotkey)
        app.installNativeEventFilter(self.hotkey_filter)
        self.registered = []
        failed = self.apply_hotkeys()
        if failed:
            self.tray.showMessage(APP_NAME, "등록하지 못한 단축키: " + ", ".join(failed), app_icon(), 5000)
        if self.cfg.get("autostart"):
            winapi.set_autostart(True)

    # ---------- 계정 ----------
    def _account_changed(self):
        self.ads.fetch()
        if self.editor:
            self.editor.update_account()

    def login(self, parent=None):
        self.launcher.hide()
        if self.account.login(parent) and self.account.logged_in:
            msg = ("모찌 플러스 이용 중 — 광고 없이 쓸 수 있어요! ⭐" if self.account.premium
                   else "무료 회원으로 로그인했어요. 광고를 없애려면 모찌 플러스를 구독하세요.")
            show_toast("로그인 완료", f"{self.account.name} 님, {msg}", msec=5000)

    def logout(self):
        if QMessageBox.question(None, APP_NAME, "로그아웃할까요?") == QMessageBox.Yes:
            self.account.logout()

    # ---------- 트레이 ----------
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(app_icon(), self.app)
        self.tray.setToolTip(f"{APP_NAME} - 클릭하면 캡처할 수 있습니다")
        menu = QMenu()
        menu.addAction(icon("menu"), "캡처 실행창 열기", self.launcher.show_at)
        menu.addSeparator()
        for mode in HOTKEY_MODES:
            menu.addAction(icon(mode), MODE_TITLES[mode], lambda m=mode: self.start_capture(m))
        menu.addSeparator()
        menu.addAction(icon("list"), "캡처목록", self.show_editor)
        menu.addAction(icon("settings"), "환경설정", self.show_settings)
        menu.addAction(icon("help"), "도움말", self.show_help)
        menu.addSeparator()
        self.tray_account = menu.addAction("로그인", self._tray_account)
        menu.aboutToShow.connect(self._sync_tray_menu)
        menu.addSeparator()
        menu.addAction(icon("exit"), "종료", self.quit)
        self.tray_menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
        if self.cfg.get("first_run", True):
            self.tray.showMessage(APP_NAME, "실행되었습니다. 작업표시줄 오른쪽 아래 아이콘을 클릭하면 캡처할 수 있어요.",
                                  app_icon(), 5000)
            self.cfg["first_run"] = False
            self.cfg.save()

    def _sync_tray_menu(self):
        a = self.account
        self.tray_account.setText(("⭐ " if a.premium else "") + f"{a.name} 님 (마이페이지)" if a.logged_in
                                  else "로그인 (광고 없이 쓰기)")

    def _tray_account(self):
        if self.account.logged_in:
            self.account.open_mypage()
        else:
            self.login()

    def _tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_launcher()

    # ---------- 단축키 ----------
    def apply_hotkeys(self):
        """환경설정의 단축키를 Windows 에 등록한다. 등록에 실패한 항목 이름 목록을 돌려준다."""
        for hk_id in self.registered:
            winapi.unregister_hotkey(hk_id)
        self.registered = []
        failed = []
        if not winapi.IS_WIN:
            return failed
        if self.cfg.get("printscreen_on", True):
            if winapi.register_hotkey(HK_PRINTSCREEN, 0, VK_PRINT):
                self.registered.append(HK_PRINTSCREEN)
            else:
                failed.append("PrintScreen")
        for mode, hk in self.cfg["hotkeys"].items():
            if not hk.get("on"):
                continue
            mods = ((winapi.MOD_WIN if hk.get("win") else 0) | (winapi.MOD_CONTROL if hk.get("ctrl") else 0) |
                    (winapi.MOD_SHIFT if hk.get("shift") else 0) | (winapi.MOD_ALT if hk.get("alt") else 0))
            hk_id = HK_MODE_IDS[mode]
            if winapi.register_hotkey(hk_id, mods, key_to_vk(hk.get("key", "A"))):
                self.registered.append(hk_id)
            else:
                failed.append(f"{MODE_TITLES[mode]} ({hotkey_label(hk)})")
        return failed

    def _on_hotkey(self, hk_id):
        if hk_id == HK_PRINTSCREEN:
            action = self.cfg.get("printscreen_action", "region")
            if action == "launcher":
                self.show_launcher()
            else:
                self.start_capture(action)
            return
        for mode, i in HK_MODE_IDS.items():
            if i == hk_id:
                self.start_capture(mode)

    def show_help(self):
        lines = []
        if self.cfg.get("printscreen_on", True):
            lines.append(f"PrintScreen : {MODE_TITLES.get(self.cfg.get('printscreen_action'), '')}")
        for mode in HOTKEY_MODES:
            hk = self.cfg["hotkeys"][mode]
            lines.append(f"{hotkey_label(hk) if hk.get('on') else '(사용 안 함)'} : {MODE_TITLES[mode]}")
        acc = self.account
        state = (f"{acc.name} 님 · " + ("⭐ 모찌 플러스 (광고 없음)" if acc.premium else "무료 회원")) \
            if acc.logged_in else "로그인 안 함 (무료)"
        QMessageBox.information(None, f"{APP_NAME} 도움말",
                                f"{APP_NAME} v{APP_VERSION}  ·  {BRAND_NAME}\n계정: {state}\n"
                                f"웹사이트: {SERVER_URL}\n\n"
                                "[단축키]\n" + "\n".join(lines) + "\n" + HELP_TAIL +
                                "\n\n설정 파일 위치: %APPDATA%\\MochiCapture")

    # ---------- 창 열기 ----------
    def show_launcher(self):
        if self.busy is not None:
            return
        if self.cfg.get("hide_launcher"):
            self.tray_menu.popup(QCursor.pos())     # 실행창 숨김 설정 -> 메뉴로 대체
        else:
            self.launcher.show_at()

    def ensure_editor(self):
        if self.editor is None:
            self.editor = ResultWindow(self)
        return self.editor

    def show_editor(self):
        self.launcher.hide()
        ed = self.ensure_editor()
        files = self.history.files()
        if files and ed.current_path is None:
            ed.show_capture(files[0])
        else:
            ed.panel.refresh(ed.current_path)
            ed.showNormal()
            ed.raise_()
            ed.activateWindow()

    def show_settings(self, page=0):
        parent = self.editor if self.editor and self.editor.isVisible() else None
        dlg = SettingsDialog(self.cfg, parent, page if isinstance(page, int) else 0)
        dlg.setWindowIcon(app_icon())
        if not dlg.exec():
            return
        winapi.set_autostart(self.cfg["autostart"])
        failed = self.apply_hotkeys()
        if failed:
            QMessageBox.warning(None, APP_NAME, "다음 단축키는 다른 프로그램이 사용 중이라 등록하지 못했습니다:\n\n"
                                + "\n".join(failed) + "\n\n다른 조합으로 바꿔 주세요.")
        if self.cfg.get("auto_prune"):
            self.history.prune()
        self.launcher.update_tooltips()
        if self.cfg.get("hide_launcher"):
            self.launcher.hide()
        if self.editor:
            self.editor.panel.refresh(self.editor.current_path)

    def open_save_folder(self):
        winapi.open_folder(self.cfg.save_dir())

    # ---------- 캡처 ----------
    def start_capture(self, mode):
        if self.busy is not None:
            return
        self.cfg["last_mode"] = mode
        self.cfg.save()
        self.launcher.hide()
        self._editor_was_visible = bool(self.editor and self.editor.isVisible())
        if self._editor_was_visible:
            self.editor.hide()               # 결과창이 캡처에 찍히지 않도록 숨김
        self.busy = "starting"
        QTimer.singleShot(250, lambda: self._begin(mode))

    def _begin(self, mode):
        cursor = bool(self.cfg.get("include_cursor"))
        if mode == "full":
            self.busy = None
            self.on_captured(capture.grab_screen_at_cursor(cursor), mode="full")
            return
        if mode == "fixed":
            frame = FixedFrame(self.cfg)
            frame.captured.connect(lambda img: self._finished(img, "fixed"))
            frame.closed.connect(self._cancelled)
            self.busy = frame
            frame.start()
            return
        shot, origin = capture.grab_virtual(cursor and mode != "scroll")
        if shot.isNull():
            self.busy = None
            return
        ov = CaptureOverlay(mode, shot, origin, winapi.list_windows(),
                            self.cfg.get("guide_color", "#ff0000"), self.cfg.get("show_overlay", True))
        ov.captured.connect(lambda img: self._finished(img, mode))
        ov.region_selected.connect(self._start_scroll)
        ov.cancelled.connect(self._cancelled)
        self.busy = ov
        ov.start()

    def _start_scroll(self, rect):
        sc = ScrollCapture(rect, self.cfg.get("scroll_delay", 450))
        sc.finished.connect(lambda img: self._finished(img, "scroll"))
        self.busy = sc
        QTimer.singleShot(100, sc.start)

    def _finished(self, img, mode=None):
        self.busy = None
        if img is None or img.isNull():
            self._cancelled()
            return
        self.on_captured(img, mode=mode)

    def _cancelled(self):
        self.busy = None
        if self._editor_was_visible and self.editor:
            self.editor.showNormal()
        self._editor_was_visible = False

    def _add_to_history(self, img):
        """최근 캡처 목록에 추가. 목록이 가득 찼고 자동 삭제가 꺼져 있으면 물어본다."""
        if self.history.is_full() and not self.cfg.get("auto_prune"):
            answer = QMessageBox.question(
                None, APP_NAME,
                f"최근 캡처 목록이 가득 찼습니다. ({self.history.limit}장)\n"
                "가장 오래된 이미지를 지우고 이번 캡처를 추가할까요?\n\n"
                "※ 환경설정 > 캡처목록 설정에서 '오래된 이미지 자동 삭제'를 켜면 더 이상 묻지 않습니다.")
            if answer != QMessageBox.Yes:
                return None
        return self.history.add(img)

    def on_captured(self, img: QImage, copy=True, mode=None):
        self._editor_was_visible = False
        if img.isNull():
            return
        cfg = self.cfg
        if mode and mode != "full" and cfg.get("keep_guide"):
            img = capture.draw_guide(img, cfg.get("guide_color", "#ff0000"))
        if copy and cfg.get("auto_copy", True):
            QApplication.clipboard().setImage(img)
        if cfg.get("auto_save", False):
            folder = cfg.save_dir()
            target = os.path.join(folder, cfg.new_file_name(cfg.get("save_format", "png"), folder))
            if save_with_format(cfg, img, target) and cfg.get("save_notice"):
                show_toast("자동 저장 완료", target, target)
        path = self._add_to_history(img)

        if not cfg.get("no_result_window") and path:
            ed = self.ensure_editor()
            ed.show_capture(path, new_capture=True)
            if cfg.get("save_dialog_after"):
                QTimer.singleShot(150, ed.save)
        elif cfg.get("save_dialog_after"):
            save_image_dialog(None, cfg, img)
        elif not cfg.get("auto_save"):
            msg = "클립보드에 복사되었습니다. Ctrl+V 로 붙여넣으세요." if copy and cfg.get("auto_copy", True) \
                else "캡처목록에 추가되었습니다."
            show_toast("캡처 완료", msg, msec=2000)

    def quit(self):
        if self.editor:
            self.editor.save_state()
            self.editor.hide()
        for hk_id in self.registered:
            winapi.unregister_hotkey(hk_id)
        self.tray.hide()
        self.cfg.save()
        self.app.quit()


def main():
    winapi.set_app_id(APP_ID)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())
    app.setStyleSheet(stylesheet())

    # 이미 실행 중이면 기존 프로그램의 실행창만 띄우고 끝낸다 (중복 실행 방지)
    sock = QLocalSocket()
    sock.connectToServer(APP_ID)
    if sock.waitForConnected(300):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(APP_ID)
    server = QLocalServer()
    server.listen(APP_ID)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.warning(None, APP_NAME, "시스템 트레이를 사용할 수 없습니다.")

    ctrl = Controller(app)

    def on_new_connection():
        conn = server.nextPendingConnection()
        conn.readyRead.connect(lambda: (conn.readAll(), ctrl.show_launcher()))

    server.newConnection.connect(on_new_connection)

    if "--hidden" not in sys.argv and not ctrl.cfg.get("hide_launcher"):
        ctrl.show_launcher()             # Windows 자동 시작(--hidden)일 때는 트레이에만 조용히 대기
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
