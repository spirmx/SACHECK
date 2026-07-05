from __future__ import annotations

import re


DEFAULT_CALENDAR_EVENT_COLOR = "#7C3AED"
CALENDAR_EVENT_COLOR_CHOICES = (
    "#7C3AED", "#6366F1", "#2563EB", "#0284C7", "#0891B2", "#0F766E",
    "#16A34A", "#65A30D", "#CA8A04", "#D97706", "#EA580C", "#DC2626",
    "#E11D48", "#DB2777", "#C026D3", "#9333EA", "#475569", "#111827",
    "#22C55E", "#06B6D4", "#F59E0B", "#EF4444", "#EC4899", "#14B8A6",
)
CALENDAR_EVENT_BACKGROUNDS = {
    "#2563EB": "#EFF6FF",
    "#D97706": "#FFFBEB",
    "#16A34A": "#F0FDF4",
    "#7C3AED": "#F5F3FF",
    "#DC2626": "#FEF2F2",
    "#0891B2": "#ECFEFF",
    "#DB2777": "#FDF2F8",
    "#0F766E": "#F0FDFA",
    "#EA580C": "#FFF7ED",
    "#A855F7": "#FAF5FF",
    "#14B8A6": "#F0FDFA",
    "#6366F1": "#EEF2FF",
    "#0284C7": "#F0F9FF",
    "#65A30D": "#F7FEE7",
    "#CA8A04": "#FEFCE8",
    "#E11D48": "#FFF1F2",
    "#C026D3": "#FDF4FF",
    "#9333EA": "#FAF5FF",
    "#475569": "#F8FAFC",
    "#111827": "#F8FAFC",
    "#22C55E": "#F0FDF4",
    "#06B6D4": "#ECFEFF",
    "#F59E0B": "#FFFBEB",
    "#EF4444": "#FEF2F2",
    "#EC4899": "#FDF2F8",
}


def normalize_calendar_event_color(value: object) -> str:
    color = str(value or "").strip().upper()
    return color if re.fullmatch(r"#[0-9A-F]{6}", color) else DEFAULT_CALENDAR_EVENT_COLOR


def calendar_event_style(event_or_color: object) -> tuple[str, str]:
    raw_color = event_or_color.get("color") if isinstance(event_or_color, dict) else event_or_color
    color = normalize_calendar_event_color(raw_color)
    return color, CALENDAR_EVENT_BACKGROUNDS.get(color, "#F8FAFC")


def apply_app_theme(settings=None):
    """Compatibility shim for the in-progress extracted settings screen."""
    return settings or {}
