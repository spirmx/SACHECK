# SA CHECK Update Channel

Current production version: `1.0.0`

SA CHECK is offline-first. Normal work, Work folders, settings, and user cache must remain local and usable without internet. Online access is used only for checking and downloading app updates.

## User-facing rule

Do not expose the update hosting URL in the app UI. Users should only see generic labels such as:

- `Update available`
- `Downloading update package`
- `Installer is launching`
- `Please contact the app publisher`

## Release manifest

For future versions, publish a manifest named:

```text
sacheck_update.json
```

Use `sacheck_update_manifest.example.json` as the template:

```json
{
  "version": "1.0.1",
  "release_date": "2026-06-20",
  "required": false,
  "installer_url": "DIRECT_DOWNLOAD_URL_TO_SA_CHECK_INSTALLER_EXE",
  "notes": [
    "Short note for users.",
    "Another change."
  ]
}
```

## Update behavior

- If there is no internet, the app stays offline and never blocks work.
- If `offline_mode` is enabled, update checks are skipped.
- If `update_checks_enabled` is disabled, update checks are skipped.
- The update button appears in the sidebar only when a newer version exists.
- The installer runs over `C:\SACHECK` and must update app system files only.
- Do not clear user settings, selected Work folders, reports, templates, or Work data.

## Forced update rules

The app forces the update prompt when any of these is true:

- Manifest has `"required": true`.
- User skipped the same update 3 times.
- Installed version is 3 patch versions behind, for example `1.0.0` to `1.0.3`.
- Major/minor version is newer, for example `1.0.0` to `1.1.0`.
