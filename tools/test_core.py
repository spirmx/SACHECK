"""Unit tests for the risky pure logic in core.flet_data.

These functions decide file names and categories that drive real
file moves/copies, so a regression here can misplace user work. Pure
(no GUI, no user file I/O), so they run fast and deterministically:

    .venv\\Scripts\\python.exe tools\\test_core.py

Exits non-zero on the first failing group.
"""
from __future__ import annotations

import os
import sys
import traceback
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.flet_data as data  # noqa: E402
from core.app_lifecycle import SingleInstanceGuard  # noqa: E402
from core.startup_preflight import parse_version  # noqa: E402
from core.flet_theme import (  # noqa: E402
    CALENDAR_EVENT_COLOR_CHOICES,
    DEFAULT_CALENDAR_EVENT_COLOR,
    calendar_event_style,
    normalize_calendar_event_color,
)


def test_safe_item_name():
    assert data.safe_item_name("A:B/C") == "A-B-C"
    assert data.safe_item_name('a<b>c:d"e/f\\g|h?i*j') == "a-b-c-d-e-f-g-h-i-j"
    assert data.safe_item_name("") == "Untitled"
    assert data.safe_item_name("   ") == "Untitled"
    assert data.safe_item_name("...") == "Untitled"
    assert data.safe_item_name("  spaced name  ") == "spaced name"
    assert data.safe_item_name("", fallback="Fallback") == "Fallback"
    assert data.safe_item_name("normal_file-01") == "normal_file-01"


def test_infer_type_extensions():
    assert data.infer_type("C:/work/report.docx") == "Word"
    assert data.infer_type("C:/work/budget.xlsx") == "Excel"
    assert data.infer_type("C:/work/manual.pdf") == "PDF"
    assert data.infer_type("C:/work/deck.pptx") == "Slide"
    assert data.infer_type("C:/work/photo.png") == "Image"
    # unknown extension on a non-existent path falls back to Other
    assert data.infer_type("C:/work/mystery.zzz") == "Other"


def test_infer_type_urls():
    assert data.infer_type("https://www.figma.com/file/abc") == "Figma"
    assert data.infer_type("https://docs.google.com/spreadsheets/d/1") == "Google Sheet"
    assert data.infer_type("https://github.com/spirmx/SACHECK") == "Project"
    assert data.infer_type("https://miro.com/app/board/xyz") == "Miro"
    # unknown host -> generic link
    assert data.infer_type("https://example.com/page") == "Link"


def test_date_only():
    assert data.date_only("2026-06-15T10:30:00") == "2026-06-15"
    assert data.date_only("2026-06-15") == "2026-06-15"
    fallback = data.date_only("")
    assert len(fallback) == 10 and fallback[4] == "-", fallback
    assert data.date_only(None)[:4].isdigit()


def test_normalize_progress_priority():
    done = data.normalize_task_dates({"name": "x", "status": "done", "progress": 50})
    assert done["progress"] == 100, done  # done forces complete
    clamp = data.normalize_task_dates({"name": "y", "status": "progress", "progress": 250})
    assert clamp["progress"] == 100, clamp
    neg = data.normalize_task_dates({"name": "z", "status": "pending", "progress": -5})
    assert neg["progress"] == 0, neg
    keep = data.normalize_task_dates({"name": "w", "status": "progress", "progress": 42})
    assert keep["progress"] == 42, keep
    bad = data.normalize_task_dates({"name": "b", "status": "pending", "priority": "oops", "tags": "notalist"})
    assert bad["priority"] == 0 and bad["tags"] == [], bad


def test_normalize_legacy_statuses():
    aliases = {
        "Waiting": data.STATUS_PENDING,
        "todo": data.STATUS_PENDING,
        "Doing": data.STATUS_PROGRESS,
        "In Progress": data.STATUS_PROGRESS,
        "active": data.STATUS_PROGRESS,
        "Success": data.STATUS_DONE,
        "Completed": data.STATUS_DONE,
        "unknown-status": data.STATUS_PENDING,
    }
    for raw, expected in aliases.items():
        normalized = data.normalize_task_dates({"name": raw, "status": raw})
        assert normalized["status"] == expected, normalized


def test_calendar_event_palette():
    assert normalize_calendar_event_color("#ef4444") == "#EF4444"
    assert normalize_calendar_event_color("invalid") == DEFAULT_CALENDAR_EVENT_COLOR
    assert calendar_event_style({"kind": "Event", "color": "#EF4444"}) == ("#EF4444", "#FEF2F2")
    assert calendar_event_style({"kind": "Meeting", "color": "#EF4444"}) == ("#EF4444", "#FEF2F2")
    assert calendar_event_style({"kind": "Deadline", "color": "#22C55E"}) == ("#22C55E", "#F0FDF4")
    assert all(calendar_event_style(color)[0] == color for color in CALENDAR_EVENT_COLOR_CHOICES)
    events, changed = data._normalize_calendar_events(
        [{"id": "event-1", "date": "2026-07-05T09:00:00", "color": "#ef4444"}]
    )
    assert changed is True
    assert events[0]["date"] == "2026-07-05"
    assert events[0]["color"] == "#EF4444"


