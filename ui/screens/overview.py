from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta

import flet as ft

from core.flet_constants import BORDER, MUTED, MUTED_2, PRIMARY, STATUS_DONE, STATUS_PENDING, STATUS_PROGRESS, TEXT, WHITE
from core.flet_data import broken_items, event_occurs_on, list_snapshots, load_activity_log, load_calendar_events
from core.flet_theme import calendar_event_style
from ui.flet_widgets import CENTER, border_all, count_up, fade_in_up, pad_only, pad_sym, pulse_dot, shake_bell, task_icon
from ui.shared import DashboardContext


STATUS_META = {
    STATUS_PENDING: ("Waiting", "#2563EB", "#EFF6FF"),
    STATUS_PROGRESS: ("Doing", "#D97706", "#FFFBEB"),
    STATUS_DONE: ("Success", "#16A34A", "#F0FDF4"),
}


def _hover(card, accent="#93C5FD"):
    def on_hover(event):
        active = event.data == "true"
        card.scale = 1.015 if active else 1
        card.border = border_all(1, accent if active else BORDER)
        card.shadow = ft.BoxShadow(blur_radius=18, color="#160F172A", offset=ft.Offset(0, 7)) if active else None
        try:
            card.update()
        except Exception:
            pass

    card.on_hover = on_hover
    card.animate_scale = ft.Animation(130, ft.AnimationCurve.EASE_OUT)
    return card


