r"""Profile common SACHECK UI paths from source.

Run:
    .\.venv\Scripts\python.exe tools\profile_performance.py
"""

import cProfile
import io
import pstats
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app  # noqa: E402


def scenario():
    root = app.TaskBoardApp()
    root.update()
    for _ in range(3):
        root.refresh(force=True)
        root.update()
    root.search_var.set("BR")
    root.run_scheduled_search_refresh()
    root.update()
    root.search_var.set("")
    root.run_scheduled_search_refresh()
    root.update()
    root.destroy()


def main():
    profile = cProfile.Profile()
    profile.enable()
    start = time.perf_counter()
    scenario()
    elapsed = time.perf_counter() - start
    profile.disable()

    stream = io.StringIO()
    pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("cumtime").print_stats(35)
    print(f"ELAPSED {elapsed:.3f}s")
    print(stream.getvalue())


if __name__ == "__main__":
    main()
