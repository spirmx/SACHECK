from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from pathlib import Path

import flet as ft

from core.flet_constants import (
    APP_NAME,
    BORDER,
    MUTED,
    MUTED_2,
    PRIMARY,
    STATUS_DONE,
    STATUS_PENDING,
    STATUS_PROGRESS,
    TEXT,
    WHITE,
)
from core.flet_data import (
    DATA_FILE,
    broken_items,
    create_snapshot,
    create_task_from_source,
    item_target,
    list_snapshots,
    load_activity_log,
    load_settings,
    load_templates,
    log_activity,
    push_undo,
    restore_snapshot,
    save_tasks,
    save_templates,
    update_template_record,
)
from ui.dialogs import show_message
from ui.flet_widgets import CENTER, border_all, pad_only, pad_sym, row_action_button, task_icon
from ui.shared import DashboardContext


def _hover(card: ft.Container, accent: str = "#86EFAC") -> ft.Container:
    def on_hover(event):
        active = event.data == "true"
        card.scale = 1.012 if active else 1
        card.border = border_all(1, accent if active else BORDER)
        card.shadow = ft.BoxShadow(blur_radius=18, color="#140F172A", offset=ft.Offset(0, 7)) if active else None
        try:
            card.update()
        except Exception:
            pass

    card.on_hover = on_hover
    card.animate_scale = ft.Animation(130, ft.AnimationCurve.EASE_OUT)
    return card


