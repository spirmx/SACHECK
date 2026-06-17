import flet as ft

from core.flet_constants import BORDER, DOING_TEXT, DONE_TEXT, MUTED, MUTED_2, PRIMARY, TEXT, WHITE
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
        width=52,
        height=52,
        border_radius=16,
        bgcolor="#EEF2FF" if active else WHITE,
        border=border_all(1, "#C7D2FE" if active else "#EEF2F7"),
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=14, color="#12000000", offset=ft.Offset(0, 5)) if active else None,
        alignment=CENTER,
        content=ft.Row(
            spacing=0,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(width=4, height=24, border_radius=999, bgcolor=PRIMARY if active else WHITE),
                ft.Container(width=44, alignment=CENTER, content=ft.Icon(icon, size=22, color=PRIMARY if active else MUTED)),
            ],
        ),
    )


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
        height=104,
        bgcolor=WHITE,
        border=border_all(1, BORDER),
        border_radius=16,
        padding=pad_sym(horizontal=18, vertical=16),
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=18, color="#10000000", offset=ft.Offset(0, 6)),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=10,
                    controls=[
                        ft.Text(title.upper(), size=11, weight=ft.FontWeight.W_800, color=MUTED),
                        ft.Text(str(value), size=30, weight=ft.FontWeight.W_800, color=TEXT),
                    ],
                ),
                ft.Container(width=38, height=38, border_radius=12, bgcolor=accent_color, alignment=CENTER, shadow=ft.BoxShadow(spread_radius=0, blur_radius=12, color="#26000000", offset=ft.Offset(0, 4)), content=ft.Icon(icon, size=19, color=WHITE)),
            ],
        ),
    )


def dropdown(width, value, options, on_select=None):
    return ft.Dropdown(
        width=width,
        height=48,
        value=value,
        options=[ft.dropdown.Option(option) for option in options],
        border_radius=14,
        border_color=BORDER,
        focused_border_color="#CBD5E1",
        bgcolor="#F8FAFC",
        text_size=14,
        color=TEXT,
        content_padding=pad_sym(horizontal=12),
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
