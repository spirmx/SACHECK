import flet as ft

from core.flet_constants import ACCENT, ACCENT_BG, ACCENT_BORDER, BORDER, DOING_TEXT, DONE_TEXT, MUTED, MUTED_2, PRIMARY, TEXT, WHITE
from core.flet_data import file_type_config


def pad_sym(horizontal=0, vertical=0):
    return ft.Padding(horizontal, vertical, horizontal, vertical)


def pad_only(left=0, top=0, right=0, bottom=0):
    return ft.Padding(left, top, right, bottom)


def border_all(width=1, color=BORDER):
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)


CENTER = ft.Alignment(0, 0)


def task_icon(task_type):
    mapping = {
        "Word": (ft.Icons.DESCRIPTION_OUTLINED, "#2F80ED"),
        "Excel": (ft.Icons.TABLE_CHART_OUTLINED, "#21A366"),
        "Google Sheet": (ft.Icons.GRID_ON_OUTLINED, "#22A56A"),
        "Miro": (ft.Icons.DASHBOARD_OUTLINED, "#111827"),
        "Canva": (ft.Icons.BRUSH_OUTLINED, "#DB2777"),
        "Figma": (ft.Icons.DESIGN_SERVICES_OUTLINED, "#A855F7"),
        "PDF": (ft.Icons.PICTURE_AS_PDF_OUTLINED, "#DC2626"),
        "Slide": (ft.Icons.SLIDESHOW_OUTLINED, "#EA580C"),
        "Diagram": (ft.Icons.ACCOUNT_TREE_OUTLINED, "#0891B2"),
        "Web": (ft.Icons.PUBLIC, "#0EA5E9"),
        "Project": (ft.Icons.FOLDER_OUTLINED, "#8B5CF6"),
        "Library": (ft.Icons.LOCAL_LIBRARY_OUTLINED, "#7C3AED"),
        "Image": (ft.Icons.IMAGE_OUTLINED, "#EC4899"),
        "Video": (ft.Icons.VIDEO_FILE_OUTLINED, "#EF4444"),
        "Audio": (ft.Icons.AUDIO_FILE_OUTLINED, "#14B8A6"),
        "Archive": (ft.Icons.FOLDER_ZIP_OUTLINED, "#A16207"),
        "Code": (ft.Icons.CODE, "#334155"),
        "Data": (ft.Icons.DATA_OBJECT, "#0F766E"),
        "Link": (ft.Icons.LINK_ROUNDED, "#14B8A6"),
    }
    if task_type in mapping:
        return mapping[task_type]
    config = file_type_config(task_type)
    if config:
        return ft.Icons.INSERT_DRIVE_FILE_OUTLINED, config.get("color") or PRIMARY
    return ft.Icons.INSERT_DRIVE_FILE_OUTLINED, MUTED


def nav_button(icon, active=False):
    return ft.Container(
        width=48,
        height=48,
        border_radius=14,
        bgcolor=ACCENT_BG if active else WHITE,
        border=border_all(1, ACCENT_BORDER if active else "#EEF2F7"),
        alignment=CENTER,
        content=ft.Row(
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(width=3, height=22, border_radius=999, bgcolor=ACCENT if active else WHITE),
                ft.Container(width=41, alignment=CENTER, content=ft.Icon(icon, size=21, color=ACCENT if active else MUTED)),
            ],
        ),
    )


def row_action_button(label, icon, on_click, width=124, primary=False):
    return ft.Button(
        label,
        icon=icon,
        on_click=on_click,
        width=width,
        height=30,
        style=ft.ButtonStyle(
            bgcolor=TEXT if primary else "#F8FAFC",
            color=WHITE if primary else "#1E3A8A",
            overlay_color="#1E293B" if primary else "#DBEAFE",
            padding=pad_sym(horizontal=8, vertical=0),
            shape=ft.RoundedRectangleBorder(radius=999),
            side=ft.BorderSide(1, "#CBD5E1" if not primary else TEXT),
            mouse_cursor=ft.MouseCursor.CLICK,
            animation_duration=120,
        ),
    )


