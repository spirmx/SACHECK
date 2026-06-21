SA CHECK V1.0.2 GitHub update package

Repo:
https://github.com/spirmx/SACHECK

Update platform:
- App reads https://raw.githubusercontent.com/spirmx/SACHECK/main/sacheck_update.json
- Installer URL points to GitHub Releases:
  https://github.com/spirmx/SACHECK/releases/download/v1.0.2/SA_CHECK_Installer.exe
- Google Drive update flow was removed from the app.

Files:
- SA_CHECK_Installer.exe : user installer/updater
- sacheck_update.json : update manifest for GitHub raw
- SACHECK_SOURCE_PYTHON_ONLY_V1.0.2_GITHUB.zip : source archive
- SACHECK_SOURCE_PYTHON_ONLY_V1.0.2_GITHUB : extracted source for development/Git upload

V1.0.2 changes:
- Theme has Apply theme button.
- Theme dropdown/switch no longer changes the app immediately.
- Update system uses GitHub manifest by default.

Install/update keeps user Work folder, settings, and cache.
