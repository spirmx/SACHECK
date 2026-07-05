from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bulk_import import import_rows


def main() -> None:
    rows = [{"path": f"C:/tmp/file-{index}.txt", "type": "Text"} for index in range(5)]
    progress = []

    def factory(row):
        if row["path"].endswith("2.txt"):
            raise OSError("copy failed")
        return {"name": row["path"]}

    result = import_rows(rows, factory, on_progress=lambda done, total, name: progress.append((done, total, name)))
    assert result.total == 5
    assert len(result.created) == 4
    assert len(result.errors) == 1 and "file-2.txt" in result.errors[0]
    assert progress[-1][0:2] == (5, 5)

    cancel_after_two = import_rows(
        rows,
        lambda row: row,
        is_cancelled=lambda: False,
        on_progress=lambda *_args: None,
    )
    assert cancel_after_two.processed == 5 and not cancel_after_two.cancelled

    checks = {"count": 0}

    def cancelled():
        checks["count"] += 1
        return checks["count"] > 2

    cancelled_result = import_rows(rows, lambda row: row, is_cancelled=cancelled)
    assert cancelled_result.cancelled and cancelled_result.processed == 2
    print("BULK IMPORT TESTS PASSED")


if __name__ == "__main__":
    main()
