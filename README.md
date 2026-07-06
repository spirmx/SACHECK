# SA CHECK

Desktop Work Board for SA/IT work tracking.

Developer / Creator: HOYTURBRO  
Alias: Hoyturbro  
Publisher: HOYTURBRO

## Current Release

Version: `2.1.0-2`

This hotfix restores the Board Kanban view by correcting the Flutter filter-row layout.

`2.1.0-2` hardens the live work strips by retiring old animation loops on re-render, which removes the lag that could build up after repeated navigation.

Latest changes:

- Removed the black frame shown before the Python loader connected.
- Replaced the default Flet EXE/title-bar icon with the SA CHECK logo.
- Reworked the startup loader as a full-window surface instead of a floating card.
- Sync now opens a centered progress loader and refreshes the app without closing it.
- Work scanning runs in the background so the window does not turn black or stay on Working.
- Every manual refresh checks the Git update channel when Online mode is enabled.
- A timeout guard returns control to the user if a folder scan takes too long.
- The colorful startup loader is centered on screen and stays visible long enough to read.
- Online startup checks use a one-second timeout and reuse the result in the updater.
- Offline mode skips update and integrity network checks and opens local work immediately.
- Added SHA-256 verified repair for approved app system files.
- Added a startup recovery card instead of leaving a black screen if dashboard handoff fails.
- Keeps the V1.0.7.1 UI sharpness, V1.0.7 Health Center, V1.0.6 reliability fixes, and V1.0.5 Template fixes.
- Silent update installs do not show the Setup wizard and SA CHECK stays closed after update.
- Does not clear Work folders, settings, cache, or local user data.
- Work folders, settings, cache, and user data are preserved during update.

## Local 1.0.9 Regression Recovery (Not Published Yet)

The 1.0.9 screen extraction originally moved Template and Calendar UI code out of
`ui/flet_dashboard.py`, but some 1.0.8 behavior was replaced by placeholders.
The current working tree restores that behavior. These changes are local and must
not be published until they have been tested and explicitly approved.

Restored behavior:

- Template reads only the `Template` folder inside every work category.
- Add File Template uses the native file picker and copies the selected file into the correct category's `Template` folder.
- Add Link Template creates a `.url` shortcut in the correct category's `Template` folder.
- Templates are grouped by work category and expose their real folder location.
- Template actions include copy to Waiting, open, open folder, copy path, details, and delete.
- Calendar Add/Edit/Delete Event works again, including time, type, color, note, daily reminder, and event-time alarm options.
- Calendar events are stored outside the install directory with a recovery cache, so an installer or Git-based app update does not remove them.

## Work Folder System

Each work category has the same four folders:

```text
<selected Work folder>\
  Word\
    Waiting\
    Doing\
    Success\
    Template\
  Excel\
    Waiting\
    Doing\
    Success\
    Template\
  <other categories>\
    Waiting\
    Doing\
    Success\
    Template\
```

Folder responsibilities:

- `Waiting` contains work that has not started.
- `Doing` contains active work.
- `Success` contains completed work.
- `Template` contains reusable source files, folders, and `.url` shortcuts.

The Work Board scanner reads only `Waiting`, `Doing`, and `Success`. The Template
Library scanner reads only `<category>\Template`. A file in `Waiting`, `Doing`, or
`Success` must never appear as a Template.

## Template System

Template records are indexed in `%APPDATA%\SA CHECK\data\templates.json`, while
the actual reusable files remain in `<selected Work folder>\<category>\Template`.
The JSON index stores metadata such as notes, usage count, and last-used time; the
folder is the source of truth for whether the reusable file or shortcut exists.

When a Template is used, SA CHECK copies it to the same category's `Waiting`
folder and creates a normal Work Board record. The original Template stays in the
`Template` folder.

## Calendar System and Update Safety

Calendar events are stored in two user-owned files outside `C:\SACHECK`:

```text
Primary: %APPDATA%\SA CHECK\data\calendar_events.json
Cache:   %APPDATA%\SA CHECK\cache\calendar\calendar_events.json
```

