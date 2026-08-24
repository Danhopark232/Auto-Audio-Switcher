param(
    [string]$InstallDir = "$env:LOCALAPPDATA\Programs\AutoAudioSwitcher",
    [switch]$NoDesktopShortcut,
    [switch]$NoStartMenuShortcut,
    [switch]$ResetConfig
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step {
    param([string]$Message)
    Write-Host "[AutoAudioSwitcher] $Message"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceCandidates = @(
    $scriptDir,
    (Join-Path $scriptDir "AutoAudioSwitcher"),
    (Join-Path (Split-Path -Parent $scriptDir) "AutoAudioSwitcher")
)
$sourceDir = $sourceCandidates | Where-Object {
    Test-Path -LiteralPath (Join-Path $_ "AutoAudioSwitcher.exe")
} | Select-Object -First 1

if (-not $sourceDir) {
    throw "AutoAudioSwitcher.exe was not found. Extract the complete distribution ZIP before running the installer."
}
$sourceExe = Join-Path $sourceDir "AutoAudioSwitcher.exe"

if ([Environment]::OSVersion.Version.Major -lt 10) {
    throw "Auto Audio Switcher requires Windows 10 or Windows 11."
}

$InstallDir = [System.IO.Path]::GetFullPath($InstallDir)
$sourceDir = [System.IO.Path]::GetFullPath($sourceDir)
$installRoot = [System.IO.Path]::GetPathRoot($InstallDir)
$normalizedInstallDir = $InstallDir.TrimEnd('\')
$normalizedSourceDir = $sourceDir.TrimEnd('\')
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
    "_internal\python3.dll"
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $sourceDir $relativePath
    if (-not (Test-Path -LiteralPath $fullPath)) {
        throw "Required bundled runtime file is missing: $relativePath. Re-extract the distribution package and run the installer again."
    }
}

Write-Step "Bundled Python runtime found. No separate Python installation is required."
Write-Step "Installing to $InstallDir"
$inPlaceInstall = $normalizedSourceDir -eq $normalizedInstallDir

$installedExe = Join-Path $InstallDir "AutoAudioSwitcher.exe"
$installMarker = Join-Path $InstallDir ".auto-audio-switcher-install"
$legacyOwnedInstall = (Test-Path -LiteralPath $installedExe) -and (Test-Path -LiteralPath (Join-Path $InstallDir "_internal\python310.dll"))
if ((Test-Path -LiteralPath $InstallDir) -and -not $inPlaceInstall -and -not (Test-Path -LiteralPath $installMarker) -and -not $legacyOwnedInstall) {
    $existingItems = @(Get-ChildItem -LiteralPath $InstallDir -Force -ErrorAction SilentlyContinue)
    if ($existingItems.Count -gt 0) {
        throw "The selected folder is not an Auto Audio Switcher installation. Choose an empty folder to protect unrelated files: $InstallDir"
    }
}

Get-Process -Name "AutoAudioSwitcher" -ErrorAction SilentlyContinue | Where-Object {
    try { $_.Path -and ([System.IO.Path]::GetFullPath($_.Path) -eq $installedExe) } catch { $false }
} | ForEach-Object {
    Write-Step "Closing the currently installed app."
    Stop-Process -Id $_.Id -Force
    $_.WaitForExit()
}

$dataDir = Join-Path $env:LOCALAPPDATA "AutoAudioSwitcher"
$existingConfig = Join-Path $dataDir "config.json"
if ($inPlaceInstall) {
    Write-Step "The extracted app is already in the selected install directory; keeping files in place."
} else {
    $backupConfig = $null
    if ((Test-Path -LiteralPath $existingConfig) -and -not $ResetConfig) {
        $backupConfig = Join-Path $env:TEMP ("AutoAudioSwitcher_config_" + [guid]::NewGuid().ToString("N") + ".json")
        Copy-Item -LiteralPath $existingConfig -Destination $backupConfig -Force
        Write-Step "Existing config will be preserved."
    }

    if (-not (Test-Path -LiteralPath $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir | Out-Null
    }

    $ownedItems = @(
        "AutoAudioSwitcher.exe",
        "_internal",
        "README.md",
        "SECURITY.md",
        "release_manifest.json",
        "Install_AutoAudioSwitcher.ps1",
        "Install_AutoAudioSwitcher.bat"
    )
    foreach ($ownedItem in $ownedItems) {
        $ownedPath = Join-Path $InstallDir $ownedItem
        if (Test-Path -LiteralPath $ownedPath) {
            Remove-Item -LiteralPath $ownedPath -Recurse -Force
        }
    }
    foreach ($appItem in $ownedItems) {
        $appItemPath = Join-Path $sourceDir $appItem
        if (Test-Path -LiteralPath $appItemPath) {
            Copy-Item -LiteralPath $appItemPath -Destination $InstallDir -Recurse -Force
        }
    }

    [System.IO.File]::WriteAllText($installMarker, "AutoAudioSwitcher`r`n", (New-Object System.Text.UTF8Encoding($false)))

    if ($backupConfig -and (Test-Path -LiteralPath $backupConfig)) {
        if (-not (Test-Path -LiteralPath $dataDir)) {
            New-Item -ItemType Directory -Path $dataDir | Out-Null
        }
        Copy-Item -LiteralPath $backupConfig -Destination $existingConfig -Force
        Remove-Item -LiteralPath $backupConfig -Force
    }
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
