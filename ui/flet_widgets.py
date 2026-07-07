import asyncio

import flet as ft

from core.flet_constants import ACCENT, ACCENT_BG, ACCENT_BORDER, BORDER, DOING_TEXT, DONE_TEXT, MUTED, MUTED_2, PRIMARY, TEXT, WHITE
from core.flet_data import file_type_config


def _with_alpha(color, alpha_hex):
    """Return a #AARRGGBB colour by prefixing an alpha byte to a #RRGGBB base.

    Flet expects the alpha byte first (see the "#18FFFFFF" tints used across the
    app), so we only touch plain 7-char hex colours and leave anything else as-is.
    """
    if isinstance(color, str) and len(color) == 7 and color.startswith("#"):
        return f"#{alpha_hex}{color[1:]}"
    return color


# Every looping animation (pulse/breathe/shake/marquee/carousel) captures the
# current epoch when it starts and stops as soon as the epoch moves on. The
# central screen re-render bumps the epoch, so loops from a previous render die
# instead of piling up forever — otherwise they accumulate on every navigation
# and eventually saturate the async loop and freeze the app.
_ANIM_EPOCH = 0

# Switch for the always-on ambient loops (pulse_dot, breathing_badge, breathe_glow).
# These repaint the Flutter canvas almost continuously and were the dominant CPU
# cost, so they default OFF. Periodic/low-duty effects (shake_bell, alert_carousel,
# marquee) and all one-shot entrance/count-up/hover effects stay on regardless.
# Default OFF for lowest CPU; the Settings "motion effects" toggle turns it on.
_MOTION = False


def set_motion(enabled: bool):
    global _MOTION
    _MOTION = bool(enabled)


def _should_animate(page):
    return page is not None and _MOTION


def bump_anim_epoch():
    """Invalidate all per-render animation loops created before now.

    Call once at the top of the central screen re-render. Returns the new epoch.
    """
    global _ANIM_EPOCH
    _ANIM_EPOCH += 1
    return _ANIM_EPOCH


def _anim_epoch():
    return _ANIM_EPOCH


def pad_sym(horizontal=0, vertical=0):
    return ft.Padding(horizontal, vertical, horizontal, vertical)


def pad_only(left=0, top=0, right=0, bottom=0):
    return ft.Padding(left, top, right, bottom)


def border_all(width=1, color=BORDER):
    side = ft.BorderSide(width, color)
    return ft.Border(left=side, top=side, right=side, bottom=side)


CENTER = ft.Alignment(0, 0)


def hover_lift(container, scale=1.02, accent=None, base_border=None, shadow=True, lift=6, dur=140):
    """Attach a lag-free hover animation (scale + optional shadow/border) to a
    Container. Only fires while pointed at, so it stays cheap even in long lists.
    """
    container.animate_scale = ft.Animation(dur, ft.AnimationCurve.EASE_OUT)
    if shadow or (accent is not None):
        container.animate = ft.Animation(dur, ft.AnimationCurve.EASE_OUT)

    def _on_hover(event):
        active = event.data == "true"
        container.scale = scale if active else 1
        if shadow:
            container.shadow = ft.BoxShadow(spread_radius=0, blur_radius=18, color="#1E0F172A", offset=ft.Offset(0, lift)) if active else None
        if accent is not None and base_border is not None:
            container.border = border_all(1, accent if active else base_border)
        try:
            container.update()
        except Exception:
            pass

    container.on_hover = _on_hover
    return container


def pulse_dot(page, color, size=9):
    """A small status dot with a cheap "heartbeat": a quick scale pop followed by a
    long rest, so the Flutter canvas is idle most of the time (no glow/halo/blur,
    single tiny control, one animated property). Static when motion is off.
    """
    dot = ft.Container(
        width=size,
        height=size,
        border_radius=999,
        bgcolor=color,
        animate_scale=ft.Animation(420, ft.AnimationCurve.EASE_IN_OUT),
    )

    async def _beat():
        epoch = _anim_epoch()
        await asyncio.sleep(0.4)  # let the control mount first
        while _MOTION and _anim_epoch() == epoch:
            dot.scale = 1.4  # quick pop
            try:
                dot.update()
            except Exception:
                break
            await asyncio.sleep(0.5)
            dot.scale = 1.0  # settle, then idle so Flutter stops repainting
            try:
                dot.update()
            except Exception:
                break
            await asyncio.sleep(2.8)

    if page is not None:
        try:
            page.run_task(_beat)
        except Exception:
            pass
    return dot


