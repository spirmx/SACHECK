import flet as ft
import ctypes
import sys

from core.app_paths import is_dev_runtime
from ui.flet_dashboard import main

APP_USER_MODEL_ID = "Hoyturbro.SACHECK.Dev" if is_dev_runtime() else "Hoyturbro.SACHECK"
APP_NAME = "SA CHECK DEV" if is_dev_runtime() else "SA CHECK"


def configure_windows_app_id():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


if __name__ == "__main__":
    configure_windows_app_id()
    ft.run(main, name=APP_NAME, assets_dir="assets")
