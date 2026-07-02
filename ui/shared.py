"""Shared context and helpers used by extracted screen modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import flet as ft


def _noop(*_args, **_kwargs):
    return None


def _identity(value=None, *_args, **_kwargs):
    return value


def _empty_list(*_args, **_kwargs):
    return []


def _default_status_theme(_status):
    return "#F8FAFC", "#2563EB"


@dataclass
class DashboardContext:
    """Portable context object for screen renderers.

    Defaults keep older call sites working while screen modules remain decoupled
    from the dashboard controller.
    """

    page: ft.Page
    state: Dict[str, Any]
    settings: Dict[str, Any]
    all_tasks: List[dict]

    root_work: Any = None

    main_body: Optional[ft.Column] = None
    header_title: Optional[ft.Text] = None
    header_subtitle: Optional[ft.Text] = None
    progress_badge: Optional[ft.Text] = None
    search_field: Optional[ft.TextField] = None
    file_picker: Optional[ft.FilePicker] = None

    current_browser_path: Dict[str, Any] = field(default_factory=dict)

    render_current: Callable = _noop
    save_and_render: Callable = _noop
    sync_now: Callable = _noop
    show_board: Callable = _noop
    show_browser: Callable = _noop
    show_settings: Callable = _noop
    show_health: Callable = _noop
    show_calendar: Callable = _noop
    show_calendar_event_dialog: Callable = _noop
    show_templates: Callable = _noop
    update_sidebar: Callable = _noop
    pick_directory: Callable = _noop
    check_for_updates: Callable = _noop
    update_channel_url: Callable = _noop
    apply_app_theme: Callable = _identity
    set_work_folder: Callable = _identity
    reset_filters: Callable = _noop
    undo_last: Callable = _noop
    add_or_update_from_path: Callable = _noop
    run_with_duplicate_guard: Callable = _noop
    remember_task_action: Callable = _noop
    show_create_new: Callable = _noop
    show_about: Callable = _noop
    show_help: Callable = _noop
    show_version_notes: Callable = _noop

    status_theme: Callable = _default_status_theme
    file_types: Callable = _empty_list
    filtered_tasks: Callable = _empty_list
    profile_media_control: Callable = _noop
    t: Callable = _identity
