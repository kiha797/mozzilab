"""모찌LAB. 실시간 알림: 로그인해 있는 동안 서버와 연결을 열어 두고,
관리자 화면에서 유료로 바꾸거나 기기 로그인을 해제하면 그 즉시 알림을 받아 구독 상태를 다시 불러온다.
(연결이 끊기면 몇 초 뒤 다시 연결하고, 그동안은 10분마다 확인하는 기존 방식이 대신한다)"""
from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtNetwork import QNetworkRequest
from PySide6.QtWebSockets import QWebSocket

from brand import APP_VERSION, SERVER_URL

PING_MS = 45 * 1000          # 공유기 · 방화벽이 조용한 연결을 끊지 않도록 45초마다 신호
RETRY_MS = (3, 10, 30, 60)   # 다시 연결할 때 기다리는 시간(초): 3초 → 10초 → 30초 → 1분


class LiveLink(QObject):
    def __init__(self, account):
        super().__init__()
        self.account = account
        self.token = None
        self.tries = 0
        self.ws = QWebSocket()
        self.ws.setParent(self)
        self.ws.connected.connect(self._connected)
        self.ws.disconnected.connect(self._disconnected)
        self.ws.textMessageReceived.connect(self._message)
        self.ping = QTimer(self)
        self.ping.timeout.connect(lambda: self.ws.sendTextMessage("ping"))
        self.retry = QTimer(self)
        self.retry.setSingleShot(True)
        self.retry.timeout.connect(self._open)
        account.changed.connect(self._sync)
        self._sync()

    def _sync(self):
        """로그인 · 로그아웃에 맞춰 연결을 열거나 닫는다"""
        token = self.account.data.get("token") if self.account.logged_in else None
        if token == self.token:
            return
        self.token = token
        self.tries = 0
        self.retry.stop()
        self.ws.abort()
        if token:
            self._open()

    def _open(self):
        if not self.token:
            return
        url = SERVER_URL.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/api/live"
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"Authorization", f"Bearer {self.token}".encode())
        req.setRawHeader(b"User-Agent", f"MozziLab/{APP_VERSION}".encode())
        self.ws.open(req)

    def _connected(self):
        if self.tries:
            self.account.refresh()     # 끊겨 있던 동안 바뀐 것이 있을 수 있으니 한 번 확인
        self.tries = 0
        self.ping.start(PING_MS)

    def _disconnected(self):
        self.ping.stop()
        if self.token:
            wait = RETRY_MS[min(self.tries, len(RETRY_MS) - 1)]
            self.tries += 1
            self.retry.start(wait * 1000)

    def _message(self, text):
        if text != "pong":
            self.account.refresh()      # 유료 전환 · 기기 해제 등 → 바로 다시 확인
