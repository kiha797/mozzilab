"""설정값 저장/불러오기 + 최근 캡처 목록(히스토리) 관리"""
import copy
import glob
import json
import os
import shutil
from datetime import datetime

from brand import APP_ID, APP_NAME  # noqa: F401  (다른 파일에서 config.APP_NAME 으로 사용)

OLD_APP_ID = "DWCapture"        # 예전 이름(DW캡처) 시절 설정 폴더


def app_dir():
    """설정/히스토리가 저장되는 폴더 (예: C:\\Users\\홍길동\\AppData\\Roaming\\MochiCapture)"""
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, APP_ID)
    old = os.path.join(base, OLD_APP_ID)
    if not os.path.exists(path) and os.path.isdir(old):
        shutil.copytree(old, path)          # DW캡처에서 쓰던 설정·캡처목록을 그대로 가져온다
    os.makedirs(path, exist_ok=True)
    return path


def default_save_dir():
    return os.path.join(os.path.expanduser("~"), "Pictures", APP_NAME)


HOTKEY_MODES = ["region", "window", "unit", "full", "scroll", "fixed"]
DEFAULT_HOTKEYS = {
    "region": {"on": True, "win": False, "ctrl": True, "shift": True, "alt": False, "key": "C"},
    "window": {"on": True, "win": False, "ctrl": True, "shift": True, "alt": False, "key": "W"},
    "unit":   {"on": True, "win": False, "ctrl": True, "shift": True, "alt": False, "key": "D"},
    "full":   {"on": True, "win": False, "ctrl": True, "shift": True, "alt": False, "key": "A"},
    "scroll": {"on": True, "win": False, "ctrl": True, "shift": True, "alt": False, "key": "S"},
    "fixed":  {"on": True, "win": False, "ctrl": True, "shift": True, "alt": False, "key": "F"},
}

# 파일명 날짜 형식: (화면에 보이는 이름, strftime 형식)
NAME_DATE_FORMATS = [
    ("20261025_153000 (날짜_시간)", "%Y%m%d_%H%M%S"),
    ("2026-10-25 15-30-00", "%Y-%m-%d %H-%M-%S"),
    ("20261025 (날짜만)", "%Y%m%d"),
    ("사용 안 함", ""),
]

# ---- 환경설정 기본값 (화면별로 묶음. '기본값으로' 버튼에서 사용) ----
GENERAL_DEFAULTS = {
    "show_overlay": True,          # 캡처 시 화면 오버레이(어둡게) 표시
    "hide_launcher": False,        # 캡처 실행창 숨김 (트레이 클릭 시 메뉴로 대체)
    "save_dialog_after": False,    # 캡처 후 저장창 바로 띄우기
    "autostart": False,            # Windows 시작 시 자동 실행
    "close_to_tray": True,         # 종료(X) 버튼 클릭 시 트레이로 최소화
    "no_result_window": False,     # 캡처 후 결과창 띄우지 않기
    "auto_copy": True,             # 캡처한 내용을 항상 클립보드로 복사
    "save_notice": False,          # 캡처 이미지 저장완료 안내창 띄우기
    "include_cursor": False,       # 캡처할 때 마우스 커서 포함
    "guide_color": "#ff0000",      # 가이드라인(선택 영역 표시선) 색
    "keep_guide": False,           # 캡처 이미지에 선택 영역 표시선 유지
}
ADVANCED_DEFAULTS = {
    "save_format": "png",          # png / jpg / bmp
    "jpg_quality": 100,
    "name_prefix": "캡처",          # 파일명 앞부분
    "name_date": "%Y%m%d_%H%M%S",  # 파일명 날짜 형식
    "name_counter": False,         # 파일명 끝에 일련번호 붙이기
    "name_counter_next": 1,
    "auto_save": False,            # 자동저장 설정 사용
    "save_dir": "",                # 저장위치 (비어 있으면 '사진\모찌캡처')
    "fixed_presets": [],           # 크기지정 캡처 프리셋 [[가로, 세로], ...] 최대 6개
    "scroll_delay": 450,           # 스크롤 캡처 대기시간(ms)
}
HOTKEY_DEFAULTS = {
    "printscreen_on": True,        # PrintScreen 키 사용
    "printscreen_action": "region",  # PrintScreen 키 기능 (launcher/region/window/...)
    "hotkeys": DEFAULT_HOTKEYS,
}
HISTORY_DEFAULTS = {
    "confirm_clear": True,         # 목록 비우기 시 알림창 띄우기
    "notice_save_all": True,       # 목록 이미지 모두 저장 완료 안내창 띄우기
    "confirm_delete": True,        # 목록 이미지 삭제 시 알림창 띄우기
    "auto_prune": False,           # 목록이 가득 찼을 경우 오래된 이미지 자동 삭제
    "history_limit": 100,          # 최근 캡처 목록 최대 장수
}
PAGE_DEFAULTS = [GENERAL_DEFAULTS, ADVANCED_DEFAULTS, HOTKEY_DEFAULTS, HISTORY_DEFAULTS]

