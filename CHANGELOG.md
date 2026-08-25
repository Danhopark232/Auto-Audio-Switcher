# Changelog

## 1.1.0 — 2026-08-25

### Highlights

- Unified control heights, panel rounding, row rounding, and spacing throughout
  the settings, program, onboarding, and edit interfaces.
- Improved settings-window fitting across Windows resolutions and DPI scales.
- Moved settings, bounded logs, and cached program icons to the current user's
  `%LOCALAPPDATA%\AutoAudioSwitcher` directory with legacy-config migration.
- Added atomic configuration saves, a backup fallback, and a configuration size
  limit to reduce corruption risk.
- Removed the general-purpose NirCmd executable and use the bundled Windows Core
  Audio COM backend directly.
- Added a non-interactive packaged-runtime diagnostic command and SHA-256 release
  manifest.
- Hardened the optional per-user installer so it preserves user settings and
  refuses to clear unrecognized non-empty directories.
- Added pinned build dependencies, automated vulnerability auditing, Windows CI,
  and compatibility regression tests.

### Distribution

- Supports 64-bit Windows 10 and Windows 11.
- Python and required libraries are bundled; no separate runtime installation is
  required.
- `AutoAudioSwitcher.exe` is available at the top level of the release ZIP.
