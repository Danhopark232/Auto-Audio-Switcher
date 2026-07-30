param(
    [string]$InstallDir = "$env:LOCALAPPDATA\AutoAudioSwitcher",
    [switch]$NoDesktopShortcut,
    [switch]$NoStartMenuShortcut,
    [switch]$ResetConfig
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[AutoAudioSwitcher] $Message"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceDir = Join-Path $scriptDir "AutoAudioSwitcher"
if (-not (Test-Path -LiteralPath $sourceDir)) {
    $sourceDir = Join-Path (Split-Path -Parent $scriptDir) "AutoAudioSwitcher"
}

$sourceExe = Join-Path $sourceDir "AutoAudioSwitcher.exe"
if (-not (Test-Path -LiteralPath $sourceExe)) {
    throw "AutoAudioSwitcher.exe was not found. Keep this installer next to the AutoAudioSwitcher folder from the distribution package."
}

if ([Environment]::OSVersion.Version.Major -lt 10) {
    throw "Auto Audio Switcher requires Windows 10 or Windows 11."
}

$InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$installRoot = [System.IO.Path]::GetPathRoot($InstallDir)
$normalizedInstallDir = $InstallDir.TrimEnd('\')
$forbiddenTargets = @(
    $installRoot,
    [System.IO.Path]::GetFullPath($env:USERPROFILE),
    [System.IO.Path]::GetFullPath($env:LOCALAPPDATA)
) | ForEach-Object { $_.TrimEnd('\') }
if ($forbiddenTargets -contains $normalizedInstallDir) {
    throw "Unsafe install directory: $InstallDir"
}

$requiredFiles = @(
    "AutoAudioSwitcher.exe",
    "_internal\python310.dll",
    "_internal\python3.dll",
    "_internal\nircmd.exe",
    "config.json"
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $sourceDir $relativePath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        throw "Required bundled runtime file is missing: $relativePath. Re-extract the distribution package and run the installer again."
    }
}

Write-Step "Bundled Python runtime found. No separate Python installation is required."
Write-Step "Installing to $InstallDir"

$installedExe = Join-Path $InstallDir "AutoAudioSwitcher.exe"
Get-Process -Name "AutoAudioSwitcher" -ErrorAction SilentlyContinue | Where-Object {
    try { $_.Path -and ([System.IO.Path]::GetFullPath($_.Path) -eq $installedExe) } catch { $false }
} | ForEach-Object {
    Write-Step "Closing the currently installed app."
    Stop-Process -Id $_.Id -Force
    $_.WaitForExit()
}

$existingConfig = Join-Path $InstallDir "config.json"
$backupConfig = $null
if ((Test-Path -LiteralPath $existingConfig) -and -not $ResetConfig) {
    $backupConfig = Join-Path $env:TEMP ("AutoAudioSwitcher_config_" + [guid]::NewGuid().ToString("N") + ".json")
    Copy-Item -LiteralPath $existingConfig -Destination $backupConfig -Force
    Write-Step "Existing config will be preserved."
}

if (-not (Test-Path -LiteralPath $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

Get-ChildItem -LiteralPath $InstallDir -Force | Where-Object { $_.Name -ne "logs" } | Remove-Item -Recurse -Force
Copy-Item -Path (Join-Path $sourceDir "*") -Destination $InstallDir -Recurse -Force

if ($backupConfig -and (Test-Path -LiteralPath $backupConfig)) {
    Copy-Item -LiteralPath $backupConfig -Destination $existingConfig -Force
    Remove-Item -LiteralPath $backupConfig -Force
}

$shell = New-Object -ComObject WScript.Shell

$programsDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$startShortcutPath = Join-Path $programsDir "Auto Audio Switcher.lnk"
if (-not $NoStartMenuShortcut) {
    $startShortcut = $shell.CreateShortcut($startShortcutPath)
    $startShortcut.TargetPath = $installedExe
    $startShortcut.WorkingDirectory = $InstallDir
    $startShortcut.IconLocation = "$installedExe,0"
    $startShortcut.Save()
    Write-Step "Start Menu shortcut created."
}

if (-not $NoDesktopShortcut) {
    $desktopShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Auto Audio Switcher.lnk"
    $desktopShortcut = $shell.CreateShortcut($desktopShortcutPath)
    $desktopShortcut.TargetPath = $installedExe
    $desktopShortcut.WorkingDirectory = $InstallDir
    $desktopShortcut.IconLocation = "$installedExe,0"
    $desktopShortcut.Save()
    Write-Step "Desktop shortcut created."
}

Write-Step "Install complete."
Write-Host ""
Write-Host "Installed app: $installedExe"
Write-Host "Python: bundled with the app, no system Python needed."
