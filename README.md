# SA CHECK

Desktop Work Board for SA/IT work tracking.

Developer / Creator: HOYTURBRO  
Alias: Hoyturbro  
Publisher: HOYTURBRO

## Current Release

Version: `1.0.8 Stable`

This patch stabilizes Calendar event editing by removing nested picker popups and using standard dialog actions.

Latest changes:

- Required update through the GitHub manifest.
- Stabilized Calendar event dialog click handling.
- Removed nested DatePicker/TimePicker popups from inside the edit dialog.
- Moved Calendar event buttons back to standard AlertDialog actions.
- Added direct date/time validation so invalid values do not save.
- Calendar event save still uses `YYYY-MM-DD` and `HH:MM` values.
- Keeps previous calendar event data compatible.
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
- `README.md` - Git/Drive developer notes.
- `release/SA_CHECK_Installer.exe` - installer payload for users and in-app updates.

Before publishing a new update:

1. Update `APP_VERSION` in `ui/flet_dashboard.py`.
2. Add a new version entry in `VERSION_HISTORY`.
3. Update `sacheck_update.json`.
4. Build the installer.
5. Push source, manifest, and installer to GitHub.
6. Pin the manifest installer URL to the new installer commit if cache-safe testing is needed.

## Current Status

`1.0.8 Stable` uses a simpler Calendar event dialog with standard actions and direct date/time validation to avoid unclickable overlays.