Writes are atomic. If the primary event file is missing or invalid, SA CHECK
recovers it from the cache. Existing 1.0.8 events previously stored inside
`app_settings.json` are migrated automatically on first load.

Snapshots now include tasks, templates, settings, and Calendar events. Restoring
a new-format snapshot restores Calendar events as well.

The installer may replace files under `C:\SACHECK`, but it must never delete or
overwrite `%APPDATA%\SA CHECK` or the selected Work folder.

## Startup Integrity and Repair (Root Cause of the 1.0.9 Revert)

On startup, `core/startup_preflight.py` hashes every source file listed in
`sacheck_integrity.json` and, when Online mode is enabled, downloads and overwrites
any file whose hash does not match the expected value. When running from source,
a local fix therefore fails the hash check and is silently reverted to the pinned
version on the next launch. This is the update-and-repair behavior that made 1.0.9
appear to "lose" the restored Template and Calendar code.

Because of this, any source change must be paired with a regenerated integrity
manifest, otherwise startup repair reverts the change:

```text
.venv\Scripts\python.exe tools\build_integrity_manifest.py
```

`sacheck_integrity.json` has been regenerated from the corrected source so startup
repair now recognizes the fixed files and no longer reverts them. `inspect_integrity`
reports zero failed files, so no repair download runs. When publishing, the fixed
source and the regenerated `sacheck_integrity.json` / `sacheck_update.json` must be
committed together so a fresh install does not reintroduce the placeholders.

## Main Systems

- Work Board: tracks Waiting, Doing, and Success by category.
- Work Browser: browses and organizes files in the selected Work folder.
- Template Library: scans only category Template folders and creates reusable copies.
- Calendar: displays work status dates and persistent user-created events.
- Sync: rescans Work and Template folders without deleting user-owned data.
- Snapshots and undo: create local recovery points before important changes.
- Health Center: checks data paths, Work folders, snapshots, and update readiness.
- Offline/Online mode: all work stays local; internet is used only for update checks and downloads when enabled.
- Safe updater: replaces application files while preserving Work, AppData, settings, cache, templates, and Calendar data.

## App Concept

SA CHECK is offline-first. Users can work without internet. Internet is only used for checking and downloading app updates when Online mode is enabled.

Installed app path:

```text
C:\SACHECK
```

User data path:

```text
%APPDATA%\SA CHECK\data
```

Work folders are selected by the user inside the app. The updater must not clear or replace user Work folders, settings, cache, or local data.

## Update Channel

The app checks the GitHub manifest:

```text
https://api.github.com/repos/spirmx/SACHECK/contents/sacheck_update.json?ref=main
```

The manifest points to:

```text
release/SA_CHECK_Installer.exe
```

For stable updater tests, the installer URL in `sacheck_update.json` can be pinned to a commit-specific raw GitHub URL after the installer binary has been pushed.

## Developer Notes

Main Flet entry:

```text
ui/flet_dashboard.py
```

Important files:

- `sacheck_update.json` - update manifest used by installed apps.
- `sacheck_integrity.json` - SHA-256 list for startup integrity checks.
- `core/startup_preflight.py` - fast online check and verified repair engine.
- `ui/startup.py` - startup loader and recovery UI.
- `README.md` - Git/Drive developer notes.
- `release/SA_CHECK_Installer.exe` - installer payload for users and in-app updates.

Before publishing a new update:

1. Update `APP_VERSION` in `ui/flet_dashboard.py`.
2. Add a new version entry in `VERSION_HISTORY`.
3. Update `sacheck_update.json`.
4. Run `python tools/build_integrity_manifest.py` after the final source edit.
5. Build the installer and calculate its SHA-256 hash.
6. Set `installer_url`, remove `installer_build_required`, and test the package.
7. Push source, integrity manifest, update manifest, and installer to GitHub.
8. Pin the manifest installer URL to the new installer commit if cache-safe testing is needed.

## Current Status

`2.1.0-2` is the current required release. It preserves offline-first Work data, settings, cache, templates, and Calendar records while adding the lag fix on top of session recovery and safer shutdown behavior.
