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


def make_ctx():
    tasks = sample_tasks()
    ctx = DashboardContext(
        page=MagicMock(),
        state={"screen": "overview", "view": "All work", "type": "All types", "sort": "Newest", "group_limits": {}, "search": "", "expanded_groups": set()},
        settings={},
        all_tasks=tasks,
        root_work=Path("C:/tmp/sacheck-smoke-work"),
        header_title=ft.Text(),
        header_subtitle=ft.Text(),
        progress_badge=ft.Text(),
        main_body=ft.Column(),
        search_field=ft.TextField(),
        file_picker=MagicMock(),
        current_browser_path={"path": Path("C:/tmp/sacheck-smoke-work")},
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


def check_board_layout(ctx):
    """Guard against Flutter's gray error box from a wrapped filter Row."""
    filters = ctx.main_body.controls[1]
    assert filters.height == 58, filters.height
    assert filters.content.wrap is False, filters.content.wrap
    assert filters.content.scroll == ft.ScrollMode.AUTO, filters.content.scroll


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
        ctx = make_ctx()
        ctx.state["screen"] = name
        try:
            fn(ctx)
            if name == "board":
                check_board_layout(ctx)
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
