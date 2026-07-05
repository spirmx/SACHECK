"""Headless smoke test for SA CHECK screens.

Constructs every screen with a mock DashboardContext so runtime errors
(bad control kwargs, missing attributes, None handling) surface without
launching the real Flet window. Run:

    .venv\\Scripts\\python.exe tools\\smoke_test.py

Exits non-zero if any screen fails to build.
"""
from __future__ import annotations

import os
import sys
import traceback
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flet as ft  # noqa: E402

import core.flet_data as data  # noqa: E402
from ui.shared import DashboardContext  # noqa: E402
from ui.screens import (  # noqa: E402
    render_board,
    render_browser,
    render_calendar,
    render_health,
    render_overview,
    render_settings,
    render_templates,
)


def sample_tasks():
    tasks = [
        data.make_task("Sample Word", "C:/tmp/a.docx", target_kind="file", task_type="Word", status="pending"),
        data.make_task("Sample Excel", "C:/tmp/b.xlsx", target_kind="file", task_type="Excel", status="progress"),
        data.make_task("Sample PDF", "C:/tmp/c.pdf", target_kind="file", task_type="PDF", status="done"),
        data.make_task("Design ref", "https://figma.com/x", target_kind="url", task_type="Figma", status="pending"),
    ]
    tasks[1]["progress"] = 50
    tasks[1]["priority"] = 8
    tasks[1]["tags"] = ["urgent", "review"]
    return data.normalize_tasks(tasks)


def make_ctx(root_work=None):
    tasks = sample_tasks()
    root_work = Path(root_work or "C:/tmp/sacheck-smoke-work")
    ctx = DashboardContext(
        page=MagicMock(),
        state={"screen": "overview", "view": "All work", "type": "All types", "sort": "Newest", "group_limits": {}, "search": "", "expanded_groups": set()},
        settings={},
        all_tasks=tasks,
        root_work=root_work,
        header_title=ft.Text(),
        header_subtitle=ft.Text(),
        progress_badge=ft.Text(),
        main_body=ft.Column(),
        search_field=ft.TextField(),
        file_picker=MagicMock(),
        current_browser_path={"path": root_work},
    )
    ctx.file_types = lambda: ["Word", "Excel", "PDF", "Figma", "Slide", "Other"]
    ctx.filtered_tasks = lambda: tasks
    ctx.status_theme = lambda _s: ("#F8FAFC", "#2563EB")
    ctx.show_board = lambda *a, **k: None
    ctx.show_create_new = lambda *a, **k: None
    ctx.render_current = lambda *a, **k: None
    ctx.save_and_render = lambda *a, **k: None
    ctx.reset_filters = lambda *a, **k: None
    return ctx


SCREENS = [
    ("overview", render_overview),
    ("board", render_board),
    ("browser", render_browser),
    ("calendar", render_calendar),
    ("templates", render_templates),
    ("health", render_health),
    ("settings", render_settings),
]


def check_migration():
    """Verify legacy task dicts (no v2 fields) normalize cleanly."""
    legacy = {"name": "old task", "status": "pending", "link": "C:/x.docx"}
    out = data.normalize_task_dates(dict(legacy))
    assert out["progress"] == 0 and out["priority"] == 0 and out["tags"] == [] and out["members"] == [], out
    done = data.normalize_task_dates({"name": "d", "status": "done"})
    assert done["progress"] == 100, done
    bad = data.normalize_task_dates({"name": "z", "status": "progress", "progress": "999", "priority": "x", "tags": "nope"})
    assert bad["progress"] == 100 and bad["priority"] == 0 and bad["tags"] == [], bad
    status_cases = {
        "Waiting": data.STATUS_PENDING,
        "Doing": data.STATUS_PROGRESS,
        "In Progress": data.STATUS_PROGRESS,
        "Success": data.STATUS_DONE,
        "Completed": data.STATUS_DONE,
        "unknown-value": data.STATUS_PENDING,
    }
    for raw, expected in status_cases.items():
        assert data.normalize_task_dates({"name": raw, "status": raw})["status"] == expected


def check_board_layout(ctx):
    """Guard Board visibility after a scrollable screen and stale task data."""
    assert ctx.main_body.scroll is None, "Board must reset scroll inherited from Home/Health"
    assert len(ctx.main_body.controls) == 3
    filters = ctx.main_body.controls[1]
    assert filters.height == 58, filters.height
    assert filters.content.wrap is False, filters.content.wrap
    assert filters.content.scroll is None, filters.content.scroll
    filter_text = " | ".join(control_texts(filters))
    for action in ("Add work", "Add file", "Add link"):
        assert action in filter_text, action
    board = ctx.main_body.controls[2]
    assert isinstance(board, ft.Row) and len(board.controls) == 3
    text = " | ".join(control_texts(board))
    for task in ("Sample Word", "Sample Excel", "Sample PDF", "Design ref"):
        assert task in text, task


