import flet as ft
from datetime import datetime
import uuid
from pathlib import Path

from core.flet_constants import (
    BORDER,
    DOING_BG,
    DOING_TEXT,
    DONE_BG,
    DONE_TEXT,
    MUTED,
    MUTED_2,
    PRIMARY,
    STATUS_DONE,
    STATUS_PENDING,
    STATUS_PROGRESS,
    STATUS_LABELS,
    TEXT,
    WAITING_BG,
    WAITING_TEXT,
    WHITE,
)
from core.flet_data import (
    apply_status_date,
    create_snapshot,
    create_task_from_source,
    delete_item_target,
    load_settings,
    open_folder,
    open_target,
    push_undo,
    rename_task_target,
    safe_item_name,
    save_templates,
    update_template_record,
    log_activity,
)
from ui.flet_widgets import CENTER, border_all, dropdown, pad_only, pad_sym, task_icon
from ui.virtual_list import DEFAULT_BATCH_SIZE, next_visible_limit, visible_slice


# Copied from flet_dashboard to avoid circular import during extraction
def row_action_button(label, icon, on_click, width=124, primary=False):
    return ft.Button(
        label,
        icon=icon,
        on_click=on_click,
        width=width,
        height=36,
        style=ft.ButtonStyle(
            bgcolor=TEXT if primary else "#F8FAFC",
            color=WHITE if primary else "#1E3A8A",
            overlay_color="#1E293B" if primary else "#DBEAFE",
            padding=pad_sym(horizontal=8, vertical=0),
            shape=ft.RoundedRectangleBorder(radius=999),
            side=ft.BorderSide(1, "#CBD5E1" if not primary else TEXT),
            mouse_cursor=ft.MouseCursor.CLICK,
            animation_duration=120,
        ),
    )


def show_message(page, title, message, kind="info"):
    # Dummy fallback until we fully refactor how show_message is passed
    print(f"[{kind.upper()}] {title}: {message}")


def task_calendar_date(task):
    if task.get("status") == STATUS_DONE and task.get("done_date"):
        return str(task.get("done_date"))[:10]
    return str(task.get("status_date") or task.get("date_added") or datetime.now().date().isoformat())[:10]


def set_task_calendar_date(task, date_text):
    parsed = datetime.strptime((date_text or "").strip(), "%Y-%m-%d").date().isoformat()
    task["status_date"] = parsed
    if task.get("status") == STATUS_DONE:
        task["done_date"] = parsed
    else:
        task["done_date"] = None
    return parsed


