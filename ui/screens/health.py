import flet as ft
from datetime import date, datetime
from pathlib import Path

from core.flet_constants import (
    BORDER, DOING_BG, DOING_TEXT, DONE_BG, DONE_TEXT, MUTED, MUTED_2,
    PRIMARY, STATUS_DONE, STATUS_PENDING, STATUS_PROGRESS, TEXT, WHITE
)
from core.flet_data import DATA_FILE, APP_NAME
from ui.dialogs import show_message
from ui.flet_widgets import CENTER, border_all, pad_only, pad_sym, task_icon, row_action_button
from ui.shared import DashboardContext

def render_health(ctx: DashboardContext) -> None:
    ctx.header_title.value = "Health Center"
    ctx.header_subtitle.value = f"{APP_NAME} / Safety & Activity"

    # Lazy loads for health checks
    try:
        from core.flet_data import (
            load_templates, broken_items, load_activity_log, list_snapshots,
            save_templates, save_tasks, log_activity, create_snapshot, push_undo,
            normalized_file_key, infer_type, item_target, restore_snapshot,
            load_settings, create_task_from_source, rename_task_target,
            update_template_record
        )
        templates = load_templates()
        problems = broken_items(ctx.all_tasks, templates)
        activity = load_activity_log(80)
        snapshots = list_snapshots(5)
    except ImportError:
        templates, problems, activity, snapshots = [], [], [], []
        save_templates, save_tasks, log_activity = None, None, None
        create_snapshot, push_undo, normalized_file_key, infer_type, item_target = None, None, None, None, None
        restore_snapshot, load_settings, create_task_from_source = None, None, None
        rename_task_target, update_template_record = None, None

    # We need root_work for health checks. Get it from ctx or settings.
    root_work_str = ctx.settings.get("root_work") or ctx.settings.get("work_folder_path") or ""
    root_work = Path(root_work_str) if root_work_str else Path(ctx.root_work)

    smart_health_on = ctx.settings.get("smart_health_enabled", True)
    workload_on = ctx.settings.get("workload_hints_enabled", True)
    stale_limit = int(ctx.settings.get("stale_doing_days") or 7)
    zombie_limit = int(ctx.settings.get("zombie_waiting_days") or 30)
    overload_doing_limit = int(ctx.settings.get("overload_doing_limit") or 4)
    overload_total_limit = int(ctx.settings.get("overload_total_limit") or 10)
    health_filter = ctx.state.get("health_filter", "All")

    def path_writable(path):
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".sacheck_health_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except Exception:
            return False

    offline_mode = bool(ctx.settings.get("offline_mode", False))
    update_url = str(ctx.update_channel_url() or "")
    health_checks = [
        {
            "label": "Work folder",
            "ok": root_work.exists() and root_work.is_dir(),
            "detail": str(root_work),
            "icon": ft.Icons.FOLDER_OUTLINED,
        },
        {
            "label": "Data folder",
            "ok": path_writable(DATA_FILE.parent),
            "detail": str(DATA_FILE.parent),
            "icon": ft.Icons.SAVE_OUTLINED,
        },
        {
            "label": "Tasks file",
            "ok": isinstance(ctx.all_tasks, list),
            "detail": f"{len(ctx.all_tasks)} records loaded",
            "icon": ft.Icons.FACT_CHECK_OUTLINED,
        },
        {
            "label": "Templates file",
            "ok": isinstance(templates, list),
            "detail": f"{len(templates)} records loaded",
            "icon": ft.Icons.ARTICLE_OUTLINED,
        },
        {
            "label": "Update channel",
            "ok": offline_mode or bool(update_url),
            "detail": "Offline mode is on" if offline_mode else ("Online checks enabled" if update_url else "Update channel is not configured"),
            "icon": ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED,
        },
        {
            "label": "Snapshots",
            "ok": bool(snapshots),
            "detail": f"{len(snapshots)} recent snapshots",
            "icon": ft.Icons.BACKUP_OUTLINED,
        },
    ]
    health_ok_count = sum(1 for check in health_checks if check["ok"])
    broken_tasks = [problem for problem in problems if problem.get("source") == "Task"]
    broken_templates = [problem for problem in problems if problem.get("source") == "Template"]

    def problem_matches_filter(problem):
        reason = problem.get("reason", "")
        if health_filter == "Tasks":
            return problem.get("source") == "Task"
        if health_filter == "Templates":
            return problem.get("source") == "Template"
        if health_filter == "Missing":
            return reason == "Missing file/folder"
        if health_filter == "No target":
            return reason == "No target"
        if health_filter == "URL shortcut":
            return reason == "Missing URL shortcut"
        return True

    visible_problems = [problem for problem in problems if problem_matches_filter(problem)]

    def task_calendar_date(task):
        return task.get("date_added") or datetime.now().date().isoformat()

    def task_date_value(task):
        try:
            return datetime.strptime(str(task_calendar_date(task))[:10], "%Y-%m-%d").date()
        except ValueError:
            return date.today()

    type_mismatches = [
        task
        for task in ctx.all_tasks
        if task.get("detected_type")
        and task.get("type")
        and task.get("detected_type") not in {"Other", "Link"}
        and task.get("type") != task.get("detected_type")
    ][:12]

    stale_doing = [
        task
        for task in ctx.all_tasks
        if workload_on and task.get("status") == STATUS_PROGRESS and (date.today() - task_date_value(task)).days >= stale_limit
    ][:12]

    zombie_waiting = [
        task
        for task in ctx.all_tasks
        if workload_on and task.get("status") == STATUS_PENDING and (date.today() - task_date_value(task)).days >= zombie_limit
    ][:12]

    day_load = {}
    for task in ctx.all_tasks:
        day_key = str(task_calendar_date(task))[:10]
        day_load.setdefault(day_key, {"total": 0, "doing": 0, "waiting": 0})
        day_load[day_key]["total"] += 1
        if task.get("status") == STATUS_PROGRESS:
            day_load[day_key]["doing"] += 1
        if task.get("status") == STATUS_PENDING:
            day_load[day_key]["waiting"] += 1

    overloaded_days = [
        (day_key, counts)
        for day_key, counts in sorted(day_load.items(), key=lambda row: row[0], reverse=True)
        if workload_on and (counts["doing"] >= overload_doing_limit or counts["total"] >= overload_total_limit)
    ][:8]

    duplicate_groups = {}
    for item in [*ctx.all_tasks, *templates]:
        key = (str(item.get("name", "")).strip().casefold(), str(item.get("type", "Other")).casefold())
        if key[0]:
            duplicate_groups.setdefault(key, []).append(item)
    duplicate_items = [items for items in duplicate_groups.values() if len(items) > 1][:8]

    inbox_path = root_work / "Inbox"
    inbox_items = []
    if inbox_path.exists():
        try:
            inbox_items = [item for item in sorted(inbox_path.iterdir(), key=lambda p: p.name.casefold()) if not item.name.startswith("~$")][:10]
        except OSError:
            inbox_items = []

    smart_findings = len(type_mismatches) + len(stale_doing) + len(zombie_waiting) + len(overloaded_days) + len(duplicate_items) + len(inbox_items)
    health_score = max(0, 100 - len(problems) * 8 - len(type_mismatches) * 4 - len(stale_doing) * 5 - len(zombie_waiting) * 3 - len(overloaded_days) * 3 - len(duplicate_items) * 4)
    ctx.progress_badge.value = f"{health_score}% smart score"

    def insight_line(icon, title, detail, color=PRIMARY, bg="#EFF6FF"):
        return ft.Container(
            height=42,
            bgcolor=bg,
            border=border_all(1, "#E2E8F0"),
            border_radius=12,
            padding=pad_only(left=10, right=10),
            content=ft.Row(
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=16, color=color),
                    ft.Column(
                        spacing=0,
                        expand=True,
                        controls=[
                            ft.Text(title, size=12, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(detail, size=10, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                ],
            ),
        )

    def smart_card(title, icon, color, bg, lines, empty_text):
        return ft.Container(
            expand=True,
            height=188,
            bgcolor=bg,
            border=border_all(1, color + "55"),
            border_radius=16,
            padding=16,
            content=ft.Column(
                spacing=10,
                controls=[
                    ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(width=36, height=36, border_radius=10, bgcolor=WHITE, border=border_all(1, color + "44"), alignment=CENTER, content=ft.Icon(icon, size=19, color=color)),
                            ft.Text(title, size=16, weight=ft.FontWeight.W_900, color=TEXT, expand=True),
                        ],
                    ),
                    ft.Container(
                        expand=True,
                        content=ft.ListView(
                            spacing=7,
                            controls=lines if lines else [ft.Container(expand=True, alignment=CENTER, content=ft.Text(empty_text, size=12, color=MUTED_2))],
                        ),
                    ),
                ],
            ),
        )

    mismatch_lines = [
        insight_line(
            ft.Icons.CATEGORY_OUTLINED,
            task.get("name", "Untitled"),
            f"Folder type {task.get('type')} but detected {task.get('detected_type')}",
            color="#D97706",
            bg="#FFFBEB",
        )
        for task in type_mismatches[:3]
    ]
    stale_lines = [
        insight_line(
            ft.Icons.SCHEDULE,
            task.get("name", "Untitled"),
            f"Doing for {(date.today() - task_date_value(task)).days} days",
            color="#EA580C",
            bg="#FFF7ED",
        )
        for task in stale_doing[:3]
    ]
    duplicate_lines = [
        insight_line(
            ft.Icons.CONTENT_COPY,
            items[0].get("name", "Untitled"),
            f"{len(items)} records share this name/type",
            color="#7C3AED",
            bg="#F5F3FF",
        )
        for items in duplicate_items[:3]
    ]
    zombie_lines = [
        insight_line(
            ft.Icons.HOURGLASS_EMPTY,
            task.get("name", "Untitled"),
            f"Waiting for {(date.today() - task_date_value(task)).days} days",
            color="#64748B",
            bg="#F8FAFC",
        )
        for task in zombie_waiting[:2]
    ]
    workload_lines = [
        insight_line(
            ft.Icons.EVENT_BUSY_OUTLINED,
            day_key,
            f"{counts['total']} tasks, {counts['doing']} doing, {counts['waiting']} waiting",
            color="#DC2626" if counts["doing"] >= overload_doing_limit else "#D97706",
            bg="#FEF2F2" if counts["doing"] >= overload_doing_limit else "#FFFBEB",
        )
        for day_key, counts in overloaded_days[:3]
    ]
    inbox_lines = [
        insight_line(
            ft.Icons.INBOX_OUTLINED,
            item.name,
            f"Suggested: Waiting / {infer_type(str(item)) if infer_type else 'Other'}",
            color="#0891B2",
            bg="#ECFEFF",
        )
        for item in inbox_items[:4]
    ]
    smart_summary_lines = [
        insight_line(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, f"{health_score}% Health Score", f"{len(problems)} broken, {smart_findings} smart findings", color=DONE_TEXT if health_score >= 80 else DOING_TEXT if health_score >= 55 else "#DC2626", bg=DONE_BG if health_score >= 80 else DOING_BG if health_score >= 55 else "#FEF2F2"),
        insight_line(ft.Icons.TIPS_AND_UPDATES_OUTLINED, "Read-only intelligence", "No Work files are changed by this scan.", color=PRIMARY, bg="#EFF6FF"),
        *stale_lines[:1],
        *zombie_lines[:1],
    ]
    smart_overview = ft.Row(
        spacing=14,
        controls=[
            smart_card("Smart Score", ft.Icons.HEALTH_AND_SAFETY_OUTLINED, PRIMARY, "#F8FBFF", smart_summary_lines, "System looks clean"),
            smart_card("Auto Classify", ft.Icons.AUTO_FIX_HIGH_OUTLINED, "#D97706", "#FFFBEB", [*mismatch_lines, *duplicate_lines][:4], "No category or duplicate hints"),
            smart_card("Workload", ft.Icons.EVENT_BUSY_OUTLINED, "#DC2626", "#FEF2F2", [*workload_lines, *stale_lines, *zombie_lines][:4], "No overload or zombie hints"),
            smart_card("Smart Inbox", ft.Icons.INBOX_OUTLINED, "#0891B2", "#ECFEFF", inbox_lines, "Create Work\\Inbox to stage loose files"),
        ],
    )

    def issue_row(problem):
        item = problem.get("item", {})
        icon, icon_color = task_icon(item.get("type", "Other"))
        is_template = problem.get("source") == "Template"

        def detail(_event):
            from ui.dialogs import show_task_detail
            show_task_detail(ctx.page, item, ctx.save_and_render, ctx.all_tasks, is_template=is_template, runtime_file_types_fn=ctx.file_types)

        def copy_target(_event):
            target_str = problem.get("target")
            if not target_str and item_target:
                target_str = item_target(item)
            ctx.page.clipboard.set(target_str)
            show_message(ctx.page, "Copied", "Target copied.")

        def save_repaired(message):
            if is_template and save_templates:
                save_templates(templates)
            elif save_tasks:
                save_tasks(ctx.all_tasks)
            if log_activity:
                log_activity("Smart Repair", message, {"item": item})
            ctx.render_current()
            show_message(ctx.page, "Smart Repair", message)

        async def relink(_event):
            before = dict(item)
            target = str(item.get("link") or "").strip()
            try:
                if create_snapshot:
                    create_snapshot("Before relink broken item")
                if item.get("target_kind") == "url" and target.startswith(("http://", "https://")):
                    if is_template:
                        update_template_record(
                            item,
                            item.get("name", "Template"),
                            file_type=item.get("type", "Other"),
                            target=target,
                            note=item.get("note", ""),
                            date_added=item.get("date_added", ""),
                        )
                    else:
                        rename_task_target(
                            item,
                            item.get("name", "Untitled task"),
                            new_target=target,
                            new_file_type=item.get("type", "Other"),
                            new_status=item.get("status", STATUS_PENDING),
                        )
                else:
                    if item.get("target_kind") == "folder":
                        selected = await ctx.pick_directory("Choose replacement folder")
                    else:
                        picked = await ctx.file_picker.pick_files(dialog_title="Choose replacement file", allow_multiple=False)
                        selected = picked[0].path if picked else ""
                    if not selected:
                        return
                    if is_template:
                        update_template_record(
                            item,
                            item.get("name", "Template"),
                            file_type=item.get("type", "Other"),
                            target=selected,
                            note=item.get("note", ""),
                            date_added=item.get("date_added", ""),
                        )
                    else:
                        replacement = create_task_from_source(
                            item.get("name", "Untitled task"),
                            selected,
                            file_type=item.get("type", "Other"),
                            note=item.get("note", ""),
                            status=item.get("status", STATUS_PENDING),
                        )
                        for key in ("name", "type", "detected_type", "link", "target_kind", "shortcut_path", "file_key"):
                            item[key] = replacement.get(key)
                if push_undo and not is_template:
                    push_undo({"kind": "task_restore", "action": "Relink broken item", "task_id": item.get("id"), "before": before, "after": dict(item)})
                save_repaired(f"{item.get('name', 'Item')} relinked successfully.")
            except Exception as exc:
                show_message(ctx.page, "Relink failed", str(exc))

        def remove_record(_event):
            if create_snapshot:
                create_snapshot("Before removing broken record")
            before = dict(item)
            if is_template:
                if item in templates:
                    templates.remove(item)
                if save_templates: save_templates(templates)
            else:
                if item in ctx.all_tasks:
                    ctx.all_tasks.remove(item)
                if save_tasks: save_tasks(ctx.all_tasks)
                if push_undo:
                    push_undo({"kind": "task_restore", "action": "Remove broken record", "task_id": before.get("id"), "before": before, "after": {}})
            if log_activity:
                log_activity("Smart Repair", f"{before.get('name', 'Item')} removed from records.", {"item": before})
            ctx.render_current()

        return ft.Container(
            height=62,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=14,
            padding=pad_only(left=12, right=8),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=38, height=38, border_radius=10, bgcolor="#FEF2F2", border=border_all(1, "#FECACA"), alignment=CENTER, content=ft.Icon(icon, size=19, color=icon_color)),
                    ft.Column(
                        expand=True,
                        spacing=2,
                        controls=[
                            ft.Text(item.get("name", "Untitled"), size=14, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"{problem.get('source')} | {problem.get('reason')} | {item.get('link') or item.get('shortcut_path') or '-'}", size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                    row_action_button("Relink", ft.Icons.DRIVE_FILE_MOVE_OUTLINE, relink, width=128, primary=True),
                    row_action_button("Detail", ft.Icons.INFO_OUTLINE, detail, width=128),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        icon_color=MUTED_2,
                        items=[
                            ft.PopupMenuItem(content="Remove record", icon=ft.Icons.DELETE_OUTLINE, on_click=remove_record),
                            ft.PopupMenuItem(content="Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_target),
                        ],
                    ),
                ],
            ),
        )

    def activity_row(entry):
        return ft.Container(
            height=58,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=14,
            padding=pad_sym(horizontal=14, vertical=8),
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.Container(width=34, height=34, border_radius=10, bgcolor="#EFF6FF", alignment=CENTER, content=ft.Icon(ft.Icons.HISTORY, size=17, color=PRIMARY)),
                    ft.Column(
                        expand=True,
                        spacing=2,
                        controls=[
                            ft.Text(entry.get("action", "Activity"), size=13, weight=ft.FontWeight.W_800, color=TEXT),
                            ft.Text(entry.get("message", ""), size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                    ft.Text(entry.get("time", ""), size=11, color=MUTED_2),
                ],
            ),
        )

    def snapshot_row(snapshot):
        def restore(_event):
            def confirm_restore(_confirm_event):
                try:
                    restored_tasks, _restored_templates = restore_snapshot(snapshot.get("path", ""))
                    ctx.all_tasks.clear()
                    ctx.all_tasks.extend(restored_tasks)
                    restored_settings = load_settings()
                    ctx.settings.clear()
                    ctx.settings.update(restored_settings)
                    restored_work = restored_settings.get("work_folder_path")
                    if restored_work:
                        ctx.set_work_folder(restored_work)
                    ctx.page.pop_dialog()
                    ctx.render_current()
                    show_message(ctx.page, "Snapshot restored", f"Restored {snapshot.get('reason', 'snapshot')}.")
                except Exception as exc:
                    show_message(ctx.page, "Restore failed", str(exc))

            ctx.page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Restore snapshot?", size=20, weight=ft.FontWeight.W_800, color=TEXT),
                    content=ft.Text("Current tasks, templates, settings, and calendar data will be backed up before this snapshot is restored.", color=MUTED),
                    actions=[
                        ft.TextButton("Cancel", on_click=lambda _e: (ctx.page.pop_dialog(), ctx.page.update())),
                        ft.Button("Restore", icon=ft.Icons.RESTORE, on_click=confirm_restore, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                    ],
                )
            )
            ctx.page.update()
        def open_snapshot_folder(_event):
            import os
            path = Path(snapshot.get("path", ""))
            if path.exists():
                os.startfile(str(path.parent))
        return ft.Container(
            height=44,
            border=border_all(1, BORDER),
            border_radius=12,
            bgcolor="#F8FAFC",
            padding=pad_sym(horizontal=12, vertical=6),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(ft.Icons.BACKUP_OUTLINED, size=16, color=MUTED),
                    ft.Column(
                        expand=True,
                        spacing=1,
                        controls=[
                            ft.Text(snapshot.get("reason", "Snapshot"), size=12, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(snapshot.get("time", ""), size=10, color=MUTED_2),
                        ],
                    ),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        icon_size=16,
                        icon_color=MUTED_2,
                        items=[
                            ft.PopupMenuItem(content="Restore snapshot", icon=ft.Icons.RESTORE, on_click=restore),
                            ft.PopupMenuItem(content="Open folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=open_snapshot_folder),
                        ],
                    ),
                ],
            ),
        )

    def health_check_tile(check):
        ok = bool(check.get("ok"))
        color = "#16A34A" if ok else "#DC2626"
        bg = "#F0FDF4" if ok else "#FEF2F2"
        return ft.Container(
            expand=True,
            height=82,
            bgcolor=bg,
            border=border_all(1, "#BBF7D0" if ok else "#FECACA"),
            border_radius=14,
            padding=14,
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=38, height=38, border_radius=10, bgcolor=WHITE, border=border_all(1, "#BBF7D0" if ok else "#FECACA"), alignment=CENTER, content=ft.Icon(check.get("icon", ft.Icons.CHECK_CIRCLE_OUTLINE), size=20, color=color)),
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Row(spacing=6, controls=[ft.Text(check.get("label", "Check"), size=13, weight=ft.FontWeight.W_900, color=TEXT), ft.Icon(ft.Icons.CHECK_CIRCLE if ok else ft.Icons.ERROR_OUTLINE, size=15, color=color)]),
                            ft.Text(check.get("detail", ""), size=11, color=MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                ],
            ),
        )

    health_check_card = ft.Container(
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=18,
        padding=18,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.MONITOR_HEART_OUTLINED, color=PRIMARY), ft.Text("Health Check", size=22, weight=ft.FontWeight.W_900, color=TEXT)]),
                        ft.Container(padding=pad_sym(horizontal=12, vertical=7), border_radius=999, bgcolor="#EFF6FF", border=border_all(1, "#BFDBFE"), content=ft.Text(f"{health_ok_count}/{len(health_checks)} checks OK", size=12, weight=ft.FontWeight.W_900, color=PRIMARY)),
                    ],
                ),
                ft.Row(spacing=12, controls=[health_check_tile(check) for check in health_checks[:3]]),
                ft.Row(spacing=12, controls=[health_check_tile(check) for check in health_checks[3:]]),
            ],
        ),
    )

    def health_filter_button(label, count):
        active = health_filter == label
        return ft.Container(
            on_click=lambda _e, value=label: (ctx.state.update({"health_filter": value}), ctx.render_current()),
            padding=pad_sym(horizontal=12, vertical=8),
            border_radius=999,
            bgcolor=PRIMARY if active else "#F8FAFC",
            border=border_all(1, "#1D4ED8" if active else "#CBD5E1"),
            content=ft.Row(
                spacing=7,
                controls=[
                    ft.Text(label, size=12, weight=ft.FontWeight.W_900, color=WHITE if active else TEXT),
                    ft.Container(width=28, height=20, border_radius=999, bgcolor=WHITE if active else "#EEF2FF", alignment=CENTER, content=ft.Text(str(count), size=10, weight=ft.FontWeight.W_900, color=PRIMARY if active else MUTED)),
                ],
            ),
        )

    issue_card = ft.Container(
        expand=2,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=18,
        padding=22,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.LINK_OFF_OUTLINED, color="#DC2626"), ft.Text("Broken Link Center", size=22, weight=ft.FontWeight.W_800, color=TEXT)]),
                        ft.Button("Scan now", icon=ft.Icons.SYNC, on_click=ctx.sync_now, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                    ],
                ),
                ft.Text("Scans task and template records for missing local targets, empty targets, and missing URL shortcuts. Work files are not changed by this scan.", size=13, color=MUTED),
                ft.Row(
                    spacing=8,
                    wrap=True,
                    controls=[
                        health_filter_button("All", len(problems)),
                        health_filter_button("Tasks", len(broken_tasks)),
                        health_filter_button("Templates", len(broken_templates)),
                        health_filter_button("Missing", sum(1 for problem in problems if problem.get("reason") == "Missing file/folder")),
                        health_filter_button("No target", sum(1 for problem in problems if problem.get("reason") == "No target")),
                        health_filter_button("URL shortcut", sum(1 for problem in problems if problem.get("reason") == "Missing URL shortcut")),
                    ],
                ),
                ft.Container(
                    expand=True,
                    content=ft.ListView(
                        expand=True,
                        spacing=10,
                        controls=[issue_row(problem) for problem in visible_problems] if visible_problems else [ft.Container(expand=True, alignment=CENTER, content=ft.Text("No broken items found for this filter", size=15, color=MUTED_2))],
                    ),
                ),
            ],
        ),
    )

    activity_card = ft.Container(
        expand=1,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=18,
        padding=22,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.HISTORY, color=MUTED), ft.Text("Activity", size=22, weight=ft.FontWeight.W_800, color=TEXT)]),
                        ft.Button("Undo", icon=ft.Icons.UNDO, on_click=ctx.undo_last, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12)))
                    ]
                ),
                ft.Container(padding=pad_sym(horizontal=12, vertical=10), border_radius=14, bgcolor="#F8FAFC", content=ft.Text("Undo restores the latest tracked rename/move/edit when possible.", size=12, color=MUTED)),
                ft.Column(spacing=8, controls=[ft.Text("Recent snapshots", size=13, weight=ft.FontWeight.W_800, color=TEXT), *([snapshot_row(snapshot) for snapshot in snapshots] if snapshots else [ft.Text("No snapshots yet", size=12, color=MUTED_2)])]),
                ft.Container(
                    expand=True,
                    content=ft.ListView(
                        expand=True,
                        spacing=10,
                        controls=[activity_row(entry) for entry in activity] if activity else [ft.Container(expand=True, alignment=CENTER, content=ft.Text("No activity yet", size=15, color=MUTED_2))],
                    ),
                ),
            ],
        ),
    )

    ctx.main_body.controls = [health_check_card] + ([smart_overview] if smart_health_on else []) + [ft.Row(spacing=18, expand=True, controls=[issue_card, activity_card])]
    ctx.page.update()