def breathing_badge(page, icon, icon_color, bg, *, size=38, radius=11, icon_size=19, ping=False):
    """An icon badge with a cheap heartbeat: a quick scale pop, then a long rest.
    No glow/blur breathing and no expanding ping ring (those repaint large areas
    continuously), so the canvas stays idle between beats. `ping` just makes the
    beat a touch stronger. Static when motion is off.
    """
    badge = ft.Container(
        width=size,
        height=size,
        border_radius=radius,
        bgcolor=bg,
        alignment=CENTER,
        content=ft.Icon(icon, size=icon_size, color=icon_color),
        shadow=ft.BoxShadow(spread_radius=0, blur_radius=5, color=_with_alpha(icon_color, "22")),
        animate_scale=ft.Animation(430, ft.AnimationCurve.EASE_IN_OUT),
    )
    peak = 1.13 if ping else 1.08

    async def _beat():
        epoch = _anim_epoch()
        await asyncio.sleep(0.35)
        while _MOTION and _anim_epoch() == epoch:
            badge.scale = peak
            try:
                badge.update()
            except Exception:
                break
            await asyncio.sleep(0.5)
            badge.scale = 1.0
            try:
                badge.update()
            except Exception:
                break
            await asyncio.sleep(3.0)

    if page is not None:
        try:
            page.run_task(_beat)
        except Exception:
            pass
    return badge


def marquee(page, build_chips, *, height=32, seconds=16, gap=10):
    """A horizontal ticker that scrolls a lane of chips continuously and
    seamlessly. `build_chips` is a callable returning a *fresh* list of controls
    each time (Flet forbids reusing one control twice), so the lane holds two
    identical copies and the loop wraps by snapping back with the animation off.
    """
    first = list(build_chips() or [])
    if not first:
        return ft.Container(height=height)

    lane = ft.Container(
        content=ft.Row(
            spacing=gap,
            tight=True,
            wrap=False,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[*first, *(build_chips() or [])],
        ),
        offset=ft.Offset(0, 0),
        animate_offset=ft.Animation(int(seconds * 1000), ft.AnimationCurve.LINEAR),
    )
    holder = ft.Container(
        height=height,
        expand=True,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        content=ft.Stack(controls=[lane], clip_behavior=ft.ClipBehavior.NONE),
    )

    async def _run():
        epoch = _anim_epoch()
        await asyncio.sleep(0.4)
        while _anim_epoch() == epoch:
            lane.offset = ft.Offset(-0.5, 0)  # scroll left by exactly one copy
            try:
                lane.update()
            except Exception:
                break
            await asyncio.sleep(seconds)
            lane.animate_offset = None  # snap back invisibly (copies are identical)
            lane.offset = ft.Offset(0, 0)
            try:
                lane.update()
            except Exception:
                break
            await asyncio.sleep(0.05)
            lane.animate_offset = ft.Animation(int(seconds * 1000), ft.AnimationCurve.LINEAR)
            try:
                lane.update()
            except Exception:
                break

    if page is not None:
        try:
            page.run_task(_run)
        except Exception:
            pass
    return ft.Row(controls=[holder])


def shake_bell(page, icon, *, period=6.0):
    """Make a bell icon periodically ring — a quick side-to-side rotation wiggle,
    then a long pause, on a loop. Self-stops when the icon detaches.
    """
    icon.rotate = ft.Rotate(0)
    icon.animate_rotation = ft.Animation(120, ft.AnimationCurve.EASE_IN_OUT)
    swings = (0.34, -0.26, 0.16, 0.0)

    async def _ring():
        epoch = _anim_epoch()
        await asyncio.sleep(0.6)
        while _anim_epoch() == epoch:
            for angle in swings:
                icon.rotate = ft.Rotate(angle)
                try:
                    icon.update()
                except Exception:
                    return
                await asyncio.sleep(0.1)
            await asyncio.sleep(period)  # rest between rings

    if page is not None:
        try:
            page.run_task(_ring)
        except Exception:
            pass
    return icon


