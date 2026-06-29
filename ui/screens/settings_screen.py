import os
import shutil
import flet as ft
from pathlib import Path

from core.flet_constants import (
    BORDER, DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES, MUTED, MUTED_2,
    PRIMARY, TEXT, WHITE, BG, STATUS_PENDING, STATUS_PROGRESS, STATUS_DONE,
    APP_VERSION
)
from core.flet_data import (
    DATA_FILE, APP_NAME, FILE_TYPES, type_color_choices, load_tasks,
    ensure_status_folders, save_settings
)
from core.flet_theme import apply_app_theme
from core.flet_utils import t
from core.app_paths import is_dev_runtime
from ui.dialogs import show_message
from ui.flet_widgets import CENTER, border_all, dropdown, pad_only, pad_sym, type_style, app_logo_control, profile_media_control, app_theme_preview, app_theme_mockup, color_swatch, nav_button
from ui.shared import DashboardContext

def render_settings(ctx: DashboardContext) -> None:
    ctx.header_title.value = "Settings"
    ctx.header_subtitle.value = f"{APP_NAME} / Configuration"

    # We mock or lazily import functions that the original render_settings needs
    try:
        from core.flet_data import load_templates, list_snapshots, check_for_updates, status_theme
    except ImportError:
        load_templates, list_snapshots, check_for_updates = lambda: [], lambda x: [], lambda manual: None
        status_theme = lambda status: ("#FFFFFF", "#000000")

    # Local state access
    root_work_str = ctx.settings.get("root_work") or ctx.settings.get("work_folder_path") or ""
    root_work = Path(root_work_str) if root_work_str else Path(ctx.root_work)
    custom_types = ctx.settings.get("custom_types", [])

    # The original file has many fields, we need to create them here or use existing
    theme_switch = ft.Switch(value=ctx.settings.get("theme") == "Dark", label="Dark theme mode")
    realtime_switch = ft.Switch(value=ctx.settings.get("realtime_sync_enabled", True), label="Real-time background sync (watch Work folder)")
    move_files_switch = ft.Switch(value=ctx.settings.get("move_files_on_status", True), label="Move actual files when changing status (Waiting / Doing / Success)")
    confirm_switch = ft.Switch(value=ctx.settings.get("confirm_risky_actions", True), label="Confirm risky actions (Delete, Clean system)")
    smart_search_switch = ft.Switch(value=ctx.settings.get("smart_search_enabled", True), label="Smart search (tags, fuzzy match, NLP hints)")
    smart_health_switch = ft.Switch(value=ctx.settings.get("smart_health_enabled", True), label="Smart health (auto-detect broken links & wrong folders)")
    workload_switch = ft.Switch(value=ctx.settings.get("workload_hints_enabled", True), label="Workload hints (warn on stale doing, zombie waiting, overbooked days)")
    template_rank_switch = ft.Switch(value=ctx.settings.get("template_ranking_enabled", True), label="Smart templates (rank by usage & recency)")
    update_checks_switch = ft.Switch(value=ctx.settings.get("update_checks_enabled", True), label="Check for app updates on startup")
    offline_mode_switch = ft.Switch(value=ctx.settings.get("offline_mode", False), label="Offline Mode (disables update checks and telemetry, hides Online status)")
    if is_dev_runtime():
        update_checks_switch.value = False
        update_checks_switch.disabled = True
        offline_mode_switch.value = True
        offline_mode_switch.disabled = True

    interval_select = dropdown(100, str(ctx.settings.get("sync_interval_seconds", 5)), ["1", "3", "5", "10", "30", "60"])
    snapshot_select = dropdown(100, str(ctx.settings.get("snapshot_retention", 25)), ["5", "10", "25", "50", "100"])
    update_interval_select = dropdown(100, str(ctx.settings.get("update_check_interval_minutes", DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES)), ["15", "30", "60", "120", "240", "1440"])

    stale_select = dropdown(100, str(ctx.settings.get("stale_doing_days", 7)), ["3", "5", "7", "14", "30"])
    zombie_select = dropdown(100, str(ctx.settings.get("zombie_waiting_days", 30)), ["7", "14", "30", "60", "90"])
    overload_doing_select = dropdown(100, str(ctx.settings.get("overload_doing_limit", 4)), ["2", "4", "6", "8", "10"])
    overload_total_select = dropdown(100, str(ctx.settings.get("overload_total_limit", 10)), ["5", "10", "15", "20", "30"])

    app_themes = ["Ocean Pro", "Midnight Purple", "Forest Green", "Sunset Orange", "Rose Gold", "Slate Gray", "High Contrast"]
    app_theme_select = dropdown(200, ctx.settings.get("app_theme_preset", "Ocean Pro"), app_themes)
    status_themes = ["Classic Blue", "Modern Pastel", "Vibrant Tech", "Monochrome"]
    status_theme_select = dropdown(200, ctx.settings.get("status_theme_preset", "Classic Blue"), status_themes)
    language_select = dropdown(160, ctx.settings.get("language", "en"), ["en", "th"])

    def on_settings_search(e):
        ctx.state["settings_search"] = e.control.value or ""
        ctx.render_current()

    settings_search = ft.TextField(
        hint_text="Search settings... (e.g. 'sync', 'theme', 'update')",
        prefix_icon=ft.Icons.SEARCH,
        value=ctx.state.get("settings_search", ""),
        height=46,
        expand=True,
        border_radius=14,
        border_color=BORDER,
        bgcolor=WHITE,
        on_change=on_settings_search,
        content_padding=pad_sym(horizontal=12),
    )

    type_name = ft.TextField(label="Type name", hint_text="e.g. Design", expand=True, border_radius=12, border_color=BORDER)
    type_ext = ft.TextField(label="Extensions (comma separated)", hint_text="e.g. .psd, .ai, .fig", expand=True, border_radius=12, border_color=BORDER)
    type_icon = ft.TextField(label="Icon text (1-3 chars)", hint_text="DES", width=120, border_radius=12, border_color=BORDER)
    type_color = ft.TextField(label="Color hex", hint_text="#2563EB", value="#2563EB", width=130, border_radius=12, border_color=BORDER)
    type_action = dropdown(180, "Open", ["Open", "Execute", "Browse", "Open Browser"])
    color_preview = ft.Container(width=40, height=40, border_radius=12, bgcolor="#2563EB")
    icon_file = {"value": ""}

    def update_color_preview(_event):
        val = type_color.value.strip()
        if val.startswith("#") and (len(val) == 4 or len(val) == 7):
            color_preview.bgcolor = val
            ctx.page.update()

    type_color.on_change = update_color_preview

    def pick_type_color(color):
        type_color.value = color
        color_preview.bgcolor = color
        ctx.page.update()

    def show_about(_event):
        show_message(ctx.page, "About", f"{APP_NAME}\nVersion {APP_VERSION}\nA modern desktop task board.")

    def show_help(_event):
        show_message(ctx.page, "Help", "User guide is available in the documentation.")

    def show_version_notes(_event):
        show_message(ctx.page, "Version notes", "v1.0.8: Improved UI performance with modular screen loading.")

    async def choose_work_folder(_e):
        try:
            selected = await ctx.pick_directory("Choose SA CHECK Work folder")
            if not selected:
                return
            selected_path = Path(selected)
            selected_path.mkdir(parents=True, exist_ok=True)
            ctx.settings["work_folder_path"] = str(selected_path)
            ctx.settings.pop("root_work", None)
            save_settings(ctx.settings)
            show_message(ctx.page, "Work folder", f"DEV Work folder changed to:\n{selected_path}")
            ctx.render_current()
        except Exception as e:
            show_message(ctx.page, "Error", str(e))

    async def choose_profile_media(_e):
        try:
            picked = await ctx.file_picker.pick_files(
                dialog_title="Choose sidebar profile media",
                allow_multiple=False,
                allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp", "gif"],
            )
            if not picked or not picked.files:
                return
            source = Path(picked.files[0].path)
            profile_dir = DATA_FILE.parent / "profile_media"
            profile_dir.mkdir(parents=True, exist_ok=True)
            target = profile_dir / f"profile{source.suffix.lower()}"
            shutil.copy2(source, target)
            ctx.settings["profile_media_path"] = str(target)
            save_settings(ctx.settings)
            show_message(ctx.page, "Profile media", "DEV profile media updated.")
            ctx.render_current()
        except Exception as e:
            show_message(ctx.page, "Profile media failed", str(e))

    async def choose_icon(_e):
        try:
            picked = await ctx.file_picker.pick_files(
                dialog_title="Choose custom type icon",
                allow_multiple=False,
                allowed_extensions=["png", "jpg", "jpeg", "webp", "bmp", "gif", "ico"],
            )
            if not picked or not picked.files:
                return
            source = Path(picked.files[0].path)
            icon_dir = DATA_FILE.parent / "custom_type_icons"
            icon_dir.mkdir(parents=True, exist_ok=True)
            target = icon_dir / f"{source.stem}_{len(list(icon_dir.glob('*')))}{source.suffix.lower()}"
            shutil.copy2(source, target)
            icon_file["value"] = str(target)
            show_message(ctx.page, "Icon image", "Icon image selected for this type.")
        except Exception as e:
            show_message(ctx.page, "Icon image failed", str(e))

    def save_theme(_event):
        ctx.settings["theme"] = "Dark" if theme_switch.value else "Light"
        ctx.settings["language"] = language_select.value or "en"
        ctx.settings["app_theme_preset"] = app_theme_select.value or "Ocean Pro"
        ctx.settings["status_theme_preset"] = status_theme_select.value or "Classic Blue"
        save_settings(ctx.settings)
        apply_app_theme(ctx.settings)
        ctx.page.bgcolor = BG
        ctx.page.theme_mode = ft.ThemeMode.DARK if theme_switch.value else ft.ThemeMode.LIGHT
        ctx.render_current()
        show_message(ctx.page, "Settings", "Theme saved.")

    def save_all_settings(_event):
        ctx.settings["theme"] = "Dark" if theme_switch.value else "Light"
        ctx.settings["language"] = language_select.value or "en"
        ctx.settings["app_theme_preset"] = app_theme_select.value or "Ocean Pro"
        ctx.settings["status_theme_preset"] = status_theme_select.value or "Classic Blue"
        ctx.settings["realtime_sync_enabled"] = bool(realtime_switch.value)
        ctx.settings["move_files_on_status"] = bool(move_files_switch.value)
        ctx.settings["confirm_risky_actions"] = bool(confirm_switch.value)
        ctx.settings["smart_search_enabled"] = bool(smart_search_switch.value)
        ctx.settings["smart_health_enabled"] = bool(smart_health_switch.value)
        ctx.settings["workload_hints_enabled"] = bool(workload_switch.value)
        ctx.settings["template_ranking_enabled"] = bool(template_rank_switch.value)
        ctx.settings["update_checks_enabled"] = False if is_dev_runtime() else bool(update_checks_switch.value)
        ctx.settings["offline_mode"] = True if is_dev_runtime() else bool(offline_mode_switch.value)
        ctx.settings["update_check_interval_minutes"] = int(update_interval_select.value or DEFAULT_UPDATE_CHECK_INTERVAL_MINUTES)
        ctx.settings["sync_interval_seconds"] = int(interval_select.value or 5)
        ctx.settings["snapshot_retention"] = int(snapshot_select.value or 25)
        ctx.settings["stale_doing_days"] = int(stale_select.value or 7)
        ctx.settings["zombie_waiting_days"] = int(zombie_select.value or 30)
        ctx.settings["overload_doing_limit"] = int(overload_doing_select.value or 4)
        ctx.settings["overload_total_limit"] = int(overload_total_select.value or 10)
        save_settings(ctx.settings)
        apply_app_theme(ctx.settings)
        ctx.page.bgcolor = BG
        ctx.page.theme_mode = ft.ThemeMode.DARK if theme_switch.value else ft.ThemeMode.LIGHT
        ctx.page.update()
        show_message(ctx.page, "Settings", "Settings saved.")

    def reset_smart_defaults(_event):
        ctx.settings.update({
            "smart_search_enabled": True,
            "smart_health_enabled": True,
            "workload_hints_enabled": True,
            "template_ranking_enabled": True,
            "stale_doing_days": 7,
            "zombie_waiting_days": 30,
            "overload_doing_limit": 4,
            "overload_total_limit": 10,
        })
        save_settings(ctx.settings)
        show_message(ctx.page, "Settings", "Smart defaults restored.")
        ctx.render_current()

    def reset_sync_defaults(_event):
        ctx.settings.update({
            "realtime_sync_enabled": True,
            "sync_interval_seconds": 5,
            "snapshot_retention": 25,
            "move_files_on_status": True,
            "confirm_risky_actions": True,
        })
        save_settings(ctx.settings)
        show_message(ctx.page, "Settings", "Sync and safety defaults restored.")
        ctx.render_current()

    def reset_ui_defaults(_event):
        ctx.settings["theme"] = "Light"
        ctx.settings["language"] = "en"
        ctx.settings["app_theme_preset"] = "Ocean Pro"
        ctx.settings["status_theme_preset"] = "Classic Blue"
        save_settings(ctx.settings)
        apply_app_theme(ctx.settings)
        ctx.page.bgcolor = BG
        ctx.page.theme_mode = ft.ThemeMode.LIGHT
        show_message(ctx.page, "Settings", "UI defaults restored.")
        ctx.render_current()

    def parse_extensions(value):
        parts = [part.strip().lower() for part in value.replace(";", ",").split(",")]
        normalized = []
        for part in parts:
            if not part: continue
            normalized.append(part if part.startswith(".") else f".{part}")
        return normalized

    def add_file_type(_event):
        name = (type_name.value or "").strip()
        if not name:
            show_message(ctx.page, "Missing type name", "Please enter a file type name.")
            return
        if name.casefold() in [item.casefold() for item in FILE_TYPES] or any(str(item.get("name", "")).casefold() == name.casefold() for item in custom_types):
            show_message(ctx.page, "Already exists", "This file type already exists.")
            return
        extensions = parse_extensions(type_ext.value or "")
        existing_extensions = {
            extension
            for item in custom_types
            for extension in parse_extensions(",".join(item.get("extensions", [])) if isinstance(item.get("extensions", []), list) else str(item.get("extensions", "")))
        }
        duplicate_extensions = [extension for extension in extensions if extension in existing_extensions]
        if duplicate_extensions:
            show_message(ctx.page, "Extension already mapped", f"{', '.join(duplicate_extensions[:3])} already belongs to another type.")
            return
        custom_types.append({
            "name": name,
            "icon": (type_icon.value or name[:3]).strip().upper(),
            "color": (type_color.value or "#2563EB").strip(),
            "icon_file": icon_file["value"],
            "extensions": extensions,
            "default_action": type_action.value or "Open",
        })
        save_settings(ctx.settings)
        ensure_status_folders()
        try: ctx.page.pop_dialog()
        except Exception: pass
        ctx.render_current()
        show_message(ctx.page, "File type added", f"{name} is ready.")

    def show_add_file_type_dialog(_event=None):
        type_name.value = ""
        type_icon.value = ""
        type_color.value = "#2563EB"
        color_preview.bgcolor = "#2563EB"
        type_ext.value = ""
        type_action.value = "Open"
        icon_file["value"] = ""
        ctx.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Row(
                    spacing=10,
                    controls=[
                        ft.Icon(ft.Icons.CATEGORY_OUTLINED, color=PRIMARY),
                        ft.Text("Add custom work type", size=20, weight=ft.FontWeight.W_900, color=TEXT),
                    ],
                ),
                content=ft.Column(
                    width=660,
                    height=370,
                    spacing=12,
                    controls=[
                        ft.Text(f"Create a new category for files, links, templates, and Work folders. {APP_NAME} will use the extensions to classify matching files.", size=13, color=MUTED),
                        ft.Row(spacing=10, controls=[type_name, type_icon, type_action]),
                        ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[color_preview, type_color, ft.Button("Icon image", icon=ft.Icons.IMAGE_OUTLINED, on_click=choose_icon, width=130)]),
                        ft.Container(
                            padding=pad_sym(horizontal=12, vertical=10),
                            border_radius=14,
                            bgcolor="#F8FAFC",
                            border=border_all(1, BORDER),
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Text("Quick colors", size=12, weight=ft.FontWeight.W_900, color=MUTED),
                                    ft.Row(spacing=8, wrap=True, controls=[ft.Container(
                                        width=30, height=30, border_radius=999, bgcolor=color, border=border_all(2, "#0F172A" if color == type_color.value else "#FFFFFF"), on_click=lambda _e, value=color: pick_type_color(value)
                                    ) for color in type_color_choices]),
                                ],
                            ),
                        ),
                        type_ext,
                    ],
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda _e: (ctx.page.pop_dialog(), ctx.page.update())),
                    ft.Button("Save type", icon=ft.Icons.SAVE_OUTLINED, on_click=add_file_type, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                ],
                bgcolor=WHITE,
                shape=ft.RoundedRectangleBorder(radius=18),
            )
        )
        ctx.page.update()

    def remove_file_type(item):
        if item in custom_types:
            custom_types.remove(item)
            save_settings(ctx.settings)
            ctx.render_current()

    def type_row(name, icon_text, extensions, custom_item=None):
        is_custom = custom_item is not None
        color = custom_item.get("color", PRIMARY) if custom_item else type_style(name)[2]
        default_action = custom_item.get("default_action", "") if custom_item else ""
        detail_text = ", ".join(extensions) if extensions else ("Your extension rules" if is_custom else "System file/link rules")
        action_text = f"{default_action} by default" if default_action else "Smart classify"
        source_text = "My type" if is_custom else "System type"
        return ft.Container(
            height=66,
            bgcolor=WHITE,
            border=border_all(1, BORDER),
            border_radius=14,
            padding=pad_only(left=12, right=8),
            content=ft.Row(
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(width=38, height=38, border_radius=11, bgcolor="#F1F5F9", alignment=CENTER, content=ft.Text(icon_text or name[:2].upper(), size=12, weight=ft.FontWeight.W_800, color=color)),
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text(name, size=15, weight=ft.FontWeight.W_800, color=TEXT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(detail_text, size=12, color=MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                    ft.Container(padding=pad_sym(horizontal=9, vertical=4), border_radius=999, bgcolor="#F8FAFC", content=ft.Text(action_text, size=11, weight=ft.FontWeight.W_800, color=MUTED)),
                    ft.Container(padding=pad_sym(horizontal=9, vertical=4), border_radius=999, bgcolor="#EFF6FF" if is_custom else "#F8FAFC", content=ft.Text(source_text, size=11, weight=ft.FontWeight.W_800, color=PRIMARY if is_custom else MUTED)),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color="#DC2626", disabled=not is_custom, tooltip="Delete custom type", on_click=lambda _e, item=custom_item: remove_file_type(item)),
                ],
            ),
        )

    settings_query = ctx.state.get("settings_search", "").strip().casefold()
    def settings_visible(*terms):
        return not settings_query or any(settings_query in str(term).casefold() for term in terms)

    builtin_rows = [type_row(name, name[:3].upper(), [], None) for name in FILE_TYPES if settings_visible(name, "built-in file type")]
    custom_rows = [
        type_row(item.get("name", "Custom"), item.get("icon", ""), item.get("extensions", []), item)
        for item in custom_types
        if settings_visible(item.get("name", "Custom"), item.get("extensions", []), "custom file type")
    ]
    status_rows = [
        ("Tasks", str(len(ctx.all_tasks)), PRIMARY, "#EFF6FF"),
        ("Templates", str(len(load_templates())), "#7C3AED", "#F5F3FF"),
        ("Snapshots", str(len(list_snapshots(100))), "#059669", "#ECFDF5"),
        ("Last sync", str(ctx.settings.get("last_sync_at") or "Never"), "#D97706", "#FFFBEB"),
    ]

    def settings_stat(label, value, color, bg):
        return ft.Container(
            expand=True,
            height=56,
            bgcolor=bg,
            border=border_all(1, color + "44"),
            border_radius=12,
            padding=pad_sym(horizontal=12, vertical=8),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(label, size=11, weight=ft.FontWeight.W_900, color=MUTED),
                    ft.Text(value, size=14, weight=ft.FontWeight.W_900, color=color, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ],
            ),
        )

    system_card = ft.Container(
        expand=True,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=14,
        padding=16,
        content=ft.ListView(
            expand=True,
            spacing=12,
            controls=[
                ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=MUTED), ft.Text("System", size=18, weight=ft.FontWeight.W_800, color=TEXT)]),
                settings_search,
                ft.Container(
                    border=border_all(1, "#E0E7FF"),
                    border_radius=12,
                    padding=14,
                    bgcolor="#F8FBFF",
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.INFO_OUTLINED, color=PRIMARY), ft.Text("Credits", size=14, weight=ft.FontWeight.W_800, color=TEXT)]),
                            ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[app_logo_control(48, 14), ft.Column(spacing=3, controls=[ft.Text(APP_NAME, size=17, weight=ft.FontWeight.W_900, color=TEXT), ft.Text("Desktop Work Board", size=12, color=MUTED)])]),
                            ft.Text("Developer / Creator: HOYTURBRO", size=13, weight=ft.FontWeight.W_800, color=TEXT, selectable=True),
                            ft.Text("Publisher: HOYTURBRO", size=12, color=MUTED, selectable=True),
                            ft.Text("Alias: Hoyturbro | Product: SA CHECK Desktop Work Board | Copyright (c) 2026 HOYTURBRO", size=12, color=MUTED, selectable=True),
                            ft.Row(spacing=10, controls=[ft.Button("About SA CHECK", icon=ft.Icons.INFO_OUTLINED, on_click=show_about), ft.Button("User guide", icon=ft.Icons.HELP_OUTLINE, on_click=show_help)]),
                        ],
                    ),
                ),
                ft.Container(
                    border=border_all(1, "#DBEAFE"),
                    border_radius=12,
                    padding=14,
                    bgcolor="#F8FBFF",
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.FOLDER_SPECIAL_OUTLINED, color=PRIMARY), ft.Text("Work Folder Source", size=14, weight=ft.FontWeight.W_800, color=TEXT)]),
                            ft.Text(str(root_work), size=12, color=MUTED, selectable=True, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Button("Choose Work folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=choose_work_folder),
                                    ft.Button("Open Work folder", icon=ft.Icons.OPEN_IN_NEW, on_click=lambda _e: os.startfile(str(root_work)) if root_work.exists() else show_message(ctx.page, "Folder not found", "Choose or create a Work folder first.")),
                                ],
                            ),
                            ft.Text(f"Data file: {DATA_FILE}", size=11, color=MUTED, selectable=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                    ),
                ),
                ft.Row(spacing=10, controls=[settings_stat(*row) for row in status_rows]),
                ft.Container(
                    border=border_all(1, "#E2E8F0"),
                    border_radius=12,
                    padding=14,
                    bgcolor="#FFFFFF",
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.PALETTE_OUTLINED, color=PRIMARY), ft.Text("Appearance", size=14, weight=ft.FontWeight.W_800, color=TEXT)]),
                            ft.Container(
                                border=border_all(1, "#DBEAFE"),
                                border_radius=14,
                                bgcolor="#F8FBFF",
                                padding=12,
                                content=ft.Row(
                                    spacing=12,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Container(width=40, height=40, border_radius=12, bgcolor="#EFF6FF", alignment=CENTER, content=ft.Icon(ft.Icons.TRANSLATE, color=PRIMARY, size=21)),
                                        ft.Column(spacing=3, expand=True, controls=[ft.Text(t("language"), size=13, weight=ft.FontWeight.W_900, color=TEXT), ft.Text(t("language_hint"), size=11, color=MUTED)]),
                                        language_select,
                                    ],
                                ),
                            ),
                            theme_switch,
                            ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[profile_media_control(52), ft.Column(spacing=4, expand=True, controls=[ft.Text("Sidebar profile media", size=13, weight=ft.FontWeight.W_900, color=TEXT), ft.Text("Use PNG, JPG, WEBP, BMP, or animated GIF. Video support needs a video runtime in a later build.", size=11, color=MUTED)]), ft.Button("Upload media", icon=ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, on_click=choose_profile_media)]),
                            ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("App theme", size=13, weight=ft.FontWeight.W_800, color=MUTED), app_theme_select, app_theme_preview()]),
                            app_theme_mockup(),
                            ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("Status theme", size=13, weight=ft.FontWeight.W_800, color=MUTED), status_theme_select]),
                            ft.Row(
                                spacing=10,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Button("Apply theme", icon=ft.Icons.CHECK_CIRCLE_OUTLINE, on_click=save_theme, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                                    ft.Text(t("theme_apply_hint"), size=11, color=MUTED),
                                ],
                            ),
                            ft.Row(
                                spacing=8,
                                controls=[
                                    ft.Container(width=74, height=28, border_radius=999, bgcolor=status_theme(STATUS_PENDING)[0], border=border_all(1, status_theme(STATUS_PENDING)[1]), alignment=CENTER, content=ft.Text("Waiting", size=11, weight=ft.FontWeight.W_800, color=status_theme(STATUS_PENDING)[1])),
                                    ft.Container(width=74, height=28, border_radius=999, bgcolor=status_theme(STATUS_PROGRESS)[0], border=border_all(1, status_theme(STATUS_PROGRESS)[1]), alignment=CENTER, content=ft.Text("Doing", size=11, weight=ft.FontWeight.W_800, color=status_theme(STATUS_PROGRESS)[1])),
                                    ft.Container(width=74, height=28, border_radius=999, bgcolor=status_theme(STATUS_DONE)[0], border=border_all(1, status_theme(STATUS_DONE)[1]), alignment=CENTER, content=ft.Text("Success", size=11, weight=ft.FontWeight.W_800, color=status_theme(STATUS_DONE)[1])),
                                ],
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    border=border_all(1, "#DBEAFE"),
                    border_radius=12,
                    padding=14,
                    bgcolor="#F8FBFF",
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.SYSTEM_UPDATE_ALT_OUTLINED, color=PRIMARY), ft.Text("System Updates", size=14, weight=ft.FontWeight.W_800, color=TEXT)]),
                            ft.Text(("DEV mode: update checks are disabled and never touch the production installer." if is_dev_runtime() else f"Current version: {APP_VERSION}. Update checks only use internet for app updates; normal work stays offline-first."), size=12, color=MUTED),
                            update_checks_switch,
                            offline_mode_switch,
                            ft.Row(
                                spacing=12,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Column(
                                        spacing=2,
                                        expand=True,
                                        controls=[
                                            ft.Text("Auto-check interval", size=13, weight=ft.FontWeight.W_800, color=TEXT),
                                            ft.Text("How often SA CHECK checks GitHub while Online mode is enabled.", size=11, color=MUTED),
                                        ],
                                    ),
                                    ft.Row(spacing=8, controls=[update_interval_select, ft.Text("minutes", size=12, color=MUTED)]),
                                ],
                            ),
                            ft.Row(spacing=10, controls=[
                                ft.Button("Check now", icon=ft.Icons.REFRESH, disabled=is_dev_runtime(), on_click=lambda _e: check_for_updates(manual=True)),
                                ft.Button("Version notes", icon=ft.Icons.FACT_CHECK_OUTLINED, on_click=show_version_notes),
                            ]),
                        ],
                    ),
                ),
                ft.Container(
                    border=border_all(1, BORDER),
                    border_radius=12,
                    padding=14,
                    bgcolor="#F8FAFC",
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.SHIELD_OUTLINED, color=MUTED), ft.Text("Sync & Safety Policy", size=14, weight=ft.FontWeight.W_800, color=TEXT)]),
                            realtime_switch,
                            ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("Sync interval", size=13, color=MUTED), interval_select, ft.Text("seconds", size=13, color=MUTED)]),
                            ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("Snapshots kept", size=13, color=MUTED), snapshot_select]),
                            move_files_switch,
                            confirm_switch,
                        ],
                    ),
                ),
                ft.Container(
                    border=border_all(1, "#DBEAFE"),
                    border_radius=12,
                    padding=14,
                    bgcolor="#F8FBFF",
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.TIPS_AND_UPDATES_OUTLINED, color=PRIMARY), ft.Text("Smart Features", size=14, weight=ft.FontWeight.W_800, color=TEXT)]),
                            smart_search_switch,
                            smart_health_switch,
                            workload_switch,
                            template_rank_switch,
                            ft.Container(
                                border=border_all(1, "#E2E8F0"),
                                border_radius=14,
                                padding=12,
                                bgcolor=WHITE,
                                content=ft.Column(
                                    spacing=10,
                                    controls=[
                                        ft.Text("Smart thresholds", size=13, weight=ft.FontWeight.W_900, color=TEXT),
                                        ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("Stale Doing", size=12, color=MUTED), stale_select, ft.Text("days", size=12, color=MUTED), ft.Text("Zombie Waiting", size=12, color=MUTED), zombie_select, ft.Text("days", size=12, color=MUTED)]),
                                        ft.Row(spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[ft.Text("Overload Doing", size=12, color=MUTED), overload_doing_select, ft.Text("tasks/day", size=12, color=MUTED), ft.Text("Overload Total", size=12, color=MUTED), overload_total_select, ft.Text("tasks/day", size=12, color=MUTED)]),
                                    ],
                                ),
                            ),
                            ft.Text(f"These features only analyze {APP_NAME} records and folder metadata. They do not rename, move, or delete Work files.", size=12, color=MUTED),
                        ],
                    ),
                ),
                ft.Container(
                    border=border_all(1, "#E2E8F0"),
                    border_radius=12,
                    padding=14,
                    bgcolor="#FFFFFF",
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.RESTART_ALT, color=MUTED), ft.Text("Reset Defaults", size=14, weight=ft.FontWeight.W_800, color=TEXT)]),
                            ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Button("Reset smart", icon=ft.Icons.TIPS_AND_UPDATES_OUTLINED, on_click=reset_smart_defaults),
                                    ft.Button("Reset sync", icon=ft.Icons.SYNC, on_click=reset_sync_defaults),
                                    ft.Button("Reset UI", icon=ft.Icons.PALETTE_OUTLINED, on_click=reset_ui_defaults),
                                ],
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    border=border_all(1, BORDER),
                    border_radius=12,
                    padding=14,
                    bgcolor="#F8FAFC",
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(spacing=8, controls=[ft.Icon(ft.Icons.BOLT_OUTLINED, color=MUTED), ft.Text("Quick actions", size=14, weight=ft.FontWeight.W_800, color=TEXT)]),
                            ft.Row(spacing=10, run_spacing=10, wrap=True, controls=[
                                ft.Button("Save settings", icon=ft.Icons.SAVE_OUTLINED, on_click=save_all_settings, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=10))),
                                ft.Button("Work browser", icon=ft.Icons.FOLDER_OUTLINED, on_click=lambda _e: (ctx.state.update({"screen": "browser"}), ctx.render_current())),
                                ft.Button("Sync now", icon=ft.Icons.SYNC, on_click=ctx.sync_now),
                                ft.Button("Reload data", icon=ft.Icons.REFRESH, on_click=lambda _e: (ctx.all_tasks.clear(), ctx.all_tasks.extend(load_tasks()), ctx.render_current())),
                                ft.Button("Create folders", icon=ft.Icons.CREATE_NEW_FOLDER_OUTLINED, on_click=lambda _e: (ensure_status_folders(), show_message(ctx.page, "Folders ready", "Work folders are ready."))),
                                ft.Button("Open data folder", icon=ft.Icons.FOLDER_OPEN_OUTLINED, on_click=lambda _e: os.startfile(str(DATA_FILE.parent))),
                            ]),
                        ],
                    ),
                ),
            ],
        ),
    )

    type_card = ft.Container(
        expand=True,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=14,
        padding=16,
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(spacing=10, controls=[ft.Icon(ft.Icons.CATEGORY_OUTLINED, color=MUTED), ft.Text("Type Library", size=18, weight=ft.FontWeight.W_800, color=TEXT)]),
                        ft.Button("+ Add custom type", icon=ft.Icons.ADD, on_click=show_add_file_type_dialog, style=ft.ButtonStyle(bgcolor=TEXT, color=WHITE, shape=ft.RoundedRectangleBorder(radius=12))),
                    ],
                ),
                ft.Container(
                    padding=pad_sym(horizontal=14, vertical=12),
                    border_radius=12,
                    bgcolor="#F8FAFC",
                    border=border_all(1, BORDER),
                    content=ft.Row(
                        spacing=10,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.AUTO_AWESOME_OUTLINED, size=18, color=PRIMARY),
                            ft.Text("System types are ready-made categories. My types are your own rules using extensions, color, and default action.", size=12, color=MUTED, expand=True),
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    content=ft.ListView(
                        spacing=10,
                        expand=True,
                        controls=[*custom_rows, *builtin_rows]
                        if [*custom_rows, *builtin_rows]
                        else [ft.Container(height=120, alignment=CENTER, content=ft.Text("No file types match this search.", size=13, color=MUTED_2))],
                    ),
                ),
            ],
        ),
    )

    active_settings_tab = ctx.state.get("settings_tab", "system")

    def settings_tab_button(label, icon, tab_key):
        selected = active_settings_tab == tab_key
        return ft.Container(
            height=42,
            padding=pad_sym(horizontal=14),
            border_radius=12,
            bgcolor=TEXT if selected else WHITE,
            border=border_all(1, TEXT if selected else BORDER),
            on_click=lambda _e, key=tab_key: (ctx.state.update({"settings_tab": key}), ctx.render_current()),
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=18, color=WHITE if selected else MUTED),
                    ft.Text(label, size=13, weight=ft.FontWeight.W_800, color=WHITE if selected else TEXT),
                ],
            ),
        )

    ctx.main_body.controls = [
        ft.Column(
            spacing=12,
            expand=True,
            controls=[
                ft.Row(
                    spacing=10,
                    controls=[
                        settings_tab_button("System & Theme", ft.Icons.TUNE_OUTLINED, "system"),
                        settings_tab_button("File Types", ft.Icons.CATEGORY_OUTLINED, "types"),
                    ],
                ),
                ft.Container(expand=True, content=system_card if active_settings_tab == "system" else type_card),
            ],
        )
    ]
    ctx.page.update()
