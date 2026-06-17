import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from io import BytesIO
from datetime import date, datetime
from pathlib import Path
from tkinter import Menu, TclError, colorchooser, filedialog, messagebox
from urllib.parse import urlparse
from urllib.request import urlopen
try:
    import winreg
except ImportError:
    winreg = None

import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFont
from category_config import load_category_module, write_category_config
from core import file_intelligence
from core.app_paths import (
    APP_ICON_FILE,
    APP_LOGO_FILE,
    DATA_FILE,
    ICON_CACHE_DIR,
    TEMPLATE_FILE,
    app_folder,
    editable_resource_path,
    resource_path,
    work_root,
)
from core.app_settings import (
    add_settings_log,
    clear_settings_log,
    fingerprint_signature,
    is_startup_enabled,
    load_app_settings,
    read_settings_log,
    save_app_settings,
    set_startup_enabled,
    startup_command,
)
from core.create_tools import CREATE_TOOLS, create_project_folder, tool_default_name, write_blank_file
from stores import TaskStore, TemplateStore
from ui.virtual_list import DEFAULT_BATCH_SIZE, next_visible_limit, visible_slice
try:
    from config.category import CATEGORIES as DEFAULT_CATEGORIES
    from config.category import CATEGORY_ICON_DIR as DEFAULT_CATEGORY_ICON_DIR
    from config.category import EXTENSION_TYPES as DEFAULT_EXTENSION_TYPES
    from config.category import URL_RULES as DEFAULT_URL_RULES
except ImportError:
    from category import CATEGORIES as DEFAULT_CATEGORIES
    from category import CATEGORY_ICON_DIR as DEFAULT_CATEGORY_ICON_DIR
    from category import EXTENSION_TYPES as DEFAULT_EXTENSION_TYPES
    from category import URL_RULES as DEFAULT_URL_RULES

try:
    import win32con
    import win32clipboard
    import win32gui
    import win32ui
    from win32com.shell import shell, shellcon
except ImportError:
    win32con = None
    win32clipboard = None
    win32gui = None
    win32ui = None
    shell = None
    shellcon = None


APP_TITLE = "SACHECK"
TASK_BATCH_SIZE = DEFAULT_BATCH_SIZE
RENDER_BATCH_SIZE = 10
SYNC_INTERVAL_MS = 7000
SEARCH_DEBOUNCE_MS = 300
RESIZE_DEBOUNCE_MS = 120
STATUS_PENDING = "pending"
STATUS_PROGRESS = "progress"
STATUS_DONE = "done"

STATUSES = [
    (STATUS_PENDING, "Waiting"),
    (STATUS_PROGRESS, "Doing"),
    (STATUS_DONE, "Success"),
]

STATUS_META = {
    STATUS_PENDING: {"folder": "Waiting", "color": "#0284c7", "bg": "#f0f9ff", "icon": "WAIT"},
    STATUS_PROGRESS: {"folder": "Doing", "color": "#d97706", "bg": "#fffbeb", "icon": "DO"},
    STATUS_DONE: {"folder": "Success", "color": "#059669", "bg": "#ecfdf5", "icon": "OK"},
}

SMART_VIEWS = {
    "All work": {},
    "Doing now": {"status": STATUS_PROGRESS},
    "Done today": {"status": "today"},
    "Needs fix": {"status": "mismatch"},
    "Links": {"kind": "url"},
    "Projects": {"kind": "folder"},
    "Old doing": {"status": STATUS_PROGRESS, "age_min": 3},
}

SORT_OPTIONS = [
    "Newest first",
    "Oldest first",
    "Name A-Z",
    "Type",
    "Status",
    "Needs fix first",
]

FILE_TYPES = DEFAULT_CATEGORIES
CATEGORY_ICON_DIR = DEFAULT_CATEGORY_ICON_DIR
EXTENSION_TYPES = DEFAULT_EXTENSION_TYPES
URL_RULES = DEFAULT_URL_RULES

THEME_PALETTES = {
    "Light": {
        "bg": "#eef6ff",           # Blue-tinted shell
        "surface": "#ffffff",      # White
        "surface_2": "#f6f9ff",    # Cool canvas
        "surface_3": "#dbeafe",    # Blue 100
        "border": "#b7ccef",       # Blue gray
        "border_soft": "#d7e4f8",  # Soft blue
        "text": "#0f172a",         # Slate 900
        "muted": "#52637a",        # Ink muted
        "muted_2": "#7f91aa",      # Ink soft
        "nav": "#082f49",          # Sky 950
        "nav_text": "#ffffff",     # White
    },
    "Dark": {
        "bg": "#07111f",           # Deep blue shell
        "surface": "#101827",      # Ink panel
        "surface_2": "#17243a",    # Ink field
        "surface_3": "#0b1220",    # Deep panel
        "border": "#315172",       # Blue edge
        "border_soft": "#213650",  # Soft edge
        "text": "#f8fafc",         # Slate 50
        "muted": "#a8b6ca",        # Cool muted
        "muted_2": "#72839a",      # Cool soft
        "nav": "#030b16",          # Blue black
        "nav_text": "#f8fafc",     # Slate 50
    },
}


DETAIL_BUTTONS = {
    "open": ("#4f46e5", "#4338ca", "#ffffff"),
    "edit": ("#7c3aed", "#6d28d9", "#ffffff"),
    "folder": ("#0f172a", "#1e293b", "#ffffff"),
}

UI_BG = THEME_PALETTES["Light"]["bg"]
UI_SURFACE = THEME_PALETTES["Light"]["surface"]
UI_SURFACE_2 = THEME_PALETTES["Light"]["surface_2"]
UI_SURFACE_3 = THEME_PALETTES["Light"]["surface_3"]
UI_BORDER = THEME_PALETTES["Light"]["border"]
UI_BORDER_SOFT = THEME_PALETTES["Light"]["border_soft"]
UI_TEXT = THEME_PALETTES["Light"]["text"]
UI_MUTED = THEME_PALETTES["Light"]["muted"]
UI_MUTED_2 = THEME_PALETTES["Light"]["muted_2"]
UI_NAV = THEME_PALETTES["Light"]["nav"]
UI_NAV_TEXT = THEME_PALETTES["Light"]["nav_text"]



def load_external_categories():
    global FILE_TYPES, CATEGORY_ICON_DIR, EXTENSION_TYPES, URL_RULES
    category_path = app_folder() / "config" / "category.py"
    if not category_path.exists() and (app_folder() / "category.py").exists():
        category_path = app_folder() / "category.py"
    try:
        module = load_category_module(category_path)
        if module is None:
            return
        FILE_TYPES = getattr(module, "CATEGORIES", FILE_TYPES)
        CATEGORY_ICON_DIR = getattr(module, "CATEGORY_ICON_DIR", CATEGORY_ICON_DIR)
        EXTENSION_TYPES = getattr(module, "EXTENSION_TYPES", EXTENSION_TYPES)
        URL_RULES = getattr(module, "URL_RULES", URL_RULES)
    except Exception:
        pass


def save_category_config(categories=None, extension_types=None, url_rules=None, icon_dir=None):
    categories = categories or FILE_TYPES
    extension_types = extension_types or EXTENSION_TYPES
    url_rules = url_rules or URL_RULES
    icon_dir = icon_dir or CATEGORY_ICON_DIR
    category_path = app_folder() / "config" / "category.py"
    return write_category_config(category_path, categories, extension_types, url_rules, icon_dir)


def apply_category_settings(categories, extension_types, url_rules, icon_dir=None):
    global FILE_TYPES, CATEGORY_ICON_DIR, EXTENSION_TYPES, URL_RULES
    FILE_TYPES = dict(categories)
    CATEGORY_ICON_DIR = icon_dir or CATEGORY_ICON_DIR
    EXTENSION_TYPES = dict(extension_types)
    URL_RULES = [dict(rule) for rule in url_rules]
    rebuild_url_extension_types()


STATUS_FOLDERS = {
    status: meta["folder"] for status, meta in STATUS_META.items()
}



def apply_theme(theme_name):
    global UI_BG, UI_SURFACE, UI_SURFACE_2, UI_SURFACE_3, UI_BORDER, UI_BORDER_SOFT
    global UI_TEXT, UI_MUTED, UI_MUTED_2, UI_NAV, UI_NAV_TEXT
    palette = THEME_PALETTES.get(theme_name, THEME_PALETTES["Light"])
    UI_BG = palette["bg"]
    UI_SURFACE = palette["surface"]
    UI_SURFACE_2 = palette["surface_2"]
    UI_SURFACE_3 = palette["surface_3"]
    UI_BORDER = palette["border"]
    UI_BORDER_SOFT = palette["border_soft"]
    UI_TEXT = palette["text"]
    UI_MUTED = palette["muted"]
    UI_MUTED_2 = palette["muted_2"]
    UI_NAV = palette["nav"]
    UI_NAV_TEXT = palette["nav_text"]
    ctk.set_appearance_mode(theme_name.lower())


def form_theme():
    return {
        "body": UI_SURFACE,
        "field": UI_SURFACE_2 if UI_SURFACE != "#ffffff" else "#ffffff",
        "field_hover": UI_SURFACE_3,
        "label": UI_MUTED,
        "text": UI_TEXT,
        "border": UI_BORDER,
        "border_soft": UI_BORDER_SOFT,
        "neutral": UI_SURFACE_2,
        "neutral_hover": UI_SURFACE_3,
        "neutral_text": UI_TEXT,
    }



def rebuild_url_extension_types():
    global URL_EXTENSION_TYPES
    URL_EXTENSION_TYPES = {
        **EXTENSION_TYPES,
        ".doc?": "Word",
        ".xls?": "Excel",
        ".ppt?": "Slide",
    }


load_external_categories()
rebuild_url_extension_types()


def is_url(target: str) -> bool:
    return target.lower().startswith(("http://", "https://"))


def is_local_file(target: str) -> bool:
    return bool(target) and not is_url(target)


def ensure_status_folders():
    for file_type in FILE_TYPES:
        for folder_name in STATUS_FOLDERS.values():
            (work_root() / "Work" / file_type / folder_name).mkdir(parents=True, exist_ok=True)
        template_folder(file_type).mkdir(parents=True, exist_ok=True)


def status_folder(status: str, file_type: str = "Other") -> Path:
    safe_type = file_type if file_type in FILE_TYPES else "Other"
    return work_root() / "Work" / safe_type / STATUS_FOLDERS.get(status, STATUS_FOLDERS[STATUS_PENDING])


def template_folder(file_type: str = "Other") -> Path:
    safe_type = file_type if file_type in FILE_TYPES else "Other"
    return work_root() / "Work" / safe_type / "Template"


def is_canonical_template_path(path: str, file_type: str = "Other") -> bool:
    if not path or is_url(path):
        return False
    try:
        return Path(path).parent.resolve() == template_folder(file_type).resolve()
    except OSError:
        return False


def read_url_shortcut_target(path: Path) -> str:
    return file_intelligence.read_url_shortcut_target(path)


def infer_type_from_url(target: str) -> str:
    return file_intelligence.infer_type_from_url(target, URL_EXTENSION_TYPES, URL_RULES)


def infer_type_from_folder(path: Path) -> str:
    return file_intelligence.infer_type_from_folder(path)


def infer_type_from_file_signature(path: Path) -> str:
    return file_intelligence.infer_type_from_file_signature(path)


def infer_type_from_path(path: str) -> str:
    return file_intelligence.infer_type_from_path(path, EXTENSION_TYPES, URL_EXTENSION_TYPES, URL_RULES)


def infer_type_from_target(target: str) -> str:
    return file_intelligence.infer_type_from_target(target, EXTENSION_TYPES, URL_EXTENSION_TYPES, URL_RULES)


def detect_project_stack(target: str) -> str:
    return file_intelligence.detect_project_stack(target)


