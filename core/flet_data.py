import json
import os
import shutil
import time
import uuid
import webbrowser
import zlib
from datetime import datetime
from pathlib import Path

from config.category import EXTENSION_TYPES, URL_RULES
from core import file_intelligence
from core.app_paths import ACTIVITY_LOG_FILE, APP_SETTINGS_FILE, DATA_FILE, SNAPSHOT_DIR, TEMPLATE_FILE, UNDO_STACK_FILE, is_dev_runtime, work_folder
from core.create_tools import create_project_folder, tool_default_name, write_blank_file
from core.flet_constants import FILE_TYPES, STATUS_DONE, STATUS_FOLDERS, STATUS_PENDING, STATUS_PROGRESS

APP_NAME = "SA CHECK DEV" if is_dev_runtime() else "SA CHECK"
APP_VERSION = "1.0.9"
MANUAL_VERSION = "2026-06-18-user-guide"
DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES = 1

type_color_choices = [
    "#7C3AED", "#6366F1", "#2563EB", "#0284C7", "#0891B2", "#0F766E",
    "#16A34A", "#65A30D", "#D97706", "#EA580C", "#E11D48", "#DB2777",
    "#9333EA", "#475569", "#111827", "#22C55E", "#06B6D4", "#F59E0B",
]

CREATE_TOOLS = [
    {"type": name, "label": name}
    for name in FILE_TYPES
]


def load_json(path, fallback):
    if not path.exists():
        return fallback
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, type(fallback)) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


