"""모찌랩 계정 로그인 + 라이선스(광고 제거 구독) 확인.
PC 에서 [로그인] -> 웹브라우저가 열리고 로그인 -> [연결 승인] -> PC 가 자동으로 로그인 완료."""
import json
import platform
import uuid
from datetime import datetime, timedelta

from PySide6.QtCore import QByteArray, QObject, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from brand import APP_SLUG, APP_VERSION, BRAND_NAME, SERVER_URL
from ui import ACCENT, app_icon, mochi_pixmap, px

OFFLINE_GRACE_DAYS = 7      # 인터넷이 안 될 때도 마지막 확인 후 7일 동안은 구독 상태 유지


def shared_device_id():
    """이 PC 고유번호. 모찌캡처·모찌PDF·모찌압축이 함께 쓴다. (%APPDATA%\\MozziLab\\device.json)"""
    import os
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    folder = os.path.join(base, "MozziLab")
    path = os.path.join(folder, "device.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            did = json.load(f).get("device_id")
            if did:
                return did
    except (OSError, ValueError):
        pass
    did = uuid.uuid4().hex
    try:
        os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"device_id": did}, f)
    except OSError:
        pass
    return did


class Api(QObject):
    """서버와 통신 (화면이 멈추지 않도록 비동기로 동작)"""

    def __init__(self):
        super().__init__()
        self.nam = QNetworkAccessManager(self)

    def request(self, method, path, body=None, token=None, callback=None):
        url = path if path.startswith("http") else SERVER_URL + path
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        req.setRawHeader(b"User-Agent", f"MochiCapture/{APP_VERSION}".encode())
        req.setTransferTimeout(10000)
        if token:
            req.setRawHeader(b"Authorization", f"Bearer {token}".encode())
        if method == "GET":
            reply = self.nam.get(req)
        else:
            reply = self.nam.post(req, QByteArray(json.dumps(body or {}).encode("utf-8")))

        def done():
            status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0
            raw = bytes(reply.readAll())
            try:
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except ValueError:
                data = {}
            if reply.error() != QNetworkReply.NoError and not status:
                status = 0                         # 서버에 연결 못 함
            reply.deleteLater()
            if callback:
                callback(int(status), data)

        reply.finished.connect(done)
        return reply

    def get_bytes(self, url, callback):
        reply = self.nam.get(QNetworkRequest(QUrl(url)))

        def done():
            data = bytes(reply.readAll()) if reply.error() == QNetworkReply.NoError else b""
            reply.deleteLater()
            callback(data)

        reply.finished.connect(done)


def _parse(iso):
    try:
        return datetime.fromisoformat(iso) if iso else None
    except ValueError:
        return None


class Account(QObject):
    changed = Signal()

    def __init__(self, cfg, api):
        super().__init__()
        self.cfg = cfg
        self.api = api
        shared_id = shared_device_id()
        if cfg.get("device_id") != shared_id:
            cfg["device_id"] = shared_id          # 모찌랩 프로그램끼리 같은 PC 번호를 씀 (PC 1대 = 1대로 계산)
            cfg.save()

    # ---------- 상태 ----------
    @property
    def data(self):
        return self.cfg.get("account") or {}

    @property
    def logged_in(self):
        return bool(self.data.get("token"))

    @property
    def name(self):
        return self.data.get("name") or self.data.get("email", "")

    @property
    def email(self):
        return self.data.get("email", "")

    @property
    def premium(self):
        d = self.data
        if not (self.logged_in and d.get("premium")):
            return False
        expires, checked = _parse(d.get("expires_at")), _parse(d.get("checked_at"))
        now = datetime.now()
        if expires and expires < now:
            return False
        return bool(checked and now - checked < timedelta(days=OFFLINE_GRACE_DAYS))

    @property
    def expires_at(self):
        return _parse(self.data.get("expires_at"))

    # ---------- 동작 ----------
    def _save(self, data):
        self.cfg["account"] = data
        self.cfg.save()
        self.changed.emit()

    def set_token(self, token):
        self._save({"token": token})

    def refresh(self, callback=None):
        """서버에 구독 상태를 다시 물어본다."""
        if not self.logged_in:
            if callback:
                callback(False)
            return
        token = self.data["token"]

        def done(status, data):
            if status == 200:
                d = dict(self.data)
                d.update({"email": data.get("email", ""), "name": data.get("name", ""),
                          "premium": bool(data.get("premium")), "expires_at": data.get("expires_at"),
                          "plan_name": data.get("plan_name", ""), "mypage_url": data.get("mypage_url", ""),
                          "pricing_url": data.get("pricing_url", ""),
                          "checked_at": datetime.now().isoformat(timespec="seconds")})
                self._save(d)
            elif status == 401:                     # 웹에서 기기 해제됨 / 토큰 만료
                self._save({})
            if callback:
                callback(status == 200)

        self.api.request("GET", "/api/me", token=token, callback=done)

    def logout(self):
        if self.logged_in:
            self.api.request("POST", "/api/logout", token=self.data["token"])
        self._save({})

    def open_web(self, path):
        QDesktopServices.openUrl(QUrl(path if path.startswith("http") else SERVER_URL + path))

    def open_pricing(self):
        self.open_web(self.data.get("pricing_url") or "/pricing")

    def open_mypage(self):
        self.open_web(self.data.get("mypage_url") or "/mypage")

    def login(self, parent=None):
        dlg = LoginDialog(self, parent)
        return dlg.exec()