def unique_destination(folder: Path, filename: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / filename
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    counter = 2
    while True:
        candidate = folder / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def is_valid_category_name(name: str) -> bool:
    if not name or name in (".", ".."):
        return False
    invalid = set('<>:"/\\|?*')
    return not any(char in invalid for char in name)


def move_folder_contents(source: Path, destination: Path):
    if not source.exists() or not source.is_dir():
        return
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = unique_destination(destination, item.name)
        shutil.move(str(item), str(target))
    try:
        source.rmdir()
    except OSError:
        pass


def move_category_files(source_type: str, destination_type: str):
    if source_type == destination_type:
        return
    source_root = work_root() / "Work" / source_type
    if not source_root.exists():
        return
    for folder_name in [*STATUS_FOLDERS.values(), "Template"]:
        move_folder_contents(source_root / folder_name, work_root() / "Work" / destination_type / folder_name)
    try:
        source_root.rmdir()
    except OSError:
        pass


def move_file_to_status_folder(target: str, status: str, file_type: str = "Other") -> str:
    if not is_local_file(target):
        return target

    source = Path(target)
    if not source.exists() or not (source.is_file() or source.is_dir()):
        raise FileNotFoundError(f"File/folder not found: {target}")

    destination_folder = status_folder(status, file_type)
    destination_folder.mkdir(parents=True, exist_ok=True)

    if source.parent.resolve() == destination_folder.resolve():
        return str(source)

    destination = unique_destination(destination_folder, source.name)
    shutil.move(str(source), str(destination))
    return str(destination)


def safe_filename(name: str) -> str:
    cleaned = "".join("_" if char in '<>:"/\\|?*' else char for char in name).strip()
    cleaned = cleaned.rstrip(". ")
    return cleaned or "Untitled"


def rename_local_file_to_task_name(target: str, task_name: str) -> str:
    if not target or is_url(target):
        return target
    source = Path(target)
    if not source.exists() or not (source.is_file() or source.is_dir()):
        return target

    desired_name = safe_filename(task_name) if source.is_dir() else f"{safe_filename(task_name)}{source.suffix}"
    if desired_name == source.name:
        return str(source)

    destination = source.with_name(desired_name)
    try:
        if destination.exists() and destination.resolve() != source.resolve():
            destination = unique_destination(source.parent, desired_name)
        shutil.move(str(source), str(destination))
        return str(destination)
    except OSError:
        return str(source)


def write_url_shortcut(task, status: str) -> str:
    folder = status_folder(status, task.get("type", "Other"))
    folder.mkdir(parents=True, exist_ok=True)
    shortcut_name = f"{safe_filename(task.get('name', 'Untitled'))}.url"
    previous = task.get("shortcut_path")
    destination = folder / shortcut_name

    if previous:
        previous_path = Path(previous)
        if previous_path.exists() and previous_path.resolve() != destination.resolve():
            destination = unique_destination(folder, shortcut_name)
            shutil.move(str(previous_path), str(destination))
    elif destination.exists():
        destination = unique_destination(folder, shortcut_name)

    destination.write_text(
        "[InternetShortcut]\n"
        f"URL={task.get('link', '').strip()}\n"
        f"; Task={task.get('name', 'Untitled')}\n"
        f"; Type={task.get('type', 'Other')}\n"
        f"; Status={STATUS_FOLDERS.get(status, STATUS_FOLDERS[STATUS_PENDING])}\n",
        encoding="utf-8",
    )
    return str(destination)


def write_template_url_shortcut(template) -> str:
    folder = template_folder(template.get("type", "Other"))
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{safe_filename(template.get('name', 'Untitled'))}.url"
    if template.get("shortcut_path"):
        previous = Path(template["shortcut_path"])
        if previous.exists() and previous.resolve() != destination.resolve():
            destination = unique_destination(folder, destination.name)
            shutil.move(str(previous), str(destination))
    elif destination.exists():
        destination = unique_destination(folder, destination.name)

    destination.write_text(
        "[InternetShortcut]\n"
        f"URL={template.get('link', '').strip()}\n"
        f"; Template={template.get('name', 'Untitled')}\n"
        f"; Type={template.get('type', 'Other')}\n",
        encoding="utf-8",
    )
    return str(destination)


def copy_file_to_template_folder(template) -> str:
    target = template.get("link", "").strip()
    if not target or is_url(target):
        return target
    source = Path(target)
    if not source.exists() or not (source.is_file() or source.is_dir()):
        raise FileNotFoundError(f"File/folder not found: {target}")
    folder = template_folder(template.get("type", "Other"))
    folder.mkdir(parents=True, exist_ok=True)
    if source.parent.resolve() == folder.resolve():
        return str(source)
    destination = unique_destination(folder, source.name)
    if source.is_dir():
        shutil.copytree(str(source), str(destination))
    else:
        shutil.copy2(str(source), str(destination))
    return str(destination)


def organize_task_target(task, status: str):
    target = task.get("link", "").strip()
    patch = {}
    if not target:
        return patch

    if task.get("target_kind") == "url" or is_url(target):
        patch["shortcut_path"] = write_url_shortcut(task, status)
        patch["target_kind"] = "url"
        detected = infer_type_from_target(target)
        patch["detected_type"] = detected
        patch["category_mismatch"] = detected_type_mismatch(task.get("type", "Other"), detected)
        patch["file_key"] = normalized_file_key(patch["shortcut_path"])
        return patch

    file_type = task.get("type", "Other")
    moved_path = move_file_to_status_folder(target, status, file_type)
    patch["link"] = rename_local_file_to_task_name(moved_path, task.get("name", "Untitled"))
    patch["shortcut_path"] = None
    patch["target_kind"] = "folder" if Path(patch["link"]).is_dir() else "file"
    detected = infer_type_from_target(patch["link"])
    patch["detected_type"] = detected
    patch["category_mismatch"] = detected_type_mismatch(file_type, detected)
    patch["file_key"] = normalized_file_key(patch["link"])
    patch["project_stack"] = detect_project_stack(patch["link"]) if Path(patch["link"]).is_dir() else ""
    return patch


def organize_template_target(template):
    target = template.get("link", "").strip()
    patch = {}
    if not target:
        return patch
    if template.get("target_kind") == "url" or is_url(target):
        patch["shortcut_path"] = write_template_url_shortcut(template)
        patch["target_kind"] = "url"
        return patch
    template_path = copy_file_to_template_folder(template)
    patch["link"] = rename_local_file_to_task_name(template_path, template.get("name", "Untitled"))
    patch["shortcut_path"] = None
    patch["target_kind"] = "file"
    return patch


def item_exists(item) -> bool:
    target = item.get("link", "").strip()
    if item.get("target_kind") == "url" or is_url(target):
        shortcut = item.get("shortcut_path")
        return not shortcut or Path(shortcut).exists()
    return bool(target) and Path(target).exists()


def normalized_file_key(path: str) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve()).casefold()
    except OSError:
        return str(path).casefold()


def folder_tree_fingerprint(root: Path):
    if not root.exists():
        return ()
    signature = []
    folders = []
    for file_type in FILE_TYPES:
        for folder_name in [*STATUS_FOLDERS.values(), "Template"]:
            folders.append(root / file_type / folder_name)
    for folder in folders:
        if not folder.exists():
            continue
        try:
            folder_stat = folder.stat()
            signature.append((str(folder).casefold(), "folder", int(folder_stat.st_mtime_ns), 0))
            for item in folder.iterdir():
                if item.name.startswith("~$"):
                    continue
                stat = item.stat()
                kind = "dir" if item.is_dir() else "file"
                size = 0 if item.is_dir() else int(stat.st_size)
                signature.append((str(item).casefold(), kind, int(stat.st_mtime_ns), size))
        except OSError:
            continue
    return tuple(sorted(signature))


def task_file_key(task) -> str:
    if task.get("target_kind") == "url":
        return normalized_file_key(task.get("shortcut_path") or task.get("link", ""))
    return normalized_file_key(task.get("link", ""))


def detected_type_mismatch(folder_type: str, detected_type: str) -> bool:
    if not detected_type or detected_type in ("Other",):
        return False
    return folder_type in FILE_TYPES and detected_type in FILE_TYPES and folder_type != detected_type


def scan_work_folder_tasks():
    tasks = []
    root = work_root() / "Work"
    if not root.exists():
        return tasks

    for file_type in FILE_TYPES:
        for status, folder_name in STATUS_FOLDERS.items():
            folder = root / file_type / folder_name
            if not folder.exists():
                continue
            for file_path in folder.iterdir():
                if not (file_path.is_file() or file_path.is_dir()) or file_path.name.startswith("~$"):
                    continue
                if file_path.is_file() and file_path.suffix.lower() == ".url":
                    url_target = read_url_shortcut_target(file_path)
                    detected_type = infer_type_from_target(url_target) if url_target else "Link"
                    target_kind = "url"
                    link = url_target or str(file_path)
                    shortcut_path = str(file_path)
                else:
                    detected_type = infer_type_from_target(str(file_path))
                    target_kind = "folder" if file_path.is_dir() else "file"
                    link = str(file_path)
                    shortcut_path = None

                tasks.append(
                    {
                        "name": file_path.stem,
                        "type": file_type,
                        "detected_type": detected_type,
                        "project_stack": detect_project_stack(str(file_path)) if file_path.is_dir() else "",
                        "category_mismatch": detected_type_mismatch(file_type, detected_type),
                        "link": link,
                        "target_kind": target_kind,
                        "shortcut_path": shortcut_path,
                        "note": "",
                        "status": status,
                        "date_added": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "done_date": date.today().isoformat() if status == STATUS_DONE else None,
                        "source": "folder_scan",
                        "file_key": normalized_file_key(str(file_path)),
                    }
                )
    return tasks


def scan_template_folder_items():
    templates = []
    root = work_root() / "Work"
    if not root.exists():
        return templates

    for file_type in FILE_TYPES:
        folder = root / file_type / "Template"
        if not folder.exists():
            continue
        for file_path in folder.iterdir():
            if not (file_path.is_file() or file_path.is_dir()) or file_path.name.startswith("~$"):
                continue
            if file_path.is_file() and file_path.suffix.lower() == ".url":
                url_target = read_url_shortcut_target(file_path)
                detected_type = infer_type_from_target(url_target) if url_target else "Link"
                templates.append(
                    {
                        "name": file_path.stem,
                        "type": file_type,
                        "detected_type": detected_type,
                        "project_stack": detect_project_stack(str(file_path)) if file_path.is_dir() else "",
                        "category_mismatch": detected_type_mismatch(file_type, detected_type),
                        "link": url_target or str(file_path),
                        "target_kind": "url",
                        "shortcut_path": str(file_path),
                        "date_added": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "source": "template_folder_scan",
                        "file_key": normalized_file_key(str(file_path)),
                    }
                )
            else:
                detected_type = infer_type_from_target(str(file_path))
                templates.append(
                    {
                        "name": file_path.stem,
                        "type": file_type,
                        "detected_type": detected_type,
                        "category_mismatch": detected_type_mismatch(file_type, detected_type),
                        "link": str(file_path),
                        "target_kind": "folder" if file_path.is_dir() else "file",
                        "shortcut_path": None,
                        "date_added": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "source": "template_folder_scan",
                        "file_key": normalized_file_key(str(file_path)),
                    }
                )
    return templates


def blend_color(hex_color: str, other: str = "#ffffff", amount: float = 0.25) -> str:
    left = hex_color.lstrip("#")
    right = other.lstrip("#")
    parts = []
    for index in (0, 2, 4):
        base = int(left[index:index + 2], 16)
        target = int(right[index:index + 2], 16)
        parts.append(round(base + (target - base) * amount))
    return "#" + "".join(f"{part:02x}" for part in parts)


def adjust_color(hex_color: str, amount: int = 0) -> str:
    color = normalize_hex_color(hex_color)
    value = color.lstrip("#")
    parts = []
    for index in (0, 2, 4):
        channel = max(0, min(255, int(value[index:index + 2], 16) + amount))
        parts.append(channel)
    return "#" + "".join(f"{part:02x}" for part in parts)


def best_text_color(hex_color: str) -> str:
    color = normalize_hex_color(hex_color).lstrip("#")
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    brightness = (red * 299 + green * 587 + blue * 114) / 1000
    return "#0f172a" if brightness > 150 else "#ffffff"


