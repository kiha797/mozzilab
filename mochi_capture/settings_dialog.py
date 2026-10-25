"""환경설정 창 (일반 설정 / 고급 설정 / 단축키 설정 / 캡처목록 설정) - 알캡처 환경설정과 같은 구성"""
import copy

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog,
                               QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                               QPushButton, QSpinBox, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from config import APP_NAME, Config, HOTKEY_MODES, NAME_DATE_FORMATS, PAGE_DEFAULTS
from ui import color_icon, icon, px

GUIDE_COLORS = [("빨강", "#ff0000"), ("주황", "#ff8c00"), ("노랑", "#ffd400"), ("초록", "#00b050"),
                ("파랑", "#1a73e8"), ("보라", "#7030a0"), ("검정", "#000000"), ("흰색", "#ffffff")]
MODE_NAMES = {"region": "직접지정", "window": "창 캡처", "unit": "단위영역",
              "full": "전체캡처", "scroll": "스크롤캡처", "fixed": "크기지정"}
PRINTSCREEN_ACTIONS = [("launcher", "실행창 열기"), ("region", "직접 지정 캡처"), ("window", "창 캡처"),
                       ("unit", "단위영역 캡처"), ("full", "전체 캡처"), ("scroll", "스크롤 캡처"),
                       ("fixed", "크기지정 캡처")]
KEYS = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + [str(i) for i in range(10)] + \
       [f"F{i}" for i in range(1, 13)]
MAX_PRESETS = 6


def key_to_vk(key):
    if key.startswith("F") and len(key) > 1:
        return 0x70 + int(key[1:]) - 1
    return ord(key)


def hotkey_label(hk):
    parts = [n for k, n in (("win", "Win"), ("ctrl", "Ctrl"), ("shift", "Shift"), ("alt", "Alt")) if hk.get(k)]
    return " + ".join(parts + [hk.get("key", "")])


def _section(text):
    lb = QLabel(text)
    lb.setObjectName("sectionTitle")
    return lb


def _line():
    ln = QFrame()
    ln.setFrameShape(QFrame.HLine)
    ln.setObjectName("sectionLine")
    return ln


# ----------------------------------------------------------------------
class FileNameDialog(QDialog):
    """[파일명 설정] - 저장할 때 붙는 파일 이름 규칙"""

    def __init__(self, work, parent=None):
        super().__init__(parent)
        self.work = work
        self.setWindowTitle("파일명 설정")
        self.setMinimumWidth(px(420))
        form = QFormLayout()
        self.prefix = QLineEdit(work.get("name_prefix", ""))
        self.prefix.setPlaceholderText("예: 캡처, 회사이름")
        self.date = QComboBox()
        for label, fmt in NAME_DATE_FORMATS:
            self.date.addItem(label, fmt)
        idx = self.date.findData(work.get("name_date", ""))
        self.date.setCurrentIndex(max(0, idx))
        self.counter = QCheckBox("파일명 끝에 일련번호 붙이기 (001, 002 …)")
        self.counter.setChecked(work.get("name_counter", False))
        self.start = QSpinBox()
        self.start.setRange(1, 99999)
        self.start.setValue(int(work.get("name_counter_next", 1)))
        self.preview = QLabel()
        self.preview.setStyleSheet("color:#ff6f91; font-weight:bold;")
        form.addRow("앞 글자", self.prefix)
        form.addRow("날짜/시간", self.date)
        form.addRow("", self.counter)
        form.addRow("다음 번호", self.start)
        form.addRow("미리보기", self.preview)
        for w in (self.prefix,):
            w.textChanged.connect(self._update)
        self.date.currentIndexChanged.connect(self._update)
        self.counter.toggled.connect(self._update)
        self.start.valueChanged.connect(self._update)
        v = QVBoxLayout(self)
        v.addLayout(form)
        v.addLayout(_ok_cancel(self))
        self._update()

    def _values(self):
        return {"name_prefix": self.prefix.text(), "name_date": self.date.currentData(),
                "name_counter": self.counter.isChecked(), "name_counter_next": self.start.value()}

    def _update(self):
        tmp = Config()
        tmp.update(self.work)
        tmp.update(self._values())
        self.start.setEnabled(self.counter.isChecked())
        self.preview.setText(tmp.preview_name())

    def accept(self):
        self.work.update(self._values())
        super().accept()


