"""Windows 전용 기능 모음 (창 목록, 스크롤, 단축키, 자동 실행 등).
Windows 가 아닌 환경에서는 아무 일도 하지 않도록 만들어 두었다."""
import ctypes
import os
import sys

IS_WIN = sys.platform == "win32"

if IS_WIN:
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    dwmapi = ctypes.WinDLL("dwmapi")
    shell32 = ctypes.WinDLL("shell32")

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.EnumChildWindows.argtypes = [wintypes.HWND, WNDENUMPROC, wintypes.LPARAM]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                   wintypes.DWORD, ctypes.c_size_t]
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                             ctypes.c_void_p, wintypes.DWORD]
    dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long

if IS_WIN:
    gdi32 = ctypes.WinDLL("gdi32")

    class CURSORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
                    ("hCursor", wintypes.HANDLE), ("ptScreenPos", wintypes.POINT)]

    class ICONINFO(ctypes.Structure):
        _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD), ("yHotspot", wintypes.DWORD),
                    ("hbmMask", wintypes.HBITMAP), ("hbmColor", wintypes.HBITMAP)]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
                    ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

    user32.GetCursorInfo.argtypes = [ctypes.POINTER(CURSORINFO)]
    user32.GetIconInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ICONINFO)]
    user32.DrawIconEx.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HANDLE, ctypes.c_int,
                                  ctypes.c_int, wintypes.UINT, wintypes.HBRUSH, wintypes.UINT]
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.GetDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateDIBSection.argtypes = [wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
                                       ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]

DWMWA_EXTENDED_FRAME_BOUNDS = 9
DWMWA_CLOAKED = 14
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x20
WM_HOTKEY = 0x0312
VK_ESCAPE = 0x1B
VK_LBUTTON = 0x01

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000


def set_app_id(app_id):
    """작업표시줄에 파이썬 아이콘 대신 우리 프로그램 아이콘이 보이게 한다."""
    if IS_WIN:
        try:
            shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(app_id))
        except Exception:
            pass


def _rect(hwnd, use_dwm=True):
    r = wintypes.RECT()
    if use_dwm and dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(r), ctypes.sizeof(r)) == 0:
        return (r.left, r.top, r.right, r.bottom)
    if user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return (r.left, r.top, r.right, r.bottom)
    return None


def _cloaked(hwnd):
    v = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(v), ctypes.sizeof(v))
    return v.value != 0


def list_windows():
    """화면에 보이는 최상위 창 목록을 위(앞)에 있는 창부터 순서대로 돌려준다.
    결과: [(hwnd, (left, top, right, bottom)), ...]"""
    if not IS_WIN:
        return []
    my_pid = os.getpid()
    result = []

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd) or _cloaked(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == my_pid:
            return True
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TRANSPARENT:
            return True
        r = _rect(hwnd)
        if r and r[2] - r[0] >= 8 and r[3] - r[1] >= 8:
            result.append((hwnd, r))
        return True

    proc = WNDENUMPROC(callback)
    user32.EnumWindows(proc, 0)
    return result


def child_rects(hwnd):
    """창 안의 하위 영역(버튼, 입력칸, 패널 등) 목록 -> '단위영역' 캡처에 사용"""
    if not IS_WIN:
        return []
    result = []

    def callback(child, _):
        if user32.IsWindowVisible(child):
            r = _rect(child, use_dwm=False)
            if r and r[2] - r[0] >= 4 and r[3] - r[1] >= 4:
                result.append(r)
        return True

    proc = WNDENUMPROC(callback)
    user32.EnumChildWindows(hwnd, proc, 0)
    return result


def scroll_at(x, y, notches=-3):
    """(x, y) 위치로 마우스를 옮기고 휠을 굴린다. 음수 = 아래로"""
    if not IS_WIN:
        return
    user32.SetCursorPos(int(x), int(y))
    user32.mouse_event(0x0800, 0, 0, (120 * notches) & 0xFFFFFFFF, 0)


def cursor_bitmaps(size=128):
    """현재 마우스 커서 모양을 검은 배경/흰 배경에 각각 그린 BGRA 바이트를 돌려준다.
    결과: (검은배경 bytes, 흰배경 bytes, 크기, (핫스팟x, 핫스팟y), (화면x, 화면y)) 또는 None"""
    if not IS_WIN:
        return None
    ci = CURSORINFO()
    ci.cbSize = ctypes.sizeof(CURSORINFO)
    if not user32.GetCursorInfo(ctypes.byref(ci)) or not (ci.flags & 1) or not ci.hCursor:
        return None
    ii = ICONINFO()
    hot = (0, 0)
    if user32.GetIconInfo(ci.hCursor, ctypes.byref(ii)):
        hot = (ii.xHotspot, ii.yHotspot)
        for bm in (ii.hbmMask, ii.hbmColor):
            if bm:
                gdi32.DeleteObject(bm)
    screen_dc = user32.GetDC(None)
    mem_dc = gdi32.CreateCompatibleDC(screen_dc)
    bmi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), size, -size, 1, 32, 0, 0, 0, 0, 0, 0)
    bits = ctypes.c_void_p()
    dib = gdi32.CreateDIBSection(mem_dc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    result = None
    if dib and bits.value:
        old = gdi32.SelectObject(mem_dc, dib)
        n = size * size * 4
        layers = []
        for fill in (0, 255):
            ctypes.memset(bits, fill, n)
            user32.DrawIconEx(mem_dc, 0, 0, ci.hCursor, 0, 0, 0, None, 3)   # DI_NORMAL
            layers.append(ctypes.string_at(bits, n))
        gdi32.SelectObject(mem_dc, old)
        gdi32.DeleteObject(dib)
        result = (layers[0], layers[1], size, hot, (ci.ptScreenPos.x, ci.ptScreenPos.y))
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(None, screen_dc)
    return result


def key_down(vk):
    if not IS_WIN:
        return False
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def register_hotkey(hk_id, mods, vk):
    if not IS_WIN:
        return False
    return bool(user32.RegisterHotKey(None, hk_id, mods | MOD_NOREPEAT, vk))


def unregister_hotkey(hk_id):
    if IS_WIN:
        user32.UnregisterHotKey(None, hk_id)


def launch_command():
    """Windows 시작 시 실행할 명령어"""
    if getattr(sys, "frozen", False):          # exe 로 만든 경우
        return f'"{sys.executable}" --hidden'
    exe = sys.executable
    pyw = exe[:-10] + "pythonw.exe" if exe.lower().endswith("python.exe") else exe
    main = os.path.abspath(sys.argv[0])          # 지금 실행 중인 프로그램의 main.py
    return f'"{pyw}" "{main}" --hidden'


def set_autostart(enable, name="MochiCapture"):
    if not IS_WIN:
        return False
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, launch_command())
            else:
                try:
                    winreg.DeleteValue(key, name)
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False


def open_folder(path):
    if IS_WIN:
        os.startfile(path)
    else:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))