def _task_day(task):
    raw = task.get("done_date") if task.get("status") == STATUS_DONE else task.get("status_date") or task.get("date_added")
    try:
        return datetime.strptime(str(raw or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _safe_activity_message(entry):
    text = str(entry.get("message") or "Workspace activity")
    return "Workspace activity recorded" if "เน€" in text else text


def render_overview(ctx: DashboardContext) -> None:
    ctx.header_title.value = "Mission Control"
    ctx.header_subtitle.value = "SA CHECK / Home"

    tasks = ctx.all_tasks or []
    total = len(tasks)
    counts = Counter(task.get("status", STATUS_PENDING) for task in tasks)
    complete = counts[STATUS_DONE]
    completion = int((complete / total) * 100) if total else 0
    ctx.progress_badge.value = f"{completion}% complete"

    now = datetime.now()
    today = now.date()
    greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 18 else "Good evening"
    calendar_events = load_calendar_events()
    activity = [entry for entry in load_activity_log(40) if str(entry.get("action") or "").casefold() != "system guard"][:6]
    snapshots = list_snapshots(5)
    issue_count = len(broken_items(tasks, []))

    alerts = []
    for offset in range(14):
        day = today + timedelta(days=offset)
        for event in calendar_events:
            if event_occurs_on(event, day):
                alerts.append(
                    {
                        "day": day,
                        "time": str(event.get("time") or "09:00")[:5],
                        "title": str(event.get("title") or "Calendar event"),
                        "kind": str(event.get("kind") or "Event"),
                        "color": event.get("color"),
                        "event": True,
                    }
                )
        for task in tasks:
            task_day = _task_day(task)
            if task_day == day and task.get("status") != STATUS_DONE:
                alerts.append(
                    {
                        "day": day,
                        "time": "Work",
                        "title": str(task.get("name") or "Untitled work"),
                        "kind": STATUS_META.get(task.get("status"), ("Work",))[0],
                        "event": False,
                    }
                )
    alerts.sort(key=lambda item: (item["day"], item["time"], item["title"].casefold()))

    tomorrow = today + timedelta(days=1)
    soon_alerts = [item for item in alerts if item["day"] in (today, tomorrow)]

    def _alert_row(item):
        is_today = item["day"] == today
        tag = "TODAY" if is_today else "TMR"
        accent = "#FB7185" if is_today else "#FBBF24"  # rose for today, amber for tomorrow
        title = str(item["title"])
        if len(title) > 34:
            title = title[:33] + "…"
        dot = pulse_dot(ctx.page, accent, size=6) if is_today else ft.Container(width=8, height=8, border_radius=99, bgcolor=accent)
        return ft.Container(
            padding=pad_sym(horizontal=10, vertical=6),
            border_radius=11,
            bgcolor="#18FFFFFF",
            border=border_all(1, "#22FFFFFF"),
            content=ft.Row(
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    dot,
                    ft.Container(padding=pad_sym(horizontal=6, vertical=1), border_radius=99, bgcolor="#26FFFFFF", content=ft.Text(tag, size=8, weight=ft.FontWeight.W_900, color=accent)),
                    ft.Text(title, size=12, weight=ft.FontWeight.W_700, color=WHITE, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(item["time"], size=10, weight=ft.FontWeight.W_800, color="#BAE6FD"),
                ],
            ),
        )

    visible_alerts = soon_alerts[:3]
    extra_alerts = len(soon_alerts) - len(visible_alerts)

    if soon_alerts:
        alert_body = ft.Column(
            spacing=6,
            controls=[
                ft.Row(
                    spacing=7,
                    controls=[
                        shake_bell(ctx.page, ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED, size=14, color="#5EEAD4")),
                        ft.Text("TODAY & TOMORROW", size=10, weight=ft.FontWeight.W_900, color="#BAE6FD", expand=True),
                        ft.Container(padding=pad_sym(horizontal=7, vertical=1), border_radius=99, bgcolor="#26FFFFFF", content=ft.Text(str(len(soon_alerts)), size=9, weight=ft.FontWeight.W_900, color=WHITE)),
                    ],
                ),
                *[_alert_row(item) for item in visible_alerts],
                ft.Text(f"+{extra_alerts} more · tap Calendar", size=9, weight=ft.FontWeight.W_700, color="#93C5FD") if extra_alerts > 0 else ft.Container(height=0),
            ],
        )
    else:
        alert_body = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            spacing=6,
            controls=[
                ft.Icon(ft.Icons.EVENT_AVAILABLE_OUTLINED, size=26, color="#5EEAD4"),
                ft.Text("You're clear", size=13, weight=ft.FontWeight.W_900, color=WHITE),
                ft.Text("No alerts today or tomorrow", size=10, color="#BAE6FD"),
            ],
        )

    alert_panel = fade_in_up(
        ctx.page,
        ft.Container(
            expand=2,
            padding=pad_sym(horizontal=13, vertical=11),
            border_radius=16,
            bgcolor="#14FFFFFF",
            border=border_all(1, "#26FFFFFF"),
            on_click=lambda _e: ctx.show_calendar(),
            content=alert_body,
        ),
        delay=0.08,
    )

    hero = ft.Container(
        expand=3,
        height=200,
        border_radius=22,
        padding=22,
        gradient=ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1), colors=["#0F172A", "#1E3A8A", "#0F766E"]),
        content=ft.Row(
            spacing=20,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Column(
                    expand=3,
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Container(width=8, height=8, border_radius=99, bgcolor="#5EEAD4"),
                                ft.Text(today.strftime("%A, %d %B %Y").upper(), size=10, weight=ft.FontWeight.W_900, color="#BAE6FD"),
                            ],
                        ),
                        ft.Text(f"{greeting}. Ready to run the day?", size=24, weight=ft.FontWeight.W_900, color=WHITE, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.Button("Create work", icon=ft.Icons.ADD_CIRCLE_OUTLINE, on_click=lambda _e: ctx.show_create_new(), style=ft.ButtonStyle(bgcolor=WHITE, color="#0F172A", shape=ft.RoundedRectangleBorder(radius=12))),
                                ft.Button("Open Calendar", icon=ft.Icons.CALENDAR_TODAY_OUTLINED, on_click=lambda _e: ctx.show_calendar(), style=ft.ButtonStyle(bgcolor="#1D4ED8", color=WHITE, side=ft.BorderSide(1, "#7DD3FC"), shape=ft.RoundedRectangleBorder(radius=12))),
                            ],
                        ),
                    ],
                ),
                alert_panel,
            ],
        ),
    )

    pct_ring = ft.ProgressRing(value=completion / 100, width=112, height=112, stroke_width=11, color="#16A34A", bgcolor="#DCFCE7")
    pct_text = ft.Text(f"{completion}%", size=23, weight=ft.FontWeight.W_900, color=TEXT)
    count_up(ctx.page, pct_text, completion, suffix="%", ring=pct_ring, ring_divisor=100)

    def pulse_row(key):
        color = STATUS_META[key][1]
        dot = pulse_dot(ctx.page, color, size=7) if key == STATUS_PROGRESS else ft.Container(width=8, height=8, border_radius=99, bgcolor=color)
        return ft.Row(spacing=7, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[dot, ft.Text(f"{STATUS_META[key][0]}  {counts[key]}", size=11, weight=ft.FontWeight.W_700, color=MUTED)])

    ring = ft.Container(
        expand=1,
        height=200,
        border=border_all(1, BORDER),
        border_radius=22,
        bgcolor=WHITE,
        padding=20,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=18,
            controls=[
                ft.Stack(
                    width=112,
                    height=112,
                    alignment=CENTER,
                    controls=[
                        pct_ring,
                        ft.Column(spacing=0, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[pct_text, ft.Text("COMPLETE", size=9, weight=ft.FontWeight.W_900, color=MUTED_2)]),
                    ],
                ),
                ft.Column(
                    spacing=8,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Text("Work pulse", size=16, weight=ft.FontWeight.W_900, color=TEXT),
                        *[pulse_row(key) for key in (STATUS_PENDING, STATUS_PROGRESS, STATUS_DONE)],
                    ],
                ),
            ],
        ),
    )

    nav_items = [
        ("Board", "Manage work", ft.Icons.DASHBOARD_ROUNDED, "#2563EB", "#EFF6FF", ctx.show_board),
        ("Files", "Browse assets", ft.Icons.FOLDER_OUTLINED, "#7C3AED", "#F5F3FF", ctx.show_browser),
        ("Calendar", "Plan & alerts", ft.Icons.CALENDAR_TODAY_OUTLINED, "#D97706", "#FFFBEB", ctx.show_calendar),
        ("Templates", "Reuse faster", ft.Icons.ARTICLE_OUTLINED, "#DB2777", "#FDF2F8", ctx.show_templates),
        ("Health", "System safety", ft.Icons.HEALTH_AND_SAFETY_OUTLINED, "#059669", "#ECFDF5", ctx.show_health),
        ("Settings", "Configure", ft.Icons.SETTINGS_OUTLINED, "#475569", "#F1F5F9", ctx.show_settings),
    ]

    def nav_tile(label, hint, icon, color, bg, action):
        card = ft.Container(
            expand=True,
            height=76,
            padding=pad_sym(horizontal=13, vertical=10),
            border=border_all(1, BORDER),
            border_radius=16,
            bgcolor=WHITE,
            ink=True,
            on_click=lambda _e: action(),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Container(width=38, height=38, border_radius=12, bgcolor=bg, alignment=CENTER, content=ft.Icon(icon, size=19, color=color)),
                    ft.Column(spacing=1, alignment=ft.MainAxisAlignment.CENTER, expand=True, controls=[ft.Text(label, size=12, weight=ft.FontWeight.W_900, color=TEXT), ft.Text(hint, size=9, color=MUTED_2, max_lines=1)]),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, size=15, color=MUTED_2),
                ],
            ),
        )
        return _hover(card, color + "88")

    navigation = ft.Row(spacing=10, controls=[fade_in_up(ctx.page, nav_tile(*item), delay=0.05 * index) for index, item in enumerate(nav_items)])

    type_counts = Counter(str(task.get("type") or "Other") for task in tasks)
    top_types = type_counts.most_common(5)
    max_type_count = max((count for _name, count in top_types), default=1)

    def type_bar(name, count):
        icon, color = task_icon(name)
        return ft.Row(
            spacing=10,
            controls=[
                ft.Container(width=28, height=28, border_radius=9, bgcolor=color + "18", alignment=CENTER, content=ft.Icon(icon, size=14, color=color)),
                ft.Text(name, width=92, size=11, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Container(expand=True, height=8, border_radius=99, bgcolor="#EEF2F7", content=ft.Row(spacing=0, controls=[ft.Container(expand=max(1, count), height=8, border_radius=99, bgcolor=color), ft.Container(expand=max(1, max_type_count - count))])),
                ft.Text(str(count), width=26, size=11, weight=ft.FontWeight.W_900, color=MUTED, text_align=ft.TextAlign.RIGHT),
            ],
        )

    week_days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    weekly_counts = [sum(1 for task in tasks if _task_day(task) == day) for day in week_days]
    weekly_max = max(weekly_counts, default=1) or 1

    def day_bar(day, count):
        bar_height = 10 + int(54 * count / weekly_max) if count else 7
        return ft.Column(
            spacing=5,
            expand=True,
            alignment=ft.MainAxisAlignment.END,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(str(count), size=9, weight=ft.FontWeight.W_800, color=MUTED_2),
                ft.Container(width=22, height=bar_height, border_radius=7, bgcolor="#2563EB" if day == today else "#BFDBFE", animate_size=ft.Animation(180, ft.AnimationCurve.EASE_OUT)),
                ft.Text(day.strftime("%a")[:2], size=9, weight=ft.FontWeight.W_800, color=TEXT if day == today else MUTED_2),
            ],
        )

    analytics = ft.Container(
        expand=3,
        height=292,
        padding=18,
        border=border_all(1, BORDER),
        border_radius=20,
        bgcolor=WHITE,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Work analytics", size=17, weight=ft.FontWeight.W_900, color=TEXT), ft.Text("Live local data", size=10, weight=ft.FontWeight.W_800, color="#059669")]),
                ft.Row(
                    spacing=22,
                    expand=True,
                    controls=[
                        ft.Container(expand=3, content=ft.Column(spacing=10, controls=[ft.Text("TOP FILE TYPES", size=9, weight=ft.FontWeight.W_900, color=MUTED_2), *([type_bar(name, count) for name, count in top_types] or [ft.Text("No work data yet", color=MUTED_2)])])),
                        ft.Container(width=1, bgcolor=BORDER),
                        ft.Container(expand=2, content=ft.Column(spacing=8, controls=[ft.Text("7-DAY ACTIVITY", size=9, weight=ft.FontWeight.W_900, color=MUTED_2), ft.Row(height=168, spacing=7, vertical_alignment=ft.CrossAxisAlignment.END, controls=[day_bar(day, count) for day, count in zip(week_days, weekly_counts)])])),
                    ],
                ),
            ],
        ),
    )

    def alert_row(item):
        is_today = item["day"] == today
        if item["event"]:
            color, bg = calendar_event_style(item.get("color"))
        else:
            color = "#DC2626" if is_today else "#2563EB"
            bg = "#FEF2F2" if is_today else "#EFF6FF"
        return ft.Container(
            height=48,
            padding=pad_sym(horizontal=10, vertical=6),
            border_radius=12,
            bgcolor=bg,
            on_click=lambda _e: ctx.show_calendar(),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Container(width=36, height=36, border_radius=10, bgcolor=WHITE, alignment=CENTER, content=ft.Column(spacing=0, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text(str(item["day"].day), size=13, weight=ft.FontWeight.W_900, color=color), ft.Text(item["day"].strftime("%b").upper(), size=7, weight=ft.FontWeight.W_900, color=MUTED_2)])),
                    ft.Column(spacing=1, expand=True, alignment=ft.MainAxisAlignment.CENTER, controls=[ft.Text(item["title"], size=11, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Text(f"{item['time']} · {item['kind']}", size=9, color=MUTED)]),
                    shake_bell(ctx.page, ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, size=16, color=color), period=3.4) if is_today else ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, size=16, color=color),
                ],
            ),
        )

    calendar_panel = ft.Container(
        expand=2,
        height=292,
        padding=18,
        border=border_all(1, BORDER),
        border_radius=20,
        bgcolor=WHITE,
        content=ft.Column(
            spacing=9,
            controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text("Calendar alerts", size=17, weight=ft.FontWeight.W_900, color=TEXT), ft.TextButton("Open", icon=ft.Icons.ARROW_FORWARD, on_click=lambda _e: ctx.show_calendar())]),
                *([alert_row(item) for item in alerts[:4]] or [ft.Container(height=170, alignment=CENTER, content=ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, controls=[ft.Icon(ft.Icons.EVENT_AVAILABLE_OUTLINED, size=34, color="#16A34A"), ft.Text("No alerts in the next 14 days", size=11, color=MUTED)]))]),
                ft.Text(f"+{len(alerts) - 4} more alerts" if len(alerts) > 4 else "14-day alert window", size=9, color=MUTED_2),
            ],
        ),
    )

    def pulse(label, value, icon, color, bg, action):
        return ft.Container(
            expand=True,
            height=70,
            padding=pad_sym(horizontal=12, vertical=9),
            border=border_all(1, BORDER),
            border_radius=15,
            bgcolor=WHITE,
            on_click=lambda _e: action(),
            content=ft.Row(spacing=9, controls=[ft.Container(width=34, height=34, border_radius=10, bgcolor=bg, alignment=CENTER, content=ft.Icon(icon, size=17, color=color)), ft.Column(spacing=1, expand=True, alignment=ft.MainAxisAlignment.CENTER, controls=[ft.Text(label, size=9, weight=ft.FontWeight.W_900, color=MUTED_2), ft.Text(value, size=11, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)])]),
        )

    system_pulse = ft.Row(
        spacing=10,
        controls=[
            pulse("CONNECTION", "Offline mode" if ctx.settings.get("offline_mode") else "Online checks", ft.Icons.WIFI, "#059669" if not ctx.settings.get("offline_mode") else "#DC2626", "#ECFDF5", ctx.show_settings),
            pulse("LAST SYNC", str(ctx.settings.get("last_sync_at") or "Not synced"), ft.Icons.SYNC, "#2563EB", "#EFF6FF", ctx.sync_now),
            pulse("HEALTH", "All clear" if not issue_count else f"{issue_count} item(s) need review", ft.Icons.HEALTH_AND_SAFETY_OUTLINED, "#16A34A" if not issue_count else "#D97706", "#F0FDF4" if not issue_count else "#FFFBEB", ctx.show_health),
            pulse("SNAPSHOTS", f"{len(snapshots)} recent backups", ft.Icons.CLOUD_DONE_OUTLINED, "#7C3AED", "#F5F3FF", ctx.show_health),
        ],
    )

    def activity_row(entry):
        return ft.Row(
            spacing=10,
            controls=[
                ft.Container(width=8, height=8, border_radius=99, bgcolor="#2563EB"),
                ft.Text(str(entry.get("action") or "Activity"), width=105, size=10, weight=ft.FontWeight.W_900, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(_safe_activity_message(entry), expand=True, size=10, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(str(entry.get("time") or "")[-8:], size=9, color=MUTED_2),
            ],
        )

    activity_panel = ft.Container(
        border=border_all(1, BORDER),
        border_radius=18,
        bgcolor="#F8FAFC",
        padding=14,
        content=ft.Column(spacing=8, controls=[ft.Text("RECENT ACTIVITY", size=9, weight=ft.FontWeight.W_900, color=MUTED_2), *([activity_row(item) for item in activity[:3]] or [ft.Text("No recent activity", size=10, color=MUTED_2)])]),
    )

    ctx.main_body.spacing = 14
    ctx.main_body.controls = [
        ft.Column(
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row(spacing=14, controls=[hero, ring]),
                navigation,
                ft.Row(spacing=14, controls=[analytics, calendar_panel]),
                system_pulse,
                activity_panel,
            ],
        )
    ]
    ctx.page.update()
