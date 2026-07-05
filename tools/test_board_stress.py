from __future__ import annotations

import os
import sys
import time
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.flet_data as data  # noqa: E402
from ui.dialogs import CATEGORY_DIALOG_BATCH, grouped_task_controls, show_category_tasks_dialog  # noqa: E402


def make_tasks(count=2000):
    types = ("Word", "Excel", "PDF", "Google Sheet", "Miro", "Web", "Project", "Other")
    return [
        data.make_task(
            f"Stress item {index:04d}",
            f"C:/tmp/stress-{index}.dat",
            target_kind="file",
            task_type=types[index % len(types)],
            status=(data.STATUS_PENDING, data.STATUS_PROGRESS, data.STATUS_DONE)[index % 3],
        )
        for index in range(count)
    ]


def main() -> None:
    tasks = make_tasks()
    page = MagicMock()
    started = time.perf_counter()
    groups = grouped_task_controls(
        page,
        tasks,
        lambda *_args: None,
        tasks,
        column_key="Stress",
        file_types_fn=lambda: ["Word", "Excel", "PDF", "Google Sheet", "Miro", "Web", "Project", "Other"],
        expanded_keys=set(),
    )
    group_elapsed = time.perf_counter() - started
    assert len(groups) == 8
    assert group_elapsed < 2.0, f"grouping 2,000 tasks took {group_elapsed:.3f}s"

    started = time.perf_counter()
    show_category_tasks_dialog(page, "Stress", tasks, lambda *_args: None, tasks)
    dialog_elapsed = time.perf_counter() - started
    dialog = page.show_dialog.call_args[0][0]
    list_view = dialog.content.content.controls[1]
    assert len(list_view.controls) == CATEGORY_DIALOG_BATCH + 1
    assert dialog_elapsed < 2.0, f"opening a 2,000-task category took {dialog_elapsed:.3f}s"
    print(f"BOARD STRESS TEST PASSED grouping={group_elapsed:.3f}s dialog={dialog_elapsed:.3f}s")


if __name__ == "__main__":
    main()