class SizeDialog(QDialog):
    """크기지정 프리셋 추가/변경"""

    def __init__(self, w=800, h=600, parent=None):
        super().__init__(parent)
        self.setWindowTitle("크기 입력")
        form = QFormLayout()
        self.w = QSpinBox()
        self.h = QSpinBox()
        for s, v in ((self.w, w), (self.h, h)):
            s.setRange(20, 10000)
            s.setValue(v)
            s.setSuffix(" px")
        form.addRow("가로", self.w)
        form.addRow("세로", self.h)
        v = QVBoxLayout(self)
        v.addLayout(form)
        v.addLayout(_ok_cancel(self))


def _ok_cancel(dlg):
    row = QHBoxLayout()
    row.addStretch(1)
    ok = QPushButton("확인")
    ok.setObjectName("primary")
    ok.setDefault(True)
    cancel = QPushButton("취소")
    ok.clicked.connect(dlg.accept)
    cancel.clicked.connect(dlg.reject)
    for b in (ok, cancel):
        b.setMinimumWidth(px(90))
        row.addWidget(b)
    return row


# ----------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None, page=0):
        super().__init__(parent)
        self.cfg = cfg
        self.work = copy.deepcopy(dict(cfg))       # 확인을 누르기 전까지는 복사본만 수정
        self.checks = {}
        self.setWindowTitle("환경설정")
        self.setMinimumSize(px(760), px(620))
        self.setStyleSheet(f"""
            QDialog {{ background: #ffffff; }}
            QListWidget#settingsNav {{ border: 1px solid #c9ced6; background: white; outline: 0; }}
            QListWidget#settingsNav::item {{ padding: {px(8)}px {px(6)}px; color: #333; }}
            QListWidget#settingsNav::item:selected {{ background: #ffe3eb; color: #333; }}
            QListWidget#settingsNav::item:hover {{ background: #fff0f4; }}
            QLabel#sectionTitle {{ font-weight: bold; font-size: 11pt; margin-top: {px(4)}px; }}
            QFrame#sectionLine {{ color: #d5d9e0; margin: {px(6)}px 0; }}
            QCheckBox {{ spacing: {px(8)}px; padding: {px(3)}px 0; font-size: 10.5pt; }}
            QPushButton {{ padding: {px(5)}px {px(14)}px; }}
        """)

        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setFixedWidth(px(200))
        self.nav.setIconSize(QSize(px(22), px(22)))
        for name, ic in (("일반 설정", "newcap"), ("고급 설정", "sliders"),
                         ("단축키 설정", "hotkey"), ("캡처목록 설정", "list")):
            self.nav.addItem(QListWidgetItem(icon(ic), name))
        self.stack = QStackedWidget()
        for build in (self._page_general, self._page_advanced, self._page_hotkeys, self._page_history):
            self.stack.addWidget(build())
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)

        defaults = QToolButton()
        defaults.setText("기본값으로  ")
        defaults.setPopupMode(QToolButton.InstantPopup)
        defaults.setFixedWidth(px(200))
        defaults.setStyleSheet(f"QToolButton {{ border:1px solid #c9ced6; padding:{px(6)}px; text-align:left; }}")
        m = QMenu(self)
        m.addAction("현재 화면만 기본값으로", self._reset_page)
        m.addAction("전체 기본값으로", self._reset_all)
        defaults.setMenu(m)

        body = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(self.nav, 1)
        left.addWidget(defaults)
        body.addLayout(left)
        right = QVBoxLayout()
        right.addWidget(self.stack, 1)
        right.addLayout(_ok_cancel(self))
        body.addLayout(right, 1)
        self.setLayout(body)

        self._load()
        self.nav.setCurrentRow(page)

    # ---------- 공통 ----------
    def _check(self, key, text):
        c = QCheckBox(text)
        self.checks[key] = c
        return c

    @staticmethod
    def _page(*widgets):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(px(10), 0, 0, 0)
        v.setSpacing(px(2))
        for item in widgets:
            if isinstance(item, QWidget):
                v.addWidget(item)
            else:
                v.addLayout(item)
        v.addStretch(1)
        return w

    # ---------- 일반 설정 ----------
    def _page_general(self):
        self.color_combo = QComboBox()
        self.color_combo.setMinimumWidth(px(180))
        for name, hexv in GUIDE_COLORS:
            self.color_combo.addItem(color_icon(QColor(hexv), px(18)), name, hexv)
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("표시선 색:"))
        color_row.addWidget(self.color_combo)
        color_row.addStretch(1)
        return self._page(
            _section("기본 설정"),
            self._check("show_overlay", f"{APP_NAME} 실행 시 화면 오버레이 표시"),
            self._check("hide_launcher", "캡처 실행창 숨김 (마우스 우클릭 메뉴로 대체)"),
            self._check("save_dialog_after", "캡처 후 저장창 바로 띄우기"),
            self._check("autostart", "Windows 시작 시 자동 실행"),
            self._check("close_to_tray", "종료버튼 클릭 시 트레이로 최소화"),
            _line(),
            _section("캡처 설정"),
            self._check("no_result_window", "캡처 후 결과창 띄우지 않기"),
            self._check("auto_copy", "캡처한 내용을 항상 클립보드로 복사"),
            self._check("save_notice", "캡처 이미지 저장완료 안내창 띄우기"),
            self._check("include_cursor", "캡처할 때 마우스 커서 포함 (스크롤 캡처는 지원하지 않음)"),
            _line(),
            _section("가이드라인 설정"),
            color_row,
            self._check("keep_guide", "캡처 이미지에 선택 영역 표시선 유지"),
        )

    # ---------- 고급 설정 ----------
    def _page_advanced(self):
        self.fmt = QComboBox()
        for f in ("PNG", "JPG", "BMP"):
            self.fmt.addItem(f, f.lower())
        self.quality = QSpinBox()
        self.quality.setRange(10, 100)
        self.fmt.currentIndexChanged.connect(lambda: self.quality.setEnabled(self.fmt.currentData() == "jpg"))
        name_btn = QPushButton("파일명 설정")
        name_btn.clicked.connect(self._edit_filename)
        self.name_preview = QLabel()
        self.name_preview.setStyleSheet("color:#777;")
        grid = QGridLayout()
        grid.addWidget(QLabel("파일 포맷"), 0, 0)
        grid.addWidget(self.fmt, 0, 1)
        grid.addWidget(QLabel("품질"), 0, 2)
        grid.addWidget(self.quality, 0, 3)
        grid.addWidget(QLabel("파일명"), 1, 0)
        grid.addWidget(name_btn, 1, 1)
        grid.addWidget(self.name_preview, 1, 2, 1, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        auto = self._check("auto_save", "자동저장 설정 사용")
        self.save_dir = QLineEdit()
        self.save_dir.setReadOnly(True)
        self.dir_btn = QPushButton("…")
        self.dir_btn.setFixedWidth(px(44))
        self.dir_btn.clicked.connect(self._browse)
        auto.toggled.connect(self._auto_save_toggled)
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("저장위치"))
        dir_row.addWidget(self.save_dir, 1)
        dir_row.addWidget(self.dir_btn)

        self.preset_table = QTableWidget(0, 2)
        self.preset_table.setHorizontalHeaderLabels(["가로", "세로"])
        self.preset_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preset_table.verticalHeader().setVisible(False)
        self.preset_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.preset_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.preset_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preset_table.setFixedSize(px(400), px(180))
        self.preset_table.itemSelectionChanged.connect(self._preset_buttons)
        self.preset_table.doubleClicked.connect(self._preset_change)
        self.p_add = QPushButton("추가")
        self.p_del = QPushButton("삭제")
        self.p_chg = QPushButton("변경")
        self.p_add.clicked.connect(self._preset_add)
        self.p_del.clicked.connect(self._preset_del)
        self.p_chg.clicked.connect(self._preset_change)
        preset_row = QHBoxLayout()
        preset_row.addWidget(self.preset_table)
        btns = QHBoxLayout()
        for b in (self.p_add, self.p_del, self.p_chg):
            btns.addWidget(b)
        bcol = QVBoxLayout()
        bcol.addLayout(btns)
        bcol.addStretch(1)
        preset_row.addLayout(bcol)
        preset_row.addStretch(1)

        self.delay = QSpinBox()
        self.delay.setRange(150, 3000)
        self.delay.setSingleStep(50)
        self.delay.setSuffix(" ms")
        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("한 번 스크롤한 뒤 기다리는 시간"))
        delay_row.addWidget(self.delay)
        delay_row.addStretch(1)

        return self._page(
            _section("이미지 저장 설정"), grid, _line(),
            _section("자동저장 설정"), auto, dir_row, _line(),
            _section("크기지정 캡처 프리셋 설정"),
            QLabel(f"자주 사용할 크기지정 캡처 사이즈를 미리 등록할 수 있습니다. (최대 {MAX_PRESETS}개)"),
            preset_row, _line(),
            _section("스크롤 캡처 설정"), delay_row,
        )

    def _auto_save_toggled(self, on):
        self.save_dir.setEnabled(on)
        self.dir_btn.setEnabled(on)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "저장위치 선택", self.save_dir.text())
        if d:
            self.save_dir.setText(d)

    def _edit_filename(self):
        if FileNameDialog(self.work, self).exec():
            self._show_name_preview()

    def _show_name_preview(self):
        tmp = Config()
        tmp.update(self.work)
        tmp["save_format"] = self.fmt.currentData()
        self.name_preview.setText("예) " + tmp.preview_name())

    # 프리셋
    def _presets(self):
        return self.work.setdefault("fixed_presets", [])

    def _fill_presets(self):
        t = self.preset_table
        t.setRowCount(0)
        for w, h in self._presets():
            r = t.rowCount()
            t.insertRow(r)
            for c, v in enumerate((w, h)):
                it = QTableWidgetItem(str(v))
                it.setTextAlignment(Qt.AlignCenter)
                t.setItem(r, c, it)
        self._preset_buttons()

    def _preset_buttons(self):
        has = bool(self.preset_table.selectedItems())
        self.p_del.setEnabled(has)
        self.p_chg.setEnabled(has)
        self.p_add.setEnabled(len(self._presets()) < MAX_PRESETS)

    def _preset_add(self):
        if len(self._presets()) >= MAX_PRESETS:
            return
        d = SizeDialog(parent=self)
        if d.exec():
            self._presets().append([d.w.value(), d.h.value()])
            self._fill_presets()

    def _preset_del(self):
        r = self.preset_table.currentRow()
        if 0 <= r < len(self._presets()):
            del self._presets()[r]
            self._fill_presets()

    def _preset_change(self):
        r = self.preset_table.currentRow()
        if 0 <= r < len(self._presets()):
            w, h = self._presets()[r]
            d = SizeDialog(w, h, self)
            if d.exec():
                self._presets()[r] = [d.w.value(), d.h.value()]
                self._fill_presets()

    # ---------- 단축키 설정 ----------
    def _page_hotkeys(self):
        self.ps_on = QCheckBox("PrintScreen 키를")
        self.ps_action = QComboBox()
        for key, name in PRINTSCREEN_ACTIONS:
            self.ps_action.addItem(name, key)
        self.ps_on.toggled.connect(self.ps_action.setEnabled)
        ps_row = QHBoxLayout()
        ps_row.addWidget(self.ps_on)
        ps_row.addWidget(self.ps_action)
        ps_row.addWidget(QLabel("기능으로 사용"))
        ps_row.addStretch(1)

        grid = QGridLayout()
        grid.setHorizontalSpacing(px(14))
        grid.setVerticalSpacing(px(6))
        self.hk_widgets = {}
        for r, mode in enumerate(HOTKEY_MODES):
            on = QCheckBox(MODE_NAMES[mode])
            win, ctrl, shift, alt = QCheckBox("윈도 키"), QCheckBox("Ctrl"), QCheckBox("Shift"), QCheckBox("Alt")
            key = QComboBox()
            key.addItems(KEYS)
            key.setMinimumWidth(px(90))
            widgets = {"on": on, "win": win, "ctrl": ctrl, "shift": shift, "alt": alt, "key": key}
            on.toggled.connect(lambda v, ws=widgets: [w.setEnabled(v) for k, w in ws.items() if k != "on"])
            for c, w in enumerate((on, win, ctrl, shift, alt)):
                grid.addWidget(w, r, c)
            grid.addWidget(key, r, 6)
            grid.setColumnStretch(5, 1)
            self.hk_widgets[mode] = widgets
        tip = QLabel("※ 다른 프로그램이 이미 쓰고 있는 조합은 등록되지 않을 수 있습니다.\n"
                     "※ Windows 11은 '설정 > 접근성 > 키보드 > Print Screen 키로 화면 캡처 열기'를 꺼야 "
                     "PrintScreen 키를 쓸 수 있습니다.")
        tip.setStyleSheet("color:#888;")
        tip.setWordWrap(True)
        return self._page(
            _section("Print Screen 키 사용"), ps_row, _line(),
            _section("캡처 단축키 설정"), QLabel("캡처 옵션별로 단축키를 지정하거나 끌 수 있습니다."),
            grid, _line(), tip,
        )

    # ---------- 캡처목록 설정 ----------
    def _page_history(self):
        self.limit = QSpinBox()
        self.limit.setRange(10, 500)
        self.limit.setSuffix(" 장")
        row = QHBoxLayout()
        row.addWidget(QLabel("최근 캡처 목록 최대 보관"))
        row.addWidget(self.limit)
        row.addStretch(1)
        return self._page(
            _section("최근 캡처 목록"),
            self._check("confirm_clear", "목록 비우기 시 알림창 띄우기"),
            self._check("notice_save_all", "목록 이미지 모두 저장 완료 안내창 띄우기"),
            self._check("confirm_delete", "목록 이미지 삭제 시 알림창 띄우기"),
            self._check("auto_prune", "최근 캡처 목록 가득 찼을 경우, 오래된 이미지 자동 삭제"),
            row,
        )

    # ---------- 값 읽기/쓰기 ----------
    def _load(self):
        w = self.work
        for k, c in self.checks.items():
            c.setChecked(bool(w.get(k)))
        i = self.color_combo.findData(w.get("guide_color"))
        if i < 0:
            self.color_combo.addItem(color_icon(QColor(w["guide_color"]), px(18)), w["guide_color"], w["guide_color"])
            i = self.color_combo.count() - 1
        self.color_combo.setCurrentIndex(i)
        self.fmt.setCurrentIndex(max(0, self.fmt.findData(w.get("save_format", "png"))))
        self.quality.setValue(int(w.get("jpg_quality", 100)))
        self.quality.setEnabled(self.fmt.currentData() == "jpg")
        self.save_dir.setText(self.cfg.save_dir() if not w.get("save_dir") else w["save_dir"])
        self._auto_save_toggled(bool(w.get("auto_save")))
        self._fill_presets()
        self.delay.setValue(int(w.get("scroll_delay", 450)))
        self._show_name_preview()
        self.ps_on.setChecked(bool(w.get("printscreen_on")))
        self.ps_action.setCurrentIndex(max(0, self.ps_action.findData(w.get("printscreen_action"))))
        self.ps_action.setEnabled(self.ps_on.isChecked())
        for mode, ws in self.hk_widgets.items():
            hk = w["hotkeys"][mode]
            for k in ("on", "win", "ctrl", "shift", "alt"):
                ws[k].setChecked(bool(hk.get(k)))
            ws["key"].setCurrentText(hk.get("key", "A"))
            for k, wd in ws.items():
                if k != "on":
                    wd.setEnabled(ws["on"].isChecked())
        self.limit.setValue(int(w.get("history_limit", 100)))

    def _collect(self):
        w = self.work
        for k, c in self.checks.items():
            w[k] = c.isChecked()
        w["guide_color"] = self.color_combo.currentData()
        w["save_format"] = self.fmt.currentData()
        w["jpg_quality"] = self.quality.value()
        w["save_dir"] = self.save_dir.text().strip()
        w["scroll_delay"] = self.delay.value()
        w["printscreen_on"] = self.ps_on.isChecked()
        w["printscreen_action"] = self.ps_action.currentData()
        for mode, ws in self.hk_widgets.items():
            w["hotkeys"][mode] = {k: ws[k].isChecked() for k in ("on", "win", "ctrl", "shift", "alt")}
            w["hotkeys"][mode]["key"] = ws["key"].currentText()
        w["history_limit"] = self.limit.value()

    def _reset_page(self):
        self._collect()
        defaults = copy.deepcopy(PAGE_DEFAULTS[self.stack.currentIndex()])
        self.work.update(defaults)
        self._load()

    def _reset_all(self):
        if QMessageBox.question(self, "환경설정", "모든 설정을 기본값으로 되돌릴까요?") == QMessageBox.Yes:
            for d in PAGE_DEFAULTS:
                self.work.update(copy.deepcopy(d))
            self._load()

    def _validate(self):
        seen = {}
        for mode in HOTKEY_MODES:
            hk = self.work["hotkeys"][mode]
            if not hk["on"]:
                continue
            if not (hk["win"] or hk["ctrl"] or hk["alt"] or hk["shift"]) and not hk["key"].startswith("F"):
                self.nav.setCurrentRow(2)
                QMessageBox.warning(self, "단축키 설정",
                                    f"'{MODE_NAMES[mode]}' 단축키에 Ctrl/Shift/Alt/윈도 키 중 하나를 함께 선택하세요.\n"
                                    "(글자 키 하나만 쓰면 평소 타자를 칠 수 없게 됩니다)")
                return False
            label = hotkey_label(hk)
            if label in seen:
                self.nav.setCurrentRow(2)
                QMessageBox.warning(self, "단축키 설정",
                                    f"'{MODE_NAMES[seen[label]]}'와 '{MODE_NAMES[mode]}'의 단축키({label})가 같습니다.")
                return False
            seen[label] = mode
        return True

    def accept(self):
        self._collect()
        if not self._validate():
            return
        self.cfg.update(copy.deepcopy(self.work))
        self.cfg.save()
        super().accept()
