"""압축 작업 모음 - ZIP(암호 AES 포함) · 7Z · TAR(GZ/BZ2/XZ) 열기·풀기·만들기
모든 작업 함수의 첫 번째 인자 report(퍼센트, 메시지)는 진행 상황을 알리는 함수다."""
import os
import tarfile
import zipfile
from dataclasses import dataclass
from datetime import datetime

import py7zr
import pyzipper

OPEN_EXTS = (".zip", ".7z", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")
FILTER = "압축 파일 (*.zip *.7z *.tar *.tar.gz *.tgz *.tar.bz2 *.tbz2 *.tar.xz *.txz)"
LEVELS = {"fast": 1, "normal": 6, "max": 9}


class ArchiveError(Exception):
    pass


class NeedPassword(ArchiveError):
    pass


@dataclass
class Entry:
    name: str           # 압축 안의 경로 (폴더 구분은 /)
    size: int
    packed: int
    mtime: datetime | None
    is_dir: bool
    encrypted: bool = False


def kind(path):
    p = path.lower()
    if p.endswith(".zip"):
        return "zip"
    if p.endswith(".7z"):
        return "7z"
    if p.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
        return "tar"
    raise ArchiveError("지원하지 않는 압축 형식입니다. (ZIP, 7Z, TAR 를 지원합니다)\n"
                       "RAR 파일은 아직 지원하지 않아요.")


def archive_stem(path):
    name = os.path.basename(path)
    for ext in sorted(OPEN_EXTS, key=len, reverse=True):
        if name.lower().endswith(ext):
            return name[: -len(ext)]
    return os.path.splitext(name)[0]


# ---------- 한글 파일 이름 ----------
def zip_name(info):
    """Windows 탐색기로 만든 ZIP 은 이름이 CP949(한글)로 저장돼 깨져 보인다 → 올바르게 바꿔 준다."""
    if info.flag_bits & 0x800:          # UTF-8 표시가 있으면 그대로
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp949")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def _safe_target(dest, name):
    """압축 파일 안의 '../../' 같은 위험한 경로가 폴더 밖으로 나가지 못하게 막는다."""
    name = name.replace("\\", "/").lstrip("/")
    target = os.path.realpath(os.path.join(dest, *[p for p in name.split("/") if p not in ("", ".")]))
    root = os.path.realpath(dest)
    if target != root and not target.startswith(root + os.sep):
        raise ArchiveError(f"위험한 경로가 들어 있어 건너뜁니다: {name}")
    return target


def _open7z(path, password):
    """7Z 열기. 암호가 틀리면 엉뚱한 오류가 나므로 '암호가 맞지 않습니다'로 바꿔 준다."""
    try:
        return py7zr.SevenZipFile(path, "r", password=password or None)
    except py7zr.exceptions.PasswordRequired:
        raise NeedPassword("암호가 걸린 압축 파일입니다.")
    except py7zr.exceptions.Bad7zFile as e:
        raise ArchiveError(f"압축 파일이 손상되었거나 열 수 없습니다.\n({e})")
    except Exception:          # noqa: BLE001
        if password:
            raise NeedPassword("암호가 맞지 않습니다.")
        raise


# ---------- 목록 ----------
def list_entries(path, password=None):
    k = kind(path)
    try:
        if k == "zip":
            with pyzipper.AESZipFile(path) as z:
                out = []
                for i in z.infolist():
                    out.append(Entry(zip_name(i).rstrip("/"), i.file_size, i.compress_size,
                                     datetime(*i.date_time) if i.date_time[0] > 1979 else None,
                                     i.is_dir(), bool(i.flag_bits & 0x1)))
                return out
        if k == "7z":
            with _open7z(path, password) as z:
                return [Entry(f.filename, f.uncompressed or 0, f.compressed or 0, f.creationtime, f.is_directory)
                        for f in z.list()]
        with tarfile.open(path) as t:
            return [Entry(m.name.rstrip("/"), m.size, m.size, datetime.fromtimestamp(m.mtime) if m.mtime else None,
                          m.isdir()) for m in t.getmembers()]
    except py7zr.exceptions.PasswordRequired:
        raise NeedPassword("암호가 걸린 압축 파일입니다.")
    except (zipfile.BadZipFile, tarfile.TarError, py7zr.exceptions.Bad7zFile) as e:
        raise ArchiveError(f"압축 파일이 손상되었거나 열 수 없습니다.\n({e})")


def is_encrypted(path):
    k = kind(path)
    if k == "zip":
        with pyzipper.AESZipFile(path) as z:
            return any(i.flag_bits & 0x1 for i in z.infolist())
    if k == "7z":
        try:
            with py7zr.SevenZipFile(path, "r") as z:
                return z.needs_password()
        except py7zr.exceptions.PasswordRequired:
            return True
    return False


# ---------- 풀기 ----------
def extract(report, path, dest, names=None, password=None):
    """압축 풀기. names 를 주면 그 항목(폴더면 안의 내용까지)만 푼다. 푼 개수를 돌려준다."""
    k = kind(path)
    os.makedirs(dest, exist_ok=True)

    def wanted(n):
        if not names:
            return True
        return any(n == w or n.startswith(w.rstrip("/") + "/") for w in names)

    count = 0
    try:
        if k == "zip":
            with pyzipper.AESZipFile(path) as z:
                if password:
                    z.setpassword(password.encode("utf-8"))
                infos = [i for i in z.infolist() if wanted(zip_name(i).rstrip("/"))]
                for n, info in enumerate(infos):
                    name = zip_name(info)
                    report(n * 100 / max(1, len(infos)), f"푸는 중: {name}")
                    target = _safe_target(dest, name)
                    if info.is_dir():
                        os.makedirs(target, exist_ok=True)
                        continue
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    try:
                        with z.open(info) as src, open(target, "wb") as out:
                            while chunk := src.read(1024 * 1024):
                                out.write(chunk)
                    except RuntimeError as e:
                        if "password" in str(e).lower() or "encrypted" in str(e).lower():
                            raise NeedPassword("암호가 필요하거나 암호가 맞지 않습니다.")
                        raise
                    if info.date_time[0] > 1979:
                        t = datetime(*info.date_time).timestamp()
                        os.utime(target, (t, t))
                    count += 1
        elif k == "7z":
            with _open7z(path, password) as z:
                all_names = [f.filename for f in z.list()]
                for nm in all_names:
                    _safe_target(dest, nm)
                targets = [nm for nm in all_names if wanted(nm)]
            report(10, "푸는 중… (7Z 는 한꺼번에 풉니다)")
            with _open7z(path, password) as z:
                if names:
                    z.extract(path=dest, targets=targets)
                else:
                    z.extractall(path=dest)
            count = len(targets)
        else:
            with tarfile.open(path) as t:
                members = [m for m in t.getmembers() if wanted(m.name.rstrip("/"))]
                for n, m in enumerate(members):
                    report(n * 100 / max(1, len(members)), f"푸는 중: {m.name}")
                    _safe_target(dest, m.name)
                    t.extract(m, dest, filter="data")
                    count += 0 if m.isdir() else 1
    except py7zr.exceptions.PasswordRequired:
        raise NeedPassword("암호가 걸린 압축 파일입니다.")
    except (zipfile.BadZipFile, tarfile.TarError, py7zr.exceptions.Bad7zFile) as e:
        raise ArchiveError(f"압축 파일이 손상되었거나 열 수 없습니다.\n({e})")
    except ArchiveError:
        raise
    except Exception as e:     # noqa: BLE001 - 7z 암호 오류 등
        if password or "password" in str(e).lower() or "crc" in str(e).lower():
            raise NeedPassword("암호가 맞지 않거나 파일이 손상되었습니다.")
        raise
    return count


# ---------- 만들기 ----------
def _walk(sources):
    """[(실제 경로, 압축 안 이름)] 목록. 폴더는 안의 파일까지 모두"""
    out = []
    for src in sources:
        src = os.path.abspath(src)
        base = os.path.dirname(src)
        if os.path.isdir(src):
            for root, dirs, files in os.walk(src):
                rel = os.path.relpath(root, base).replace(os.sep, "/")
                if not files and not dirs:
                    out.append((root, rel + "/"))
                for f in sorted(files):
                    full = os.path.join(root, f)
                    out.append((full, os.path.relpath(full, base).replace(os.sep, "/")))
        elif os.path.isfile(src):
            out.append((src, os.path.basename(src)))
    return out


def create(report, sources, out, fmt="zip", level="normal", password=""):
    """압축 파일 만들기. 만든 파일 경로를 돌려준다."""
    items = _walk(sources)
    if not items:
        raise ArchiveError("압축할 파일이나 폴더를 추가해 주세요.")
    out_abs = os.path.abspath(out)
    items = [(p, a) for p, a in items if os.path.abspath(p) != out_abs]     # 자기 자신은 제외
    os.makedirs(os.path.dirname(out_abs), exist_ok=True)
    total = sum(os.path.getsize(p) for p, a in items if not a.endswith("/")) or 1
    done = 0
    lv = LEVELS.get(level, 6)
    tmp = out_abs + ".part"
    try:
        if fmt == "7z":
            filters = [{"id": py7zr.FILTER_LZMA2, "preset": lv}]
            with py7zr.SevenZipFile(tmp, "w", filters=filters, password=password or None,
                                    header_encryption=bool(password)) as z:
                for p, arc in items:
                    report(done * 100 / total, f"압축 중: {arc}")
                    if arc.endswith("/"):
                        z.write(p, arc.rstrip("/"))
                    else:
                        z.write(p, arc)
                        done += os.path.getsize(p)
        else:
            kw = {"compression": pyzipper.ZIP_DEFLATED, "compresslevel": lv}
            if password:
                kw["encryption"] = pyzipper.WZ_AES
            with pyzipper.AESZipFile(tmp, "w", **kw) as z:
                if password:
                    z.setpassword(password.encode("utf-8"))
                for p, arc in items:
                    report(done * 100 / total, f"압축 중: {arc}")
                    if arc.endswith("/"):
                        z.writestr(arc, b"")             # 빈 폴더
                    else:
                        z.write(p, arc)
                        done += os.path.getsize(p)
        os.replace(tmp, out_abs)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return out_abs


def default_extract_dir(path):
    """원본 옆에 같은 이름의 폴더. 이미 있으면 (2), (3)…"""
    base = os.path.join(os.path.dirname(os.path.abspath(path)), archive_stem(path))
    cand, n = base, 2
    while os.path.exists(cand):
        cand = f"{base} ({n})"
        n += 1
    return cand