def center_toplevel(window, master, width: int, height: int):
    try:
        master.update_idletasks()
        x = master.winfo_x() + max(0, (master.winfo_width() - width) // 2)
        y = master.winfo_y() + max(0, (master.winfo_height() - height) // 2)
    except Exception:
        x = (window.winfo_screenwidth() - width) // 2
        y = (window.winfo_screenheight() - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def focus_and_select(entry):
    entry.focus_set()
    try:
        entry.select_range(0, "end")
    except Exception:
        pass


def load_icon_font(font_size: int, bold: bool = True):
    from PIL import ImageFont

    if bold:
        candidates = ("segoeuib.ttf", "tahomabd.ttf", "arialbd.ttf")
    else:
        candidates = ("segoeui.ttf", "tahoma.ttf", "arial.ttf")
    for name in candidates:
        try:
            return ImageFont.truetype(name, font_size)
        except Exception:
            continue
    return ImageFont.load_default()


def normalize_hex_color(value: str, fallback: str = "#2563eb") -> str:
    value = (value or "").strip()
    if not value:
        return fallback
    if not value.startswith("#"):
        value = f"#{value}"
    if len(value) == 4:
        value = "#" + "".join(char * 2 for char in value[1:])
    if len(value) != 7:
        return fallback
    try:
        int(value[1:], 16)
    except ValueError:
        return fallback
    return value.lower()


def cache_key(value: str) -> str:
    return safe_filename(value.lower().replace("://", "_"))[:80]


def fetch_favicon(url: str) -> Image.Image | None:
    parsed = urlparse(url)
    domain = parsed.netloc
    if not domain:
        return None
    ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = ICON_CACHE_DIR / f"web_{cache_key(domain)}.png"
    if cache_path.exists():
        return Image.open(cache_path).convert("RGBA")
    favicon_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"
    with urlopen(favicon_url, timeout=4) as response:
        image = Image.open(BytesIO(response.read())).convert("RGBA")
    image.save(cache_path)
    return image


def extract_windows_icon(path: str) -> Image.Image | None:
    if not all([win32con, win32gui, win32ui, shell, shellcon]):
        return None

    flags = shellcon.SHGFI_ICON | shellcon.SHGFI_LARGEICON
    info = shell.SHGetFileInfo(path, 0, flags)
    hicon = info[0]
    if not hicon:
        return None

    size = 32
    hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    mem_dc = hdc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(hdc, size, size)
    old_bitmap = mem_dc.SelectObject(bitmap)
    win32gui.DrawIconEx(mem_dc.GetHandleOutput(), 0, 0, hicon, size, size, 0, None, win32con.DI_NORMAL)
    bmp_info = bitmap.GetInfo()
    bmp_bits = bitmap.GetBitmapBits(True)
    image = Image.frombuffer(
        "RGBA",
        (bmp_info["bmWidth"], bmp_info["bmHeight"]),
        bmp_bits,
        "raw",
        "BGRA",
        0,
        1,
    )
    mem_dc.SelectObject(old_bitmap)
    win32gui.DestroyIcon(hicon)
    mem_dc.DeleteDC()
    hdc.DeleteDC()
    return image


def ensure_app_icon() -> Path:
    if APP_ICON_FILE.exists():
        return APP_ICON_FILE

    ICON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if APP_LOGO_FILE.exists():
        logo = Image.open(APP_LOGO_FILE).convert("RGBA")
        logo = logo.resize((256, 256), Image.Resampling.LANCZOS)
        logo.save(APP_ICON_FILE, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        return APP_ICON_FILE

    from PIL import ImageDraw

    scale = 4
    canvas = 256 * scale
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(values):
        return tuple(int(value * scale) for value in values)

    def rounded(values, radius, fill, outline=None, width=1):
        draw.rounded_rectangle(
            box(values),
            radius=int(radius * scale),
            fill=fill,
            outline=outline,
            width=int(width * scale),
        )

    # Clean, readable SA app mark with a subtle work-board accent.
    rounded((24, 30, 238, 242), 50, (0, 0, 0, 105))
    rounded((18, 18, 238, 238), 50, "#0f172a")
    for y in range(18 * scale, 238 * scale):
        ratio = (y - 18 * scale) / (220 * scale)
        r = int(37 + (29 - 37) * ratio)
        g = int(99 + (78 - 99) * ratio)
        b = int(235 + (216 - 235) * ratio)
        draw.line((18 * scale, y, 238 * scale, y), fill=(r, g, b, 255), width=1)
    rounded((18, 18, 238, 238), 50, None, outline=(147, 197, 253, 150), width=2)
    rounded((48, 52, 208, 210), 34, (7, 17, 31, 210))
    rounded((66, 184, 100, 198), 6, "#38bdf8")
    rounded((112, 184, 146, 198), 6, "#facc15")
    rounded((158, 184, 192, 198), 6, "#22c55e")

    small_font = load_icon_font(30 * scale)
    big_font = load_icon_font(86 * scale)
    draw.text((62 * scale, 72 * scale), "SA", fill="#ffffff", font=big_font)
    draw.text((145 * scale, 58 * scale), "IT", fill="#bfdbfe", font=small_font)

    image = image.resize((256, 256), Image.Resampling.LANCZOS)
    image.save(APP_ICON_FILE, sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    return APP_ICON_FILE


def make_file_type_icon(file_type: str, size: int = 44) -> Image.Image:
    # Try loading a real icon from the assets folder first
    meta = FILE_TYPES.get(file_type, FILE_TYPES["Other"])
    icon_file = meta.get("icon_file")
    if icon_file:
        icon_path = editable_resource_path(str(Path(CATEGORY_ICON_DIR) / icon_file))
        if icon_path.exists():
            try:
                img = Image.open(icon_path).convert("RGBA")
                return img.resize((size, size), Image.Resampling.LANCZOS)
            except Exception:
                pass

    asset_name = file_type.lower().replace(" ", "_")
    for ext in [".png", ".jpg", ".webp"]:
        asset_path = app_folder() / "assets" / f"{asset_name}{ext}"
        if asset_path.exists():
            try:
                img = Image.open(asset_path).convert("RGBA")
                return img.resize((size, size), Image.Resampling.LANCZOS)
            except Exception:
                continue

    from PIL import ImageDraw

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    color = meta["color"]
    draw.rounded_rectangle((2, 2, size - 2, size - 2), radius=10, fill=color)
    draw.rounded_rectangle((8, 8, size - 8, size - 8), radius=7, fill=blend_color(color, "#000000", 0.18))
    text = meta["icon"]
    font_size = 18 if len(text) <= 1 else 11
    font = load_icon_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (size - (bbox[2] - bbox[0])) / 2
    y = (size - (bbox[3] - bbox[1])) / 2 - 1
    draw.text((x, y), text, fill="#ffffff" if file_type != "Miro" else "#111827", font=font)
    return image


def make_settings_icon(size: int = 24) -> Image.Image:
    scale = 4
    canvas = size * scale
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    track = (226, 232, 240, 255)
    accent = (56, 189, 248, 255)
    knob = (255, 255, 255, 255)
    rows = [(7, 8, 16), (12, 15, 8), (17, 10, 18)]
    for y, knob_x, end_x in rows:
        y *= scale
        x1 = 4 * scale
        x2 = 20 * scale
        draw.rounded_rectangle(
            (x1, y - 1 * scale, x2, y + 1 * scale),
            radius=1 * scale,
            fill=track,
        )
        draw.rounded_rectangle(
            (x1, y - 1 * scale, end_x * scale, y + 1 * scale),
            radius=1 * scale,
            fill=accent,
        )
        cx = knob_x * scale
        draw.ellipse((cx - 3 * scale, y - 3 * scale, cx + 3 * scale, y + 3 * scale), fill=knob)
        draw.ellipse((cx - 2 * scale, y - 2 * scale, cx + 2 * scale, y + 2 * scale), fill=(15, 23, 42, 255))
    return image.resize((size, size), Image.Resampling.LANCZOS)


def make_progress_ring(done: int, progress: int, total: int, size: int = 86) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pad = 8
    box = (pad, pad, size - pad, size - pad)
    width = 10
    draw.arc(box, 0, 360, fill="#dbeafe", width=width)
    if total <= 0:
        return image
    done_angle = int(360 * (done / total))
    progress_angle = int(360 * (progress / total))
    start = -90
    if done_angle:
        draw.arc(box, start, start + done_angle, fill="#22c55e", width=width)
        start += done_angle
    if progress_angle:
        draw.arc(box, start, start + progress_angle, fill="#60a5fa", width=width)
    inner_pad = pad + width + 6
    draw.ellipse((inner_pad, inner_pad, size - inner_pad, size - inner_pad), fill=(255, 255, 255, 70))
    percent = int((done / total) * 100)
    text = f"{percent}%"
    try:
        font = ImageFont.truetype("arial.ttf", max(13, size // 5))
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        ((size - text_w) / 2, (size - text_h) / 2 - 1),
        text,
        fill=(15, 23, 42, 255),
        font=font,
    )
    return image


def copy_text_to_clipboard(root, text: str):
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()


def copy_file_to_clipboard(path: str) -> bool:
    if not win32clipboard:
        return False
    file_path = str(Path(path).resolve())
    dropfiles = (
        b"\x14\x00\x00\x00"
        b"\x00\x00\x00\x00"
        b"\x00\x00\x00\x00"
        b"\x00\x00\x00\x00"
        b"\x00\x00\x00\x00"
        b"\x01\x00\x00\x00"
    )
    data = dropfiles + file_path.encode("utf-16le") + b"\x00\x00\x00\x00"
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
    finally:
        win32clipboard.CloseClipboard()
    return True


def add_entry_context_menu(entry):
    native = getattr(entry, "_entry", entry)

    def cut():
        try:
            selected = native.selection_get()
            native.clipboard_clear()
            native.clipboard_append(selected)
            native.delete("sel.first", "sel.last")
            return "break"
        except Exception:
            native.event_generate("<<Cut>>")
            return "break"

    def copy():
        try:
            selected = native.selection_get()
            native.clipboard_clear()
            native.clipboard_append(selected)
            return "break"
        except Exception:
            native.event_generate("<<Copy>>")
            return "break"

    def paste():
        try:
            text = native.clipboard_get()
            try:
                native.delete("sel.first", "sel.last")
            except Exception:
                pass
            native.insert("insert", text)
            return "break"
        except Exception:
            native.event_generate("<<Paste>>")
            return "break"

    def select_all():
        try:
            native.select_range(0, "end")
            native.icursor("end")
            return "break"
        except Exception:
            return "break"

    menu = Menu(entry, tearoff=0)
    menu.add_command(label="Cut", command=cut)
    menu.add_command(label="Copy", command=copy)
    menu.add_command(label="Paste", command=paste)
    menu.add_separator()
    menu.add_command(label="Select all", command=select_all)
    native.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root), add="+")
    for sequence in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
        native.bind(sequence, lambda _event: paste())
    for sequence in ("<Control-c>", "<Control-C>"):
        native.bind(sequence, lambda _event: copy())
    for sequence in ("<Control-x>", "<Control-X>"):
        native.bind(sequence, lambda _event: cut())
    for sequence in ("<Control-a>", "<Control-A>"):
        native.bind(sequence, lambda _event: select_all())


def add_textbox_context_menu(textbox):
    native = getattr(textbox, "_textbox", textbox)

    def cut():
        native.event_generate("<<Cut>>")
        return "break"

    def copy():
        native.event_generate("<<Copy>>")
        return "break"

    def paste():
        try:
            text = native.clipboard_get()
            try:
                native.delete("sel.first", "sel.last")
            except Exception:
                pass
            native.insert("insert", text)
            return "break"
        except Exception:
            native.event_generate("<<Paste>>")
            return "break"

    def select_all():
        native.tag_add("sel", "1.0", "end")
        return "break"

    menu = Menu(textbox, tearoff=0)
    menu.add_command(label="Cut", command=cut)
    menu.add_command(label="Copy", command=copy)
    menu.add_command(label="Paste", command=paste)
    menu.add_separator()
    menu.add_command(label="Select all", command=select_all)
    native.bind("<Button-3>", lambda event: menu.tk_popup(event.x_root, event.y_root), add="+")
    for sequence in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
        native.bind(sequence, lambda _event: paste())
    for sequence in ("<Control-a>", "<Control-A>"):
        native.bind(sequence, lambda _event: select_all())
    for sequence in ("<Control-c>", "<Control-C>"):
        native.bind(sequence, lambda _event: copy())
    for sequence in ("<Control-x>", "<Control-X>"):
        native.bind(sequence, lambda _event: cut())


from ui.diagnostics_window import DiagnosticsWindow
from ui.settings_window import SettingsWindow
from ui.windows import (
    CreateNewWindow,
    LinkForm,
    TaskDetailWindow,
    TaskForm,
    TemplateDetailWindow,
    TemplateFileForm,
    TemplateWindow,
)

class TaskBoardApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.app_settings = load_app_settings()
        self.theme_name = self.app_settings.get("theme", "Light")
        apply_theme(self.theme_name)
        if self.app_settings.get("launch_on_startup") and not is_startup_enabled():
            try:
                set_startup_enabled(True)
            except Exception as exc:
                add_settings_log("Startup", f"Auto Run sync failed: {exc}")
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        try:
            self.iconbitmap(str(ensure_app_icon()))
            if APP_LOGO_FILE.exists():
                self._window_icon_photo = ImageTk.PhotoImage(
                    Image.open(APP_LOGO_FILE).convert("RGBA").resize((32, 32), Image.Resampling.LANCZOS)
                )
                self.iconphoto(True, self._window_icon_photo)
        except Exception:
            pass
        self.geometry(self.app_settings.get("window_geometry", "1320x840"))
        self.minsize(1120, 680)
        self.configure(fg_color=UI_BG)
        ensure_status_folders()
        self.store = TaskStore(
            DATA_FILE,
            task_file_key=task_file_key,
            scan_work_folder_tasks=scan_work_folder_tasks,
            item_exists=item_exists,
            status_done=STATUS_DONE,
        )
        self.template_store = TemplateStore(
            TEMPLATE_FILE,
            normalized_file_key=normalized_file_key,
            scan_template_folder_items=scan_template_folder_items,
            item_exists=item_exists,
            is_canonical_template_path=is_canonical_template_path,
        )
        self.column_frames = {}
        self.icon_images = {}
        self.type_icon_images = {}
        self.expanded_groups = {}
        self.group_bodies = {}
        self.group_buttons = {}
        self.group_frames = {}
        self.group_task_ids = {}
        self.card_widgets = {}
        self.visible_card_ids = set()
        self.visible_group_keys = set()
        self.group_visible_limits = {}
        self.search_text_cache = {}
        self.stat_value_labels = {}
        self.column_count_labels = {}
        self.stat_cards = {}
        self.stat_card_colors = {}
        self.filter_buttons = {}
        self.column_render_signatures = {}
        self.type_breakdown_signature = None
        self.render_batch_jobs = {}
        self.resize_refresh_job = None
        self.last_window_size = (0, 0)
        self.header_logo_image = None
        self.settings_icon_image = None
        self.dynamic_island_job = None
        self.dynamic_island_expanded = True
        self.island_marquee_offset = 0
        self.island_pulse_step = 0
        self.island_current_task_id = None
        self.focused_task_id = None
        self.last_work_fingerprint = None
        self.last_template_fingerprint = None
        self.sync_thread_running = False
        self.pending_sync_result = None
        self.last_sync_info = None
        self.diagnostics_events = []
        self.sync_poll_job = None
        self.search_var = ctk.StringVar(value="")
        self.category_filter_var = ctk.StringVar(value="All categories")
        self.sort_var = ctk.StringVar(value=SORT_OPTIONS[0])
        self.smart_view_var = ctk.StringVar(value="All work")
        self.search_refresh_job = None
        self.suspend_search_trace = False
        self.search_materialized = False
        self.search_var.trace_add("write", self.schedule_search_refresh)
        self.active_status_filter = None

        initial_fingerprint = folder_tree_fingerprint(work_root() / "Work")
        self.last_work_fingerprint = initial_fingerprint
        self.last_template_fingerprint = tuple(item for item in initial_fingerprint if "\\template\\" in item[0])
        work_signature = fingerprint_signature(initial_fingerprint)
        template_signature = fingerprint_signature(self.last_template_fingerprint)
        if self.app_settings.get("work_fingerprint") != work_signature:
            self.store.sync_from_work_folders()
            self.app_settings["work_fingerprint"] = work_signature
        if self.app_settings.get("template_fingerprint") != template_signature:
            self.template_store.sync_from_template_folders()
            self.app_settings["template_fingerprint"] = template_signature
        save_app_settings(self.app_settings)

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.build_sidebar()
        self.build_header()
        self.build_report_panel()
        self.build_board()

        self.refresh()
        self.update_dynamic_island()
        self.bind("<Configure>", self.schedule_resize_reflow)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(SYNC_INTERVAL_MS, self.auto_sync)

    def record_diagnostic(self, kind, detail):
        self.diagnostics_events.append(
            {
                "time": datetime.now().strftime("%H:%M:%S"),
                "kind": kind,
                "detail": detail,
            }
        )
        self.diagnostics_events = self.diagnostics_events[-80:]

    def on_close(self):
        self.app_settings["window_geometry"] = self.geometry()
        self.app_settings["last_view"] = {
            "smart_view": self.smart_view_var.get(),
            "category": self.category_filter_var.get(),
            "sort": self.sort_var.get(),
        }
        save_app_settings(self.app_settings)
        self.destroy()

    def rebuild_shell(self):
        scroll_positions = self.capture_scroll_positions()
        self.cancel_search_refresh()
        self.cancel_render_batches()
        if self.resize_refresh_job:
            try: self.after_cancel(self.resize_refresh_job)
            except Exception: pass
            self.resize_refresh_job = None
        if self.sync_poll_job:
            try: self.after_cancel(self.sync_poll_job)
            except Exception: pass
            self.sync_poll_job = None
        if self.dynamic_island_job:
            try: self.after_cancel(self.dynamic_island_job)
            except Exception: pass
            self.dynamic_island_job = None
        for child in list(self.winfo_children()):
            if child.winfo_toplevel() == self: child.destroy()
        self.configure(fg_color=UI_BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        self.type_breakdown_signature = None
        self.column_render_signatures.clear()
        self.render_batch_jobs.clear()
        self.group_bodies.clear()
        self.group_buttons.clear()
        self.group_frames.clear()
        self.group_task_ids.clear()
        self.card_widgets.clear()
        self.visible_card_ids.clear()
        self.visible_group_keys.clear()
        self.stat_cards.clear()
        self.stat_value_labels.clear()
        self.column_count_labels.clear()

        self.build_header()
        self.build_report_panel()
        self.build_board()

        self.refresh(force=True)
        self.update_dynamic_island()
        self.after(50, lambda: self.restore_scroll_positions(scroll_positions))

    def set_theme(self, theme_name):
        if theme_name not in THEME_PALETTES or theme_name == self.theme_name:
            return
        self.theme_name = theme_name
        self.app_settings["theme"] = theme_name
        save_app_settings(self.app_settings)
        apply_theme(theme_name)
        self.record_diagnostic("Theme", f"Changed to {theme_name}")
        self.rebuild_shell()

    def auto_sync(self):
        """Periodically sync with file system without blocking the UI thread."""
        if not self.sync_thread_running:
            self.sync_thread_running = True
            self.pending_sync_result = None
            threading.Thread(target=self.scan_work_folders_background, daemon=True).start()
            self.poll_auto_sync_result()
        self.after(SYNC_INTERVAL_MS, self.auto_sync)

    def scan_work_folders_background(self):
        try:
            work_fingerprint = folder_tree_fingerprint(work_root() / "Work")
            template_fingerprint = tuple(item for item in work_fingerprint if "\\template\\" in item[0])
            work_items = None
            template_items = None
            if work_fingerprint != self.last_work_fingerprint:
                work_items = scan_work_folder_tasks()
            if template_fingerprint != self.last_template_fingerprint:
                template_items = scan_template_folder_items()
            self.pending_sync_result = (work_fingerprint, template_fingerprint, work_items, template_items, None)
        except Exception as exc:
            self.pending_sync_result = (None, None, None, None, exc)

    def poll_auto_sync_result(self):
        result = self.pending_sync_result
        if result is None:
            self.sync_poll_job = self.after(160, self.poll_auto_sync_result)
            return
        self.sync_poll_job = None
        self.pending_sync_result = None
        self.sync_thread_running = False
        work_fingerprint, template_fingerprint, work_items, template_items, exc = result
        if exc or work_fingerprint is None:
            return
        changed = False
        fingerprint_changed = False
        if work_fingerprint != self.last_work_fingerprint:
            changed = self.store.sync_from_scanned(work_items or []) or changed
            self.last_work_fingerprint = work_fingerprint
            self.app_settings["work_fingerprint"] = fingerprint_signature(work_fingerprint)
            fingerprint_changed = True
        if template_fingerprint != self.last_template_fingerprint:
            changed = self.template_store.sync_from_scanned(template_items or []) or changed
            self.last_template_fingerprint = template_fingerprint
            self.app_settings["template_fingerprint"] = fingerprint_signature(template_fingerprint)
            fingerprint_changed = True
        if fingerprint_changed:
            save_app_settings(self.app_settings)
        if changed:
            self.refresh(force=True)

    def toggle_dynamic_island(self):
        self.dynamic_island_expanded = not self.dynamic_island_expanded
        try:
            if self.dynamic_island_expanded:
                self.island_task_label.grid()
                self.progress.grid()
            else:
                self.island_task_label.grid_remove()
                self.progress.grid_remove()
        except (RuntimeError, TclError):
            pass

    def focused_work_task(self):
        if not self.focused_task_id:
            return None
        for task in self.store.tasks:
            if task.get("id") == self.focused_task_id:
                return task
        self.focused_task_id = None
        return None

    def island_default_type(self):
        counts = {}
        for task in self.store.tasks:
            file_type = task.get("type", "Other")
            counts[file_type] = counts.get(file_type, 0) + 1
        if not counts:
            return "Other"
        return max(counts, key=lambda key: (counts[key], key != "Other"))

    def tool_label_for_task(self, task):
        if not task:
            return "Ready"
        if task.get("target_kind") == "folder":
            stack = task.get("project_stack")
            return stack or "Project"
        if task.get("target_kind") == "url" or is_url(task.get("link", "")):
            return f"{task.get('type', 'Link')} Link"
        return task.get("type", "File")

    def marquee_text(self, text, width=42):
        clean = " ".join(str(text or "").split())
        if len(clean) <= width:
            return clean
        padded = f"{clean}     "
        offset = self.island_marquee_offset % len(padded)
        doubled = padded + padded
        return doubled[offset:offset + width]

    def update_dynamic_island(self, schedule_next=True):
        if not getattr(self, "summary_label", None):
            return
        if schedule_next and self.dynamic_island_job:
            try:
                self.after_cancel(self.dynamic_island_job)
            except Exception:
                pass
            self.dynamic_island_job = None
        task = self.focused_work_task()
        now_text = datetime.now().strftime("%H:%M")
        icon_type = task.get("type", "Other") if task else self.island_default_type()
        tool_text = self.tool_label_for_task(task) if task else icon_type
        active_color = FILE_TYPES.get(icon_type, FILE_TYPES.get("Other", {"color": "#38bdf8"})).get("color", "#38bdf8")
        pulse_amount = 0.30 + (self.island_pulse_step % 6) * 0.055
        pulse_border = blend_color(active_color, "#38bdf8", pulse_amount)
        task_id = task.get("id") if task else None
        if task_id != self.island_current_task_id:
            self.island_current_task_id = task_id
            self.island_marquee_offset = 0

        try:
            self.island_time_label.configure(text=now_text)
            self.summary_card.configure(border_color=pulse_border)
            self.progress.configure(progress_color=active_color)
        except (RuntimeError, TclError):
            pass

        if schedule_next:
            self.island_marquee_offset += 1
            self.island_pulse_step += 1
        if schedule_next:
            self.dynamic_island_job = self.after(900, self.update_dynamic_island)

    def capture_scroll_positions(self):
        positions = {}
        for status, frame in self.column_frames.items():
            canvas = getattr(frame, "_parent_canvas", None)
            if canvas:
                positions[status] = canvas.yview()[0]
        return positions

    def restore_scroll_positions(self, positions):
        for status, position in positions.items():
            frame = self.column_frames.get(status)
            canvas = getattr(frame, "_parent_canvas", None) if frame else None
            if canvas:
                canvas.yview_moveto(position)

    def cancel_render_batches(self):
        for job in list(self.render_batch_jobs.values()):
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self.render_batch_jobs.clear()

    def cancel_render_batch(self, key):
        job = self.render_batch_jobs.pop(key, None)
        if job:
            try:
                self.after_cancel(job)
            except Exception:
                pass

    def schedule_resize_reflow(self, event=None):
        if event is not None and event.widget is not self:
            return
        size = (self.winfo_width(), self.winfo_height())
        if size == self.last_window_size:
            return
        self.last_window_size = size
        if self.resize_refresh_job:
            try:
                self.after_cancel(self.resize_refresh_job)
            except Exception:
                pass
        positions = self.capture_scroll_positions()
        self.resize_refresh_job = self.after(
            RESIZE_DEBOUNCE_MS,
            lambda positions=positions: self.finish_resize_reflow(positions),
        )

    def finish_resize_reflow(self, positions):
        self.resize_refresh_job = None
        self.restore_scroll_positions(positions)

    def render_or_reuse_card(self, body, task, row):
        task_id = task.get("id")
        widget = self.card_widgets.get(task_id)
        if widget is not None:
            if widget.master == body:
                widget.grid(row=row, column=0, padx=4, pady=(0, 1), sticky="ew")
                self.visible_card_ids.add(task_id)
                return
            try:
                widget.destroy()
            except Exception:
                pass
            self.card_widgets.pop(task_id, None)
            self.visible_card_ids.discard(task_id)
        self.render_card(body, task, row)

    def schedule_card_batch(self, key, body, tasks, start_row=1, batch_size=RENDER_BATCH_SIZE):
        self.cancel_render_batch(key)

        def render_next(offset=0):
            if not body.winfo_exists():
                self.render_batch_jobs.pop(key, None)
                return
            chunk = tasks[offset:offset + batch_size]
            for index, task in enumerate(chunk, start=start_row + offset):
                self.render_or_reuse_card(body, task, index)
            next_offset = offset + len(chunk)
            if next_offset < len(tasks):
                self.render_batch_jobs[key] = self.after(12, lambda: render_next(next_offset))
            else:
                self.render_batch_jobs.pop(key, None)

        render_next(0)

    def cancel_search_refresh(self):
        if self.search_refresh_job:
            try:
                self.after_cancel(self.search_refresh_job)
            except Exception:
                pass
            self.search_refresh_job = None

    def schedule_search_refresh(self, *_args):
        if self.suspend_search_trace:
            return
        self.cancel_search_refresh()
        self.search_refresh_job = self.after(SEARCH_DEBOUNCE_MS, self.run_scheduled_search_refresh)

    def run_scheduled_search_refresh(self):
        self.search_refresh_job = None
        has_query = bool(self.search_var.get().strip())
        if has_query and not self.search_materialized:
            self.search_materialized = True
            self.refresh(force=True)
            return
        if not has_query and self.search_materialized:
            self.search_materialized = False
            self.refresh(force=True)
            return
        self.apply_live_search()

    def set_status_filter(self, status):
        if self.active_status_filter == status:
            status = None
        self.active_status_filter = status
        self.smart_view_var.set("All work" if status is None else "Custom view")
        self.cancel_search_refresh()
        self.refresh()

    def set_category_filter(self, category):
        self.smart_view_var.set("Custom view")
        self.category_filter_var.set(category)
        self.cancel_search_refresh()
        self.refresh(force=True)

    def set_sort_mode(self, sort_mode):
        self.sort_var.set(sort_mode)
        self.cancel_search_refresh()
        self.refresh(force=True)

    def apply_smart_view(self, view_name):
        if view_name == "Custom view":
            return
        view = SMART_VIEWS.get(view_name, {})
        self.smart_view_var.set(view_name)
        self.active_status_filter = view.get("status")
        self.category_filter_var.set(view.get("category", "All categories"))
        if view_name == "Needs fix":
            self.sort_var.set("Needs fix first")
        elif view_name in ("Doing now", "Old doing"):
            self.sort_var.set("Oldest first")
        else:
            self.sort_var.set("Newest first")
        self.cancel_search_refresh()
        self.refresh(force=True)

    def clear_filters(self):
        self.active_status_filter = None
        self.category_filter_var.set("All categories")
        self.sort_var.set(SORT_OPTIONS[0])
        self.smart_view_var.set("All work")
        self.cancel_search_refresh()
        self.suspend_search_trace = True
        try:
            self.search_var.set("")
        finally:
            self.suspend_search_trace = False
        self.reset_board_render_cache()
        self.refresh(force=True)
        self.record_diagnostic("View", "Cleared search, filters, sort, and render cache")

    def sync_now(self):
        changed = self.rescan_work_folders(show_message=False)
        if hasattr(self, "report_label"):
            self.report_label.configure(text="Synced from disk and folders" if changed else "Reloaded from disk; no folder changes")
            self.after(
                1800,
                lambda: self.report_label.configure(text="System Ready")
                if self.winfo_exists() and hasattr(self, "report_label")
                else None,
            )

    def reset_board_render_cache(self):
        self.cancel_render_batches()
        self.column_render_signatures.clear()
        self.type_breakdown_signature = None
        self.group_bodies.clear()
        self.group_buttons.clear()
        self.group_frames.clear()
        self.group_task_ids.clear()
        self.card_widgets.clear()
        self.visible_card_ids.clear()
        self.visible_group_keys.clear()
        for frame in self.column_frames.values():
            for child in frame.winfo_children():
                child.destroy()

    def task_matches_filters(self, task):
        status_filter = self.active_status_filter
        if status_filter == "today":
            if task.get("done_date") != date.today().isoformat():
                return False
        elif status_filter == "mismatch":
            if not task.get("category_mismatch"):
                return False
        elif status_filter and task.get("status", STATUS_PENDING) != status_filter:
            return False
        category_filter = self.category_filter_var.get()
        if category_filter and category_filter != "All categories" and task.get("type", "Other") != category_filter:
            return False
        view_name = self.smart_view_var.get()
        view = SMART_VIEWS.get(view_name, {})
        kind_filter = view.get("kind")
        if kind_filter == "url" and not (task.get("target_kind") == "url" or is_url(task.get("link", ""))):
            return False
        if kind_filter == "folder" and task.get("target_kind") != "folder":
            return False
        age_min = view.get("age_min")
        if age_min is not None and self.task_age_days(task) < age_min:
            return False
        return True

    def task_matches_search(self, task):
        query = self.search_var.get().strip().casefold()
        if not query:
            return True

        return query in self.task_search_text(task)

    def task_search_text(self, task):
        signature = (
            task.get("id"),
            task.get("name"),
            task.get("type"),
            task.get("note"),
            task.get("link"),
            task.get("status"),
            task.get("date_added"),
            task.get("detected_type"),
            task.get("project_stack"),
            task.get("target_kind"),
        )
        cached = self.search_text_cache.get(task.get("id"))
        if cached and cached[0] == signature:
            return cached[1]
        searchable = " ".join(str(value or "") for value in signature[1:]).casefold()
        self.search_text_cache[task.get("id")] = (signature, searchable)
        return searchable

    def filtered_sorted_tasks(self, tasks):
        visible = [task for task in tasks if self.task_matches_filters(task) and self.task_matches_search(task)]
        sort_mode = self.sort_var.get()

        def parsed_added(task):
            value = task.get("date_added", "")
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    return datetime.strptime(value[:16 if "%H" in fmt else 10], fmt)
                except (TypeError, ValueError):
                    continue
            return datetime.min

        def date_rank(task):
            parsed = parsed_added(task)
            return parsed.toordinal() * 86400 + parsed.hour * 3600 + parsed.minute * 60 + parsed.second

        if sort_mode == "Oldest first":
            visible.sort(key=parsed_added)
        elif sort_mode == "Name A-Z":
            visible.sort(key=lambda task: task.get("name", "").casefold())
        elif sort_mode == "Type":
            visible.sort(key=lambda task: (task.get("type", "Other"), task.get("name", "").casefold()))
        elif sort_mode == "Status":
            status_order = {STATUS_PENDING: 0, STATUS_PROGRESS: 1, STATUS_DONE: 2}
            visible.sort(key=lambda task: (status_order.get(task.get("status", STATUS_PENDING), 9), task.get("type", ""), task.get("name", "").casefold()))
        elif sort_mode == "Needs fix first":
            visible.sort(key=lambda task: (not bool(task.get("category_mismatch")), -date_rank(task)))
        else:
            visible.sort(key=parsed_added, reverse=True)
        return visible

    def apply_live_search(self):
        query = self.search_var.get().strip()
        status_tasks = [task for task in self.store.tasks if self.task_matches_filters(task)]
        visible_ids = {task.get("id") for task in status_tasks if self.task_matches_search(task)}
        current_ids = set(self.card_widgets)

        shown = 0
        for task_id in current_ids:
            widget = self.card_widgets.get(task_id)
            if not widget:
                continue
            should_show = task_id in visible_ids
            is_showing = task_id in self.visible_card_ids
            if should_show and not is_showing:
                widget.grid()
                self.visible_card_ids.add(task_id)
            elif not should_show and is_showing:
                widget.grid_remove()
                self.visible_card_ids.discard(task_id)
            if should_show:
                shown += 1

        for key, group in self.group_frames.items():
            task_ids = self.group_task_ids.get(key, [])
            has_match = any(task_id in visible_ids for task_id in task_ids)
            is_showing = key in self.visible_group_keys
            if has_match and not is_showing:
                group.grid()
                self.visible_group_keys.add(key)
            elif not has_match and is_showing:
                group.grid_remove()
                self.visible_group_keys.discard(key)
            if has_match:
                body = self.group_bodies.get(key)
                button = self.group_buttons.get(key)
                if query:
                    if body:
                        try:
                            if not body.winfo_ismapped():
                                body.grid()
                        except Exception:
                            body.grid()
                    if button:
                        button.configure(text="Collapse")
                else:
                    expanded = self.expanded_groups.get(key, False)
                    if body:
                        if expanded:
                            try:
                                if not body.winfo_ismapped():
                                    body.grid()
                            except Exception:
                                body.grid()
                        else:
                            if body.winfo_ismapped():
                                body.grid_remove()
                    if button:
                        button.configure(text="Collapse" if expanded else "Expand")

        total = len(self.store.tasks)
        done = sum(1 for task in self.store.tasks if task.get("status") == STATUS_DONE)
        progress = sum(1 for task in self.store.tasks if task.get("status") == STATUS_PROGRESS)
        pending = sum(1 for task in self.store.tasks if task.get("status") == STATUS_PENDING)
        today = date.today().isoformat()
        today_done = sum(1 for task in self.store.tasks if task.get("done_date") == today)
        search_note = f"  |  search: {shown} match" if query else ""
        self.report_label.configure(
            text=f"{shown if query else len(status_tasks)}/{total} shown  |  W {pending}  D {progress}  S {done}  Today {today_done}{search_note}"
        )

    def task_age_days(self, task):
        added = task.get("date_added", "")
        try:
            return (datetime.now() - datetime.strptime(added[:10], "%Y-%m-%d")).days
        except (TypeError, ValueError):
            return 0

    def update_filter_visuals(self):
        for key, card in self.stat_cards.items():
            active = (
                (key == "total" and self.active_status_filter is None)
                or (key == "pending" and self.active_status_filter == STATUS_PENDING)
                or (key == "progress" and self.active_status_filter == STATUS_PROGRESS)
                or (key == "done" and self.active_status_filter == STATUS_DONE)
                or (key == "today" and self.active_status_filter == "today")
                or (key == "mismatch" and self.active_status_filter == "mismatch")
            )
            accent = self.stat_card_colors.get(key, "#2563eb")
            card.configure(border_color=accent if active else UI_BORDER_SOFT, border_width=2 if active else 1)

    def task_render_signature(self, tasks):
        return tuple(
            (
                task.get("id"),
                task.get("status"),
                task.get("type"),
                task.get("name"),
                task.get("link"),
                task.get("shortcut_path"),
                task.get("target_kind"),
                task.get("detected_type"),
                task.get("project_stack"),
                task.get("category_mismatch"),
                task.get("note"),
                task.get("date_added"),
                task.get("done_date"),
            )
            for task in tasks
        )

    def type_breakdown_render_signature(self, tasks):
        signature = [("active_category", self.category_filter_var.get())]
        for file_type in FILE_TYPES:
            type_tasks = [task for task in tasks if task.get("type") == file_type]
            signature.append(
                (
                    file_type,
                    len(type_tasks),
                    sum(1 for task in type_tasks if task.get("status") == STATUS_PENDING),
                    sum(1 for task in type_tasks if task.get("status") == STATUS_PROGRESS),
                    sum(1 for task in type_tasks if task.get("status") == STATUS_DONE),
                )
            )
        return tuple(signature)

    def clear_group_cache_for_status(self, status):
        prefix = f"{status}:"
        for key in [key for key in self.render_batch_jobs if key.startswith(prefix)]:
            self.cancel_render_batch(key)
        for key in [key for key in self.group_bodies if key.startswith(prefix)]:
            self.group_bodies.pop(key, None)
        for key in [key for key in self.group_buttons if key.startswith(prefix)]:
            self.group_buttons.pop(key, None)
        for key in [key for key in self.group_frames if key.startswith(prefix)]:
            self.group_frames.pop(key, None)
            self.visible_group_keys.discard(key)
        for key in [key for key in self.group_task_ids if key.startswith(prefix)]:
            for task_id in self.group_task_ids.get(key, []):
                self.card_widgets.pop(task_id, None)
                self.visible_card_ids.discard(task_id)
            self.group_task_ids.pop(key, None)

    def load_more_group(self, status, file_type):
        key = f"{status}:{file_type}"
        total = len(
            [
                task
                for task in self.store.tasks
                if task.get("status", STATUS_PENDING) == status and task.get("type", "Other") == file_type
            ]
        )
        self.group_visible_limits[key] = next_visible_limit(self.group_visible_limits.get(key), total, TASK_BATCH_SIZE)
        self.column_render_signatures.pop(status, None)
        self.refresh(columns_to_update=[status], force=True)

    def render_empty_state(self, status):
        meta = STATUS_META.get(status, STATUS_META[STATUS_PENDING])
        empty = ctk.CTkFrame(
            self.column_frames[status],
            fg_color=blend_color(meta["color"], UI_SURFACE, 0.94),
            corner_radius=12,
            border_width=1,
            border_color=blend_color(meta["color"], UI_BORDER_SOFT, 0.35),
        )
        empty.grid(row=0, column=0, padx=4, pady=12, sticky="ew")
        empty.grid_columnconfigure(0, weight=1)
        has_filter = bool(self.search_var.get().strip()) or self.active_status_filter is not None
        ctk.CTkLabel(
            empty,
            text=meta["icon"],
            width=48,
            height=30,
            corner_radius=10,
            fg_color=blend_color(meta["color"], UI_SURFACE, 0.18),
            text_color=best_text_color(meta["color"]),
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=(14, 6))
        ctk.CTkLabel(
            empty,
            text="No matching tasks" if has_filter else "No tasks yet",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=1, column=0, padx=12, pady=(0, 4))
        ctk.CTkLabel(
            empty,
            text="Filters are active" if has_filter else "Drop new work here from Quick actions",
            text_color=UI_MUTED_2,
            font=ctk.CTkFont(size=11),
        ).grid(row=2, column=0, padx=12, pady=(0, 10))
        ctk.CTkButton(
            empty,
            text="Clear filter" if has_filter else "+ Add file",
            width=120,
            height=30,
            fg_color=blend_color(meta["color"], UI_SURFACE, 0.72),
            hover_color=blend_color(meta["color"], UI_SURFACE, 0.58),
            text_color=UI_TEXT,
            command=self.clear_filters if has_filter else self.add_task,
        ).grid(row=3, column=0, padx=12, pady=(0, 14))

    def build_sidebar(self):
        nav = ctk.CTkFrame(
            self,
            fg_color=blend_color("#60a5fa", UI_SURFACE, 0.88 if self.theme_name == "Light" else 0.72),
            corner_radius=0,
            width=88,
            border_width=1,
            border_color=UI_BORDER_SOFT,
        )
        nav.grid(row=0, column=0, rowspan=3, sticky="nsw")
        nav.grid_propagate(False)
        nav.grid_columnconfigure(0, weight=1)
        nav.grid_rowconfigure(8, weight=1)

        if APP_LOGO_FILE.exists():
            logo_image = Image.open(APP_LOGO_FILE).convert("RGBA")
            self.header_logo_image = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(44, 44))
            ctk.CTkLabel(nav, text="", image=self.header_logo_image, width=54, height=54).grid(row=0, column=0, pady=(18, 20))
        else:
            ctk.CTkLabel(
                nav,
                text="S",
                width=54,
                height=54,
                corner_radius=16,
                fg_color="#2563eb",
                text_color="#ffffff",
                font=ctk.CTkFont(size=24, weight="bold"),
            ).grid(row=0, column=0, pady=(18, 20))

        nav_items = [
            ("Board", "B", self.clear_filters, True),
            ("Folders", "F", lambda: os.startfile(work_root() / "Work") if (work_root() / "Work").exists() else None, False),
            ("Templates", "T", self.open_templates, False),
            ("Sync", "R", self.sync_now, False),
            ("Diag", "D", self.open_diagnostics, False),
        ]
        for row, (_name, label, command, active) in enumerate(nav_items, start=1):
            ctk.CTkButton(
                nav,
                text=label,
                width=54,
                height=54,
                corner_radius=14,
                command=command,
                fg_color=UI_SURFACE if active else "transparent",
                hover_color=UI_SURFACE_2,
                text_color=UI_TEXT if active else UI_MUTED,
                border_width=1 if active else 0,
                border_color=UI_BORDER_SOFT,
                font=ctk.CTkFont(size=18, weight="bold"),
            ).grid(row=row, column=0, pady=5)

        self.settings_icon_image = ctk.CTkImage(
            light_image=make_settings_icon(22),
            dark_image=make_settings_icon(22),
            size=(22, 22),
        )
        ctk.CTkButton(
            nav,
            text="",
            image=self.settings_icon_image,
            width=54,
            height=54,
            corner_radius=14,
            command=self.open_settings,
            fg_color="transparent",
            hover_color=UI_SURFACE_2,
            text_color=UI_MUTED,
        ).grid(row=9, column=0, pady=(8, 18), sticky="s")

    def build_header(self):
        header = ctk.CTkFrame(self, fg_color=UI_BG, corner_radius=0, height=178)
        header.grid(row=0, column=1, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        crumb_row = ctk.CTkFrame(header, fg_color="transparent", height=64)
        crumb_row.grid(row=0, column=0, columnspan=2, padx=(34, 26), pady=(14, 0), sticky="ew")
        crumb_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            crumb_row,
            text=APP_TITLE,
            text_color=UI_TEXT,
            font=ctk.CTkFont(family="Segoe UI Variable", size=25, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkFrame(crumb_row, fg_color=UI_BORDER_SOFT, width=1, height=30).grid(row=0, column=1, padx=22, sticky="w")
        ctk.CTkLabel(
            crumb_row,
            text="WORK  >  TQM Work  /  Work",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=17),
        ).grid(row=0, column=1, padx=(44, 0), sticky="w")

        hero = ctk.CTkFrame(header, fg_color="transparent")
        hero.grid(row=1, column=0, padx=(34, 20), pady=(10, 0), sticky="nsew")
        hero.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            hero,
            text="Project Overview",
            text_color=UI_TEXT,
            font=ctk.CTkFont(family="Segoe UI Variable", size=36, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        legend = ctk.CTkFrame(hero, fg_color="transparent")
        legend.grid(row=1, column=0, pady=(8, 0), sticky="w")
        for index, (label, color) in enumerate([
            ("Status", "#60a5fa"),
            ("Progress", "#fb923c"),
            ("Brainstorm", "#a855f7"),
            ("Path", "#8b5cf6"),
        ]):
            ctk.CTkLabel(legend, text="●", text_color=color, font=ctk.CTkFont(size=16)).grid(row=0, column=index * 2, padx=(0, 6))
            ctk.CTkLabel(legend, text=label, text_color=UI_MUTED, font=ctk.CTkFont(size=16)).grid(row=0, column=index * 2 + 1, padx=(0, 18))

        self.summary_card = ctk.CTkFrame(
            header,
            fg_color=UI_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=UI_BORDER_SOFT,
            width=470,
            height=118,
        )
        self.summary_card.grid(row=1, column=1, padx=(0, 30), pady=(0, 8), sticky="e")
        self.summary_card.grid_propagate(False)
        self.summary_card.grid_columnconfigure((1, 2, 3), weight=1)

        top_line = ctk.CTkFrame(self.summary_card, fg_color="transparent")
        top_line.grid(row=0, column=0, columnspan=4, padx=16, pady=(10, 2), sticky="ew")
        top_line.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top_line, text="Project Overview", text_color=UI_TEXT, font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
        self.island_time_label = ctk.CTkLabel(top_line, text="--:--", text_color=UI_TEXT, font=ctk.CTkFont(size=22))
        self.island_time_label.grid(row=0, column=1, sticky="e")

        self.summary_ring_label = ctk.CTkLabel(self.summary_card, text="", width=82, height=82)
        self.summary_ring_label.grid(row=1, column=0, rowspan=2, padx=(20, 22), pady=(2, 14), sticky="w")

        self.summary_done_count = ctk.CTkLabel(self.summary_card, text="0%", text_color=UI_TEXT, font=ctk.CTkFont(size=25, weight="bold"))
        self.summary_done_count.grid(row=1, column=1, padx=8)
        ctk.CTkLabel(self.summary_card, text="complete", text_color=UI_MUTED, font=ctk.CTkFont(size=13)).grid(row=2, column=1, padx=8, sticky="n")

        self.summary_doing_count = ctk.CTkLabel(self.summary_card, text="0", text_color=UI_TEXT, font=ctk.CTkFont(size=25, weight="bold"))
        self.summary_doing_count.grid(row=1, column=2, padx=8)
        self.island_tool_label = ctk.CTkLabel(self.summary_card, text="in motion", text_color=UI_MUTED, font=ctk.CTkFont(size=13))
        self.island_tool_label.grid(row=2, column=2, padx=8, sticky="n")

        self.summary_remaining_count = ctk.CTkLabel(self.summary_card, text="0/0", text_color=UI_TEXT, font=ctk.CTkFont(size=25, weight="bold"))
        self.summary_remaining_count.grid(row=1, column=3, padx=(8, 18))
        self.summary_label = ctk.CTkLabel(self.summary_card, text="total done", text_color=UI_MUTED, font=ctk.CTkFont(size=13))
        self.summary_label.grid(row=2, column=3, padx=(8, 18), sticky="n")

        self.island_task_label = ctk.CTkLabel(self.summary_card, text="", width=1, height=1)
        self.island_status_dot = ctk.CTkFrame(self.summary_card, fg_color="#22c55e", width=1, height=1)
        self.island_tool_icon_label = ctk.CTkLabel(self.summary_card, text="", width=1, height=1)
        self.progress = ctk.CTkProgressBar(self.summary_card, width=1, height=1, progress_color="#22c55e", fg_color=UI_BORDER_SOFT)

    def build_report_panel(self):
        panel = ctk.CTkFrame(self, fg_color=UI_BG, corner_radius=0)
        panel.grid(row=1, column=1, sticky="ew")
        panel.grid_columnconfigure(0, weight=1)

        dashboard = ctk.CTkFrame(
            panel,
            fg_color="transparent",
            corner_radius=0,
        )
        dashboard.grid(row=0, column=0, padx=(34, 28), pady=(0, 6), sticky="ew")
        dashboard.grid_columnconfigure(0, weight=1)

        action_bar = ctk.CTkFrame(
            dashboard,
            fg_color=blend_color("#f97316", UI_SURFACE, 0.96 if self.theme_name == "Light" else 0.88),
            corner_radius=14,
            border_width=1,
            border_color=UI_BORDER_SOFT,
            height=58,
        )
        action_bar.grid(row=0, column=0, pady=(0, 12), sticky="ew")
        action_bar.grid_propagate(False)
        action_bar.grid_columnconfigure(5, weight=1)

        action_specs = [
            ("+ New Task", self.open_create_new, "#334155", "#1e293b", "#ffffff", 138),
            ("+ Add Asset", self.add_task, UI_SURFACE, UI_SURFACE_2, UI_TEXT, 140),
            ("Link Reference", self.add_link, UI_SURFACE, UI_SURFACE_2, UI_TEXT, 150),
            ("+ Create Project", self.add_project, UI_SURFACE, UI_SURFACE_2, UI_TEXT, 166),
            ("Manage Templates", self.open_templates, UI_SURFACE, UI_SURFACE_2, UI_TEXT, 180),
        ]
        for index, (text, command, fg, hover, color, width) in enumerate(action_specs):
            ctk.CTkButton(
                action_bar,
                text=text,
                command=command,
                width=width,
                height=38,
                corner_radius=9,
                fg_color=fg,
                hover_color=hover,
                text_color=color,
                border_width=0 if index == 0 else 1,
                border_color=UI_BORDER_SOFT,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=index, padx=(10 if index == 0 else 4, 4), pady=10, sticky="w")
        ctk.CTkButton(
            action_bar,
            text="Sync",
            command=self.sync_now,
            width=92,
            height=38,
            corner_radius=9,
            fg_color=UI_SURFACE,
            hover_color=UI_SURFACE_2,
            text_color=UI_TEXT,
            border_width=1,
            border_color=UI_BORDER_SOFT,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=6, padx=(4, 4), pady=10, sticky="e")
        ctk.CTkButton(
            action_bar,
            text="Diag",
            command=self.open_diagnostics,
            width=86,
            height=38,
            corner_radius=9,
            fg_color=UI_SURFACE,
            hover_color=UI_SURFACE_2,
            text_color=UI_TEXT,
            border_width=1,
            border_color=UI_BORDER_SOFT,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=7, padx=(4, 10), pady=10, sticky="e")

        control_bar = ctk.CTkFrame(dashboard, fg_color="transparent", corner_radius=0)
        control_bar.grid(row=1, column=0, sticky="ew")
        control_bar.grid_columnconfigure(0, weight=3)
        control_bar.grid_columnconfigure(1, weight=1)

        search_box = ctk.CTkFrame(control_bar, fg_color=UI_SURFACE, corner_radius=11, border_width=1, border_color=UI_BORDER_SOFT)
        search_box.grid(row=0, column=0, padx=(0, 8), pady=(0, 10), sticky="nsew")
        search_box.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            search_box,
            text="Find",
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=0, padx=(14, 6))
        search_entry = ctk.CTkEntry(
            search_box,
            textvariable=self.search_var,
            placeholder_text="Find work...",
            fg_color=UI_SURFACE_2,
            border_width=1,
            border_color=UI_BORDER_SOFT,
            height=38,
            font=ctk.CTkFont(size=14),
        )
        search_entry.grid(row=0, column=1, padx=(0, 8), pady=8, sticky="ew")
        add_entry_context_menu(search_entry)
        ctk.CTkButton(
            search_box,
            text="X",
            width=32,
            height=30,
            fg_color="transparent",
            hover_color=UI_SURFACE_2,
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.clear_filters,
        ).grid(row=0, column=2, padx=(0, 10))

        overview = ctk.CTkFrame(control_bar, fg_color=UI_SURFACE, corner_radius=8, border_width=1, border_color=UI_BORDER_SOFT)
        overview.grid(row=0, column=1, padx=(8, 0), pady=(0, 10), sticky="nsew")
        overview.grid_columnconfigure(0, weight=1)
        self.dashboard_status_label = ctk.CTkLabel(
            overview,
            text="Work health",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=10, weight="bold"),
        )
        self.dashboard_status_label.grid(row=0, column=0, padx=12, pady=(4, 0), sticky="w")
        self.dashboard_progress_label = ctk.CTkLabel(
            overview,
            text="0%",
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.dashboard_progress_label.grid(row=1, column=0, padx=12, pady=(0, 0), sticky="w")
        self.dashboard_progress = ctk.CTkProgressBar(overview, height=6, progress_color="#22c55e", fg_color=UI_BORDER_SOFT)
        self.dashboard_progress.grid(row=2, column=0, padx=12, pady=(0, 6), sticky="ew")

        view_controls = ctk.CTkFrame(control_bar, fg_color=UI_SURFACE, corner_radius=8, border_width=1, border_color=UI_BORDER_SOFT)
        view_controls.grid(row=1, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        view_controls.grid_columnconfigure(1, weight=1)
        view_controls.grid_columnconfigure(3, weight=1)
        view_controls.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(
            view_controls,
            text="Work view",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=0, padx=(10, 4), pady=6, sticky="w")
        smart_values = [*SMART_VIEWS.keys(), "Custom view"]
        ctk.CTkOptionMenu(
            view_controls,
            values=smart_values,
            variable=self.smart_view_var,
            command=self.apply_smart_view,
            height=28,
            corner_radius=6,
            fg_color=UI_SURFACE_2,
            button_color=UI_BORDER_SOFT,
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=1, padx=(0, 8), pady=6, sticky="ew")

        ctk.CTkLabel(
            view_controls,
            text="Type",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=2, padx=(0, 4), pady=6, sticky="w")
        ctk.CTkOptionMenu(
            view_controls,
            values=["All categories", *FILE_TYPES.keys()],
            variable=self.category_filter_var,
            command=self.set_category_filter,
            height=28,
            corner_radius=6,
            fg_color=UI_SURFACE_2,
            button_color=UI_BORDER_SOFT,
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=3, padx=(0, 8), pady=6, sticky="ew")

        ctk.CTkLabel(
            view_controls,
            text="Sort",
            text_color=UI_MUTED,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).grid(row=0, column=4, padx=(0, 4), pady=6, sticky="w")
        ctk.CTkOptionMenu(
            view_controls,
            values=SORT_OPTIONS,
            variable=self.sort_var,
            command=self.set_sort_mode,
            height=28,
            corner_radius=6,
            fg_color=UI_SURFACE_2,
            button_color=UI_BORDER_SOFT,
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=5, padx=(0, 8), pady=6, sticky="ew")
        ctk.CTkButton(
            view_controls,
            text="Clear Filters",
            width=96,
            height=28,
            corner_radius=6,
            fg_color=UI_SURFACE_2,
            hover_color=UI_SURFACE_3,
            text_color=UI_TEXT,
            border_width=1,
            border_color=UI_BORDER_SOFT,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.clear_filters,
        ).grid(row=0, column=6, padx=(0, 10), pady=6, sticky="e")

        top_row = ctk.CTkFrame(dashboard, fg_color="transparent")
        top_row.grid(row=2, column=0, pady=(0, 10), sticky="ew")
        for index in range(4):
            top_row.grid_columnconfigure(index, weight=1, uniform="stat_card")

        stat_specs = [
            ("total", "TOTAL", "All work", "#60a5fa"),
            ("pending", "WAITING", "Waiting list", STATUS_META[STATUS_PENDING]["color"]),
            ("progress", "DOING", "Active work", STATUS_META[STATUS_PROGRESS]["color"]),
            ("done", "COMPLETED", "Complete", STATUS_META[STATUS_DONE]["color"]),
        ]
        self.stat_card_colors = {}
        for index, (key, badge, label, color) in enumerate(stat_specs):
            self.stat_card_colors[key] = color
            card_bg = blend_color(color, UI_SURFACE, 0.82 if self.theme_name == "Light" else 0.72)
            card = ctk.CTkFrame(top_row, fg_color=card_bg, corner_radius=14, border_width=1, border_color=blend_color(color, UI_BORDER_SOFT, 0.20), height=130)
            card.grid(row=0, column=index, padx=(0 if index == 0 else 10, 0), sticky="nsew")
            card.grid_propagate(False)
            card.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                card,
                text=badge,
                text_color=UI_TEXT,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=0, padx=16, pady=(18, 0), sticky="w")
            val_label = ctk.CTkLabel(card, text="0", text_color=UI_TEXT, font=ctk.CTkFont(size=32, weight="bold"))
            val_label.grid(row=1, column=0, padx=16, pady=(2, 0), sticky="w")
            txt_label = ctk.CTkLabel(card, text=label, text_color=UI_MUTED, font=ctk.CTkFont(size=13))
            txt_label.grid(row=2, column=0, padx=16, pady=(12, 0), sticky="w")
            ctk.CTkFrame(card, fg_color=blend_color(color, UI_BORDER, 0.22), height=1).grid(row=3, column=0, padx=16, pady=(9, 0), sticky="ew")
            
            self.stat_value_labels[key] = val_label
            self.stat_cards[key] = card
            
            handler = lambda _e, k=key: self.set_status_filter(None if k == "total" else ("today" if k == "today" else k))
            card.bind("<Button-1>", handler)
            val_label.bind("<Button-1>", handler)
            txt_label.bind("<Button-1>", handler)

        type_panel = ctk.CTkFrame(dashboard, fg_color=UI_SURFACE, corner_radius=14, border_width=1, border_color=UI_BORDER_SOFT)
        type_panel.grid(row=3, column=0, pady=(0, 5), sticky="ew")
        type_panel.grid_columnconfigure(0, weight=1)
        
        self.type_row = ctk.CTkFrame(type_panel, fg_color="transparent")
        self.type_row.grid(row=0, column=0, padx=6, pady=4, sticky="ew")
        for index in range(8):
            self.type_row.grid_columnconfigure(index, weight=1, uniform="type_chip")

        self.report_label = ctk.CTkLabel(dashboard, text="", text_color=UI_MUTED, font=ctk.CTkFont(size=10))
        self.report_label.grid(row=4, column=0, padx=4, pady=(0, 4), sticky="w")

    def build_board(self):
        board = ctk.CTkFrame(self, fg_color=UI_BG, corner_radius=0)
        board.grid(row=2, column=1, sticky="nsew", padx=(34, 28), pady=(2, 18))
        board.grid_rowconfigure(0, weight=1)
        board_labels = {
            STATUS_PENDING: "Waiting List",
            STATUS_PROGRESS: "Active Work",
            STATUS_DONE: "Complete",
        }
        for index, (status, label) in enumerate(STATUSES):
            meta = STATUS_META[status]
            board.grid_columnconfigure(index, weight=1, uniform="kanban")
            column = ctk.CTkFrame(
                board,
                fg_color=blend_color(meta["color"], UI_SURFACE, 0.92 if self.theme_name == "Light" else 0.84),
                corner_radius=14,
                border_width=1,
                border_color=blend_color(meta["color"], UI_BORDER, 0.15),
            )
            column.grid(row=0, column=index, padx=(0 if index == 0 else 14, 0), sticky="nsew")
            column.grid_columnconfigure(0, weight=1)
            column.grid_rowconfigure(1, weight=1)
            header = ctk.CTkFrame(column, fg_color=blend_color(meta["color"], UI_SURFACE, 0.62 if self.theme_name == "Light" else 0.50), corner_radius=12)
            header.grid(row=0, column=0, sticky="ew")
            header.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                header,
                text="=" if status == STATUS_PENDING else ("+" if status == STATUS_PROGRESS else "OK"),
                width=30,
                height=30,
                corner_radius=9,
                fg_color=blend_color(meta["color"], UI_SURFACE, 0.26),
                text_color=meta["color"],
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=0, padx=(12, 8), pady=12, sticky="w")
            ctk.CTkLabel(
                header,
                text=board_labels.get(status, label),
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=UI_TEXT,
            ).grid(row=0, column=1, sticky="w")
            count_label = ctk.CTkLabel(
                header,
                text="0 tasks",
                width=72,
                height=28,
                corner_radius=9,
                fg_color=blend_color(meta["color"], UI_SURFACE, 0.75),
                text_color=UI_TEXT,
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            count_label.grid(row=0, column=2, padx=(8, 12), pady=12, sticky="e")
            self.column_count_labels[status] = count_label
            scroll = ctk.CTkScrollableFrame(
                column,
                fg_color=blend_color(meta["color"], UI_SURFACE_2, 0.95 if self.theme_name == "Light" else 0.90),
                corner_radius=12,
            )
            scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(10, 10))
            scroll.grid_columnconfigure(0, weight=1)
            self.column_frames[status] = scroll

    def refresh(self, columns_to_update=None, force=False):
        scroll_positions = self.capture_scroll_positions()

        all_tasks = self.store.tasks
        task_ids = {task.get("id") for task in all_tasks}
        for task_id in [task_id for task_id in self.search_text_cache if task_id not in task_ids]:
            self.search_text_cache.pop(task_id, None)
        tasks = self.filtered_sorted_tasks(all_tasks)
        total = len(all_tasks)
        shown = len(tasks)
        done = sum(1 for task in all_tasks if task.get("status") == STATUS_DONE)
        progress = sum(1 for task in all_tasks if task.get("status") == STATUS_PROGRESS)
        pending = sum(1 for task in all_tasks if task.get("status") == STATUS_PENDING)
        mismatch = sum(1 for task in all_tasks if task.get("category_mismatch"))
        percent = int((done / total) * 100) if total else 0

        self.summary_label.configure(text="Remaining")
        if hasattr(self, "summary_doing_count"):
            self.summary_doing_count.configure(text=str(progress))
            self.summary_remaining_count.configure(text=f"{done}/{total}")
            self.summary_done_count.configure(text=f"{percent}%")
            self.summary_label.configure(text="total done")
            ring = make_progress_ring(done, progress, total, 86)
            self.summary_ring_image = ctk.CTkImage(light_image=ring, dark_image=ring, size=(86, 86))
            self.summary_ring_label.configure(image=self.summary_ring_image)
        self.progress.set(done / total if total else 0)
        self.update_dynamic_island(schedule_next=False)
        if hasattr(self, "dashboard_progress"):
            ratio = done / total if total else 0
            self.dashboard_progress.set(ratio)
            self.dashboard_progress_label.configure(text=f"{percent}% complete")
            if mismatch:
                health_text = f"{mismatch} item needs category fix"
            elif progress:
                health_text = f"{progress} work item in motion"
            elif done and done == total:
                health_text = "All visible work completed"
            else:
                health_text = "Ready for today's queue"
            self.dashboard_status_label.configure(text=health_text)

        today = date.today().isoformat()
        today_done = sum(1 for task in tasks if task.get("done_date") == today)
        stat_values = {
            "total": total,
            "pending": pending,
            "progress": progress,
            "done": done,
            "today": today_done,
            "mismatch": mismatch,
        }
        for key, value in stat_values.items():
            label = self.stat_value_labels.get(key)
            if label:
                label.configure(text=str(value))
        self.update_filter_visuals()
        self.report_label.configure(
            text=(
                f"{shown}/{total} shown  |  {self.smart_view_var.get()}  |  "
                f"{self.category_filter_var.get()}  |  {self.sort_var.get()}  |  "
                f"W {pending}  D {progress}  S {done}  Today {today_done}  Fix {mismatch}"
            )
        )

        self.render_type_breakdown(tasks, force=force)

        target_statuses = columns_to_update or [status for status, _label in STATUSES]
        for status, _label in STATUSES:
            visible = [task for task in tasks if task.get("status", STATUS_PENDING) == status]
            count_label = self.column_count_labels.get(status)
            if count_label:
                count_label.configure(text=f"{len(visible)} tasks")
            if status not in target_statuses:
                continue
            
            signature = self.task_render_signature(visible)
            if not force and self.column_render_signatures.get(status) == signature:
                continue
            self.column_render_signatures[status] = signature
            
            # Performance Optimization: Widget Recycling
            # 1. Hide current visible items in this column
            prefix = f"{status}:"
            for key in [k for k in self.visible_group_keys if k.startswith(prefix)]:
                if key in self.group_frames:
                    self.group_frames[key].grid_remove()
                    self.visible_group_keys.discard(key)
            
            if not visible:
                for key in [key for key in self.render_batch_jobs if key.startswith(f"{status}:")]:
                    self.cancel_render_batch(key)
                # Still destroy column children if completely empty to show empty state
                for child in self.column_frames[status].winfo_children():
                    child.destroy()
                self.render_empty_state(status)
                continue
                
            # Remove empty state if it exists
            for child in self.column_frames[status].winfo_children():
                if isinstance(child, ctk.CTkFrame) and not hasattr(child, '_is_reused_group'):
                    child.destroy()

            row = 0
            for file_type in FILE_TYPES:
                grouped_tasks = [task for task in visible if task.get("type", "Other") == file_type]
                if grouped_tasks:
                    key = f"{status}:{file_type}"
                    if key in self.group_frames:
                        group = self.group_frames[key]
                        group.grid(row=row, column=0, pady=2, sticky="ew")
                        self.visible_group_keys.add(key)
                        # We still need to refresh the body if it's expanded
                        self.update_group_content(status, file_type, grouped_tasks)
                    else:
                        self.render_type_group(self.column_frames[status], status, file_type, grouped_tasks, row)
                        if key in self.group_frames:
                            self.group_frames[key]._is_reused_group = True
                    row += 1
        
        # Final cleanup: Destroy widgets that are no longer in the store
        active_ids = {task.get("id") for task in all_tasks}
        for task_id in list(self.card_widgets.keys()):
            if task_id not in active_ids:
                widget = self.card_widgets.pop(task_id)
                try:
                    widget.destroy()
                except Exception:
                    pass
                self.visible_card_ids.discard(task_id)
        self.after_idle(lambda positions=scroll_positions: self.restore_scroll_positions(positions))
        if self.search_var.get().strip():
            self.apply_live_search()

    def register_pulse(self, widget, color, option, persistent=False):
        return

    def animate_status(self):
        return

    def get_task_icon(self, task, size=44):
        target = task.get("link", "").strip()
        if not target:
            return self.get_type_icon(task.get("type", "Other"), size)
        key = f"{task.get('target_kind', '')}:{target}:{size}"
        if key in self.icon_images:
            return self.icon_images[key]

        image = None
        try:
            if is_url(target):
                image = fetch_favicon(target)
            elif Path(target).exists():
                image = extract_windows_icon(target)
        except Exception:
            image = None

        if not image:
            image = make_file_type_icon(task.get("type", "Other"), size)
        image = image.resize((size, size))
        self.icon_images[key] = ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
        return self.icon_images[key]

    def get_type_icon(self, file_type, size=34):
        key = f"{file_type}:{size}"
        if key not in self.type_icon_images:
            image = make_file_type_icon(file_type, size)
            self.type_icon_images[key] = ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
        return self.type_icon_images[key]

    def render_type_breakdown(self, tasks, force=False):
        signature = self.type_breakdown_render_signature(tasks)
        if self.type_breakdown_signature == signature:
            return
        self.type_breakdown_signature = signature
        for child in self.type_row.winfo_children():
            child.destroy()

        visible_types = []
        for file_type in FILE_TYPES:
            type_tasks = [task for task in tasks if task.get("type") == file_type]
            if type_tasks:
                visible_types.append((file_type, type_tasks))

        max_visible_types = 10
        hidden_type_count = max(0, len(visible_types) - max_visible_types)
        visible_types = visible_types[:max_visible_types]
        columns = min(5, max(1, len(visible_types)))
        for index in range(12):
            self.type_row.grid_columnconfigure(index, weight=0, uniform="")
        for index in range(columns):
            self.type_row.grid_columnconfigure(index, weight=1, uniform="type_chip")
        if not visible_types:
            ctk.CTkLabel(
                self.type_row,
                text="No workload to show",
                text_color=UI_MUTED,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
            return

        for index, (file_type, type_tasks) in enumerate(visible_types):
            meta = FILE_TYPES[file_type]
            total = len(type_tasks)
            category_active = self.category_filter_var.get() == file_type
            chip_color = meta["color"] if total else UI_BORDER
            chip_bg = chip_color if category_active else blend_color(chip_color, UI_SURFACE, 0.90)
            chip_hover = blend_color(chip_color, UI_SURFACE, 0.74)
            text_color = best_text_color(chip_color) if category_active else UI_TEXT

            chip = ctk.CTkButton(
                self.type_row,
                text=f"{file_type}  {total}",
                image=self.get_type_icon(file_type, 20),
                compound="left",
                command=lambda ft=file_type: self.set_category_filter(ft),
                fg_color=chip_bg,
                hover_color=chip_hover,
                text_color=text_color,
                corner_radius=10,
                border_width=2 if category_active else 1,
                border_color=chip_color,
                height=38,
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w",
            )
            chip.grid(row=index // columns, column=index % columns, padx=5, pady=5, sticky="ew")
        if hidden_type_count:
            more = ctk.CTkButton(
                self.type_row,
                text=f"+ {hidden_type_count} more",
                command=lambda: self.set_category_filter("All categories"),
                fg_color=UI_SURFACE,
                hover_color=UI_SURFACE_2,
                text_color=UI_MUTED,
                corner_radius=10,
                border_width=1,
                border_color=UI_BORDER,
                height=38,
                font=ctk.CTkFont(size=11, weight="bold"),
            )
            more.grid(row=len(visible_types) // columns, column=len(visible_types) % columns, padx=5, pady=5, sticky="ew")

    def toggle_group(self, status, file_type):
        key = f"{status}:{file_type}"
        expanded = not self.expanded_groups.get(key, False)
        self.expanded_groups[key] = expanded
        button = self.group_buttons.get(key)
        body = self.group_bodies.get(key)
        if expanded and body is not None and not body.winfo_children():
            self.column_render_signatures.pop(status, None)
            self.refresh(columns_to_update=[status], force=True)
            return
        if button:
            button.configure(text="Collapse" if expanded else "Expand")
        if body:
            if expanded:
                body.grid()
            else:
                body.grid_remove()

    def open_task_detail(self, task):
        self.focused_task_id = task.get("id")
        self.update_dynamic_island(schedule_next=False)
        TaskDetailWindow(self, task.copy())

    def render_type_group(self, parent, status, file_type, tasks, row):
        meta = FILE_TYPES[file_type]
        key = f"{status}:{file_type}"
        expanded = self.expanded_groups.get(key, False)
        group = ctk.CTkFrame(
            parent,
            fg_color=blend_color(meta["color"], UI_SURFACE, 0.94 if self.theme_name == "Light" else 0.88),
            corner_radius=8,
            border_width=1,
            border_color=blend_color(meta["color"], UI_BORDER, 0.22),
        )
        group.grid(row=row, column=0, pady=4, sticky="ew")
        group.grid_columnconfigure(0, weight=1)
        group._is_reused_group = True
        self.group_frames[key] = group
        self.visible_group_keys.add(key)
        self.group_task_ids[key] = [task.get("id") for task in tasks]

        header = ctk.CTkFrame(group, fg_color=blend_color(meta["color"], UI_SURFACE, 0.82), corner_radius=6)
        header.grid(row=0, column=0, padx=6, pady=4, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        chevron = "Collapse" if expanded else "Expand"
        toggle_button = ctk.CTkButton(
            header,
            text=chevron,
            width=70,
            height=22,
            corner_radius=4,
            fg_color=blend_color(meta["color"], UI_SURFACE, 0.70),
            hover_color=blend_color(meta["color"], UI_SURFACE, 0.55),
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=11),
            command=lambda status=status, file_type=file_type: self.toggle_group(status, file_type),
        )
        toggle_button.grid(row=0, column=3, padx=(6, 0), sticky="e")
        self.group_buttons[key] = toggle_button
        ctk.CTkLabel(
            header,
            text="",
            image=self.get_type_icon(file_type, 24),
            width=28,
            height=28,
        ).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkLabel(
            header,
            text=f"{file_type} ({len(tasks)})",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=UI_TEXT,
        ).grid(row=0, column=1, sticky="w")
        visible_tasks, limit = visible_slice(tasks, self.group_visible_limits.get(key), TASK_BATCH_SIZE)
        if len(tasks) > TASK_BATCH_SIZE:
            ctk.CTkLabel(
                header,
                text=f"Showing {len(visible_tasks)} of {len(tasks)}",
                text_color=UI_MUTED,
                font=ctk.CTkFont(size=10),
            ).grid(row=0, column=2, padx=6, sticky="e")

        body = ctk.CTkFrame(group, fg_color="transparent")
        body.grid(row=1, column=0, sticky="ew")
        body.grid_columnconfigure(0, weight=1)
        self.group_bodies[key] = body

        should_render_body = expanded or bool(self.search_var.get().strip())
        if not should_render_body:
            body.grid_remove()
            return

        list_header = ctk.CTkFrame(body, fg_color=blend_color(meta["color"], UI_SURFACE_2, 0.96), corner_radius=4)
        list_header.grid(row=0, column=0, padx=6, pady=(0, 2), sticky="ew")
        list_header.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(list_header, text="", width=34).grid(row=0, column=1, padx=(6, 4), pady=3)
        ctk.CTkLabel(list_header, text="File name", text_color=UI_MUTED, font=ctk.CTkFont(size=10, weight="bold")).grid(
            row=0, column=2, padx=(0, 6), pady=3, sticky="w"
        )
        ctk.CTkLabel(list_header, text="Action", text_color=UI_MUTED, font=ctk.CTkFont(size=10, weight="bold"), width=100).grid(
            row=0, column=3, padx=(0, 6), pady=3
        )

        self.schedule_card_batch(key, body, visible_tasks, start_row=1)
        if len(tasks) > len(visible_tasks):
            ctk.CTkButton(
                body,
                text=f"Load {min(TASK_BATCH_SIZE, len(tasks) - len(visible_tasks))} more",
                height=30,
                fg_color=UI_SURFACE_2,
                hover_color=UI_BORDER_SOFT,
                text_color=UI_TEXT,
                command=lambda status=status, file_type=file_type: self.load_more_group(status, file_type),
            ).grid(row=len(visible_tasks) + 1, column=0, padx=8, pady=(6, 10), sticky="ew")

        if not expanded:
            body.grid_remove()

    def update_group_content(self, status, file_type, tasks):
        key = f"{status}:{file_type}"
        body = self.group_bodies.get(key)
        if not body:
            return
        
        expanded = self.expanded_groups.get(key, False)
        should_render_body = expanded or bool(self.search_var.get().strip())
        
        if not should_render_body:
            body.grid_remove()
            return
        
        body.grid()
        visible_tasks, limit = visible_slice(tasks, self.group_visible_limits.get(key), TASK_BATCH_SIZE)
        
        # Hide all cards currently in this body
        for task_id in self.group_task_ids.get(key, []):
            if task_id in self.card_widgets:
                self.card_widgets[task_id].grid_remove()
                self.visible_card_ids.discard(task_id)
        
        self.group_task_ids[key] = [task.get("id") for task in tasks]
        
        self.schedule_card_batch(key, body, visible_tasks, start_row=1)

    def render_card(self, parent, task, row):
        status_meta = STATUS_META.get(task.get("status", STATUS_PENDING), STATUS_META[STATUS_PENDING])
        type_meta = FILE_TYPES.get(task.get("type"), FILE_TYPES.get("Other", {"color": status_meta["color"]}))
        type_color = type_meta.get("color", status_meta["color"])
        row_base = UI_SURFACE if row % 2 else UI_SURFACE_2
        row_bg = blend_color(type_color, row_base, 0.96 if self.theme_name == "Light" else 0.92)
        hover_bg = blend_color(type_color, row_base, 0.84 if self.theme_name == "Light" else 0.78)
        base_border = blend_color(type_color, UI_BORDER_SOFT, 0.38)
        title_text = task.get("name", "Untitled")
        if task.get("target_kind") == "folder" and task.get("project_stack"):
            title_text = f"{title_text} / {task.get('project_stack')}"
        display_title = title_text if len(title_text) <= 56 else f"{title_text[:53]}..."
        item = ctk.CTkFrame(
            parent,
            fg_color=row_bg,
            corner_radius=6,
            border_width=1,
            border_color=base_border,
        )
        item.grid(row=row, column=0, padx=5, pady=(0, 3), sticky="ew")
        item.grid_columnconfigure(1, minsize=32)
        item.grid_columnconfigure(2, weight=1)
        item.grid_columnconfigure(3, minsize=92)
        self.visible_card_ids.add(task.get("id"))
        self.card_widgets[task.get("id")] = item

        status_bar = ctk.CTkFrame(item, fg_color=type_color, width=4, height=28, corner_radius=2)
        status_bar.grid(row=0, column=0, padx=(0, 6), pady=4, sticky="w")

        task_icon = self.get_task_icon(task, 22)
        icon_label = ctk.CTkLabel(
            item,
            text="",
            image=task_icon,
            width=24,
            height=24,
            corner_radius=4,
            fg_color=UI_SURFACE_2,
        )
        icon_label.grid(row=0, column=1, padx=(0, 6), pady=4, sticky="w")
        icon_label.bind("<Button-1>", lambda _e, t=task: self.open_task_detail(t))

        title = ctk.CTkLabel(
            item,
            text=display_title,
            text_color=UI_TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
            justify="left",
            height=20,
        )
        title.grid(row=0, column=2, padx=(0, 6), pady=4, sticky="ew")
        title.bind("<Button-1>", lambda _e, t=task: self.open_task_detail(t))
        for hover_widget in (item, icon_label, title):
            hover_widget.bind(
                "<Enter>",
                lambda _e, w=item, bg=hover_bg, c=type_color: w.configure(fg_color=bg, border_color=c),
            )
            hover_widget.bind(
                "<Leave>",
                lambda _e, w=item, bg=row_bg, c=base_border: w.configure(fg_color=bg, border_color=c),
            )

        actions = ctk.CTkFrame(item, fg_color="transparent")
        actions.grid(row=0, column=3, padx=(0, 4), pady=4, sticky="e")
        ctk.CTkButton(
            actions,
            text="Open",
            width=40,
            height=24,
            corner_radius=4,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=DETAIL_BUTTONS["open"][0],
            hover_color=DETAIL_BUTTONS["open"][1],
            text_color=DETAIL_BUTTONS["open"][2],
            command=lambda t=task: self.open_target(t),
        ).grid(row=0, column=0, padx=(0, 4), sticky="e")

        ctk.CTkButton(
            actions,
            text="View",
            width=40,
            height=24,
            corner_radius=4,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=UI_SURFACE_2,
            hover_color=blend_color(type_color, UI_SURFACE, 0.80),
            text_color=UI_TEXT,
            command=lambda t=task: self.open_task_detail(t),
        ).grid(row=0, column=1, sticky="e")

    def fix_task_type(self, task):
        detected_type = task.get("detected_type")
        if not detected_type or detected_type not in FILE_TYPES:
            messagebox.showinfo("Cannot detect type", "This file/link type cannot be detected automatically.")
            return
        patch = {"type": detected_type, "category_mismatch": False}
        try:
            task_for_move = task.copy()
            task_for_move.update(patch)
            patch.update(organize_task_target(task_for_move, task.get("status", STATUS_PENDING)))
        except Exception as exc:
            messagebox.showerror(
                "Cannot move file",
                f"Could not move this file/link to {detected_type}:\n{task.get('link', '')}\n\n{exc}",
            )
            return
        old_status = task.get("status", STATUS_PENDING)
        self.store.update(task["id"], patch)
        self.refresh(columns_to_update=[old_status], force=True)

    def add_task(self):
        task = {
            "name": "",
            "type": "Other",
            "link": "",
            "target_kind": "file",
            "note": "",
            "status": STATUS_PENDING,
        }
        TaskForm(self, self.save_task, task=task, mode="file")

    def add_link(self):
        LinkForm(self, self.save_task)

    def add_project(self):
        task = {
            "name": "",
            "type": "Project" if "Project" in FILE_TYPES else "Other",
            "link": "",
            "target_kind": "folder",
            "note": "",
            "status": STATUS_PENDING,
        }
        TaskForm(self, self.save_task, task=task, mode="folder")

    def open_create_new(self):
        CreateNewWindow(self)

    def create_new_work(self, tool, name):
        file_type = tool.get("type", "Other")
        if file_type not in FILE_TYPES:
            file_type = "Other"
        kind = tool.get("kind", "file")
        clean_name = safe_filename(name)
        task_name = clean_name
        target = ""
        target_kind = kind

        try:
            if kind == "url":
                target = tool.get("url", "")
                target_kind = "url"
            elif kind == "folder":
                folder = status_folder(STATUS_PROGRESS, file_type)
                target_path = unique_destination(folder, clean_name)
                create_project_folder(target_path, clean_name)
                target = str(target_path)
                target_kind = "folder"
            else:
                extension = tool.get("extension", ".txt")
                if not extension.startswith("."):
                    extension = f".{extension}"
                if clean_name.lower().endswith(extension.lower()):
                    base_name = clean_name[: -len(extension)].rstrip(". ")
                    clean_name = safe_filename(base_name) if base_name else "Untitled"
                    task_name = clean_name
                filename = f"{clean_name}{extension}"
                target_path = unique_destination(status_folder(STATUS_PROGRESS, file_type), filename)
                write_blank_file(target_path, tool)
                target = str(target_path)
                target_kind = "file"

            task = {
                "id": str(uuid.uuid4()),
                "name": task_name,
                "type": file_type,
                "link": target,
                "target_kind": target_kind,
                "shortcut_path": None,
                "note": f"Created from {tool.get('name', 'Create New')}",
                "status": STATUS_PROGRESS,
                "date_added": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "done_date": None,
            }
            if target_kind == "url":
                task.update(organize_task_target(task, STATUS_PROGRESS))
            else:
                detected = infer_type_from_target(target)
                task.update(
                    {
                        "shortcut_path": None,
                        "detected_type": detected,
                        "category_mismatch": detected_type_mismatch(file_type, detected),
                        "file_key": normalized_file_key(target),
                        "project_stack": detect_project_stack(target) if target_kind == "folder" else "",
                    }
                )
            self.store.add_or_update(task)
            self.focused_task_id = task.get("id")
            self.last_work_fingerprint = folder_tree_fingerprint(work_root() / "Work")
            self.refresh(columns_to_update=[STATUS_PROGRESS], force=True)
            self.after(120, lambda created=task, selected=tool: self.open_created_work(created, selected))
            return True
        except Exception as exc:
            messagebox.showerror("Cannot create work", f"Could not create this work item:\n{name}\n\n{exc}")
            return False

    def open_created_work(self, task, tool):
        if tool.get("kind") == "folder" and tool.get("launcher"):
            launcher = tool.get("launcher")
            target = task.get("link", "")
            try:
                launcher_path = shutil.which(launcher)
                if launcher_path:
                    if launcher_path.lower().endswith((".cmd", ".bat")):
                        subprocess.Popen(
                            [os.environ.get("COMSPEC", "cmd.exe"), "/c", launcher_path, target],
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                        return
                    subprocess.Popen(
                        [launcher_path, target],
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    return
            except Exception:
                pass
        self.open_target(task)

    def edit_task(self, task):
        mode = task.get("target_kind") or ("url" if is_url(task.get("link", "")) else "file")
        if mode == "url":
            LinkForm(self, self.save_task, task=task.copy())
        else:
            TaskForm(self, self.save_task, task=task.copy(), mode=mode)

    def save_task(self, task):
        try:
            task.update(organize_task_target(task, task.get("status", STATUS_PENDING)))
        except Exception as exc:
            messagebox.showerror(
                "Cannot organize task",
                f"Could not organize this file/link:\n{task.get('link', '')}\n\n{exc}",
            )
            return

        self.store.add_or_update(task)
        self.refresh()

    def move_task(self, task, direction):
        order = [status for status, _label in STATUSES]
        current = order.index(task.get("status", STATUS_PENDING))
        new_status = order[max(0, min(len(order) - 1, current + direction))]
        self.set_task_status(task, new_status)

    def set_task_status(self, task, new_status):
        if task.get("status", STATUS_PENDING) == new_status:
            return

        old_status = task.get("status", STATUS_PENDING)
        patch = {"status": new_status}

        try:
            task_for_move = task.copy()
            task_for_move.update(patch)
            patch.update(organize_task_target(task_for_move, new_status))
        except Exception as exc:
            messagebox.showerror(
                "Cannot organize task",
                f"Could not organize this file/link for the new status:\n{task.get('link', '')}\n\n{exc}",
            )
            return

        if new_status == STATUS_DONE and task.get("status") != STATUS_DONE:
            patch["done_date"] = date.today().isoformat()
        if new_status != STATUS_DONE:
            patch["done_date"] = None
        self.store.update(task["id"], patch)
        self.refresh(columns_to_update=[old_status, new_status], force=True)

    def delete_task(self, task):
        if task.get("status") != STATUS_DONE:
            messagebox.showinfo("Delete blocked", "Delete is only allowed from the Done column.")
            return False
        if messagebox.askyesno("Delete task", f"Delete '{task.get('name')}'?"):
            self.store.delete(task["id"])
            self.refresh()
            return True
        return False

    def open_templates(self):
        TemplateWindow(self)

    def open_settings(self):
        SettingsWindow(self)

    def open_diagnostics(self):
        DiagnosticsWindow(self)

    def reload_category_settings(self, show_message=True):
        load_external_categories()
        rebuild_url_extension_types()
        ensure_status_folders()
        self.icon_images.clear()
        self.type_icon_images.clear()
        self.type_breakdown_signature = None
        self.column_render_signatures.clear()
        self.group_bodies.clear()
        self.group_buttons.clear()
        self.group_frames.clear()
        self.group_task_ids.clear()
        self.card_widgets.clear()
        self.visible_card_ids.clear()
        self.visible_group_keys.clear()
        self.store.sync_from_work_folders()
        self.template_store.sync_from_template_folders()
        self.refresh(force=True)
        if show_message:
            messagebox.showinfo("Reloaded", "Category rules were reloaded.")

    def rescan_work_folders(self, show_message=True):
        started = time.perf_counter()
        before_tasks = self.task_render_signature(self.store.tasks)
        before_templates = tuple(
            (
                template.get("id"),
                template.get("name"),
                template.get("type"),
                template.get("link"),
                template.get("target_kind"),
            )
            for template in self.template_store.templates
        )
        self.store.load()
        self.template_store.load()
        changed = self.store.sync_from_work_folders()
        template_changed = self.template_store.sync_from_template_folders()
        after_tasks = self.task_render_signature(self.store.tasks)
        after_templates = tuple(
            (
                template.get("id"),
                template.get("name"),
                template.get("type"),
                template.get("link"),
                template.get("target_kind"),
            )
            for template in self.template_store.templates
        )
        changed = changed or before_tasks != after_tasks
        template_changed = template_changed or before_templates != after_templates
        work_fingerprint = folder_tree_fingerprint(work_root() / "Work")
        self.last_work_fingerprint = work_fingerprint
        self.last_template_fingerprint = tuple(item for item in work_fingerprint if "\\template\\" in item[0])
        self.app_settings["work_fingerprint"] = fingerprint_signature(work_fingerprint)
        self.app_settings["template_fingerprint"] = fingerprint_signature(self.last_template_fingerprint)
        save_app_settings(self.app_settings)
        self.reset_board_render_cache()
        self.refresh(force=True)
        duration_ms = int((time.perf_counter() - started) * 1000)
        message = "Work and Template folders were reloaded." if changed or template_changed else "Reloaded from disk. No folder changes found."
        self.last_sync_info = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration_ms": duration_ms,
            "tasks_changed": changed,
            "templates_changed": template_changed,
            "task_count": len(self.store.tasks),
            "template_count": len(self.template_store.templates),
            "message": message,
        }
        self.record_diagnostic(
            "Sync",
            f"{message} tasks={len(self.store.tasks)} templates={len(self.template_store.templates)} duration={duration_ms}ms",
        )
        if show_message:
            messagebox.showinfo(
                "Rescan complete",
                message,
            )
        return changed or template_changed

    def save_template(self, template):
        try:
            template.update(organize_template_target(template))
        except Exception as exc:
            messagebox.showerror(
                "Cannot save template",
                f"Could not save this template:\n{template.get('link', '')}\n\n{exc}",
            )
            return
        self.template_store.add_or_update(template)

    def item_path_for_actions(self, item):
        if item.get("target_kind") == "url" or is_url(item.get("link", "")):
            return item.get("shortcut_path") or item.get("link", "")
        return item.get("link", "")

    def open_item_folder(self, item):
        target = self.item_path_for_actions(item)
        if not target:
            return
        if is_url(target):
            target = item.get("shortcut_path", "")
        path = Path(target)
        try:
            if path.exists():
                os.startfile(str(path.parent))
            else:
                messagebox.showwarning("Missing file", "This file or shortcut is missing.")
                self.refresh()
        except Exception as exc:
            messagebox.showerror("Cannot open folder", str(exc))

    def copy_item_path(self, item):
        target = item.get("link", "").strip()
        if not target:
            return
        copy_text_to_clipboard(self, target)
        messagebox.showinfo("Copied", "Copied URL/path to clipboard.")

    def copy_item_file(self, item):
        target = item.get("link", "").strip()
        if not target or is_url(target):
            return
        if not Path(target).exists():
            messagebox.showwarning("Missing file", "This file is missing.")
            self.refresh()
            return
        try:
            if copy_file_to_clipboard(target):
                messagebox.showinfo("Copied", "Copied file to clipboard. You can paste it into LINE or supported systems.")
            else:
                self.copy_item_path(item)
        except Exception as exc:
            messagebox.showerror("Cannot copy file", f"Copied path may be safer for this app.\n\n{exc}")

    def open_target(self, task):
        target = task.get("link", "").strip()
        if not target:
            return
        try:
            if target.lower().startswith(("http://", "https://")):
                webbrowser.open(target)
            else:
                os.startfile(target)
        except Exception as exc:
            messagebox.showerror("Cannot open", f"Could not open this file/link:\n{target}\n\n{exc}")



def run():
    # Ensure DPI awareness for maximum sharpness on Windows.
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = TaskBoardApp()
    app.mainloop()


if __name__ == "__main__":
    run()
