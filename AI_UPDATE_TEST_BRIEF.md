# Gemini / Antigravity Brief

Check SA CHECK update flow.

Need:
- Read Google Drive folder.
- Prefer `sacheck_update.json`.
- If manifest missing, detect latest version from file names like `V1.0.2`.
- Use installer `.exe` in same folder.
- Never expose Drive link in UI.
- Keep user cache/work folders during update.

Test:
- Folder has manifest + installer.
- Folder has only versioned zip/exe.
- Offline mode skips update check.
