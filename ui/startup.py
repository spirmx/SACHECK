from __future__ import annotations

import sys
import time
from pathlib import Path

import flet as ft

from core.startup_preflight import StartupResult, run_startup_preflight


BG = "#EAF4F7"
SURFACE = "#FFFFFF"
ACCENT = "#2563EB"
TEXT = "#12213A"
MUTED = "#5F718B"
BORDER = "#CFE0E8"
SUCCESS = "#16A36A"
WARNING = "#F59E0B"
ERROR = "#EF4B5A"
MINIMUM_LOADER_SECONDS = 1.4
STEP_COLORS = ("#2563EB", "#13A8A8", "#F59E0B", "#16A36A")
STEP_BACKGROUNDS = ("#EAF2FF", "#E8FBFB", "#FFF7E6", "#EAF9F1")


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
        page.window.maximized = False
        page.window.width = 800
        page.window.height = 600
        page.window.min_width = 800
        page.window.min_height = 600
        page.window.resizable = False
    except Exception:
        pass

    status_text = ft.Text("Starting SA CHECK services...", size=13, weight=ft.FontWeight.W_600, color=TEXT, expand=True)
    status_icon = ft.Icon(ft.Icons.ROCKET_LAUNCH_OUTLINED, size=19, color=ACCENT)
    status_panel = ft.Container(
        height=48,
        padding=ft.Padding.symmetric(horizontal=14),
        border_radius=10,
        bgcolor="#EFF6FF",
        border=ft.Border.all(1, "#BFDBFE"),
        content=ft.Row(spacing=10, controls=[status_icon, status_text]),
    )
    progress = ft.ProgressBar(value=0.04, height=7, color=ACCENT, bgcolor="#DCE7EF", border_radius=99)
    percent_text = ft.Text("4%", size=11, weight=ft.FontWeight.W_800, color=ACCENT)
    mode_chip = ft.Container(
        visible=False,
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        border_radius=99,
        bgcolor="#F1F5F9",
        border=ft.Border.all(1, BORDER),
        content=ft.Text("Online check", size=10, weight=ft.FontWeight.W_700, color=MUTED),
    )
    step_labels = [
        ft.Text("Environment", size=10, color=MUTED),
        ft.Text("Assets", size=10, color=MUTED),
        ft.Text("Connectivity", size=10, color=MUTED),
        ft.Text("Finalize", size=10, color=MUTED),
    ]
    step_dots = [ft.Container(width=9, height=9, border_radius=99, bgcolor="#B9C8D3") for _ in range(4)]
    step_cards = [
        ft.Container(
            width=114,
            height=48,
            padding=ft.Padding.symmetric(horizontal=10),
            border_radius=9,
            bgcolor=STEP_BACKGROUNDS[index],
            border=ft.Border.all(1, STEP_COLORS[index] if index == 0 else BORDER),
            content=ft.Row(spacing=7, controls=[step_dots[index], step_labels[index]]),
        )
        for index in range(4)
    ]

    step_row = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=8,
        controls=step_cards,
    )
    logo = ft.Container(
        width=76,
        height=76,
        border_radius=20,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        bgcolor="#F4F8FB",
        border=ft.Border.all(1, "#BFD4E2"),
        shadow=ft.BoxShadow(blur_radius=16, color="#260F4C81", offset=ft.Offset(0, 6)),
        content=ft.Image(
            src=app_logo,
            width=76,
            height=76,
            fit=ft.BoxFit.COVER,
            error_content=ft.Container(
                alignment=ft.Alignment(0, 0),
                content=ft.Text("SA", size=22, weight=ft.FontWeight.W_900, color=ACCENT),
            ),
        ),
    )
    card = ft.Container(
        width=570,
        height=420,
        border_radius=16,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        bgcolor=SURFACE,
        border=ft.Border.all(1, BORDER),
        shadow=ft.BoxShadow(blur_radius=28, color="#2A315D70", offset=ft.Offset(0, 12)),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
            controls=[
                ft.Row(
                    spacing=0,
                    controls=[ft.Container(expand=True, height=8, bgcolor=color) for color in STEP_COLORS],
                ),
                ft.Container(
                    expand=True,
                    padding=ft.Padding.only(left=34, right=34, top=24, bottom=20),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=11,
                        controls=[
                            logo,
                            ft.Text(app_name, size=24, weight=ft.FontWeight.W_900, color=TEXT),
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                                border_radius=99,
                                bgcolor="#EEF2FF",
                                content=ft.Text(f"VERSION {app_version}", size=10, weight=ft.FontWeight.W_800, color="#4F46E5"),
                            ),
                            status_panel,
                            ft.Row(spacing=10, controls=[ft.Container(expand=True, content=progress), percent_text]),
                            step_row,
                            mode_chip,
                            ft.Row(
                                spacing=6,
                                alignment=ft.MainAxisAlignment.CENTER,
                                controls=[
                                    ft.Icon(ft.Icons.LOCK_OUTLINE, size=13, color="#70859A"),
                                    ft.Text("Work folders, settings, and cache stay local.", size=10, color="#70859A"),
                                ],
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )
    page.add(ft.Container(expand=True, alignment=ft.Alignment(0, 0), bgcolor=BG, content=card))
    _safe_update(page)
    try:
        page.run_task(page.window.center)
    except Exception:
        pass

    step_indexes = {"boot": 0, "local": 1, "online": 2, "repair": 2, "offline": 2, "ready": 3}

    def set_status(step: str, message: str, value: float) -> None:
        status_text.value = message
        progress.value = value
        percent_text.value = f"{int(value * 100)}%"
        active = step_indexes.get(step, 0)
        for index, dot in enumerate(step_dots):
            dot.bgcolor = SUCCESS if index < active else STEP_COLORS[index] if index == active else "#B9C8D3"
            step_cards[index].border = ft.Border.all(1, STEP_COLORS[index] if index == active else BORDER)
        if step == "online":
            mode_chip.visible = True
            mode_chip.bgcolor = "#FFF7E6"
            mode_chip.border = ft.Border.all(1, "#FCD38A")
            mode_chip.content.value = "Checking online services"
            mode_chip.content.color = "#A65D03"
        elif step == "offline":
            mode_chip.visible = True
            mode_chip.bgcolor = "#F1F5F9"
            mode_chip.border = ft.Border.all(1, BORDER)
            mode_chip.content.value = "Offline mode"
            mode_chip.content.color = MUTED
        elif step == "repair":
            progress.color = ERROR
            status_panel.bgcolor = "#FFF1F2"
            status_panel.border = ft.Border.all(1, "#FECDD3")
            status_icon.color = ERROR
            mode_chip.visible = True
            mode_chip.bgcolor = "#FFF1F2"
            mode_chip.border = ft.Border.all(1, "#FECDD3")
            mode_chip.content.value = "Verified repair"
            mode_chip.content.color = "#BE123C"
        elif step == "ready":
            progress.color = SUCCESS
            status_panel.bgcolor = "#EAF9F1"
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
                        border_radius=14,
                        bgcolor=SURFACE,
                        border=ft.Border.all(1, ERROR),
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
                                    border_radius=9,
                                    bgcolor="#FFF1F2",
                                    border=ft.Border.all(1, "#FECDD3"),
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
                                        shape=ft.RoundedRectangleBorder(radius=9),
                                    ),
                                ),
                            ],
                        ),
                    ),
                )
            )
            _safe_update(page)

    page.run_thread(worker)