def count_up(page, text_control, target, *, duration=0.85, suffix="", prefix="", ring=None, ring_divisor=100):
    """Tween a number from 0 up to `target` (ease-out) by stepping the Text value,
    optionally driving a ProgressRing's value in lockstep. ProgressRing/Text don't
    tween on their own, so we step them from an async task; safe on detach.
    """
    try:
        target = int(target)
    except (TypeError, ValueError):
        return text_control

    def _label(value):
        return f"{prefix}{value}{suffix}"

    if target <= 0:
        text_control.value = _label(target)
        if ring is not None:
            ring.value = max(0.0, target) / ring_divisor
        return text_control

    steps = min(max(target, 1), 26)
    text_control.value = _label(0)
    if ring is not None:
        ring.value = 0.0

    async def _run():
        await asyncio.sleep(0.06)
        for step in range(1, steps + 1):
            t = step / steps
            eased = 1 - (1 - t) * (1 - t)  # ease-out
            value = round(target * eased)
            text_control.value = _label(value)
            ok = True
            try:
                text_control.update()
            except Exception:
                ok = False
            if ring is not None:
                ring.value = value / ring_divisor
                try:
                    ring.update()
                except Exception:
                    ok = False
            if not ok:
                return
            await asyncio.sleep(duration / steps)
        text_control.value = _label(target)
        try:
            text_control.update()
        except Exception:
            pass

    if page is not None:
        try:
            page.run_task(_run)
        except Exception:
            text_control.value = _label(target)
            if ring is not None:
                ring.value = target / ring_divisor
    else:
        text_control.value = _label(target)
        if ring is not None:
            ring.value = target / ring_divisor
    return text_control


def alert_carousel(page, items, build_card, *, interval=4.0, transition=None):
    """Cycle through `items` one card at a time with an animated swap — a compact,
    reliable "running alerts" ticker. `build_card(item, index)` must return a
    freshly-keyed control so the switcher detects the change and animates it.
    """
    if not items:
        return ft.Container(height=0)

    switcher = ft.AnimatedSwitcher(
        content=build_card(items[0], 0),
        transition=transition or ft.AnimatedSwitcherTransition.SCALE,
        duration=430,
        reverse_duration=260,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
    )
    state = {"i": 0}

    async def _rotate():
        epoch = _anim_epoch()
        await asyncio.sleep(interval)
        while _anim_epoch() == epoch:
            state["i"] = (state["i"] + 1) % len(items)
            switcher.content = build_card(items[state["i"]], state["i"])
            try:
                switcher.update()
            except Exception:
                break
            await asyncio.sleep(interval)

    if page is not None and len(items) > 1:
        try:
            page.run_task(_rotate)
        except Exception:
            pass
    return switcher


def fade_in_up(page, control, *, delay=0.0, dy=0.18, dur=340):
    """Reveal a control by fading and sliding it up into place. `delay` lets you
    stagger a group (e.g. nav tiles) for a cascading entrance. Falls back to a
    plain visible control if there is no page to schedule on.
    """
    control.opacity = 0
    control.offset = ft.Offset(0, dy)
    control.animate_opacity = ft.Animation(dur, ft.AnimationCurve.EASE_OUT)
    control.animate_offset = ft.Animation(dur, ft.AnimationCurve.EASE_OUT)

    async def _reveal():
        await asyncio.sleep(0.02 + max(0.0, delay))
        control.opacity = 1
        control.offset = ft.Offset(0, 0)
        try:
            control.update()
        except Exception:
            pass

    if page is not None:
        try:
            page.run_task(_reveal)
        except Exception:
            control.opacity = 1
            control.offset = ft.Offset(0, 0)
    else:
        control.opacity = 1
        control.offset = ft.Offset(0, 0)
    return control