def _task_day(task: dict) -> date | None:
    raw = task.get("status_date") or task.get("date_added")
    try:
        return datetime.strptime(str(raw or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def render_health(ctx: DashboardContext) -> None:
    """Render a practical diagnostics dashboard for data, links and workload."""

    ctx.header_title.value = "System Health"
    ctx.header_subtitle.value = f"{APP_NAME} / Diagnostics & Recovery"

    templates = load_templates()
    problems = broken_items(ctx.all_tasks, templates)
    snapshots = list_snapshots(8)
    activity = [
        item
        for item in load_activity_log(40)
        if str(item.get("action") or "").casefold() != "system guard"
    ][:10]

    today = date.today()
    root_text = str(ctx.settings.get("work_folder_path") or ctx.settings.get("root_work") or ctx.root_work or "")
    root_work = Path(root_text) if root_text else DATA_FILE.parent
    offline_mode = bool(ctx.settings.get("offline_mode", False))
    update_url = str(ctx.update_channel_url() or "")
    stale_days = max(1, int(ctx.settings.get("stale_doing_days") or 7))
    waiting_days = max(1, int(ctx.settings.get("zombie_waiting_days") or 30))
    tab = str(ctx.state.get("health_tab") or "overview")
    problem_filter = str(ctx.state.get("health_filter") or "All")

    def can_write(folder: Path) -> bool:
        probe = folder / ".sacheck_health_probe"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass
            return False

    checks = [
        {
            "title": "Work folder",
            "detail": str(root_work),
            "ok": root_work.exists() and root_work.is_dir(),
            "icon": ft.Icons.FOLDER_OUTLINED,
            "fix": "Choose a valid workspace in Settings",
        },
        {
            "title": "Data storage",
            "detail": str(DATA_FILE.parent),
            "ok": can_write(DATA_FILE.parent),
            "icon": ft.Icons.SAVE_OUTLINED,
            "fix": "Check folder access permissions",
        },
        {
            "title": "Records",
            "detail": f"{len(ctx.all_tasks)} tasks and {len(templates)} templates loaded",
            "ok": isinstance(ctx.all_tasks, list) and isinstance(templates, list),
            "icon": ft.Icons.FACT_CHECK_OUTLINED,
            "fix": "Restore the latest snapshot",
        },
        {
            "title": "Update channel",
            "detail": "Offline mode" if offline_mode else ("Connected to update channel" if update_url else "Update URL is missing"),
            "ok": offline_mode or bool(update_url),
            "icon": ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED,
            "fix": "Configure updates in Settings",
        },
        {
            "title": "Recovery backup",
            "detail": f"{len(snapshots)} recent snapshots available",
            "ok": bool(snapshots),
            "icon": ft.Icons.BACKUP_OUTLINED,
            "fix": "Create the first recovery snapshot",
        },
    ]

    stale_doing = [
        task
        for task in ctx.all_tasks
        if task.get("status") == STATUS_PROGRESS
        and _task_day(task)
        and (today - _task_day(task)).days >= stale_days
    ]
    old_waiting = [
        task
        for task in ctx.all_tasks
        if task.get("status") == STATUS_PENDING
        and _task_day(task)
        and (today - _task_day(task)).days >= waiting_days
    ]
    type_mismatches = [
        task
        for task in ctx.all_tasks
        if task.get("detected_type")
        and task.get("type")
        and task.get("detected_type") not in {"Other", "Link"}
        and task.get("type") != task.get("detected_type")
    ]

    duplicate_index: dict[tuple[str, str], list[dict]] = {}
    for item in [*ctx.all_tasks, *templates]:
        key = (
            str(item.get("name") or "").strip().casefold(),
            str(item.get("type") or "Other").strip().casefold(),
        )
        if key[0]:
            duplicate_index.setdefault(key, []).append(item)
    duplicate_groups = [items for items in duplicate_index.values() if len(items) > 1]

    failed_checks = sum(not check["ok"] for check in checks)
    warning_count = len(stale_doing) + len(old_waiting) + len(type_mismatches) + len(duplicate_groups)
    critical_count = failed_checks + len(problems)
    health_score = max(0, 100 - critical_count * 12 - min(warning_count, 10) * 3)
    score_color = "#16A34A" if health_score >= 85 else "#D97706" if health_score >= 60 else "#DC2626"
    score_label = "Healthy" if health_score >= 85 else "Review needed" if health_score >= 60 else "Action required"
    ctx.progress_badge.value = f"{health_score}% health"

    status_counts = Counter(task.get("status", STATUS_PENDING) for task in ctx.all_tasks)

    def set_tab(value: str):
        ctx.state["health_tab"] = value
        ctx.render_current()

    def create_backup(_event):
        try:
            create_snapshot("Manual Health Center backup")
            ctx.render_current()
            show_message(ctx.page, "Backup ready", "Tasks, templates, calendar and settings were saved.")
        except Exception as exc:
            show_message(ctx.page, "Backup failed", str(exc))

    def run_scan(_event):
        log_activity(
            "Health scan",
            f"Scan complete: {critical_count} critical signals, {warning_count} warnings.",
        )
        ctx.render_current()
        show_message(ctx.page, "Health scan complete", f"Found {critical_count} critical signals and {warning_count} warnings.")

    hero = ft.Container(
        height=196,
        border_radius=22,
        padding=24,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=["#052E2B", "#0F766E", "#164E63"],
        ),
        content=ft.Row(
            spacing=22,
            controls=[
                ft.Column(
                    expand=True,
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Container(width=8, height=8, border_radius=99, bgcolor="#5EEAD4"),
                                ft.Text("LIVE LOCAL DIAGNOSTICS", size=10, weight=ft.FontWeight.W_900, color="#99F6E4"),
                            ],
                        ),
                        ft.Text("Know what needs attention.", size=27, weight=ft.FontWeight.W_900, color=WHITE),
                        ft.Text(
                            "Health checks your workspace, broken links, backups and workload. It never deletes or changes work files during a scan.",
                            size=12,
                            color="#CCFBF1",
                            max_lines=2,
                        ),
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.Button(
                                    "Run health scan",
                                    icon=ft.Icons.MONITOR_HEART_OUTLINED,
                                    on_click=run_scan,
                                    style=ft.ButtonStyle(bgcolor=WHITE, color="#064E3B", shape=ft.RoundedRectangleBorder(radius=12)),
                                ),
                                ft.Button(
                                    "Create backup",
                                    icon=ft.Icons.BACKUP_OUTLINED,
                                    on_click=create_backup,
                                    style=ft.ButtonStyle(bgcolor="#03302E", color=WHITE, overlay_color="#0F766E", side=ft.BorderSide(1.5, "#5EEAD4"), shape=ft.RoundedRectangleBorder(radius=12)),
                                ),
                                ft.Button(
                                    "Settings",
                                    icon=ft.Icons.TUNE_OUTLINED,
                                    on_click=lambda _e: ctx.show_settings(),
                                    style=ft.ButtonStyle(bgcolor="#03302E", color=WHITE, overlay_color="#0F766E", side=ft.BorderSide(1.5, "#5EEAD4"), shape=ft.RoundedRectangleBorder(radius=12)),
                                ),
                            ],
                        ),
                    ],
                ),
                ft.Container(
                    width=250,
                    padding=18,
                    border_radius=18,
                    bgcolor="#24FFFFFF",
                    border=border_all(1, "#467DD3C7"),
                    content=ft.Row(
                        spacing=17,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Stack(
                                width=104,
                                height=104,
                                alignment=CENTER,
                                controls=[
                                    ft.ProgressRing(value=health_score / 100, width=104, height=104, stroke_width=10, color="#5EEAD4", bgcolor="#225EEAD4"),
                                    ft.Column(
                                        spacing=0,
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Text(f"{health_score}", size=25, weight=ft.FontWeight.W_900, color=WHITE),
                                            ft.Text("SCORE", size=9, weight=ft.FontWeight.W_900, color="#99F6E4"),
                                        ],
                                    ),
                                ],
                            ),
                            ft.Column(
                                spacing=6,
                                alignment=ft.MainAxisAlignment.CENTER,
                                controls=[
                                    ft.Text(score_label, size=14, weight=ft.FontWeight.W_900, color=WHITE),
                                    ft.Text(f"{critical_count} critical", size=11, color="#FECACA"),
                                    ft.Text(f"{warning_count} warnings", size=11, color="#FDE68A"),
                                    ft.Text(f"{sum(check['ok'] for check in checks)}/{len(checks)} checks pass", size=11, color="#A7F3D0"),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )

    summary_meta = [
        ("Broken links", len(problems), "Records that cannot open their target", ft.Icons.LINK_OFF_OUTLINED, "#DC2626", "#FEF2F2", "repairs"),
        ("Workload warnings", len(stale_doing) + len(old_waiting), "Doing or Waiting longer than expected", ft.Icons.SCHEDULE_OUTLINED, "#D97706", "#FFFBEB", "overview"),
        ("Type mismatches", len(type_mismatches), "Folder category differs from detected file", ft.Icons.CATEGORY_OUTLINED, "#7C3AED", "#F5F3FF", "overview"),
        ("Recovery points", len(snapshots), "Backups ready to restore", ft.Icons.BACKUP_OUTLINED, "#059669", "#ECFDF5", "activity"),
    ]

    def summary_card(title, value, hint, icon, color, bg, target):
        card = ft.Container(
            expand=True,
            height=92,
            padding=14,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=17,
            ink=True,
            on_click=lambda _e: set_tab(target),
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.Container(width=43, height=43, border_radius=13, bgcolor=bg, alignment=CENTER, content=ft.Icon(icon, size=21, color=color)),
                    ft.Column(
                        spacing=1,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(title, size=12, weight=ft.FontWeight.W_900, color=TEXT), ft.Text(str(value), size=20, weight=ft.FontWeight.W_900, color=color)]),
                            ft.Text(hint, size=10, color=MUTED, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                ],
            ),
        )
        return _hover(card, color + "66")

    summaries = ft.Row(spacing=11, controls=[summary_card(*item) for item in summary_meta])

    def tab_button(label, icon, value, count=None):
        active = tab == value
        controls = [
            ft.Icon(icon, size=17, color=WHITE if active else MUTED),
            ft.Text(label, size=12, weight=ft.FontWeight.W_900, color=WHITE if active else TEXT),
        ]
        if count is not None:
            controls.append(
                ft.Container(
                    width=28,
                    height=20,
                    border_radius=99,
                    alignment=CENTER,
                    bgcolor=WHITE if active else "#E2E8F0",
                    content=ft.Text(str(count), size=9, weight=ft.FontWeight.W_900, color="#0F766E" if active else MUTED),
                )
            )
        return ft.Container(
            height=40,
            padding=pad_sym(horizontal=14),
            border_radius=12,
            bgcolor="#0F766E" if active else "#F8FAFC",
            border=border_all(1, "#0F766E" if active else BORDER),
            ink=True,
            on_click=lambda _e: set_tab(value),
            content=ft.Row(spacing=8, controls=controls),
        )

    tab_bar = ft.Container(
        height=58,
        padding=pad_sym(horizontal=10, vertical=8),
        border=border_all(1, BORDER),
        border_radius=16,
        bgcolor=WHITE,
        content=ft.Row(
            spacing=8,
            controls=[
                tab_button("Overview", ft.Icons.SPACE_DASHBOARD_OUTLINED, "overview"),
                tab_button("Repair Center", ft.Icons.BUILD_CIRCLE_OUTLINED, "repairs", len(problems)),
                tab_button("Backup & Activity", ft.Icons.HISTORY, "activity", len(snapshots)),
            ],
        ),
    )

    def check_tile(check):
        ok = bool(check["ok"])
        color = "#16A34A" if ok else "#DC2626"
        bg = "#F0FDF4" if ok else "#FEF2F2"
        return ft.Container(
            height=66,
            padding=pad_sym(horizontal=12, vertical=9),
            border=border_all(1, "#BBF7D0" if ok else "#FECACA"),
            border_radius=14,
            bgcolor=bg,
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Container(width=36, height=36, border_radius=11, bgcolor=WHITE, alignment=CENTER, content=ft.Icon(check["icon"], size=18, color=color)),
                    ft.Column(
                        spacing=1,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Row(spacing=6, controls=[ft.Text(check["title"], size=12, weight=ft.FontWeight.W_900, color=TEXT), ft.Icon(ft.Icons.CHECK_CIRCLE if ok else ft.Icons.ERROR_OUTLINE, size=14, color=color)]),
                            ft.Text(check["detail"] if ok else check["fix"], size=10, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                ],
            ),
        )

    def signal_row(icon, title, detail, count, color, bg):
        return ft.Container(
            height=60,
            padding=pad_sym(horizontal=12, vertical=8),
            border=border_all(1, BORDER),
            border_radius=14,
            bgcolor=WHITE,
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Container(width=36, height=36, border_radius=11, bgcolor=bg, alignment=CENTER, content=ft.Icon(icon, size=18, color=color)),
                    ft.Column(
                        spacing=1,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Text(title, size=12, weight=ft.FontWeight.W_900, color=TEXT),
                            ft.Text(detail, size=10, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                    ft.Container(width=34, height=26, border_radius=99, bgcolor=bg, alignment=CENTER, content=ft.Text(str(count), size=11, weight=ft.FontWeight.W_900, color=color)),
                ],
            ),
        )

    def status_bar(label, value, total, color):
        ratio = value / max(total, 1)
        return ft.Column(
            spacing=5,
            controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text(label, size=11, weight=ft.FontWeight.W_800, color=TEXT), ft.Text(str(value), size=11, weight=ft.FontWeight.W_900, color=color)]),
                ft.ProgressBar(value=ratio, height=7, border_radius=99, color=color, bgcolor="#EEF2F7"),
            ],
        )

    check_panel = ft.Container(
        expand=3,
        padding=18,
        border=border_all(1, BORDER),
        border_radius=20,
        bgcolor=WHITE,
        content=ft.Column(
            spacing=11,
            controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Core system checks", size=17, weight=ft.FontWeight.W_900, color=TEXT), ft.Text(f"{sum(check['ok'] for check in checks)}/{len(checks)} PASS", size=10, weight=ft.FontWeight.W_900, color=score_color)]),
                ft.Text("These checks confirm that SA CHECK can read, save, recover and update safely.", size=11, color=MUTED),
                *[check_tile(check) for check in checks],
            ],
        ),
    )

    signal_panel = ft.Container(
        expand=2,
        padding=18,
        border=border_all(1, BORDER),
        border_radius=20,
        bgcolor=WHITE,
        content=ft.Column(
            spacing=11,
            controls=[
                ft.Text("What needs attention", size=17, weight=ft.FontWeight.W_900, color=TEXT),
                ft.Text("Warnings help prioritize cleanup; they do not modify any files.", size=11, color=MUTED),
                signal_row(ft.Icons.LINK_OFF_OUTLINED, "Broken targets", "Task or template target is missing", len(problems), "#DC2626", "#FEF2F2"),
                signal_row(ft.Icons.SCHEDULE_OUTLINED, "Stale Doing", f"No status change for {stale_days}+ days", len(stale_doing), "#D97706", "#FFFBEB"),
                signal_row(ft.Icons.HOURGLASS_EMPTY, "Long Waiting", f"Waiting for {waiting_days}+ days", len(old_waiting), "#64748B", "#F1F5F9"),
                signal_row(ft.Icons.CATEGORY_OUTLINED, "Wrong category", "Detected type differs from assigned type", len(type_mismatches), "#7C3AED", "#F5F3FF"),
                signal_row(ft.Icons.CONTENT_COPY, "Duplicate records", "Same name and category appear twice", len(duplicate_groups), "#0891B2", "#ECFEFF"),
            ],
        ),
    )

    workflow_panel = ft.Container(
        padding=18,
        border=border_all(1, BORDER),
        border_radius=20,
        bgcolor=WHITE,
        content=ft.Row(
            spacing=24,
            controls=[
                ft.Column(
                    width=210,
                    spacing=5,
                    controls=[
                        ft.Text("Current workload", size=16, weight=ft.FontWeight.W_900, color=TEXT),
                        ft.Text("A quick balance check for active work.", size=10, color=MUTED),
                    ],
                ),
                ft.Container(expand=True, content=status_bar("Waiting", status_counts[STATUS_PENDING], len(ctx.all_tasks), "#2563EB")),
                ft.Container(expand=True, content=status_bar("Doing", status_counts[STATUS_PROGRESS], len(ctx.all_tasks), "#D97706")),
                ft.Container(expand=True, content=status_bar("Completed", status_counts[STATUS_DONE], len(ctx.all_tasks), "#16A34A")),
            ],
        ),
    )

    overview_view = ft.Column(
        spacing=14,
        controls=[
            ft.Row(spacing=14, controls=[check_panel, signal_panel]),
            workflow_panel,
        ],
    )

    def problem_matches(problem):
        if problem_filter == "Tasks":
            return problem.get("source") == "Task"
        if problem_filter == "Templates":
            return problem.get("source") == "Template"
        if problem_filter == "Missing":
            return problem.get("reason") == "Missing file/folder"
        return True

    visible_problems = [problem for problem in problems if problem_matches(problem)]

    def filter_button(label, count):
        active = problem_filter == label
        return ft.Container(
            height=34,
            padding=pad_sym(horizontal=11),
            border_radius=99,
            bgcolor="#0F766E" if active else "#F8FAFC",
            border=border_all(1, "#0F766E" if active else BORDER),
            on_click=lambda _e, value=label: (ctx.state.update({"health_filter": value}), ctx.render_current()),
            content=ft.Row(
                spacing=7,
                controls=[
                    ft.Text(label, size=11, weight=ft.FontWeight.W_900, color=WHITE if active else TEXT),
                    ft.Text(str(count), size=10, weight=ft.FontWeight.W_900, color="#99F6E4" if active else MUTED),
                ],
            ),
        )

    def issue_row(problem):
        item = problem.get("item") or {}
        is_template = problem.get("source") == "Template"
        icon, icon_color = task_icon(item.get("type", "Other"))

        async def relink(_event):
            try:
                create_snapshot("Before Health Center relink")
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
                    save_templates(templates)
                else:
                    before = dict(item)
                    replacement = create_task_from_source(
                        item.get("name", "Untitled task"),
                        selected,
                        file_type=item.get("type", "Other"),
                        note=item.get("note", ""),
                        status=item.get("status", STATUS_PENDING),
                    )
                    item.update(replacement)
                    push_undo({"kind": "task_restore", "action": "Relink broken item", "task_id": item.get("id"), "before": before, "after": dict(item)})
                    save_tasks(ctx.all_tasks)
                log_activity("Health repair", f"Relinked {item.get('name', 'record')}.")
                ctx.render_current()
                show_message(ctx.page, "Link repaired", f"{item.get('name', 'Record')} now points to an existing target.")
            except Exception as exc:
                show_message(ctx.page, "Relink failed", str(exc))

        async def copy_path(_event):
            await ctx.page.clipboard.set(problem.get("target") or item_target(item) or "")
            show_message(ctx.page, "Copied", "Target path copied.")

        def remove_record(_event):
            try:
                create_snapshot("Before removing broken record")
                before = dict(item)
                if is_template:
                    if item in templates:
                        templates.remove(item)
                    save_templates(templates)
                else:
                    if item in ctx.all_tasks:
                        ctx.all_tasks.remove(item)
                    save_tasks(ctx.all_tasks)
                    push_undo({"kind": "task_restore", "action": "Remove broken record", "task_id": before.get("id"), "before": before, "after": {}})
                log_activity("Health repair", f"Removed broken record {before.get('name', 'Untitled')}.")
                ctx.render_current()
            except Exception as exc:
                show_message(ctx.page, "Remove failed", str(exc))

        return ft.Container(
            height=64,
            padding=pad_only(left=12, right=8),
            border=border_all(1, BORDER),
            border_radius=14,
            bgcolor=WHITE,
            content=ft.Row(
                spacing=11,
                controls=[
                    ft.Container(width=38, height=38, border_radius=11, bgcolor="#FEF2F2", alignment=CENTER, content=ft.Icon(icon, size=18, color=icon_color)),
                    ft.Column(
                        spacing=1,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Row(spacing=8, controls=[ft.Text(item.get("name", "Untitled"), size=13, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Container(padding=pad_sym(horizontal=7, vertical=2), border_radius=99, bgcolor="#FEE2E2", content=ft.Text(problem.get("source", "Record"), size=9, weight=ft.FontWeight.W_900, color="#B91C1C"))]),
                            ft.Text(f"{problem.get('reason', 'Broken target')}  •  {problem.get('target') or '-'}", size=10, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                    row_action_button("Relink", ft.Icons.DRIVE_FILE_MOVE_OUTLINE, relink, width=112, primary=True),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        icon_color=MUTED_2,
                        items=[
                            ft.PopupMenuItem(content="Copy path", icon=ft.Icons.CONTENT_COPY, on_click=copy_path),
                            ft.PopupMenuItem(content="Remove record", icon=ft.Icons.DELETE_OUTLINE, on_click=remove_record),
                        ],
                    ),
                ],
            ),
        )

    repair_view = ft.Container(
        height=390,
        padding=20,
        border=border_all(1, BORDER),
        border_radius=20,
        bgcolor=WHITE,
        content=ft.Column(
            spacing=13,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(spacing=2, controls=[ft.Text("Broken Link Repair Center", size=19, weight=ft.FontWeight.W_900, color=TEXT), ft.Text("Relink missing targets without touching the original work files.", size=11, color=MUTED)]),
                        ft.Button("Scan again", icon=ft.Icons.REFRESH, on_click=run_scan, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                    ],
                ),
                ft.Row(
                    spacing=8,
                    controls=[
                        filter_button("All", len(problems)),
                        filter_button("Tasks", sum(problem.get("source") == "Task" for problem in problems)),
                        filter_button("Templates", sum(problem.get("source") == "Template" for problem in problems)),
                        filter_button("Missing", sum(problem.get("reason") == "Missing file/folder" for problem in problems)),
                    ],
                ),
                ft.Container(
                    height=300,
                    content=ft.ListView(
                        spacing=9,
                        controls=[issue_row(problem) for problem in visible_problems]
                        if visible_problems
                        else [
                            ft.Container(
                                height=280,
                                alignment=CENTER,
                                content=ft.Column(
                                    spacing=8,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Container(width=56, height=56, border_radius=18, bgcolor="#ECFDF5", alignment=CENTER, content=ft.Icon(ft.Icons.VERIFIED_OUTLINED, size=28, color="#059669")),
                                        ft.Text("No broken targets", size=15, weight=ft.FontWeight.W_900, color=TEXT),
                                        ft.Text("Every record in this filter can reach its file, folder or shortcut.", size=11, color=MUTED),
                                    ],
                                ),
                            )
                        ],
                    ),
                ),
            ],
        ),
    )

    def restore_row(snapshot):
        def restore(_event):
            def confirm(_confirm_event):
                try:
                    restored_tasks, _ = restore_snapshot(snapshot.get("path", ""))
                    ctx.all_tasks.clear()
                    ctx.all_tasks.extend(restored_tasks)
                    restored_settings = load_settings()
                    ctx.settings.clear()
                    ctx.settings.update(restored_settings)
                    work_folder = restored_settings.get("work_folder_path")
                    if work_folder:
                        ctx.set_work_folder(work_folder)
                    ctx.page.pop_dialog()
                    ctx.render_current()
                    show_message(ctx.page, "Snapshot restored", "Tasks, templates, calendar and settings were restored.")
                except Exception as exc:
                    show_message(ctx.page, "Restore failed", str(exc))

            ctx.page.show_dialog(
                ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Restore this snapshot?", weight=ft.FontWeight.W_900, color=TEXT),
                    content=ft.Text("A new safety backup will be created before the restore.", color=MUTED),
                    actions=[
                        ft.TextButton("Cancel", on_click=lambda _e: (ctx.page.pop_dialog(), ctx.page.update())),
                        ft.Button("Restore", icon=ft.Icons.RESTORE, on_click=confirm, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                    ],
                )
            )
            ctx.page.update()

        return ft.Container(
            height=56,
            padding=pad_sym(horizontal=12, vertical=7),
            border=border_all(1, BORDER),
            border_radius=13,
            bgcolor="#F8FAFC",
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Container(width=34, height=34, border_radius=10, bgcolor="#DCFCE7", alignment=CENTER, content=ft.Icon(ft.Icons.BACKUP_OUTLINED, size=17, color="#059669")),
                    ft.Column(
                        spacing=1,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Text(snapshot.get("reason", "Snapshot"), size=11, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(snapshot.get("time", ""), size=9, color=MUTED_2),
                        ],
                    ),
                    ft.IconButton(icon=ft.Icons.RESTORE, icon_size=17, icon_color="#0F766E", tooltip="Restore snapshot", on_click=restore),
                ],
            ),
        )

    def activity_row(entry):
        return ft.Container(
            height=56,
            padding=pad_sym(horizontal=12, vertical=7),
            border=border_all(1, BORDER),
            border_radius=13,
            bgcolor=WHITE,
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Container(width=34, height=34, border_radius=10, bgcolor="#EFF6FF", alignment=CENTER, content=ft.Icon(ft.Icons.HISTORY, size=17, color=PRIMARY)),
                    ft.Column(
                        spacing=1,
                        expand=True,
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Text(entry.get("action", "Activity"), size=11, weight=ft.FontWeight.W_900, color=TEXT),
                            ft.Text(entry.get("message", ""), size=9, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                    ft.Text(str(entry.get("time", ""))[5:16], size=9, color=MUTED_2),
                ],
            ),
        )

    backup_view = ft.Row(
        spacing=14,
        controls=[
            ft.Container(
                expand=1,
                height=390,
                padding=18,
                border=border_all(1, BORDER),
                border_radius=20,
                bgcolor=WHITE,
                content=ft.Column(
                    spacing=11,
                    controls=[
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Recovery snapshots", size=17, weight=ft.FontWeight.W_900, color=TEXT), ft.IconButton(icon=ft.Icons.ADD_CIRCLE_OUTLINE, tooltip="Create backup", on_click=create_backup)]),
                        ft.Text("Restore tasks and app settings to an earlier safe point.", size=10, color=MUTED),
                        *([restore_row(snapshot) for snapshot in snapshots[:5]] or [ft.Container(height=250, alignment=CENTER, content=ft.Text("No snapshots yet", color=MUTED_2))]),
                    ],
                ),
            ),
            ft.Container(
                expand=2,
                height=390,
                padding=18,
                border=border_all(1, BORDER),
                border_radius=20,
                bgcolor=WHITE,
                content=ft.Column(
                    spacing=11,
                    controls=[
                        ft.Text("Recent app activity", size=17, weight=ft.FontWeight.W_900, color=TEXT),
                        ft.Text("A local audit trail of backups, repairs and work changes.", size=10, color=MUTED),
                        ft.Container(height=304, content=ft.ListView(spacing=8, controls=[activity_row(item) for item in activity] if activity else [ft.Container(height=280, alignment=CENTER, content=ft.Text("No activity recorded yet", color=MUTED_2))])),
                    ],
                ),
            ),
        ],
    )

    active_view = repair_view if tab == "repairs" else backup_view if tab == "activity" else overview_view
    ctx.main_body.controls = [
        hero,
        summaries,
        tab_bar,
        active_view,
        ft.Container(height=4),
    ]
    ctx.main_body.spacing = 14
    ctx.main_body.scroll = ft.ScrollMode.AUTO