def retry_file_operation(operation, *, attempts=4, delay=0.18, label="File operation"):
    last_error = None
    for attempt in range(attempts):
        try:
            return operation()
        except (OSError, PermissionError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            time.sleep(delay * (attempt + 1))
    raise OSError(f"{label} failed after {attempts} attempts. Close any app using the file and try again. Last error: {last_error}")


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")

    def write_and_replace():
        with temp_path.open("w", encoding="utf-8") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)

    try:
        retry_file_operation(write_and_replace, label=f"Save {path.name}")
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def date_only(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return datetime.now().date().isoformat()
    return text[:10]


def normalize_task_dates(task):
    status = task.get("status") or STATUS_PENDING
    task["status"] = status
    if not task.get("date_added"):
        task["date_added"] = datetime.now().date().isoformat()
    if not task.get("status_date"):
        task["status_date"] = date_only(task.get("done_date") or task.get("date_added"))
    else:
        task["status_date"] = date_only(task.get("status_date"))
    if status == STATUS_DONE:
        task["done_date"] = date_only(task.get("done_date") or task.get("status_date") or task.get("date_added"))
    else:
        task["done_date"] = None
    return task


def normalize_tasks(tasks):
    if not isinstance(tasks, list):
        return []
    return [normalize_task_dates(task) for task in tasks if isinstance(task, dict)]


def load_tasks():
    return normalize_tasks(load_json(DATA_FILE, []))


def save_tasks(tasks):
    save_json(DATA_FILE, normalize_tasks(tasks))


def load_templates():
    return load_json(TEMPLATE_FILE, [])


def save_templates(templates):
    save_json(TEMPLATE_FILE, templates)


def load_settings():
    return load_json(APP_SETTINGS_FILE, {})


def save_settings(settings):
    save_json(APP_SETTINGS_FILE, settings)


def status_theme(status):
    palette = {
        STATUS_PENDING: ("#EFF6FF", "#2563EB"),
        STATUS_PROGRESS: ("#FFFBEB", "#D97706"),
        STATUS_DONE: ("#F0FDF4", "#16A34A"),
    }
    return palette.get(status, ("#F8FAFC", "#2563EB"))


def update_channel_url():
    return ""


def check_for_updates(manual=False):
    return None


def migrate_work_folder(new_root):
    settings = load_settings()
    settings["work_folder_path"] = str(new_root)
    save_settings(settings)
    Path(new_root).mkdir(parents=True, exist_ok=True)
    return Path(new_root)


def create_snapshot(reason: str):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = SNAPSHOT_DIR / f"{stamp}.json"
    data = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reason": reason,
        "tasks": load_tasks(),
        "templates": load_templates(),
        "settings": settings,
    }
    save_json(path, data)
    retention = int(settings.get("snapshot_retention") or 25)
    snapshots = sorted(SNAPSHOT_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    for old in snapshots[retention:]:
        try:
            old.unlink()
        except OSError:
            pass
    log_activity("Snapshot", f"Backup snapshot created: {reason}", {"file": str(path)})
    return path


def list_snapshots(limit=12):
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(SNAPSHOT_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
        data = load_json(path, {})
        rows.append({"path": str(path), "time": data.get("time", ""), "reason": data.get("reason", path.stem)})
    return rows


def restore_snapshot(snapshot_path: str):
    data = load_json(Path(snapshot_path), {})
    if not isinstance(data, dict):
        raise ValueError("Snapshot is invalid.")
    create_snapshot("Before snapshot restore")
    save_tasks(data.get("tasks", []))
    save_templates(data.get("templates", []))
    save_settings(data.get("settings", {}))
    log_activity("Restore snapshot", f"Restored snapshot from {data.get('time', Path(snapshot_path).stem)}", {"file": snapshot_path})
    return load_tasks(), load_templates()


def load_activity_log(limit=160):
    items = load_json(ACTIVITY_LOG_FILE, [])
    if not isinstance(items, list):
        return []
    return items[-limit:][::-1]


def log_activity(action: str, message: str, details: dict | None = None):
    items = load_json(ACTIVITY_LOG_FILE, [])
    if not isinstance(items, list):
        items = []
    items.append(
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "message": message,
            "details": details or {},
        }
    )
    if len(items) > 500:
        items = items[-500:]
    save_json(ACTIVITY_LOG_FILE, items)


def load_undo_stack(limit=30):
    items = load_json(UNDO_STACK_FILE, [])
    if not isinstance(items, list):
        return []
    return items[-limit:]


def push_undo(action: dict):
    items = load_undo_stack(30)
    action["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    items.append(action)
    save_json(UNDO_STACK_FILE, items[-30:])


def pop_undo():
    items = load_undo_stack(30)
    if not items:
        return None
    action = items.pop()
    save_json(UNDO_STACK_FILE, items)
    return action


def broken_items(tasks=None, templates=None):
    problems = []
    for source, items in [("Task", tasks if tasks is not None else load_tasks()), ("Template", templates if templates is not None else load_templates())]:
        for item in items:
            link = (item.get("link") or "").strip()
            shortcut = (item.get("shortcut_path") or "").strip()
            target = item_target(item)
            if not target:
                problems.append({"source": source, "reason": "No target", "target": "", "item": item})
                continue
            if link.startswith(("http://", "https://")) and shortcut and not Path(shortcut).exists():
                problems.append({"source": source, "reason": "Missing URL shortcut", "target": shortcut, "item": item})
                continue
            if target.startswith(("http://", "https://")):
                continue
            if not Path(target).exists():
                problems.append({"source": source, "reason": "Missing file/folder", "target": target, "item": item})
    return problems


def custom_file_types():
    settings = load_settings()
    items = settings.get("custom_file_types", [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict) and item.get("name")]


def file_type_config(name: str) -> dict:
    for item in custom_file_types():
        if item.get("name") == name:
            return item
    return {}


def runtime_file_types():
    names = list(FILE_TYPES)
    for item in custom_file_types():
        name = item.get("name", "").strip()
        if name and name not in names:
            names.append(name)
    return names


def custom_extension_types():
    mapping = {}
    for item in custom_file_types():
        name = item.get("name", "").strip()
        extensions = item.get("extensions", [])
        if isinstance(extensions, str):
            extensions = [part.strip() for part in extensions.replace(";", ",").split(",")]
        for extension in extensions:
            extension = str(extension).strip().lower()
            if not extension:
                continue
            if not extension.startswith("."):
                extension = f".{extension}"
            mapping[extension] = name
    return mapping


def work_signature():
    root = work_folder()
    if not root.exists():
        return {"count": 0, "mtime": 0, "hash": 0}
    count = 0
    newest_mtime = 0
    checksum = 0
    stack = [root]
    while stack:
        folder = stack.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if entry.name.startswith(".") or entry.name.startswith("~$"):
                        continue
                    try:
                        stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    count += 1
                    newest_mtime = max(newest_mtime, int(stat.st_mtime_ns))
                    relative = str(Path(entry.path).relative_to(root)).casefold()
                    checksum = zlib.crc32(f"{relative}|{stat.st_mtime_ns}|{stat.st_size}".encode("utf-8", "ignore"), checksum)
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
        except OSError:
            continue
    return {"count": count, "mtime": newest_mtime, "hash": checksum & 0xFFFFFFFF}


def infer_type(target):
    extension_types = {**EXTENSION_TYPES, **custom_extension_types()}
    url_extension_types = {**extension_types, ".doc?": "Word", ".xls?": "Excel", ".ppt?": "Slide"}
    return file_intelligence.infer_type_from_target(str(target), extension_types, url_extension_types, URL_RULES)


def make_task(name, target, target_kind=None, task_type=None, note="", status="pending"):
    target_text = str(target).strip()
    kind = target_kind or ("url" if target_text.startswith(("http://", "https://")) else ("folder" if Path(target_text).is_dir() else "file"))
    resolved_type = task_type or infer_type(target_text)
    today = datetime.now().date().isoformat()
    return {
        "id": str(uuid.uuid4()),
        "name": name.strip() or Path(target_text).stem or "Untitled task",
        "type": resolved_type,
        "detected_type": resolved_type,
        "status": status,
        "target_kind": kind,
        "link": target_text,
        "shortcut_path": "" if kind == "url" else target_text,
        "file_key": target_text.casefold() if kind != "url" else "",
        "note": note.strip(),
        "date_added": today,
        "status_date": today,
        "done_date": today if status == STATUS_DONE else None,
    }


def apply_status_date(task, status, force=False):
    today = datetime.now().date().isoformat()
    previous_status = task.get("status")
    status_changed = force or previous_status != status
    task["status"] = status
    if status_changed or not task.get("status_date"):
        task["status_date"] = today
    if status == STATUS_DONE:
        if status_changed or not task.get("done_date"):
            task["done_date"] = today
    elif status_changed or task.get("done_date"):
        task["done_date"] = None
    return task


def normalized_file_key(path: str) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve()).casefold()
    except OSError:
        return str(path).casefold()


def task_file_key(task) -> str:
    if task.get("target_kind") == "url":
        return normalized_file_key(task.get("shortcut_path") or task.get("link", ""))
    return normalized_file_key(task.get("link", ""))


def is_under_work(target: str) -> bool:
    if not target:
        return False
    try:
        path = Path(target).resolve()
        root = work_folder().resolve()
        return str(path).casefold().startswith(str(root).casefold())
    except OSError:
        return False


def status_folder(status: str, file_type: str = "Other") -> Path:
    safe_type = file_type if file_type in runtime_file_types() else "Other"
    return work_folder() / safe_type / STATUS_FOLDERS.get(status, STATUS_FOLDERS[STATUS_PENDING])


def template_folder(file_type: str = "Other") -> Path:
    safe_type = file_type if file_type in runtime_file_types() else "Other"
    return work_folder() / safe_type / "Template"


def ensure_status_folders():
    for file_type in runtime_file_types():
        for folder_name in STATUS_FOLDERS.values():
            (work_folder() / file_type / folder_name).mkdir(parents=True, exist_ok=True)
        template_folder(file_type).mkdir(parents=True, exist_ok=True)


def read_url_shortcut_target(path: Path) -> str:
    return file_intelligence.read_url_shortcut_target(path)


def detect_project_stack(target: str) -> str:
    return file_intelligence.detect_project_stack(target)


def scan_work_folder_tasks():
    tasks = []
    root = work_folder()
    if not root.exists():
        return tasks

    for file_type in runtime_file_types():
        for status, folder_name in STATUS_FOLDERS.items():
            folder = root / file_type / folder_name
            if not folder.exists():
                continue
            for file_path in folder.iterdir():
                if not (file_path.is_file() or file_path.is_dir()) or file_path.name.startswith("~$"):
                    continue
                if file_path.is_file() and file_path.suffix.lower() == ".url":
                    url_target = read_url_shortcut_target(file_path)
                    detected_type = infer_type(url_target) if url_target else "Link"
                    target_kind = "url"
                    link = url_target or str(file_path)
                    shortcut_path = str(file_path)
                else:
                    detected_type = infer_type(str(file_path))
                    target_kind = "folder" if file_path.is_dir() else "file"
                    link = str(file_path)
                    shortcut_path = None

                file_day = datetime.fromtimestamp(file_path.stat().st_mtime).date().isoformat()
                tasks.append(
                    {
                        "id": str(uuid.uuid4()),
                        "name": file_path.stem,
                        "type": file_type,
                        "detected_type": detected_type,
                        "project_stack": detect_project_stack(str(file_path)) if file_path.is_dir() else "",
                        "category_mismatch": False,
                        "link": link,
                        "target_kind": target_kind,
                        "shortcut_path": shortcut_path,
                        "note": "",
                        "status": status,
                        "date_added": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "status_date": file_day,
                        "done_date": file_day if status == STATUS_DONE else None,
                        "source": "folder_scan",
                        "file_key": normalized_file_key(str(file_path)),
                    }
                )
    return tasks


def scan_template_folder_items():
    templates = []
    root = work_folder()
    if not root.exists():
        return templates
    for file_type in runtime_file_types():
        folder = root / file_type / "Template"
        if not folder.exists():
            continue
        for file_path in folder.iterdir():
            if not (file_path.is_file() or file_path.is_dir()) or file_path.name.startswith("~$"):
                continue
            if file_path.is_file() and file_path.suffix.lower() == ".url":
                url_target = read_url_shortcut_target(file_path)
                link = url_target or str(file_path)
                target_kind = "url"
                shortcut_path = str(file_path)
            else:
                link = str(file_path)
                target_kind = "folder" if file_path.is_dir() else "file"
                shortcut_path = None
            templates.append(
                {
                    "id": str(uuid.uuid4()),
                    "name": file_path.stem,
                    "type": file_type,
                    "detected_type": infer_type(link),
                    "link": link,
                    "target_kind": target_kind,
                    "shortcut_path": shortcut_path,
                    "note": "",
                    "date_added": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "source": "template_folder_scan",
                    "file_key": normalized_file_key(str(file_path)),
                }
            )
    return templates


def should_prune_missing(item):
    source = item.get("source", "")
    if source in {"folder_scan", "template_folder_scan"}:
        return True
    if item.get("target_kind") == "url":
        return is_under_work(item.get("shortcut_path", "")) and not Path(item.get("shortcut_path", "")).exists()
    target = item.get("link", "")
    return is_under_work(target) and not Path(target).exists()


def merge_by_identity(current_items, scanned_items, prune_missing=False):
    changed = False
    by_key = {task_file_key(item): item for item in current_items if task_file_key(item)}
    by_url = {item.get("link"): item for item in current_items if item.get("target_kind") == "url" and item.get("link")}
    scanned_keys = {task_file_key(item) for item in scanned_items if task_file_key(item)}
    scanned_urls = {item.get("link") for item in scanned_items if item.get("target_kind") == "url" and item.get("link")}
    for item in scanned_items:
        key = task_file_key(item)
        current = by_key.get(key) or by_url.get(item.get("link"))
        if current:
            before = dict(current)
            item_id = current.get("id")
            note = current.get("note", "")
            usage_count = current.get("usage_count")
            last_used = current.get("last_used")
            previous_status = current.get("status")
            previous_status_date = current.get("status_date")
            previous_done_date = current.get("done_date")
            previous_date_added = current.get("date_added")
            current.update(item)
            current["id"] = item_id or current.get("id")
            if note and not item.get("note"):
                current["note"] = note
            if usage_count is not None:
                current["usage_count"] = usage_count
            if last_used:
                current["last_used"] = last_used
            if previous_date_added:
                current["date_added"] = previous_date_added
            if previous_status == current.get("status"):
                if previous_status_date:
                    current["status_date"] = previous_status_date
                if current.get("status") == STATUS_DONE and previous_done_date:
                    current["done_date"] = previous_done_date
            elif not current.get("status_date"):
                current["status_date"] = item.get("status_date") or datetime.now().date().isoformat()
            changed = changed or current != before
        else:
            current_items.append(item)
            if key:
                by_key[key] = item
            changed = True
    if prune_missing:
        before = len(current_items)
        current_items[:] = [
            item
            for item in current_items
            if (
                task_file_key(item) in scanned_keys
                or (item.get("target_kind") == "url" and item.get("link") in scanned_urls)
                or not should_prune_missing(item)
            )
        ]
        changed = changed or len(current_items) != before
    return changed


def sync_from_work(force=False):
    settings = load_settings()
    signature = work_signature()
    if not force and settings.get("work_signature") == signature:
        return load_tasks(), load_templates(), False
    tasks = load_tasks()
    templates = load_templates()
    tasks_changed = merge_by_identity(tasks, scan_work_folder_tasks(), prune_missing=True)
    templates_changed = merge_by_identity(templates, scan_template_folder_items(), prune_missing=True)
    if tasks_changed:
        save_tasks(tasks)
    if templates_changed:
        save_json(TEMPLATE_FILE, templates)
    if settings.get("work_signature") != signature:
        settings["work_signature"] = signature
        settings["last_sync_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_settings(settings)
    if tasks_changed or templates_changed:
        log_activity(
            "Sync",
            "Work folders were synchronized.",
            {"tasks": len(tasks), "templates": len(templates), "signature": signature},
        )
    return tasks, templates, tasks_changed or templates_changed


def create_task_from_tool(tool, title):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    safe_title = title.strip() or tool_default_name(tool, timestamp)
    kind = tool.get("kind")
    file_type = tool.get("type", "Other")
    if kind == "url":
        return create_task_from_source(safe_title, tool.get("url", ""), file_type=file_type, status=STATUS_PENDING)

    folder = status_folder(STATUS_PENDING, file_type)
    if kind == "folder":
        target = folder / safe_title
        create_project_folder(target, safe_title)
        return make_task(safe_title, str(target), target_kind="folder", task_type=file_type, status=STATUS_PENDING)

    extension = tool.get("extension", ".txt")
    target = folder / f"{safe_title}{extension}"
    counter = 2
    while target.exists():
        target = folder / f"{safe_title} ({counter}){extension}"
        counter += 1
    write_blank_file(target, tool)
    return make_task(safe_title, str(target), target_kind="file", task_type=file_type, status=STATUS_PENDING)


def unique_target_path(folder: Path, name: str, suffix: str = "") -> Path:
    target = folder / f"{name}{suffix}"
    counter = 2
    while target.exists():
        target = folder / f"{name} ({counter}){suffix}"
        counter += 1
    return target


def safe_item_name(name: str, fallback: str = "Untitled") -> str:
    cleaned = (name or "").strip() or fallback
    for char in '<>:"/\\|?*':
        cleaned = cleaned.replace(char, "-")
    return cleaned.strip(" .") or fallback


def write_url_shortcut(folder: Path, name: str, url: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = unique_target_path(folder, safe_item_name(name), ".url")
    retry_file_operation(lambda: target.write_text(f"[InternetShortcut]\nURL={url.strip()}\n", encoding="utf-8"), label=f"Write shortcut {target.name}")
    return target


def copy_source_to_folder(source: str, folder: Path, name: str) -> Path:
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError("Source file/folder was not found.")
    folder.mkdir(parents=True, exist_ok=True)
    safe_name = safe_item_name(name, source_path.stem if source_path.is_file() else source_path.name)
    if source_path.is_dir():
        target = unique_target_path(folder, safe_name)
        retry_file_operation(lambda: shutil.copytree(source_path, target), attempts=3, label=f"Copy folder {source_path.name}")
        return target
    target = unique_target_path(folder, safe_name, source_path.suffix)
    retry_file_operation(lambda: shutil.copy2(source_path, target), attempts=3, label=f"Copy file {source_path.name}")
    return target


def resolve_add_type(source: str, requested_type: str = "Other") -> str:
    requested = (requested_type or "Other").strip() or "Other"
    detected = infer_type(source)
    if requested in {"Other", "Link"} and detected not in {"Other", "Link"}:
        return detected
    if requested == "Other" and str(source).strip().startswith(("http://", "https://")):
        return detected if detected != "Other" else "Web"
    return requested


def create_task_from_source(name: str, source: str, file_type: str = "Other", note: str = "", status: str = STATUS_PENDING):
    safe_name = safe_item_name(name, "Untitled task")
    resolved_type = resolve_add_type(source, file_type)
    folder = status_folder(status, resolved_type)
    if str(source).strip().startswith(("http://", "https://")):
        shortcut = write_url_shortcut(folder, safe_name, source)
        task = make_task(safe_name, source, target_kind="url", task_type=resolved_type, note=note, status=status)
        task["shortcut_path"] = str(shortcut)
        task["file_key"] = normalized_file_key(str(shortcut))
        return task
    target = copy_source_to_folder(source, folder, safe_name)
    return make_task(target.stem if target.is_file() else target.name, str(target), target_kind="folder" if target.is_dir() else "file", task_type=resolved_type, note=note, status=status)


def create_template_from_source(name: str, source: str, file_type: str = "Other", note: str = ""):
    safe_name = safe_item_name(name, "Template")
    resolved_type = resolve_add_type(source, file_type)
    folder = template_folder(resolved_type)
    if str(source).strip().startswith(("http://", "https://")):
        target = write_url_shortcut(folder, safe_name, source)
        link = source
        target_kind = "url"
        shortcut_path = str(target)
    else:
        target = copy_source_to_folder(source, folder, safe_name)
        link = str(target)
        target_kind = "folder" if target.is_dir() else "file"
        shortcut_path = str(target)
    return {
        "id": str(uuid.uuid4()),
        "name": safe_name,
        "type": resolved_type,
        "detected_type": infer_type(link),
        "link": link,
        "target_kind": target_kind,
        "shortcut_path": shortcut_path,
        "note": note.strip(),
        "date_added": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "manual_template",
        "file_key": normalized_file_key(shortcut_path),
    }


def update_template_record(template, name: str, file_type: str = "Other", target: str = "", note: str = "", date_added: str = ""):
    safe_name = safe_item_name(name, template.get("name", "Template"))
    requested_target = (target or template.get("link") or template.get("shortcut_path") or "").strip()
    if not requested_target:
        raise ValueError("Template target is empty.")
    resolved_type = (file_type or template.get("type") or "Other").strip() or "Other"
    destination_folder = template_folder(resolved_type)
    destination_folder.mkdir(parents=True, exist_ok=True)

    old_targets = []
    old_shortcut = template.get("shortcut_path") or ""
    old_link = template.get("link") or ""
    if old_shortcut:
        old_targets.append(old_shortcut)
    if old_link and not old_link.startswith(("http://", "https://")):
        old_targets.append(old_link)
    old_keys = {normalized_file_key(path) for path in old_targets if path}

    def delete_old_targets(except_key=""):
        for old in dict.fromkeys(old_targets):
            if not old or normalized_file_key(old) == except_key:
                continue
            path = Path(old)
            if not path.exists() or not is_under_work(str(path)):
                continue
            if path.is_dir():
                retry_file_operation(lambda p=path: shutil.rmtree(p), label=f"Delete old template folder {path.name}")
            else:
                retry_file_operation(lambda p=path: p.unlink(), label=f"Delete old template file {path.name}")

    if requested_target.startswith(("http://", "https://")):
        shortcut = write_url_shortcut(destination_folder, safe_name, requested_target)
        final_key = normalized_file_key(str(shortcut))
        delete_old_targets(except_key=final_key)
        template.update(
            {
                "name": safe_name,
                "type": resolved_type,
                "detected_type": infer_type(requested_target),
                "link": requested_target,
                "target_kind": "url",
                "shortcut_path": str(shortcut),
                "note": note.strip(),
                "date_added": date_added or template.get("date_added") or datetime.now().strftime("%Y-%m-%d %H:%M"),
                "source": template.get("source") or "manual_template",
                "file_key": final_key,
            }
        )
        return template

    requested_path = Path(requested_target)
    if not requested_path.exists():
        raise FileNotFoundError(f"Template target not found: {requested_target}")

    requested_key = normalized_file_key(str(requested_path))
    if requested_key in old_keys and is_under_work(str(requested_path)):
        suffix = "" if requested_path.is_dir() else requested_path.suffix
        desired_stem = Path(safe_name).stem if Path(safe_name).suffix and not requested_path.is_dir() else safe_name
        desired_name = desired_stem if requested_path.is_dir() else f"{desired_stem}{suffix}"
        final_path = destination_folder / desired_name
        if normalized_file_key(str(final_path)) != requested_key:
            if final_path.exists():
                final_path = unique_target_path(final_path.parent, final_path.stem, final_path.suffix)
            retry_file_operation(lambda: requested_path.rename(final_path), label=f"Move template {requested_path.name}")
    else:
        final_path = copy_source_to_folder(str(requested_path), destination_folder, safe_name)
        delete_old_targets(except_key=normalized_file_key(str(final_path)))

    final_path = Path(final_path)
    template.update(
        {
            "name": final_path.stem if final_path.is_file() else final_path.name,
            "type": resolved_type,
            "detected_type": infer_type(str(final_path)),
            "link": str(final_path),
            "target_kind": "folder" if final_path.is_dir() else "file",
            "shortcut_path": str(final_path),
            "note": note.strip(),
            "date_added": date_added or template.get("date_added") or datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": template.get("source") or "manual_template",
            "file_key": normalized_file_key(str(final_path)),
        }
    )
    return template


def delete_item_target(item) -> bool:
    targets = []
    shortcut = item.get("shortcut_path") or ""
    link = item.get("link") or ""
    if shortcut:
        targets.append(shortcut)
    if link and not link.startswith(("http://", "https://")):
        targets.append(link)
    deleted = False
    for target in dict.fromkeys(targets):
        path = Path(target)
        if not path.exists() or not is_under_work(str(path)):
            continue
        if path.is_dir():
            retry_file_operation(lambda p=path: shutil.rmtree(p), label=f"Delete folder {path.name}")
        else:
            retry_file_operation(lambda p=path: p.unlink(), label=f"Delete file {path.name}")
        deleted = True
    return deleted


def item_target(item) -> str:
    link = (item.get("link") or "").strip()
    shortcut = (item.get("shortcut_path") or "").strip()
    if link.startswith(("http://", "https://")):
        return link
    return shortcut or link


def rename_task_target(task, new_name: str, new_target: str = "", new_file_type: str | None = None, new_status: str | None = None):
    clean_name = (new_name or task.get("name") or "Untitled task").strip()
    safe_name = safe_item_name(clean_name, task.get("name") or "Untitled task")
    current_target = item_target(task)
    requested_target = (new_target or current_target).strip()
    resolved_type = new_file_type or task.get("type", "Other")
    resolved_status = new_status or task.get("status", STATUS_PENDING)
    previous_status = task.get("status")

    if requested_target.startswith(("http://", "https://")):
        task["name"] = safe_name
        task["type"] = resolved_type
        apply_status_date(task, resolved_status)
        task["link"] = requested_target
        task["target_kind"] = "url"
        shortcut_text = task.get("shortcut_path") or ""
        shortcut = Path(shortcut_text) if shortcut_text else None
        if shortcut and shortcut.exists() and is_under_work(str(shortcut)):
            destination_folder = status_folder(resolved_status, resolved_type)
            destination_folder.mkdir(parents=True, exist_ok=True)
            target_path = destination_folder / f"{safe_name}.url"
            if normalized_file_key(str(target_path)) != normalized_file_key(str(shortcut)):
                if target_path.exists():
                    target_path = unique_target_path(target_path.parent, target_path.stem, target_path.suffix)
                retry_file_operation(lambda: shortcut.rename(target_path), label=f"Move shortcut {shortcut.name}")
            task["shortcut_path"] = str(target_path)
            task["file_key"] = normalized_file_key(str(target_path))
        else:
            target_path = write_url_shortcut(status_folder(resolved_status, resolved_type), safe_name, requested_target)
            task["shortcut_path"] = str(target_path)
            task["file_key"] = normalized_file_key(str(target_path))
        return task

    current_path = Path(current_target) if current_target else None
    requested_path = Path(requested_target) if requested_target else None
    if requested_target and (not requested_path or not requested_path.exists()):
        raise FileNotFoundError(f"Target file/folder was not found: {requested_target}")

    old_shortcut = task.get("shortcut_path") or ""
    if task.get("target_kind") == "url" and old_shortcut:
        shortcut_path = Path(old_shortcut)
        if shortcut_path.exists() and is_under_work(str(shortcut_path)):
            retry_file_operation(lambda: shortcut_path.unlink(), label=f"Delete old shortcut {shortcut_path.name}")

    if current_path and current_path.exists() and requested_path and normalized_file_key(str(current_path)) == normalized_file_key(str(requested_path)):
        suffix = "" if current_path.is_dir() else current_path.suffix
        desired_stem = Path(safe_name).stem if Path(safe_name).suffix and not current_path.is_dir() else safe_name
        desired_name = desired_stem if current_path.is_dir() else f"{desired_stem}{suffix}"
        destination_folder = current_path.parent
        if is_under_work(str(current_path)):
            destination_folder = status_folder(resolved_status, resolved_type)
            destination_folder.mkdir(parents=True, exist_ok=True)
        target_path = destination_folder / desired_name
        if normalized_file_key(str(target_path)) != normalized_file_key(str(current_path)):
            if target_path.exists():
                target_path = unique_target_path(target_path.parent, target_path.stem, target_path.suffix)
            retry_file_operation(lambda: current_path.rename(target_path), label=f"Move item {current_path.name}")
            requested_path = target_path

    final_target = str(requested_path) if requested_path else requested_target
    if final_target:
        task["link"] = final_target
        task["target_kind"] = "folder" if Path(final_target).is_dir() else "file"
        task["shortcut_path"] = final_target
        task["file_key"] = normalized_file_key(final_target)
        task["type"] = resolved_type
        apply_status_date(task, resolved_status, force=previous_status != resolved_status)
        task["name"] = Path(final_target).stem if Path(final_target).suffix else Path(final_target).name
    else:
        task["name"] = safe_name
        apply_status_date(task, resolved_status)
    return task


def create_task_from_template(template, title=""):
    file_type = template.get("type", "Other")
    source = item_target(template)
    if not source:
        raise ValueError("Template target is empty.")
    name = (title or template.get("name") or "Template work").strip()
    return create_task_from_source(name, source, file_type=file_type, note=template.get("note", ""), status=STATUS_PENDING)


def open_target(task):
    target = task.get("link") or task.get("shortcut_path") or ""
    if not target:
        return False
    if target.startswith(("http://", "https://")):
        webbrowser.open(target)
        return True
    if Path(target).exists():
        os.startfile(target)
        return True
    return False


def open_folder(task):
    for target in [task.get("link"), task.get("shortcut_path")]:
        if not target:
            continue
        path = Path(target)
        if path.is_dir():
            os.startfile(str(path))
            return True
        if path.exists():
            os.startfile(str(path.parent))
            return True
    return False


def file_meta(path):
    try:
        stat = path.stat()
        size = stat.st_size
        if size >= 1024 * 1024:
            size_text = f"{size / (1024 * 1024):.1f} MB"
        elif size >= 1024:
            size_text = f"{size / 1024:.1f} KB"
        else:
            size_text = f"{size} B"
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        return f"{modified}  |  {size_text}"
    except OSError:
        return "Unavailable"


def list_work_items_page(path, offset=0, limit=250):
    items = []
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                entry_path = Path(entry.path)
                items.append((entry.is_dir(), entry.name.casefold(), entry_path))
    except OSError:
        return [], 0
    items.sort(key=lambda item: (not item[0], item[1]))
    total = len(items)
    return [item[2] for item in items[offset : offset + limit]], total


def list_work_items(path):
    items, _total = list_work_items_page(path, 0, 250)
    return items