def breathe_glow(page, control, color, *, base_blur=10, peak_blur=26, base_alpha="14", peak_alpha="55", period=2.0):
    """Make any Container softly pulse its coloured shadow — a calm "you are here"
    beacon (e.g. today's calendar cell). Self-stops when the control detaches.
    """
    if getattr(control, "animate", None) is None:
        control.animate = ft.Animation(int(period * 700), ft.AnimationCurve.EASE_IN_OUT)
    state = {"on": False}

    async def _loop():
        epoch = _anim_epoch()
        await asyncio.sleep(0.4)
        while _MOTION and _anim_epoch() == epoch:
            state["on"] = not state["on"]
            control.shadow = ft.BoxShadow(
                spread_radius=0,
                blur_radius=peak_blur if state["on"] else base_blur,
                color=_with_alpha(color, peak_alpha if state["on"] else base_alpha),
                offset=ft.Offset(0, 4),
            )
            try:
                control.update()
            except Exception:
                break
            await asyncio.sleep(period)

    if page is not None:
        try:
            page.run_task(_loop)
        except Exception:
            pass
    return control


def animated_status_pill(page, label, color, bg, *, pulse=False, dot_color=None):
    """A status chip that pops in (scale + fade with a soft overshoot) and, when
    `pulse` is set, carries a breathing dot for "live" statuses like Doing.
    """
    dot_hue = dot_color or color
    dot = pulse_dot(page, dot_hue) if pulse else ft.Container(width=9, height=9, border_radius=999, bgcolor=dot_hue)

    pill = ft.Container(
        padding=pad_sym(horizontal=13, vertical=7),
        border_radius=999,
        bgcolor=bg,
        border=border_all(1, color),
        scale=0.7,
        opacity=0,
        animate=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
        animate_scale=ft.Animation(360, ft.AnimationCurve.EASE_OUT_BACK),
        animate_opacity=ft.Animation(240, ft.AnimationCurve.EASE_OUT),
        content=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                dot,
                ft.Text(label, size=12, weight=ft.FontWeight.W_900, color=color),
            ],
        ),
    )

    async def _reveal():
        await asyncio.sleep(0.03)
        pill.scale = 1
        pill.opacity = 1
        try:
            pill.update()
        except Exception:
            pass

    if page is not None:
        try:
            page.run_task(_reveal)
        except Exception:
            pill.scale = 1
            pill.opacity = 1
    else:
        pill.scale = 1
        pill.opacity = 1
    return pill


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
    button = ft.Container(
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
    return hover_lift(button, scale=1.045, accent=ACCENT_BORDER, base_border=ACCENT_BORDER if active else "#EEF2F7", shadow=not active, lift=3, dur=120)


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
    swatch = ft.Container(
        width=28,
        height=28,
        border_radius=999,
        bgcolor=color,
        border=border_all(3 if selected else 1, TEXT if selected else WHITE),
        alignment=CENTER,
        content=ft.Icon(ft.Icons.CHECK, size=13, color=WHITE) if selected else None,
        on_click=on_click,
    )
    return hover_lift(swatch, scale=1.13, shadow=True, lift=3, dur=110)


def app_theme_preview(theme=None, selected=False, on_click=None):
    theme = theme or {}
    bg = theme.get("bg", "#F8FAFC") if isinstance(theme, dict) else "#F8FAFC"
    primary = theme.get("primary", PRIMARY) if isinstance(theme, dict) else PRIMARY
    surface = theme.get("surface", WHITE) if isinstance(theme, dict) else WHITE
    preview = ft.Container(
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
    return hover_lift(preview, scale=1.025, accent=primary, base_border=primary if selected else BORDER, shadow=True, lift=4, dur=140)


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
    card = ft.Container(
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
    return hover_lift(card, scale=1.018, accent=accent_color, base_border=BORDER, shadow=True, lift=4, dur=140)


def dropdown(width, value, options, on_select=None):
    return ft.Dropdown(
        width=width,
        height=44,
        value=value,
        options=[ft.dropdown.Option(option) for option in options],
        border_radius=12,
        border_color=BORDER,
        border_width=1,
        focused_border_color=ACCENT,
        focused_border_width=2,
        bgcolor=WHITE,
        fill_color=WHITE,
        filled=True,
        text_size=13,
        color=TEXT,
        text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_700, color=TEXT),
        content_padding=pad_sym(horizontal=13),
        hover_color="#F1F5F9",
        elevation=6,
        on_select=on_select,
    )


def add_destination_header(title, subtitle, icon, destination):
    """Shared Add-file/Add-link header used across every destination screen."""
    return ft.Row(
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                width=42,
                height=42,
                border_radius=13,
                bgcolor="#EFF6FF",
                alignment=CENTER,
                content=ft.Icon(icon, size=22, color=PRIMARY),
                animate_scale=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
            ),
            ft.Column(
                spacing=2,
                expand=True,
                controls=[
                    ft.Text(title, size=22, weight=ft.FontWeight.W_900, color=TEXT),
                    ft.Text(subtitle, size=12, color=MUTED),
                ],
            ),
            ft.Container(
                padding=pad_sym(horizontal=10, vertical=5),
                border_radius=999,
                bgcolor="#ECFDF5",
                border=border_all(1, "#A7F3D0"),
                content=ft.Text(destination, size=10, weight=ft.FontWeight.W_900, color="#047857"),
            ),
        ],
    )


