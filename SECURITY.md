# Security

## Supported platform

Auto Audio Switcher supports 64-bit Windows 10 and Windows 11. The application
runs with the current user's privileges (`asInvoker`) and does not require
administrator access.

## Local data and privacy

The application does not include telemetry or upload runtime information.
Configuration, bounded diagnostic logs, cached program icons, and runtime
diagnostics are stored per user under:

`%LOCALAPPDATA%\AutoAudioSwitcher`

Logs can contain local audio device names, program names, and executable paths.
Review them before sharing them publicly.

## Distribution integrity

Release builds are self-contained and do not download or execute a Python
installer. Audio switching uses the bundled Python COM backend and does not
invoke a general-purpose third-party command utility. `release_manifest.json`
records the SHA-256 hash of the main executable. Public production releases
should be Authenticode-signed with a consistent verified publisher identity
before upload. Microsoft documents how signing and publisher reputation affect
SmartScreen at:

https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation

## Reporting a vulnerability

Do not include private device names, local paths, or complete logs in a public
issue. Open a GitHub security advisory for vulnerabilities when that feature is
available for the repository; otherwise open a minimal issue asking the
maintainer for a private reporting channel.