def show_task_date_dialog(page, task, save_and_render, all_tasks=None):
    date_field = ft.TextField(
        label="Calendar date",
        hint_text="YYYY-MM-DD",
        value=task_calendar_date(task),
        border_radius=12,
        border_color=BORDER,
        prefix_icon=ft.Icons.EVENT_OUTLINED,
    )
    status_label = STATUS_LABELS.get(task.get("status"), "Waiting")

    def save_date(_event):
        before = dict(task)
        try:
            new_date = set_task_calendar_date(task, date_field.value)
        except ValueError:
            show_message(page, "Invalid date", "Use YYYY-MM-DD, for example 2026-06-15.")
            return
        create_snapshot("Before task date edit")
        if all_tasks is not None:
            push_undo({"kind": "task_restore", "action": "Edit calendar date", "task_id": task.get("id"), "before": before, "after": dict(task)})
        log_activity("Edit calendar date", f"{task.get('name', 'Untitled task')} set to {new_date}.", {"task_id": task.get("id"), "before": before, "after": dict(task)})
        page.pop_dialog()
        save_and_render("Calendar date updated.")

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Text("Edit calendar date", size=20, weight=ft.FontWeight.W_800, color=TEXT),
            content=ft.Column(
                width=420,
                height=150,
                spacing=12,
                controls=[
                    ft.Text(task.get("name", "Untitled task"), size=15, weight=ft.FontWeight.W_700, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(f"Status: {status_label}", size=13, color=MUTED),
                    date_field,
                ],
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                ft.Button("Save date", icon=ft.Icons.SAVE_OUTLINED, on_click=save_date, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
            ],
            bgcolor=WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
    )
    page.update()


def show_task_detail(page, task, save_and_render, all_tasks, is_template=False, template_to_work=None, template_records=None, runtime_file_types_fn=None, app_name="SA CHECK"):
    icon, icon_color = task_icon(task.get("type", "Other"))
    status_label = STATUS_LABELS.get(task.get("status"), "Template" if is_template else "Waiting")
    target = task.get("link", "") or task.get("shortcut_path", "")
    note = task.get("note") or "No note"
    current_status_label = STATUS_LABELS.get(task.get("status"), "Waiting")
    status_options = ["Waiting", "Doing", "Success"]
    status_lookup = {"Waiting": STATUS_PENDING, "Doing": STATUS_PROGRESS, "Success": STATUS_DONE}
    is_untracked_browser_item = bool(all_tasks is not None and not is_template and task not in all_tasks)

    def status_style(status):
        if status == STATUS_PROGRESS or status == "Doing":
            return "Doing", DOING_TEXT, DOING_BG
        if status == STATUS_DONE or status == "Success":
            return "Success", DONE_TEXT, DONE_BG
        if status == "Template":
            return "Template", PRIMARY, "#EFF6FF"
        return "Waiting", WAITING_TEXT, WAITING_BG

    def status_pill(status, label=None):
        resolved_label, color, bg = status_style(status)
        return ft.Container(
            padding=pad_sym(horizontal=12, vertical=7),
            border_radius=999,
            bgcolor=bg,
            border=border_all(1, color),
            content=ft.Row(
                spacing=7,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=8, height=8, border_radius=999, bgcolor=color),
                    ft.Text(label or resolved_label, size=12, weight=ft.FontWeight.W_900, color=color),
                ],
            ),
        )

    def set_status(status):
        before = dict(task)
        create_snapshot("Before detail status move")
        if load_settings().get("move_files_on_status", True):
            try:
                rename_task_target(task, task.get("name", "Untitled task"), task.get("link", ""), new_file_type=task.get("type", "Other"), new_status=status)
            except Exception as exc:
                show_message(page, "Move failed", str(exc))
                return
        else:
            apply_status_date(task, status)
        push_undo({"kind": "task_restore", "action": "Move status", "task_id": task.get("id"), "before": before, "after": dict(task)})
        log_activity("Move status", f"{task.get('name', 'Untitled task')} moved.", {"task_id": task.get("id"), "before": before, "after": dict(task)})
        page.pop_dialog()
        save_and_render("Status updated.")

    def delete_task(_event):
        def confirm_delete(_confirm_event):
            before = dict(task)
            create_snapshot("Before task delete")
            try:
                delete_item_target(task)
            except Exception as exc:
                show_message(page, "Delete failed", str(exc))
                return
            if task in all_tasks:
                all_tasks.remove(task)
            push_undo({"kind": "task_restore", "action": "Delete task", "task_id": task.get("id"), "before": before, "after": {}})
            log_activity("Delete task", f"{before.get('name', 'Untitled task')} removed from board.", {"task_id": before.get("id")})
            page.pop_dialog()
            save_and_render("Task deleted.")

        page.pop_dialog()
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Delete task?", size=20, weight=ft.FontWeight.W_800, color=TEXT),
                content=ft.Container(
                    border=border_all(1, "#FECACA"),
                    border_radius=14,
                    bgcolor="#FEF2F2",
                    padding=pad_sym(horizontal=14, vertical=12),
                    content=ft.Row(
                        spacing=10,
                        controls=[
                            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#DC2626", size=22),
                            ft.Text(f"This removes the {app_name} record and deletes the Work file/shortcut.", size=14, color="#991B1B"),
                        ],
                    ),
                ),
                actions=[
                    ft.TextButton("No", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Yes, delete", on_click=confirm_delete, style=ft.ButtonStyle(color=WHITE, bgcolor="#DC2626", overlay_color="#B91C1C", shape=ft.RoundedRectangleBorder(radius=10))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def edit_task(_event):
        name_field = ft.TextField(label="Task name", value=task.get("name", ""), border_radius=12, border_color=BORDER)
        file_types = runtime_file_types_fn() if runtime_file_types_fn else ["Word", "Excel", "Other"]
        type_field = dropdown(520, task.get("type", "Other"), file_types)
        status_field = dropdown(520, current_status_label, status_options)
        target_field = ft.TextField(label="Target path / URL", value=target, border_radius=12, border_color=BORDER)
        date_field = ft.TextField(label="Calendar date", value=task_calendar_date(task), hint_text="YYYY-MM-DD", border_radius=12, border_color=BORDER, prefix_icon=ft.Icons.EVENT_OUTLINED)
        note_field = ft.TextField(label="Note / description", value=task.get("note", ""), multiline=True, min_lines=10, max_lines=10, border_radius=12, border_color=BORDER)

        def save_edit(_save_event):
            new_target = target_field.value.strip()
            new_type = type_field.value or task.get("type", "Other")
            new_status = status_lookup.get(status_field.value, task.get("status", STATUS_PENDING))
            before = dict(task)
            try:
                parsed_date = datetime.strptime((date_field.value or "").strip(), "%Y-%m-%d").date().isoformat()
            except ValueError:
                show_message(page, "Invalid date", "Use YYYY-MM-DD, for example 2026-06-15.")
                return
            create_snapshot("Before task edit")
            try:
                rename_task_target(
                    task,
                    name_field.value.strip() or task.get("name", "Untitled task"),
                    new_target,
                    new_file_type=new_type,
                    new_status=new_status,
                )
            except Exception as exc:
                show_message(page, "Rename failed", str(exc))
                return
            task["type"] = new_type
            task["detected_type"] = task.get("detected_type") or task["type"]
            task["note"] = note_field.value.strip()
            set_task_calendar_date(task, parsed_date)
            push_undo({"kind": "task_restore", "action": "Edit task", "task_id": task.get("id"), "before": before, "after": dict(task)})
            log_activity("Edit task", f"{task.get('name', 'Untitled task')} edited.", {"task_id": task.get("id"), "before": before, "after": dict(task)})
            page.pop_dialog()
            save_and_render("Task updated.")

        page.pop_dialog()
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    spacing=16,
                    controls=[
                        ft.Container(width=58, height=58, border_radius=16, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=32, color=icon_color)),
                        ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text(f"Edit Task: {task.get('name', 'Untitled task')}", size=26, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text(modified_text(), size=13, color=MUTED),
                            ],
                        ),
                    ],
                ),
                content=ft.Row(
                    width=980,
                    height=520,
                    spacing=24,
                    controls=[
                        ft.Container(
                            expand=True,
                            border=border_all(1, BORDER),
                            border_radius=18,
                            padding=22,
                            content=ft.Column(
                                spacing=16,
                                controls=[
                                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=MUTED), ft.Text("Core Details", size=22, weight=ft.FontWeight.W_800, color=TEXT)]),
                                    name_field,
                                    ft.Column(spacing=8, controls=[ft.Text("File type", size=13, weight=ft.FontWeight.W_800, color=TEXT), type_field]),
                                    ft.Column(spacing=8, controls=[ft.Text("Status", size=13, weight=ft.FontWeight.W_800, color=TEXT), status_field]),
                                    date_field,
                                    ft.Column(spacing=8, controls=[ft.Text("Target Path / URL", size=13, weight=ft.FontWeight.W_800, color=TEXT), target_field]),
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            border=border_all(1, BORDER),
                            border_radius=18,
                            padding=22,
                            content=ft.Column(
                                spacing=16,
                                controls=[
                                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.EDIT_NOTE_OUTLINED, color=MUTED), ft.Text("Detailed Notes", size=22, weight=ft.FontWeight.W_800, color=TEXT)]),
                                    note_field,
                                ],
                            ),
                        ),
                    ],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Save Changes", icon=ft.Icons.SAVE_OUTLINED, on_click=save_edit, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def edit_template(_event):
        if not is_template:
            edit_task(_event)
            return
        name_field = ft.TextField(label="Template name", value=task.get("name", ""), border_radius=12, border_color=BORDER)
        file_types = runtime_file_types_fn() if runtime_file_types_fn else ["Word", "Excel", "Other"]
        type_field = dropdown(520, task.get("type", "Other"), file_types)
        target_field = ft.TextField(label="Template file / URL", value=target, border_radius=12, border_color=BORDER)
        date_field = ft.TextField(label="Template date", value=str(task.get("date_added") or datetime.now().strftime("%Y-%m-%d"))[:10], hint_text="YYYY-MM-DD", border_radius=12, border_color=BORDER, prefix_icon=ft.Icons.EVENT_OUTLINED)
        note_field = ft.TextField(label="Note / description", value=task.get("note", ""), multiline=True, min_lines=8, max_lines=8, border_radius=12, border_color=BORDER)

        def save_template_edit(_save_event):
            new_name = safe_item_name(name_field.value, task.get("name", "Template"))
            new_type = type_field.value or task.get("type", "Other")
            new_target = (target_field.value or target).strip()
            try:
                parsed_date = datetime.strptime((date_field.value or "").strip(), "%Y-%m-%d").date().strftime("%Y-%m-%d")
            except ValueError:
                show_message(page, "Invalid date", "Use YYYY-MM-DD, for example 2026-06-15.")
                return
            if not new_target:
                show_message(page, "Missing target", "Choose a template file or URL.")
                return
            before = dict(task)
            create_snapshot("Before template edit")
            try:
                update_template_record(task, new_name, file_type=new_type, target=new_target, note=note_field.value or "", date_added=parsed_date)
                task["id"] = before.get("id") or task.get("id")
                task["usage_count"] = before.get("usage_count", task.get("usage_count", 0))
                task["last_used"] = before.get("last_used", task.get("last_used", ""))
                if template_records is not None and task not in template_records:
                    template_records.append(task)
                save_templates(template_records if template_records is not None else [])
            except Exception as exc:
                show_message(page, "Template edit failed", str(exc))
                return
            log_activity("Edit template", f"{task.get('name', 'Template')} updated.", {"before": before, "after": dict(task)})
            page.pop_dialog()
            save_and_render("Template updated.")

        page.pop_dialog()
        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    spacing=16,
                    controls=[
                        ft.Container(width=58, height=58, border_radius=16, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=32, color=icon_color)),
                        ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text(f"Edit Template: {task.get('name', 'Template')}", size=24, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                ft.Text("Templates only store name, type, date, target, and note.", size=13, color=MUTED),
                            ],
                        ),
                    ],
                ),
                content=ft.Row(
                    width=900,
                    height=440,
                    spacing=22,
                    controls=[
                        ft.Container(
                            expand=True,
                            border=border_all(1, BORDER),
                            border_radius=18,
                            padding=20,
                            content=ft.Column(
                                spacing=14,
                                controls=[
                                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.ARTICLE_OUTLINED, color=MUTED), ft.Text("Template Details", size=20, weight=ft.FontWeight.W_800, color=TEXT)]),
                                    name_field,
                                    ft.Column(spacing=8, controls=[ft.Text("Template type", size=13, weight=ft.FontWeight.W_800, color=TEXT), type_field]),
                                    date_field,
                                    target_field,
                                ],
                            ),
                        ),
                        ft.Container(
                            expand=True,
                            border=border_all(1, BORDER),
                            border_radius=18,
                            padding=20,
                            content=ft.Column(
                                spacing=14,
                                controls=[
                                    ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.EDIT_NOTE_OUTLINED, color=MUTED), ft.Text("Template Note", size=20, weight=ft.FontWeight.W_800, color=TEXT)]),
                                    note_field,
                                ],
                            ),
                        ),
                    ],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (page.pop_dialog(), page.update())),
                    ft.Button("Save Template", icon=ft.Icons.SAVE_OUTLINED, on_click=save_template_edit, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=16),
            )
        )
        page.update()

    def modified_text():
        try:
            path = Path(target)
            if path.exists():
                return datetime.fromtimestamp(path.stat().st_mtime).strftime("Last modified: %A, %B %d, %Y, %H:%M")
        except OSError:
            pass
        return f"Added: {task.get('date_added', '-')}"

    def copy_target(_event):
        page.clipboard.set(target)
        show_message(page, "Copied", "Path copied.")

    def copy_to_waiting(_event):
        if not target:
            show_message(page, "Copy failed", "No target path or URL to copy.")
            return

        def create_copy():
            try:
                create_snapshot("Before copy task to Waiting")
                copied = create_task_from_source(
                    task.get("name", "Untitled task"),
                    target,
                    file_type=task.get("type", "Other"),
                    note=task.get("note", ""),
                    status=STATUS_PENDING,
                )
            except Exception as exc:
                show_message(page, "Copy failed", str(exc), kind="danger")
                return
            all_tasks.append(copied)
            push_undo({"kind": "task_restore", "action": "Copy to Waiting", "task_id": copied.get("id"), "before": {}, "after": dict(copied)})
            log_activity("Copy to Waiting", f"{task.get('name', 'Untitled task')} copied to Waiting.", {"source_task_id": task.get("id"), "task_id": copied.get("id")})
            page.pop_dialog()
            save_and_render(f"Copied to Waiting as {copied.get('name', 'Untitled task')}.")

        # For dialogs without duplicate guard passed in context, we just skip it for now and directly run it
        # TODO: wire run_with_duplicate_guard from DashboardContext
        create_copy()

    def add_detail_item_to_board(_event):
        if not is_untracked_browser_item:
            return
        try:
            create_snapshot("Before add browser detail to board")
            task["id"] = task.get("id") or str(uuid.uuid4())
            task["status"] = task.get("status") or STATUS_PENDING
            set_task_calendar_date(task, task_calendar_date(task))
            all_tasks.append(task)
            push_undo({"kind": "task_restore", "action": "Add browser item", "task_id": task.get("id"), "before": {}, "after": dict(task)})
            log_activity("Add browser item", f"{task.get('name', 'Untitled task')} added to board from detail.", {"task_id": task.get("id")})
            page.pop_dialog()
            save_and_render("Added to board.")
        except Exception as exc:
            show_message(page, "Add failed", str(exc))

    def template_to_work_action(_event):
        if template_to_work:
            page.pop_dialog()
            template_to_work(_event)
        else:
            show_message(page, "Template", "Open the Template page to create work from this item.")

    def action_button(label, icon_name, on_click, primary=False, danger=False, disabled=False):
        bg = "#2563EB" if primary else "#FEF2F2" if danger else "#F8FAFC"
        fg = WHITE if primary else "#DC2626" if danger else TEXT
        side_color = "#2563EB" if primary else "#FECACA" if danger else BORDER
        hover = "#1D4ED8" if primary else "#FEE2E2" if danger else "#E2E8F0"
        return ft.Button(
            label,
            icon=icon_name,
            on_click=on_click,
            expand=True,
            disabled=disabled,
            height=48,
            style=ft.ButtonStyle(
                bgcolor=bg,
                color=fg,
                overlay_color=hover,
                side=ft.BorderSide(1, side_color),
                shape=ft.RoundedRectangleBorder(radius=12),
            ),
        )

    meta_controls = [
        ft.Container(padding=pad_sym(horizontal=10, vertical=6), border_radius=9, bgcolor="#F1F5F9", content=ft.Text(f"{task.get('type', 'Other')} File", size=13, color=TEXT)),
        ft.Text("|", size=14, color=MUTED_2),
        ft.Container(padding=pad_sym(horizontal=10, vertical=6), border_radius=9, bgcolor="#F1F5F9", content=ft.Text(task.get("target_kind", "file").title(), size=13, color=TEXT)),
    ]
    if is_template:
        meta_controls.extend(
            [
                ft.Text("|", size=14, color=MUTED_2),
                ft.Container(padding=pad_sym(horizontal=10, vertical=6), border_radius=9, bgcolor="#F1F5F9", content=ft.Text("System Template", size=13, color=TEXT)),
            ]
        )
    else:
        meta_controls.extend(
            [
                ft.Text("|", size=14, color=MUTED_2),
                status_pill(task.get("status", STATUS_PENDING)),
                dropdown(170, current_status_label, status_options, lambda e: set_status(status_lookup.get(e.control.value, STATUS_PENDING))),
            ]
        )

    page.show_dialog(
        ft.AlertDialog(
            modal=True,
            title=ft.Row(
                spacing=24,
                controls=[
                    ft.Container(width=78, height=78, border_radius=22, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=42, color=icon_color)),
                    ft.Column(
                        spacing=8,
                        expand=True,
                        controls=[
                            ft.Text(task.get("name", "Untitled task"), size=32, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=meta_controls,
                            ),
                        ],
                    ),
                ],
            ),
            content=ft.Column(
                width=1020,
                height=540,
                spacing=16,
                controls=[
                    ft.Row(
                        spacing=20,
                        expand=True,
                        controls=[
                            ft.Container(
                                expand=True,
                                border=border_all(1, BORDER),
                                border_radius=18,
                                padding=18,
                                content=ft.Column(
                                    spacing=12,
                                    controls=[
                                        ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.ROUTE_OUTLINED, color=MUTED), ft.Text("Target Location", size=20, weight=ft.FontWeight.W_800, color=TEXT)]),
                                        ft.Container(
                                            height=128,
                                            border=border_all(1, BORDER),
                                            border_radius=14,
                                            bgcolor="#F8FAFC",
                                            padding=16,
                                            content=ft.Text(target or "No target", size=14, color=TEXT, selectable=True),
                                        ),
                                        ft.Button("Copy Path", icon=ft.Icons.CONTENT_COPY, on_click=copy_target, width=170, height=42),
                                    ],
                                ),
                            ),
                            ft.Container(
                                expand=True,
                                border=border_all(1, BORDER),
                                border_radius=18,
                                padding=18,
                                content=ft.Column(
                                    spacing=12,
                                    controls=[
                                        ft.Row(
                                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                            controls=[
                                                ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.EDIT_NOTE_OUTLINED, color=MUTED), ft.Text("Item Notes", size=20, weight=ft.FontWeight.W_800, color=TEXT)]),
                                                ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, tooltip="Edit details", on_click=edit_template if is_template else edit_task, disabled=is_untracked_browser_item),
                                            ],
                                        ),
                                        ft.Container(
                                            expand=True,
                                            border=border_all(1, BORDER),
                                            border_radius=14,
                                            bgcolor="#F8FAFC",
                                            padding=16,
                                            content=ft.Text(note if note != "No note" else "No note currently available for this item.", size=14, color=TEXT, selectable=True),
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=14,
                        controls=(
                            [
                                action_button("To Work", ft.Icons.ADD_TASK_OUTLINED, template_to_work_action, primary=True),
                                action_button("Edit Template", ft.Icons.EDIT_OUTLINED, edit_template),
                                action_button("Open Template", ft.Icons.OPEN_IN_NEW, lambda _e: open_target(task)),
                                action_button("Copy Path", ft.Icons.CONTENT_COPY, copy_target),
                                action_button("Show in Folder", ft.Icons.FOLDER_OPEN_OUTLINED, lambda _e: open_folder(task)),
                            ]
                            if is_template
                            else [
                                action_button("Open", ft.Icons.OPEN_IN_NEW, lambda _e: open_target(task), primary=not is_untracked_browser_item),
                                action_button("Add to Board", ft.Icons.ADD_TASK_OUTLINED, add_detail_item_to_board, primary=True) if is_untracked_browser_item else action_button("Edit", ft.Icons.EDIT_OUTLINED, edit_task),
                                action_button("Date", ft.Icons.EVENT_OUTLINED, lambda _e: show_task_date_dialog(page, task, save_and_render, all_tasks), disabled=is_untracked_browser_item),
                                action_button("Copy", ft.Icons.CONTENT_COPY, copy_to_waiting, disabled=is_untracked_browser_item),
                                action_button("Show in Folder", ft.Icons.FOLDER_OPEN_OUTLINED, lambda _e: open_folder(task)),
                                action_button("Delete", ft.Icons.DELETE_OUTLINE, delete_task, danger=True, disabled=is_untracked_browser_item),
                            ]
                        ),
                    ),
                    ft.Container(alignment=ft.Alignment(1, 0), content=ft.Text(modified_text(), size=13, color=MUTED_2)),
                ],
            ),
            actions=[ft.TextButton("Close", on_click=lambda _e: (page.pop_dialog(), page.update()))],
            bgcolor=WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
    )
    page.update()


