import flet as ft
import os
from pathlib import Path
from datetime import datetime
import uuid

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
    create_snapshot,
    file_meta,
    infer_type,
    list_work_items_page,
    make_task,
    normalized_file_key,
    rename_task_target,
    status_folder,
)
from ui.dialogs import row_action_button, show_message, show_task_detail
from ui.flet_widgets import CENTER, border_all, dropdown, pad_only, pad_sym, task_icon
from ui.shared import DashboardContext

# Functions related to browser extracted from flet_dashboard.py

def go_to_browser_path(ctx: DashboardContext, path):
    if not Path(path).exists():
        show_message(ctx.page, "Folder not found", "This folder may have been moved or deleted.")
        ctx.current_browser_path["path"] = ctx.root_work
    else:
        ctx.current_browser_path["path"] = Path(path)
    ctx.state.update({"browser_limit": 160, "browser_selected": ""})
    ctx.render_current()

def breadcrumb_controls(ctx: DashboardContext):
    try:
        base = ctx.root_work.resolve()
        current = ctx.current_browser_path["path"].resolve()
    except OSError:
        base = ctx.root_work
        current = ctx.current_browser_path["path"]
    parts = [("Work", base)]
    if str(current).casefold().startswith(str(base).casefold()):
        relative = current.relative_to(base)
        walker = base
        for part in relative.parts:
            walker = walker / part
            parts.append((part, walker))
    controls = []
    for index, (label, path) in enumerate(parts):
        if index:
            controls.append(ft.Text("/", color=MUTED_2, size=14))
        controls.append(ft.TextButton(label, on_click=lambda _e, p=path: go_to_browser_path(ctx, p)))
    return controls


def type_style_fn(file_type):
    from ui.flet_dashboard import type_style # Workaround for now
    return type_style(file_type)

def status_style_values_fn(status, fallback_type="Other"):
    from ui.flet_dashboard import status_style_values # Workaround
    return status_style_values(status, fallback_type)


