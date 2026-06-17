"""Virtual-list tuning helpers.

CustomTkinter does not provide a native virtual list, so SACHECK uses
collapsed groups plus batched materialization. This keeps 1000+ tasks from
becoming 1000+ widgets on initial render.
"""

DEFAULT_BATCH_SIZE = 40


def next_visible_limit(current_limit: int | None, total_count: int, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    current = current_limit or batch_size
    return min(total_count, current + batch_size)


def visible_slice(items, limit: int | None, batch_size: int = DEFAULT_BATCH_SIZE):
    resolved_limit = limit or batch_size
    return items[:resolved_limit], resolved_limit
