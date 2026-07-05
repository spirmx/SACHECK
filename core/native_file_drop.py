from __future__ import annotations

import ctypes
import os
import threading
import time
from ctypes import wintypes
from typing import Callable


WM_DROPFILES = 0x0233
WM_COPYGLOBALDATA = 0x0049
WM_COPYDATA = 0x004A
GWLP_WNDPROC = -4
MSGFLT_ALLOW = 1


class NativeFileDropBridge:
    """Windows Explorer file-drop bridge for Flet desktop windows."""

    def __init__(self, title_hint: str, on_files: Callable[[list[str]], None]):
        self.title_hint = str(title_hint or "").casefold()
        self.on_files = on_files
        self.hwnd = None
        self.old_proc = None
        self._wnd_proc = None
        self.error = ""

    def _find_window(self):
        user32 = ctypes.windll.user32
        current_pid = os.getpid()
        found = []
        enum_proc_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def inspect(hwnd, _lparam):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value != current_pid or not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, len(buffer))
            title = buffer.value.casefold()
            if not self.title_hint or self.title_hint in title:
                found.append(hwnd)
                return False
            return True

        callback = enum_proc_type(inspect)
        user32.EnumWindows(callback, 0)
        return found[0] if found else None

    def install(self, timeout: float = 12.0) -> bool:
        if os.name != "nt":
            return False
        try:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline and not self.hwnd:
                self.hwnd = self._find_window()
                if not self.hwnd:
                    time.sleep(0.25)
            if not self.hwnd:
                self.error = "SA CHECK window was not found."
                return False

            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32
            lresult = ctypes.c_ssize_t
            wnd_proc_type = ctypes.WINFUNCTYPE(lresult, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
            set_window_long = user32.SetWindowLongPtrW
            set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            set_window_long.restype = ctypes.c_void_p
            user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user32.CallWindowProcW.restype = lresult

            def window_proc(hwnd, message, wparam, lparam):
                if message == WM_DROPFILES:
                    paths = []
                    count = shell32.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                    for index in range(count):
                        length = shell32.DragQueryFileW(wparam, index, None, 0)
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        shell32.DragQueryFileW(wparam, index, buffer, len(buffer))
                        if buffer.value:
                            paths.append(buffer.value)
                    shell32.DragFinish(wparam)
                    if paths:
                        try:
                            self.on_files(paths)
                        except Exception:
                            pass
                    return 0
                return user32.CallWindowProcW(self.old_proc, hwnd, message, wparam, lparam)

            self._wnd_proc = wnd_proc_type(window_proc)
            self.old_proc = set_window_long(self.hwnd, GWLP_WNDPROC, ctypes.cast(self._wnd_proc, ctypes.c_void_p))
            if not self.old_proc:
                self.error = "Could not attach the Windows file-drop handler."
                return False
            change_filter = getattr(user32, "ChangeWindowMessageFilterEx", None)
            if change_filter:
                for message in (WM_DROPFILES, WM_COPYGLOBALDATA, WM_COPYDATA):
                    change_filter(self.hwnd, message, MSGFLT_ALLOW, None)
            shell32.DragAcceptFiles(self.hwnd, True)
            return True
        except Exception as exc:
            self.error = str(exc)
            return False


def install_native_file_drop(title_hint: str, on_files: Callable[[list[str]], None]) -> NativeFileDropBridge | None:
    if os.name != "nt":
        return None
    bridge = NativeFileDropBridge(title_hint, on_files)
    threading.Thread(target=bridge.install, name="sacheck-file-drop", daemon=True).start()
    return bridge
