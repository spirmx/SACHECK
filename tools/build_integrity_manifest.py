import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "sacheck_integrity.json"
UPDATE_OUTPUT = ROOT / "sacheck_update.json"
RAW_BASE_URL = "https://raw.githubusercontent.com/spirmx/SACHECK/main"
SOURCE_ROOTS = ("config", "core", "stores", "ui")
TOP_LEVEL_FILES = ("app.py", "flet_app.py")
EXTERNAL_ASSETS = ("assets/app/app.ico", "assets/app/app_logo.png")
RELEASE_VERSION = "2.1.0-2"
RELEASE_DATE = "2026-07-06"
RELEASE_REQUIRED = True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entry(path: Path, mode: str) -> dict:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256(path),
        "mode": mode,
    }


def main() -> None:
    files = [ROOT / name for name in TOP_LEVEL_FILES]
    for folder in SOURCE_ROOTS:
        files.extend(sorted((ROOT / folder).rglob("*.py")))
    entries = [entry(path, "source") for path in files if path.is_file()]
    entries.extend(entry(ROOT / name, "all") for name in EXTERNAL_ASSETS if (ROOT / name).is_file())
    payload = {
        "version": RELEASE_VERSION,
        "algorithm": "sha256",
        "system_files": entries,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    existing_update = {}
    if UPDATE_OUTPUT.is_file():
        try:
            existing_update = json.loads(UPDATE_OUTPUT.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            existing_update = {}
    installer = ROOT / "release" / "SA_CHECK_Installer.exe"
    existing_url = str(existing_update.get("installer_url") or "") if existing_update.get("version") == RELEASE_VERSION else ""
    installer_url = os.environ.get("SACHECK_INSTALLER_URL", "").strip() or existing_url
    if installer.is_file() and not installer_url:
        installer_url = f"{RAW_BASE_URL}/release/SA_CHECK_Installer.exe"
    installer_hash = sha256(installer) if installer.is_file() else ""
    update_payload = {
        "version": RELEASE_VERSION,
        "release_date": RELEASE_DATE,
        "required": RELEASE_REQUIRED,
        "release_status": "ready" if installer_hash else "installer_build_required",
        "installer_url": installer_url if installer_hash else "",
        "installer_sha256": installer_hash,
        "installer_size": installer.stat().st_size if installer_hash else 0,
        "repair_version": RELEASE_VERSION,
        "notes": [
            "Smoothed the live Doing work island: removed the lag and the janky character-by-character scroll on the task name.",
            "The header strip now rebuilds only when the open task changes and ticks the clock once per second instead of repainting every frame.",
            "Keeps the 2.1 four-state sync indicator, sync hardening, and workflow animations intact.",
            "This is a required update for installed versions older than 2.1.0-2.",
            "Work folders, settings, cache, and user data remain preserved during updates.",
        ],
        "repair_files": [
            {
                "path": item["path"],
                "sha256": item["sha256"],
                "url": f"{RAW_BASE_URL}/{item['path']}",
                "mode": item["mode"],
            }
            for item in entries
        ],
    }
    UPDATE_OUTPUT.write_text(json.dumps(update_payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT} ({len(entries)} files)")
    print(f"Wrote {UPDATE_OUTPUT} ({len(update_payload['repair_files'])} repair files)")


if __name__ == "__main__":
    main()
