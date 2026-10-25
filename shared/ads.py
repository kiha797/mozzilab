"""무료 사용자용 광고 (결과창 오른쪽 위 배너 + 캡처 후 왼쪽 아래 팝업).
광고 내용은 관리자 사이트(광고 관리)에서 정하고, 서버에 연결이 안 되면 기본 광고를 보여준다.
모찌 플러스 구독자에게는 광고가 보이지 않는다."""
import random

from PySide6.QtCore import QEvent, QObject, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout, QWidget

from brand import APP_SLUG, SERVER_URL
from ui import mochi_pixmap, px

HOUSE_ADS = {
    "banner": [{"id": None, "title": "광고 없이 쾌적하게, 모찌 플러스", "subtitle": "월 5,500원 · 모든 모찌LAB. 광고 제거",
                "bg_color": "#ff6f91", "button_text": "자세히 알아보기", "image_url": "", "weight": 1}],
    "popup": [{"id": None, "title": "광고가 신경 쓰이나요?", "subtitle": "모찌 플러스로 모든 모찌LAB. 프로그램을 광고 없이 쓰세요. 언제든 해지 가능!",
               "bg_color": "#ff8fab", "button_text": "광고 없이 쓰기", "image_url": "", "weight": 1}],
}


class AdManager(QObject):
    changed = Signal()

    def __init__(self, cfg, api, account):
        super().__init__()
        self.cfg = cfg
        self.api = api
        self.account = account
        self.data = {"show_ads": True, "popup_every": 1, "pricing_url": SERVER_URL + "/pricing", **HOUSE_ADS}
        self.images = {}

    @property
    def show_ads(self):
        return not self.account.premium and self.data.get("show_ads", True)

    def fetch(self):
        token = self.account.data.get("token")

        def done(status, data):
            if status == 200:
                data.setdefault("banner", [])
                data.setdefault("popup", [])
                if not data["banner"]:
                    data["banner"] = HOUSE_ADS["banner"]
                if not data["popup"]:
                    data["popup"] = HOUSE_ADS["popup"]
                self.data = data
                for ad in data["banner"] + data["popup"]:
                    self._load_image(ad.get("image_url"))
            self.changed.emit()

        self.api.request("GET", f"/api/ads?app={APP_SLUG}", token=token, callback=done)

    def _load_image(self, url):
        if not url or url in self.images:
            return
        self.images[url] = None

        def done(data):
            pm = QPixmap()
            if data and pm.loadFromData(data):
                self.images[url] = pm
                self.changed.emit()

        self.api.get_bytes(url, done)

    def image(self, ad):
        return self.images.get(ad.get("image_url") or "")

    def pick(self, kind):
        items = self.data.get(kind) or HOUSE_ADS[kind]
        return random.choices(items, weights=[max(1, int(a.get("weight", 1))) for a in items])[0]

    def report_view(self, ad):
        if ad and ad.get("id"):
            self.api.request("POST", f"/api/ads/{ad['id']}/view")

    def click(self, ad):
        url = (ad or {}).get("click_url") or self.data.get("pricing_url") or SERVER_URL + "/pricing"
        QDesktopServices.openUrl(QUrl(url))

    def should_popup(self):
        """N번 캡처할 때마다 한 번 팝업 광고 (관리자 설정 '팝업 광고 빈도')"""
        if not self.show_ads:
            return False
        self.cfg["capture_count"] = int(self.cfg.get("capture_count", 0)) + 1
        self.cfg.save()
        return self.cfg["capture_count"] % max(1, int(self.data.get("popup_every", 1))) == 0


class AdCard(QWidget):
    """광고 한 장 (이미지가 있으면 이미지, 없으면 배경색 + 모찌 + 글자)"""

    def __init__(self, ads, size, big_text=False):
        super().__init__()
        self.ads = ads
        self.ad = None
        self.big = big_text
        self.setFixedSize(size)
        self.setCursor(Qt.PointingHandCursor)
        ads.changed.connect(self.update)

    def set_ad(self, ad):
        self.ad = ad
        self.setToolTip(f"{ad.get('title', '')} (광고)")
        self.ads.report_view(ad)
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.ad:
            self.ads.click(self.ad)

    def paintEvent(self, _):
        if not self.ad:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(r, px(10), px(10))
        p.setClipPath(path)
        pm = self.ads.image(self.ad)
        if pm and not pm.isNull():
            scaled = pm.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawPixmap((self.width() - scaled.width()) // 2, (self.height() - scaled.height()) // 2, scaled)
        else:
            base = QColor(self.ad.get("bg_color") or "#ff6f91")
            g = QLinearGradient(0, 0, self.width(), self.height())
            g.setColorAt(0, base)
            g.setColorAt(1, base.lighter(130))
            p.fillPath(path, g)
            m = mochi_pixmap(int(self.height() * (0.62 if self.big else 0.8)))
            mx = px(14)
            my = self.height() - m.height() - px(10) if self.big else (self.height() - m.height()) // 2
            p.drawPixmap(mx, my, m)
            dark = base.lightness() > 185
            p.setPen(QColor("#3b2f2f") if dark else Qt.white)
            tx = mx + m.width() + px(12) if not self.big else px(18)
            ty = px(16) if self.big else 0
            tw = self.width() - tx - px(12)
            f = QFont(self.font())
            f.setBold(True)
            f.setPointSizeF(15 if self.big else 11.5)
            p.setFont(f)
            title_h = p.fontMetrics().height() * (2 if self.big else 1)
            if self.big:
                p.drawText(QRectF(tx, ty + px(16), tw, title_h), Qt.TextWordWrap, self.ad.get("title", ""))
            else:
                title = p.fontMetrics().elidedText(self.ad.get("title", ""), Qt.ElideRight, int(tw))
                p.drawText(QRectF(tx, px(14), tw, self.height() / 2), Qt.AlignLeft | Qt.AlignVCenter, title)
            f.setBold(False)
            f.setPointSizeF(10.5 if self.big else 9)
            p.setFont(f)
            if self.big:
                sub = QRectF(tx + m.width() * 0.9, ty + px(16) + title_h + px(6), tw - m.width() * 0.9, self.height())
                p.drawText(sub, Qt.TextWordWrap, self.ad.get("subtitle", ""))
            else:
                p.drawText(QRectF(tx, self.height() / 2 + px(2), tw, self.height() / 2 - px(8)),
                           Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, self.ad.get("subtitle", ""))
        # 'AD' 표시
        p.setClipping(False)
        f = QFont(self.font())
        f.setPointSizeF(7.5)
        f.setBold(True)
        p.setFont(f)
        badge = QRectF(px(6), px(6), px(26), px(15))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 110))
        p.drawRoundedRect(badge, px(4), px(4))
        p.setPen(Qt.white)
        p.drawText(badge, Qt.AlignCenter, "AD")


