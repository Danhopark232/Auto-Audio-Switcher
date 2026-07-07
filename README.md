# Auto Audio Switcher

Auto Audio Switcher is a Windows desktop utility that switches the default audio
output between a speaker device and a headset device based on the programs you
run. It is designed for game-focused workflows where some apps should use a
headset, while the desktop can return to speakers afterward.

## Current Version

The current UI version focuses on faster audio switching, a compact mini view,
and clearer per-program control.

### Main Features

- **Speaker / Headset output profiles**: choose one Windows output device for
  speaker mode and one for headset mode.
- **Unified Program List**: programs are managed in a single list instead of
  separate Ask and Auto lists.
- **Ask / Auto toggle per program**: each program row can be switched between:
  - **Ask**: shows a small confirmation prompt before changing audio output.
  - **Auto**: changes the audio output immediately when the program is detected.
- **Per-program target output**: each program can target either Speaker or
  Headset.
- **Output Switch Hotkey**: configure a hotkey to manually toggle between
  Speaker and Headset output.
- **Mini view**: a small bottom-screen control panel shows detected programs,
  audio switching status, and quick Speaker / Headset buttons.
- **First-run guide**: new users are guided through output selection and the
  Ask / Auto behavior.
- **Startup option**: the app can be configured to run when Windows starts.
- **Runtime logs**: logs are saved under `logs/auto_audio_switcher.log` to help
  diagnose intermittent detection, prompt, mini-view, and audio-switch issues.

## Recent UI Behavior

- The mini view animates from the bottom of the screen and hides after
  notifications finish.
- Ask prompts can be answered with the mouse, `Enter` for Yes, or `Esc` for No.
- Ask prompts now force-close correctly even if the mini view had previously
  been pinned by dragging.
- The settings window uses a two-column layout: settings on the left and the
  program list on the right.
- The Add Running Program dialog opens with `Recent`, `A-Z`, and `Resource`
  sorting, with Recent selected by default.

## Requirements

- Windows 10 or Windows 11
- Packaged EXE build for normal users
- Python environment only when running from source

## Notes

This project is actively being refined around real runtime behavior. If audio
switching, prompt dismissal, or mini-view hiding behaves unexpectedly, check the
latest log file in `logs/` and include the surrounding timestamp when reporting
the issue.
