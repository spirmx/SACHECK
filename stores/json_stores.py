"""JSON-backed task and template stores."""

from __future__ import annotations

import json
import uuid
from datetime import date
from pathlib import Path
from typing import Callable


class TaskStore:
    def __init__(
        self,
        path: Path,
        *,
        task_file_key: Callable[[dict], str],
        scan_work_folder_tasks: Callable[[], list[dict]],
        item_exists: Callable[[dict], bool],
        status_done: str,
    ):
        self.path = path
        self.task_file_key = task_file_key
        self.scan_work_folder_tasks = scan_work_folder_tasks
        self.item_exists = item_exists
        self.status_done = status_done
        self.tasks = []
        self.load()

    def load(self):
        if not self.path.exists():
            self.tasks = []
            return
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            self.tasks = data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            backup = self.path.with_suffix(".broken.json")
            try:
                self.path.replace(backup)
            except OSError:
                pass
            self.tasks = []

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self.tasks, file, ensure_ascii=False, indent=2)

    def add(self, task):
        self.tasks.append(task)
        self.save()

    def update(self, task_id, patch):
        for task in self.tasks:
            if task["id"] == task_id:
                task.update(patch)
                break
        self.save()

    def delete(self, task_id):
        self.tasks = [task for task in self.tasks if task["id"] != task_id]
        self.save()

    def replace_type(self, old_type, new_type):
        changed = False
        for task in self.tasks:
            if task.get("type") == old_type:
                task["type"] = new_type
                changed = True
            if task.get("detected_type") == old_type:
                task["detected_type"] = new_type
                changed = True
        if changed:
            self.save()
        return changed

    def add_or_update(self, task):
        existing = False
        incoming_key = self.task_file_key(task)
        for item in self.tasks:
            same_id = item.get("id") == task.get("id")
            same_file = incoming_key and self.task_file_key(item) == incoming_key
            same_url = (
                task.get("target_kind") == "url"
                and item.get("target_kind") == "url"
                and item.get("link") == task.get("link")
            )
            if same_id or same_file or same_url:
                preserved_note = item.get("note", "")
                item.update(task)
                if preserved_note and not task.get("note"):
                    item["note"] = preserved_note
                existing = True
                break
        if not existing:
            self.tasks.append(task)
        self.save()

    def sync_from_work_folders(self):
        return self.sync_from_scanned(self.scan_work_folder_tasks())

    def sync_from_scanned(self, scanned):
        changed = False
        existing_by_key = {self.task_file_key(task): task for task in self.tasks if self.task_file_key(task)}
        existing_by_url = {
            task.get("link"): task
            for task in self.tasks
            if task.get("target_kind") == "url" and task.get("link")
        }

        for scanned_task in scanned:
            key = scanned_task["file_key"]
            current = existing_by_key.get(key)
            if current is None and scanned_task.get("target_kind") == "url":
                current = existing_by_url.get(scanned_task.get("link"))
            if current:
                patch = {
                    "name": current.get("name") or scanned_task["name"],
                    "type": scanned_task["type"],
                    "detected_type": scanned_task["detected_type"],
                    "project_stack": scanned_task.get("project_stack", ""),
                    "category_mismatch": scanned_task["category_mismatch"],
                    "link": scanned_task["link"],
                    "target_kind": scanned_task["target_kind"],
                    "shortcut_path": scanned_task["shortcut_path"],
                    "status": scanned_task["status"],
                    "file_key": scanned_task["file_key"],
                }
                if current.get("status") != self.status_done and scanned_task["status"] == self.status_done:
                    patch["done_date"] = date.today().isoformat()
                if scanned_task["status"] != self.status_done:
                    patch["done_date"] = None
                if any(current.get(name) != value for name, value in patch.items()):
                    current.update(patch)
                    changed = True
            else:
                scanned_task["id"] = str(uuid.uuid4())
                self.tasks.append(scanned_task)
                existing_by_key[key] = scanned_task
                changed = True

        before = len(self.tasks)
        self.tasks = [task for task in self.tasks if self.item_exists(task)]
        if len(self.tasks) != before:
            changed = True

        if changed:
            self.save()
        return changed

    def prune_missing(self):
        before = len(self.tasks)
        self.tasks = [task for task in self.tasks if self.item_exists(task)]
        if len(self.tasks) != before:
            self.save()


