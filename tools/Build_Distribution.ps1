param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$Version = "1.1.0",
    [string]$SourceDir = "",
    [string]$OutputDir = "",
    [switch]$Use7Zip
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$dist = if ($OutputDir) { [System.IO.Path]::GetFullPath($OutputDir) } else { Join-Path $ProjectRoot "dist" }
if (-not (Test-Path -LiteralPath $dist)) {
    New-Item -ItemType Directory -Path $dist | Out-Null
}
$source = if ($SourceDir) { [System.IO.Path]::GetFullPath($SourceDir) } else { Join-Path $dist "AutoAudioSwitcher" }
$installerDir = Join-Path $ProjectRoot "installer"
$stageParent = Join-Path $dist "_zip_stage"
$stage = Join-Path $stageParent "release"
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
New-Item -ItemType Directory -Path $stage | Out-Null
Copy-Item -Path (Join-Path $source "*") -Destination $stage -Recurse -Force

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

Copy-Item -LiteralPath (Join-Path $installerDir "Install_AutoAudioSwitcher.ps1") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $installerDir "Install_AutoAudioSwitcher.bat") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "README.md") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "CHANGELOG.md") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot "SECURITY.md") -Destination $stage -Force

$diagnosticsDir = Join-Path $stageParent "diagnostics"
$stagedExe = Join-Path $stage "AutoAudioSwitcher.exe"
$diagnosticsArguments = @("--diagnostics", ('"--diagnostics-dir={0}"' -f $diagnosticsDir))
$diagnosticsProcess = Start-Process -FilePath $stagedExe -ArgumentList $diagnosticsArguments -WindowStyle Hidden -Wait -PassThru
if ($diagnosticsProcess.ExitCode -ne 0) {
    throw "Packaged runtime diagnostics failed with exit code $($diagnosticsProcess.ExitCode)."
}
$diagnosticsReport = Join-Path $diagnosticsDir "runtime_diagnostics.json"
if (-not (Test-Path -LiteralPath $diagnosticsReport)) {
    throw "Packaged runtime diagnostics did not create a report."
}
$diagnostics = Get-Content -LiteralPath $diagnosticsReport -Raw | ConvertFrom-Json
if (-not $diagnostics.ok -or -not $diagnostics.frozen) {
    throw "Packaged runtime diagnostics reported an invalid self-contained build."
}

$releaseManifest = [ordered]@{
    product = "Auto Audio Switcher"
    version = $Version
    architecture = "Windows x64"
    self_contained = $true
    python_install_required = $false
    executable_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $stagedExe).Hash
} | ConvertTo-Json
[System.IO.File]::WriteAllText((Join-Path $stage "release_manifest.json"), $releaseManifest + [Environment]::NewLine, $utf8NoBom)

$signature = Get-AuthenticodeSignature -LiteralPath $stagedExe
if ($signature.Status -ne "Valid") {
    Write-Warning "AutoAudioSwitcher.exe is not Authenticode-signed. Sign release files before a public production launch to reduce SmartScreen friction."
}

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$sevenZip = Get-Command 7z.exe -ErrorAction SilentlyContinue
if ($Use7Zip -and $sevenZip) {
    Push-Location $stage
    try {
        $archiveItemNames = @(Get-ChildItem -LiteralPath $stage -Force | Select-Object -ExpandProperty Name)
        & $sevenZip.Source a -tzip -mx=9 $zipPath $archiveItemNames | Out-Host
    } finally {
        Pop-Location
    }
} else {
    $archiveItems = @(Get-ChildItem -LiteralPath $stage -Force | Select-Object -ExpandProperty FullName)
    Compress-Archive -LiteralPath $archiveItems -DestinationPath $zipPath -CompressionLevel Optimal
}

Remove-Item -LiteralPath $stageParent -Recurse -Force
$zip = Get-Item -LiteralPath $zipPath
$zipHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash
Write-Host ("SHA256: {0}" -f $zipHash)
$zip