def render_browser(ctx: DashboardContext) -> None:
    ctx.header_title.value = "Work Browser & File Organizer"
    ctx.header_subtitle.value = "SA CHECK / Work"
    current = ctx.current_browser_path["path"]
    browser_limit = max(80, min(400, int(ctx.state.get("browser_limit", 160) or 160)))
    all_items, total_raw = list_work_items_page(current, 0, browser_limit)
    query = ctx.state.get("browser_search", "").strip().casefold()
    all_items = [path for path in all_items if not query or query in path.name.casefold() or query in path.suffix.casefold() or query in str(path).casefold()]
    sort_key = ctx.state.get("browser_sort", "Name")

    def item_sort_value(path):
        try:
            stat = path.stat()
        except OSError:
            stat = None
        if sort_key == "Modified":
            return stat.st_mtime if stat else 0
        if sort_key == "Size":
            return stat.st_size if stat else 0
        if sort_key == "Type":
            return ("Folder" if path.is_dir() else path.suffix.lower(), path.name.casefold())
        return path.name.casefold()

    all_items.sort(key=item_sort_value, reverse=bool(ctx.state.get("browser_desc")))
    task_by_key = {}
    for task in ctx.all_tasks:
        for target in [task.get("shortcut_path"), task.get("link")]:
            if not target or str(target).startswith(("http://", "https://")):
                continue
            task_by_key[normalized_file_key(str(target))] = task

    visible_records = []
    selected_key = ctx.state.get("browser_selected", "")

    def folder_label(path):
        if path.name == "Template":
            return "TEMPLATE"
        status_by_folder = {"Waiting": "WAITING", "Doing": "DOING", "Success": "SUCCESS"}
        return status_by_folder.get(path.name, "FOLDER")

    def browser_folder_style(path, record=None):
        name = path.name
        parent_name = path.parent.name
        status_colors = {
            "Waiting": (WAITING_BG, "#BFDBFE", WAITING_TEXT),
            "Doing": (DOING_BG, "#FED7AA", DOING_TEXT),
            "Success": (DONE_BG, "#BBF7D0", DONE_TEXT),
            "Template": ("#EEF2FF", "#A5B4FC", "#4F46E5"),
        }
        if name in status_colors:
            return status_colors[name]
        if parent_name in ctx.file_types() and name.casefold() in {"template", "waiting", "doing", "success"}:
            return status_colors.get(name, type_style_fn(parent_name))
        if name in ctx.file_types():
            return type_style_fn(name)
        if record and record.get("type") and record.get("type") not in {"Project", "Other"}:
            return type_style_fn(record.get("type"))
        semantic_colors = {
            "Project": ("#F5F3FF", "#C4B5FD", "#7C3AED"),
            "Canva": ("#F0FDFA", "#5EEAD4", "#0F766E"),
            "Diagram": ("#FAF5FF", "#D8B4FE", "#9333EA"),
            "Archive": ("#F8FAFC", "#CBD5E1", "#475569"),
            "Image": ("#FDF2F8", "#F9A8D4", "#DB2777"),
            "Video": ("#FFF1F2", "#FDA4AF", "#E11D48"),
            "Code": ("#ECFEFF", "#67E8F9", "#0891B2"),
            "Data": ("#F0FDF4", "#86EFAC", "#16A34A"),
        }
        return semantic_colors.get(name, ("#F8FAFC", "#CBD5E1", "#64748B"))

    def record_for_path(path):
        key = normalized_file_key(str(path))
        task = task_by_key.get(key)

        if path.is_dir():
            if path.parent.resolve() == ctx.root_work.resolve():
                path_type = path.name
            elif path.name in {"Waiting", "Doing", "Success", "Template"}:
                path_type = path.parent.name
            else:
                path_type = "Project"
        else:
            path_type = infer_type(path)

        if task:
            return {"kind": "task", "task": task, "path": path, "type": task.get("type", path_type), "status": task.get("status", STATUS_PENDING), "key": task.get("id") or key}

        status = "folder" if path.is_dir() else "untracked"
        if path.is_dir():
            if path.name == "Waiting":
                status = STATUS_PENDING
            elif path.name == "Doing":
                status = STATUS_PROGRESS
            elif path.name == "Success":
                status = STATUS_DONE

        return {"kind": "folder" if path.is_dir() else "file", "task": None, "path": path, "type": path_type, "status": status, "key": key}

    def children_for(path, limit=60):
        children, _total = list_work_items_page(path, 0, limit)
        if query:
            children = [child for child in children if query in child.name.casefold() or query in str(child).casefold()]
        children.sort(key=item_sort_value, reverse=bool(ctx.state.get("browser_desc")))
        return children

    total_items = len(all_items)
    ctx.progress_badge.value = "Synced (Realtime)" if ctx.settings.get("realtime_sync_enabled", True) else "Manual sync"
    selected_record = None
    preview_slot = {"control": None}

    def load_more(_event):
        ctx.state["browser_limit"] = min(total_raw, ctx.state.get("browser_limit", 160) + 160)
        ctx.render_current()

    def set_selected(record):
        ctx.state["browser_selected"] = record["key"]
        if preview_slot.get("control") is not None:
            preview_slot["control"].content = preview_panel(record)
            ctx.page.update()
        else:
            ctx.render_current()

    def move_record(record, status_value):
        task = record.get("task")
        if not task:
            ctx.add_or_update_from_path(record["path"])
            task = next((item for item in ctx.all_tasks if normalized_file_key(item.get("link", "")) == normalized_file_key(str(record["path"]))), None)
            if not task:
                return
        before = dict(task)
        create_snapshot("Before browser status move")
        try:
            rename_task_target(task, task.get("name", "Untitled task"), task.get("link", ""), new_file_type=task.get("type", record.get("type", "Other")), new_status=status_value)
        except Exception as exc:
            show_message(ctx.page, "Move failed", str(exc))
            return
        ctx.remember_task_action("Browser status move", task, before)
        # Note: save_tasks will happen in save_and_render
        ctx.save_and_render(f"Moved to {STATUS_LABELS.get(status_value)}.")

    def status_badge(record):
        status = record.get("status")
        if status == STATUS_PENDING:
            label, color, bg, badge_border = "WAITING", WAITING_TEXT, WAITING_BG, "#BFDBFE"
        elif status == STATUS_PROGRESS:
            label, color, bg, badge_border = "DOING", DOING_TEXT, DOING_BG, "#FED7AA"
        elif status == STATUS_DONE:
            label, color, bg, badge_border = "SUCCESS", DONE_TEXT, DONE_BG, "#BBF7D0"
        elif record.get("kind") == "folder":
            label = folder_label(record["path"])
            bg, badge_border, color = browser_folder_style(record["path"], record)
        else:
            label, color, bg, badge_border = "FILE", MUTED, "#F1F5F9", BORDER
        if record.get("kind") == "folder" and not record.get("task"):
            return ft.Container(
                height=28,
                padding=pad_sym(horizontal=10),
                border_radius=999,
                bgcolor=bg,
                border=border_all(1, badge_border),
                alignment=CENTER,
                content=ft.Text(label, size=10, weight=ft.FontWeight.W_900, color=color),
            )
        return ft.PopupMenuButton(
            content=ft.Container(
                height=28,
                padding=pad_sym(horizontal=10),
                border_radius=999,
                bgcolor=bg,
                border=border_all(1, color),
                alignment=CENTER,
                content=ft.Row(spacing=5, controls=[ft.Text(label, size=10, weight=ft.FontWeight.W_900, color=color), ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=13, color=color)]),
            ),
            items=[
                ft.PopupMenuItem(content="Move to Waiting", icon=ft.Icons.RADIO_BUTTON_UNCHECKED, on_click=lambda _e, r=record: move_record(r, STATUS_PENDING)),
                ft.PopupMenuItem(content="Move to Doing", icon=ft.Icons.PLAY_CIRCLE_OUTLINE, on_click=lambda _e, r=record: move_record(r, STATUS_PROGRESS)),
                ft.PopupMenuItem(content="Move to Success", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=lambda _e, r=record: move_record(r, STATUS_DONE)),
            ],
        )

    def record_row(record, compact=False):
        if not any(item["key"] == record["key"] for item in visible_records):
            visible_records.append(record)
        path = record["path"]
        task = record.get("task")
        icon, icon_color = task_icon(record["type"])
        is_selected = ctx.state.get("browser_selected") == record["key"]
        location = path.parent.name
        row_bg, row_border, row_accent = status_style_values_fn(record.get("status"), record.get("type", "Other"))
        type_bg, _type_border, _type_accent = type_style_fn(record.get("type", "Other"))
        if record.get("kind") == "folder" and not task:
            row_bg, row_border, row_accent = browser_folder_style(path, record)
            type_bg = "#FFFFFF"
            icon = ft.Icons.FOLDER_OUTLINED
            icon_color = row_accent

        def open_record(_event):
            if path.is_dir():
                go_to_browser_path(ctx, path)
            else:
                os.startfile(str(path))

        def detail_record(_event):
            detail_task = task or make_task(path.stem if path.is_file() else path.name, str(path), target_kind="folder" if path.is_dir() else "file", task_type=record["type"], note=file_meta(path) if path.is_file() else "Folder")
            show_task_detail(ctx.page, detail_task, ctx.save_and_render, ctx.all_tasks, runtime_file_types_fn=ctx.file_types)

        def copy_record(_event):
            ctx.page.clipboard.set(str(path))
            show_message(ctx.page, "Copied", "Path copied.")

        return ft.Container(
            height=52 if compact else 58,
            bgcolor="#EFF6FF" if is_selected else row_bg if compact else WHITE,
            border=border_all(1.5 if is_selected else 1, PRIMARY if is_selected else row_border if compact else BORDER),
            border_radius=14,
            padding=pad_only(left=10, right=4),
            on_click=lambda _e, r=record: set_selected(r),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=5, height=34, border_radius=999, bgcolor=row_accent),
                    ft.Container(width=34, height=34, border_radius=10, bgcolor=type_bg, border=border_all(1, row_border), alignment=CENTER, content=ft.Icon(icon, size=17, color=icon_color)),
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text(task.get("name", path.stem if path.is_file() else path.name) if task else path.name, size=14, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(
                                spacing=6,
                                controls=[
                                    ft.Text(f"Location: /{location}", size=11, color=MUTED_2, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Container(padding=pad_sym(horizontal=7, vertical=2), border_radius=999, bgcolor=type_bg, content=ft.Text(record.get("type", "Other"), size=10, weight=ft.FontWeight.W_800, color=icon_color)),
                                ],
                            ),
                        ],
                    ),
                    status_badge(record),
                    row_action_button("Open", ft.Icons.OPEN_IN_NEW, open_record, width=96),
                    row_action_button("Detail", ft.Icons.INFO_OUTLINE, detail_record, width=100),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        icon_size=18,
                        icon_color=MUTED_2,
                        items=[
                            ft.PopupMenuItem(content="Add to board" if not task else "Already on board", icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda _e, p=path: ctx.add_or_update_from_path(p)),
                            ft.PopupMenuItem(content="Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_record),
                            ft.PopupMenuItem(content="Show in folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=lambda _e, p=path: os.startfile(str(p if p.is_dir() else p.parent))),
                        ],
                    ),
                ],
            ),
        )

    def folder_card(path, level=0):
        record = record_for_path(path)
        visible_records.append(record)
        child_paths = children_for(path, 28 if level == 0 else 0) if path.is_dir() else []
        child_controls = []
        if path.is_dir():
            for child in child_paths:
                child_controls.append(record_row(record_for_path(child), compact=True))
            if not child_controls:
                child_controls.append(ft.Container(height=44, alignment=CENTER, content=ft.Text("Empty folder", size=12, color=MUTED_2)))
        icon, icon_color = task_icon(record["type"])
        title_text = path.name
        subtitle = f"{len(child_paths)} items" if path.is_dir() else file_meta(path)
        if record.get("task"):
            subtitle = f"Tracked | {STATUS_LABELS.get(record.get('status'), 'Waiting')} | {subtitle}"
        if not path.is_dir():
            return record_row(record)
        group_bg, group_border, group_accent = browser_folder_style(path, record)
        icon_bg = "#FFFFFF"
        icon = ft.Icons.FOLDER_OUTLINED
        icon_color = group_accent
        return ft.Container(
            bgcolor=group_bg,
            border=border_all(1, group_border),
            border_radius=16,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=10, color="#0A000000", offset=ft.Offset(0, 4)) if level == 0 else None,
            content=ft.ExpansionTile(
                expanded=False,
                maintain_state=True,
                tile_padding=pad_only(left=12, right=8),
                controls_padding=pad_only(left=10, right=10, bottom=10),
                title=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=5, height=34, border_radius=999, bgcolor=group_accent),
                        ft.Container(width=34, height=34, border_radius=10, bgcolor=icon_bg, border=border_all(1, group_border), alignment=CENTER, content=ft.Icon(icon, size=17, color=icon_color)),
                        ft.Column(spacing=1, expand=True, controls=[ft.Text(title_text, size=14, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Text(subtitle, size=11, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)]),
                        status_badge(record),
                        row_action_button("Open", ft.Icons.FOLDER_OPEN_OUTLINED, lambda _e, p=path: go_to_browser_path(ctx, p), width=96),
                        row_action_button("Detail", ft.Icons.INFO_OUTLINE, lambda _e, r=record: set_selected(r), width=98),
                    ],
                ),
                controls=[ft.Column(spacing=8, controls=child_controls)],
            ),
        )

    organizer_controls = [folder_card(path) for path in all_items]
    if total_raw > len(all_items):
        organizer_controls.append(
            ft.Container(
                height=52,
                alignment=CENTER,
                content=ft.Button(
                    f"Load more ({total_raw - len(all_items)} left)",
                    icon=ft.Icons.EXPAND_MORE,
                    on_click=load_more,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
                ),
            )
        )
    selected_record = next((record for record in visible_records if record["key"] == selected_key or str(record["path"]) == selected_key), None)
    if not selected_record and visible_records:
        selected_record = visible_records[0]
    ctx.state["browser_selected"] = selected_record["key"] if selected_record else ""

    toolbar = ft.Container(
        height=118,
        bgcolor="#F8FBFF",
        border=border_all(1, "#BFDBFE"),
        border_radius=18,
        padding=pad_sym(horizontal=18, vertical=10),
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=MUTED, on_click=lambda _e: go_to_browser_path(ctx, current.parent if current != ctx.root_work else ctx.root_work)),
                        ft.Row(spacing=4, controls=breadcrumb_controls(ctx), expand=True),
                        ft.Button("Open in Explorer", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=lambda _e: os.startfile(str(current)) if current.exists() else show_message(ctx.page, "Folder not found", "This folder may have been moved or deleted."), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                        ft.Button("Refresh", icon=ft.Icons.REFRESH, on_click=lambda _e: ctx.render_current(), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                    ],
                ),
                ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.TextField(
                            hint_text="Search this folder...",
                            prefix_icon=ft.Icons.SEARCH,
                            value=ctx.state.get("browser_search", ""),
                            height=44,
                            expand=True,
                            border_radius=14,
                            border_color=BORDER,
                            bgcolor="#F8FAFC",
                            on_change=lambda e: (ctx.state.update({"browser_search": e.control.value or "", "browser_limit": 160, "browser_selected": ""}), ctx.render_current()),
                        ),
                        dropdown(160, ctx.state.get("browser_sort", "Name"), ["Name", "Modified", "Type", "Size"], lambda e: (ctx.state.update({"browser_sort": e.control.value, "browser_selected": ""}), ctx.render_current())),
                        ft.IconButton(icon=ft.Icons.SOUTH if ctx.state.get("browser_desc") else ft.Icons.NORTH, tooltip="Toggle sort direction", on_click=lambda _e: (ctx.state.update({"browser_desc": not ctx.state.get("browser_desc"), "browser_selected": ""}), ctx.render_current())),
                        ft.PopupMenuButton(
                            content=ft.Container(height=42, padding=pad_sym(horizontal=14), border_radius=12, bgcolor="#F8FAFC", alignment=CENTER, content=ft.Row(spacing=7, controls=[ft.Icon(ft.Icons.TRAVEL_EXPLORE, size=17, color=MUTED), ft.Text("Jump", size=13, weight=ft.FontWeight.W_800, color=TEXT)])),
                            items=[
                                ft.PopupMenuItem(content="Work root", icon=ft.Icons.HOME_OUTLINED, on_click=lambda _e: go_to_browser_path(ctx, ctx.root_work)),
                                *[ft.PopupMenuItem(content=file_type, icon=ft.Icons.FOLDER_OUTLINED, on_click=lambda _e, p=ctx.root_work / file_type: go_to_browser_path(ctx, p)) for file_type in ctx.file_types()[:18]],
                            ],
                        ),
                    ],
                ),
            ],
        ),
    )
    listing = ft.Container(
        expand=True,
        bgcolor="#F8FBFF",
        border=border_all(1, "#DBEAFE"),
        border_radius=22,
        padding=18,
        content=ft.ListView(
            expand=True,
            spacing=10,
            controls=organizer_controls if organizer_controls else [ft.Container(expand=True, alignment=CENTER, content=ft.Text("No files found", color=MUTED_2, size=15))],
        ),
    )

    def preview_panel(record):
        if not record:
            return ft.Container(width=380, bgcolor=WHITE, border=border_all(1, BORDER), border_radius=22, padding=22, alignment=CENTER, content=ft.Text("Select a file to preview", color=MUTED_2))
        path = record["path"]
        task = record.get("task")
        is_dir = path.is_dir()
        item_type = record.get("type") or ("Project" if is_dir else infer_type(path))
        icon, icon_color = task_icon(item_type)
        preview_bg, preview_border, preview_accent = status_style_values_fn(record.get("status"), item_type)
        type_bg, _type_border, _type_accent = type_style_fn(item_type)
        board_task = task
        try:
            stat = path.stat()
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            size = "Folder" if is_dir else file_meta(path).split("  |  ")[-1]
        except OSError:
            modified = "-"
            size = "-"

        sub_items = []
        sub_total = 0
        sub_raw_total = 0
        sub_key = normalized_file_key(str(path))
        sub_query = str(ctx.state.setdefault("browser_sub_search", {}).get(sub_key, "") or "").strip().casefold()
        if is_dir:
            try:
                all_sub_items = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold()))
                sub_raw_total = len(all_sub_items)
                if sub_query:
                    all_sub_items = [item for item in all_sub_items if sub_query in item.name.casefold() or sub_query in str(item).casefold()]
                sub_total = len(all_sub_items)
                sub_items = all_sub_items[:80]
            except OSError:
                sub_items = []
                sub_total = 0
                sub_raw_total = 0

        def open_selected(_event):
            if not path.exists():
                show_message(ctx.page, "Missing item", "This file or folder was moved/deleted outside SA CHECK.")
                ctx.state["browser_selected"] = ""
                ctx.render_current()
                return
            if is_dir:
                go_to_browser_path(ctx, path)
            else:
                os.startfile(str(path))

        def detail_selected(_event):
            if not path.exists():
                show_message(ctx.page, "Missing item", "This file or folder was moved/deleted outside SA CHECK.")
                ctx.state["browser_selected"] = ""
                ctx.render_current()
                return
            detail_task = board_task or make_task(path.stem if path.is_file() else path.name, str(path), target_kind="folder" if is_dir else "file", task_type=item_type, note=file_meta(path) if path.is_file() else "Folder")
            show_task_detail(ctx.page, detail_task, ctx.save_and_render, ctx.all_tasks, runtime_file_types_fn=ctx.file_types)

        def copy_selected_path(_event):
            ctx.page.clipboard.set(str(path))
            show_message(ctx.page, "Copied", "Path copied.")

        def rename_selected(_event):
            if board_task:
                show_task_detail(ctx.page, board_task, ctx.save_and_render, ctx.all_tasks, runtime_file_types_fn=ctx.file_types)
            else:
                show_message(ctx.page, "Rename", "Add this item to the board first to rename safely.")

        status_text = STATUS_LABELS.get(board_task.get("status"), "Untracked") if board_task else "Untracked"
        board_text = board_task.get("name", path.name) if board_task else "Not on board"
        sub_list_height = min(220, max(88, 36 * min(len(sub_items), 5) + 22))

        def open_sub_item(item):
            def handler(_event):
                if item.exists():
                    os.startfile(str(item))
                else:
                    show_message(ctx.page, "Missing item", "This sub-item was moved or deleted.")
            return handler

        def sub_item_row(item):
            return ft.Container(
                height=32,
                border_radius=10,
                padding=pad_sym(horizontal=8),
                on_click=open_sub_item(item),
                content=ft.Row(
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.FOLDER_OUTLINED if item.is_dir() else ft.Icons.INSERT_DRIVE_FILE_OUTLINED, size=14, color=MUTED),
                        ft.Text(item.name, size=12, color=MUTED, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Icon(ft.Icons.OPEN_IN_NEW, size=13, color=MUTED_2),
                    ],
                ),
            )

        def update_sub_search(event):
            ctx.state.setdefault("browser_sub_search", {})[sub_key] = event.control.value or ""
            if preview_slot.get("control") is not None:
                preview_slot["control"].content = preview_panel(record)
                ctx.page.update()

        return ft.Container(
            width=380,
            bgcolor=preview_bg,
            border=border_all(1, preview_border),
            border_radius=22,
            padding=22,
            content=ft.Column(
                spacing=16,
                controls=[
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Container(width=6, height=58, border_radius=999, bgcolor=preview_accent),
                            ft.Container(width=58, height=58, border_radius=16, bgcolor=type_bg, border=border_all(1, preview_border), alignment=CENTER, content=ft.Icon(icon, size=30, color=icon_color)),
                            ft.Column(
                                expand=True,
                                spacing=4,
                                controls=[
                                    ft.Text(board_task.get("name", path.name) if board_task else path.name, size=18, weight=ft.FontWeight.W_800, color=TEXT, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(item_type, size=12, color=MUTED),
                                ],
                            ),
                        ],
                    ),
                    ft.Row(spacing=8, controls=[ft.Text("Current status:", size=12, weight=ft.FontWeight.W_800, color=MUTED), status_badge(record)]),
                    ft.Container(padding=pad_sym(horizontal=12, vertical=10), border_radius=14, bgcolor=WHITE, border=border_all(1, preview_border), content=ft.Text(str(path), size=12, color=MUTED, selectable=True)),
                    ft.Column(spacing=8, controls=[
                        ft.Text(f"Modified: {modified}", size=13, color=MUTED),
                        ft.Text(f"Size: {size}", size=13, color=MUTED),
                        ft.Text(f"Board task: {board_text}", size=13, color=MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"Board status: {status_text}", size=13, color=MUTED),
                    ]),
                    ft.Container(
                        visible=bool(sub_items),
                        padding=pad_sym(horizontal=12, vertical=10),
                        border_radius=14,
                        bgcolor="#F8FAFC",
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Row(
                                    spacing=8,
                                    controls=[
                                        ft.Text("Sub-items", size=12, weight=ft.FontWeight.W_900, color=TEXT, expand=True),
                                        ft.Text(f"{sub_total}/{sub_raw_total} items" if sub_query else f"{sub_total} items", size=11, weight=ft.FontWeight.W_800, color=MUTED_2),
                                    ],
                                ),
                                ft.TextField(
                                    hint_text="Find sub-item...",
                                    prefix_icon=ft.Icons.SEARCH,
                                    value=ctx.state.setdefault("browser_sub_search", {}).get(sub_key, ""),
                                    height=38,
                                    border_radius=12,
                                    border_color=BORDER,
                                    bgcolor=WHITE,
                                    text_size=12,
                                    on_change=update_sub_search,
                                ),
                                ft.Container(
                                    height=sub_list_height,
                                    content=ft.ListView(
                                        spacing=4,
                                        controls=[sub_item_row(item) for item in sub_items] if sub_items else [ft.Container(height=36, alignment=CENTER, content=ft.Text("No sub-items match", size=11, color=MUTED_2))],
                                    ),
                                ),
                                ft.Text(f"Showing first {len(sub_items)}. Open folder for all items.", size=10, color=MUTED_2, visible=sub_total > len(sub_items)),
                            ],
                        ),
                    ),
                    ft.Row(spacing=10, controls=[row_action_button("Open", ft.Icons.OPEN_IN_NEW, open_selected, width=104, primary=True), row_action_button("Detail", ft.Icons.INFO_OUTLINE, detail_selected, width=108)]),
                    ft.Row(spacing=10, controls=[ft.Button("Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_selected_path, expand=True, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))), ft.Button("Rename", icon=ft.Icons.EDIT_OUTLINED, on_click=rename_selected, expand=True, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)))]),
                ],
            ),
        )

    preview_host = ft.Container(content=preview_panel(selected_record))
    preview_slot["control"] = preview_host
    ctx.main_body.controls = [toolbar, ft.Row(spacing=18, expand=True, controls=[listing, preview_host])]
    ctx.page.update()
