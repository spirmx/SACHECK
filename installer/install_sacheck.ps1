$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ReleaseRoot = Join-Path $ProjectRoot "release"
$InstallRoot = "C:\SACHECK"
$AppRoot = Join-Path $InstallRoot "app"
$LegacyInstallRoot = Join-Path $env:LOCALAPPDATA "SACHECK"
$LegacyAppRoot = Join-Path $LegacyInstallRoot "app"
$ExeName = "SACHECK.exe"
$SourceExe = Join-Path $ReleaseRoot $ExeName
$TargetExe = Join-Path $AppRoot $ExeName
$ShortcutName = "SA CHECK.lnk"
$LegacyShortcutName = "SACHECK.lnk"
$AppUserModelId = "Hoyturbro.SACHECK.Desktop"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) $ShortcutName
$LegacyDesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) $LegacyShortcutName
$StartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "SA CHECK"
$LegacyStartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "SACHECK"
$StartMenuShortcut = Join-Path $StartMenuDir $ShortcutName
$LegacyStartMenuShortcut = Join-Path $LegacyStartMenuDir $LegacyShortcutName
$TaskbarDir = Join-Path $env:APPDATA "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
$TaskbarShortcut = Join-Path $TaskbarDir $ShortcutName

if (!(Test-Path $SourceExe)) {
    throw "Cannot find $SourceExe. Build the app first."
}

New-Item -ItemType Directory -Path $AppRoot -Force | Out-Null
New-Item -ItemType Directory -Path $StartMenuDir -Force | Out-Null
New-Item -ItemType Directory -Path $TaskbarDir -Force | Out-Null

$ExistingSettingsFile = Join-Path $AppRoot "data\app_settings.json"
$LegacySettingsFile = Join-Path $LegacyAppRoot "data\app_settings.json"
$ExistingSettings = $null
if (Test-Path $ExistingSettingsFile) {
    try {
        $ExistingSettings = Get-Content -LiteralPath $ExistingSettingsFile -Raw | ConvertFrom-Json
    } catch {
        $ExistingSettings = $null
    }
} elseif (Test-Path $LegacySettingsFile) {
    try {
        $ExistingSettings = Get-Content -LiteralPath $LegacySettingsFile -Raw | ConvertFrom-Json
    } catch {
        $ExistingSettings = $null
    }
}

foreach ($item in @("assets", "config", "core", "stores", "ui", "tools", "cache", "data")) {
    $source = Join-Path $ReleaseRoot $item
    $target = Join-Path $AppRoot $item
    if (Test-Path $source) {
        Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
    }
}

Copy-Item -LiteralPath (Join-Path $ReleaseRoot "category_config.py") -Destination (Join-Path $AppRoot "category_config.py") -Force
Copy-Item -LiteralPath $SourceExe -Destination $TargetExe -Force

$IconPath = Join-Path $AppRoot "assets\app\app.ico"
$WshShell = New-Object -ComObject WScript.Shell
foreach ($shortcutPath in @($DesktopShortcut, $StartMenuShortcut, $TaskbarShortcut)) {
    $shortcut = $WshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $TargetExe
    $shortcut.WorkingDirectory = $AppRoot
    if (Test-Path $IconPath) {
        $shortcut.IconLocation = $IconPath
    }
    $shortcut.Save()
}

foreach ($badShortcut in Get-ChildItem -LiteralPath $TaskbarDir -Filter "*.lnk" -ErrorAction SilentlyContinue) {
    if ($badShortcut.Name -like "Flet*" -or $badShortcut.Name -like "*Flet*") {
        Remove-Item -LiteralPath $badShortcut.FullName -Force -ErrorAction SilentlyContinue
    }
}

foreach ($shortcutPath in @($LegacyDesktopShortcut, $LegacyStartMenuShortcut)) {
    if (Test-Path $shortcutPath) {
        Remove-Item -LiteralPath $shortcutPath -Force
    }
}
if ((Test-Path $LegacyStartMenuDir) -and -not (Get-ChildItem -LiteralPath $LegacyStartMenuDir -Force -ErrorAction SilentlyContinue)) {
    Remove-Item -LiteralPath $LegacyStartMenuDir -Force
}

$SettingsDir = Join-Path $AppRoot "data"
$SettingsFile = Join-Path $SettingsDir "app_settings.json"
New-Item -ItemType Directory -Path $SettingsDir -Force | Out-Null
$settings = @{}
if (Test-Path $SettingsFile) {
    try {
        $copiedSettings = Get-Content -LiteralPath $SettingsFile -Raw | ConvertFrom-Json
        foreach ($property in $copiedSettings.PSObject.Properties) {
            $settings[$property.Name] = $property.Value
        }
    } catch {
    }
}
$settings["theme"] = "Light"
if ($ExistingSettings) {
    foreach ($property in $ExistingSettings.PSObject.Properties) {
        $settings[$property.Name] = $property.Value
    }
}
$settings["launch_on_startup"] = $true
$settings | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $SettingsFile -Encoding UTF8

$RunKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Set-ItemProperty -Path $RunKey -Name "SACHECK" -Value "`"$TargetExe`""

Write-Host "SACHECK installed to $AppRoot" -ForegroundColor Green
Write-Host "Desktop shortcut: $DesktopShortcut" -ForegroundColor Green
Write-Host "Start Menu shortcut: $StartMenuShortcut" -ForegroundColor Green
Write-Host "Auto Run enabled for Windows startup" -ForegroundColor Green