def type_style(file_type):
    icon, color = task_icon(file_type)
    return icon, color, "#EFF6FF"


def app_logo_control(size=44, radius=14):
    return ft.Container(
        width=size,
        height=size,
        border_radius=radius,
        bgcolor="#EEF2FF",
        alignment=CENTER,
        content=ft.Image(src="app/app_logo.png", fit=ft.BoxFit.COVER, width=size, height=size),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )


def profile_media_control(size=48):
    return app_logo_control(size=size, radius=14)


def color_swatch(color, selected=False, on_click=None):
    return ft.Container(
        width=28,
        height=28,
        border_radius=999,
        bgcolor=color,
        border=border_all(3 if selected else 1, TEXT if selected else WHITE),
        alignment=CENTER,
        content=ft.Icon(ft.Icons.CHECK, size=13, color=WHITE) if selected else None,
        on_click=on_click,
    )


def app_theme_preview(theme=None, selected=False, on_click=None):
    theme = theme or {}
    bg = theme.get("bg", "#F8FAFC") if isinstance(theme, dict) else "#F8FAFC"
    primary = theme.get("primary", PRIMARY) if isinstance(theme, dict) else PRIMARY
    surface = theme.get("surface", WHITE) if isinstance(theme, dict) else WHITE
    return ft.Container(
        width=132,
        height=76,
        padding=pad_sym(horizontal=10, vertical=8),
        border_radius=14,
        bgcolor=bg,
        border=border_all(2 if selected else 1, primary if selected else BORDER),
        on_click=on_click,
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Container(width=34, height=10, border_radius=999, bgcolor=primary),
                ft.Container(height=28, border_radius=8, bgcolor=surface, border=border_all(1, BORDER)),
            ],
        ),
    )


def app_theme_mockup(theme=None):
    return app_theme_preview(theme, selected=True)


def stat_card(title, value):
    accents = {
        "TOTAL": ("#F3E8FF", "#7E22CE", ft.Icons.APPS_ROUNDED),
        "WAITING": ("#DBEAFE", "#2563EB", ft.Icons.INBOX_OUTLINED),
        "DOING": ("#FFEDD5", "#C2410C", ft.Icons.TRACK_CHANGES_ROUNDED),
        "COMPLETED": ("#DCFCE7", "#059669", ft.Icons.CHECK_CIRCLE_OUTLINE),
    }
    accent_bg, accent_color, icon = accents.get(title.upper(), ("#F8FAFC", PRIMARY, ft.Icons.INSERT_CHART_OUTLINED))
    return ft.Container(
        expand=True,
        height=66,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=12,
        padding=pad_sym(horizontal=14, vertical=10),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(title.upper(), size=11, weight=ft.FontWeight.W_700, color=MUTED),
                        ft.Text(str(value), size=22, weight=ft.FontWeight.W_800, color=TEXT),
                    ],
                ),
                ft.Container(width=30, height=30, border_radius=9, bgcolor=accent_bg, alignment=CENTER, content=ft.Icon(icon, size=17, color=accent_color)),
            ],
        ),
    )


def dropdown(width, value, options, on_select=None):
    return ft.Dropdown(
        width=width,
        height=38,
        value=value,
        options=[ft.dropdown.Option(option) for option in options],
        border_radius=10,
        border_color=BORDER,
        focused_border_color=ACCENT,
        bgcolor="#F8FAFC",
        text_size=13,
        color=TEXT,
        content_padding=pad_sym(horizontal=10),
        on_select=on_select,
        filled=True,
    )


def status_button(label, bgcolor, color, on_click):
    return ft.Button(
        label,
        on_click=on_click,
        expand=True,
        style=ft.ButtonStyle(bgcolor=bgcolor, color=color, shape=ft.RoundedRectangleBorder(radius=10)),
    )


def message_dialog(title, message):
    return ft.AlertDialog(
        modal=False,
        title=ft.Text(title, size=18, weight=ft.FontWeight.W_700, color=TEXT),
        content=ft.Text(message, size=14, color=MUTED),
        bgcolor=WHITE,
        shape=ft.RoundedRectangleBorder(radius=16),
    )
