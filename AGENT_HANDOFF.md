# SA CHECK Agent Handoff

Current release target: `2.0.8-1`. Before continuing, verify `git status`, all linked worktrees, and the update/integrity manifests. Do not build from an older clean branch when another worktree contains uncommitted UI work.

This file is the continuation contract for any agent editing this repository. Inspect the live tree; do not assume the last release describes current work.

## Baseline and current target

- Repository: `spirmx/SACHECK`, branch `main`.
- Last known pre-release baseline: `ef7e12c` (`2.0.7`).
- Current source/release target: `2.0.8`, required update. Refresh the actual HEAD with `git log` after checkout.
- Release `2.0.8` unifies Add file/link UI across Board and Templates, restores Template inline types, and adds event-driven animations. Preserve and inspect dirty work before changing anything.
- Claude recovery stash: `stash@{0}` when this document was created, label `recover-claude-ui-cache-2026-07-05`. Stash indexes move; identify it by label/commit, never by index alone.
- Earlier safety stash: label `codex-pre-v2-release-main-work`.

Always refresh this evidence with:

```powershell
git status --short
git diff --stat
git diff -- ui/flet_dashboard.py
git log -8 --oneline --decorate
git stash list
```

Do not run a build, regenerate manifests, restore a stash, or publish while unaware of dirty files. Existing dirty changes are user work.

## Claude cache recovery

The recovered UI is retained in Git history and a named stash. First inspect without applying:

```powershell
git stash list
git stash show --stat "stash^{/recover-claude-ui-cache-2026-07-05}"
git stash show -p "stash^{/recover-claude-ui-cache-2026-07-05}"
```

Never `pop` it onto active work. If recovery is actually needed, create a temporary branch/worktree from the stash or apply it only after making a new safety stash. Compare individual files and restore only intentional sections. Calendar, Settings, Templates, dialogs, startup, and Board behavior must not be replaced wholesale with older copies.

## Tests

Run from the repository root with the project virtual environment:

```powershell
.venv\Scripts\python.exe tools\test_core.py
.venv\Scripts\python.exe tools\smoke_test.py
.venv\Scripts\python.exe tools\test_bulk_import.py
.venv\Scripts\python.exe tools\test_board_groups.py
.venv\Scripts\python.exe tools\test_board_stress.py
```

Also run `python -m compileall` on changed Python packages and manually exercise the modified Flet flows. A successful build is not a substitute for these tests.

## Release and integrity procedure

1. Inspect the dirty worktree and reconcile all intended changes.
2. Update every version source together: `APP_VERSION` and `VERSION_HISTORY` in `ui/flet_dashboard.py`, `pyproject.toml`, constants and notes in `tools/build_integrity_manifest.py`, and the new versioned `installer/SACHECK_<version>.iss` copied from the prior script with its build input/output versions updated.
3. Run all tests above before packaging.
4. Build the Windows app into the exact directory referenced by the Inno Setup `[Files]` entry.
5. Compile the Inno Setup script so the final artifact is `release/SA_CHECK_Installer.exe`. Test install/update behavior and confirm `%APPDATA%\SA CHECK`, selected Work folders, settings, cache, templates, and Calendar data remain untouched.
6. Only after the final installer exists, run:

```powershell
.venv\Scripts\python.exe tools\build_integrity_manifest.py
```

7. Confirm `sacheck_integrity.json` hashes the final source and `sacheck_update.json` reports `ready`, the correct version, required flag, installer size, URL, and SHA-256. Re-run integrity generation after any source or installer change.
8. Test the installer and startup/update/repair path. Startup repair in `core/startup_preflight.py` overwrites mismatched source-mode files, so publishing stale manifests causes apparent code rollback.
9. Commit source, installer script, installer binary, integrity manifest, and update manifest atomically. Push only after reviewing the staged diff. Verify GitHub-served manifests and installer hash.

Never publish a manifest for a version before its matching tested installer exists.

## Continuation snapshot

Create a shareable source ZIP after meaningful work:

```powershell
.venv\Scripts\python.exe tools\export_source_snapshot.py
```

The timestamped archive is written beneath `build/source-snapshots/` (`build/` is gitignored). It contains tracked source/config/docs/tests/assets using current working-tree contents, plus commit/status/stash metadata and SHA-256 checksums. The exporter excludes builds, releases, Git/Claude state, user data, caches, virtual environments, and common secret filenames, then reopens and verifies the ZIP. Do not commit generated snapshot ZIPs.
