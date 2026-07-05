"""Export a verified, shareable snapshot of the SA CHECK source tree."""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "build" / "source-snapshots"
INCLUDED_ROOTS = {
    "assets", "config", "core", "design", "installer", "stores", "tools", "ui", "web-prototype"
}
INCLUDED_TOP_LEVEL = {
    ".gitignore", "app.py", "flet_app.py", "pyproject.toml", "requirements.txt",
    "sacheck_integrity.json", "sacheck_update.json", "sacheck_update_manifest.example.json",
}
INCLUDED_SUFFIXES = {".md", ".txt"}
EXCLUDED_PARTS = {
    ".git", ".claude", ".venv", "venv", "build", "dist", "release", "cache", "data",
    "__pycache__", ".dev_profile", ".dev_work",
}
SECRET_MARKERS = {
    ".env", "credentials", "credential", "secrets", "secret", "private_key", "id_rsa", "id_ed25519",
}


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=check, capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout.strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_safe_tracked_file(relative: str) -> bool:
    path = PurePosixPath(relative)
    lowered_parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if lowered_parts & EXCLUDED_PARTS:
        return False
    if any(marker in name for marker in SECRET_MARKERS):
        return False
    return path.parts[0] in INCLUDED_ROOTS or relative in INCLUDED_TOP_LEVEL or (
        len(path.parts) == 1 and path.suffix.lower() in INCLUDED_SUFFIXES
    )


def main() -> None:
    tracked = [line for line in git("ls-files").splitlines() if line and is_safe_tracked_file(line)]
    files = [(name, (ROOT / name).read_bytes()) for name in sorted(tracked) if (ROOT / name).is_file()]
    if not files:
        raise RuntimeError("No tracked source files found; run this script inside the repository")

    now = datetime.now(timezone.utc)
    short_head = git("rev-parse", "--short=12", "HEAD")
    metadata = {
        "created_utc": now.isoformat(),
        "git_head": git("rev-parse", "HEAD"),
        "git_branch": git("branch", "--show-current") or "DETACHED",
        "git_describe": git("describe", "--always", "--dirty", "--tags"),
        "git_status_short": git("status", "--short"),
        "git_stashes": git("stash", "list"),
        "file_count": len(files),
        "scope": "tracked source/config/docs/tests/assets; working-tree contents",
        "excluded": sorted(EXCLUDED_PARTS),
    }
    checksums = "".join(f"{sha256(data)}  {name}\n" for name, data in files).encode("utf-8")
    extra = {
        "SNAPSHOT_METADATA.json": (json.dumps(metadata, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
        "FILE_SHA256SUMS.txt": checksums,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archive = OUTPUT_DIR / f"SACHECK-source-{now:%Y%m%dT%H%M%SZ}-{short_head}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in [*files, *extra.items()]:
            bundle.writestr(name, data)

    expected = {name: sha256(data) for name, data in [*files, *extra.items()]}
    with zipfile.ZipFile(archive, "r") as bundle:
        corrupt = bundle.testzip()
        if corrupt:
            raise RuntimeError(f"ZIP CRC verification failed at {corrupt}")
        actual_names = set(bundle.namelist())
        if actual_names != set(expected):
            raise RuntimeError("ZIP contents differ from the export plan")
        for name, digest in expected.items():
            if sha256(bundle.read(name)) != digest:
                raise RuntimeError(f"ZIP SHA-256 verification failed at {name}")

    print(f"Created and verified: {archive}")
    print(f"Files: {len(files)} tracked + {len(extra)} metadata")


if __name__ == "__main__":
    main()
