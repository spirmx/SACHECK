import calendar
import flet as ft
from datetime import date, datetime, timedelta

from core.flet_constants import (
    BORDER, DOING_BG, DOING_TEXT, DONE_BG, DONE_TEXT, MUTED, MUTED_2,
    PRIMARY, STATUS_DONE, STATUS_PENDING, STATUS_PROGRESS, STATUS_LABELS,
    TEXT, WAITING_BG, WAITING_TEXT, WHITE,
)
from core.flet_data import APP_NAME
from ui.dialogs import show_message
from ui.flet_widgets import CENTER, border_all, pad_only, pad_sym, task_icon
from ui.shared import DashboardContext

def render_calendar(ctx: DashboardContext) -> None:
    ctx.header_title.value = "Calendar"
    ctx.header_subtitle.value = f"{APP_NAME} / Work Schedule"

    calendar_state = ctx.state.setdefault("calendar_state", {
        "status": "All",
        "year": date.today().year,
        "month": date.today().month,
        "selected": date.today()
    })

    try:
        from core.flet_data import load_calendar_events, event_occurs_on
        calendar_events = load_calendar_events()
    except ImportError:
        calendar_events = []
        def event_occurs_on(event, day):
            try:
                return datetime.strptime(str(event.get("date") or "")[:10], "%Y-%m-%d").date() == day
            except (ValueError, TypeError):
                return False

    status_filter = calendar_state.get("status", "All")
    calendar_items = []
    grouped_by_day = {}
    all_grouped_by_day = {}
    events_by_day = {}

    def event_date_value(event):
        try:
            return datetime.strptime(str(event.get("date") or ""), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    def task_day(task):
        if task.get("status") == STATUS_DONE and task.get("done_date"):
            return str(task.get("done_date"))[:10]
        return str(task.get("status_date") or task.get("date_added") or datetime.now().date().isoformat())[:10]

    grid_first = date(calendar_state["year"], calendar_state["month"], 1)
    grid_start = grid_first - timedelta(days=grid_first.weekday())
    for offset in range(42):
        cell_day = grid_start + timedelta(days=offset)
        for event in calendar_events:
            if event_occurs_on(event, cell_day):
                events_by_day.setdefault(cell_day, []).append(event)

    for task in ctx.all_tasks:
        try:
            parsed = datetime.strptime(task_day(task), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        calendar_items.append((parsed, task))
        all_grouped_by_day.setdefault(parsed, []).append(task)
        if status_filter == "All" or task.get("status") == status_filter:
            grouped_by_day.setdefault(parsed, []).append(task)

    filtered_count = sum(len(items) for items in grouped_by_day.values())
    total_count = len(calendar_items)
    event_count = len(calendar_events)
    status_counts = {
        "All": total_count,
        STATUS_PENDING: sum(1 for _day, item in calendar_items if item.get("status") == STATUS_PENDING),
        STATUS_PROGRESS: sum(1 for _day, item in calendar_items if item.get("status") == STATUS_PROGRESS),
        STATUS_DONE: sum(1 for _day, item in calendar_items if item.get("status") == STATUS_DONE),
    }

    today = date.today()
    selected_day = calendar_state["selected"]
    year = calendar_state["year"]
    month = calendar_state["month"]
    ctx.progress_badge.value = f"{filtered_count}/{total_count} work + {event_count} events" if status_filter != "All" else f"{total_count} work + {event_count} events"
    month_label = ft.Text(f"{calendar.month_name[month]} {year}", size=24, weight=ft.FontWeight.W_800, color=TEXT)

    thai_holidays = {
        (1, 1): "New Year", (4, 6): "Chakri Day", (4, 13): "Songkran",
        (4, 14): "Songkran", (4, 15): "Songkran", (5, 1): "Labour Day",
        (5, 4): "Coronation Day", (6, 3): "Queen Suthida Birthday",
        (7, 28): "King Vajiralongkorn Birthday", (8, 12): "Mother's Day",
        (10, 13): "King Bhumibol Memorial Day", (10, 23): "Chulalongkorn Day",
        (12, 5): "Father's Day", (12, 10): "Constitution Day", (12, 31): "New Year's Eve",
    }

    def calendar_day_info(day):
        notes = []
        if day.weekday() == 5:
            notes.append(("SAT", "Weekend", "#BE185D", "#FDF2FA"))
        elif day.weekday() == 6:
            notes.append(("SUN", "Weekend", "#DC2626", "#FFF1F2"))
        holiday_name = thai_holidays.get((day.month, day.day))
        if holiday_name:
            notes.append(("HOL", holiday_name, "#7C3AED", "#F5F3FF"))
        return notes

    def refresh_calendar():
        ctx.render_current()

    def shift_month(delta):
        next_month = calendar_state["month"] + delta
        next_year = calendar_state["year"]
        if next_month < 1:
            next_month = 12
            next_year -= 1
        elif next_month > 12:
            next_month = 1
            next_year += 1
        calendar_state.update({"year": next_year, "month": next_month, "selected": date(next_year, next_month, 1)})
        refresh_calendar()

    def select_day(day):
        calendar_state["selected"] = day
        calendar_state["year"] = day.year
        calendar_state["month"] = day.month
        refresh_calendar()

    def set_calendar_status(status_value):
        calendar_state["status"] = status_value
        refresh_calendar()

    def status_chip(label, status_value, color, bg):
        selected = status_filter == status_value
        return ft.Container(
            height=44,
            padding=pad_sym(horizontal=14),
            border_radius=14,
            bgcolor=bg if selected else WHITE,
            border=border_all(1.5 if selected else 1, color if selected else BORDER),
            on_click=lambda _e, value=status_value: set_calendar_status(value),
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=9, height=9, border_radius=999, bgcolor=color),
                    ft.Text(label, size=12, weight=ft.FontWeight.W_800, color=TEXT),
                    ft.Container(
                        padding=pad_sym(horizontal=8, vertical=3),
                        border_radius=999,
                        bgcolor="#F8FAFC" if selected else "#EEF2F7",
                        content=ft.Text(str(status_counts.get(status_value, 0)), size=11, weight=ft.FontWeight.W_800, color=color),
                    ),
                ],
            ),
        )

    def task_chip(task):
        status = task.get("status")
        color = WAITING_TEXT if status == STATUS_PENDING else DOING_TEXT if status == STATUS_PROGRESS else DONE_TEXT
        bg = WHITE if status == STATUS_PENDING else "#FFF7ED" if status == STATUS_PROGRESS else "#DCFCE7"
        icon, icon_color = task_icon(task.get("type", "Other"))

        # Helper menu (simplified)
        def show_details(_e):
            from ui.dialogs import show_task_detail
            show_task_detail(ctx.page, task, ctx.save_and_render, ctx.all_tasks, runtime_file_types_fn=ctx.file_types)

        return ft.PopupMenuButton(
            content=ft.Container(
                height=21,
                border_radius=8,
                bgcolor=bg,
                border=border_all(1, "#E2E8F0"),
                padding=pad_sym(horizontal=6),
                content=ft.Row(
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(icon, size=10, color=icon_color),
                        ft.Text(task.get("name", "Untitled task"), size=10, weight=ft.FontWeight.W_700, color=color, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    ],
                ),
            ),
            items=[
                ft.PopupMenuItem(content="Details", icon=ft.Icons.INFO_OUTLINE, on_click=show_details)
            ]
        )

    def event_style(event):
        kind = event.get("kind", "Event")
        if kind == "Meeting":
            return "#2563EB", "#EFF6FF"
        elif kind == "Deadline":
            return "#DC2626", "#FEF2F2"
        return "#7C3AED", "#F5F3FF"

    def event_chip(event):
        color, bg = event_style(event)
        def show_event(_e):
            ctx.show_calendar_event_dialog(event=event)

        return ft.Container(
            height=21,
            border_radius=8,
            bgcolor=bg,
            border=border_all(1, color + "55"),
            padding=pad_sym(horizontal=6),
            on_click=show_event,
            content=ft.Row(
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.CELEBRATION_OUTLINED, size=10, color=color),
                    ft.Text(f"{event.get('time', '09:00')} {event.get('title', 'Event')}", size=10, weight=ft.FontWeight.W_800, color=color, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                ],
            ),
        )

    def day_cell(day):
        weekday_palette = [
            ("#EEF4FF", "#BFD4FF"), ("#EAFBFF", "#A7E6F0"), ("#ECFDF3", "#A7E3B8"),
            ("#FFFAE6", "#F4D783"), ("#FFF2E6", "#F0C29B"), ("#FDF2FA", "#E7A8D4"),
            ("#FFF1F2", "#E9A4A8"),
        ]
        is_current_month = day.month == month
        is_selected = day == selected_day
        is_today = day == today
        raw_day_tasks = sorted(all_grouped_by_day.get(day, []), key=lambda item: (item.get("status", ""), item.get("name", "")))
        day_tasks = sorted(grouped_by_day.get(day, []), key=lambda item: (item.get("status", ""), item.get("name", "")))
        day_events = sorted(events_by_day.get(day, []), key=lambda item: item.get("title", ""))
        waiting_count = sum(1 for item in raw_day_tasks if item.get("status") == STATUS_PENDING)
        doing_count = sum(1 for item in raw_day_tasks if item.get("status") == STATUS_PROGRESS)
        done_count = sum(1 for item in raw_day_tasks if item.get("status") == STATUS_DONE)
        visible_events = day_events[:1]
        visible_tasks = day_tasks[: max(0, 2 - len(visible_events))]
        weekday_bg, weekday_border = weekday_palette[day.weekday()]
        day_notes = calendar_day_info(day)
        cell_bg = "#DBEAFE" if is_today else (weekday_bg if is_current_month else "#F8FAFC")
        cell_border = PRIMARY if is_selected else (weekday_border if is_current_month else BORDER)
        return ft.Container(
            expand=True,
            height=90,
            bgcolor=cell_bg,
            border=border_all(3 if is_today else (2 if is_selected else 1), PRIMARY if is_today else cell_border),
            border_radius=14,
            padding=8,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=14, color="#302563EB", offset=ft.Offset(0, 5)) if is_today else (ft.BoxShadow(spread_radius=0, blur_radius=8, color="#10000000", offset=ft.Offset(0, 3)) if is_current_month else None),
            on_click=lambda _e, value=day: select_day(value),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=5,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Container(
                                        width=24,
                                        height=24,
                                        border_radius=999,
                                        bgcolor=PRIMARY if is_today else None,
                                        alignment=CENTER,
                                        content=ft.Text(str(day.day), size=13 if is_today else 12, weight=ft.FontWeight.W_900 if is_today else ft.FontWeight.W_800, color=WHITE if is_today else (TEXT if is_current_month else MUTED_2)),
                                    ),
                                    ft.Container(
                                        height=18,
                                        padding=pad_sym(horizontal=6),
                                        border_radius=999,
                                        bgcolor="#172554",
                                        alignment=CENTER,
                                        content=ft.Text("TODAY", size=8, weight=ft.FontWeight.W_900, color=WHITE),
                                    ) if is_today else ft.Container(width=0, height=0),
                                ],
                            ),
                            ft.Text(f"W{waiting_count} D{doing_count} S{done_count}" if raw_day_tasks else "", size=9, color=MUTED_2),
                        ],
                    ),
                    *[event_chip(event) for event in visible_events],
                    *[task_chip(task) for task in visible_tasks],
                    ft.Container(
                        height=15,
                        border_radius=999,
                        bgcolor="#F1F5F9",
                        alignment=CENTER,
                        content=ft.Text(f"+{(len(day_tasks) - len(visible_tasks)) + (len(day_events) - len(visible_events))}", size=9, weight=ft.FontWeight.W_700, color=MUTED),
                    ) if (len(day_tasks) > len(visible_tasks) or len(day_events) > len(visible_events)) else ft.Container(height=0),
                    ft.Row(
                        spacing=4,
                        controls=[
                            ft.Container(
                                height=13,
                                padding=pad_sym(horizontal=5),
                                border_radius=999,
                                bgcolor=note_bg,
                                content=ft.Text(code, size=8, weight=ft.FontWeight.W_900, color=note_color),
                            )
                            for code, _title, note_color, note_bg in day_notes[:2]
                        ],
                    ) if day_notes else ft.Container(height=0),
                ],
            ),
        )

    first_day = date(year, month, 1)
    start_day = first_day - timedelta(days=first_day.weekday())
    weekday_row = ft.Row(
        spacing=6,
        controls=[ft.Container(expand=True, alignment=CENTER, content=ft.Text(label, size=12, weight=ft.FontWeight.W_800, color=MUTED)) for label in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]],
    )
    week_rows = []
    for week_index in range(6):
        week_start = start_day + timedelta(days=week_index * 7)
        week_rows.append(ft.Row(spacing=6, controls=[day_cell(week_start + timedelta(days=offset)) for offset in range(7)]))

    selected_tasks = sorted(grouped_by_day.get(selected_day, []), key=lambda item: (item.get("status", ""), item.get("name", "")))
    selected_events = sorted(events_by_day.get(selected_day, []), key=lambda item: item.get("title", ""))
    selected_day_notes = calendar_day_info(selected_day)

    def selected_task_row(task):
        icon, icon_color = task_icon(task.get("type", "Other"))
        status = STATUS_LABELS.get(task.get("status"), "Waiting")
        status_bg = WAITING_BG if task.get("status") == STATUS_PENDING else DOING_BG if task.get("status") == STATUS_PROGRESS else DONE_BG
        status_color = WAITING_TEXT if task.get("status") == STATUS_PENDING else DOING_TEXT if task.get("status") == STATUS_PROGRESS else DONE_TEXT

        def show_details(_e):
            from ui.dialogs import show_task_detail
            show_task_detail(ctx.page, task, ctx.save_and_render, ctx.all_tasks, runtime_file_types_fn=ctx.file_types)

        return ft.Container(
            height=68,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=14,
            padding=pad_only(left=12, right=4),
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=38, height=38, border_radius=11, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Icon(icon, size=19, color=icon_color)),
                    ft.Column(
                        spacing=3,
                        expand=True,
                        controls=[
                            ft.Text(task.get("name", "Untitled task"), size=14, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(
                                spacing=6,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Text(task.get("type", "Other"), size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Container(
                                        padding=pad_sym(horizontal=7, vertical=3),
                                        border_radius=7,
                                        bgcolor=status_bg,
                                        content=ft.Text(status, size=11, weight=ft.FontWeight.W_800, color=status_color),
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        icon_size=18,
                        icon_color=MUTED_2,
                        items=[
                            ft.PopupMenuItem(content="Details", icon=ft.Icons.INFO_OUTLINE, on_click=show_details)
                        ]
                    ),
                ],
            ),
        )

    def selected_event_row(event):
        color, bg = event_style(event)
        note_preview = event.get("note") or "No note yet."
        event_time = event.get("time", "09:00")

        def show_event(_e):
            ctx.show_calendar_event_dialog(event=event)

        return ft.Container(
            height=116,
            bgcolor=bg,
            border=border_all(1, color + "55"),
            border_radius=14,
            padding=pad_only(left=12, right=4, top=10, bottom=10),
            on_click=show_event,
            content=ft.Row(
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Container(width=38, height=38, border_radius=11, bgcolor=WHITE, alignment=CENTER, content=ft.Icon(ft.Icons.CELEBRATION_OUTLINED, size=19, color=color)),
                    ft.Column(
                        spacing=4,
                        expand=True,
                        controls=[
                            ft.Text(event.get("title", "Event"), size=14, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"{event.get('kind', 'Event')} | {event_time}", size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(note_preview, size=12, color=MUTED, max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                ],
            ),
        )

    calendar_panel = ft.Container(
        expand=True,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=22,
        padding=14,
        content=ft.Column(spacing=6, controls=[weekday_row, *week_rows]),
    )
    detail_panel = ft.Container(
        width=360,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=22,
        padding=20,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            spacing=3,
                            controls=[
                                ft.Text(selected_day.strftime("%A"), size=13, weight=ft.FontWeight.W_800, color=MUTED),
                                ft.Text(selected_day.strftime("%d %B %Y"), size=20, weight=ft.FontWeight.W_800, color=TEXT),
                                ft.Text(f"{len(selected_tasks)} work / {len(selected_events)} events", size=11, weight=ft.FontWeight.W_700, color=MUTED_2),
                                ft.Row(
                                    spacing=6,
                                    controls=[
                                        ft.Container(
                                            padding=pad_sym(horizontal=8, vertical=4),
                                            border_radius=999,
                                            bgcolor=note_bg,
                                            content=ft.Text(title, size=10, weight=ft.FontWeight.W_800, color=note_color),
                                        )
                                        for _code, title, note_color, note_bg in selected_day_notes
                                    ],
                                ) if selected_day_notes else ft.Text("Regular workday", size=11, weight=ft.FontWeight.W_700, color=MUTED_2),
                            ],
                        ),
                        ft.Container(padding=pad_sym(horizontal=10, vertical=5), border_radius=999, bgcolor="#F8FAFC", content=ft.Text(str(len(selected_tasks) + len(selected_events)), size=13, weight=ft.FontWeight.W_800, color=PRIMARY)),
                    ],
                ),
                ft.Container(
                    expand=True,
                    content=ft.ListView(
                        expand=True,
                        spacing=10,
                        controls=[
                            *([ft.Text("Events", size=12, weight=ft.FontWeight.W_900, color=MUTED)] if selected_events else []),
                            *[selected_event_row(event) for event in selected_events],
                            *([ft.Text("Work", size=12, weight=ft.FontWeight.W_900, color=MUTED)] if selected_tasks else []),
                            *[selected_task_row(task) for task in selected_tasks],
                        ] if selected_tasks or selected_events else [ft.Container(expand=True, alignment=CENTER, content=ft.Text("No work or events on this day", size=14, color=MUTED_2))],
                    ),
                ),
            ],
        ),
    )
    toolbar = ft.Container(
        height=58,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=18,
        padding=pad_sym(horizontal=18, vertical=6),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[month_label]),
                ft.Row(
                    spacing=6,
                    controls=[
                        ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Previous month", on_click=lambda _e: shift_month(-1)),
                        ft.Button("Today", icon=ft.Icons.TODAY_OUTLINED, on_click=lambda _e: (calendar_state.update({"year": today.year, "month": today.month, "selected": today}), refresh_calendar())),
                        ft.Button("Add Event", icon=ft.Icons.ADD_ALERT_OUTLINED, on_click=lambda _e: ctx.show_calendar_event_dialog(selected_date=calendar_state.get("selected")), style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12))),
                        ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, tooltip="Next month", on_click=lambda _e: shift_month(1)),
                    ],
                ),
            ],
        ),
    )
    status_overview = ft.Container(
        height=54,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=18,
        padding=pad_sym(horizontal=18, vertical=5),
        content=ft.Row(
            spacing=10,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("Status", size=12, weight=ft.FontWeight.W_900, color=MUTED),
                status_chip("All work", "All", PRIMARY, "#EFF6FF"),
                status_chip("Waiting", STATUS_PENDING, WAITING_TEXT, WAITING_BG),
                status_chip("Doing", STATUS_PROGRESS, DOING_TEXT, DOING_BG),
                status_chip("Success", STATUS_DONE, DONE_TEXT, DONE_BG),
                ft.Container(expand=True),
                ft.Text("Click a status to verify every job by day.", size=11, color=MUTED_2),
            ],
        ),
    )

    ctx.main_body.controls = [toolbar, status_overview, ft.Row(spacing=18, expand=True, controls=[calendar_panel, detail_panel])]
    ctx.page.update()