STATUS_MENU_STYLE = {
    "Waiting": ("#2563EB", "#EFF6FF", ft.Icons.INBOX_OUTLINED),
    "Doing": ("#D97706", "#FFFBEB", ft.Icons.BOLT_OUTLINED),
    "Success": ("#16A34A", "#F0FDF4", ft.Icons.CHECK_CIRCLE_OUTLINE),
}


def status_menu(current_label, on_change, width=182):
    """Colourful status picker (Waiting / Doing / Success) with hover animation.

    on_change receives the chosen label string.
    """
    color, bg, icon = STATUS_MENU_STYLE.get(current_label, STATUS_MENU_STYLE["Waiting"])

    def menu_item(label):
        item_color, item_bg, item_icon = STATUS_MENU_STYLE[label]
        selected = label == current_label
        return ft.PopupMenuItem(
            content=ft.Container(
                width=width - 24,
                padding=pad_sym(horizontal=10, vertical=8),
                border_radius=10,
                bgcolor=item_bg,
                border=border_all(1, item_color if selected else item_bg),
                content=ft.Row(
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(width=26, height=26, border_radius=8, bgcolor=item_color, alignment=CENTER, content=ft.Icon(item_icon, size=15, color=WHITE)),
                        ft.Text(label, size=13, weight=ft.FontWeight.W_800, color=item_color, expand=True),
                        ft.Icon(ft.Icons.CHECK_ROUNDED, size=16, color=item_color) if selected else ft.Container(width=0, height=0),
                    ],
                ),
            ),
            on_click=lambda _e, chosen=label: on_change(chosen),
        )

    arrow = ft.Icon(
        ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
        size=18,
        color=color,
        rotate=ft.Rotate(0),
        animate_rotation=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
    )

    trigger = ft.Container(
        width=width,
        height=44,
        padding=pad_sym(horizontal=12),
        border_radius=12,
        bgcolor=bg,
        border=border_all(1.5, color),
        alignment=CENTER,
        animate=ft.Animation(160, ft.AnimationCurve.EASE_OUT),
        animate_scale=ft.Animation(140, ft.AnimationCurve.EASE_OUT),
        content=ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(width=9, height=9, border_radius=99, bgcolor=color),
                ft.Text(current_label, size=13, weight=ft.FontWeight.W_900, color=color, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                arrow,
            ],
        ),
    )

    def on_hover(event):
        active = event.data == "true"
        trigger.scale = 1.03 if active else 1
        trigger.shadow = (
            ft.BoxShadow(spread_radius=0, blur_radius=16, color=_with_alpha(color, "44"), offset=ft.Offset(0, 4))
            if active
            else None
        )
        arrow.rotate = ft.Rotate(0.5) if active else ft.Rotate(0)
        try:
            trigger.update()
        except Exception:
            pass

    trigger.on_hover = on_hover

    return ft.PopupMenuButton(
        content=trigger,
        menu_position=ft.PopupMenuPosition.UNDER,
        items=[menu_item("Waiting"), menu_item("Doing"), menu_item("Success")],
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
