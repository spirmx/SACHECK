from __future__ import annotations

from collections import Counter

import flet as ft

from core.flet_constants import (
    BORDER,
    MUTED,
    MUTED_2,
    STATUS_DONE,
    STATUS_PENDING,
    STATUS_PROGRESS,
    TEXT,
    WHITE,
)
from ui.dialogs import kanban_column
from ui.flet_widgets import CENTER, border_all, count_up, dropdown, fade_in_up, pad_sym
from ui.shared import DashboardContext


STATUS_META = {
    STATUS_PENDING: {
        "title": "Waiting",
        "subtitle": "Ready to start",
        "icon": ft.Icons.INBOX_OUTLINED,
        "color": "#2563EB",
        "bg": "#EFF6FF",
    },
    STATUS_PROGRESS: {
        "title": "Doing",
        "subtitle": "Work in progress",
        "icon": ft.Icons.BOLT_OUTLINED,
        "color": "#D97706",
        "bg": "#FFFBEB",
    },
    STATUS_DONE: {
        "title": "Completed",
        "subtitle": "Finished work",
        "icon": ft.Icons.CHECK_CIRCLE_OUTLINE,
        "color": "#16A34A",
        "bg": "#F0FDF4",
    },
}


def _hover(card: ft.Container, accent: str) -> ft.Container:
    def on_hover(event):
        active = event.data == "true"
        card.scale = 1.01 if active else 1
        card.border = border_all(1, accent if active else BORDER)
        card.shadow = ft.BoxShadow(blur_radius=16, color="#120F172A", offset=ft.Offset(0, 6)) if active else None
        try:
            card.update()
        except Exception:
            pass

    card.on_hover = on_hover
    card.animate_scale = ft.Animation(120, ft.AnimationCurve.EASE_OUT)
    return card