def task_card(page, task, save_and_render, all_tasks):
    icon, icon_color = task_icon(task.get("type", "Other"))

    def copy_target(_event):
        page.clipboard.set(task.get("link", ""))
        show_message(page, "Copied", "Task target copied to clipboard.")

    def try_open(_event):
        if not open_target(task):
            show_message(page, "Cannot open", "The target file or link was not found.")

    def try_folder(_event):
        if not open_folder(task):
            show_message(page, "Cannot open folder", "No valid folder was found for this task.")

    def open_detail(_event):
        show_task_detail(page, task, save_and_render, all_tasks)

    def move_to(status):
        before = dict(task)
        create_snapshot("Before card status move")
        if load_settings().get("move_files_on_status", True):
            try:
                rename_task_target(task, task.get("name", "Untitled task"), task.get("link", ""), new_file_type=task.get("type", "Other"), new_status=status)
            except Exception as exc:
                show_message(page, "Move failed", str(exc))
                return
        else:
            apply_status_date(task, status)
        push_undo({"kind": "task_restore", "action": "Move status", "task_id": task.get("id"), "before": before, "after": dict(task)})
        log_activity("Move status", f"{task.get('name', 'Untitled task')} moved.", {"task_id": task.get("id"), "before": before, "after": dict(task)})
        save_and_render("Status updated.")

    menu = ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        icon_size=19,
        icon_color=MUTED_2,
        items=[
            ft.PopupMenuItem(content="Folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=try_folder),
            ft.PopupMenuItem(content="Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_target),
            ft.PopupMenuItem(content="Edit date", icon=ft.Icons.EVENT_OUTLINED, on_click=lambda _e: show_task_date_dialog(page, task, save_and_render, all_tasks)),
            ft.PopupMenuItem(content="Move to Waiting", icon=ft.Icons.RADIO_BUTTON_UNCHECKED, on_click=lambda _e: move_to(STATUS_PENDING)),
            ft.PopupMenuItem(content="Move to Doing", icon=ft.Icons.PLAY_CIRCLE_OUTLINE, on_click=lambda _e: move_to(STATUS_PROGRESS)),
            ft.PopupMenuItem(content="Move to Success", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=lambda _e: move_to(STATUS_DONE)),
        ],
    )

    return ft.Container(
        height=44,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=10,
        padding=pad_only(left=10, right=2),
        content=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(width=26, height=26, border_radius=8, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=15, color=icon_color)),
                ft.Text(task.get("name", "Untitled task"), size=13, color=TEXT, weight=ft.FontWeight.W_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                row_action_button("Open", ft.Icons.OPEN_IN_NEW, try_open, width=88),
                row_action_button("Detail", ft.Icons.INFO_OUTLINE, open_detail, width=92),
                menu,
            ],
        ),
    )


