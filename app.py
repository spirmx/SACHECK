import flet as ft
import ctypes
import sys

from ui.flet_dashboard import main
from core.app_lifecycle import SingleInstanceGuard, activate_existing_window

APP_USER_MODEL_ID = "Hoyturbro.SACHECK"
APP_NAME = "SA CHECK"


def configure_windows_app_id():
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def run():
    configure_windows_app_id()
    with SingleInstanceGuard() as instance:
        if instance.already_running:
            activate_existing_window(APP_NAME)
            return
        ft.run(main, name=APP_NAME, assets_dir="assets")


if __name__ == "__main__":
    run()