def render_board(ctx: DashboardContext) -> None:
    ctx.header_title.value = "Work Board"
    ctx.header_subtitle.value = "SA CHECK / Live workflow"

    valid_views = {"All work", "Waiting", "Doing", "Completed"}
    valid_sorts = {"Newest", "Oldest", "Name", "Priority", "Progress"}
    available_types = ctx.file_types()
    if ctx.state.get("view") not in valid_views:
        ctx.state["view"] = "All work"
    if ctx.state.get("type") not in {"All types", *available_types}:
        ctx.state["type"] = "All types"
    if ctx.state.get("sort") not in valid_sorts:
        ctx.state["sort"] = "Newest"
    ctx.state.setdefault("group_limits", {})
    ctx.state.setdefault("expanded_groups", set())

    visible = list(ctx.filtered_tasks() or [])
    by_status = {
        status: [task for task in visible if task.get("status") == status]
        for status in (STATUS_PENDING, STATUS_PROGRESS, STATUS_DONE)
    }
    all_counts = Counter(task.get("status", STATUS_PENDING) for task in ctx.all_tasks)
    total = len(ctx.all_tasks)
    completed = all_counts[STATUS_DONE]
    completion = int((completed / total) * 100) if total else 0
    ctx.progress_badge.value = f"{completion}% complete"

    active_filters = (
        bool(str(ctx.state.get("search") or "").strip())
        or ctx.state["view"] != "All work"
        or ctx.state["type"] != "All types"
    )

    def on_view_change(event):
        ctx.state.update({"view": event.control.value or "All work", "group_limits": {}})
        ctx.render_current()

    def on_type_change(event):
        ctx.state.update({"type": event.control.value or "All types", "group_limits": {}})
        ctx.render_current()

    def on_sort_change(event):
        ctx.state.update({"sort": event.control.value or "Newest", "group_limits": {}})
        ctx.render_current()

    ctx.search_field.expand = False
    ctx.search_field.width = 330

    pulse = ft.Container(
        height=100,
        padding=18,
        border_radius=20,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, -1),
            end=ft.Alignment(1, 1),
            colors=["#0F172A", "#1E3A8A", "#0F766E"],
        ),
        content=ft.Row(
            spacing=22,
            controls=[
                ft.Column(
                    width=310,
                    spacing=5,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Container(width=8, height=8, border_radius=99, bgcolor="#5EEAD4"),
                                ft.Text("LIVE WORKFLOW", size=9, weight=ft.FontWeight.W_900, color="#99F6E4"),
                            ],
                        ),
                        ft.Text("Keep work moving.", size=22, weight=ft.FontWeight.W_900, color=WHITE),
                        ft.Row(
                            spacing=9,
                            controls=[
                                ft.Container(
                                    expand=True,
                                    content=ft.ProgressBar(
                                        value=completion / 100,
                                        height=7,
                                        border_radius=99,
                                        color="#5EEAD4",
                                        bgcolor="#35FFFFFF",
                                    ),
                                ),
                                ft.Text(f"{completion}%", size=11, weight=ft.FontWeight.W_900, color=WHITE),
                            ],
                        ),
                    ],
                ),
                ft.Container(width=1, height=56, bgcolor="#35FFFFFF"),
                *[
                    ft.Container(
                        expand=True,
                        padding=pad_sym(horizontal=14, vertical=9),
                        border_radius=15,
                        bgcolor="#18FFFFFF",
                        border=border_all(1, "#24FFFFFF"),
                        content=ft.Row(
                            spacing=11,
                            controls=[
                                ft.Container(
                                    width=36,
                                    height=36,
                                    border_radius=11,
                                    bgcolor="#24FFFFFF",
                                    alignment=CENTER,
                                    content=ft.Icon(STATUS_META[status]["icon"], size=18, color="#DDFDF8"),
                                ),
                                ft.Column(
                                    spacing=0,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    controls=[
                                        count_up(ctx.page, ft.Text(str(all_counts[status]), size=20, weight=ft.FontWeight.W_900, color=WHITE), all_counts[status]),
                                        ft.Text(STATUS_META[status]["title"], size=9, weight=ft.FontWeight.W_800, color="#C7D2FE"),
                                    ],
                                ),
                            ],
                        ),
                    )
                    for status in (STATUS_PENDING, STATUS_PROGRESS, STATUS_DONE)
                ],
            ],
        ),
    )

    filters = ft.Container(
        height=58,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=14,
        padding=pad_sym(horizontal=12, vertical=8),
        content=ft.Row(
            spacing=9,
            wrap=False,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ctx.search_field,
                dropdown(138, ctx.state["view"], ["All work", "Waiting", "Doing", "Completed"], on_view_change),
                dropdown(138, ctx.state["type"], ["All types", *available_types], on_type_change),
                dropdown(138, ctx.state["sort"], ["Newest", "Oldest", "Name", "Priority", "Progress"], on_sort_change),
                ft.Container(
                    height=32,
                    padding=pad_sym(horizontal=10),
                    border_radius=99,
                    bgcolor="#ECFDF5" if visible else "#FEF2F2",
                    border=border_all(1, "#A7F3D0" if visible else "#FECACA"),
                    content=ft.Row(
                        spacing=6,
                        controls=[
                            ft.Icon(ft.Icons.VISIBILITY_OUTLINED, size=14, color="#059669" if visible else "#DC2626"),
                            ft.Text(f"{len(visible)} of {total}", size=10, weight=ft.FontWeight.W_900, color="#047857" if visible else "#B91C1C"),
                        ],
                    ),
                ),
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_size=18,
                    icon_color="#0F766E",
                    tooltip="Sync and refresh",
                    on_click=ctx.sync_now,
                ),
                ft.IconButton(
                    icon=ft.Icons.FILTER_ALT_OFF_OUTLINED,
                    icon_size=18,
                    icon_color="#DC2626" if active_filters else MUTED_2,
                    tooltip="Clear filters",
                    disabled=not active_filters,
                    on_click=lambda _e: ctx.reset_filters(),
                ),
                ft.Container(expand=True),
                ft.Button(
                    "Add work",
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    on_click=lambda _e: ctx.show_create_new(),
                    height=40,
                    style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=10)),
                ),
                ft.Button(
                    "Add file",
                    icon=ft.Icons.UPLOAD_FILE_OUTLINED,
                    on_click=ctx.show_add_files,
                    height=40,
                    style=ft.ButtonStyle(bgcolor="#F8FAFC", color=TEXT, side=ft.BorderSide(1, BORDER), shape=ft.RoundedRectangleBorder(radius=10)),
                ),
                ft.Button(
                    "Add link",
                    icon=ft.Icons.LINK_ROUNDED,
                    on_click=ctx.show_add_link,
                    height=40,
                    style=ft.ButtonStyle(bgcolor="#F8FAFC", color=TEXT, side=ft.BorderSide(1, BORDER), shape=ft.RoundedRectangleBorder(radius=10)),
                ),
            ],
        ),
    )

    board = ft.Row(
        spacing=12,
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            fade_in_up(
                ctx.page,
                kanban_column(
                    ctx.page,
                    STATUS_META[status]["title"],
                    by_status[status],
                    STATUS_META[status]["bg"],
                    STATUS_META[status]["color"],
                    ctx.save_and_render,
                    ctx.all_tasks,
                    grouped=True,
                    group_limits=ctx.state["group_limits"],
                    on_more=ctx.render_current,
                    file_types_fn=ctx.file_types,
                    expanded_keys=ctx.state["expanded_groups"],
                    subtitle=STATUS_META[status]["subtitle"],
                    icon=STATUS_META[status]["icon"],
                    on_add=ctx.show_create_new if status == STATUS_PENDING else None,
                ),
                delay=0.06 * column_index,
                dy=0.05,
            )
            for column_index, status in enumerate((STATUS_PENDING, STATUS_PROGRESS, STATUS_DONE))
        ],
    )

    no_results = ft.Container(
        expand=True,
        border=border_all(1, BORDER),
        border_radius=18,
        bgcolor=WHITE,
        alignment=CENTER,
        content=ft.Column(
            spacing=10,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(width=58, height=58, border_radius=18, bgcolor="#FEF2F2", alignment=CENTER, content=ft.Icon(ft.Icons.SEARCH_OFF_OUTLINED, size=28, color="#DC2626")),
                ft.Text("No work matches these filters", size=16, weight=ft.FontWeight.W_900, color=TEXT),
                ft.Text("Your tasks are still safe. Clear the search and filters to show the full Board.", size=11, color=MUTED),
                ft.Button("Show all work", icon=ft.Icons.FILTER_ALT_OFF_OUTLINED, on_click=lambda _e: ctx.reset_filters(), style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
            ],
        ),
    )

    ctx.main_body.spacing = 12
    ctx.main_body.scroll = None
    ctx.main_body.expand = True
    ctx.main_body.controls = [
        pulse,
        filters,
        no_results if total and not visible else board,
    ]
    ctx.page.update()
