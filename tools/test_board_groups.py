"""Headless tests for the Board category-grouping feature.

Runs independently of the main app (no Flet window): it builds the group
cards and the category popup with a mock page and asserts behavior.

    .venv\\Scripts\\python.exe tools\\test_board_groups.py

Exits non-zero if any check fails. Covers:
  * tasks group by file type inside a status column
  * inline preview never exceeds CATEGORY_PREVIEW_LIMIT
  * the "More / View all" button is ALWAYS present (even for small groups)
  * "More +N" reports the correct hidden count for heavy categories
  * the category popup opens and its name search filters correctly
"""
from __future__ import annotations

import os
import sys
import traceback
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.flet_data as data  # noqa: E402
from ui.dialogs import (  # noqa: E402
    CATEGORY_PREVIEW_LIMIT,
    grouped_task_controls,
    show_category_tasks_dialog,
    type_group_card,
)


def make_tasks(file_type, count, status="pending"):
    tasks = [
        data.make_task(
            f"{file_type} file {i:03d}",
            f"C:/tmp/{file_type.lower()}-{i}.dat",
            target_kind="file",
            task_type=file_type,
            status=status,
        )
        for i in range(count)
    ]
    return data.normalize_tasks(tasks)


def group_button(card):
    """Return the trailing button control from a type_group_card container."""
    column = card.content.controls[0]  # ExpansionTile -> ft.Column
    return column.controls[-1]


def button_label(card):
    return group_button(card).content.controls[1].value


def preview_count(card):
    column = card.content.controls[0]
    return len(column.controls) - 1  # minus the button


CHECKS = []


def check(name, fn):
    CHECKS.append((name, fn))


def run():
    page = MagicMock()
    noop = lambda *_a, **_k: None

    def small_group():
        tasks = make_tasks("Word", 3)
        card = type_group_card(page, "Word", tasks, noop, tasks, group_key="Waiting:Word", expanded_keys=set())
        assert preview_count(card) == 3, f"expected 3 preview cards, got {preview_count(card)}"
        assert button_label(card) == "View all", f"small group label should be 'View all', got {button_label(card)!r}"

    def large_group():
        tasks = make_tasks("Excel", 103)
        card = type_group_card(page, "Excel", tasks, noop, tasks, group_key="Waiting:Excel", expanded_keys=set())
        assert preview_count(card) == CATEGORY_PREVIEW_LIMIT, f"preview should cap at {CATEGORY_PREVIEW_LIMIT}, got {preview_count(card)}"
        expected = f"More +{103 - CATEGORY_PREVIEW_LIMIT}"
        assert button_label(card) == expected, f"expected {expected!r}, got {button_label(card)!r}"

    def exactly_limit():
        tasks = make_tasks("PDF", CATEGORY_PREVIEW_LIMIT)
        card = type_group_card(page, "PDF", tasks, noop, tasks, group_key="Waiting:PDF", expanded_keys=set())
        assert preview_count(card) == CATEGORY_PREVIEW_LIMIT
        assert button_label(card) == "View all", f"exactly-limit group should say 'View all', got {button_label(card)!r}"

    def groups_by_type():
        mixed = make_tasks("Word", 2) + make_tasks("Figma", 3) + make_tasks("PDF", 1)
        controls = grouped_task_controls(page, mixed, noop, mixed, column_key="Waiting", expanded_keys=set())
        assert len(controls) == 3, f"expected 3 type groups, got {len(controls)}"

    def popup_search():
        tasks = make_tasks("Word", 103)
        show_category_tasks_dialog(page, "Word", tasks, noop, tasks)
        assert page.show_dialog.called, "show_dialog was not called"
        dlg = page.show_dialog.call_args[0][0]
        column = dlg.content.content
        search, list_view = column.controls[0], column.controls[1]

        class E:
            class control:
                value = "file 042"

        search.on_change(E())
        assert len(list_view.controls) == 1, f"search 'file 042' should match 1, got {len(list_view.controls)}"

        class E2:
            class control:
                value = ""

        search.on_change(E2())
        assert len(list_view.controls) == 103, f"cleared search should show 103, got {len(list_view.controls)}"

    check("small group -> preview 3, button 'View all'", small_group)
    check("large group -> preview 10, button 'More +93'", large_group)
    check("exactly-limit group -> button 'View all'", exactly_limit)
    check("mixed tasks -> one card per file type", groups_by_type)
    check("category popup search filters by name", popup_search)

    failures = 0
    for name, fn in CHECKS:
        try:
            fn()
            print(f"[ok]   {name}")
        except Exception:
            failures += 1
            print(f"[FAIL] {name}")
            traceback.print_exc()

    print()
    if failures:
        print(f"BOARD GROUP TESTS FAILED ({failures} of {len(CHECKS)})")
        return 1
    print(f"BOARD GROUP TESTS PASSED ({len(CHECKS)} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