DEFAULTS = {
    **GENERAL_DEFAULTS, **ADVANCED_DEFAULTS, **HOTKEY_DEFAULTS, **HISTORY_DEFAULTS,
    "fixed_rect": None,        # 크기지정 창의 마지막 위치/크기 [x, y, w, h]
    "launcher_pos": None,      # 실행창 마지막 위치 [x, y]
    "editor_geometry": None,   # 결과창 마지막 위치/크기 [x, y, w, h]
    "last_mode": "region",
    "last_dialog_dir": "",     # 저장창에서 마지막으로 고른 폴더
    "device_id": "",           # 이 PC 고유번호 (로그인 기기 구분용)
    "account": {},             # 로그인 정보 {token, email, name, premium, expires_at, checked_at}
    "capture_count": 0,        # 팝업 광고 빈도 계산용
    "update_checked_at": "",   # 마지막 업데이트 확인 시각
    "update_skip": "",         # '이 버전 건너뛰기' 한 버전
    "first_run": True,
}


class Config(dict):
    def __init__(self):
        super().__init__(copy.deepcopy(DEFAULTS))
        self.path = os.path.join(app_dir(), "config.json")

    @classmethod
    def load(cls):
        cfg = cls()
        try:
            with open(cfg.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        for k, v in data.items():
            if k not in DEFAULTS:
                continue
            d = DEFAULTS[k]
            if d is not None and not isinstance(v, type(d)) and not (
                    isinstance(d, (int, float)) and isinstance(v, (int, float))):
                continue                     # 예전 버전 설정과 형식이 다르면 무시
            if k == "hotkeys":
                merged = copy.deepcopy(DEFAULT_HOTKEYS)
                for mode, hk in v.items():
                    if mode in merged and isinstance(hk, dict):
                        merged[mode].update(hk)
                v = merged
            cfg[k] = v
        return cfg

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(dict(self), f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def reset_page(self, page_defaults):
        for k, v in page_defaults.items():
            self[k] = copy.deepcopy(v)

    def save_dir(self):
        path = self.get("save_dir") or default_save_dir()
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            path = default_save_dir()
            os.makedirs(path, exist_ok=True)
        return path

    def preview_name(self, ext=None, counter=None):
        ext = ext or self.get("save_format", "png")
        parts = []
        if self.get("name_prefix", "").strip():
            parts.append(self["name_prefix"].strip())
        if self.get("name_date"):
            parts.append(datetime.now().strftime(self["name_date"]))
        if self.get("name_counter"):
            parts.append(f"{counter or int(self.get('name_counter_next', 1)):03d}")
        stem = "_".join(parts) or "캡처"
        for ch in '\\/:*?"<>|':
            stem = stem.replace(ch, "-")
        return f"{stem}.{ext}"

    def new_file_name(self, ext=None, folder=None):
        """파일명 설정 규칙대로 새 파일 이름을 만든다. folder 를 주면 겹치지 않게 (2), (3)..을 붙인다."""
        name = self.preview_name(ext)
        if self.get("name_counter"):
            self["name_counter_next"] = int(self.get("name_counter_next", 1)) + 1
            self.save()
        if folder:
            stem, e = os.path.splitext(name)
            n = 2
            while os.path.exists(os.path.join(folder, name)):
                name = f"{stem} ({n}){e}"
                n += 1
        return name


class History:
    """최근 캡처 목록. 캡처 이미지를 PNG 로 보관하고 최대 N장까지만 유지한다."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.folder = os.path.join(app_dir(), "history")
        os.makedirs(self.folder, exist_ok=True)

    @property
    def limit(self):
        return int(self.cfg.get("history_limit", 100))

    def files(self):
        """최신순 파일 목록"""
        return sorted(glob.glob(os.path.join(self.folder, "*.png")), reverse=True)

    def is_full(self):
        return len(self.files()) >= self.limit

    def add(self, qimage, prune=True):
        name = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3] + ".png"
        path = os.path.join(self.folder, name)
        qimage.save(path, "PNG")
        if prune:
            self.prune()
        return path

    def prune(self):
        for old in self.files()[self.limit:]:
            self.delete(old)

    def delete(self, path):
        try:
            os.remove(path)
        except OSError:
            pass

    def clear(self):
        for f in self.files():
            self.delete(f)

    def export(self, paths, folder):
        prefix = self.cfg.get("name_prefix", "").strip() or "캡처"
        for f in paths:
            stem = os.path.splitext(os.path.basename(f))[0]
            shutil.copy2(f, os.path.join(folder, f"{prefix}_{stem}.png"))
        return len(paths)
