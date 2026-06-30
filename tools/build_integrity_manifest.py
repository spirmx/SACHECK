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
        "version": "1.0.9-02 Abillity",
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
    existing_url = str(existing_update.get("installer_url") or "") if existing_update.get("version") == "1.0.9-02 Abillity" else ""
    installer_url = os.environ.get("SACHECK_INSTALLER_URL", "").strip() or existing_url
    if installer.is_file() and not installer_url:
        installer_url = f"{RAW_BASE_URL}/release/SA_CHECK_Installer.exe"
    installer_hash = sha256(installer) if installer.is_file() else ""
    update_payload = {
        "version": "1.0.9-02 Abillity",
        "release_date": "2026-06-30",
        "required": False,
        "release_status": "ready" if installer_hash else "installer_build_required",
        "installer_url": installer_url if installer_hash else "",
        "installer_sha256": installer_hash,
        "installer_size": installer.stat().st_size if installer_hash else 0,
        "repair_version": "1.0.9-02 Abillity",
        "notes": [
            "Removed the black native startup frame by showing the window only after the loader is ready.",
            "Replaced the Flet executable and title-bar icon with the SA CHECK logo.",
            "Changed the startup loader from a floating card to a full-window loading surface.",
            "Sync now safely refreshes Work data and settings without closing or blanking the app.",
            "Manual refresh checks the Git update channel when Online mode is enabled.",
            "Work scanning runs in the background with timeout and error recovery.",
            "The startup loader is centered on screen and remains visible long enough to read.",
            "Fixed About SA CHECK and User guide buttons in the Settings Credits section.",
            "Settings now opens the real About, User guide, and Version notes dialogs.",
            "Added a bright, colorful startup loader before the Work Board opens.",
            "Online startup checks use a short timeout and reuse the result in the existing updater.",
            "Offline mode skips update and integrity network checks and opens local work immediately.",
            "Added SHA-256 verified repair support for app system files.",
            "Work folders, settings, cache, and user data are never cleared by startup repair.",
            "Added a recovery screen instead of leaving the app on a black screen if dashboard startup fails.",
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
