# SA CHECK Agent Handoff

Current release target: `2.1.0-1`. Before continuing, verify `git status`, all linked worktrees, and the update/integrity manifests. Do not build from an older clean branch when another worktree contains uncommitted UI work.

This file is the continuation contract for any agent editing this repository. Inspect the live tree; do not assume the last release describes current work.

## Release 2.1.0-1 — work-session reliability

- Removed the character-by-character live-work marquee that caused UI lag. Long names now use ellipsis, the clock updates only when the second changes, and the island rebuilds only when active work changes.
- Added persistent session recovery in `%APPDATA%\SA CHECK\data\runtime_session.json`; stale or malformed entries are ignored and old single-item sessions migrate automatically.
- Added safe shutdown: background loops stop, active sync receives up to five seconds to finish, then Tasks, Calendar, and Settings are flushed atomically before exit.
- Added an automatic retained snapshot before shutdown using the existing snapshot/retention system. Failures are isolated and written to Activity Log rather than blocking exit indefinitely.
- Added the Work Switcher. `Ctrl+Tab` cycles forward and `Ctrl+Shift+Tab` cycles backward through up to 12 most-recently-opened tasks without relaunching files or browser tabs.
- Dynamic Island shows the selected MRU position as `work x/y`; opening a task again moves it to the front of the list.
- Added regression coverage for session persistence, recovery, MRU ordering, forward/reverse cycling, and lifecycle/package safety. Core, smoke, Board group, bulk import, and 2,000-task stress checks passed.
- Built and installed the matching package into `C:\SACHECK`; update and integrity manifests match installer size and SHA-256.

## Release 2.1.0 — sync visibility and stability consolidation

- Added the Sidebar scheduled-sync indicator requested in the marked red area: gray is idle, amber animates while syncing, green confirms success for 60 seconds, and red remains visible after failure.
- Sync failures are written to Activity Log with component, error type, message, context, and traceback where available.
- Added the Header live-work strip requested in the marked green area. It shows `Doing · <task name>`; only long task names scroll and the status-change time remains fixed at the right.
- Added `status_changed_at` to new work and status transitions while remaining compatible with old records.
- Added non-blocking sync locking, guarded priority parsing, safe task-list snapshots, refresh timeout/error propagation, and command/render failure reporting.
- Release positioning: 2.1.0 consolidates reliability, offline-first data safety, recovery, update, Board scaling, import, drag/drop, and workflow UI work accumulated since the 1.x platform.
- Cleanup completed: obsolete generated Python caches and superseded Windows build outputs were removed; user data, `.venv`, source snapshots, and active build tooling were preserved.
- Per user instruction, do not install the 2.1.0 package over the currently installed local application during this release pass.

## Baseline and current target

- Repository: `spirmx/SACHECK`, branch `main`.
- Last known pre-release baseline: `ef7e12c` (`2.0.7`).
- Current source/release target: `2.1.0-1`, required update. Refresh the actual HEAD with `git log` after checkout.
- Release `2.1.0-1` adds low-overhead live-work rendering, session recovery, safe shutdown backup, and the MRU Work Switcher on top of the 2.1.0 stability baseline.
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

---

## Session log — 2026-07-05 · UI animations & Home hero alert panel

Goal: add tasteful animations / "ลูกเล่น" across the app and surface the daily
alert (today + tomorrow) in the Home hero. All changes are on the dev working tree
and were verified in the live app (`python app.py`). Not built/released yet.

### What was added (by screen)

- **Home** (`ui/screens/overview.py`): hero rebuilt as a two-pane Row — left = date / greeting / Create-work + Open-Calendar buttons; **right = alert panel that fills the formerly empty hero space**, listing **today & tomorrow** alerts (pulse dot on today rows, taps to Calendar). Also: completion `ProgressRing` + `%` **count up** on load, **Doing** dot in Work pulse breathes, nav tiles **fade/stagger in**.
- **Board** (`ui/screens/board.py` + `ui/dialogs.py`): summary numbers **count up**; 3 columns **fade in** staggered; **Doing** column header icon breathes + ping ring (only when it has tasks). Task-detail status pill pops in, Doing dot breathes, status picker hover glow + rotating chevron.
- **Files** (`ui/screens/browser.py`): metric numbers **count up**; metric icons breathe (VISIBLE pings = "scan"); metric cards **fade/stagger in**.
- **Templates** (`ui/screens/templates.py`): template cards **pop in** (staggered); primary **Use** button breathing glow.
- **Calendar** (`ui/screens/calendar_screen.py`): **today's** cell softly breathes its glow.

### Reusable helpers added — `ui/flet_widgets.py`

`pulse_dot`, `breathing_badge`, `breathe_glow`, `animated_status_pill`, `count_up`
(number tween, can drive a `ProgressRing`), `fade_in_up`, `alert_carousel`
(AnimatedSwitcher cycler — currently unused after hero became a static panel),
`_with_alpha`; plus `status_menu` upgraded. All animation loops run via
`page.run_task`, guard `update()` in try/except, and self-stop on control detach.

### Fixed / worked around

- **Integrity self-repair was reverting screen edits.** `core/startup_preflight` restores files listed in `sacheck_integrity.json` that the remote manifest also repairs; the set now spans `ui/screens/*.py` broadly (older notes said only board/health). `overview.py` edits vanished on relaunch until fixed. **Removed from `sacheck_integrity.json` this session:** `board.py`, `browser.py`, `calendar_screen.py`, `overview.py`, `templates.py`. Helpers under `ui/` root (`flet_widgets.py`, `dialogs.py`, `flet_dashboard.py`) stick without removal. Dev-only — `tools/build_integrity_manifest.py` regenerates the ship manifest, so Pro self-heal is unaffected. **Before editing any `ui/screens/*.py`, remove its entry first.**
- **`animate_offset` does not tween smoothly in this Flet 0.85 build (it snaps).** A continuous scrolling marquee was tried and abandoned for `alert_carousel`, then the static hero panel; `fade_in_up`'s slide is effectively just the opacity fade. `animate_scale` / `animate_opacity` / container `animate` (shadow/border) work fine. `ProgressRing.value` doesn't self-tween → `count_up` steps it manually.

### State / next steps

- Not built or released — version still `2.0.8-1`. Follow the release/integrity procedure above before shipping (the removed `sacheck_integrity.json` entries are dev convenience; the manifest is rebuilt at package time).
- Optional follow-ups: tune subtle glows (Templates "Use", Calendar today cell); add flourishes to **Settings** / **Health** (remove `health.py` from `sacheck_integrity.json` first). Per-task card entrance is intentionally NOT staggered (up to ~2000 tasks → no per-row async loops).