class AdBlock(QWidget):
    """결과창 오른쪽 위: 배너 광고 + [자세히 알아보기] 버튼 (알캡처와 같은 배치)"""

    def __init__(self, ads):
        super().__init__()
        self.ads = ads
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.card = AdCard(ads, QSize(px(300), px(84)))
        self.more = QPushButton("자세히 알아보기")
        self.more.setObjectName("adMore")
        self.more.setCursor(Qt.PointingHandCursor)
        self.more.setFixedSize(px(118), px(84))
        self.more.setStyleSheet(f"QPushButton#adMore {{ background: #3b2f2f; color: white; border: none; "
                                f"border-radius: {px(10)}px; font-weight: bold; font-size: 10.5pt; margin-left: {px(4)}px; }}"
                                "QPushButton#adMore:hover { background: #55443f; }")
        self.more.clicked.connect(lambda: self.ads.click(self.card.ad))
        h.addWidget(self.card)
        h.addWidget(self.more)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.timer.start(60_000)                 # 1분마다 다른 광고

    def rotate(self):
        if not self.isVisible() and not self.ads.show_ads:
            return
        ad = self.ads.pick("banner")
        self.card.set_ad(ad)
        self.more.setText(ad.get("button_text") or "자세히 알아보기")


class PopupAd(QFrame):
    """캡처 직후 결과창 왼쪽 아래에 뜨는 광고 (X 로 닫기)"""

    def __init__(self, ads, host):
        super().__init__(host)
        self.ads = ads
        self.host = host
        self.setObjectName("popupAd")
        self.setStyleSheet("QFrame#popupAd { background: white; border: 1px solid #e5dcdc; border-radius: 12px; }")
        v = QVBoxLayout(self)
        v.setContentsMargins(px(6), px(6), px(6), px(6))
        v.setSpacing(px(4))
        self.card = AdCard(ads, QSize(px(340), px(200)), big_text=True)
        v.addWidget(self.card)
        row = QHBoxLayout()
        self.cta = QPushButton("광고 없이 쓰기")
        self.cta.setObjectName("popupCta")
        self.cta.setStyleSheet(f"QPushButton#popupCta {{ background: #ff6f91; color: white; border: none; "
                               f"border-radius: {px(6)}px; padding: {px(6)}px {px(16)}px; font-weight: bold; }}"
                               "QPushButton#popupCta:hover { background: #e8557a; }")
        self.cta.setCursor(Qt.PointingHandCursor)
        self.cta.clicked.connect(lambda: self.ads.click(self.card.ad))
        no_ads = QLabel("<a href='#' style='color:#8a7c7e; text-decoration:none'>모찌 플러스로 광고 끄기 ›</a>")
        no_ads.setStyleSheet("background: transparent; font-size: 9pt;")
        no_ads.linkActivated.connect(lambda _: self.ads.click(None))
        row.addWidget(no_ads)
        row.addStretch(1)
        row.addWidget(self.cta)
        v.addLayout(row)
        self.close_btn = QToolButton(self)
        self.close_btn.setText("✕")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setStyleSheet("QToolButton { background: rgba(0,0,0,120); color: white; border: none; "
                                     f"border-radius: {px(11)}px; font-weight: bold; }}")
        self.close_btn.setFixedSize(px(22), px(22))
        self.close_btn.clicked.connect(self.hide)
        self.adjustSize()
        self.close_btn.move(self.width() - px(32), px(12))
        host.installEventFilter(self)
        self.hide()

    def show_ad(self):
        ad = self.ads.pick("popup")
        self.card.set_ad(ad)
        self.cta.setText(ad.get("button_text") or "자세히 알아보기")
        self._place()
        self.show()
        self.raise_()

    def _place(self):
        self.move(px(14), self.host.height() - self.height() - px(14))

    def eventFilter(self, obj, e):
        if obj is self.host and e.type() == QEvent.Resize and self.isVisible():
            self._place()
        return False