def grouped_task_card(page, task, save_and_render, all_tasks):
    return task_card(page, task, save_and_render, all_tasks)


def type_group_card(page, file_type, tasks, save_and_render, all_tasks, group_key=None, group_limits=None, on_more=None):
    icon, icon_color = task_icon(file_type)
    limit = (group_limits or {}).get(group_key, DEFAULT_BATCH_SIZE)
    visible_tasks, resolved_limit = visible_slice(tasks, limit, DEFAULT_BATCH_SIZE)
    hidden_count = max(0, len(tasks) - len(visible_tasks))
    controls = [grouped_task_card(page, task, save_and_render, all_tasks) for task in visible_tasks]
    if hidden_count:
        def load_more(_event):
            if group_limits is not None and group_key:
                group_limits[group_key] = next_visible_limit(resolved_limit, len(tasks), DEFAULT_BATCH_SIZE)
            if on_more:
                on_more()

        controls.append(
            ft.Container(
                height=44,
                border_radius=10,
                bgcolor="#F8FAFC",
                alignment=CENTER,
                content=ft.Button(
                    f"Show more ({hidden_count} left)",
                    icon=ft.Icons.EXPAND_MORE,
                    on_click=load_more,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                ),
            )
        )
    return ft.Container(
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=13,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=12, color="#10000000", offset=ft.Offset(0, 4)),
        content=ft.ExpansionTile(
            expanded=False,
            maintain_state=True,
            tile_padding=pad_only(left=10, right=8),
            controls_padding=pad_only(left=8, right=8, bottom=8),
            collapsed_bgcolor=WHITE,
            bgcolor=WHITE,
            title=ft.Row(
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=28, height=28, border_radius=9, bgcolor="#F8FAFC", alignment=CENTER, content=ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=16, color=MUTED)),
                    ft.Container(width=30, height=30, border_radius=9, bgcolor="#EFF6FF", alignment=CENTER, content=ft.Icon(icon, size=16, color=icon_color)),
                    ft.Text(file_type, size=13, weight=ft.FontWeight.W_800, color=TEXT, expand=True),
                    ft.Container(padding=pad_sym(horizontal=8, vertical=3), border_radius=999, bgcolor="#F8FAFC", content=ft.Text(str(len(tasks)), size=11, weight=ft.FontWeight.W_800, color=MUTED)),
                ],
            ),
            controls=[ft.Column(spacing=7, controls=controls)],
        ),
    )