def test_custom_file_type_creation():
    settings = {"custom_file_types": []}
    original_save = data.save_settings
    original_folders = data.ensure_status_folders
    calls = []
    try:
        data.save_settings = lambda value: calls.append(("save", value))
        data.ensure_status_folders = lambda: calls.append(("folders", None))
        item = data.create_custom_file_type(
            settings,
            "CAD Drawing",
            extensions="dwg, .dxf",
            icon="cad",
            color="#2563eb",
        )
        assert item["name"] == "CAD Drawing"
        assert item["extensions"] == [".dwg", ".dxf"]
        assert item["icon"] == "CAD" and item["color"] == "#2563EB"
        assert [name for name, _value in calls] == ["save", "folders"]
        try:
            data.create_custom_file_type(settings, "cad drawing")
            raise AssertionError("duplicate type name should fail")
        except ValueError:
            pass
    finally:
        data.save_settings = original_save
        data.ensure_status_folders = original_folders


def test_update_build_version():
    assert parse_version("2.0.8-1") == (2, 0, 8, 1)
    assert parse_version("2.0.8-1") > parse_version("2.0.8")


def test_active_work_session_recovery():
    original_file = data.SESSION_FILE
    original_active = data._ACTIVE_OPEN_WORK
    original_history = data._OPEN_WORK_HISTORY
    original_index = data._ACTIVE_OPEN_INDEX
    try:
        with tempfile.TemporaryDirectory() as folder:
            data.SESSION_FILE = Path(folder) / "runtime_session.json"
            task = {"id": "task-1", "name": "Recovered work", "type": "Word"}
            second = {"id": "task-2", "name": "Second work", "type": "Excel"}
            data._ACTIVE_OPEN_WORK = None
            data._OPEN_WORK_HISTORY = []
            data._ACTIVE_OPEN_INDEX = -1
            data._mark_active_open_work(task)
            data._mark_active_open_work(second)
            assert data.SESSION_FILE.is_file()
            assert data.active_open_work()["id"] == "task-2"
            assert data.active_open_work()["switcher_total"] == 2
            assert data.cycle_active_open_work()["id"] == "task-1"
            assert data.cycle_active_open_work(-1)["id"] == "task-2"
            data._ACTIVE_OPEN_WORK = None
            data._OPEN_WORK_HISTORY = []
            restored = data.restore_active_work_session([task, second])
            assert restored and restored["id"] == "task-2"
            assert restored["name"] == "Second work" and restored["recovered"] is True
            data._ACTIVE_OPEN_WORK = None
            data._OPEN_WORK_HISTORY = []
            assert data.restore_active_work_session([]) is None
    finally:
        data.SESSION_FILE = original_file
        data._ACTIVE_OPEN_WORK = original_active
        data._OPEN_WORK_HISTORY = original_history
        data._ACTIVE_OPEN_INDEX = original_index


def test_unique_target_and_resolve_type():
    # resolve_add_type keeps a specific requested type, upgrades Other/Link
    assert data.resolve_add_type("C:/x/a.docx", "Word") == "Word"
    assert data.resolve_add_type("C:/x/a.docx", "Other") == "Word"
    # unknown URL added as Other keeps the detected generic "Link" type
    assert data.resolve_add_type("https://example.com", "Other") == "Link"
    # a typed URL is detected past Other
    assert data.resolve_add_type("https://www.figma.com/file/a", "Other") == "Figma"


def test_single_instance_guard():
    if sys.platform != "win32":
        return
    name = rf"Local\Hoyturbro.SACHECK.Test.{uuid.uuid4()}"
    first = SingleInstanceGuard(name)
    second = None
    try:
        assert first.already_running is False
        second = SingleInstanceGuard(name)
        assert second.already_running is True
    finally:
        if second:
            second.close()
        first.close()


def test_lifecycle_and_package_hygiene():
    root = Path(__file__).resolve().parents[1]
    dashboard = (root / "ui" / "flet_dashboard.py").read_text(encoding="utf-8")
    assert "state[\"closing\"] = True" in dashboard
    assert "os._exit(0)" in dashboard
    assert "shutdown_event.wait(sync_interval_seconds())" in dashboard
    config = (root / "pyproject.toml").read_text(encoding="utf-8")
    for excluded in ('".claude"', '".git"', '"**/__pycache__"', '"*.pyc"'):
        assert excluded in config, excluded


TESTS = [
    ("safe_item_name", test_safe_item_name),
    ("infer_type (extensions)", test_infer_type_extensions),
    ("infer_type (urls)", test_infer_type_urls),
    ("date_only", test_date_only),
    ("normalize progress/priority", test_normalize_progress_priority),
    ("normalize legacy statuses", test_normalize_legacy_statuses),
    ("calendar event palette", test_calendar_event_palette),
    ("custom file type creation", test_custom_file_type_creation),
    ("update build version", test_update_build_version),
    ("active work session recovery", test_active_work_session_recovery),
    ("resolve_add_type", test_unique_target_and_resolve_type),
    ("single instance guard", test_single_instance_guard),
    ("lifecycle/package hygiene", test_lifecycle_and_package_hygiene),
]


def main():
    failures = []
    for name, fn in TESTS:
        try:
            fn()
            print(f"[ok]   {name}")
        except Exception:
            print(f"[FAIL] {name}")
            traceback.print_exc()
            failures.append(name)
    print()
    if failures:
        print("CORE TESTS FAILED ->", ", ".join(failures))
        sys.exit(1)
    print("CORE TESTS PASSED")


if __name__ == "__main__":
    main()
