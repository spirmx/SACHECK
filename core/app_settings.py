import json
import sys
from datetime import datetime
from pathlib import Path

from core.app_paths import APP_SETTINGS_FILE, SETTINGS_LOG_FILE, app_folder

try:
    import winreg
except ImportError:
    winreg = None


STARTUP_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "SACHECK"
THEME_NAMES = {"Light", "Dark"}


def load_app_settings():
    default = {"theme": "Light", "launch_on_startup": False}
    if not APP_SETTINGS_FILE.exists():
        return default
    try:
        data = json.loads(APP_SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            default.update(data)
    except (OSError, json.JSONDecodeError):
        pass
    if default.get("theme") not in THEME_NAMES:
        default["theme"] = "Light"
    default["launch_on_startup"] = bool(default.get("launch_on_startup"))
    return default


def save_app_settings(settings):
    APP_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    APP_SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def read_settings_log(limit=80):
    if not SETTINGS_LOG_FILE.exists():
        return []
    try:
        data = json.loads(SETTINGS_LOG_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data[-limit:]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def add_settings_log(action, detail):
    logs = read_settings_log(limit=240)
    logs.append(
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "detail": detail,
        }
    )
    SETTINGS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_LOG_FILE.write_text(json.dumps(logs[-240:], ensure_ascii=False, indent=2), encoding="utf-8")


def clear_settings_log():
    SETTINGS_LOG_FILE.write_text("[]", encoding="utf-8")


def fingerprint_signature(fingerprint) -> str:
    try:
        return json.dumps(fingerprint, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        return ""


def startup_command():
    if getattr(sys, "frozen", False):
        target = Path(sys.executable).resolve()
        return f'"{target}"'
    release_exe = app_folder() / "release" / "SACHECK.exe"
    if release_exe.exists():
        return f'"{release_exe.resolve()}"'
    return f'"{Path(sys.executable).resolve()}" "{(app_folder() / "app.py").resolve()}"'


def is_startup_enabled():
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
        return bool(value)
    except OSError:
        return False


def set_startup_enabled(enabled):
    if winreg is None:
        return
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, STARTUP_VALUE_NAME)
            except OSError:
                pass
