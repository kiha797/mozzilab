"""자동 업데이트 - GitHub 다운로드 페이지(Releases)에서 새 버전을 확인하고, 받아서 조용히 설치한다.
- 프로그램을 켤 때 하루 한 번 확인 (메뉴의 '업데이트 확인'으로 바로 확인도 가능)
- 새 버전 설명(릴리스 노트)에 [필수] 가 있으면 '이 버전 건너뛰기'를 없앤다"""
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QProcess, Qt, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout

import brand
from ui import ACCENT, app_icon, mochi_pixmap, px

RELEASE_API = "https://api.github.com/repos/kiha797/mozzilab/releases/latest"
CHECK_EVERY = timedelta(hours=20)
MANDATORY_MARK = "[필수]"
SILENT_ARGS = ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/CLOSEAPPLICATIONS"]


def parse_version(v):
    nums = [int(x) for x in re.findall(r"\d+", v or "")][:3]
    return tuple(nums + [0] * (3 - len(nums)))


class UpdateDialog(QDialog):
    def __init__(self, updater, latest, url, mandatory):
        super().__init__(None)
        self.updater = updater
        self.latest = latest
        self.url = url
        self.reply = None
        self.setWindowTitle(f"{brand.APP_NAME} 업데이트")
        self.setWindowIcon(app_icon())
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(px(420))
        self.setStyleSheet("QDialog { background: white; }")
        v = QVBoxLayout(self)
        v.setContentsMargins(px(28), px(22), px(28), px(18))
        v.setSpacing(px(8))
        pic = QLabel()
        pic.setPixmap(mochi_pixmap(px(90)))
        pic.setAlignment(Qt.AlignCenter)
        title = QLabel("중요한 업데이트가 있어요!" if mandatory else "새 버전이 나왔어요! 🎉")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        ver = QLabel(f"{brand.APP_NAME}  {brand.APP_VERSION}  →  <b style='color:{ACCENT}'>{latest}</b>")
        ver.setAlignment(Qt.AlignCenter)
        self.info = QLabel("설정과 저장해 둔 내용은 그대로 남아요.\n업데이트하면 프로그램이 잠깐 닫혔다가 다시 켜집니다.")
        self.info.setAlignment(Qt.AlignCenter)
        self.info.setStyleSheet("color: #6b5d5d;")
        self.bar = QProgressBar()
        self.bar.hide()
        for w in (pic, title, ver, self.info, self.bar):
            v.addWidget(w)
        row = QHBoxLayout()
        self.skip = QPushButton("이 버전 건너뛰기")
        self.skip.clicked.connect(self._skip)
        self.skip.setVisible(not mandatory)
        self.later = QPushButton("나중에")
        self.later.clicked.connect(self.reject)
        self.go = QPushButton("지금 업데이트")
        self.go.setObjectName("primary")
        self.go.setDefault(True)
        self.go.clicked.connect(self._download)
        row.addWidget(self.skip)
        row.addStretch(1)
        row.addWidget(self.later)
        row.addWidget(self.go)
        v.addSpacing(px(6))
        v.addLayout(row)

    def _skip(self):
        self.updater.cfg["update_skip"] = self.latest
        self.updater.cfg.save()
        self.reject()

    def _download(self):
        self.go.setEnabled(False)
        self.skip.hide()
        self.bar.show()
        self.bar.setValue(0)
        self.info.setText("새 버전을 내려받는 중…")
        req = QNetworkRequest(QUrl(self.url))
        req.setRawHeader(b"User-Agent", f"{brand.APP_ID}/{brand.APP_VERSION}".encode())
        req.setAttribute(QNetworkRequest.RedirectPolicyAttribute, QNetworkRequest.NoLessSafeRedirectPolicy)
        self.reply = self.updater.nam.get(req)
        self.reply.downloadProgress.connect(
            lambda got, total: total > 0 and self.bar.setValue(int(got * 100 / total)))
        self.reply.finished.connect(self._downloaded)

    def _downloaded(self):
        r = self.reply
        if r.error() != QNetworkReply.NoError:
            self.info.setText(f"내려받지 못했어요. 인터넷 연결을 확인하고 다시 시도해 주세요.\n({r.errorString()})")
            self.go.setEnabled(True)
            self.bar.hide()
            return
        path = os.path.join(tempfile.gettempdir(), f"{brand.APP_ID}_Setup_{self.latest}.exe")
        with open(path, "wb") as f:
            f.write(bytes(r.readAll()))
        r.deleteLater()
        self.info.setText("설치를 시작합니다. 잠시 뒤 새 버전이 켜져요!")
        self.bar.setValue(100)
        if sys.platform != "win32":
            self.info.setText(f"설치파일을 받았습니다:\n{path}")
            return
        if QProcess.startDetached(path, SILENT_ARGS):
            self.accept()
            self.updater.on_quit()                 # 설치가 진행되도록 프로그램을 닫는다
        else:
            self.info.setText(f"설치를 시작하지 못했어요. 아래 파일을 직접 실행해 주세요.\n{path}")
            self.go.setEnabled(True)


class Updater(QObject):
    def __init__(self, cfg, on_quit):
        super().__init__()
        self.cfg = cfg
        self.on_quit = on_quit
        self.nam = QNetworkAccessManager(self)
        self.dialog = None

    def check(self, manual=False):
        """새 버전 확인. manual=True 면 하루 한 번 제한 없이 바로 확인하고 결과를 알려 준다."""
        if not manual:
            try:
                last = datetime.fromisoformat(self.cfg.get("update_checked_at") or "")
                if datetime.now() - last < CHECK_EVERY:
                    return
            except ValueError:
                pass
        req = QNetworkRequest(QUrl(RELEASE_API))
        req.setRawHeader(b"User-Agent", f"{brand.APP_ID}/{brand.APP_VERSION}".encode())
        req.setRawHeader(b"Accept", b"application/vnd.github+json")
        req.setTransferTimeout(15000)
        reply = self.nam.get(req)
        reply.finished.connect(lambda: self._checked(reply, manual))

    def _message(self, text):
        box = QMessageBox(QMessageBox.Information, f"{brand.APP_NAME} 업데이트", text)
        box.setWindowIcon(app_icon())
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        box.exec()

    def _checked(self, reply, manual):
        import json
        ok = reply.error() == QNetworkReply.NoError
        raw = bytes(reply.readAll())
        reply.deleteLater()
        if not ok:
            if manual:
                self._message("업데이트를 확인하지 못했어요. 인터넷 연결을 확인해 주세요.")
            return
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            return
        self.cfg["update_checked_at"] = datetime.now().isoformat(timespec="seconds")
        self.cfg.save()
        latest = (data.get("tag_name") or "").lstrip("vV")
        if parse_version(latest) <= parse_version(brand.APP_VERSION):
            if manual:
                self._message(f"지금 최신 버전({brand.APP_VERSION})을 쓰고 있어요. 🍡")
            return
        mandatory = MANDATORY_MARK in (data.get("body") or "") or MANDATORY_MARK in (data.get("name") or "")
        if not manual and not mandatory and self.cfg.get("update_skip") == latest:
            return
        name = f"{brand.APP_ID}_Setup.exe"
        url = next((a.get("browser_download_url") for a in data.get("assets", []) if a.get("name") == name), None)
        if not url:
            if manual:
                self._message("새 버전 설치파일을 아직 준비 중이에요. 잠시 뒤 다시 확인해 주세요.")
            return
        self.dialog = UpdateDialog(self, latest, url, mandatory)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
