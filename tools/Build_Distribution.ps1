param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$Version = "1.0.1",
    [string]$SourceDir = "",
    [switch]$Use7Zip
)

$ErrorActionPreference = "Stop"

$dist = Join-Path $ProjectRoot "dist"
$source = if ($SourceDir) { [System.IO.Path]::GetFullPath($SourceDir) } else { Join-Path $dist "AutoAudioSwitcher" }
$installerDir = Join-Path $ProjectRoot "installer"
$stageParent = Join-Path $dist "_zip_stage"
$stage = Join-Path $stageParent "AutoAudioSwitcher"
$zipPath = Join-Path $dist ("AutoAudioSwitcher-v{0}-Windows-x64.zip" -f $Version)

if (-not (Test-Path -LiteralPath (Join-Path $source "AutoAudioSwitcher.exe"))) {
    throw "Build output was not found: $source"
}

$distResolved = (Resolve-Path $dist).Path
if (Test-Path -LiteralPath $stageParent) {
    $stageResolved = (Resolve-Path $stageParent).Path
    if (-not $stageResolved.StartsWith($distResolved, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe stage path: $stageResolved"
    }
    Remove-Item -LiteralPath $stageParent -Recurse -Force
}

New-Item -ItemType Directory -Path $stageParent | Out-Null
Copy-Item -LiteralPath $source -Destination $stageParent -Recurse -Force

$logsPath = Join-Path $stage "logs"
if (Test-Path -LiteralPath $logsPath) {
    Remove-Item -LiteralPath $logsPath -Recurse -Force
}

$cleanConfig = [ordered]@{
    headset_name = ""
    headset_id = ""
    speaker_name = ""
    speaker_id = ""
    auto_list = @()
    ask_list = @()
    program_order = @()
    start_with_windows = $false
    settings_geometry = ""
    output_switch_hotkey = ""
    ask_timeout_seconds = 15
    mini_notification_seconds = 5
    onboarding_completed = $false
    language = "en"
} | ConvertTo-Json -Depth 8

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $stage "config.json"), $cleanConfig + [Environment]::NewLine, $utf8NoBom)
$internalConfig = Join-Path $stage "_internal\config.json"
if (Test-Path -LiteralPath $internalConfig) {
    [System.IO.File]::WriteAllText($internalConfig, $cleanConfig + [Environment]::NewLine, $utf8NoBom)
}

Copy-Item -LiteralPath (Join-Path $installerDir "Install_AutoAudioSwitcher.ps1") -Destination $stageParent -Force
Copy-Item -LiteralPath (Join-Path $installerDir "Install_AutoAudioSwitcher.bat") -Destination $stageParent -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "README.md") -Destination $stageParent -Force

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$sevenZip = Get-Command 7z.exe -ErrorAction SilentlyContinue
if ($Use7Zip -and $sevenZip) {
    Push-Location $stageParent
    try {
        & $sevenZip.Source a -tzip -mx=9 $zipPath "AutoAudioSwitcher" "Install_AutoAudioSwitcher.ps1" "Install_AutoAudioSwitcher.bat" "README.md" | Out-Host
    } finally {
        Pop-Location
    }
} else {
    Compress-Archive -LiteralPath $stage, (Join-Path $stageParent "Install_AutoAudioSwitcher.ps1"), (Join-Path $stageParent "Install_AutoAudioSwitcher.bat"), (Join-Path $stageParent "README.md") -DestinationPath $zipPath -CompressionLevel Optimal
}

Remove-Item -LiteralPath $stageParent -Recurse -Force
Get-Item -LiteralPath $zipPath