def control_types(control):
    found = [type(control).__name__]
    children = []
    for attr in ("controls",):
        value = getattr(control, attr, None)
        if isinstance(value, list):
            children.extend(value)
    for attr in ("content", "title"):
        value = getattr(control, attr, None)
        if value is not None:
            children.append(value)
    for child in children:
        found.extend(control_types(child))
    return found


def control_texts(control):
    found = []
    value = getattr(control, "value", None)
    if isinstance(control, ft.Text) and isinstance(value, str):
        found.append(value)
    children = []
    value = getattr(control, "controls", None)
    if isinstance(value, list):
        children.extend(value)
    for attr in ("content", "title"):
        value = getattr(control, attr, None)
        if value is not None:
            children.append(value)
    for child in children:
        found.extend(control_texts(child))
    return found


def check_health_layout(ctx):
    assert ctx.header_title.value == "System Health"
    assert len(ctx.main_body.controls) == 5
    text = " | ".join(
        item
        for control in ctx.main_body.controls
        for item in control_texts(control)
    )
    for required in (
        "Know what needs attention.",
        "Core system checks",
        "What needs attention",
        "Repair Center",
        "Backup & Activity",
    ):
        assert required in text, required


def find_text_controls(control, value):
    found = []
    if isinstance(control, ft.Text) and control.value == value:
        found.append(control)
    children = []
    controls = getattr(control, "controls", None)
    if isinstance(controls, list):
        children.extend(controls)
    for attr in ("content", "title"):
        child = getattr(control, attr, None)
        if child is not None:
            children.append(child)
    for child in children:
        found.extend(find_text_controls(child, value))
    return found


def check_calendar_layout():
    original_load = data.load_calendar_events
    try:
        today = date.today()
        data.load_calendar_events = lambda: [
            {
                "id": "red-event",
                "title": "Red event",
                "date": today.isoformat(),
                "time": "09:00",
                "kind": "Event",
                "color": "#EF4444",
                "recurrence": "none",
            }
        ]
        ctx = make_ctx()
        ctx.state["screen"] = "calendar"
        ctx.state["calendar_state"] = {
            "status": "All",
            "year": today.year,
            "month": today.month,
            "selected": today,
        }
        render_calendar(ctx)
        chips = [
            item
            for control in ctx.main_body.controls
            for item in find_text_controls(control, "09:00 Red event")
        ]
        assert chips and all(item.color == "#EF4444" for item in chips), [
            item.color for item in chips
        ]
    finally:
        data.load_calendar_events = original_load


def check_browser_layout():
    with tempfile.TemporaryDirectory(prefix="sacheck-browser-smoke-") as temp:
        root = Path(temp)
        (root / "Folder A").mkdir()
        (root / "Folder A" / "child.txt").write_text("child", encoding="utf-8")
        (root / "sample.docx").write_text("document", encoding="utf-8")
        ctx = make_ctx(root)
        ctx.state["screen"] = "browser"
        render_browser(ctx)
        assert len(ctx.main_body.controls) == 3
        names = []
        for control in ctx.main_body.controls:
            names.extend(control_types(control))
        assert "ExpansionTile" not in names, "Files must not eagerly render folder children"


def main():
    failures = []
    try:
        check_migration()
        print("[ok]   data-model migration")
    except Exception:
        print("[FAIL] data-model migration")
        traceback.print_exc()
        failures.append("migration")

    for name, fn in SCREENS:
        if name == "browser":
            try:
                check_browser_layout()
                print("[ok]   screen: browser")
            except Exception:
                print("[FAIL] screen: browser")
                traceback.print_exc()
                failures.append("browser")
            continue
        if name == "calendar":
            try:
                check_calendar_layout()
                print("[ok]   screen: calendar")
            except Exception:
                print("[FAIL] screen: calendar")
                traceback.print_exc()
                failures.append("calendar")
            continue
        ctx = make_ctx()
        ctx.state["screen"] = name
        try:
            if name == "board":
                ctx.main_body.scroll = ft.ScrollMode.AUTO
            fn(ctx)
            if name == "board":
                check_board_layout(ctx)
            if name == "health":
                check_health_layout(ctx)
            print(f"[ok]   screen: {name}")
        except Exception:
            print(f"[FAIL] screen: {name}")
            traceback.print_exc()
            failures.append(name)

    print()
    if failures:
        print("SMOKE TEST FAILED ->", ", ".join(failures))
        sys.exit(1)
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