def grouped_task_controls(page, tasks, save_and_render, all_tasks, column_key="", group_limits=None, on_more=None, file_types_fn=None):
    grouped = {}
    for task in tasks:
        grouped.setdefault(task.get("type", "Other"), []).append(task)
    controls = []
    ordered_types = [file_type for file_type in (file_types_fn() if file_types_fn else []) if file_type in grouped]
    ordered_types.extend(sorted(file_type for file_type in grouped if file_type not in ordered_types))
    for file_type in ordered_types:
        controls.append(type_group_card(page, file_type, grouped[file_type], save_and_render, all_tasks, f"{column_key}:{file_type}", group_limits, on_more))
    return controls

def kanban_column(page, title, tasks, tint, accent, save_and_render, all_tasks, grouped=True, group_limits=None, on_more=None, file_types_fn=None):
    if tasks:
        controls = grouped_task_controls(page, tasks, save_and_render, all_tasks, title, group_limits, on_more, file_types_fn) if grouped else [task_card(page, task, save_and_render, all_tasks) for task in tasks]
        body = ft.ListView(spacing=7, expand=True, controls=controls)
    else:
        body = ft.Container(expand=True, alignment=CENTER, content=ft.Text("No tasks yet", size=13, weight=ft.FontWeight.W_500, color=MUTED_2))
    return ft.Container(
        expand=True,
        bgcolor=tint,
        border=border_all(1, BORDER),
        border_radius=14,
        padding=8,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Container(
                    height=36,
                    padding=pad_sym(horizontal=10, vertical=0),
                    border_radius=10,
                    bgcolor=accent,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(
                                spacing=8,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Container(width=4, height=20, border_radius=999, bgcolor="#FFFFFF99"),
                                    ft.Text(title, size=14, weight=ft.FontWeight.W_700, color=WHITE),
                                    ft.Container(padding=pad_sym(horizontal=7, vertical=2), border_radius=999, bgcolor="#FFFFFFE8", content=ft.Text(str(len(tasks)), size=11, weight=ft.FontWeight.W_800, color=accent)),
                                ],
                            ),
                            ft.Icon(ft.Icons.MORE_VERT, size=18, color="#FFFFFFCC"),
                        ],
                    ),
                ),
                ft.Container(expand=True, content=body),
            ],
        ),
    )
