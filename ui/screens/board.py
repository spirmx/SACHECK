import flet as ft

from core.flet_constants import (
    BORDER,
    MUTED,
    PRIMARY,
    STATUS_DONE,
    STATUS_PENDING,
    STATUS_PROGRESS,
    TEXT,
    WHITE,
)
from ui.dialogs import kanban_column
from ui.flet_widgets import border_all, dropdown, pad_sym, stat_card
from ui.shared import DashboardContext


def render_board(ctx: DashboardContext) -> None:
    ctx.header_title.value = "Project Overview"
    ctx.header_subtitle.value = "SA CHECK / Work Board"

    visible = ctx.filtered_tasks()
    waiting = [task for task in visible if task.get("status") == STATUS_PENDING]
    doing = [task for task in visible if task.get("status") == STATUS_PROGRESS]
    done = [task for task in visible if task.get("status") == STATUS_DONE]

    total_all = len(ctx.all_tasks)
    done_all = sum(1 for task in ctx.all_tasks if task.get("status") == STATUS_DONE)
    ctx.progress_badge.value = f"{int((done_all / total_all) * 100) if total_all else 0}% Complete"

    stats = ft.Row(
        spacing=10,
        controls=[
            stat_card("TOTAL", total_all),
            stat_card("WAITING", sum(1 for task in ctx.all_tasks if task.get("status") == STATUS_PENDING)),
            stat_card("DOING", sum(1 for task in ctx.all_tasks if task.get("status") == STATUS_PROGRESS)),
            stat_card("COMPLETED", done_all),
        ],
    )

    def on_view_change(e):
        ctx.state.update({"view": e.control.value, "group_limits": {}})
        ctx.render_current()

    def on_type_change(e):
        ctx.state.update({"type": e.control.value, "group_limits": {}})
        ctx.render_current()

    def on_sort_change(e):
        ctx.state.update({"sort": e.control.value, "group_limits": {}})
        ctx.render_current()

    filters = ft.Container(
        height=50,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=12,
        padding=pad_sym(horizontal=12, vertical=6),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ctx.search_field,
                dropdown(170, ctx.state["view"], ["All work", "Waiting", "Doing", "Completed"], on_view_change),
                dropdown(170, ctx.state["type"], ["All types", *ctx.file_types()], on_type_change),
                dropdown(160, ctx.state["sort"], ["Newest", "Oldest", "Name"], on_sort_change),
                ft.Container(padding=pad_sym(horizontal=11, vertical=8), border_radius=999, bgcolor="#F8FAFC", content=ft.Text(f"{len(visible)} shown", size=12, weight=ft.FontWeight.W_800, color=MUTED)),
                ft.Button("Reset", icon=ft.Icons.RESTART_ALT, on_click=lambda _e: ctx.reset_filters(), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
            ],
        ),
    )

    expanded_keys = ctx.state.setdefault("expanded_groups", set())

    board = ft.Row(
        spacing=10,
        expand=True,
        controls=[
            kanban_column(
                ctx.page, "Waiting List", waiting, *ctx.status_theme(STATUS_PENDING),
                ctx.save_and_render, ctx.all_tasks, grouped=True,
                group_limits=ctx.state["group_limits"], on_more=ctx.render_current,
                file_types_fn=ctx.file_types, expanded_keys=expanded_keys
            ),
            kanban_column(
                ctx.page, "Active Work", doing, *ctx.status_theme(STATUS_PROGRESS),
                ctx.save_and_render, ctx.all_tasks, grouped=True,
                group_limits=ctx.state["group_limits"], on_more=ctx.render_current,
                file_types_fn=ctx.file_types, expanded_keys=expanded_keys
            ),
            kanban_column(
                ctx.page, "Complete", done, *ctx.status_theme(STATUS_DONE),
                ctx.save_and_render, ctx.all_tasks, grouped=True,
                group_limits=ctx.state["group_limits"], on_more=ctx.render_current,
                file_types_fn=ctx.file_types, expanded_keys=expanded_keys
            ),
        ],
    )

    smart_help = ft.Container(
        height=36,
        bgcolor="#F8FBFF",
        border=border_all(1, "#DBEAFE"),
        border_radius=14,
        padding=pad_sym(horizontal=14, vertical=6),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.TIPS_AND_UPDATES_OUTLINED, size=16, color=PRIMARY),
                ft.Text("Smart Search:", size=12, weight=ft.FontWeight.W_900, color=TEXT),
                ft.Text("try `doing word`, `success today`, `zombie`, `>7`, `miro waiting`", size=12, color=MUTED),
            ],
        ),
    )

    ctx.main_body.spacing = 10
    controls = [stats, filters]
    if ctx.settings.get("smart_search_enabled", True):
        controls.append(smart_help)
    controls.append(board)

    ctx.main_body.controls = controls
    ctx.page.update()
