from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


StatusCallback = Callable[[str, str, float], None]
PROTECTED_TOP_LEVEL = {"cache", "data", "work"}
ALLOWED_TOP_LEVEL = {"app.py", "flet_app.py", "assets", "config", "core", "stores", "ui"}


@dataclass
class StartupResult:
    online_enabled: bool = False
    online_checked: bool = False
    manifest: dict | None = None
    update_available: bool = False
    repaired_files: list[str] = field(default_factory=list)
    health_issues: list[str] = field(default_factory=list)
    warning: str = ""
    elapsed_seconds: float = 0.0


def _notify(callback: StatusCallback | None, step: str, message: str, progress: float) -> None:
    if callback:
        callback(step, message, max(0.0, min(1.0, progress)))


def parse_version(value: object) -> tuple[int, int, int, int]:
    import re

    match = re.search(r"(\d+)\.(\d+)\.(\d+)(?:[-._ ]+(\d+))?", str(value or ""))
    if not match:
        return (0, 0, 0, 0)
    return tuple(int(part or 0) for part in match.groups())


def _read_json_url(url: str, timeout: float) -> dict:
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(
        f"{url}{separator}startup={int(time.time())}",
        headers={"User-Agent": "SA-CHECK-Startup/2.0.3", "Accept": "application/json", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(2 * 1024 * 1024)
    data = json.loads(payload.decode("utf-8-sig"))
    if isinstance(data, dict) and "content" in data and str(data.get("encoding", "")).lower() == "base64":
        data = json.loads(base64.b64decode(str(data["content"])).decode("utf-8-sig"))
    return data if isinstance(data, dict) else {}


def _load_integrity_manifest(app_root: Path) -> dict:
    path = app_root / "sacheck_integrity.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def _safe_system_target(app_root: Path, relative: str, frozen: bool) -> Path | None:
    relative_path = Path(str(relative or "").replace("\\", "/"))
    if not relative or relative_path.is_absolute() or ".." in relative_path.parts:
        return None
    if not relative_path.parts or relative_path.parts[0].casefold() in PROTECTED_TOP_LEVEL:
        return None
    if relative_path.parts[0] not in ALLOWED_TOP_LEVEL:
        return None
    if frozen and relative_path.suffix.lower() in {".py", ".pyc", ".pyd"}:
        return None
    root = app_root.resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def _applicable(entry: dict, frozen: bool) -> bool:
    mode = str(entry.get("mode") or "all").lower()
    return mode == "all" or (mode == "source" and not frozen) or (mode == "external" and frozen)


def inspect_integrity(app_root: Path, frozen: bool = False) -> tuple[list[dict], list[str]]:
    integrity = _load_integrity_manifest(app_root)
    entries = integrity.get("system_files") or []
    if not isinstance(entries, list):
        return [], ["Integrity manifest is invalid."]
    failed: list[dict] = []
    issues: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or not _applicable(entry, frozen):
            continue
        relative = str(entry.get("path") or "").strip()
        expected = str(entry.get("sha256") or "").strip().lower()
        target = _safe_system_target(app_root, relative, frozen)
        if target is None or len(expected) != 64:
            issues.append(f"Unsafe integrity entry: {relative or '(empty path)'}")
            continue
        try:
            valid = target.is_file() and _sha256(target) == expected
        except OSError:
            valid = False
        if not valid:
            failed.append({"path": relative, "sha256": expected, "target": target})
            issues.append(f"System file failed verification: {relative}")
    return failed, issues


def _download_verified(url: str, expected_sha256: str, target: Path, timeout: float) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "SA-CHECK-Repair/2.0.3"})
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="sacheck-repair-", suffix=".part", delete=False, dir=target.parent) as temp:
            temp_path = Path(temp.name)
            digest = hashlib.sha256()
            with urllib.request.urlopen(request, timeout=timeout) as response:
                while True:
                    chunk = response.read(128 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    temp.write(chunk)
            temp.flush()
            os.fsync(temp.fileno())
        if digest.hexdigest().lower() != expected_sha256.lower():
            raise ValueError("Downloaded repair file did not match its SHA-256 hash.")
        os.replace(temp_path, target)
        temp_path = None
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def repair_failed_files(
    app_root: Path,
    failed: list[dict],
    remote_manifest: dict,
    app_version: str,
    frozen: bool = False,
    timeout: float = 3.0,
) -> tuple[list[str], list[str]]:
    repair_version = str(remote_manifest.get("repair_version") or remote_manifest.get("version") or "")
    if parse_version(repair_version) != parse_version(app_version):
        return [], ["Repair files target a different app version; normal update is required."] if failed else []
    entries = remote_manifest.get("repair_files") or []
    if not isinstance(entries, list):
        entries = []
    by_path = {str(item.get("path") or ""): item for item in entries if isinstance(item, dict)}
    repaired: list[str] = []
    errors: list[str] = []
    for problem in failed:
        relative = problem["path"]
        expected = problem["sha256"]
        remote = by_path.get(relative) or {}
        url = str(remote.get("url") or "").strip()
        remote_hash = str(remote.get("sha256") or "").strip().lower()
        target = _safe_system_target(app_root, relative, frozen)
        if not target or not url or remote_hash != expected:
            errors.append(f"No verified repair source for {relative}.")
            continue
        try:
            _download_verified(url, expected, target, timeout)
            repaired.append(relative)
        except Exception as exc:
            errors.append(f"Could not repair {relative}: {exc}")
    return repaired, errors


def run_startup_preflight(
    *,
    settings: dict,
    manifest_url: str,
    app_version: str,
    app_root: Path,
    frozen: bool = False,
    timeout: float = 2.5,
    status: StatusCallback | None = None,
) -> StartupResult:
    started = time.perf_counter()
    result = StartupResult()
    online_enabled = not bool(settings.get("offline_mode", False)) and bool(settings.get("update_checks_enabled", True))
    result.online_enabled = online_enabled and bool(str(manifest_url or "").strip())
    _notify(status, "boot", "Starting SA CHECK services...", 0.08)

    if not online_enabled or not str(manifest_url or "").strip():
        _notify(status, "offline", "Offline mode: opening local workspace...", 0.92)
        result.elapsed_seconds = time.perf_counter() - started
        return result

    _notify(status, "local", "Checking core files...", 0.22)
    failed, issues = inspect_integrity(app_root, frozen=frozen)
    result.health_issues = issues

    try:
        _notify(status, "online", "Checking update channel...", 0.46)
        manifest = _read_json_url(str(manifest_url).strip(), timeout)
        result.online_checked = True
        result.manifest = manifest or None
        result.update_available = bool(manifest and parse_version(manifest.get("version")) > parse_version(app_version))
        if failed:
            _notify(status, "repair", "Repairing verified system files...", 0.68)
            repaired, repair_errors = repair_failed_files(
                app_root,
                failed,
                manifest,
                app_version,
                frozen=frozen,
                timeout=max(timeout, 3.0),
            )
            result.repaired_files = repaired
            if repaired:
                _, remaining = inspect_integrity(app_root, frozen=frozen)
                result.health_issues = remaining
            result.health_issues.extend(repair_errors)
    except Exception as exc:
        result.warning = f"Online startup check skipped: {exc}"

    _notify(status, "ready", "Workspace ready.", 1.0)
    result.elapsed_seconds = time.perf_counter() - started
    return result
