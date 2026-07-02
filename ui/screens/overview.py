import time

import flet as ft

from core.flet_constants import (
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
from ui.flet_widgets import CENTER, border_all, pad_only, pad_sym, task_icon
from ui.shared import DashboardContext

_EASE = ft.AnimationCurve.EASE_OUT
STATUS_META = {
    STATUS_PENDING: ("Waiting", "#2563EB", "#EFF6FF"),
    STATUS_PROGRESS: ("Doing", "#D97706", "#FFFBEB"),
    STATUS_DONE: ("Success", "#16A34A", "#F0FDF4"),
}
PREVIEW_LIMIT = 6


def _hoverable(card, accent, base_border=BORDER):
    def on_hover(event):
        hovering = event.data == "true"
        card.scale = 1.02 if hovering else 1
        card.border = border_all(1, accent if hovering else base_border)
        card.shadow = ft.BoxShadow(spread_radius=0, blur_radius=16, color="#16000000", offset=ft.Offset(0, 7)) if hovering else None
        card.update()

    card.on_hover = on_hover
    card.animate = ft.Animation(150, _EASE)
    card.animate_scale = ft.Animation(150, _EASE)
    return card


def render_overview(ctx: DashboardContext) -> None:
    ctx.header_title.value = "Command Center"
    ctx.header_subtitle.value = "SA CHECK / Overview"

    tasks = ctx.all_tasks or []
    total = len(tasks)
    waiting = [task for task in tasks if task.get("status") == STATUS_PENDING]
    doing = [task for task in tasks if task.get("status") == STATUS_PROGRESS]
    done = [task for task in tasks if task.get("status") == STATUS_DONE]
    pct = int((len(done) / total) * 100) if total else 0
    ctx.progress_badge.value = f"{pct}% Complete"

    hero = ft.Container(
        border=border_all(1, BORDER),
        border_radius=18,
        bgcolor=WHITE,
        padding=26,
        content=ft.Column(
            spacing=10,
            controls=[
                ft.Row(spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Container(width=8, height=8, border_radius=99, bgcolor=PRIMARY),
                    ft.Text("SA INTELLIGENCE", size=11, weight=ft.FontWeight.W_900, color=PRIMARY),
                ]),
                ft.Text(f"{len(doing)} in progress  ·  {len(waiting)} waiting", size=27, weight=ft.FontWeight.W_900, color=TEXT),
                ft.Text("ภาพรวมงานทั้งหมด ผูกกับโฟลเดอร์งานจริง — เปิด Work Board เพื่อจัดการ หรือสร้างงานใหม่", size=13, color=MUTED),
                ft.Row(spacing=10, controls=[
                    ft.Button("Open board", icon=ft.Icons.DASHBOARD_ROUNDED, on_click=lambda _e: ctx.show_board(), style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12), animation_duration=140)),
                    ft.Button("New work", icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda _e: ctx.show_create_new(), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), animation_duration=140)),
                ]),
            ],
        ),
    )

    def metric_card(label, value, accent, icon, fraction):
        bar = ft.Container(
            height=5,
            border_radius=99,
            bgcolor="#EEF2F6",
            content=ft.Row(
                spacing=0,
                controls=[
                    ft.Container(expand=max(1, int(round(fraction * 100))), height=5, border_radius=99, bgcolor=accent),
                    ft.Container(expand=max(1, 100 - int(round(fraction * 100)))),
                ],
            ) if 0 < fraction < 1 else ft.Container(height=5, border_radius=99, bgcolor=accent if fraction >= 1 else "#EEF2F6"),
        )
        card = ft.Container(
            expand=True,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=14,
            padding=pad_sym(horizontal=16, vertical=13),
            content=ft.Column(
                spacing=9,
                controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Text(label, size=11, weight=ft.FontWeight.W_800, color=MUTED),
                        ft.Container(width=28, height=28, border_radius=9, bgcolor=accent + "18", alignment=CENTER, content=ft.Icon(icon, size=16, color=accent)),
                    ]),
                    ft.Text(str(value), size=27, weight=ft.FontWeight.W_900, color=TEXT),
                    bar,
                ],
            ),
        )
        return _hoverable(card, accent + "88")

    metrics = ft.Row(
        spacing=12,
        controls=[
            metric_card("TOTAL", total, PRIMARY, ft.Icons.APPS_ROUNDED, 1.0),
            metric_card("WAITING", len(waiting), "#2563EB", ft.Icons.INBOX_OUTLINED, (len(waiting) / total) if total else 0),
            metric_card("DOING", len(doing), "#D97706", ft.Icons.BOLT_OUTLINED, (len(doing) / total) if total else 0),
            metric_card("SUCCESS", len(done), "#16A34A", ft.Icons.CHECK_CIRCLE_OUTLINE, (len(done) / total) if total else 0),
        ],
    )

    def preview_row(task):
        icon, icon_color = task_icon(task.get("type", "Other"))
        row = ft.Container(
            height=42,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=10,
            padding=pad_only(left=10, right=10),
            ink=True,
            on_click=lambda _e: ctx.show_board(),
            tooltip="Open on board",
            content=ft.Row(
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=26, height=26, border_radius=8, bgcolor=icon_color, alignment=CENTER, content=ft.Icon(icon, size=14, color=WHITE)),
                    ft.Text(task.get("name", "Untitled task"), size=12, color=TEXT, weight=ft.FontWeight.W_500, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, size=16, color=MUTED_2),
                ],
            ),
        )
        return _hoverable(row, icon_color)

    def mini_column(status, items):
        label, color, bg = STATUS_META[status]
        rows = [preview_row(task) for task in items[:PREVIEW_LIMIT]]
        if not items:
            rows.append(ft.Container(height=70, alignment=CENTER, content=ft.Text("No work here yet", size=12, color=MUTED_2)))
        elif len(items) > PREVIEW_LIMIT:
            rows.append(ft.Container(alignment=CENTER, content=ft.TextButton(f"+{len(items) - PREVIEW_LIMIT} more on board", icon=ft.Icons.ARROW_FORWARD, on_click=lambda _e: ctx.show_board())))
        return ft.Container(
            expand=True,
            border=border_all(1, BORDER),
            border_radius=16,
            bgcolor="#F8FAFC",
            padding=12,
            content=ft.Column(
                spacing=9,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Row(spacing=8, controls=[
                                ft.Container(width=9, height=9, border_radius=99, bgcolor=color),
                                ft.Text(label, size=13, weight=ft.FontWeight.W_800, color=TEXT),
                            ]),
                            ft.Container(padding=pad_sym(horizontal=8, vertical=2), border_radius=999, bgcolor=bg, content=ft.Text(str(len(items)), size=11, weight=ft.FontWeight.W_800, color=color)),
                        ],
                    ),
                    *rows,
                ],
            ),
        )

    mini = ft.Row(
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.START,
        controls=[
            mini_column(STATUS_PENDING, waiting),
            mini_column(STATUS_PROGRESS, doing),
            mini_column(STATUS_DONE, done),
        ],
    )

    body = ft.Column(
        spacing=14,
        controls=[hero, metrics, mini],
        opacity=0,
        offset=ft.Offset(0, 0.03),
        animate_opacity=ft.Animation(240, _EASE),
        animate_offset=ft.Animation(240, _EASE),
    )

    ctx.main_body.spacing = 14
    ctx.main_body.controls = [body]
    ctx.page.update()

    def _enter():
        try:
            time.sleep(0.03)
            body.opacity = 1
            body.offset = ft.Offset(0, 0)
            body.update()
        except Exception:
            pass

    try:
        ctx.page.run_thread(_enter)
    except Exception:
        body.opacity = 1
        body.offset = ft.Offset(0, 0)
