# SA CHECK

Desktop Work Board for SA/IT work tracking.

Developer / Creator: HOYTURBRO  
Alias: Hoyturbro  
Publisher: HOYTURBRO

## Current Release

Version: `1.0.9-01 Abillity`

This release adds a safe in-app refresh to the Sync button while keeping the startup loader and update checks reliable.

`1.0.9-01 Abillity` refreshes Work data and settings without closing the app, checks Git for updates, and keeps the current screen mounted throughout the operation.

Latest changes:

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

`1.0.9-01 Abillity` adds safe in-app refresh and fixes the Settings Credits buttons while preserving offline-first Work data, settings, and cache.
