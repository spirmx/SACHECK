import shutil
import sys
import json
import os
from pathlib import Path


def app_folder() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def user_data_folder() -> Path:
    root = os.environ.get("APPDATA")
    if root:
        return Path(root) / "SA CHECK"
    return Path.home() / "AppData" / "Roaming" / "SA CHECK"


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return app_folder() / relative_path


def editable_resource_path(relative_path: str) -> Path:
    external = app_folder() / relative_path
    if external.exists():
        return external
    return resource_path(relative_path)


def ensure_project_layout():
    folders = ["config", "assets/app", "assets/category_icons"]
    if not getattr(sys, "frozen", False):
        folders.extend(["data", "data/snapshots", "cache/icons", "release"])
    for folder in folders:
        (app_folder() / folder).mkdir(parents=True, exist_ok=True)
    for folder in ["data", "data/snapshots", "cache/icons", "cache/calendar"]:
        (user_data_folder() / folder).mkdir(parents=True, exist_ok=True)


def migrate_file_if_needed(old_relative: str, new_relative: str):
    old_path = app_folder() / old_relative
    new_path = app_folder() / new_relative
    if old_path.exists() and not new_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old_path), str(new_path))


def migrate_folder_contents_if_needed(old_relative: str, new_relative: str):
    old_path = app_folder() / old_relative
    new_path = app_folder() / new_relative
    if not old_path.exists() or not old_path.is_dir():
        return
    new_path.mkdir(parents=True, exist_ok=True)
    for item in old_path.iterdir():
        destination = new_path / item.name
        if destination.exists():
            continue
        shutil.move(str(item), str(destination))
    try:
        old_path.rmdir()
    except OSError:
        pass


def work_root() -> Path:
    return Path.home() / "Documents" / "SA CHECK Work"


def _settings_file() -> Path:
    return user_data_folder() / "data" / "app_settings.json"


def configured_work_folder() -> Path | None:
    path = _settings_file()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = str(data.get("work_folder_path") or "").strip()
    if not value:
        return None
    return Path(value).expanduser()


def work_folder() -> Path:
    return configured_work_folder() or (work_root() / "Work")


ensure_project_layout()
migrate_file_if_needed("tasks.json", "data/tasks.json")
migrate_file_if_needed("templates.json", "data/templates.json")
migrate_file_if_needed("app.ico", "assets/app/app.ico")
migrate_file_if_needed("assets/app_logo.png", "assets/app/app_logo.png")
migrate_folder_contents_if_needed("Icon_Cache", "cache/icons")

def migrate_user_file_if_needed(old_relative: str, new_relative: str):
    old_path = app_folder() / old_relative
    new_path = user_data_folder() / new_relative
    if old_path.exists() and not new_path.exists():
        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(old_path), str(new_path))


migrate_user_file_if_needed("data/tasks.json", "data/tasks.json")
migrate_user_file_if_needed("data/templates.json", "data/templates.json")
migrate_user_file_if_needed("data/app_settings.json", "data/app_settings.json")
migrate_user_file_if_needed("data/settings_log.json", "data/settings_log.json")
migrate_user_file_if_needed("data/activity_log.json", "data/activity_log.json")
migrate_user_file_if_needed("data/undo_stack.json", "data/undo_stack.json")
migrate_user_file_if_needed("data/calendar_events.json", "data/calendar_events.json")
migrate_user_file_if_needed("data/runtime_session.json", "data/runtime_session.json")

DATA_FILE = user_data_folder() / "data" / "tasks.json"
TEMPLATE_FILE = user_data_folder() / "data" / "templates.json"
APP_SETTINGS_FILE = _settings_file()
SETTINGS_LOG_FILE = user_data_folder() / "data" / "settings_log.json"
ACTIVITY_LOG_FILE = user_data_folder() / "data" / "activity_log.json"
UNDO_STACK_FILE = user_data_folder() / "data" / "undo_stack.json"
CALENDAR_FILE = user_data_folder() / "data" / "calendar_events.json"
CALENDAR_CACHE_FILE = user_data_folder() / "cache" / "calendar" / "calendar_events.json"
SESSION_FILE = user_data_folder() / "data" / "runtime_session.json"
SNAPSHOT_DIR = user_data_folder() / "data" / "snapshots"
ICON_CACHE_DIR = user_data_folder() / "cache" / "icons"
APP_ICON_FILE = app_folder() / "assets" / "app" / "app.ico"
APP_LOGO_FILE = editable_resource_path("assets/app/app_logo.png")
