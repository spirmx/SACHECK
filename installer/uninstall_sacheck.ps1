$ErrorActionPreference = "Stop"

$InstallRoot = "C:\SACHECK"
$LegacyInstallRoot = Join-Path $env:LOCALAPPDATA "SACHECK"
$DesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "SA CHECK.lnk"
$LegacyDesktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "SACHECK.lnk"
$StartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "SA CHECK"
$LegacyStartMenuDir = Join-Path ([Environment]::GetFolderPath("Programs")) "SACHECK"

Get-Process SACHECK -ErrorAction SilentlyContinue | Stop-Process -Force

Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "SACHECK" -ErrorAction SilentlyContinue

if (Test-Path $DesktopShortcut) {
    Remove-Item -LiteralPath $DesktopShortcut -Force
}
if (Test-Path $LegacyDesktopShortcut) {
    Remove-Item -LiteralPath $LegacyDesktopShortcut -Force
}
if (Test-Path $StartMenuDir) {
    Remove-Item -LiteralPath $StartMenuDir -Recurse -Force
}
if (Test-Path $LegacyStartMenuDir) {
    Remove-Item -LiteralPath $LegacyStartMenuDir -Recurse -Force
}
if (Test-Path $InstallRoot) {
    Remove-Item -LiteralPath $InstallRoot -Recurse -Force
}
if (Test-Path $LegacyInstallRoot) {
    Remove-Item -LiteralPath $LegacyInstallRoot -Recurse -Force
}

Write-Host "SACHECK uninstalled." -ForegroundColor Green
