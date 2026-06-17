import shutil
import sys
import json
from pathlib import Path


def app_folder() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


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
    folders = ["config", "data", "data/snapshots", "cache/icons", "assets/app", "assets/category_icons"]
    if not getattr(sys, "frozen", False):
        folders.append("release")
    for folder in folders:
        (app_folder() / folder).mkdir(parents=True, exist_ok=True)


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
    for path in [app_folder(), *app_folder().parents]:
        if path.name == "TQM Work Inside":
            return path
    desktop_root = Path.home() / "Desktop" / "TQM Work Inside"
    if desktop_root.exists() or (Path.home() / "Desktop").exists():
        return desktop_root
    return app_folder()


def _settings_file() -> Path:
    return app_folder() / "data" / "app_settings.json"


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

DATA_FILE = app_folder() / "data" / "tasks.json"
TEMPLATE_FILE = app_folder() / "data" / "templates.json"
APP_SETTINGS_FILE = _settings_file()
SETTINGS_LOG_FILE = app_folder() / "data" / "settings_log.json"
ACTIVITY_LOG_FILE = app_folder() / "data" / "activity_log.json"
UNDO_STACK_FILE = app_folder() / "data" / "undo_stack.json"
SNAPSHOT_DIR = app_folder() / "data" / "snapshots"
ICON_CACHE_DIR = app_folder() / "cache" / "icons"
APP_ICON_FILE = app_folder() / "assets" / "app" / "app.ico"
APP_LOGO_FILE = editable_resource_path("assets/app/app_logo.png")
