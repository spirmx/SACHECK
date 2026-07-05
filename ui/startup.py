from __future__ import annotations

import sys
import time
from pathlib import Path

import flet as ft

from core.startup_preflight import StartupResult, run_startup_preflight


# --- Clean light loader palette (white base, teal accent) ---
BG = "#FFFFFF"
SURFACE = "#FFFFFF"
PANEL = "#F8FAFC"
BORDER = "#E2E8F0"
ACCENT = "#0F766E"          # teal brand accent (progress, active step)
ACCENT_SOFT = "#14B8A6"
ACCENT_TINT = "#F0FDFA"
TEXT = "#0F172A"
MUTED = "#64748B"
FAINT = "#94A3B8"
TRACK = "#E8EEF3"
SUCCESS = "#16A34A"
WARNING = "#D97706"
ERROR = "#DC2626"
MINIMUM_LOADER_SECONDS = 1.4
STEP_COLORS = (ACCENT, ACCENT, ACCENT, ACCENT)
STEP_BACKGROUNDS = (PANEL, PANEL, PANEL, PANEL)


def _safe_update(page: ft.Page) -> None:
    try:
        page.update()
    except Exception:
        pass


def show_startup_loader(
    page: ft.Page,
    *,
    dashboard_main,
    settings: dict,
    app_name: str,
    app_version: str,
    app_logo: str,
    app_root: Path,
    manifest_url: str,
) -> None:
    page.title = f"{app_name} - Starting"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(font_family="Segoe UI")
    try:
        page.window.title_bar_hidden = True
        page.window.title_bar_buttons_hidden = True
        page.window.maximized = False
        page.window.width = 800
        page.window.height = 560
        page.window.min_width = 800
        page.window.min_height = 560
        page.window.resizable = False
        page.window.bgcolor = BG
        icon_path = app_root / "assets" / "app" / "app.ico"
        if icon_path.is_file():
            page.window.icon = str(icon_path)
    except Exception:
        pass

    status_text = ft.Text("Starting SA CHECK services...", size=13, weight=ft.FontWeight.W_600, color=TEXT, expand=True)
    status_icon = ft.Icon(ft.Icons.ROCKET_LAUNCH_OUTLINED, size=19, color=ACCENT)
    status_panel = ft.Container(
        height=48,
        width=360,
        padding=ft.Padding.symmetric(horizontal=14),
        border_radius=12,
        bgcolor=PANEL,
        border=ft.Border.all(1, BORDER),
        content=ft.Row(spacing=10, controls=[status_icon, status_text]),
    )
    progress = ft.ProgressBar(value=0.04, height=6, color=ACCENT, bgcolor=TRACK, border_radius=99)
    percent_text = ft.Text("4%", size=11, weight=ft.FontWeight.W_800, color=ACCENT)
    mode_chip = ft.Container(
        visible=False,
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        border_radius=99,
        bgcolor=PANEL,
        border=ft.Border.all(1, BORDER),
        content=ft.Text("Online check", size=10, weight=ft.FontWeight.W_700, color=MUTED),
    )
    step_labels = [
        ft.Text("Environment", size=10, color=MUTED),
        ft.Text("Assets", size=10, color=MUTED),
        ft.Text("Connectivity", size=10, color=MUTED),
        ft.Text("Finalize", size=10, color=MUTED),
    ]
    step_dots = [ft.Container(width=9, height=9, border_radius=99, bgcolor="#CBD5E1") for _ in range(4)]
    step_cards = [
        ft.Container(
            width=118,
            height=46,
            padding=ft.Padding.symmetric(horizontal=11),
            border_radius=11,
            bgcolor=STEP_BACKGROUNDS[index],
            border=ft.Border.all(1, STEP_COLORS[index] if index == 0 else BORDER),
            content=ft.Row(spacing=8, controls=[step_dots[index], step_labels[index]]),
        )
        for index in range(4)
    ]

    step_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=8,
        controls=step_cards,
    )
    logo = ft.Container(
        width=88,
        height=88,
        border_radius=24,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        bgcolor="#F1F5F9",
        border=ft.Border.all(1, ACCENT_SOFT),
        shadow=ft.BoxShadow(blur_radius=26, spread_radius=1, color="#2214B8A6", offset=ft.Offset(0, 6)),
        content=ft.Image(
            src=app_logo,
            width=88,
            height=88,
            fit=ft.BoxFit.COVER,
            error_content=ft.Container(
                alignment=ft.Alignment(0, 0),
                content=ft.Text("SA", size=26, weight=ft.FontWeight.W_900, color=ACCENT),
            ),
        ),
    )
    loader_surface = ft.Container(
        expand=True,
        bgcolor=BG,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
            controls=[
                ft.Container(height=3, width=180, bgcolor=ACCENT, border_radius=99),
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                    padding=ft.Padding.only(left=112, right=112, top=30, bottom=26),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=14,
                        controls=[
                            logo,
                            ft.Text(app_name, size=26, weight=ft.FontWeight.W_900, color=TEXT),
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=12, vertical=4),
                                border_radius=99,
                                bgcolor=ACCENT_TINT,
                                border=ft.Border.all(1, "#99F6E4"),
                                content=ft.Row(
                                    spacing=6,
                                    controls=[
                                        ft.Container(width=6, height=6, border_radius=99, bgcolor=ACCENT),
                                        ft.Text(f"VERSION {app_version}", size=10, weight=ft.FontWeight.W_800, color=ACCENT),
                                    ],
                                ),
                            ),
                            status_panel,
                            ft.Row(spacing=10, width=372, controls=[ft.Container(expand=True, content=progress), percent_text]),
                            step_row,
                            mode_chip,
                            ft.Row(
                                spacing=6,
                                alignment=ft.MainAxisAlignment.CENTER,
                                controls=[
                                    ft.Icon(ft.Icons.LOCK_OUTLINE, size=13, color=FAINT),
                                    ft.Text("Work folders, settings, and cache stay local.", size=10, color=FAINT),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )
    page.add(loader_surface)
    _safe_update(page)

    async def reveal_loader() -> None:
        try:
            await page.window.center()
        except Exception:
            pass
        try:
            page.window.visible = True
        except Exception:
            pass
        _safe_update(page)

    try:
        page.run_task(reveal_loader)
    except Exception:
        try:
            page.window.visible = True
        except Exception:
            pass
        _safe_update(page)

    step_indexes = {"boot": 0, "local": 1, "online": 2, "repair": 2, "offline": 2, "ready": 3}

    def set_status(step: str, message: str, value: float) -> None:
        status_text.value = message
        progress.value = value
        percent_text.value = f"{int(value * 100)}%"
        active = step_indexes.get(step, 0)
        for index, dot in enumerate(step_dots):
            if index < active:
                dot.bgcolor = SUCCESS
                step_cards[index].border = ft.Border.all(1, BORDER)
                step_labels[index].color = MUTED
            elif index == active:
                dot.bgcolor = STEP_COLORS[index]
                step_cards[index].border = ft.Border.all(1, STEP_COLORS[index])
                step_labels[index].color = TEXT
            else:
                dot.bgcolor = "#CBD5E1"
                step_cards[index].border = ft.Border.all(1, BORDER)
                step_labels[index].color = MUTED
        if step == "online":
            mode_chip.visible = True
            mode_chip.bgcolor = "#FFFBEB"
            mode_chip.border = ft.Border.all(1, "#FCD38A")
            mode_chip.content.value = "Checking online services"
            mode_chip.content.color = "#A65D03"
        elif step == "offline":
            mode_chip.visible = True
            mode_chip.bgcolor = PANEL
            mode_chip.border = ft.Border.all(1, BORDER)
            mode_chip.content.value = "Offline mode"
            mode_chip.content.color = MUTED
        elif step == "repair":
            progress.color = ERROR
            status_panel.bgcolor = "#FEF2F2"
            status_panel.border = ft.Border.all(1, "#FECACA")
            status_icon.color = ERROR
            mode_chip.visible = True
            mode_chip.bgcolor = "#FEF2F2"
            mode_chip.border = ft.Border.all(1, "#FECACA")
            mode_chip.content.value = "Verified repair"
            mode_chip.content.color = "#BE123C"
        elif step == "ready":
            progress.color = SUCCESS
            status_panel.bgcolor = "#ECFDF5"
            status_panel.border = ft.Border.all(1, "#A7E4C5")
            status_icon.color = SUCCESS
        _safe_update(page)

    def worker() -> None:
        started = time.perf_counter()
        result = run_startup_preflight(
            settings=settings,
            manifest_url=manifest_url,
            app_version=app_version,
            app_root=app_root,
            frozen=bool(getattr(sys, "frozen", False)),
            timeout=1.0,
            status=set_status,
        )
        remaining = MINIMUM_LOADER_SECONDS - (time.perf_counter() - started)
        if remaining > 0:
            time.sleep(remaining)
        if result.health_issues:
            status_text.value = "Opened in safe mode; repair details are available in Health Center."
            status_text.color = "#BE123C"
            progress.color = WARNING
            _safe_update(page)
            time.sleep(0.35)
        try:
            page.controls.clear()
            page.window.resizable = True
        except Exception:
            pass
        try:
            dashboard_main(page, startup_result=result)
        except Exception as exc:
            page.controls.clear()
            page.bgcolor = BG
            page.add(
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Container(
                        width=560,
                        padding=32,
                        border_radius=16,
                        bgcolor=SURFACE,
                        border=ft.Border.all(1, "#FECACA"),
                        content=ft.Column(
                            spacing=14,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.HEALTH_AND_SAFETY_OUTLINED, size=42, color=ERROR),
                                ft.Text("SA CHECK could not finish starting", size=21, weight=ft.FontWeight.W_900, color=TEXT),
                                ft.Text("The app stayed open so you can retry. Work folders and user data were not changed.", size=13, color=MUTED, text_align=ft.TextAlign.CENTER),
                                ft.Container(
                                    width=500,
                                    padding=12,
                                    border_radius=10,
                                    bgcolor="#FEF2F2",
                                    border=ft.Border.all(1, "#FECACA"),
                                    content=ft.Text(str(exc), size=11, color="#BE123C", selectable=True),
                                ),
                                ft.Button(
                                    "Retry startup",
                                    icon=ft.Icons.REFRESH,
                                    on_click=lambda _e: (
                                        page.controls.clear(),
                                        show_startup_loader(
                                            page,
                                            dashboard_main=dashboard_main,
                                            settings=settings,
                                            app_name=app_name,
                                            app_version=app_version,
                                            app_logo=app_logo,
                                            app_root=app_root,
                                            manifest_url=manifest_url,
                                        ),
                                    ),
                                    style=ft.ButtonStyle(
                                        bgcolor=ACCENT,
                                        color="#FFFFFF",
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                    ),
                                ),
                            ],
                        ),
                    ),
                )
            )
            _safe_update(page)

    page.run_thread(worker)