class TemplateStore:
    def __init__(
        self,
        path: Path,
        *,
        normalized_file_key: Callable[[str], str],
        scan_template_folder_items: Callable[[], list[dict]],
        item_exists: Callable[[dict], bool],
        is_canonical_template_path: Callable[[str, str], bool],
    ):
        self.path = path
        self.normalized_file_key = normalized_file_key
        self.scan_template_folder_items = scan_template_folder_items
        self.item_exists = item_exists
        self.is_canonical_template_path = is_canonical_template_path
        self.templates = []
        self.load()

    def load(self):
        if not self.path.exists():
            self.templates = []
            return
        try:
            with self.path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            self.templates = data if isinstance(data, list) else []
            if self.dedupe():
                self.save()
        except (OSError, json.JSONDecodeError):
            self.templates = []

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self.templates, file, ensure_ascii=False, indent=2)

    def dedupe(self):
        changed = False
        grouped = {}
        for template in self.templates:
            path_key = self.template_key(template)
            key = path_key or (
                template.get("name", "").strip().casefold(),
                template.get("type", "Other"),
                template.get("target_kind", "file"),
            )
            current = grouped.get(key)
            if current is None:
                grouped[key] = template
                continue

            changed = True
            current_path = current.get("link", "")
            template_path = template.get("link", "")
            if template.get("source") == "template_folder_scan":
                grouped[key] = template
            elif self.is_canonical_template_path(template_path, template.get("type", "Other")):
                grouped[key] = template
            elif not self.is_canonical_template_path(current_path, current.get("type", "Other")):
                grouped[key] = template

        self.templates = list(grouped.values())
        return changed

    def add_or_update(self, template):
        existing = False
        for item in self.templates:
            if item["id"] == template["id"]:
                item.update(template)
                existing = True
                break
        if not existing:
            for item in self.templates:
                same_link = self.template_key(item) and self.template_key(item) == self.template_key(template)
                same_url = (
                    item.get("target_kind") == "url"
                    and template.get("target_kind") == "url"
                    and item.get("link") == template.get("link")
                )
                if same_link or same_url:
                    item.update(template)
                    existing = True
                    break
        if not existing:
            self.templates.append(template)
        self.dedupe()
        self.save()

    def delete(self, template_id):
        self.templates = [template for template in self.templates if template["id"] != template_id]
        self.save()

    def replace_type(self, old_type, new_type):
        changed = False
        for template in self.templates:
            if template.get("type") == old_type:
                template["type"] = new_type
                changed = True
            if template.get("detected_type") == old_type:
                template["detected_type"] = new_type
                changed = True
        if changed:
            self.dedupe()
            self.save()
        return changed

    def template_key(self, template):
        if template.get("target_kind") == "url":
            return self.normalized_file_key(template.get("shortcut_path") or template.get("link", ""))
        return self.normalized_file_key(template.get("link", ""))

    def sync_from_template_folders(self):
        return self.sync_from_scanned(self.scan_template_folder_items())

    def sync_from_scanned(self, scanned):
        changed = False
        existing_by_key = {self.template_key(template): template for template in self.templates if self.template_key(template)}
        existing_by_url = {
            template.get("link"): template
            for template in self.templates
            if template.get("target_kind") == "url" and template.get("link")
        }

        for scanned_template in scanned:
            key = scanned_template["file_key"]
            current = existing_by_key.get(key)
            if current is None and scanned_template.get("target_kind") == "url":
                current = existing_by_url.get(scanned_template.get("link"))
            if current:
                patch = {
                    "name": current.get("name") or scanned_template["name"],
                    "type": scanned_template["type"],
                    "detected_type": scanned_template["detected_type"],
                    "category_mismatch": scanned_template["category_mismatch"],
                    "link": scanned_template["link"],
                    "target_kind": scanned_template["target_kind"],
                    "shortcut_path": scanned_template["shortcut_path"],
                    "file_key": scanned_template["file_key"],
                    "source": scanned_template["source"],
                }
                if any(current.get(name) != value for name, value in patch.items()):
                    current.update(patch)
                    changed = True
            else:
                scanned_template["id"] = str(uuid.uuid4())
                self.templates.append(scanned_template)
                existing_by_key[key] = scanned_template
                changed = True

        before = len(self.templates)
        self.templates = [template for template in self.templates if self.item_exists(template)]
        if len(self.templates) != before:
            changed = True

        if changed:
            self.dedupe()
            self.save()
        return changed

    def prune_missing(self):
        before = len(self.templates)
        self.templates = [template for template in self.templates if self.item_exists(template)]
        if len(self.templates) != before:
            self.save()