class LoginDialog(QDialog):
    def __init__(self, account, parent=None):
        super().__init__(parent)
        self.account = account
        self.api = account.api
        self.device_code = None
        self.verify_url = None
        self.setWindowTitle(f"{BRAND_NAME} 로그인")
        self.setWindowIcon(app_icon())
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(px(420))
        self.setStyleSheet("QDialog { background: white; }")

        v = QVBoxLayout(self)
        v.setContentsMargins(px(28), px(24), px(28), px(20))
        v.setSpacing(px(8))
        pic = QLabel()
        pic.setPixmap(mochi_pixmap(px(96)))
        pic.setAlignment(Qt.AlignCenter)
        title = QLabel(f"{BRAND_NAME} 계정으로 로그인")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self.info = QLabel("서버에 연결하는 중…")
        self.info.setAlignment(Qt.AlignCenter)
        self.info.setWordWrap(True)
        self.info.setStyleSheet("color: #6b5d5d;")
        self.code = QLabel("")
        self.code.setAlignment(Qt.AlignCenter)
        self.code.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.code.setStyleSheet(f"font-size: 22pt; font-weight: bold; letter-spacing: 4px; color: {ACCENT};"
                                "background: #fff8f1; border-radius: 12px; padding: 10px;")
        self.code.hide()
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #a3979a; font-size: 9pt;")
        for w in (pic, title, self.info, self.code, self.status):
            v.addWidget(w)
        row = QHBoxLayout()
        self.open_btn = QPushButton("브라우저 다시 열기")
        self.open_btn.clicked.connect(self._open_browser)
        self.open_btn.setEnabled(False)
        self.retry_btn = QPushButton("다시 시도")
        self.retry_btn.clicked.connect(self._start)
        self.retry_btn.hide()
        cancel = QPushButton("닫기")
        cancel.clicked.connect(self.reject)
        row.addWidget(self.open_btn)
        row.addWidget(self.retry_btn)
        row.addStretch(1)
        row.addWidget(cancel)
        v.addSpacing(px(6))
        v.addLayout(row)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        QTimer.singleShot(0, self._start)

    def _start(self):
        self.retry_btn.hide()
        self.info.setText("서버에 연결하는 중…")
        self.api.request("POST", "/api/device/start", {
            "device_id": self.account.cfg["device_id"],
            "device_name": platform.node() or "내 PC",
            "app": APP_SLUG, "version": APP_VERSION,
        }, callback=self._started)

    def _started(self, status, data):
        if status != 200 or "device_code" not in data:
            self.info.setText("모찌랩 서버에 연결할 수 없어요.\n인터넷 연결을 확인하고 다시 시도해 주세요.")
            self.status.setText(f"서버 주소: {SERVER_URL}")
            self.retry_btn.show()
            return
        self.device_code = data["device_code"]
        self.verify_url = data["verify_url"]
        self.code.setText(data["user_code"])
        self.code.show()
        self.info.setText("웹브라우저가 열리면 로그인(또는 회원가입)한 뒤\n아래 코드를 확인하고 [연결 승인]을 눌러 주세요.")
        self.status.setText("승인을 기다리는 중… (10분 안에 완료해 주세요)")
        self.open_btn.setEnabled(True)
        self._open_browser()
        self.timer.start(max(2, int(data.get("interval", 3))) * 1000)

    def _open_browser(self):
        if self.verify_url:
            QDesktopServices.openUrl(QUrl(self.verify_url))

    def _poll(self):
        self.api.request("POST", "/api/device/poll", {"device_code": self.device_code}, callback=self._polled)

    def _polled(self, status, data):
        st = data.get("status")
        if st == "approved" and data.get("token"):
            self.timer.stop()
            self.account.set_token(data["token"])
            self.status.setText("로그인 완료! 계정 정보를 불러오는 중…")
            self.account.refresh(lambda ok: self.accept())
        elif st in ("expired", "denied", "invalid", "used"):
            self.timer.stop()
            self.code.hide()
            self.info.setText("시간이 지났거나 연결이 거절되었어요.\n[다시 시도]를 눌러 주세요." if st != "denied"
                              else "웹에서 연결을 거절했어요.")
            self.status.setText("")
            self.retry_btn.show()

    def done(self, r):
        self.timer.stop()
        super().done(r)
