from __future__ import annotations

import ctypes
import sys


ERROR_ALREADY_EXISTS = 183
SW_RESTORE = 9
MUTEX_NAME = r"Local\Hoyturbro.SACHECK.SingleInstance"


class SingleInstanceGuard:
    """Process-lifetime Windows mutex used to reject duplicate app launches."""

    def __init__(self, name: str = MUTEX_NAME):
        self.handle = None
        self.already_running = False
        if sys.platform != "win32":
            return
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        self.handle = kernel32.CreateMutexW(None, False, name)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.already_running = ctypes.get_last_error() == ERROR_ALREADY_EXISTS

    def close(self) -> None:
        if not self.handle or sys.platform != "win32":
            return
        ctypes.windll.kernel32.CloseHandle(self.handle)
        self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()


def activate_existing_window(title: str = "SA CHECK") -> bool:
    """Restore the existing main window when a second launch is attempted."""
    if sys.platform != "win32":
        return False
    user32 = ctypes.windll.user32
    found = {"handle": 0}

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visitor(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        if buffer.value.strip().casefold().startswith(title.casefold()):
            found["handle"] = hwnd
            return False
        return True

    user32.EnumWindows(visitor, 0)
    hwnd = found["handle"]
    if not hwnd:
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    return True
