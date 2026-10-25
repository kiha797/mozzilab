"""모찌PDF·모찌압축 등이 함께 쓰는 간단한 설정 저장소 (%APPDATA%\\<APP_ID>\\config.json)"""
import copy
import json
import os

BASE_DEFAULTS = {
    "device_id": "",           # 이 PC 고유번호 (로그인 기기 구분용)
    "account": {},             # 로그인 정보
    "capture_count": 0,        # 팝업 광고 빈도 계산용 (작업 완료 횟수)
    "last_dir": "",            # 마지막으로 연 폴더
    "geometry": None,          # 창 위치/크기
    "update_checked_at": "",   # 마지막 업데이트 확인 시각
    "update_skip": "",         # '이 버전 건너뛰기' 한 버전
}


def app_dir(app_id):
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, app_id)
    os.makedirs(path, exist_ok=True)
    return path


class AppConfig(dict):
    def __init__(self, app_id, defaults=None):
        super().__init__(copy.deepcopy({**BASE_DEFAULTS, **(defaults or {})}))
        self.path = os.path.join(app_dir(app_id), "config.json")
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in self:
                    self[k] = v
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(dict(self), f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def start_dir(self):
        d = self.get("last_dir") or ""
        return d if d and os.path.isdir(d) else os.path.expanduser("~")

    def remember_dir(self, path):
        if path:
            self["last_dir"] = path if os.path.isdir(path) else os.path.dirname(path)
            self.save()
