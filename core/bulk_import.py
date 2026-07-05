from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


@dataclass
class BulkImportResult:
    total: int
    created: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    cancelled: bool = False

    @property
    def processed(self) -> int:
        return len(self.created) + len(self.errors)


ProgressCallback = Callable[[int, int, str], None]
TaskFactory = Callable[[dict], dict]


def import_rows(
    rows: Iterable[dict],
    task_factory: TaskFactory,
    *,
    on_progress: ProgressCallback | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> BulkImportResult:
    """Process prepared import rows without depending on Flet controls."""
    prepared = [dict(row) for row in rows]
    result = BulkImportResult(total=len(prepared))
    for index, row in enumerate(prepared, start=1):
        if is_cancelled and is_cancelled():
            result.cancelled = True
            break
        path = str(row.get("path") or "").strip()
        label = Path(path).name or path or f"Item {index}"
        if on_progress:
            on_progress(index - 1, result.total, label)
        try:
            result.created.append(task_factory(row))
        except Exception as exc:
            result.errors.append(f"{label}: {exc}")
        if on_progress:
            on_progress(index, result.total, label)
    return result
