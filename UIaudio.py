import hashlib
import json
import logging
import math
import os
import queue
import shutil
import sys
import threading
import time
import ctypes


def enable_windows_dpi_awareness():
    if sys.platform != "win32":
        return "not-windows"
    try:
        result = ctypes.windll.shcore.SetProcessDpiAwareness(2)
        if result in (0, -2147024891):  # S_OK or E_ACCESSDENIED (already configured)
            return "per-monitor"
    except Exception:
        pass
    try:
        if ctypes.windll.user32.SetProcessDPIAware():
            return "system"
    except Exception:
        pass
    return "unavailable"


WINDOWS_DPI_AWARENESS = enable_windows_dpi_awareness()

import tkinter as tk
import winreg
from ctypes import wintypes
from logging.handlers import RotatingFileHandler
from tkinter import filedialog, font, messagebox

import customtkinter as ctk
import PIL
import psutil
import pystray
import win32con
import win32gui
import win32ui
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageTk


# This app mixes CustomTkinter widgets with pixel-rendered Tk canvases and PIL
# images.  CustomTkinter's live per-monitor DPI updates only resize its own
# widgets, leaving those pixel assets at their previous scale.  Keep one
# coherent scale for the lifetime of the process; it is calculated explicitly
# from the launch monitor and its work area below.
ctk.deactivate_automatic_dpi_awareness()


APP_NAME = "AutoAudioSwitcher"
APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)


def get_app_data_dir(app_dir=APP_DIR, frozen=None, local_app_data=None):
    frozen = getattr(sys, "frozen", False) if frozen is None else bool(frozen)
    if not frozen:
        return app_dir
    local_app_data = local_app_data if local_app_data is not None else os.environ.get("LOCALAPPDATA", "")
    return os.path.join(local_app_data, APP_NAME) if local_app_data else app_dir


APP_DATA_DIR = get_app_data_dir()
LEGACY_CONFIG_FILE = os.path.join(APP_DIR, "config.json")
CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")
CONFIG_BACKUP_FILE = os.path.join(APP_DATA_DIR, "config.json.bak")
LOG_DIR = os.path.join(APP_DATA_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "auto_audio_switcher.log")
SETTINGS_EVENT_LOG_FILE = os.path.join(LOG_DIR, "settings_events.log")
APP_ICON_FILE = os.path.join(RESOURCE_DIR, "assets", "app_icon.png")
APP_ICON_ICO_FILE = os.path.join(RESOURCE_DIR, "assets", "app_icon.ico")
ICON_DIR = os.path.join(RESOURCE_DIR, "assets", "icons")
PROGRAM_ICON_CACHE_DIR = os.path.join(APP_DATA_DIR, "program_icons")
APP_VERSION = "1.1.0"
WINDOWS_APP_ID = "AutoAudioSwitcher.AutoAudioSwitcher"
SINGLE_INSTANCE_MUTEX_NAME = "Local\\AutoAudioSwitcher.SingleInstance"
ERROR_ALREADY_EXISTS = 183
CHECK_INTERVAL_SECONDS = 1
CURRENT_AUDIO_SYNC_INTERVAL_SECONDS = 5
DEVICE_CACHE_REFRESH_INTERVAL_SECONDS = 2
KEYBOARD_EVENTS_PER_TICK = 8
PROGRAM_EXIT_GRACE_SECONDS = 1
ASK_TIMEOUT_SECONDS = 15
ASK_TIMEOUT_OPTION_SECONDS = [5, 15, 30]
MINI_NOTIFICATION_SECONDS = 5
MINI_NOTIFICATION_OPTION_SECONDS = [1, 2, 3, 4, 5, 10, 15, 20, 25, 30, 45, 60]
STARTUP_MINI_POPUP_SECONDS = 3
SHOW_STARTUP_ONBOARDING_EVERY_RUN = False
MINI_WIDTH = 546
MINI_HEIGHT = 94
MINI_ANIMATION_STEPS = 18
MINI_ANIMATION_INTERVAL_MS = 10
SETTINGS_DEFAULT_WIDTH = 1132
SETTINGS_DEFAULT_HEIGHT = 668
SETTINGS_MIN_WIDTH = 1132
SETTINGS_MIN_HEIGHT = 668
DISPLAY_FIT_MARGIN_X = 48
DISPLAY_FIT_MARGIN_Y = 72
MIN_EFFECTIVE_UI_SCALE = 0.5
SETTINGS_SAVE_GAP = 10
SETTINGS_DEVICE_GAP = 12
SETTINGS_LEFT_WIDTH = 300
SETTINGS_RIGHT_WIDTH = 800
SETTINGS_DEVICE_WIDTH = 272
SETTINGS_DROPDOWN_MENU_MIN_CHARS = 36
SETTINGS_HOTKEY_HEIGHT = 37
UI_RADIUS_CONTROL = 8
UI_RADIUS_PANEL = 12
UI_RADIUS_ROW = 8
UI_SPACE_XS = 4
UI_SPACE_SM = 8
UI_SPACE_MD = 12
UI_SPACE_LG = 16
UI_CONTROL_HEIGHT_COMPACT = 30
UI_CONTROL_HEIGHT = 38
UI_CONTROL_HEIGHT_LARGE = 40
PROGRAM_ICON_SIZE = 32
MINI_DETECTED_ICON_SIZE = 52
MINI_DETECTED_ICON_SOURCE_SIZE = 128
MINI_DETECTED_ICON_CORNER_RADIUS = 7
PROGRAM_LIST_NAME_FONT_SIZE = 11
MINI_DEVICE_BUTTON_WIDTH = 52
MINI_DEVICE_BUTTON_HEIGHT = 42
MINI_DEVICE_BUTTON_GAP = 6
AUDIO_SWITCHING_BUTTON_WIDTH = MINI_DEVICE_BUTTON_WIDTH * 2 + MINI_DEVICE_BUTTON_GAP
ACTIVE_GRADIENT_START = "#2563E8"
ACTIVE_GRADIENT_END = "#153782"
MINI_BUTTON_ACTIVE_GRADIENT_START = ACTIVE_GRADIENT_START
MINI_BUTTON_ACTIVE_GRADIENT_END = ACTIVE_GRADIENT_END
INACTIVE_BUTTON_GRADIENT_START = (60, 60, 60, 102)
INACTIVE_BUTTON_GRADIENT_END = (60, 60, 60, 102)
INACTIVE_BUTTON_BORDER = (82, 82, 82, 77)
SETTINGS_CONTROL_DIVIDER = (24, 24, 24, 255)
INACTIVE_ICON_GRADIENT_START = (255, 255, 255, 176)
INACTIVE_ICON_GRADIENT_END = (255, 255, 255, 102)
INACTIVE_BUTTON_HOVER_GRADIENT_START = (0, 149, 255, 105)
INACTIVE_BUTTON_HOVER_GRADIENT_END = (0, 149, 255, 105)
INACTIVE_BUTTON_HOVER_BORDER = (0, 145, 217, 77)
INACTIVE_ICON_HOVER_GRADIENT_START = (255, 255, 255, 230)
INACTIVE_ICON_HOVER_GRADIENT_END = (255, 255, 255, 153)
MINI_BG_GRADIENT_START = "#212121"
MINI_BG_GRADIENT_END = "#212121"
MINI_BG_FALLBACK = "#212121"
MARQUEE_FADE_WIDTH = 15
MARQUEE_STEP_PX = 1
MARQUEE_INTERVAL_MS = 45
MARQUEE_EDGE_PAUSE_TICKS = 22
RUNNING_PROGRAM_CPU_SAMPLE_SECONDS = 0.25
MIN_RUNNING_PROGRAM_CPU_PERCENT = 0.5
MIN_RUNNING_PROGRAM_MEMORY_MB = 50
CPU_CORE_COUNT = max(1, psutil.cpu_count(logical=True) or 1)
LOG_RETENTION_DAYS = 14
LOG_CLEANUP_INTERVAL_MS = 6 * 60 * 60 * 1000
MAIN_LOG_MAX_BYTES = 750_000
MAIN_LOG_BACKUP_COUNT = 3
SETTINGS_LOG_MAX_BYTES = 250_000
SETTINGS_LOG_BACKUP_COUNT = 2
MAX_CONFIG_BYTES = 2_000_000
IGNORED_RUNNING_PROGRAM_NAMES = {
    "idle",
    "system idle process",
}
WINDOW_BG = "#171717"
TITLE_BAR_BG = "#0D0D0D"
SURFACE_BG = "#101010"
PANEL_BG = "#111111"
SETTINGS_OUTER_BG = "#212121"
SETTINGS_PANEL_BG = "#181818"
SETTINGS_DROPDOWN_BG = "#333333"
SETTINGS_PANEL_RADIUS = UI_RADIUS_PANEL
SETTINGS_ROW_BG = "#1C1C1C"
SETTINGS_GRADIENT_END = SETTINGS_OUTER_BG
SETTINGS_DEVICE_ACTIVE_START = ACTIVE_GRADIENT_START
SETTINGS_DEVICE_ACTIVE_END = ACTIVE_GRADIENT_END
CONTROL_BG = "#333333"
CONTROL_HOVER = "#414141"
FIELD_BG = "#303335"
FIELD_BORDER = "#4A4D50"
ACTIVE_COLOR = ACTIVE_GRADIENT_START
ACTIVE_HOVER_COLOR = "#1D4ED8"
DEVICE_ACTIVE_COLOR = ACTIVE_GRADIENT_START
DEVICE_INACTIVE_COLOR = "#20073F"
SPI_GETWORKAREA = 0x0030
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2
GA_ROOT = 2
MONITOR_DEFAULTTONEAREST = 2
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
LLKHF_INJECTED = 0x10
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
HOTKEY_NONE_LABEL = "None"
HOTKEY_OPTIONS = [HOTKEY_NONE_LABEL] + [f"F{index}" for index in range(1, 25)] + [chr(code) for code in range(ord("A"), ord("Z") + 1)]
HOTKEY_VK = {
    **{f"F{index}": 0x6F + index for index in range(1, 13)},
    **{f"F{index}": 0x7B + (index - 12) for index in range(13, 25)},
    **{chr(code): code for code in range(ord("A"), ord("Z") + 1)},
}
DEFAULT_LANGUAGE = "en"
LANGUAGE_OPTIONS = {
    "en": "English",
    "ko": "한국어",
}
LANGUAGE_TEXT = {
    "settings": {"en": "Settings", "ko": "설정"},
    "refresh": {"en": "Refresh outputs", "ko": "출력 새로고침"},
    "refreshing": {"en": "Refreshing...", "ko": "새로고침 중..."},
    "speaker": {"en": "Speaker", "ko": "스피커"},
    "headset": {"en": "Headset", "ko": "헤드셋"},
    "ask_duration": {"en": "Ask duration", "ko": "확인창 유지 시간"},
    "mini_duration": {"en": "Mini duration", "ko": "미니창 표시 시간"},
    "run_on_startup": {"en": "Run on Start up", "ko": "Windows 시작 시 실행"},
    "language": {"en": "Language", "ko": "언어"},
    "save": {"en": "Save", "ko": "저장"},
    "program_list": {"en": "Program List", "ko": "프로그램 목록"},
    "no_program_detected": {"en": "No Program Detected", "ko": "감지된 프로그램 없음"},
    "changing_audio_output": {"en": "Changing audio output...", "ko": "오디오 출력 변경 중..."},
    "audio_output_changed": {"en": "Audio output changed", "ko": "오디오 출력 변경됨"},
    "switch_to": {"en": "Switch to {mode}?", "ko": "{mode} 모드로 변경할까요?"},
    "yes": {"en": "Yes", "ko": "예"},
    "no": {"en": "No", "ko": "아니오"},
}


def normalize_language_code(value):
    if not isinstance(value, str):
        return DEFAULT_LANGUAGE
    cleaned = value.strip().lower()
    if cleaned in LANGUAGE_OPTIONS:
        return cleaned
    if cleaned in ("english", "en-us", "en_us"):
        return "en"
    if cleaned in ("korean", "ko-kr", "ko_kr", "한국어"):
        return "ko"
    return DEFAULT_LANGUAGE


def language_label_for_code(value):
    return LANGUAGE_OPTIONS.get(normalize_language_code(value), LANGUAGE_OPTIONS[DEFAULT_LANGUAGE])


def language_code_from_label(value):
    for code, label in LANGUAGE_OPTIONS.items():
        if value == label:
            return code
    return normalize_language_code(value)


def translate_text(language, key, **kwargs):
    template = LANGUAGE_TEXT.get(key, {}).get(normalize_language_code(language), LANGUAGE_TEXT.get(key, {}).get(DEFAULT_LANGUAGE, key))
    try:
        return template.format(**kwargs)
    except Exception:
        return template


def initialize_com_for_thread():
    try:
        import comtypes

        comtypes.CoInitialize()
        return comtypes
    except Exception:
        logging.debug("COM initialization skipped", exc_info=True)
        return None


def uninitialize_com_for_thread(comtypes_module):
    if not comtypes_module:
        return
    try:
        comtypes_module.CoUninitialize()
    except Exception:
        logging.debug("COM uninitialization skipped", exc_info=True)
HHOOK = getattr(wintypes, "HHOOK", wintypes.HANDLE)
HINSTANCE = getattr(wintypes, "HINSTANCE", wintypes.HANDLE)
HMODULE = getattr(wintypes, "HMODULE", wintypes.HANDLE)
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
LRESULT = ctypes.c_ssize_t
LOW_LEVEL_KEYBOARD_PROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, WPARAM, LPARAM)


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [
        ("hIcon", wintypes.HICON),
        ("iIcon", ctypes.c_int),
        ("dwAttributes", wintypes.DWORD),
        ("szDisplayName", wintypes.WCHAR * 260),
        ("szTypeName", wintypes.WCHAR * 80),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def get_shell_file_icon(path, large=True):
    if not path:
        return None
    shell_info = SHFILEINFOW()
    flags = 0x000000100 | (0x000000000 if large else 0x000000001)  # SHGFI_ICON | size
    attributes = 0
    if not os.path.exists(path):
        flags |= 0x000000010  # SHGFI_USEFILEATTRIBUTES
        attributes = 0x00000080  # FILE_ATTRIBUTE_NORMAL
    result = ctypes.windll.shell32.SHGetFileInfoW(
        path,
        attributes,
        ctypes.byref(shell_info),
        ctypes.sizeof(shell_info),
        flags,
    )
    return shell_info.hIcon if result and shell_info.hIcon else None


def query_process_image_path(pid):
    """Return an executable path using the least-privileged Windows process query."""
    if sys.platform != "win32" or not pid:
        return ""
    process_handle = None
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        process_handle = kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not process_handle:
            return ""
        buffer = ctypes.create_unicode_buffer(32768)
        length = wintypes.DWORD(len(buffer))
        if kernel32.QueryFullProcessImageNameW(process_handle, 0, buffer, ctypes.byref(length)):
            return buffer.value
    except Exception:
        pass
    finally:
        if process_handle:
            try:
                ctypes.windll.kernel32.CloseHandle(process_handle)
            except Exception:
                pass
    return ""


def get_visible_window_processes():
    """Map visible app PIDs to their current desktop Z-order and representative HWND."""
    windows = {}
    foreground = 0
    try:
        foreground = int(win32gui.GetForegroundWindow() or 0)
    except Exception:
        pass

    def collect(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd).strip():
                return
            process_id = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), ctypes.byref(process_id))
            pid = int(process_id.value)
            if not pid or pid in windows:
                return
            windows[pid] = {
                "window_rank": len(windows),
                "window_handle": int(hwnd),
                "is_foreground": int(hwnd) == foreground,
            }
        except Exception:
            return

    try:
        win32gui.EnumWindows(collect, None)
    except Exception:
        pass
    return windows


def running_program_recent_sort_key(program):
    window_rank = program.get("window_rank")
    has_visible_window = window_rank is not None
    return (
        1 if has_visible_window else 0,
        -int(window_rank) if has_visible_window else 0,
        float(program.get("create_time") or 0),
        str(program.get("name") or "").casefold(),
    )


def should_include_running_program(cpu_percent, memory_mb, has_visible_window=False):
    return bool(
        has_visible_window
        or cpu_percent >= MIN_RUNNING_PROGRAM_CPU_PERCENT
        or memory_mb >= MIN_RUNNING_PROGRAM_MEMORY_MB
    )


def get_window_icon_handle(hwnd):
    if not hwnd:
        return None
    user32 = ctypes.windll.user32
    for icon_type in (1, 2, 0):  # ICON_BIG, ICON_SMALL2, ICON_SMALL
        try:
            result = ctypes.c_size_t()
            if user32.SendMessageTimeoutW(
                wintypes.HWND(hwnd),
                0x007F,
                wintypes.WPARAM(icon_type),
                wintypes.LPARAM(0),
                0x0002,
                100,
                ctypes.byref(result),
            ) and result.value:
                return int(result.value)
        except Exception:
            pass
    for class_index in (-14, -34):  # GCLP_HICON, GCLP_HICONSM
        try:
            getter = getattr(user32, "GetClassLongPtrW", user32.GetClassLongW)
            getter.restype = ctypes.c_size_t
            icon_handle = getter(wintypes.HWND(hwnd), class_index)
            if icon_handle:
                return int(icon_handle)
        except Exception:
            pass
    return None


def get_image_from_icon_handle(icon_handle, source_size=32):
    if not icon_handle:
        return None
    screen_dc_handle = None
    hdc = None
    memory_dc = None
    bitmap = None
    try:
        screen_dc_handle = win32gui.GetDC(0)
        hdc = win32ui.CreateDCFromHandle(screen_dc_handle)
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(hdc, source_size, source_size)
        memory_dc = hdc.CreateCompatibleDC()
        memory_dc.SelectObject(bitmap)
        win32gui.DrawIconEx(memory_dc.GetSafeHdc(), 0, 0, icon_handle, source_size, source_size, 0, 0, win32con.DI_NORMAL)
        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)
        return Image.frombuffer(
            "RGBA",
            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr,
            "raw",
            "BGRA",
            0,
            1,
        ).copy()
    except Exception:
        return None
    finally:
        if memory_dc is not None:
            try:
                memory_dc.DeleteDC()
            except Exception:
                pass
        if bitmap is not None:
            try:
                win32gui.DeleteObject(bitmap.GetHandle())
            except Exception:
                pass
        if screen_dc_handle:
            try:
                win32gui.ReleaseDC(0, screen_dc_handle)
            except Exception:
                pass


def get_icon_from_window(hwnd, size=32, source_size=None, corner_radius=0):
    source_size = max(source_size or size, size)
    image = get_image_from_icon_handle(get_window_icon_handle(hwnd), source_size)
    if image is None:
        return None
    source_corner_radius = int(corner_radius * source_size / size) if size else corner_radius
    image = apply_rounded_corners(image, source_corner_radius)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))


def apply_rounded_corners(image, radius):
    if radius <= 0:
        return image

    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=radius, fill=255)
    image = image.copy()
    image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
    return image


def get_icon_from_exe(exe_path, size=32, source_size=None, corner_radius=0, use_shell_fallback=True):
    extracted_icons = []
    shell_icon = None
    try:
        if not exe_path:
            return None

        source_size = max(source_size or size, size)
        large_icons = []
        small_icons = []
        if os.path.exists(exe_path):
            large_icons, small_icons = win32gui.ExtractIconEx(exe_path, 0)
            extracted_icons = list(large_icons) + list(small_icons)
        icons = (large_icons or small_icons) if size >= 32 else (small_icons or large_icons)
        icon_handle = icons[0] if icons else None
        if not icon_handle and use_shell_fallback:
            shell_icon = get_shell_file_icon(exe_path, large=size >= 32)
            icon_handle = shell_icon
        if not icon_handle:
            return None

        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(hdc, source_size, source_size)
        memory_dc = hdc.CreateCompatibleDC()
        memory_dc.SelectObject(bitmap)

        win32gui.DrawIconEx(memory_dc.GetSafeHdc(), 0, 0, icon_handle, source_size, source_size, 0, 0, win32con.DI_NORMAL)

        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)
        image = Image.frombuffer("RGBA", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRA", 0, 1)
        source_corner_radius = int(corner_radius * source_size / size) if size else corner_radius
        image = apply_rounded_corners(image, source_corner_radius)
        return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
    except Exception:
        return None
    finally:
        for icon in extracted_icons:
            try:
                win32gui.DestroyIcon(icon)
            except Exception:
                pass
        if shell_icon:
            try:
                win32gui.DestroyIcon(shell_icon)
            except Exception:
                pass


def get_icon_from_image(image_path, size=32, source_size=None, corner_radius=0):
    try:
        if not image_path or not os.path.exists(image_path):
            return None

        source_size = max(source_size or size, size)
        image = Image.open(image_path).convert("RGBA")
        image.thumbnail((source_size, source_size), Image.LANCZOS)

        canvas = Image.new("RGBA", (source_size, source_size), (0, 0, 0, 0))
        x = (source_size - image.width) // 2
        y = (source_size - image.height) // 2
        canvas.alpha_composite(image, (x, y))

        source_corner_radius = int(corner_radius * source_size / size) if size else corner_radius
        canvas = apply_rounded_corners(canvas, source_corner_radius)
        return ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(size, size))
    except Exception:
        return None


def make_app_icon_image(size=64):
    try:
        image = Image.open(APP_ICON_FILE).convert("RGBA")
        image.thumbnail((size, size), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
        return canvas
    except Exception:
        image = Image.new("RGBA", (size, size), (26, 26, 26, 255))
        draw = ImageDraw.Draw(image)
        pad = max(2, size // 8)
        draw.rounded_rectangle((pad, pad, size - pad, size - pad), radius=max(4, size // 5), fill=(187, 235, 65, 255))
        draw.arc((size * 0.28, size * 0.27, size * 0.72, size * 0.72), 205, 335, fill=(255, 255, 255, 255), width=max(2, size // 12))
        draw.rectangle((size * 0.26, size * 0.46, size * 0.38, size * 0.62), fill=(255, 255, 255, 255))
        draw.rectangle((size * 0.62, size * 0.46, size * 0.74, size * 0.62), fill=(255, 255, 255, 255))
        return image


def make_app_icon(size=18):
    image = make_app_icon_image(size)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))


def make_tray_image():
    return make_app_icon_image(64)


def calculate_effective_ui_scale(native_scale, work_width, work_height):
    native_scale = max(MIN_EFFECTIVE_UI_SCALE, float(native_scale or 1.0))
    usable_width = max(1, int(work_width) - DISPLAY_FIT_MARGIN_X)
    usable_height = max(1, int(work_height) - DISPLAY_FIT_MARGIN_Y)
    fit_scale = min(usable_width / SETTINGS_DEFAULT_WIDTH, usable_height / SETTINGS_DEFAULT_HEIGHT)
    return max(MIN_EFFECTIVE_UI_SCALE, min(native_scale, fit_scale))


def calculate_scaled_window_size(width, height, scale):
    return max(1, round(width * scale)), max(1, round(height * scale))


def centered_scaled_geometry(width, height, scale, work_area):
    left, top, right, bottom = work_area
    physical_width, physical_height = calculate_scaled_window_size(width, height, scale)
    work_width = max(1, right - left)
    work_height = max(1, bottom - top)
    x = left + max(0, (work_width - physical_width) // 2)
    y = top + max(0, (work_height - physical_height) // 2)
    return f"{width}x{height}+{x}+{y}"


def read_config_object(path, max_bytes=MAX_CONFIG_BYTES):
    if os.path.getsize(path) > max_bytes:
        raise ValueError(f"config exceeds {max_bytes} bytes")
    with open(path, "r", encoding="utf-8-sig") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise ValueError("config root must be a JSON object")
    return loaded


def migrate_legacy_config(config_file=CONFIG_FILE, legacy_file=LEGACY_CONFIG_FILE):
    if os.path.normcase(os.path.abspath(config_file)) == os.path.normcase(os.path.abspath(legacy_file)):
        return False
    if os.path.exists(config_file) or not os.path.isfile(legacy_file):
        return False
    if os.path.getsize(legacy_file) > MAX_CONFIG_BYTES:
        logging.warning("legacy config migration skipped oversized file=%s", legacy_file)
        return False
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    shutil.copy2(legacy_file, config_file)
    logging.info("legacy config migrated source=%s destination=%s", legacy_file, config_file)
    return True


def command_line_option_value(arguments, option):
    for index, argument in enumerate(arguments):
        if argument.startswith(f"{option}="):
            return argument.split("=", 1)[1]
        if argument == option and index + 1 < len(arguments):
            return arguments[index + 1]
    return ""


def run_runtime_diagnostics(data_dir=None):
    data_dir = os.path.abspath(data_dir or APP_DATA_DIR)
    checks = {
        "windows_10_or_newer": sys.platform == "win32" and sys.getwindowsversion().major >= 10,
        "64_bit_runtime": sys.maxsize > 2**32,
        "app_icon_available": os.path.isfile(APP_ICON_FILE),
        "native_audio_backend_available": False,
        "data_directory_writable": False,
    }
    report_path = os.path.join(data_dir, "runtime_diagnostics.json")
    probe_path = os.path.join(data_dir, f".write_test_{os.getpid()}.tmp")
    try:
        from pycaw.pycaw import AudioUtilities  # noqa: F401

        checks["native_audio_backend_available"] = True
    except Exception:
        logging.exception("runtime diagnostics native audio backend check failed")
    try:
        os.makedirs(data_dir, exist_ok=True)
        with open(probe_path, "w", encoding="utf-8") as probe:
            probe.write("ok")
        checks["data_directory_writable"] = True
    except Exception:
        logging.exception("runtime diagnostics data directory check failed path=%s", data_dir)
    finally:
        try:
            if os.path.exists(probe_path):
                os.remove(probe_path)
        except OSError:
            pass

    report = {
        "app_version": APP_VERSION,
        "frozen": bool(getattr(sys, "frozen", False)),
        "python_version": sys.version.split()[0],
        "pillow_version": PIL.__version__,
        "app_dir": APP_DIR,
        "app_data_dir": data_dir,
        "checks": checks,
        "ok": all(checks.values()),
    }
    try:
        temporary_path = f"{report_path}.tmp"
        with open(temporary_path, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=2, ensure_ascii=False)
        os.replace(temporary_path, report_path)
    except Exception:
        logging.exception("runtime diagnostics report write failed path=%s", report_path)
        report["ok"] = False
    logging.info("runtime diagnostics complete ok=%s checks=%s report=%s", report["ok"], checks, report_path)
    return report["ok"], report_path


def cleanup_expired_logs(now=None):
    if not os.path.isdir(LOG_DIR):
        return 0
    cutoff = (now or time.time()) - LOG_RETENTION_DAYS * 24 * 60 * 60
    active_names = {os.path.basename(LOG_FILE), os.path.basename(SETTINGS_EVENT_LOG_FILE)}
    prefixes = tuple(f"{name}." for name in active_names)
    removed = 0
    for name in os.listdir(LOG_DIR):
        if not name.startswith(prefixes):
            continue
        path = os.path.join(LOG_DIR, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
                removed += 1
        except OSError:
            continue
    return removed


def install_exception_logging_hooks():
    def log_main_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            return sys.__excepthook__(exc_type, exc_value, exc_traceback)
        logging.critical("unhandled main-thread exception", exc_info=(exc_type, exc_value, exc_traceback))

    def log_thread_exception(args):
        logging.critical(
            "unhandled thread exception thread=%s",
            getattr(args.thread, "name", None),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = log_main_exception
    if hasattr(threading, "excepthook"):
        threading.excepthook = log_thread_exception


def setup_logging():
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        removed_logs = cleanup_expired_logs()
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        handler = RotatingFileHandler(LOG_FILE, maxBytes=MAIN_LOG_MAX_BYTES, backupCount=MAIN_LOG_BACKUP_COUNT, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)s] %(threadName)s %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
        settings_logger = logging.getLogger("settings_events")
        settings_logger.setLevel(logging.INFO)
        settings_logger.propagate = False
        for existing_handler in list(settings_logger.handlers):
            settings_logger.removeHandler(existing_handler)
        settings_handler = RotatingFileHandler(SETTINGS_EVENT_LOG_FILE, maxBytes=SETTINGS_LOG_MAX_BYTES, backupCount=SETTINGS_LOG_BACKUP_COUNT, encoding="utf-8")
        settings_handler.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d %(message)s", "%Y-%m-%d %H:%M:%S"))
        settings_logger.addHandler(settings_handler)
        install_exception_logging_hooks()
        windows_version = sys.getwindowsversion()
        logging.info(
            "logging started version=%s app_dir=%s app_data_dir=%s resource_dir=%s frozen=%s python=%s windows=%s.%s.%s pid=%s retention_days=%s removed_expired=%s",
            APP_VERSION,
            APP_DIR,
            APP_DATA_DIR,
            RESOURCE_DIR,
            getattr(sys, "frozen", False),
            sys.version.split()[0],
            windows_version.major,
            windows_version.minor,
            windows_version.build,
            os.getpid(),
            LOG_RETENTION_DAYS,
            removed_logs,
        )
    except Exception:
        logging.basicConfig(level=logging.INFO)


def log_exception(context):
    logging.exception("%s", context)


def configure_windows_app_identity():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except Exception:
        pass


def acquire_single_instance_mutex():
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.restype = wintypes.DWORD
        handle = kernel32.CreateMutexW(None, True, SINGLE_INSTANCE_MUTEX_NAME)
        if not handle or kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return None
        return handle
    except Exception:
        return True


def draw_ui_icon_image(kind, size=64, color=(245, 245, 245, 255)):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = max(2, size // 12)
    c = color

    if kind == "speaker":
        draw.polygon(
            [
                (size * 0.16, size * 0.38),
                (size * 0.34, size * 0.38),
                (size * 0.55, size * 0.22),
                (size * 0.55, size * 0.78),
                (size * 0.34, size * 0.62),
                (size * 0.16, size * 0.62),
            ],
            fill=c,
        )
        draw.arc((size * 0.48, size * 0.28, size * 0.84, size * 0.72), -45, 45, fill=c, width=width)
        draw.arc((size * 0.56, size * 0.14, size * 0.98, size * 0.86), -45, 45, fill=c, width=width)
    elif kind == "headset":
        draw.arc((size * 0.16, size * 0.10, size * 0.84, size * 0.86), 190, 350, fill=c, width=width + 1)
        draw.rounded_rectangle((size * 0.12, size * 0.46, size * 0.28, size * 0.76), radius=width, fill=c)
        draw.rounded_rectangle((size * 0.72, size * 0.46, size * 0.88, size * 0.76), radius=width, fill=c)
        draw.line((size * 0.76, size * 0.75, size * 0.58, size * 0.84), fill=c, width=width)
        draw.ellipse((size * 0.52, size * 0.78, size * 0.64, size * 0.90), fill=c)
    elif kind == "gear":
        center = size / 2
        points = []
        for index in range(16):
            radius = size * (0.43 if index % 2 == 0 else 0.33)
            angle = -math.pi / 2 + index * math.pi / 8
            points.append((center + math.cos(angle) * radius, center + math.sin(angle) * radius))
        draw.polygon(points, fill=c)
        draw.ellipse((size * 0.34, size * 0.34, size * 0.66, size * 0.66), fill=(0, 0, 0, 0))
    elif kind == "trash":
        draw.rounded_rectangle((size * 0.26, size * 0.34, size * 0.74, size * 0.84), radius=width, outline=c, width=width)
        draw.line((size * 0.20, size * 0.28, size * 0.80, size * 0.28), fill=c, width=width)
        draw.line((size * 0.38, size * 0.20, size * 0.62, size * 0.20), fill=c, width=width)
        draw.line((size * 0.42, size * 0.44, size * 0.42, size * 0.74), fill=c, width=width)
        draw.line((size * 0.58, size * 0.44, size * 0.58, size * 0.74), fill=c, width=width)
    elif kind == "handle":
        dot = max(4, size // 12)
        for x in (size * 0.38, size * 0.62):
            for y in (size * 0.28, size * 0.50, size * 0.72):
                draw.ellipse((x - dot, y - dot, x + dot, y + dot), fill=c)
    elif kind == "minimize":
        draw.line((size * 0.24, size * 0.64, size * 0.76, size * 0.64), fill=c, width=width)
    elif kind == "close":
        draw.line((size * 0.28, size * 0.28, size * 0.72, size * 0.72), fill=c, width=width)
        draw.line((size * 0.72, size * 0.28, size * 0.28, size * 0.72), fill=c, width=width)
    elif kind == "edit":
        try:
            edit_font = ImageFont.truetype("arial.ttf", int(size * 0.62))
        except Exception:
            edit_font = None
        text = "E"
        if edit_font:
            bbox = draw.textbbox((0, 0), text, font=edit_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text(((size - text_width) / 2, (size - text_height) / 2 - size * 0.06), text, fill=c, font=edit_font)
        else:
            draw.text((size * 0.34, size * 0.24), text, fill=c)

    return image


def ensure_icon_assets():
    os.makedirs(ICON_DIR, exist_ok=True)
    for name in ("speaker", "headset", "gear", "trash", "handle", "minimize", "close", "edit"):
        path = os.path.join(ICON_DIR, f"{name}.png")
        if not os.path.exists(path):
            draw_ui_icon_image(name, size=128).save(path)


def apply_inactive_icon_gradient(icon, start_rgba=INACTIVE_ICON_GRADIENT_START, end_rgba=INACTIVE_ICON_GRADIENT_END):
    alpha = icon.getchannel("A")
    gradient = create_rgba_linear_gradient(icon.width, icon.height, start_rgba, end_rgba, angle_degrees=149)
    gradient_alpha = gradient.getchannel("A")
    combined_alpha = ImageChops.multiply(alpha, gradient_alpha)
    result = Image.new("RGBA", icon.size, (255, 255, 255, 255))
    result.putalpha(combined_alpha)
    return result


def load_icon_image(kind, black=False, inactive_gradient=False, hover_gradient=False, fallback_size=128):
    black_path = os.path.join(ICON_DIR, f"{kind}_b.png")
    path = os.path.join(ICON_DIR, f"{kind}.png")
    if black and os.path.exists(black_path):
        image = Image.open(black_path).convert("RGBA")
        return apply_inactive_icon_gradient(
            image,
            INACTIVE_ICON_HOVER_GRADIENT_START if hover_gradient else INACTIVE_ICON_GRADIENT_START,
            INACTIVE_ICON_HOVER_GRADIENT_END if hover_gradient else INACTIVE_ICON_GRADIENT_END,
        ) if inactive_gradient else image
    try:
        image = Image.open(path).convert("RGBA")
        if black:
            alpha = image.getchannel("A")
            image = Image.new("RGBA", image.size, (0, 0, 0, 255))
            image.putalpha(alpha)
        if inactive_gradient:
            image = apply_inactive_icon_gradient(
                image,
                INACTIVE_ICON_HOVER_GRADIENT_START if hover_gradient else INACTIVE_ICON_GRADIENT_START,
                INACTIVE_ICON_HOVER_GRADIENT_END if hover_gradient else INACTIVE_ICON_GRADIENT_END,
            )
        return image
    except Exception:
        color = (0, 0, 0, 255) if black else (245, 245, 245, 255)
        image = draw_ui_icon_image(kind, size=fallback_size, color=color)
        return apply_inactive_icon_gradient(
            image,
            INACTIVE_ICON_HOVER_GRADIENT_START if hover_gradient else INACTIVE_ICON_GRADIENT_START,
            INACTIVE_ICON_HOVER_GRADIENT_END if hover_gradient else INACTIVE_ICON_GRADIENT_END,
        ) if inactive_gradient else image


def make_ui_icon(kind, size=28, black=False, inactive_gradient=False):
    image = load_icon_image(kind, black=black, inactive_gradient=inactive_gradient)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))


def make_ui_icon_photo(kind, size=28, scale=1.0):
    scaled_size = max(1, round(size * scale))
    image = load_icon_image(kind)
    image.thumbnail((scaled_size, scaled_size), Image.LANCZOS)
    canvas = Image.new("RGBA", (scaled_size, scaled_size), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((scaled_size - image.width) // 2, (scaled_size - image.height) // 2))
    return ImageTk.PhotoImage(canvas)


def ctk_image_to_photo(image, appearance_mode="dark", scale=1.0):
    if isinstance(image, ctk.CTkImage):
        return image.create_scaled_photo_image(scale, appearance_mode)
    return image


def get_windows_font_path(filename):
    return os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", filename)


def get_pil_text_font(size, bold=False):
    candidates = (
        ["malgunbd.ttf", "malgun.ttf", "segoeuib.ttf", "segoeui.ttf"]
        if bold
        else ["malgun.ttf", "malgunsl.ttf", "segoeui.ttf"]
    )
    for name in candidates:
        for source in (get_windows_font_path(name), name):
            try:
                return ImageFont.truetype(source, size)
            except Exception:
                continue
    return ImageFont.load_default()


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[index:index + 2], 16) for index in (0, 2, 4))


def create_css_like_gradient(width, height, start_hex, end_hex):
    return create_linear_gradient(width, height, start_hex, end_hex, angle_degrees=129, solid_until=0.3965)


def create_rgba_linear_gradient(width, height, start_rgba, end_rgba, angle_degrees=91, solid_until=0):
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = image.load()
    angle = math.radians(angle_degrees)
    dx = math.sin(angle)
    dy = -math.cos(angle)
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    projections = [x * dx + y * dy for x, y in corners]
    minimum = min(projections)
    maximum = max(projections)
    span = maximum - minimum or 1
    start = tuple(start_rgba)
    end = tuple(end_rgba)

    for y in range(height):
        for x in range(width):
            t = (x * dx + y * dy - minimum) / span
            t = 0 if t < solid_until else (t - solid_until) / (1 - solid_until) if solid_until < 1 else 1
            t = min(1, max(0, t))
            pixels[x, y] = tuple(int(start[channel] + (end[channel] - start[channel]) * t) for channel in range(4))
    return image


def make_inactive_button_surface(width, height, radius=UI_RADIUS_CONTROL, rounded_top=True, rounded_bottom=True, hover=False):
    surface = create_rgba_linear_gradient(
        width,
        height,
        INACTIVE_BUTTON_HOVER_GRADIENT_START if hover else INACTIVE_BUTTON_GRADIENT_START,
        INACTIVE_BUTTON_HOVER_GRADIENT_END if hover else INACTIVE_BUTTON_GRADIENT_END,
        angle_degrees=135,
    )
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    if not rounded_top:
        mask_draw.rectangle((0, 0, width, radius), fill=255)
    if not rounded_bottom:
        mask_draw.rectangle((0, height - radius - 1, width, height), fill=255)
    surface.putalpha(ImageChops.multiply(surface.getchannel("A"), mask))

    border = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, outline=INACTIVE_BUTTON_HOVER_BORDER if hover else INACTIVE_BUTTON_BORDER, width=1)
    if not rounded_top:
        border_draw.rectangle((0, 0, width, radius), fill=(0, 0, 0, 0))
    if not rounded_bottom:
        border_draw.rectangle((0, height - radius - 1, width, height), fill=(0, 0, 0, 0))
    surface.alpha_composite(border)
    return surface


def create_linear_gradient(width, height, start_hex, end_hex, angle_degrees=91, solid_until=0):
    start = hex_to_rgb(start_hex)
    end = hex_to_rgb(end_hex)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = image.load()
    angle = math.radians(angle_degrees)
    dx = math.sin(angle)
    dy = -math.cos(angle)
    projections = [x * dx + y * dy for x, y in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1))]
    minimum = min(projections)
    span = max(1, max(projections) - minimum)

    for y in range(height):
        for x in range(width):
            position = ((x * dx + y * dy) - minimum) / span
            if position <= solid_until:
                ratio = 0
            else:
                ratio = min(1, (position - solid_until) / max(0.001, 1 - solid_until))
            color = tuple(round(start[index] + (end[index] - start[index]) * ratio) for index in range(3))
            pixels[x, y] = (*color, 255)
    return image


def make_mini_background_image(scale=1.0):
    width = max(1, round(MINI_WIDTH * scale))
    height = max(1, round(MINI_HEIGHT * scale))
    image = create_linear_gradient(width, height, MINI_BG_GRADIENT_START, MINI_BG_GRADIENT_END, angle_degrees=91)
    return ImageTk.PhotoImage(image)


def make_mini_background_slice(width, height, x, y, scale=1.0):
    background = create_linear_gradient(max(1, round(MINI_WIDTH * scale)), max(1, round(MINI_HEIGHT * scale)), MINI_BG_GRADIENT_START, MINI_BG_GRADIENT_END, angle_degrees=91)
    image = background.crop((x, y, x + width, y + height))
    return ImageTk.PhotoImage(image)


def make_setting_device_header_image(kind, text, active, width=269, height=39, hover=False, disabled=False):
    image = Image.new("RGBA", (width, height), SETTINGS_PANEL_BG)
    if disabled:
        background = Image.new("RGBA", (width, height), (40, 40, 40, 210))
        border = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(border).rounded_rectangle((0, 0, width - 1, height - 1), radius=UI_RADIUS_CONTROL, outline=(74, 74, 74, 100), width=1)
        background.alpha_composite(border)
    elif active:
        background = create_css_like_gradient(width, height, SETTINGS_DEVICE_ACTIVE_START, SETTINGS_DEVICE_ACTIVE_END)
    else:
        background = make_inactive_button_surface(width, height, radius=UI_RADIUS_CONTROL, rounded_bottom=False, hover=hover)

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, width - 1, height + UI_RADIUS_CONTROL), radius=UI_RADIUS_CONTROL, fill=255)
    if active:
        background.putalpha(mask)
    image.alpha_composite(background)

    icon = load_icon_image(kind, black=False, inactive_gradient=not active, hover_gradient=hover)
    if disabled:
        icon.putalpha(icon.getchannel("A").point(lambda value: int(value * 0.35)))
    icon.thumbnail((24, 24), Image.LANCZOS)

    text_font = get_pil_text_font(18)

    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), text, font=text_font)
    content_width = icon.width + 8 + bbox[2] - bbox[0]
    x = (width - content_width) // 2
    y = (height - icon.height) // 2
    image.alpha_composite(icon, (x, y))
    text_fill = (255, 255, 255, 110) if disabled else (255, 255, 255, 255)
    draw.text((x + icon.width + 8, (height - (bbox[3] - bbox[1])) / 2 - 1), text, fill=text_fill, font=text_font)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_setting_device_dropdown_image(text, active, width=269, height=37, hover=False, rounded_bottom=True):
    image = Image.new("RGBA", (width, height), SETTINGS_PANEL_BG)
    background = (
        create_css_like_gradient(width, height, SETTINGS_DEVICE_ACTIVE_START, SETTINGS_DEVICE_ACTIVE_END)
        if active
        else make_inactive_button_surface(width, height, radius=UI_RADIUS_CONTROL, rounded_top=False, rounded_bottom=rounded_bottom, hover=hover)
    )
    image.alpha_composite(background)
    mask = Image.new("L", (width, height), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle((0, -UI_RADIUS_CONTROL, width - 1, height - 1), radius=UI_RADIUS_CONTROL, fill=255)
    if not rounded_bottom:
        draw_mask.rectangle((0, height - 8, width, height), fill=255)
    if active:
        background.putalpha(mask)
        image = Image.new("RGBA", (width, height), SETTINGS_PANEL_BG)
        image.alpha_composite(background)

    text_font = get_pil_text_font(12)

    draw = ImageDraw.Draw(image)
    display_text = text if len(text) <= 28 else text[:25] + "..."
    bbox = draw.textbbox((0, 0), display_text, font=text_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_fill = (255, 255, 255, 255)
    draw.text(((width - text_width) / 2 - 8, (height - text_height) / 2 - 1), display_text, fill=text_fill, font=text_font)
    triangle = [(width - 24, height // 2 - 3), (width - 12, height // 2 - 3), (width - 18, height // 2 + 4)]
    draw.polygon(triangle, fill=text_fill)
    if not rounded_bottom:
        draw.line((0, height - 1, width - 1, height - 1), fill=SETTINGS_CONTROL_DIVIDER, width=1)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_program_target_button_image(kind, active=False, hover=False, width=38, height=39):
    image = Image.new("RGBA", (width, height), SETTINGS_ROW_BG)
    if active:
        background = create_css_like_gradient(width, height, ACTIVE_GRADIENT_START, ACTIVE_GRADIENT_END)
        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=UI_RADIUS_CONTROL, fill=255)
        background.putalpha(mask)
    else:
        background = make_inactive_button_surface(width, height, radius=UI_RADIUS_CONTROL, hover=hover)
    image.alpha_composite(background)

    icon = load_icon_image(kind, black=False, inactive_gradient=not active, hover_gradient=hover)
    icon.thumbnail((24, 24), Image.LANCZOS)
    image.alpha_composite(icon, ((width - icon.width) // 2, (height - icon.height) // 2))
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_settings_control_surface(
    width,
    height,
    rounded_top_left=False,
    rounded_top_right=False,
    rounded_bottom_left=False,
    rounded_bottom_right=False,
    stroke_top=True,
    stroke_right=True,
    stroke_bottom=True,
    stroke_left=True,
    hover=False,
    fill_color=None,
):
    if fill_color is None:
        surface = create_rgba_linear_gradient(
            width,
            height,
            INACTIVE_BUTTON_HOVER_GRADIENT_START if hover else INACTIVE_BUTTON_GRADIENT_START,
            INACTIVE_BUTTON_HOVER_GRADIENT_END if hover else INACTIVE_BUTTON_GRADIENT_END,
            angle_degrees=135,
        )
    else:
        surface = Image.new("RGBA", (width, height), fill_color)
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = UI_RADIUS_CONTROL
    mask_draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=255)
    if not rounded_top_left:
        mask_draw.rectangle((0, 0, radius, radius), fill=255)
    if not rounded_top_right:
        mask_draw.rectangle((width - radius - 1, 0, width, radius), fill=255)
    if not rounded_bottom_left:
        mask_draw.rectangle((0, height - radius - 1, radius, height), fill=255)
    if not rounded_bottom_right:
        mask_draw.rectangle((width - radius - 1, height - radius - 1, width, height), fill=255)
    surface.putalpha(ImageChops.multiply(surface.getchannel("A"), mask))

    border = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_color = INACTIVE_BUTTON_HOVER_BORDER if hover else INACTIVE_BUTTON_BORDER
    if stroke_top:
        border_draw.line((radius if rounded_top_left else 0, 0, width - radius - 1 if rounded_top_right else width - 1, 0), fill=border_color, width=1)
    if stroke_bottom:
        border_draw.line((radius if rounded_bottom_left else 0, height - 1, width - radius - 1 if rounded_bottom_right else width - 1, height - 1), fill=border_color, width=1)
    if stroke_left:
        border_draw.line((0, radius if rounded_top_left else 0, 0, height - radius - 1 if rounded_bottom_left else height - 1), fill=border_color, width=1)
    if stroke_right:
        border_draw.line((width - 1, radius if rounded_top_right else 0, width - 1, height - radius - 1 if rounded_bottom_right else height - 1), fill=border_color, width=1)
    if rounded_top_left and (stroke_top or stroke_left):
        border_draw.arc((0, 0, radius * 2, radius * 2), 180, 270, fill=border_color, width=1)
    if rounded_top_right and (stroke_top or stroke_right):
        border_draw.arc((width - radius * 2 - 1, 0, width - 1, radius * 2), 270, 360, fill=border_color, width=1)
    if rounded_bottom_left and (stroke_bottom or stroke_left):
        border_draw.arc((0, height - radius * 2 - 1, radius * 2, height - 1), 90, 180, fill=border_color, width=1)
    if rounded_bottom_right and (stroke_bottom or stroke_right):
        border_draw.arc((width - radius * 2 - 1, height - radius * 2 - 1, width - 1, height - 1), 0, 90, fill=border_color, width=1)
    border.putalpha(ImageChops.multiply(border.getchannel("A"), mask))
    surface.alpha_composite(border)
    return surface


def make_settings_segment_image(
    text,
    width,
    height=37,
    icon_kind=None,
    rounded_left=False,
    rounded_right=False,
    rounded_top_left=None,
    rounded_top_right=None,
    rounded_bottom_left=None,
    rounded_bottom_right=None,
    separator_left=False,
    separator_right=False,
    stroke_top=True,
    stroke_right=True,
    stroke_bottom=True,
    stroke_left=True,
):
    image = Image.new("RGBA", (width, height), SETTINGS_PANEL_BG)
    top_left = rounded_left if rounded_top_left is None else rounded_top_left
    top_right = rounded_right if rounded_top_right is None else rounded_top_right
    bottom_left = rounded_left if rounded_bottom_left is None else rounded_bottom_left
    bottom_right = rounded_right if rounded_bottom_right is None else rounded_bottom_right
    segment = make_settings_control_surface(
        width,
        height,
        rounded_top_left=top_left,
        rounded_top_right=top_right,
        rounded_bottom_left=bottom_left,
        rounded_bottom_right=bottom_right,
        stroke_top=stroke_top,
        stroke_right=stroke_right,
        stroke_bottom=stroke_bottom,
        stroke_left=stroke_left,
    )
    image.alpha_composite(segment)

    text_font = get_pil_text_font(15 if icon_kind else 14, bold=bool(icon_kind))

    icon = None
    if icon_kind:
        try:
            icon = Image.open(os.path.join(ICON_DIR, f"{icon_kind}.png")).convert("RGBA")
        except Exception:
            icon = draw_ui_icon_image(icon_kind, size=128)
        icon.thumbnail((24, 24), Image.LANCZOS)

    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), text, font=text_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    content_width = text_width + ((icon.width + 8) if icon else 0)
    x = max(0, (width - content_width) // 2)
    if icon:
        image.alpha_composite(icon, (x, (height - icon.height) // 2))
        x += icon.width + 8
    draw.text((x, (height - text_height) / 2 - bbox[1]), text, fill=(255, 255, 255, 255), font=text_font)
    if separator_left:
        draw.line((0, 0, 0, height - 1), fill=SETTINGS_CONTROL_DIVIDER, width=1)
    if separator_right:
        draw.line((width - 1, 0, width - 1, height - 1), fill=SETTINGS_CONTROL_DIVIDER, width=1)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_settings_dropdown_segment_image(
    text,
    width,
    height=37,
    rounded_top_left=False,
    rounded_top_right=False,
    rounded_bottom_left=False,
    rounded_bottom_right=False,
    separator_left=False,
    separator_right=False,
    stroke_top=True,
    stroke_right=True,
    stroke_bottom=True,
    stroke_left=True,
    arrow_width=None,
    fill_color=CONTROL_BG,
):
    arrow_width = min(width, max(1, arrow_width or height))
    image = Image.new("RGBA", (width, height), SETTINGS_PANEL_BG)
    segment = make_settings_control_surface(
        width,
        height,
        rounded_top_left=rounded_top_left,
        rounded_top_right=rounded_top_right,
        rounded_bottom_left=rounded_bottom_left,
        rounded_bottom_right=rounded_bottom_right,
        stroke_top=stroke_top,
        stroke_right=stroke_right,
        stroke_bottom=stroke_bottom,
        stroke_left=stroke_left,
        fill_color=fill_color,
    )
    image.alpha_composite(segment)

    text_font = get_pil_text_font(13)

    draw = ImageDraw.Draw(image)
    display_text = text
    text_area_width = max(1, width - arrow_width)
    max_text_width = max(24, text_area_width - 16)
    while display_text:
        bbox = draw.textbbox((0, 0), display_text, font=text_font)
        if bbox[2] - bbox[0] <= max_text_width:
            break
        display_text = display_text[:-1]
    if display_text != text and len(display_text) > 3:
        display_text = display_text[:-3] + "..."

    bbox = draw.textbbox((0, 0), display_text, font=text_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = max(8, (text_area_width - text_width) // 2)
    y = (height - text_height) / 2 - bbox[1]
    draw.text((x, y), display_text, fill=(255, 255, 255, 255), font=text_font)

    arrow_x = text_area_width + arrow_width // 2
    arrow_y = height // 2
    draw.line((text_area_width, 1, text_area_width, height - 2), fill=SETTINGS_CONTROL_DIVIDER, width=1)
    draw.line((arrow_x - 5, arrow_y - 2, arrow_x, arrow_y + 3, arrow_x + 5, arrow_y - 2), fill=(255, 255, 255, 255), width=2)
    if separator_left:
        draw.line((0, 0, 0, height - 1), fill=SETTINGS_CONTROL_DIVIDER, width=1)
    if separator_right:
        draw.line((width - 1, 0, width - 1, height - 1), fill=SETTINGS_CONTROL_DIVIDER, width=1)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_onboarding_dropdown_image(text, width, height=38):
    button_width = 52
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    left = Image.new("RGBA", (width - button_width, height), CONTROL_BG)
    right = create_css_like_gradient(button_width, height, ACTIVE_GRADIENT_START, ACTIVE_GRADIENT_END)
    image.alpha_composite(left, (0, 0))
    image.alpha_composite(right, (width - button_width, 0))

    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=UI_RADIUS_CONTROL, fill=255)
    image.putalpha(mask)

    text_font = get_pil_text_font(13)
    draw = ImageDraw.Draw(image)
    display_text = text or ""
    max_text_width = max(24, width - button_width - 24)
    while display_text and draw.textbbox((0, 0), display_text, font=text_font)[2] > max_text_width:
        display_text = display_text[:-1]
    if display_text != (text or "") and len(display_text) > 3:
        display_text = display_text[:-3] + "..."
    bbox = draw.textbbox((0, 0), display_text, font=text_font)
    draw.text((10, (height - (bbox[3] - bbox[1])) / 2 - bbox[1]), display_text, fill=(255, 255, 255, 255), font=text_font)

    arrow_x = width - button_width // 2
    arrow_y = height // 2
    draw.line((arrow_x - 5, arrow_y - 2, arrow_x, arrow_y + 3, arrow_x + 5, arrow_y - 2), fill=(255, 255, 255, 255), width=2)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_settings_gradient_image(width, height):
    return ImageTk.PhotoImage(Image.new("RGBA", (max(1, width), max(1, height)), SETTINGS_GRADIENT_END))


def make_mini_button_image(kind, active=False, hover=False, disabled=False):
    width = MINI_DEVICE_BUTTON_WIDTH
    height = MINI_DEVICE_BUTTON_HEIGHT
    if disabled:
        background = Image.new("RGBA", (width, height), (40, 40, 40, 210))
        border = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border)
        border_draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=UI_RADIUS_CONTROL, outline=(74, 74, 74, 100), width=1)
        background.alpha_composite(border)
    elif active:
        background = create_css_like_gradient(width, height, MINI_BUTTON_ACTIVE_GRADIENT_START, MINI_BUTTON_ACTIVE_GRADIENT_END)
    else:
        background = make_inactive_button_surface(width, height, radius=UI_RADIUS_CONTROL, hover=hover)

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=UI_RADIUS_CONTROL, fill=255)
    button = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    button.alpha_composite(background)
    if active:
        button.putalpha(mask)

    icon = load_icon_image(kind, black=False, inactive_gradient=not active, hover_gradient=hover)
    if disabled:
        alpha = icon.getchannel("A").point(lambda value: int(value * 0.35))
        icon.putalpha(alpha)
    icon.thumbnail((28, 28), Image.LANCZOS)
    x = (width - icon.width) // 2
    y = (height - icon.height) // 2
    button.alpha_composite(icon, (x, y))
    return ctk.CTkImage(light_image=button, dark_image=button, size=(width, height))


def make_audio_switching_button_image(width=AUDIO_SWITCHING_BUTTON_WIDTH, height=MINI_DEVICE_BUTTON_HEIGHT):
    image = Image.new("RGBA", (width, height), CONTROL_BG)
    mask = Image.new("L", (width, height), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle((0, 0, width - 1, height - 1), radius=UI_RADIUS_CONTROL, fill=255)
    image.putalpha(mask)

    draw = ImageDraw.Draw(image)
    text = "Switching..."
    text_font = get_pil_text_font(12, bold=True)
    bbox = draw.textbbox((0, 0), text, font=text_font)
    draw.text(
        ((width - (bbox[2] - bbox[0])) / 2, (height - (bbox[3] - bbox[1])) / 2 - bbox[1]),
        text,
        fill=(255, 255, 255, 255),
        font=text_font,
    )
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_ask_button_photo(text, fill_color, width=72, height=42, text_color=(255, 255, 255, 255), bold=False, scale=1.0):
    if fill_color == ACTIVE_COLOR:
        image = create_css_like_gradient(width, height, ACTIVE_GRADIENT_START, ACTIVE_GRADIENT_END)
    else:
        image = Image.new("RGBA", (width, height), fill_color)
    draw = ImageDraw.Draw(image)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=UI_RADIUS_CONTROL, fill=255)
    image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
    text_font = get_pil_text_font(13, bold=bold)
    bbox = draw.textbbox((0, 0), text, font=text_font)
    draw.text(
        ((width - (bbox[2] - bbox[0])) / 2, (height - (bbox[3] - bbox[1])) / 2 - bbox[1] - 1),
        text,
        fill=text_color,
        font=text_font,
    )
    scaled_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    if scaled_size != image.size:
        image = image.resize(scaled_size, Image.LANCZOS)
    return ImageTk.PhotoImage(image)


def make_ask_auto_toggle_preview_image(width=468, height=84):
    image = Image.new("RGBA", (width, height), PANEL_BG)
    draw = ImageDraw.Draw(image)
    row_x = 10
    row_y = 14
    row_w = width - 20
    row_h = 56
    draw.rounded_rectangle((row_x, row_y, row_x + row_w, row_y + row_h), radius=UI_RADIUS_ROW, fill=SETTINGS_ROW_BG)

    icon_x = row_x + 12
    icon_y = row_y + 10
    draw.rounded_rectangle((icon_x, icon_y, icon_x + 36, icon_y + 36), radius=UI_RADIUS_CONTROL, fill="#272A2F")
    icon_font = get_pil_text_font(9, bold=True)
    app_text = "APP"
    app_bbox = draw.textbbox((0, 0), app_text, font=icon_font)
    draw.text(
        (icon_x + (36 - (app_bbox[2] - app_bbox[0])) / 2, icon_y + (36 - (app_bbox[3] - app_bbox[1])) / 2 - app_bbox[1]),
        app_text,
        fill="#CFCFCF",
        font=icon_font,
    )

    name_font = get_pil_text_font(14)
    draw.text((icon_x + 48, row_y + 18), "Game.exe", fill=(255, 255, 255, 255), font=name_font)

    button_font = get_pil_text_font(12, bold=True)
    button_w = 58
    button_h = 38
    gap = 6
    auto_x = row_x + row_w - 14 - button_w
    ask_x = auto_x - gap - button_w
    button_y = row_y + 9

    def draw_mode_button(x, text, active):
        fill = ACTIVE_COLOR if active else CONTROL_BG
        hover_border = "#525252" if not active else ACTIVE_COLOR
        draw.rounded_rectangle((x, button_y, x + button_w, button_y + button_h), radius=UI_RADIUS_CONTROL, fill=fill, outline=hover_border)
        bbox = draw.textbbox((0, 0), text, font=button_font)
        draw.text(
            (x + (button_w - (bbox[2] - bbox[0])) / 2, button_y + (button_h - (bbox[3] - bbox[1])) / 2 - bbox[1]),
            text,
            fill=(255, 255, 255, 255),
            font=button_font if active else get_pil_text_font(12),
        )

    draw_mode_button(ask_x, "Ask", True)
    draw_mode_button(auto_x, "Auto", False)
    return ImageTk.PhotoImage(image)


def make_ask_before_change_preview_image(width=468, height=118):
    image = Image.new("RGBA", (width, height), (16, 16, 16, 255))
    draw = ImageDraw.Draw(image)

    prompt_y = 14
    prompt_h = 74
    prompt = create_linear_gradient(width, prompt_h, MINI_BG_GRADIENT_START, MINI_BG_GRADIENT_END, angle_degrees=91)
    image.alpha_composite(prompt, (0, prompt_y))

    icon = draw_ui_icon_image("headset", size=128)
    icon.thumbnail((28, 28), Image.LANCZOS)
    image.alpha_composite(icon, (28, prompt_y + 23))

    title_font = get_pil_text_font(20, bold=True)
    detail_font = get_pil_text_font(13)
    draw.text((70, prompt_y + 18), "Switch to Headset?", fill=(255, 255, 255, 255), font=title_font)
    draw.text((70, prompt_y + 48), "Aviassembly  |  24s", fill=(184, 184, 184, 255), font=detail_font)

    yes = create_css_like_gradient(82, 42, ACTIVE_GRADIENT_START, ACTIVE_GRADIENT_END)
    yes_mask = Image.new("L", (82, 42), 0)
    ImageDraw.Draw(yes_mask).rounded_rectangle((0, 0, 81, 41), radius=UI_RADIUS_CONTROL, fill=255)
    yes.putalpha(yes_mask)
    yes_draw = ImageDraw.Draw(yes)
    yes_font = get_pil_text_font(14, bold=True)
    bbox = yes_draw.textbbox((0, 0), "Yes", font=yes_font)
    yes_draw.text(((82 - (bbox[2] - bbox[0])) / 2, (42 - (bbox[3] - bbox[1])) / 2 - bbox[1]), "Yes", fill=(255, 255, 255, 255), font=yes_font)
    image.alpha_composite(yes, (width - 190, prompt_y + 16))

    no = Image.new("RGBA", (82, 42), (68, 68, 68, 255))
    no_mask = Image.new("L", (82, 42), 0)
    ImageDraw.Draw(no_mask).rounded_rectangle((0, 0, 81, 41), radius=UI_RADIUS_CONTROL, fill=255)
    no.putalpha(no_mask)
    no_draw = ImageDraw.Draw(no)
    bbox = no_draw.textbbox((0, 0), "No", font=detail_font)
    no_draw.text(((82 - (bbox[2] - bbox[0])) / 2, (42 - (bbox[3] - bbox[1])) / 2 - bbox[1]), "No", fill=(255, 255, 255, 255), font=detail_font)
    image.alpha_composite(no, (width - 100, prompt_y + 16))

    taskbar_y = prompt_y + prompt_h
    draw.rectangle((0, taskbar_y, width, height), fill=(32, 31, 22, 255))
    draw.line((0, taskbar_y, width, taskbar_y), fill=(75, 75, 58, 255), width=1)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


class AutoAudioApp(ctk.CTk):
    def __init__(self, start_mode="tray", preview_mode=False):
        super().__init__()
        self.configure_display_scaling()
        self.preview_mode = bool(preview_mode)
        logging.info("AutoAudioApp init start_mode=%s preview_mode=%s", start_mode, self.preview_mode)

        ctk.set_appearance_mode("dark")
        self.config_data = self.load_config()
        self.is_mini = True
        self.is_running = True
        self.last_state = "speaker"
        self.manual_override = False
        self.manual_override_during_detection = False
        self.current_detected_name = self.tr("no_program_detected")
        self.current_detected_icon = None
        self.pending_prompt_key = None
        self.ask_countdown_after_id = None
        self.notification_after_id = None
        self.ask_active = False
        self.ask_resolving = False
        self.ask_program = None
        self.ask_target = None
        self.ask_restore_program = None
        self.ask_restore_prompt_key = None
        self.recent_detected_program = None
        self.recent_detected_list_key = None
        self.detected_missing_since = None
        self.notification_active = False
        self.current_audio_mode_cache = None
        self.last_audio_sync_time = 0
        self.last_device_cache_refresh_time = 0
        self.last_audio_switch_failure_reason = None
        self.last_audio_switch_failure_target = None
        self.offline_audio_mode = None
        self.offline_audio_target = None
        self.offline_device_log_keys = set()
        self.loop_guard_log_keys = set()
        self.detection_rules_cache_key = None
        self.detection_rules_cache = []
        self.onboarding_active = False
        self.mini_animation_after_id = None
        self.mini_pinned_by_user = False
        self.keyboard_hook = None
        self.keyboard_hook_proc = None
        self.keyboard_event_queue = queue.SimpleQueue()
        self.keyboard_event_after_id = None
        self.output_switch_hotkey_down = False
        self.ask_keyboard_down_vk = None
        self.hotkey_capture_active = False
        self.exe_icon_cache = {}
        self.window_icon_cache = {}
        self.program_icon_preload_queue = []
        self.program_icon_load_counter = 0
        self.audio_device_ids = {}
        self.audio_device_id_cache_dirty = False
        self.device_cache_lock = threading.Lock()
        self.audio_switching = False
        self.audio_switch_target = None
        self.audio_switch_previous_state = None
        self.pending_audio_switch_mode = None
        self.pending_audio_switch_source = None
        self.audio_switch_ignored_log_time = 0
        self.settings_event_seq = 0
        self.settings_busy_click_log_time = 0
        self.settings_pending_log_time = 0
        self.audio_refresh_button = None
        self.settings_device_refresh_active = False
        self.device_controls = {}
        self.settings_image_cache = {}
        self.active_settings_dropdown = None
        self.program_list_render_token = 0
        self.settings_bg_bound = False
        self.log_cleanup_after_id = None
        self.tray = None
        ensure_icon_assets()
        self.icons = {
            "app": make_app_icon(18),
            "speaker": make_ui_icon("speaker", 28),
            "speaker_dim": make_ui_icon("speaker", 28, inactive_gradient=True),
            "speaker_b": make_ui_icon("speaker", 28, black=True),
            "headset": make_ui_icon("headset", 28),
            "headset_dim": make_ui_icon("headset", 28, inactive_gradient=True),
            "headset_b": make_ui_icon("headset", 28, black=True),
            "gear": make_ui_icon("gear", 22),
            "trash": make_ui_icon("trash", 28),
            "handle": make_ui_icon("handle", 24),
            "minimize": make_ui_icon("minimize", 16),
            "close": make_ui_icon("close", 16),
            "edit": make_ui_icon("edit", 28),
            "no_app": make_ui_icon("NoAppDetected", MINI_DETECTED_ICON_SIZE),
        }
        self.app_window_icon_photo = ImageTk.PhotoImage(make_app_icon_image(64))
        self.mini_button_images = {
            "speaker_active": make_mini_button_image("speaker", active=True),
            "speaker_inactive": make_mini_button_image("speaker", active=False),
            "speaker_hover": make_mini_button_image("speaker", active=False, hover=True),
            "speaker_disabled": make_mini_button_image("speaker", disabled=True),
            "headset_active": make_mini_button_image("headset", active=True),
            "headset_inactive": make_mini_button_image("headset", active=False),
            "headset_hover": make_mini_button_image("headset", active=False, hover=True),
            "headset_disabled": make_mini_button_image("headset", disabled=True),
            "switching": make_audio_switching_button_image(),
        }
        self.current_detected_icon = self.icons["no_app"]
        self.audio_device_names = self.initial_output_names_from_config()

        self.title("Auto Audio Switcher")
        self.apply_window_icon(self)
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)

        self.set_ui_mode("mini")
        self.draw_ui()
        if not self.preview_mode:
            self.start_tray()
            self.sync_keyboard_hook_state()

        if start_mode == "settings":
            self.switch_mode("settings")
        elif start_mode == "mini":
            self.switch_mode("mini")
        else:
            self.show_startup_mini_popup()
        if not self.preview_mode:
            self.after(250, self.show_startup_onboarding_popups)
            self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
            self.monitor_thread.start()
            logging.info("monitor thread started")
        else:
            self.monitor_thread = None
            logging.info("safe UI preview active; background integrations disabled")
        self.schedule_log_cleanup()

    def report_callback_exception(self, exc, val, tb):
        logging.error("tk callback exception", exc_info=(exc, val, tb))

    def show_startup_mini_popup(self):
        self.switch_mode("mini", focus=False, animate_mini=True)
        self.after(STARTUP_MINI_POPUP_SECONDS * 1000, self.hide_startup_mini_popup)

    def hide_startup_mini_popup(self):
        if self.is_mini and self.winfo_viewable() and not self.ask_active and not self.notification_active and not self.onboarding_active and not self.mini_pinned_by_user:
            self.hide_to_tray()

    def restore_mini_focus_after_onboarding(self):
        if not self.is_mini or not self.winfo_viewable():
            return
        self.mini_pinned_by_user = False
        self.bind("<FocusOut>", self.on_mini_focus_out)
        self.animate_mini_in()
        self.after(STARTUP_MINI_POPUP_SECONDS * 1000, self.hide_startup_mini_popup)

    def show_startup_onboarding_popups(self):
        # Source runs are development runs, so keep showing onboarding for
        # py UIaudio.py even when the packaged app stays first-run only.
        show_every_run = SHOW_STARTUP_ONBOARDING_EVERY_RUN or not getattr(sys, "frozen", False)
        if not show_every_run and self.config_data.get("onboarding_completed"):
            return
        self.onboarding_active = True
        self.show_audio_output_setup_popup()

    def show_audio_output_setup_popup(self):
        self.audio_device_names = self.get_output_device_names()
        device_options = self.build_device_options()
        speaker_default = self.device_option_for_name(self.config_data.get("speaker_name"), device_options)
        headset_default = self.device_option_for_name(self.config_data.get("headset_name"), device_options)
        if speaker_default not in device_options:
            speaker_default = device_options[0]
        if headset_default not in device_options:
            headset_default = device_options[0]

        popup = ctk.CTkToplevel(self)

        def finish():
            if device_options and device_options[0] != "No audio device found":
                self.config_data["speaker_name"] = self.device_name_from_option(speaker_var.get())
                self.config_data["headset_name"] = self.device_name_from_option(headset_var.get())
                self.save_config()
            try:
                popup.grab_release()
            except Exception:
                pass
            if popup.winfo_exists():
                popup.destroy()
            self.after(STARTUP_MINI_POPUP_SECONDS * 1000, self.hide_startup_mini_popup)
            self.after(120, self.show_change_mode_intro_popup)

        self.prepare_popup(
            popup,
            "Audio Output Setup",
            520,
            352,
            grab=False,
            close_command=finish,
            allow_minimize=False,
            center_on_screen=True,
        )
        popup.protocol("WM_DELETE_WINDOW", finish)

        body = ctk.CTkFrame(popup, fg_color=WINDOW_BG, corner_radius=0)
        body.pack(fill="both", expand=True, padx=UI_SPACE_LG, pady=UI_SPACE_LG)

        ctk.CTkLabel(body, text="Choose audio outputs", font=("Segoe UI", 22, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(
            body,
            text="Choose the Windows output devices used by Speaker and Headset mode. You can change these later in Settings.",
            font=("Segoe UI", 13),
            text_color="#B8B8B8",
            anchor="w",
            justify="left",
            wraplength=470,
        ).pack(anchor="w", pady=(UI_SPACE_XS, UI_SPACE_MD))

        speaker_var = ctk.StringVar(value=speaker_default)
        headset_var = ctk.StringVar(value=headset_default)

        for label_text, variable in (("Speaker output", speaker_var), ("Headset output", headset_var)):
            ctk.CTkLabel(body, text=label_text, font=("Segoe UI", 13, "bold"), text_color="#E8E8E8").pack(anchor="w", pady=(0, 5))
            self.create_onboarding_device_dropdown(body, variable, device_options).pack(fill="x", pady=(0, 12))

        ctk.CTkButton(
            body,
            text="Continue",
            height=40,
            fg_color=ACTIVE_COLOR,
            hover_color=ACTIVE_HOVER_COLOR,
            text_color="white",
            corner_radius=UI_RADIUS_CONTROL,
            command=finish,
        ).pack(fill="x", pady=(0, 0))
        popup.after(100, popup.focus_force)

    def create_onboarding_device_dropdown(self, parent, variable, values):
        width = 484
        label = ctk.CTkLabel(parent, text="", width=width, height=38, cursor="hand2")
        menu = tk.Menu(
            label,
            tearoff=0,
            background=SETTINGS_DROPDOWN_BG,
            foreground="white",
            activebackground=ACTIVE_COLOR,
            activeforeground="white",
            borderwidth=0,
            activeborderwidth=0,
            relief="flat",
            bd=0,
        )

        def refresh():
            image = make_onboarding_dropdown_image(variable.get(), width)
            label._onboarding_dropdown_image = image
            label.configure(image=image)

        def select(value):
            variable.set(value)
            refresh()

        for value in values:
            menu.add_command(label=str(value).ljust(max(1, width // 7)), command=lambda selected=value: select(selected))

        def open_menu(event=None):
            try:
                menu.tk_popup(label.winfo_rootx(), label.winfo_rooty() + label.winfo_height())
            finally:
                menu.grab_release()

        label.bind("<Button-1>", open_menu)
        refresh()
        return label

    def show_change_mode_intro_popup(self):
        popup = ctk.CTkToplevel(self)

        def finish():
            self.config_data["onboarding_completed"] = True
            self.save_config()
            self.onboarding_active = False
            try:
                popup.grab_release()
            except Exception:
                pass
            if popup.winfo_exists():
                popup.destroy()
            self.after(80, self.restore_mini_focus_after_onboarding)

        self.prepare_popup(
            popup,
            "Change Mode Guide",
            540,
            580,
            grab=False,
            close_command=finish,
            allow_minimize=False,
            center_on_screen=True,
        )
        popup.protocol("WM_DELETE_WINDOW", finish)

        body = ctk.CTkFrame(popup, fg_color=WINDOW_BG, corner_radius=0)
        body.pack(fill="both", expand=True, padx=UI_SPACE_LG, pady=UI_SPACE_LG)

        ctk.CTkLabel(body, text="How program rules work", font=("Segoe UI", 22, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(
            body,
            text="Add a program once, then choose how that program should switch audio.",
            font=("Segoe UI", 13),
            text_color="#B8B8B8",
            anchor="w",
            justify="left",
            wraplength=470,
        ).pack(anchor="w", pady=(UI_SPACE_XS, UI_SPACE_MD))

        for title, description in (
            ("Program List", "Each row has an Ask / Auto toggle group. Use it to decide whether the program switches immediately or asks first."),
            ("Ask / Auto", "Ask shows a confirmation prompt before switching. Auto switches immediately when the program is detected and keeps the mini view visible for the configured duration."),
        ):
            card = ctk.CTkFrame(body, fg_color=PANEL_BG, corner_radius=UI_RADIUS_PANEL)
            card.pack(fill="x", pady=(0, UI_SPACE_MD))
            ctk.CTkLabel(card, text=title, font=("Segoe UI", 15, "bold"), text_color="white").pack(anchor="w", padx=UI_SPACE_MD, pady=(UI_SPACE_MD, UI_SPACE_XS))
            ctk.CTkLabel(card, text=description, font=("Segoe UI", 12), text_color="#B8B8B8", anchor="w", justify="left", wraplength=470).pack(anchor="w", padx=UI_SPACE_MD, pady=(0, UI_SPACE_SM))
            if title == "Program List":
                self.ask_auto_toggle_preview_image = make_ask_auto_toggle_preview_image()
                ctk.CTkLabel(card, text="", image=self.ask_auto_toggle_preview_image).pack(fill="x", padx=UI_SPACE_MD, pady=(0, UI_SPACE_MD))
            if title == "Ask / Auto":
                self.ask_before_change_preview_image = make_ask_before_change_preview_image()
                ctk.CTkLabel(card, text="", image=self.ask_before_change_preview_image).pack(fill="x", padx=UI_SPACE_MD, pady=(0, UI_SPACE_MD))

        ctk.CTkButton(
            body,
            text="Got it",
            height=40,
            fg_color=ACTIVE_COLOR,
            hover_color=ACTIVE_HOVER_COLOR,
            text_color="white",
            corner_radius=UI_RADIUS_CONTROL,
            command=finish,
        ).pack(fill="x", pady=(2, 0))
        popup.after(100, popup.focus_force)

    def default_config(self):
        return {
            "headset_name": "",
            "headset_id": "",
            "speaker_name": "",
            "speaker_id": "",
            "auto_list": [],
            "ask_list": [],
            "start_with_windows": False,
            "settings_geometry": "",
            "output_switch_hotkey": "",
            "ask_timeout_seconds": ASK_TIMEOUT_SECONDS,
            "mini_notification_seconds": MINI_NOTIFICATION_SECONDS,
            "onboarding_completed": False,
            "language": DEFAULT_LANGUAGE,
        }

    def initial_output_names_from_config(self):
        names = []
        for key in ("speaker_name", "headset_name"):
            name = self.config_data.get(key) or ""
            if name and name != "No audio device found" and name not in names:
                names.append(name)
        return names

    def load_config(self):
        config = self.default_config()
        try:
            migrate_legacy_config()
        except Exception:
            logging.exception("legacy config migration failed source=%s destination=%s", LEGACY_CONFIG_FILE, CONFIG_FILE)
        if os.path.exists(CONFIG_FILE):
            try:
                config.update(read_config_object(CONFIG_FILE))
            except Exception:
                logging.exception("config load failed file=%s", CONFIG_FILE)
                if os.path.exists(CONFIG_BACKUP_FILE):
                    try:
                        config.update(read_config_object(CONFIG_BACKUP_FILE))
                        logging.warning("config restored from backup file=%s", CONFIG_BACKUP_FILE)
                    except Exception:
                        logging.exception("config backup load failed; defaults will be used file=%s", CONFIG_BACKUP_FILE)

        config["auto_list"] = self.normalize_program_list(config.get("auto_list", []))
        config["ask_list"] = self.normalize_program_list(config.get("ask_list", []))
        config["auto_list"], config["ask_list"] = self.deduplicate_program_lists(config["auto_list"], config["ask_list"])
        config.pop("microphone_name", None)
        config.pop("microphone_mute_hotkey", None)
        config["speaker_id"] = config.get("speaker_id") or ""
        config["headset_id"] = config.get("headset_id") or ""
        config["ask_timeout_seconds"] = self.parse_ask_timeout_seconds(config.get("ask_timeout_seconds", ASK_TIMEOUT_SECONDS))
        config["mini_notification_seconds"] = self.parse_mini_notification_seconds(config.get("mini_notification_seconds", MINI_NOTIFICATION_SECONDS))
        config["language"] = normalize_language_code(config.get("language", DEFAULT_LANGUAGE))
        logging.info(
            "config loaded auto_rules=%s ask_rules=%s language=%s onboarding_completed=%s",
            len(config["auto_list"]),
            len(config["ask_list"]),
            config["language"],
            bool(config.get("onboarding_completed")),
        )
        return config

    def current_language(self):
        return normalize_language_code(getattr(self, "config_data", {}).get("language", DEFAULT_LANGUAGE))

    def tr(self, key, **kwargs):
        return translate_text(self.current_language(), key, **kwargs)

    def ui_font_family(self):
        return "Malgun Gothic" if self.current_language() == "ko" else "Segoe UI"

    def parse_duration_seconds(self, value, fallback):
        if isinstance(value, str):
            cleaned = value.strip().lower()
            for suffix in ("seconds", "second", "secs", "sec", "s"):
                cleaned = cleaned.replace(suffix, "")
            value = cleaned.strip()
        try:
            seconds = int(float(value))
        except (TypeError, ValueError):
            seconds = fallback
        return max(1, seconds)

    def parse_ask_timeout_seconds(self, value):
        return self.parse_duration_seconds(value, ASK_TIMEOUT_SECONDS)

    def parse_mini_notification_seconds(self, value):
        return self.parse_duration_seconds(value, MINI_NOTIFICATION_SECONDS)

    def get_ask_timeout_seconds(self):
        return self.parse_ask_timeout_seconds(self.config_data.get("ask_timeout_seconds", ASK_TIMEOUT_SECONDS))

    def format_ask_timeout_seconds(self, seconds=None):
        return f"{self.parse_ask_timeout_seconds(seconds if seconds is not None else self.get_ask_timeout_seconds())}s"

    def get_mini_notification_seconds(self):
        return self.parse_mini_notification_seconds(self.config_data.get("mini_notification_seconds", MINI_NOTIFICATION_SECONDS))

    def format_mini_notification_seconds(self, seconds=None):
        return f"{self.parse_mini_notification_seconds(seconds if seconds is not None else self.get_mini_notification_seconds())}s"

    def normalize_program_list(self, value):
        normalized = []
        if isinstance(value, dict):
            for name, path in value.items():
                normalized.append(
                    {
                        "name": name,
                        "match_type": "process_name",
                        "value": name,
                        "path": path,
                        "icon_path": "",
                        "target_audio": "headset",
                    }
                )
        elif isinstance(value, list):
            for item in value:
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or item.get("value") or "Unknown"
                match_type = item.get("match_type") or "process_name"
                value_text = item.get("value") or name
                normalized.append(
                    {
                        "name": name,
                        "match_type": match_type,
                        "value": value_text,
                        "path": item.get("path") or "",
                        "icon_path": item.get("icon_path") or "",
                        "target_audio": item.get("target_audio") if item.get("target_audio") in ("speaker", "headset") else "headset",
                    }
                )
        return normalized

    def normalized_program_rule_key(self, program):
        match_type = (program.get("match_type") or "process_name").strip().casefold()
        value = (program.get("value") or "").strip()
        if match_type == "path" and value:
            value = os.path.normcase(os.path.abspath(value))
        else:
            value = value.casefold()
        return match_type, value

    def deduplicate_program_lists(self, auto_list, ask_list):
        seen = set()
        deduped_auto = []
        deduped_ask = []
        for program in auto_list:
            key = self.normalized_program_rule_key(program)
            if key in seen:
                continue
            seen.add(key)
            deduped_auto.append(program)
        for program in ask_list:
            key = self.normalized_program_rule_key(program)
            if key in seen:
                continue
            seen.add(key)
            deduped_ask.append(program)
        return deduped_auto, deduped_ask

    def save_config(self):
        temporary_path = f"{CONFIG_FILE}.tmp"
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(temporary_path, "w", encoding="utf-8") as file:
                json.dump(self.config_data, file, indent=4, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            if os.path.isfile(CONFIG_FILE):
                shutil.copy2(CONFIG_FILE, CONFIG_BACKUP_FILE)
            os.replace(temporary_path, CONFIG_FILE)
        except Exception:
            logging.exception("config save failed file=%s", CONFIG_FILE)
            try:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
            except OSError:
                pass
            raise

    def schedule_log_cleanup(self):
        if self.log_cleanup_after_id:
            try:
                self.after_cancel(self.log_cleanup_after_id)
            except Exception:
                pass
        removed = cleanup_expired_logs()
        if removed:
            logging.info("expired rotated logs removed count=%s retention_days=%s", removed, LOG_RETENTION_DAYS)
        if self.is_running:
            self.log_cleanup_after_id = self.after(LOG_CLEANUP_INTERVAL_MS, self.schedule_log_cleanup)

    def configure_display_scaling(self):
        left, top, right, bottom = self.get_work_area()
        native_scale = self.get_native_display_scale()
        effective_scale = calculate_effective_ui_scale(native_scale, right - left, bottom - top)
        ctk.set_widget_scaling(effective_scale)
        ctk.set_window_scaling(effective_scale)
        self.effective_ui_scale = effective_scale
        settings_width, settings_height = calculate_scaled_window_size(
            SETTINGS_DEFAULT_WIDTH,
            SETTINGS_DEFAULT_HEIGHT,
            effective_scale,
        )
        logging.info(
            "display scaling configured awareness=%s native_scale=%.3f effective_scale=%.3f work_area=%sx%s settings_physical=%sx%s",
            WINDOWS_DPI_AWARENESS,
            native_scale,
            self.effective_ui_scale,
            right - left,
            bottom - top,
            settings_width,
            settings_height,
        )

    def get_native_display_scale(self):
        if sys.platform == "win32":
            try:
                get_dpi_for_window = ctypes.windll.user32.GetDpiForWindow
                get_dpi_for_window.argtypes = [wintypes.HWND]
                get_dpi_for_window.restype = wintypes.UINT
                dpi = int(get_dpi_for_window(wintypes.HWND(self.winfo_id())))
                if dpi > 0:
                    return max(MIN_EFFECTIVE_UI_SCALE, dpi / 96.0)
            except Exception:
                pass
            try:
                get_dpi_for_system = ctypes.windll.user32.GetDpiForSystem
                get_dpi_for_system.restype = wintypes.UINT
                dpi = int(get_dpi_for_system())
                if dpi > 0:
                    return max(MIN_EFFECTIVE_UI_SCALE, dpi / 96.0)
            except Exception:
                pass
        try:
            dpi = float(self.winfo_fpixels("1i"))
            if dpi > 0:
                return max(MIN_EFFECTIVE_UI_SCALE, dpi / 96.0)
        except Exception:
            pass
        return 1.0

    def ui_pixel_scale(self):
        return max(MIN_EFFECTIVE_UI_SCALE, float(getattr(self, "effective_ui_scale", 1.0)))

    def scaled_ui_px(self, value):
        return max(1, round(float(value) * self.ui_pixel_scale()))

    def canvas_font(self, size, bold=False, family=None):
        font_family = family or self.ui_font_family()
        font_size = -self.scaled_ui_px(size)
        return (font_family, font_size, "bold") if bold else (font_family, font_size)

    def logical_widget_width(self, widget, fallback):
        try:
            physical_width = widget.winfo_width()
            if physical_width > 1:
                return max(1, round(physical_width / self.ui_pixel_scale()))
        except Exception:
            pass
        return int(fallback)

    def apply_window_icon(self, window=None):
        window = window or self
        try:
            window.iconphoto(True, self.app_window_icon_photo)
        except Exception:
            pass
        if os.path.exists(APP_ICON_ICO_FILE):
            try:
                window.iconbitmap(default=APP_ICON_ICO_FILE)
            except Exception:
                try:
                    window.iconbitmap(APP_ICON_ICO_FILE)
                except Exception:
                    pass

    def set_ui_mode(self, mode):
        if mode == "mini":
            self.is_mini = True
            self.minsize(MINI_WIDTH, MINI_HEIGHT)
            self.maxsize(MINI_WIDTH, MINI_HEIGHT)
            self.resizable(False, False)
            self.overrideredirect(True)
            self.attributes("-topmost", True)
            self.set_mini_geometry()
        else:
            self.is_mini = False
            self.configure(fg_color=SETTINGS_GRADIENT_END)
            try:
                self.tk.call(self._w, "configure", "-background", SETTINGS_GRADIENT_END)
            except Exception:
                pass
            self.maxsize(0, 0)
            self.minsize(SETTINGS_MIN_WIDTH, SETTINGS_MIN_HEIGHT)
            self.resizable(False, False)
            self.overrideredirect(False)
            self.attributes("-topmost", False)
            self.set_settings_geometry()
            self.apply_window_icon(self)

    def set_mini_geometry(self, extra_height=0):
        width, height, x, y = self.get_mini_geometry_parts(extra_height=extra_height)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def get_mini_geometry_parts(self, extra_height=0, y_offset=0):
        left, top, right, bottom = self.get_work_area()
        height = MINI_HEIGHT + extra_height
        physical_width = round(MINI_WIDTH * self.ui_pixel_scale())
        physical_height = round(height * self.ui_pixel_scale())
        x = max(left, right - physical_width)
        y = max(top, bottom - physical_height + y_offset)
        return MINI_WIDTH, height, x, y

    def get_mini_hidden_y(self):
        _, _, _, bottom = self.get_work_area()
        return bottom

    def cancel_mini_animation(self):
        if self.mini_animation_after_id:
            try:
                self.after_cancel(self.mini_animation_after_id)
            except Exception:
                pass
            self.mini_animation_after_id = None

    def animate_mini_in(self, from_current=False):
        if not self.is_mini:
            return
        logging.info("mini animate in start visible=%s pinned=%s ask=%s notification=%s", self.winfo_viewable(), self.mini_pinned_by_user, self.ask_active, self.notification_active)
        self.cancel_mini_animation()
        width, height, final_x, final_y = self.get_mini_geometry_parts()
        hidden_y = self.get_mini_hidden_y()
        if from_current and self.winfo_viewable():
            start_y = max(final_y, min(self.winfo_y(), hidden_y))
        else:
            start_y = hidden_y
        self.geometry(f"{width}x{height}+{final_x}+{start_y}")
        self.deiconify()
        self.lift()
        if start_y <= final_y:
            self.geometry(f"{width}x{height}+{final_x}+{final_y}")
            self.mini_animation_after_id = None
            logging.info("mini animate in settled without movement")
            return
        self.mini_animation_after_id = self.after(
            MINI_ANIMATION_INTERVAL_MS,
            lambda: self.animate_mini_to(width, height, final_x, final_x, start_y, final_y, 1, hide_after=False),
        )

    def animate_mini_out(self, on_complete=None):
        if not self.is_mini or not self.winfo_viewable():
            logging.info("mini animate out skipped is_mini=%s visible=%s", self.is_mini, self.winfo_viewable())
            self.withdraw()
            if on_complete:
                on_complete()
            return
        logging.info("mini animate out start pinned=%s ask=%s notification=%s", self.mini_pinned_by_user, self.ask_active, self.notification_active)
        self.cancel_mini_animation()
        width, height, _, final_y = self.get_mini_geometry_parts()
        start_x = self.winfo_x()
        hidden_y = self.get_mini_hidden_y()
        start_y = max(final_y, min(self.winfo_y(), hidden_y))
        end_y = hidden_y
        self.geometry(f"{width}x{height}+{start_x}+{start_y}")
        self.mini_animation_after_id = self.after(
            MINI_ANIMATION_INTERVAL_MS,
            lambda: self.animate_mini_to(width, height, start_x, start_x, start_y, end_y, 1, hide_after=True, on_complete=on_complete),
        )

    def animate_mini_to(self, width, height, start_x, end_x, start_y, end_y, step, hide_after, on_complete=None):
        progress = min(1, step / MINI_ANIMATION_STEPS)
        eased = progress * progress * progress * (progress * (progress * 6 - 15) + 10)
        raw_x = start_x + (end_x - start_x) * eased
        raw_y = start_y + (end_y - start_y) * eased
        min_x, max_x = sorted((start_x, end_x))
        min_y, max_y = sorted((start_y, end_y))
        x = int(max(min_x, min(max_x, round(raw_x))))
        y = int(max(min_y, min(max_y, round(raw_y))))
        if progress >= 1:
            x = int(end_x)
            y = int(end_y)
        self.geometry(f"{width}x{height}+{x}+{y}")

        if progress >= 1:
            self.mini_animation_after_id = None
            if hide_after:
                self.withdraw()
            logging.info("mini animation complete hide_after=%s visible=%s", hide_after, self.winfo_viewable())
            if on_complete:
                on_complete()
            return

        self.mini_animation_after_id = self.after(
            MINI_ANIMATION_INTERVAL_MS,
            lambda: self.animate_mini_to(width, height, start_x, end_x, start_y, end_y, step + 1, hide_after, on_complete=on_complete),
        )

    def get_work_area(self):
        if sys.platform == "win32":
            try:
                user32 = ctypes.windll.user32
                monitor_from_window = user32.MonitorFromWindow
                monitor_from_window.argtypes = [wintypes.HWND, wintypes.DWORD]
                monitor_from_window.restype = wintypes.HMONITOR
                monitor = monitor_from_window(wintypes.HWND(self.winfo_id()), MONITOR_DEFAULTTONEAREST)
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(info)
                if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                    return info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom
            except Exception:
                pass
        rect = wintypes.RECT()
        try:
            ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

    def set_settings_geometry(self):
        geometry = self.config_data.get("settings_geometry")
        try:
            if geometry:
                self.geometry(self.normalize_settings_geometry(geometry))
            else:
                self.center_settings_geometry(SETTINGS_DEFAULT_WIDTH, SETTINGS_DEFAULT_HEIGHT)
        except Exception:
            self.center_settings_geometry(SETTINGS_DEFAULT_WIDTH, SETTINGS_DEFAULT_HEIGHT)

    def normalize_settings_geometry(self, geometry):
        parts = geometry.split("+", 1)
        size = parts[0]
        width_text, height_text = size.split("x", 1)
        width = min(SETTINGS_DEFAULT_WIDTH, max(SETTINGS_MIN_WIDTH, int(width_text)))
        height = min(SETTINGS_DEFAULT_HEIGHT, max(SETTINGS_MIN_HEIGHT, int(height_text)))
        return self.center_settings_geometry_string(width, height)

    def center_settings_geometry(self, width, height):
        self.geometry(self.center_settings_geometry_string(width, height))

    def center_settings_geometry_string(self, width, height):
        return centered_scaled_geometry(width, height, self.ui_pixel_scale(), self.get_work_area())

    def remember_settings_geometry(self):
        if not self.is_mini:
            self.update_idletasks()
            scale = self.ui_pixel_scale()
            width = max(SETTINGS_MIN_WIDTH, round(self.winfo_width() / scale))
            height = max(SETTINGS_MIN_HEIGHT, round(self.winfo_height() / scale))
            self.config_data["settings_geometry"] = f"{width}x{height}"

    def get_window_frame_handle(self, window=None):
        window = window or self
        window.update_idletasks()
        raw_handle = None
        try:
            raw_handle = window.frame()
        except Exception:
            pass
        if not raw_handle:
            raw_handle = window.winfo_id()

        try:
            hwnd_value = int(raw_handle, 0) if isinstance(raw_handle, str) else int(raw_handle)
        except Exception:
            hwnd_value = int(window.winfo_id())

        try:
            user32 = ctypes.windll.user32
            user32.GetAncestor.argtypes = [wintypes.HWND, ctypes.c_uint]
            user32.GetAncestor.restype = wintypes.HWND
            root_hwnd = user32.GetAncestor(wintypes.HWND(hwnd_value), GA_ROOT)
            if root_hwnd:
                return wintypes.HWND(root_hwnd)
        except Exception:
            pass
        return wintypes.HWND(hwnd_value)

    def apply_dark_title_bar(self, window=None):
        try:
            hwnd = self.get_window_frame_handle(window)
            dwmapi = ctypes.windll.dwmapi
            dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
            dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long

            enabled = ctypes.c_int(1)
            for attribute in (DWMWA_USE_IMMERSIVE_DARK_MODE, DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1):
                dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled))

            corner_preference = ctypes.c_int(DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(corner_preference), ctypes.sizeof(corner_preference))

            caption_color = ctypes.c_uint(0x181818)
            text_color = ctypes.c_uint(0xFFFFFF)
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(caption_color), ctypes.sizeof(caption_color))
            dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, ctypes.byref(text_color), ctypes.sizeof(text_color))
        except Exception:
            pass

    def install_settings_background(self):
        try:
            self.tk.call(self._w, "configure", "-background", SETTINGS_GRADIENT_END)
        except Exception:
            pass
        self.settings_bg_label = None
        self._settings_bg_size = None

    def update_settings_background(self, event=None):
        if self.is_mini or not hasattr(self, "settings_bg_label"):
            return
        if not self.widget_exists(self.settings_bg_label):
            return
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        if getattr(self, "_settings_bg_size", None) == (width, height):
            return
        self._settings_bg_size = (width, height)
        self.settings_bg_photo = make_settings_gradient_image(width, height)
        self.settings_bg_label.configure(image=self.settings_bg_photo)
        self.settings_bg_label.lower()

    def center_child_geometry(self, width, height):
        self.update_idletasks()
        parent_width = self.winfo_width() if self.winfo_width() > 1 else self.winfo_screenwidth()
        parent_height = self.winfo_height() if self.winfo_height() > 1 else self.winfo_screenheight()
        parent_x = self.winfo_x() if self.winfo_viewable() else 0
        parent_y = self.winfo_y() if self.winfo_viewable() else 0
        physical_width = round(width * self.ui_pixel_scale())
        physical_height = round(height * self.ui_pixel_scale())
        x = parent_x + max(0, (parent_width - physical_width) // 2)
        y = parent_y + max(0, (parent_height - physical_height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def center_screen_geometry(self, width, height):
        return centered_scaled_geometry(width, height, self.ui_pixel_scale(), self.get_work_area())

    def bind_popup_drag(self, window, handle):
        drag = {"x": 0, "y": 0}

        def start(event):
            drag["x"] = event.x
            drag["y"] = event.y

        def move(event):
            window.geometry(f"+{event.x_root - drag['x']}+{event.y_root - drag['y']}")

        handle.bind("<ButtonPress-1>", start)
        handle.bind("<B1-Motion>", move)

    def create_popup_titlebar(self, window, close_command=None, allow_minimize=True):
        close_command = close_command or window.destroy
        titlebar = ctk.CTkFrame(window, fg_color=TITLE_BAR_BG, height=28, corner_radius=0)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)
        self.bind_popup_drag(window, titlebar)

        ctk.CTkLabel(titlebar, text="", image=self.icons["app"], width=18, height=18).pack(side="left", padx=(7, 7), pady=5)
        ctk.CTkLabel(titlebar, text="Auto Audio", font=("Segoe UI", 11), text_color="#E8E8E8").pack(side="left")

        ctk.CTkButton(titlebar, text="", image=self.icons["close"], width=28, height=24, fg_color="transparent", hover_color="#333333", command=close_command).pack(side="right", padx=(0, 4))
        if allow_minimize:
            ctk.CTkButton(titlebar, text="", image=self.icons["minimize"], width=28, height=24, fg_color="transparent", hover_color="#333333", command=window.iconify).pack(side="right", padx=2)
        ctk.CTkButton(titlebar, text="", image=self.icons["gear"], width=30, height=24, fg_color="transparent", hover_color="#333333", command=lambda: self.switch_mode("settings")).pack(side="right", padx=2)
        return titlebar

    def prepare_popup(self, window, title, width, height, grab=True, close_command=None, allow_minimize=True, center_on_screen=False):
        window.title(title)
        self.apply_window_icon(window)
        window.geometry(self.center_screen_geometry(width, height) if center_on_screen else self.center_child_geometry(width, height))
        if self.winfo_viewable():
            window.transient(self)
        window.overrideredirect(True)
        window.configure(fg_color=WINDOW_BG)
        self.create_popup_titlebar(window, close_command=close_command, allow_minimize=allow_minimize)
        window.deiconify()
        window.attributes("-topmost", True)
        window.lift()
        window.focus_force()
        if grab:
            window.grab_set()

    def refresh_audio_device_cache(self, include_input=False):
        comtypes_module = initialize_com_for_thread()
        try:
            import warnings

            warnings.filterwarnings("ignore")
            from pycaw.pycaw import AudioUtilities
            from pycaw.utils import AudioDeviceState

            output_devices = []
            output_ids = {}
            for device in AudioUtilities.GetAllDevices():
                try:
                    name = getattr(device, "FriendlyName", None) or getattr(device, "friendly_name", None)
                    if not name:
                        continue
                    flow = AudioUtilities.GetEndpointDataFlow(device.id)
                    if flow == "eRender":
                        output_ids[name] = device.id
                        if getattr(device, "state", None) == AudioDeviceState.Active and name not in output_devices:
                            output_devices.append(name)
                except Exception:
                    continue
            with self.device_cache_lock:
                self.audio_device_names = output_devices
                self.audio_device_ids = output_ids
            for mode in ("speaker", "headset"):
                name = self.config_data.get(f"{mode}_name") or ""
                if name in output_ids and self.config_data.get(f"{mode}_id") != output_ids[name]:
                    self.config_data[f"{mode}_id"] = output_ids[name]
                    self.audio_device_id_cache_dirty = True
            self.last_device_cache_refresh_time = time.monotonic()
            return output_devices, []
        except Exception:
            logging.exception("audio device cache refresh failed")
            with self.device_cache_lock:
                return list(getattr(self, "audio_device_names", [])), []
        finally:
            uninitialize_com_for_thread(comtypes_module)

    def refresh_audio_device_cache_if_stale(self, force=False):
        now = time.monotonic()
        if force or now - getattr(self, "last_device_cache_refresh_time", 0) >= DEVICE_CACHE_REFRESH_INTERVAL_SECONDS:
            before_outputs = tuple(getattr(self, "audio_device_names", []))
            self.refresh_audio_device_cache(include_input=False)
            self.sync_audio_config_with_devices(save_changes=True)
            changed = before_outputs != tuple(getattr(self, "audio_device_names", []))
            if changed:
                logging.info("audio device list changed devices=%s", self.audio_device_names)
                self.after(0, lambda state=self.last_state: self.update_mini_buttons_ui(state))
            return changed
        return False

    def get_output_device_names(self, force=False):
        if force or not getattr(self, "audio_device_names", None):
            self.refresh_audio_device_cache(include_input=False)
        with self.device_cache_lock:
            return list(self.audio_device_names)

    def audio_device_hints(self, mode):
        if mode == "headset":
            return (
                "headset",
                "headphone",
                "headphones",
                "earbuds",
                "earphone",
                "arctis",
                "razer",
                "logitech",
                "wireless",
                "헤드셋",
                "헤드폰",
                "이어폰",
                "이어버드",
            )
        return (
            "speaker",
            "speakers",
            "realtek",
            "monitor",
            "display",
            "hdmi",
            "pebble",
            "스피커",
            "모니터",
        )

    def infer_audio_device_mode(self, name):
        lowered = (name or "").casefold()
        if not lowered:
            return None
        speaker_score = sum(1 for hint in self.audio_device_hints("speaker") if hint in lowered)
        headset_score = sum(1 for hint in self.audio_device_hints("headset") if hint in lowered)
        if speaker_score > headset_score:
            return "speaker"
        if headset_score > speaker_score:
            return "headset"
        return None

    def looks_like_corrupt_device_name(self, name):
        if not isinstance(name, str) or not name:
            return False
        if "\ufffd" in name:
            return True
        if "?" in name and any(ord(char) > 127 for char in name):
            return True
        if name.count("?") >= 2:
            return True
        return any(token in name for token in ("ㅽ", "ㅻ", "而", "뵾", "뱶"))

    def pick_audio_device(self, mode, devices, exclude=None):
        devices = [name for name in devices if name and name != "No audio device found"]
        if not devices:
            return ""
        excluded = {exclude} if exclude else set()
        candidates = [name for name in devices if name not in excluded] or devices
        hints = self.audio_device_hints(mode)
        for name in candidates:
            lowered = name.lower()
            if any(hint in lowered for hint in hints):
                return name
        return candidates[0]

    def sync_audio_config_with_devices(self, save_changes=False):
        devices = [name for name in getattr(self, "audio_device_names", []) if name]
        if not devices:
            return False
        if "offline_device_log_keys" not in self.__dict__:
            self.offline_device_log_keys = set()

        changed = False
        speaker = self.config_data.get("speaker_name") or ""
        headset = self.config_data.get("headset_name") or ""
        speaker_hint = self.infer_audio_device_mode(speaker)
        headset_hint = self.infer_audio_device_mode(headset)

        if (
            speaker in devices
            and headset in devices
            and speaker != headset
            and speaker_hint == "headset"
            and headset_hint == "speaker"
        ):
            logging.warning("audio config appears swapped; correcting speaker=%s headset=%s", speaker, headset)
            speaker, headset = headset, speaker
            self.config_data["speaker_name"] = speaker
            self.config_data["headset_name"] = headset
            changed = True

        if speaker not in devices:
            if self.looks_like_corrupt_device_name(speaker):
                candidate = self.pick_audio_device("speaker", devices, exclude=headset)
                if candidate and self.infer_audio_device_mode(candidate) == "speaker":
                    logging.warning("configured speaker output name was corrupt; repairing speaker=%s -> %s", speaker, candidate)
                    speaker = candidate
                    self.config_data["speaker_name"] = speaker
                    changed = True
                else:
                    logging.warning("configured speaker output name appears corrupt but no speaker-like active device is available; keeping saved value speaker=%s", speaker)
            elif speaker and speaker != "No audio device found":
                log_key = ("speaker", speaker)
                if log_key not in self.offline_device_log_keys:
                    logging.warning("configured speaker output is not currently active; keeping saved value speaker=%s", speaker)
                    self.offline_device_log_keys.add(log_key)
            else:
                speaker = self.pick_audio_device("speaker", devices)
                self.config_data["speaker_name"] = speaker
                changed = True
        elif self.infer_audio_device_mode(speaker) == "headset" and len(devices) > 1:
            self.offline_device_log_keys.discard(("speaker", speaker))
            candidate = self.pick_audio_device("speaker", devices, exclude=headset)
            if candidate != speaker and self.infer_audio_device_mode(candidate) == "speaker":
                logging.warning("speaker output looked like headset; correcting speaker=%s -> %s", speaker, candidate)
                speaker = candidate
                self.config_data["speaker_name"] = speaker
                changed = True
        else:
            self.offline_device_log_keys.discard(("speaker", speaker))

        if headset not in devices:
            if self.looks_like_corrupt_device_name(headset):
                candidate = self.pick_audio_device("headset", devices, exclude=speaker)
                if candidate and self.infer_audio_device_mode(candidate) == "headset":
                    logging.warning("configured headset output name was corrupt; repairing headset=%s -> %s", headset, candidate)
                    headset = candidate
                    self.config_data["headset_name"] = headset
                    changed = True
                else:
                    logging.warning("configured headset output name appears corrupt but no headset-like active device is available; keeping saved value headset=%s", headset)
            elif headset and headset != "No audio device found":
                log_key = ("headset", headset)
                if log_key not in self.offline_device_log_keys:
                    logging.warning("configured headset output is not currently active; keeping saved value headset=%s", headset)
                    self.offline_device_log_keys.add(log_key)
            else:
                headset = self.pick_audio_device("headset", devices, exclude=speaker)
                self.config_data["headset_name"] = headset
                changed = True
        elif len(devices) > 1 and headset == speaker:
            self.offline_device_log_keys.discard(("headset", headset))
            speaker = self.pick_audio_device("speaker", devices)
            self.config_data["speaker_name"] = speaker
            headset = self.pick_audio_device("headset", devices, exclude=speaker)
            self.config_data["headset_name"] = headset
            changed = True
        elif self.infer_audio_device_mode(headset) == "speaker" and len(devices) > 1:
            self.offline_device_log_keys.discard(("headset", headset))
            candidate = self.pick_audio_device("headset", devices, exclude=speaker)
            if candidate != headset and self.infer_audio_device_mode(candidate) == "headset":
                logging.warning("headset output looked like speaker; correcting headset=%s -> %s", headset, candidate)
                headset = candidate
                self.config_data["headset_name"] = headset
                changed = True
        else:
            self.offline_device_log_keys.discard(("headset", headset))

        if changed and save_changes:
            self.save_config()
        return changed

    def draw_ui(self):
        self.unbind("<FocusOut>")
        for widget in self.winfo_children():
            widget.destroy()

        if self.is_mini:
            self.draw_mini_ui()
        else:
            self.draw_settings_ui()

    def create_marquee_label(self, parent, text, font_tuple, text_color, bg_color, height, bg_origin=None):
        scale = self.ui_pixel_scale()
        scaled_height = max(1, round(height * scale))
        font_size = abs(int(font_tuple[1])) if len(font_tuple) > 1 else 11
        scaled_font = (font_tuple[0], -max(1, round(font_size * scale)), *font_tuple[2:])
        scaled_origin = tuple(round(value * scale) for value in bg_origin) if bg_origin else None
        canvas = tk.Canvas(parent, height=scaled_height, width=1, bg=bg_color, bd=0, highlightthickness=0, relief="flat")
        canvas._marquee_config = {
            "text": text or "",
            "font": scaled_font,
            "text_color": text_color,
            "bg_color": bg_color,
            "bg_origin": scaled_origin,
            "height": scaled_height,
            "scale": scale,
            "offset": 0,
            "direction": 1,
            "pause": MARQUEE_EDGE_PAUSE_TICKS,
            "job": None,
        }
        canvas.bind("<Configure>", lambda event, c=canvas: self.reset_marquee(c))
        self.render_marquee(canvas)
        return canvas

    def reset_marquee(self, canvas):
        if not self.widget_exists(canvas):
            return
        self.cancel_marquee(canvas)
        config = canvas._marquee_config
        config["offset"] = 0
        config["direction"] = 1
        config["pause"] = MARQUEE_EDGE_PAUSE_TICKS
        self.render_marquee(canvas)

    def cancel_marquee(self, canvas):
        try:
            job = canvas._marquee_config.get("job")
            if job:
                canvas.after_cancel(job)
            canvas._marquee_config["job"] = None
        except Exception:
            pass

    def render_marquee(self, canvas):
        try:
            if not self.widget_exists(canvas):
                return
            config = canvas._marquee_config
            self.cancel_marquee(canvas)
            width = canvas.winfo_width()
            height = config["height"]
            text = config["text"]
            canvas.delete("all")
            if width <= 1 or not text:
                return
            if config.get("bg_origin"):
                bg_x, bg_y = config["bg_origin"]
                photo = make_mini_background_slice(width, height, bg_x, bg_y, config.get("scale", 1.0))
                canvas._marquee_bg_photo = photo
                canvas.create_image(0, 0, image=photo, anchor="nw")

            text_font = config["font"]
            text_width = self.measure_text(text, text_font)
            fade_width = max(1, round(MARQUEE_FADE_WIDTH * config.get("scale", 1.0)))
            max_offset = max(0, text_width - width + fade_width)
            offset = min(config["offset"], max_offset)
            config["offset"] = offset
            canvas.create_text(
                -offset,
                height / 2,
                text=text,
                fill=config["text_color"],
                font=text_font,
                anchor="w",
            )

            if max_offset > 0:
                self.draw_marquee_fade(canvas, config["bg_color"], width, height, config.get("bg_origin"))
                config["job"] = canvas.after(MARQUEE_INTERVAL_MS, lambda c=canvas: self.advance_marquee(c))
            else:
                config["job"] = None
        except Exception:
            pass

    def advance_marquee(self, canvas):
        try:
            if not self.widget_exists(canvas):
                return
            config = canvas._marquee_config
            width = canvas.winfo_width()
            fade_width = max(1, round(MARQUEE_FADE_WIDTH * config.get("scale", 1.0)))
            max_offset = max(0, self.measure_text(config["text"], config["font"]) - width + fade_width)
            if max_offset <= 0:
                self.render_marquee(canvas)
                return

            if config["pause"] > 0:
                config["pause"] -= 1
            else:
                config["offset"] += config["direction"] * max(1, round(MARQUEE_STEP_PX * config.get("scale", 1.0)))
                if config["offset"] >= max_offset:
                    config["offset"] = max_offset
                    config["direction"] = -1
                    config["pause"] = MARQUEE_EDGE_PAUSE_TICKS
                elif config["offset"] <= 0:
                    config["offset"] = 0
                    config["direction"] = 1
                    config["pause"] = MARQUEE_EDGE_PAUSE_TICKS
            self.render_marquee(canvas)
        except Exception:
            pass

    def measure_text(self, text, font_tuple):
        try:
            weight = font_tuple[2] if len(font_tuple) > 2 else "normal"
            text_font = font.Font(family=font_tuple[0], size=font_tuple[1], weight=weight)
            return text_font.measure(text)
        except Exception:
            return len(text) * 8

    def fit_text_to_width(self, text, font_tuple, max_width):
        text = text or ""
        if self.measure_text(text, font_tuple) <= max_width:
            return text
        ellipsis = "..."
        while text and self.measure_text(text + ellipsis, font_tuple) > max_width:
            text = text[:-1]
        return text + ellipsis if text else ellipsis

    def update_mini_detect_canvas(self, name=None, icon=None):
        if not self.widget_exists(getattr(self, "mini_canvas", None)):
            return
        display_name = name or self.tr("no_program_detected")
        display_icon = icon or self.icons.get("no_app")
        scale = self.ui_pixel_scale()
        font_tuple = self.canvas_font(17, bold=True)
        max_text_width = max(self.scaled_ui_px(40), round((MINI_WIDTH - 76 - 168 - 30) * scale))
        self.mini_canvas.itemconfigure(self.mini_name_item, text=self.fit_text_to_width(display_name, font_tuple, max_text_width))
        self.mini_detected_photo = ctk_image_to_photo(display_icon, scale=scale)
        self.mini_canvas.itemconfigure(self.mini_icon_item, image=self.mini_detected_photo)

    def draw_marquee_fade(self, canvas, bg_color, width, height, bg_origin=None):
        scale = canvas._marquee_config.get("scale", 1.0) if hasattr(canvas, "_marquee_config") else 1.0
        fade_width = min(max(1, round(MARQUEE_FADE_WIDTH * scale)), max(1, width))
        if bg_origin:
            bg_x, bg_y = bg_origin
            background = create_linear_gradient(max(1, round(MINI_WIDTH * scale)), max(1, round(MINI_HEIGHT * scale)), MINI_BG_GRADIENT_START, MINI_BG_GRADIENT_END, angle_degrees=91)
            image = background.crop((bg_x + width - fade_width, bg_y, bg_x + width, bg_y + height)).convert("RGBA")
            alpha_mask = Image.new("L", (fade_width, height), 0)
            mask_draw = ImageDraw.Draw(alpha_mask)
            for x in range(fade_width):
                alpha = int(255 * ((x + 1) / fade_width))
                mask_draw.line((x, 0, x, height), fill=alpha)
            image.putalpha(alpha_mask)
        else:
            rgb = tuple(int(bg_color[index:index + 2], 16) for index in (1, 3, 5))
            image = Image.new("RGBA", (fade_width, height), (*rgb, 0))
            draw = ImageDraw.Draw(image)
            for x in range(fade_width):
                alpha = int(255 * ((x + 1) / fade_width))
                draw.line((x, 0, x, height), fill=(*rgb, alpha))
        photo = ImageTk.PhotoImage(image)
        canvas._marquee_fade_photo = photo
        canvas.create_image(width - fade_width, 0, image=photo, anchor="nw")

    def draw_mini_ui(self):
        self.configure(fg_color=MINI_BG_FALLBACK)
        self.bind("<FocusOut>", self.on_mini_focus_out)

        if self.ask_active:
            self.draw_ask_mini_ui()
            return

        scale = self.ui_pixel_scale()
        px = lambda value: max(1, round(value * scale))
        mini_canvas = tk.Canvas(self, width=px(MINI_WIDTH), height=px(MINI_HEIGHT), highlightthickness=0, bd=0, bg=MINI_BG_FALLBACK)
        self.mini_canvas = mini_canvas
        mini_canvas.pack(fill="both", expand=True)
        self.mini_bg_photo = make_mini_background_image(scale)
        mini_canvas.create_image(0, 0, image=self.mini_bg_photo, anchor="nw")
        mini_canvas.bind("<ButtonPress-1>", self.start_move)
        mini_canvas.bind("<B1-Motion>", self.do_move)

        header = ctk.CTkFrame(mini_canvas, fg_color="transparent", height=28, corner_radius=0)
        mini_canvas.create_window(0, 0, window=header, anchor="nw", width=px(MINI_WIDTH), height=px(28))
        header.pack_propagate(False)
        header.bind("<ButtonPress-1>", self.start_move)
        header.bind("<B1-Motion>", self.do_move)

        ctk.CTkLabel(header, text="", image=self.icons["app"], width=18, height=18).pack(side="left", padx=(7, 7), pady=5)
        ctk.CTkLabel(header, text="Auto Audio", font=("Segoe UI", 11), text_color="#E8E8E8").pack(side="left")
        ctk.CTkButton(header, text="", image=self.icons["close"], width=28, height=24, fg_color="transparent", hover_color="#333333", command=self.hide_to_tray).pack(side="right", padx=(0, 4))
        ctk.CTkButton(header, text="", image=self.icons["minimize"], width=28, height=24, fg_color="transparent", hover_color="#333333", command=self.hide_to_tray).pack(side="right", padx=2)
        ctk.CTkButton(header, text="", image=self.icons["gear"], width=34, height=24, fg_color="transparent", hover_color="#333333", command=lambda: self.switch_mode("settings")).pack(side="right", padx=4)

        self.mini_detected_photo = ctk_image_to_photo(self.current_detected_icon, scale=scale)
        self.mini_icon_item = mini_canvas.create_image(px(38), px(62), image=self.mini_detected_photo)
        self.mini_name_item = mini_canvas.create_text(px(76), px(62), text="", fill="white", font=self.canvas_font(17, bold=True, family="Segoe UI"), anchor="w")
        self.update_mini_detect_canvas(self.current_detected_name, self.current_detected_icon)

        button_frame = ctk.CTkFrame(mini_canvas, fg_color="transparent", bg_color="transparent")
        self.mini_button_frame = button_frame
        mini_canvas.create_window(px(MINI_WIDTH - 12), px(62), window=button_frame, anchor="e", width=px((MINI_DEVICE_BUTTON_WIDTH * 2) + MINI_DEVICE_BUTTON_GAP), height=px(MINI_DEVICE_BUTTON_HEIGHT))

        self.speaker_btn = ctk.CTkLabel(button_frame, text="", image=self.mini_button_images["speaker_inactive"], width=MINI_DEVICE_BUTTON_WIDTH, height=MINI_DEVICE_BUTTON_HEIGHT)
        self.speaker_btn.bind("<Button-1>", lambda event: self.manual_set_audio("speaker"))
        self.speaker_btn.pack(side="left", padx=(0, MINI_DEVICE_BUTTON_GAP))

        self.headset_btn = ctk.CTkLabel(button_frame, text="", image=self.mini_button_images["headset_inactive"], width=MINI_DEVICE_BUTTON_WIDTH, height=MINI_DEVICE_BUTTON_HEIGHT)
        self.headset_btn.bind("<Button-1>", lambda event: self.manual_set_audio("headset"))
        self.headset_btn.pack(side="left")

        self.update_mini_buttons_ui(self.last_state)
        if self.audio_switching:
            self.show_audio_switching_ui(self.audio_switch_target, redraw=False)

    def draw_ask_mini_ui(self):
        self.configure(fg_color=MINI_BG_FALLBACK)
        scale = self.ui_pixel_scale()
        px = lambda value: max(1, round(value * scale))
        target = self.ask_target or "headset"
        program_name = self.ask_program.get("name", "Program") if self.ask_program else "Program"

        mini_canvas = tk.Canvas(self, width=px(MINI_WIDTH), height=px(MINI_HEIGHT), highlightthickness=0, bd=0, bg=MINI_BG_FALLBACK)
        mini_canvas.pack(fill="both", expand=True)
        self.ask_mini_bg_photo = make_mini_background_image(scale)
        mini_canvas.create_image(0, 0, image=self.ask_mini_bg_photo, anchor="nw")
        mini_canvas.bind("<ButtonPress-1>", self.start_move)
        mini_canvas.bind("<B1-Motion>", self.do_move)

        self.ask_icon_photo = make_ui_icon_photo(target, 28, scale=scale)
        mini_canvas.create_image(px(91), px(47), image=self.ask_icon_photo)
        mini_canvas.create_text(px(117), px(32), text=self.tr("switch_to", mode=self.audio_label(target)), fill="white", font=self.canvas_font(15, bold=True), anchor="w")
        self.ask_label_canvas = mini_canvas
        self.ask_label_item = mini_canvas.create_text(px(117), px(62), text=program_name, fill="#B8B8B8", font=self.canvas_font(11, family="Segoe UI"), anchor="w")

        self.ask_yes_button_photo = make_ask_button_photo(self.tr("yes"), ACTIVE_COLOR, text_color=(255, 255, 255, 255), bold=True, scale=scale)
        self.ask_no_button_photo = make_ask_button_photo(self.tr("no"), "#444444", scale=scale)
        yes_button = mini_canvas.create_image(px(355), px(49), image=self.ask_yes_button_photo)
        no_button = mini_canvas.create_image(px(433), px(49), image=self.ask_no_button_photo)
        mini_canvas.tag_bind(yes_button, "<Button-1>", lambda event: self.accept_ask_prompt(target))
        mini_canvas.tag_bind(no_button, "<Button-1>", lambda event: self.dismiss_ask_prompt(immediate=True))

    def bind_ask_keyboard_shortcuts(self):
        self.bind_all("<Return>", self.handle_ask_enter_key)
        self.bind_all("<KP_Enter>", self.handle_ask_enter_key)
        self.bind_all("<Escape>", self.handle_ask_escape_key)

    def unbind_ask_keyboard_shortcuts(self):
        for key_sequence in ("<Return>", "<KP_Enter>", "<Escape>"):
            try:
                self.unbind_all(key_sequence)
            except Exception:
                pass

    def handle_ask_enter_key(self, event=None):
        if not self.ask_active or self.ask_resolving:
            return
        self.accept_ask_prompt(self.ask_target or "headset")
        return "break"

    def handle_ask_escape_key(self, event=None):
        if not self.ask_active or self.ask_resolving:
            return
        self.dismiss_ask_prompt(immediate=True)
        return "break"

    def draw_settings_ui(self):
        started_at = time.perf_counter()
        self.log_settings_event("draw_settings_begin", mode="settings")
        self.configure(fg_color=SETTINGS_GRADIENT_END)
        self.device_controls = {}
        self.install_settings_background()
        device_options = self.build_device_options()

        bottom = ctk.CTkFrame(self, fg_color="transparent", bg_color=SETTINGS_GRADIENT_END)
        ctk.CTkButton(bottom, text=self.tr("save"), height=UI_CONTROL_HEIGHT_LARGE, fg_color=ACTIVE_COLOR, hover_color=ACTIVE_HOVER_COLOR, text_color="white", corner_radius=UI_RADIUS_CONTROL, command=self.save_and_close).pack(fill="x", padx=UI_SPACE_MD, pady=UI_SPACE_MD)
        bottom.pack(side="bottom", fill="x", padx=0, pady=0)

        body = ctk.CTkFrame(self, fg_color="transparent", bg_color=SETTINGS_GRADIENT_END, corner_radius=0)
        body.pack(side="top", fill="both", expand=True, padx=UI_SPACE_MD, pady=(UI_SPACE_MD, 0))
        body.grid_columnconfigure(0, weight=0, minsize=SETTINGS_LEFT_WIDTH)
        body.grid_columnconfigure(1, weight=1, minsize=SETTINGS_RIGHT_WIDTH)
        body.grid_rowconfigure(0, weight=1)

        left_column = ctk.CTkFrame(body, fg_color="transparent", bg_color=SETTINGS_GRADIENT_END, corner_radius=0, width=SETTINGS_LEFT_WIDTH)
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, UI_SPACE_SM // 2))

        right_column = ctk.CTkFrame(body, fg_color="transparent", bg_color=SETTINGS_GRADIENT_END, corner_radius=0)
        right_column.grid(row=0, column=1, sticky="nsew", padx=(UI_SPACE_SM // 2, 0))

        settings_panel = ctk.CTkFrame(left_column, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_GRADIENT_END, corner_radius=SETTINGS_PANEL_RADIUS, border_width=0)
        settings_panel.pack(fill="both", expand=True, padx=0, pady=(0, 0))
        settings_content = ctk.CTkFrame(settings_panel, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        settings_content.pack(fill="x", padx=UI_SPACE_LG, pady=(UI_SPACE_MD, UI_SPACE_LG))

        settings_header = ctk.CTkFrame(settings_content, fg_color="transparent", bg_color="transparent", corner_radius=0)
        settings_header.pack(fill="x", padx=0, pady=(0, 8))
        ctk.CTkLabel(settings_header, text=self.tr("settings"), font=(self.ui_font_family(), 22, "bold"), text_color="white", fg_color="transparent", bg_color="transparent").pack(side="left", anchor="w")
        self.audio_refresh_button = ctk.CTkButton(
            settings_header,
            text=self.tr("refresh"),
            width=82,
            height=UI_CONTROL_HEIGHT_COMPACT,
            fg_color=CONTROL_BG,
            hover_color=CONTROL_HOVER,
            text_color="white",
            corner_radius=UI_RADIUS_CONTROL,
            font=(self.ui_font_family(), 12),
            command=self.refresh_settings_devices_async,
        )
        self.audio_refresh_button.pack(side="right", pady=(2, 0))

        device_frame = ctk.CTkFrame(settings_content, fg_color="transparent", bg_color="transparent")
        device_frame.pack(fill="x", padx=0)
        device_frame.grid_columnconfigure(0, weight=1)

        self.create_device_box(device_frame, self.tr("speaker"), "speaker", device_options).grid(row=0, column=0, sticky="ew")
        self.create_device_box(device_frame, self.tr("headset"), "headset", device_options).grid(row=1, column=0, sticky="ew", pady=(SETTINGS_DEVICE_GAP, 0))

        self.create_output_switch_hotkey_settings(settings_content)

        self.startup_var = ctk.BooleanVar(value=bool(self.config_data.get("start_with_windows", False)))
        bottom_options = ctk.CTkFrame(settings_content, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        bottom_options.pack(fill="x", padx=0, pady=(UI_SPACE_LG, 0))
        timeout_options = [self.format_ask_timeout_seconds(seconds) for seconds in ASK_TIMEOUT_OPTION_SECONDS]
        self.ask_timeout_var = ctk.StringVar(value=self.format_ask_timeout_seconds())
        ask_timeout_frame = ctk.CTkFrame(bottom_options, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        ask_timeout_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            ask_timeout_frame,
            text=self.tr("ask_duration"),
            font=(self.ui_font_family(), 13),
            text_color="#B8B8B8",
            anchor="w",
        ).pack(fill="x", pady=(0, 5))
        self.ask_timeout_combo = self.create_editable_duration_dropdown_field(
            ask_timeout_frame,
            self.ask_timeout_var,
            timeout_options,
            width=SETTINGS_DEVICE_WIDTH,
            height=UI_CONTROL_HEIGHT_COMPACT,
            formatter=self.format_ask_timeout_seconds,
            command=lambda value: self.ask_timeout_var.set(self.format_ask_timeout_seconds(value)),
        )
        self.ask_timeout_combo.pack(fill="x")

        mini_duration_options = [self.format_mini_notification_seconds(seconds) for seconds in MINI_NOTIFICATION_OPTION_SECONDS]
        self.mini_notification_var = ctk.StringVar(value=self.format_mini_notification_seconds())
        mini_duration_frame = ctk.CTkFrame(bottom_options, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        mini_duration_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            mini_duration_frame,
            text=self.tr("mini_duration"),
            font=(self.ui_font_family(), 13),
            text_color="#B8B8B8",
            anchor="w",
        ).pack(fill="x", pady=(0, 5))
        self.mini_notification_combo = self.create_editable_duration_dropdown_field(
            mini_duration_frame,
            self.mini_notification_var,
            mini_duration_options,
            width=SETTINGS_DEVICE_WIDTH,
            height=UI_CONTROL_HEIGHT_COMPACT,
            formatter=self.format_mini_notification_seconds,
            command=lambda value: self.apply_mini_notification_duration_setting(save=False),
        )
        self.mini_notification_combo.pack(fill="x")
        self.mini_notification_var.trace_add("write", lambda *_: self.apply_mini_notification_duration_setting(save=False))

        ctk.CTkCheckBox(
            bottom_options,
            text=self.tr("run_on_startup"),
            variable=self.startup_var,
            font=(self.ui_font_family(), 14),
            fg_color=ACTIVE_COLOR,
            hover_color=ACTIVE_HOVER_COLOR,
        ).pack(anchor="w", pady=(0, 12))

        self.language_var = ctk.StringVar(value=language_label_for_code(self.current_language()))
        language_frame = ctk.CTkFrame(bottom_options, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        language_frame.pack(fill="x", pady=(0, 0))
        ctk.CTkLabel(
            language_frame,
            text=self.tr("language"),
            font=(self.ui_font_family(), 13),
            text_color="#B8B8B8",
            anchor="w",
        ).pack(fill="x", pady=(0, 5))
        self.language_combo = self.create_settings_dropdown_field(
            language_frame,
            self.language_var,
            list(LANGUAGE_OPTIONS.values()),
            width=SETTINGS_DEVICE_WIDTH,
            height=UI_CONTROL_HEIGHT_COMPACT,
            command=self.apply_language_setting,
        )
        self.language_combo.pack(fill="x")

        program_panel = ctk.CTkFrame(right_column, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_GRADIENT_END, corner_radius=SETTINGS_PANEL_RADIUS, border_width=0)
        program_panel.pack(fill="both", expand=True, padx=0, pady=(0, 0))
        program_content = ctk.CTkFrame(program_panel, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        program_content.pack(fill="both", expand=True, padx=UI_SPACE_LG, pady=(UI_SPACE_MD, UI_SPACE_LG))
        ctk.CTkLabel(program_content, text=self.tr("program_list"), font=(self.ui_font_family(), 22, "bold"), text_color="white", fg_color="transparent", bg_color="transparent").pack(anchor="w", padx=0, pady=(0, UI_SPACE_SM))
        self.program_list_frame = ctk.CTkFrame(program_content, fg_color="transparent", bg_color="transparent", corner_radius=0)
        self.program_list_frame.pack(fill="both", expand=True)
        self.refresh_program_lists()
        self.log_settings_event("draw_settings_end", elapsed_ms=int((time.perf_counter() - started_at) * 1000), devices=len(device_options))


    def build_device_options(self):
        options = []
        for name in self.audio_device_names:
            if name and name not in options:
                options.append(name)
        for key in ("speaker_name", "headset_name"):
            saved_name = self.config_data.get(key) or ""
            if saved_name and saved_name != "No audio device found" and saved_name not in options:
                options.append(saved_name)
        return options or ["No audio device found"]

    def device_name_from_option(self, value):
        return value or ""

    def device_option_for_name(self, name, device_options=None):
        if not name:
            return ""
        device_options = device_options or self.build_device_options()
        if name in device_options:
            return name
        return name

    def refresh_settings_devices_async(self):
        if self.settings_device_refresh_active:
            self.log_settings_event("refresh_outputs_ignored_busy")
            return
        started_at = time.perf_counter()
        self.log_settings_event("refresh_outputs_begin")
        self.settings_device_refresh_active = True
        button = getattr(self, "audio_refresh_button", None)
        try:
            if self.widget_exists(button):
                button.configure(text=self.tr("refreshing"), state="disabled")
        except Exception:
            pass

        def worker():
            try:
                self.refresh_audio_device_cache(include_input=False)
                if self.audio_device_id_cache_dirty:
                    self.audio_device_id_cache_dirty = False
                    self.save_config()
            finally:
                try:
                    worker_elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                    self.after(0, lambda: self.finish_settings_devices_refresh(worker_elapsed_ms))
                except tk.TclError:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def finish_settings_devices_refresh(self, worker_elapsed_ms=None):
        started_at = time.perf_counter()
        self.settings_device_refresh_active = False
        self.update_settings_device_options()
        button = getattr(self, "audio_refresh_button", None)
        try:
            if self.widget_exists(button):
                button.configure(text=self.tr("refresh"), state="normal")
        except Exception:
            pass
        self.log_settings_event(
            "refresh_outputs_end",
            worker_ms=worker_elapsed_ms,
            ui_ms=int((time.perf_counter() - started_at) * 1000),
            devices=len(getattr(self, "audio_device_names", [])),
        )

    def menu_min_chars_for_width(self, pixel_width):
        try:
            return max(1, int((int(pixel_width) or SETTINGS_DEVICE_WIDTH) / 7))
        except Exception:
            return SETTINGS_DROPDOWN_MENU_MIN_CHARS

    def padded_menu_label(self, label, pixel_width=None):
        text = str(label)
        if not pixel_width:
            return text
        return text.ljust(self.menu_min_chars_for_width(pixel_width))

    def configure_flat_dropdown_menu(self, menu, bg_color=SETTINGS_DROPDOWN_BG):
        try:
            menu.configure(
                background=bg_color,
                foreground="white",
                activebackground=ACTIVE_COLOR,
                activeforeground="white",
                borderwidth=0,
                activeborderwidth=0,
                relief="flat",
                bd=0,
            )
        except Exception:
            pass

    def replace_menu_commands(self, menu, options, command, min_width=None):
        menu.delete(0, "end")
        for option in options:
            menu.add_command(label=self.padded_menu_label(option, min_width), command=lambda value=option: command(value))
        self.configure_flat_dropdown_menu(menu)

    def style_settings_combo_dropdown(self, combo):
        menu = getattr(combo, "_dropdown_menu", None)
        if not menu:
            return
        try:
            width = int(combo.cget("width") or combo.winfo_width() or SETTINGS_DEVICE_WIDTH)
            menu._min_character_width = self.menu_min_chars_for_width(width)
            menu._add_menu_commands()
        except Exception:
            pass
        try:
            menu.configure(
                borderwidth=0,
                activeborderwidth=0,
                relief="flat",
                bg=SETTINGS_DROPDOWN_BG,
                activebackground=ACTIVE_COLOR,
                activeforeground="white",
            )
        except Exception:
            pass

    def update_settings_device_options(self):
        if not self.widget_exists(getattr(self, "program_list_frame", None)) and not getattr(self, "device_controls", None):
            return
        started_at = time.perf_counter()
        device_options = self.build_device_options()
        refreshed = 0
        for mode, controls in getattr(self, "device_controls", {}).items():
            variable = controls.get("variable")
            menu = controls.get("menu")
            dropdown = controls.get("dropdown")
            button = controls.get("button")
            if not variable or not menu or not self.widget_exists(dropdown) or not self.widget_exists(button):
                continue
            configured = self.config_data.get(f"{mode}_name")
            configured_option = self.device_option_for_name(configured, device_options)
            if variable.get() not in device_options:
                variable.set(configured_option if configured_option in device_options else device_options[0])
            menu_width = max(120, (dropdown.winfo_width() or SETTINGS_DEVICE_WIDTH) - 4)
            self.replace_menu_commands(menu, device_options, variable.set, min_width=menu_width)
            refresh = controls.get("refresh")
            if refresh:
                refresh()
                refreshed += 1
        self.log_settings_event_throttled(
            "device_options",
            0.5,
            "device_options_updated",
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            controls=refreshed,
            devices=len(device_options),
        )

    def create_device_box(self, parent, title, mode, device_options):
        header_width = SETTINGS_DEVICE_WIDTH
        is_configured = self.is_audio_mode_configured(mode)
        is_active = self.last_state == mode
        frame = ctk.CTkFrame(parent, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, width=header_width, height=81, corner_radius=UI_RADIUS_CONTROL, border_width=0)
        frame.pack_propagate(False)
        frame.grid_propagate(False)
        content_width = header_width - 4
        header_image = self.settings_header_image(mode, title, is_active, width=content_width, disabled=not is_configured)
        device_button = ctk.CTkLabel(frame, text="", image=header_image, width=content_width, height=39, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, cursor="hand2")
        device_button.configure(image=header_image)
        device_button._settings_header_image = header_image
        if is_configured:
            device_button.bind("<Button-1>", lambda event: self.manual_set_audio(mode))
        else:
            device_button.configure(cursor="arrow")
        device_button.pack(fill="x", padx=2, pady=(2, 0))

        saved_device = self.config_data.get(f"{mode}_name") or ""
        selected_device = self.device_option_for_name(saved_device, device_options)
        if selected_device not in device_options:
            selected_device = device_options[0]
        variable = ctk.StringVar(value=selected_device)
        if mode == "speaker":
            self.sp_var = variable
        else:
            self.hs_var = variable

        dropdown_image = self.settings_dropdown_image(selected_device, is_active, width=content_width)
        option_menu = ctk.CTkLabel(frame, text="", image=dropdown_image, width=content_width, height=37, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, cursor="hand2")
        option_menu._settings_dropdown_image = dropdown_image
        dropdown_menu = tk.Menu(
            option_menu,
            tearoff=0,
            background=SETTINGS_DROPDOWN_BG,
            foreground="white",
            activebackground=ACTIVE_COLOR,
            activeforeground="white",
            borderwidth=0,
            activeborderwidth=0,
            relief="flat",
        )
        self.configure_flat_dropdown_menu(dropdown_menu)
        for device_name in device_options:
            dropdown_menu.add_command(label=self.padded_menu_label(device_name, content_width), command=lambda value=device_name: variable.set(value))

        def refresh_visuals():
            if not self.widget_exists(frame) or not self.widget_exists(device_button) or not self.widget_exists(option_menu):
                return
            started_at = time.perf_counter()
            current_width = max(120, self.logical_widget_width(frame, header_width) - 4)
            configured = self.is_audio_mode_configured(mode)
            interactive = configured and not self.audio_switching
            active = self.last_state == mode
            header = self.settings_header_image(mode, title, active, width=current_width, disabled=not configured)
            dropdown = self.settings_dropdown_image(variable.get(), active, width=current_width)
            device_button._settings_header_image = header
            option_menu._settings_dropdown_image = dropdown
            device_button.configure(image=header, width=current_width)
            option_menu.configure(image=dropdown, width=current_width)
            self.configure_flat_dropdown_menu(dropdown_menu)
            if interactive:
                device_button.configure(cursor="hand2")
                device_button.bind("<Button-1>", lambda event: self.manual_set_audio(mode))
                device_button.unbind("<Motion>")
                device_button.unbind("<Enter>")
                device_button.unbind("<Leave>")
            else:
                device_button.configure(cursor="arrow")
                device_button.unbind("<Button-1>")
                device_button.unbind("<Enter>")
                device_button.unbind("<Motion>")
                device_button.unbind("<Leave>")
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            if elapsed_ms >= 20:
                self.log_settings_event("device_visual_refresh_slow", mode=mode, elapsed_ms=elapsed_ms, active=active, switching=self.audio_switching)

        def open_dropdown(event=None):
            current_options = self.build_device_options()
            self.log_settings_event("device_dropdown_open", mode=mode, options=len(current_options))
            self.show_flat_settings_dropdown(
                option_menu,
                current_options,
                lambda value: variable.set(value),
                width=option_menu.winfo_width() or content_width,
                row_height=30,
            )

        device_button.unbind("<Enter>")
        device_button.unbind("<Motion>")
        device_button.unbind("<Leave>")
        option_menu.bind("<Button-1>", open_dropdown)
        option_menu.unbind("<Enter>")
        option_menu.unbind("<Motion>")
        option_menu.unbind("<Leave>")
        option_menu.pack(fill="x", padx=2, pady=(1, 2))
        def on_device_selection_changed(*_):
            self.log_settings_event("device_selection_changed", mode=mode, value=variable.get())
            refresh_visuals()

        variable.trace_add("write", on_device_selection_changed)
        self.device_controls[mode] = {"button": device_button, "menu": dropdown_menu, "dropdown": option_menu, "title": title, "variable": variable, "refresh": refresh_visuals}
        return frame

    def create_output_switch_hotkey_settings(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        frame.pack(fill="x", padx=0, pady=(UI_SPACE_LG, 0))

        header_width = SETTINGS_DEVICE_WIDTH
        header_image = self.settings_header_image("speaker", "Output Switch Hotkey", False, width=header_width)
        header_label = ctk.CTkLabel(
            frame,
            text="",
            image=header_image,
            width=header_width,
            height=39,
            fg_color=SETTINGS_PANEL_BG,
            bg_color=SETTINGS_PANEL_BG,
        )
        header_label._settings_header_image = header_image
        header_label.pack(fill="x")

        current_hotkey = self.config_data.get("output_switch_hotkey", "") or HOTKEY_NONE_LABEL
        self.output_switch_hotkey_var = ctk.StringVar(value=current_hotkey if current_hotkey in HOTKEY_OPTIONS else HOTKEY_NONE_LABEL)
        row = ctk.CTkFrame(frame, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        row.pack(fill="x", pady=(1, 0))
        hotkey_width = SETTINGS_DEVICE_WIDTH // 2
        detect_width = SETTINGS_DEVICE_WIDTH - hotkey_width
        hotkey_label = ctk.CTkLabel(row, text="", height=SETTINGS_HOTKEY_HEIGHT, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, cursor="hand2")
        hotkey_menu = tk.Menu(
            hotkey_label,
            tearoff=0,
            background=SETTINGS_DROPDOWN_BG,
            foreground="white",
            activebackground=ACTIVE_COLOR,
            activeforeground="white",
            borderwidth=0,
            activeborderwidth=0,
            relief="flat",
        )
        self.configure_flat_dropdown_menu(hotkey_menu)
        for hotkey_name in HOTKEY_OPTIONS:
            hotkey_menu.add_command(label=self.padded_menu_label(hotkey_name, hotkey_width), command=lambda value=hotkey_name: self.output_switch_hotkey_var.set(value))

        def refresh_output_hotkey_menu():
            width = hotkey_width
            image = make_settings_dropdown_segment_image(
                self.output_switch_hotkey_var.get(),
                width,
                SETTINGS_HOTKEY_HEIGHT,
                rounded_bottom_left=True,
                separator_right=True,
                stroke_top=False,
                stroke_right=False,
                fill_color=None,
            )
            hotkey_label._dropdown_image = image
            hotkey_label.configure(image=image, width=width, height=SETTINGS_HOTKEY_HEIGHT)

        def open_output_hotkey_menu(event=None):
            self.show_flat_settings_dropdown(
                hotkey_label,
                HOTKEY_OPTIONS,
                lambda value: self.output_switch_hotkey_var.set(value),
                width=hotkey_label.winfo_width() or hotkey_width,
                row_height=SETTINGS_HOTKEY_HEIGHT,
            )

        refresh_output_hotkey_menu()
        hotkey_label.bind("<Button-1>", open_output_hotkey_menu)
        def apply_output_hotkey_change(*_):
            refresh_output_hotkey_menu()
            self.apply_output_switch_hotkey_setting()

        self.output_switch_hotkey_var.trace_add("write", apply_output_hotkey_change)
        hotkey_label.pack(side="left", fill="x", expand=True, padx=(0, 0))

        detect_image = make_settings_segment_image(
            "Detect",
            detect_width,
            height=SETTINGS_HOTKEY_HEIGHT,
            rounded_bottom_right=True,
            stroke_top=False,
            stroke_left=False,
        )
        detect_button = ctk.CTkLabel(
            row,
            text="",
            image=detect_image,
            width=detect_width,
            height=SETTINGS_HOTKEY_HEIGHT,
            fg_color=SETTINGS_PANEL_BG,
            bg_color=SETTINGS_PANEL_BG,
            cursor="hand2",
        )
        detect_button._segment_image = detect_image
        self.bind_click_target(detect_button, self.open_output_switch_hotkey_capture)
        detect_button.pack(side="left")

    def open_hotkey_capture(self, variable):
        capture = ctk.CTkToplevel(self)
        capture.title("Detect Hotkey")
        capture.geometry(self.center_child_geometry(320, 140))
        capture.transient(self)
        capture.grab_set()
        capture.configure(fg_color="#171717")
        self.hotkey_capture_active = True

        ctk.CTkLabel(capture, text="Press a key", font=("Segoe UI", 16, "bold"), text_color="white").pack(pady=(UI_SPACE_MD * 2, UI_SPACE_SM))
        ctk.CTkLabel(capture, text="F13-F24 can be selected from the dropdown.", font=("Segoe UI", 11), text_color="#B8B8B8").pack()
        focus_entry = tk.Entry(capture, bd=0, highlightthickness=0)
        focus_entry.place(x=-20, y=-20, width=1, height=1)

        def close_capture():
            self.hotkey_capture_active = False
            try:
                capture.grab_release()
            except Exception:
                pass
            if capture.winfo_exists():
                capture.destroy()

        def capture_key(event):
            key_name = self.normalize_hotkey_name(event.keysym)
            if key_name == "ESC":
                close_capture()
                return "break"
            if key_name in HOTKEY_VK:
                variable.set(key_name)
                close_capture()
                return "break"
            return "break"

        capture.bind("<KeyPress>", capture_key)
        focus_entry.bind("<KeyPress>", capture_key)
        capture.protocol("WM_DELETE_WINDOW", close_capture)
        capture.after(50, capture.lift)
        capture.after(100, focus_entry.focus_force)

    def open_output_switch_hotkey_capture(self):
        self.open_hotkey_capture(self.output_switch_hotkey_var)

    def apply_output_switch_hotkey_setting(self):
        if not hasattr(self, "output_switch_hotkey_var"):
            return
        hotkey = self.output_switch_hotkey_var.get()
        if hotkey not in HOTKEY_OPTIONS:
            hotkey = HOTKEY_NONE_LABEL
            self.output_switch_hotkey_var.set(hotkey)
            return
        configured_hotkey = "" if hotkey == HOTKEY_NONE_LABEL else hotkey
        self.config_data["output_switch_hotkey"] = configured_hotkey
        self.output_switch_hotkey_down = False
        self.sync_keyboard_hook_state()
        self.save_config()
        logging.info("output switch hotkey updated hotkey=%s", configured_hotkey or "None")

    def apply_language_setting(self, selected_label=None):
        old_language = self.current_language()
        selected_label = selected_label or (self.language_var.get() if hasattr(self, "language_var") else "")
        new_language = language_code_from_label(selected_label)
        self.config_data["language"] = new_language
        if hasattr(self, "language_var"):
            normalized_label = language_label_for_code(new_language)
            if self.language_var.get() != normalized_label:
                self.language_var.set(normalized_label)
        self.save_settings()
        if new_language != old_language and not self.is_mini:
            self.after(0, self.draw_ui)

    def apply_mini_notification_duration_setting(self, save=True):
        if not hasattr(self, "mini_notification_var"):
            return
        seconds = self.parse_mini_notification_seconds(self.mini_notification_var.get())
        self.config_data["mini_notification_seconds"] = seconds
        if save:
            self.mini_notification_var.set(self.format_mini_notification_seconds(seconds))

    def refresh_program_lists(self):
        self.program_list_render_token += 1
        self.program_icon_load_counter = 0
        if not self.widget_exists(getattr(self, "program_list_frame", None)):
            return
        for widget in self.program_list_frame.winfo_children():
            widget.destroy()
        self.program_list_frame.grid_columnconfigure(0, weight=1)
        self.program_list_frame.grid_rowconfigure(0, weight=1)
        self.create_program_list_ui(self.program_list_frame)

    def iter_program_entries(self):
        entries = [
            (key, program)
            for key in ("ask_list", "auto_list")
            for program in self.config_data.get(key, [])
        ]
        order = self.ensure_program_display_order(entries)
        entries_by_id = {self.program_rule_id(program): (key, program) for key, program in entries}
        yielded = set()
        for rule_id in order:
            entry = entries_by_id.get(rule_id)
            if entry:
                yielded.add(rule_id)
                yield entry
        for key, program in entries:
            rule_id = self.program_rule_id(program)
            if rule_id not in yielded:
                yield key, program

    def program_rule_id(self, program):
        match_type = (program.get("match_type") or "process_name").strip().casefold()
        value = (program.get("value") or "").strip().casefold()
        return f"{match_type}:{value}"

    def ensure_program_display_order(self, entries=None):
        entries = entries if entries is not None else [
            (key, program)
            for key in ("ask_list", "auto_list")
            for program in self.config_data.get(key, [])
        ]
        existing_ids = [self.program_rule_id(program) for _, program in entries]
        existing_set = set(existing_ids)
        order = self.config_data.get("program_order")
        if not isinstance(order, list):
            order = []
        normalized_order = []
        seen = set()
        for rule_id in order:
            if isinstance(rule_id, str) and rule_id in existing_set and rule_id not in seen:
                normalized_order.append(rule_id)
                seen.add(rule_id)
        for rule_id in existing_ids:
            if rule_id not in seen:
                normalized_order.append(rule_id)
                seen.add(rule_id)
        if normalized_order != self.config_data.get("program_order"):
            self.config_data["program_order"] = normalized_order
        return normalized_order

    def create_program_list_ui(self, parent):
        section = ctk.CTkFrame(parent, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        section.grid(row=0, column=0, sticky="nsew")
        section.grid_rowconfigure(0, weight=1)
        section.grid_columnconfigure(0, weight=1)

        scroll_shell = ctk.CTkFrame(section, fg_color=SURFACE_BG, bg_color=SETTINGS_PANEL_BG, border_width=1, border_color="#080808", corner_radius=SETTINGS_PANEL_RADIUS)
        scroll_shell.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, UI_SPACE_SM))
        scroll_shell.pack_propagate(False)
        scroll = ctk.CTkScrollableFrame(scroll_shell, fg_color=SURFACE_BG, bg_color=SURFACE_BG, border_width=0, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=4, pady=4)
        self.normalize_scrollable_background(scroll, SURFACE_BG)

        entries = list(self.iter_program_entries())
        if not entries:
            placeholder = ctk.CTkLabel(scroll, text="No programs yet", text_color="#777777", height=40)
            placeholder._empty_placeholder = True
            placeholder.pack(fill="x")
        else:
            self.program_list_render_token += 1
            self.render_program_rows_batch(scroll, entries, self.program_list_render_token)

        ctk.CTkButton(section, text="+  Add Program", height=UI_CONTROL_HEIGHT_LARGE, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=UI_RADIUS_CONTROL, font=("Segoe UI", 14), command=lambda: self.open_add_program_menu("ask_list")).grid(row=1, column=0, sticky="ew", padx=0, pady=0)

    def render_program_rows_batch(self, parent, entries, token, start=0, batch_size=8):
        if token != getattr(self, "program_list_render_token", None) or not self.widget_exists(parent):
            return
        end = min(len(entries), start + batch_size)
        for key, program in entries[start:end]:
            self.create_program_row(parent, key, program)
        if end < len(entries):
            self.after(1, lambda: self.render_program_rows_batch(parent, entries, token, end, batch_size))

    def create_program_row(self, parent, key, program):
        item = ctk.CTkFrame(parent, fg_color=SETTINGS_ROW_BG, corner_radius=UI_RADIUS_ROW, height=54)
        item.pack(fill="x", pady=UI_SPACE_XS // 2, padx=UI_SPACE_XS)
        item.pack_propagate(False)

        icon_source = self.get_program_icon_source(program)
        icon = self.get_cached_program_icon_if_ready(icon_source, size=PROGRAM_ICON_SIZE, use_shell_fallback=False)
        icon_label = ctk.CTkLabel(item, text="" if icon else "APP", image=icon, width=38, height=38, fg_color="#272A2F", corner_radius=UI_RADIUS_CONTROL, font=("Segoe UI", 9, "bold"))
        icon_label.pack(side="left", padx=(10, 8), pady=6)
        if not icon and icon_source:
            self.schedule_program_icon_load(icon_label, icon_source, self.program_list_render_token, size=PROGRAM_ICON_SIZE, use_shell_fallback=False)

        text_box = ctk.CTkFrame(item, fg_color="transparent")
        text_box.pack(side="left", fill="both", expand=True, padx=0, pady=5)
        name_canvas = self.create_marquee_label(
            text_box,
            program.get("name", "Unknown"),
            ("Segoe UI", PROGRAM_LIST_NAME_FONT_SIZE),
            "white",
            SETTINGS_ROW_BG,
            42,
        )
        name_canvas.pack(fill="both", expand=True)

        ctk.CTkButton(item, text="", image=self.icons["trash"], width=38, height=39, fg_color="#991B1B", hover_color="#B91C1C", corner_radius=UI_RADIUS_CONTROL, command=lambda p=program, k=key: self.remove_program(k, p)).pack(side="right", padx=(UI_SPACE_XS, UI_SPACE_SM))
        self.create_program_target_button(item, key, program, "headset").pack(side="right", padx=2)
        self.create_program_target_button(item, key, program, "speaker").pack(side="right", padx=2)
        item._program_current_key = key
        auto_button = self.create_program_mode_button(item, program, "auto_list", "Auto")
        ask_button = self.create_program_mode_button(item, program, "ask_list", "Ask")
        item._program_mode_buttons = {"ask_list": ask_button, "auto_list": auto_button}
        auto_button.pack(side="right", padx=2)
        ask_button.pack(side="right", padx=2)
        self.create_program_icon_button(item, "edit", lambda p=program, k=key: self.edit_program_name(k, p)).pack(side="right", padx=2)
        return item

    def get_program_icon_source(self, program, process_path=None):
        return program.get("icon_path") or process_path or program.get("path") or ""

    def preload_program_icon_cache(self):
        sources = []
        for key in ("ask_list", "auto_list"):
            for program in self.config_data.get(key, []):
                source = self.get_program_icon_source(program)
                if source and source not in sources:
                    sources.append(source)
        self.program_icon_preload_queue = sources
        self.preload_next_program_icon()

    def preload_next_program_icon(self):
        if not self.program_icon_preload_queue:
            return
        source = self.program_icon_preload_queue.pop(0)
        self.get_cached_program_icon(source, size=PROGRAM_ICON_SIZE, use_shell_fallback=False)
        self.after(80, self.preload_next_program_icon)

    def program_icon_cache_key(self, path, size=PROGRAM_ICON_SIZE, source_size=None, corner_radius=0, use_shell_fallback=True):
        return (path or "", size, source_size or size, corner_radius, bool(use_shell_fallback))

    def get_cached_program_icon_if_ready(self, path, size=PROGRAM_ICON_SIZE, source_size=None, corner_radius=0, use_shell_fallback=True):
        return self.exe_icon_cache.get(self.program_icon_cache_key(path, size, source_size, corner_radius, use_shell_fallback))

    def load_program_icon_into_label(self, label, path, size=PROGRAM_ICON_SIZE, use_shell_fallback=True):
        if not self.widget_exists(label):
            return
        icon = self.get_cached_program_icon(path, size=size, use_shell_fallback=use_shell_fallback)
        if self.widget_exists(label) and icon:
            label.configure(image=icon, text="")

    def schedule_program_icon_load(self, label, path, token, size=PROGRAM_ICON_SIZE, use_shell_fallback=True):
        if not path or self.get_cached_program_icon_if_ready(path, size=size, use_shell_fallback=use_shell_fallback):
            return
        self.program_icon_load_counter += 1
        delay_ms = min(600, 30 * self.program_icon_load_counter)

        def load_if_current():
            if token != getattr(self, "program_list_render_token", None) or not self.widget_exists(label):
                return
            self.load_program_icon_into_label(label, path, size=size, use_shell_fallback=use_shell_fallback)

        self.after(delay_ms, load_if_current)

    def get_cached_program_icon(self, path, size=PROGRAM_ICON_SIZE, source_size=None, corner_radius=0, use_shell_fallback=True):
        cache_key = self.program_icon_cache_key(path, size, source_size, corner_radius, use_shell_fallback)
        if cache_key not in self.exe_icon_cache:
            extension = os.path.splitext(path or "")[1].lower()
            if extension in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico"):
                icon = get_icon_from_image(path, size=size, source_size=source_size, corner_radius=corner_radius)
            else:
                icon = get_icon_from_exe(path, size=size, source_size=source_size, corner_radius=corner_radius, use_shell_fallback=use_shell_fallback)
            self.exe_icon_cache[cache_key] = icon
        return self.exe_icon_cache[cache_key]

    def get_cached_window_icon(self, hwnd, size=PROGRAM_ICON_SIZE, source_size=None, corner_radius=0):
        cache_key = (int(hwnd or 0), size, source_size or size, corner_radius)
        if cache_key not in self.window_icon_cache:
            self.window_icon_cache[cache_key] = get_icon_from_window(
                hwnd,
                size=size,
                source_size=source_size,
                corner_radius=corner_radius,
            )
        return self.window_icon_cache[cache_key]

    def cache_running_program_icon(self, program):
        hwnd = program.get("window_handle")
        if not hwnd:
            return ""
        image = get_image_from_icon_handle(get_window_icon_handle(hwnd), MINI_DETECTED_ICON_SOURCE_SIZE)
        if image is None:
            return ""
        try:
            os.makedirs(PROGRAM_ICON_CACHE_DIR, exist_ok=True)
            identity = f'{program.get("name", "")}\0{program.get("path", "")}'.encode("utf-8", errors="replace")
            filename = f"{hashlib.sha256(identity).hexdigest()[:24]}.png"
            icon_path = os.path.join(PROGRAM_ICON_CACHE_DIR, filename)
            image.save(icon_path, "PNG", optimize=True)
            logging.info("running program icon cached name=%s path=%s", program.get("name"), icon_path)
            return icon_path
        except Exception:
            logging.exception("running program icon cache failed name=%s", program.get("name"))
            return ""

    def update_detect_ui_with_program_icon(self, program, icon_source):
        icon = self.get_cached_program_icon(
            icon_source,
            size=MINI_DETECTED_ICON_SIZE,
            source_size=MINI_DETECTED_ICON_SOURCE_SIZE,
            corner_radius=MINI_DETECTED_ICON_CORNER_RADIUS,
        ) if icon_source else None
        self.update_detect_ui(program.get("name", "Unknown"), icon)

    def normalize_scrollable_background(self, scroll, color):
        for attr in ("_parent_canvas", "_parent_frame"):
            widget = getattr(scroll, attr, None)
            if widget is None:
                continue
            try:
                if hasattr(widget, "configure"):
                    widget.configure(bg=color)
            except Exception:
                pass
            try:
                widget.configure(fg_color=color, bg_color=color)
            except Exception:
                pass
        scrollbar = getattr(scroll, "_scrollbar", None)
        if scrollbar is not None:
            try:
                scrollbar.configure(fg_color=color, bg_color=color)
            except Exception:
                pass

    def bind_click_target(self, widget, command):
        def handle_click(event=None):
            command()
            return "break"

        targets = [widget]
        try:
            targets.extend(widget.winfo_children())
        except Exception:
            pass
        for target in targets:
            try:
                target.bind("<Button-1>", handle_click)
            except Exception:
                pass
            try:
                target.configure(cursor="hand2")
            except Exception:
                pass

    def program_key(self, program):
        return program.get("match_type"), program.get("value")

    def find_program_index(self, key, program):
        target = self.program_key(program)
        for index, item in enumerate(self.config_data[key]):
            if self.program_key(item) == target:
                return index
        return None

    def create_program_target_button(self, parent, key, program, mode):
        active = program.get("target_audio") == mode
        normal_image = make_program_target_button_image(mode, active=active, hover=False)
        hover_image = make_program_target_button_image(mode, active=active, hover=not active)
        button = ctk.CTkLabel(
            parent,
            text="",
            image=normal_image,
            width=38,
            height=39,
            cursor="hand2",
        )
        button._target_normal_image = normal_image
        button._target_hover_image = hover_image
        button.bind("<Button-1>", lambda event: self.set_program_target(key, program, mode))
        if not active:
            button.bind("<Enter>", lambda event: button.configure(image=button._target_hover_image))
            button.bind("<Leave>", lambda event: button.configure(image=button._target_normal_image))
        return button

    def create_program_icon_button(self, parent, icon_kind, command):
        normal_image = make_program_target_button_image(icon_kind, active=False, hover=False)
        hover_image = make_program_target_button_image(icon_kind, active=False, hover=True)
        button = ctk.CTkLabel(
            parent,
            text="",
            image=normal_image,
            width=38,
            height=39,
            cursor="hand2",
        )
        button._normal_image = normal_image
        button._hover_image = hover_image
        button.bind("<Button-1>", lambda event: command())
        button.bind("<Enter>", lambda event: button.configure(image=button._hover_image))
        button.bind("<Leave>", lambda event: button.configure(image=button._normal_image))
        return button

    def configure_program_mode_button(self, button, active, label):
        if not self.widget_exists(button):
            return
        button.configure(
            text=label,
            fg_color=ACTIVE_COLOR if active else CONTROL_BG,
            hover_color=ACTIVE_HOVER_COLOR if active else CONTROL_HOVER,
            font=("Segoe UI", 12, "bold" if active else "normal"),
        )

    def create_program_mode_button(self, parent, program, target_key, label):
        active = getattr(parent, "_program_current_key", "") == target_key
        button = ctk.CTkButton(
            parent,
            text=label,
            width=50,
            height=39,
            fg_color=ACTIVE_COLOR if active else CONTROL_BG,
            hover_color=ACTIVE_HOVER_COLOR if active else CONTROL_HOVER,
            text_color="white",
            corner_radius=UI_RADIUS_CONTROL,
            font=("Segoe UI", 12, "bold" if active else "normal"),
            command=lambda: self.set_program_mode(getattr(parent, "_program_current_key", ""), program, target_key, parent),
        )
        return button

    def set_program_mode(self, source_key, program, target_key, row=None):
        if source_key == target_key:
            return
        source_index = self.find_program_index(source_key, program)
        if source_index is None:
            return
        if self.program_exists(target_key, program):
            messagebox.showinfo("Auto Audio", "This program rule already exists in that mode.")
            return
        moved_program = self.config_data[source_key].pop(source_index)
        self.config_data[target_key].append(moved_program)
        self.ensure_program_display_order()
        self.save_config()
        if self.widget_exists(row):
            row._program_current_key = target_key
            for key, button in getattr(row, "_program_mode_buttons", {}).items():
                self.configure_program_mode_button(button, key == target_key, "Ask" if key == "ask_list" else "Auto")
        else:
            self.refresh_program_lists()

    def switch_mode(self, target, focus=True, animate_mini=None):
        was_visible = self.winfo_viewable()
        was_mini = self.is_mini
        was_animating_mini = was_mini and self.mini_animation_after_id is not None
        self.cancel_mini_animation()
        should_animate_mini = target == "mini" and ((animate_mini if animate_mini is not None else not (was_visible and was_mini)) or was_animating_mini)
        logging.info("switch_mode target=%s was_visible=%s was_mini=%s animating=%s focus=%s animate_mini=%s should_animate=%s", target, was_visible, was_mini, was_animating_mini, focus, animate_mini, should_animate_mini)

        if target == "settings" and was_visible and was_mini:
            self.animate_mini_out(on_complete=lambda: self.switch_mode("settings", focus=focus))
            return

        if target == "mini" and was_visible and was_mini and was_animating_mini:
            self.animate_mini_in(from_current=True)
            if focus:
                self.after(50, self.focus_force)
            return

        if target == "settings" and was_visible:
            self.withdraw()
        elif should_animate_mini and was_visible and not was_mini:
            self.withdraw()
        self.set_ui_mode(target)
        self.draw_ui()
        if target != "settings":
            self.update_idletasks()
        if should_animate_mini:
            self.animate_mini_in(from_current=was_visible and was_mini)
            if focus:
                self.after(50, self.focus_force)
            return
        self.deiconify()
        self.lift()
        if target == "settings":
            self.after(100, self.apply_dark_title_bar)
        if target == "mini" and focus:
            self.after(50, self.focus_force)

    def on_mini_focus_out(self, event):
        if not self.is_mini or not self.winfo_viewable():
            return
        self.after(120, self.hide_mini_if_focus_left)

    def hide_mini_if_focus_left(self):
        if not self.is_mini or not self.winfo_viewable():
            return
        if self.mini_pinned_by_user:
            return
        if self.ask_active or self.notification_active:
            return
        focused = self.focus_get()
        if focused is None:
            self.hide_to_tray()

    def start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y
        self._drag_started = False

    def do_move(self, event):
        if self.is_mini:
            self._drag_started = True
            self.mini_pinned_by_user = True
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def audio_label(self, state):
        return self.tr("headset") if state == "headset" else self.tr("speaker")

    def log_once(self, key, message, *args, level=logging.INFO):
        if "loop_guard_log_keys" not in self.__dict__:
            self.loop_guard_log_keys = set()
        if key in self.loop_guard_log_keys:
            return
        self.loop_guard_log_keys.add(key)
        logging.log(level, message, *args)

    def log_settings_event(self, event, **fields):
        try:
            self.settings_event_seq += 1
            payload = " ".join(f"{key}={value}" for key, value in fields.items())
            logging.getLogger("settings_events").info("seq=%s event=%s %s", self.settings_event_seq, event, payload)
        except Exception:
            pass

    def log_settings_event_throttled(self, key, interval_seconds, event, **fields):
        now = time.monotonic()
        attr_name = f"_settings_event_last_{key}"
        if now - getattr(self, attr_name, 0) < interval_seconds:
            return
        setattr(self, attr_name, now)
        self.log_settings_event(event, **fields)

    def close_settings_dropdown(self):
        popup = getattr(self, "active_settings_dropdown", None)
        self.active_settings_dropdown = None
        if popup is not None:
            try:
                if popup.winfo_exists():
                    try:
                        popup.grab_release()
                    except Exception:
                        pass
                    popup.destroy()
            except Exception:
                pass

    def show_flat_settings_dropdown(self, anchor, options, command, width=None, row_height=30, max_visible=8):
        if not options or not self.widget_exists(anchor):
            return
        self.close_settings_dropdown()
        try:
            anchor.update_idletasks()
        except Exception:
            pass
        scale = self.ui_pixel_scale()
        content_width = max(1, int(width or anchor.winfo_width() or round(SETTINGS_DEVICE_WIDTH * scale)))
        visible_count = max(1, min(len(options), max_visible))
        scaled_row_height = max(1, round(row_height * scale))
        content_height = scaled_row_height * visible_count
        popup_width = content_width
        popup_height = content_height
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.configure(bg=SETTINGS_OUTER_BG, bd=0, highlightthickness=0)
        try:
            popup.attributes("-topmost", True)
            popup.transient(self)
        except Exception:
            pass
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height()
        left, top, right, bottom = self.get_work_area()
        x = max(left, min(x, right - popup_width))
        if y + popup_height > bottom:
            y = max(top, anchor.winfo_rooty() - popup_height)
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
        self.log_settings_event("dropdown_popup_show", width=content_width, height=content_height, x=x, y=y, options=len(options))
        canvas = tk.Canvas(
            popup,
            width=popup_width,
            height=popup_height,
            bg=SETTINGS_OUTER_BG,
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        canvas.pack(fill="both", expand=True)
        state = {"offset": 0, "hover": None}

        def build_dropdown_background():
            radius = 8
            bg_rgb = hex_to_rgb(SETTINGS_OUTER_BG)
            image = Image.new("RGB", (content_width, content_height), bg_rgb)
            rows = Image.new("RGB", (content_width, content_height), bg_rgb)
            rows_draw = ImageDraw.Draw(rows)
            for row in range(visible_count):
                index = state["offset"] + row
                if index >= len(options):
                    break
                top = row * scaled_row_height
                bottom = top + scaled_row_height
                fill = CONTROL_HOVER if state["hover"] == index else CONTROL_BG
                rows_draw.rectangle((0, top, content_width, bottom), fill=hex_to_rgb(fill))

            mask = Image.new("L", (content_width, content_height), 0)
            mask_draw = ImageDraw.Draw(mask)
            if content_height > radius:
                mask_draw.rectangle((0, 0, content_width, content_height - radius), fill=255)
            mask_draw.rounded_rectangle((0, max(0, content_height - radius * 2), content_width, content_height), radius=radius, fill=255)
            image.paste(rows, (0, 0), mask)
            return ImageTk.PhotoImage(image)

        def redraw():
            canvas.delete("all")
            self.settings_dropdown_bg_photo = build_dropdown_background()
            canvas.create_image(0, 0, image=self.settings_dropdown_bg_photo, anchor="nw")
            for row in range(visible_count):
                index = state["offset"] + row
                if index >= len(options):
                    break
                top = row * scaled_row_height
                canvas.create_text(max(1, round(10 * scale)), top + scaled_row_height / 2, text=str(options[index]), fill="white", font=self.canvas_font(11), anchor="w")
            if len(options) > visible_count:
                track_height = max(12, int(content_height * visible_count / len(options)))
                max_offset = max(1, len(options) - visible_count)
                track_top = int((content_height - track_height) * state["offset"] / max_offset)
                canvas.create_rectangle(content_width - 4, track_top, content_width - 2, track_top + track_height, fill="#565656", outline="#565656")

        def select_at(event):
            if event.x < 0 or event.y < 0 or event.x >= content_width or event.y >= content_height:
                self.close_settings_dropdown()
                return "break"
            index = state["offset"] + int(event.y // scaled_row_height)
            if 0 <= index < len(options):
                value = options[index]
                self.close_settings_dropdown()
                command(value)
            return "break"

        def on_motion(event):
            if event.x < 0 or event.y < 0 or event.x >= content_width or event.y >= content_height:
                index = None
            else:
                index = state["offset"] + int(event.y // scaled_row_height)
            if index != state["hover"]:
                state["hover"] = index if index is not None and 0 <= index < len(options) else None
                redraw()

        def on_leave(event=None):
            if state["hover"] is not None:
                state["hover"] = None
                redraw()

        def on_wheel(event):
            if len(options) <= visible_count:
                return "break"
            delta = -1 if event.delta > 0 else 1
            state["offset"] = max(0, min(len(options) - visible_count, state["offset"] + delta))
            redraw()
            return "break"

        canvas.bind("<Button-1>", select_at)
        popup.bind("<Button-1>", select_at)
        canvas.bind("<Motion>", on_motion)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<MouseWheel>", on_wheel)
        popup.bind("<Escape>", lambda event: self.close_settings_dropdown())
        self.active_settings_dropdown = popup
        redraw()
        try:
            popup.deiconify()
            popup.lift()
            popup.attributes("-topmost", True)
            popup.grab_set()

            def release_topmost():
                try:
                    if popup.winfo_exists():
                        popup.attributes("-topmost", False)
                except Exception:
                    pass

            popup.after(250, release_topmost)
        except Exception:
            pass

    def create_settings_dropdown_field(self, parent, variable, values, width=SETTINGS_DEVICE_WIDTH, height=30, command=None):
        label = ctk.CTkLabel(parent, text="", width=width, height=height, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, cursor="hand2")

        def refresh(*_):
            current_width = max(width, self.logical_widget_width(label, width))
            image = make_settings_dropdown_segment_image(
                variable.get(),
                current_width,
                height,
                rounded_top_left=True,
                rounded_top_right=True,
                rounded_bottom_left=True,
                rounded_bottom_right=True,
            )
            label._settings_dropdown_image = image
            label.configure(image=image, width=current_width, height=height)

        def select(value):
            variable.set(value)
            refresh()
            if command:
                command(value)

        def open_dropdown(event=None):
            refresh()
            self.show_flat_settings_dropdown(label, values, select, width=label.winfo_width() or width, row_height=height)

        label.bind("<Button-1>", open_dropdown)
        variable.trace_add("write", refresh)
        label.after(0, refresh)
        return label

    def create_editable_duration_dropdown_field(self, parent, variable, values, width=SETTINGS_DEVICE_WIDTH, height=30, formatter=None, command=None):
        frame = ctk.CTkFrame(parent, width=width, height=height, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        frame.pack_propagate(False)
        arrow_width = height
        scale = self.ui_pixel_scale()
        px = lambda value: max(1, round(value * scale))
        background = ctk.CTkLabel(frame, text="", width=width, height=height, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG)
        background.place(x=0, y=0, relwidth=1, relheight=1)
        entry = tk.Entry(
            frame,
            textvariable=variable,
            bd=0,
            relief="flat",
            bg=CONTROL_BG,
            fg="white",
            insertbackground="white",
            selectbackground=ACTIVE_COLOR,
            selectforeground="white",
            font=self.canvas_font(13),
        )
        entry.place(x=px(10), y=px(1), width=px(max(40, width - arrow_width - 12)), height=px(max(1, height - 2)))
        background.configure(cursor="hand2")

        def refresh(*_):
            current_width = max(width, self.logical_widget_width(frame, width))
            image = make_settings_dropdown_segment_image(
                "",
                current_width,
                height,
                rounded_top_left=True,
                rounded_top_right=True,
                rounded_bottom_left=True,
                rounded_bottom_right=True,
                arrow_width=arrow_width,
            )
            frame._settings_dropdown_image = image
            background.configure(image=image, width=current_width, height=height)
            background.image = image
            entry.place_configure(width=px(max(40, current_width - arrow_width - 12)), height=px(max(1, height - 2)))

        def normalize_value():
            if formatter:
                variable.set(formatter(variable.get()))
            if command:
                command(variable.get())

        def select(value):
            variable.set(value)
            normalize_value()
            refresh()

        def open_dropdown(event=None):
            refresh()
            self.show_flat_settings_dropdown(frame, values, select, width=frame.winfo_width() or width, row_height=height)
            return "break"

        def on_background_click(event):
            current_width = max(width, self.logical_widget_width(frame, width))
            if event.x >= px(current_width - arrow_width):
                return open_dropdown(event)
            entry.focus_set()
            return "break"

        background.bind("<Button-1>", on_background_click)
        entry.bind("<Return>", lambda event: (normalize_value(), "break")[-1])
        entry.bind("<FocusOut>", lambda event: normalize_value())
        variable.trace_add("write", refresh)
        frame.after(0, refresh)
        return frame

    def remember_settings_image(self, key, factory):
        cache = getattr(self, "settings_image_cache", None)
        if cache is None:
            self.settings_image_cache = {}
            cache = self.settings_image_cache
        if key in cache:
            return cache[key]
        if len(cache) > 200:
            cache.clear()
        image = factory()
        cache[key] = image
        return image

    def settings_header_image(self, kind, text, active, width, hover=False, disabled=False):
        cache_key = ("header", kind, text, bool(active), int(width), bool(hover), bool(disabled))
        return self.remember_settings_image(
            cache_key,
            lambda: make_setting_device_header_image(kind, text, active, width=width, hover=hover, disabled=disabled),
        )

    def settings_dropdown_image(self, text, active, width, hover=False):
        cache_key = ("dropdown", text, bool(active), int(width), bool(hover))
        return self.remember_settings_image(
            cache_key,
            lambda: make_setting_device_dropdown_image(text, active, width=width, hover=hover),
        )

    def widget_exists(self, widget):
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except tk.TclError:
            return False
        except Exception:
            return False

    def audio_mode_target_name(self, mode):
        return self.config_data.get("headset_name" if mode == "headset" else "speaker_name", "")

    def is_audio_mode_configured(self, mode):
        target = self.audio_mode_target_name(mode)
        return bool(target and target != "No audio device found")

    def resolve_audio_mode_target(self, mode):
        target = self.audio_mode_target_name(mode)
        if not target or target == "No audio device found":
            return target, ""
        with self.device_cache_lock:
            output_ids = dict(getattr(self, "audio_device_ids", {}))
        return target, output_ids.get(target, "") or self.config_data.get(f"{mode}_id", "")

    def remember_offline_audio_selection(self, mode, target):
        self.offline_audio_mode = mode
        self.offline_audio_target = target
        self.current_audio_mode_cache = mode
        self.last_audio_sync_time = time.monotonic()
        logging.info("offline audio selection retained mode=%s target=%s", mode, target)

    def clear_offline_audio_selection(self, reason):
        mode = getattr(self, "offline_audio_mode", None)
        target = getattr(self, "offline_audio_target", None)
        if mode or target:
            logging.info("offline audio selection cleared mode=%s target=%s reason=%s", mode, target, reason)
        self.offline_audio_mode = None
        self.offline_audio_target = None

    def is_audio_output_active(self, target):
        with self.device_cache_lock:
            return target in getattr(self, "audio_device_names", [])

    def update_mini_buttons_ui(self, state):
        if self.audio_switching:
            self.show_audio_switching_ui(self.audio_switch_target, redraw=False)
            return
        self.clear_audio_switching_ui(redraw=False)
        if self.widget_exists(getattr(self, "speaker_btn", None)) and self.widget_exists(getattr(self, "headset_btn", None)):
            configured_modes = {
                "speaker": self.is_audio_mode_configured("speaker"),
                "headset": self.is_audio_mode_configured("headset"),
            }
            selected = state
            self.speaker_btn.configure(image=self.mini_button_images[self.mini_button_image_key("speaker", selected, configured_modes["speaker"])])
            self.headset_btn.configure(image=self.mini_button_images[self.mini_button_image_key("headset", selected, configured_modes["headset"])])
            for mode, button in (("speaker", self.speaker_btn), ("headset", self.headset_btn)):
                configured = self.is_audio_mode_configured(mode)
                if configured:
                    button.configure(cursor="hand2")
                    button.bind("<Button-1>", lambda event, target_mode=mode: self.manual_set_audio(target_mode))
                    button.bind("<Enter>", lambda event, target_mode=mode: self.set_mini_device_button_hover(target_mode, True))
                    button.bind("<Leave>", lambda event, target_mode=mode: self.set_mini_device_button_hover(target_mode, False))
                else:
                    button.configure(cursor="arrow")
                    button.unbind("<Button-1>")
                    button.unbind("<Enter>")
                    button.unbind("<Motion>")
                    button.unbind("<Leave>")
        self.update_device_controls_ui(state)

    def mini_button_image_key(self, mode, selected, configured):
        if configured:
            return f"{mode}_active" if selected == mode else f"{mode}_inactive"
        return f"{mode}_disabled"

    def set_mini_device_button_hover(self, mode, is_hovered):
        if self.audio_switching or self.last_state == mode or not self.is_audio_mode_configured(mode):
            return
        button = getattr(self, f"{mode}_btn", None)
        if self.widget_exists(button):
            image_key = f"{mode}_hover" if is_hovered else f"{mode}_inactive"
            button.configure(image=self.mini_button_images[image_key])

    def show_audio_switching_ui(self, target=None, redraw=True):
        self.audio_switching = True
        self.audio_switch_target = target
        if redraw:
            self.update_mini_detect_canvas(self.tr("changing_audio_output"), self.icons.get("speaker" if target == "speaker" else "headset"))
        if not self.widget_exists(getattr(self, "mini_button_frame", None)):
            return
        for button_name in ("speaker_btn", "headset_btn"):
            button = getattr(self, button_name, None)
            if self.widget_exists(button):
                button.pack_forget()
        label = getattr(self, "audio_switching_btn", None)
        if not self.widget_exists(label):
            label = ctk.CTkLabel(
                self.mini_button_frame,
                text="",
                image=self.mini_button_images["switching"],
                width=AUDIO_SWITCHING_BUTTON_WIDTH,
                height=MINI_DEVICE_BUTTON_HEIGHT,
            )
            self.audio_switching_btn = label
        if not label.winfo_ismapped():
            label.pack(side="left")

    def clear_audio_switching_ui(self, redraw=True):
        label = getattr(self, "audio_switching_btn", None)
        if self.widget_exists(label) and label.winfo_ismapped():
            label.pack_forget()
        if self.widget_exists(getattr(self, "speaker_btn", None)) and not self.speaker_btn.winfo_ismapped():
            self.speaker_btn.pack(side="left", padx=(0, MINI_DEVICE_BUTTON_GAP))
        if self.widget_exists(getattr(self, "headset_btn", None)) and not self.headset_btn.winfo_ismapped():
            self.headset_btn.pack(side="left")
        if redraw:
            self.update_mini_buttons_ui(self.last_state)

    def update_device_controls_ui(self, state):
        for mode, controls in getattr(self, "device_controls", {}).items():
            try:
                refresh = controls.get("refresh")
                if refresh:
                    refresh()
            except Exception:
                pass

    def update_detect_ui(self, name, icon=None):
        self.current_detected_name = name
        display_icon = icon or self.icons.get("no_app")
        self.current_detected_icon = display_icon
        if self.ask_active or self.notification_active:
            return
        self.update_mini_detect_canvas(name, display_icon)

    def show_audio_change_notification(self, target, program_name=None, icon=None, animate=True, duration_seconds=None):
        duration_seconds = self.get_mini_notification_seconds() if duration_seconds is None else self.parse_mini_notification_seconds(duration_seconds)
        if self.notification_after_id:
            try:
                self.after_cancel(self.notification_after_id)
            except Exception:
                pass
            self.notification_after_id = None

        self.notification_active = True
        self.ask_active = False
        self.pending_prompt_key = None
        self.mini_pinned_by_user = False
        self.current_detected_icon = icon
        was_mini_visible = self.is_mini and self.winfo_viewable()
        logging.info("notification show target=%s program=%s duration=%s was_mini_visible=%s", target, program_name, duration_seconds, was_mini_visible)
        self.switch_mode("mini", focus=False, animate_mini=not was_mini_visible)
        self.update_mini_buttons_ui(target)

        fallback_icon = self.icons.get("no_app") if program_name == self.tr("no_program_detected") or program_name == "No Program Detected" else self.icons["headset"] if target == "headset" else self.icons["speaker"]
        self.update_mini_detect_canvas(self.tr("audio_output_changed"), icon or fallback_icon)
        self.notification_after_id = self.after(int(duration_seconds * 1000), self.finish_audio_change_notification)
        logging.info("notification hide scheduled after_ms=%s", int(duration_seconds * 1000))

    def finish_audio_change_notification(self):
        logging.info("notification finish visible=%s is_mini=%s ask=%s pinned=%s", self.winfo_viewable(), self.is_mini, self.ask_active, self.mini_pinned_by_user)
        self.notification_active = False
        self.notification_after_id = None
        if self.is_mini and self.winfo_viewable() and not self.ask_active and not self.mini_pinned_by_user:
            self.animate_mini_out()
        else:
            logging.info("notification finish did not hide mini")

    def cancel_audio_change_notification(self):
        if self.notification_after_id:
            try:
                self.after_cancel(self.notification_after_id)
            except Exception:
                pass
            self.notification_after_id = None
        self.notification_active = False
        logging.info("notification cancelled")

    def apply_settings_device_selection(self, mode=None):
        started_at = time.perf_counter()
        targets = (mode,) if mode in ("speaker", "headset") else ("speaker", "headset")
        changed_modes = []
        for target_mode in targets:
            variable = getattr(self, "sp_var" if target_mode == "speaker" else "hs_var", None)
            if not variable:
                continue
            selected_name = self.device_name_from_option(variable.get())
            if selected_name and selected_name != "No audio device found":
                previous_name = self.config_data.get(f"{target_mode}_name")
                self.config_data[f"{target_mode}_name"] = selected_name
                if previous_name != selected_name:
                    changed_modes.append(target_mode)
                with self.device_cache_lock:
                    selected_id = self.audio_device_ids.get(selected_name, "")
                if selected_id:
                    self.config_data[f"{target_mode}_id"] = selected_id
                elif previous_name != selected_name:
                    self.config_data[f"{target_mode}_id"] = ""
        self.log_settings_event_throttled(
            "apply_selection",
            0.25,
            "apply_device_selection",
            mode=mode,
            elapsed_ms=int((time.perf_counter() - started_at) * 1000),
            changed=",".join(changed_modes) if changed_modes else "none",
        )

    def log_audio_switch_busy(self, mode, source):
        now = time.monotonic()
        if now - getattr(self, "audio_switch_ignored_log_time", 0) >= 1.0:
            self.audio_switch_ignored_log_time = now
            logging.info("audio switch ignored while busy requested=%s current_target=%s source=%s", mode, self.audio_switch_target, source)

    def queue_pending_audio_switch(self, mode, source):
        if mode not in ("speaker", "headset") or not self.is_audio_mode_configured(mode):
            return
        if mode == self.audio_switch_target:
            self.log_settings_event_throttled("same_target_busy", 1.0, "audio_click_ignored_same_target", mode=mode, source=source)
            return
        if mode == self.pending_audio_switch_mode:
            self.log_settings_event_throttled("same_pending_busy", 1.0, "audio_click_ignored_same_pending", mode=mode, source=source)
            return
        self.pending_audio_switch_mode = mode
        self.pending_audio_switch_source = source
        self.log_audio_switch_busy(mode, source)
        now = time.monotonic()
        if now - getattr(self, "settings_pending_log_time", 0) >= 0.5:
            self.settings_pending_log_time = now
            logging.info("audio switch queued latest mode=%s source=%s", mode, source)
            self.log_settings_event("audio_switch_pending_updated", mode=mode, source=source, current_target=self.audio_switch_target)

    def consume_pending_audio_switch(self):
        mode = self.pending_audio_switch_mode
        source = self.pending_audio_switch_source or "manual"
        self.pending_audio_switch_mode = None
        self.pending_audio_switch_source = None
        if mode not in ("speaker", "headset"):
            return None, source
        return mode, source

    def manual_set_audio(self, mode):
        source_area = "mini" if self.is_mini else "settings"
        self.log_settings_event("manual_audio_click", mode=mode, source_area=source_area, switching=self.audio_switching, current_target=self.audio_switch_target)
        if self.audio_switching:
            if mode == self.audio_switch_target or mode == self.pending_audio_switch_mode:
                self.log_settings_event_throttled("busy_click_duplicate", 1.0, "manual_audio_click_ignored_duplicate", mode=mode, current_target=self.audio_switch_target, pending=self.pending_audio_switch_mode)
                return
            if not self.is_mini:
                self.apply_settings_device_selection(mode)
            self.queue_pending_audio_switch(mode, "manual")
            return
        if not self.is_mini:
            self.apply_settings_device_selection(mode)
        logging.info("manual audio requested mode=%s last_state=%s switching=%s", mode, self.last_state, self.audio_switching)
        self.request_audio_switch(mode, source="manual")

    def request_audio_switch(self, mode, source="manual"):
        if mode not in ("speaker", "headset"):
            return
        if self.audio_switching:
            self.queue_pending_audio_switch(mode, source)
            return
        if not self.is_audio_mode_configured(mode):
            logging.info("audio switch skipped unconfigured mode=%s source=%s", mode, source)
            self.update_mini_buttons_ui(self.last_state)
            return
        current_mode = self.current_audio_mode_cache or self.last_state
        logging.info("audio switch starting mode=%s source=%s current=%s", mode, source, current_mode)
        if source == "hotkey":
            self.start_audio_switch(mode, source=source, on_success=lambda: self.finish_hotkey_audio_switch(mode))
        else:
            self.start_audio_switch(mode, source=source, on_success=lambda: self.finish_manual_audio_switch(mode))

    def finish_manual_audio_switch(self, mode):
        detected = self.find_matching_program() if self.is_mini else None
        self.last_state = mode
        self.manual_override = True
        self.manual_override_during_detection = detected is not None
        if detected and detected[0] == "ask_list" and mode == "headset":
            self.ask_restore_program = detected[1]
            self.ask_restore_prompt_key = None

    def finish_hotkey_audio_switch(self, mode):
        self.finish_manual_audio_switch(mode)
        if not self.is_mini and self.winfo_viewable():
            logging.info("output switch hotkey completed in settings mode=%s; keeping settings window visible", mode)
            return
        logging.info("output switch hotkey notification scheduled mode=%s duration=%s", mode, self.get_mini_notification_seconds())
        self.show_audio_change_notification(mode)

    def start_audio_switch(self, mode, source="manual", on_success=None, on_failure=None):
        if self.audio_switching:
            logging.info("audio switch ignored because already switching requested=%s current_target=%s", mode, self.audio_switch_target)
            return
        started_at = time.perf_counter()
        logging.info("audio switch start mode=%s is_mini=%s visible=%s", mode, self.is_mini, self.winfo_viewable())
        if not self.is_mini:
            self.log_settings_event("audio_switch_start", mode=mode, source=source, visible=self.winfo_viewable())
        if self.is_mini and not self.winfo_viewable():
            self.switch_mode("mini", focus=False, animate_mini=True)
        if self.is_mini:
            self.show_audio_switching_ui(mode)
        else:
            self.audio_switching = True
            self.audio_switch_target = mode
            self.audio_switch_previous_state = self.last_state
            self.last_state = mode
            self.current_audio_mode_cache = mode
            self.last_audio_sync_time = time.monotonic()
            self.update_device_controls_ui(mode)

        def worker():
            try:
                changed = self.set_audio(mode)
            except Exception:
                changed = False
                self.last_audio_switch_failure_reason = "exception"
                self.last_audio_switch_failure_target = self.audio_mode_target_name(mode)
                logging.exception("audio switch worker failed mode=%s", mode)
            worker_finished_at = time.perf_counter()
            if not self.is_mini:
                self.log_settings_event("audio_switch_worker_done", mode=mode, changed=changed, worker_ms=int((worker_finished_at - started_at) * 1000))
            self.after(0, lambda: self.finish_audio_switch(mode, changed, on_success, on_failure, worker_finished_at))

        threading.Thread(target=worker, daemon=True).start()

    def finish_audio_switch(self, mode, changed, on_success=None, on_failure=None, worker_finished_at=None):
        finish_started_at = time.perf_counter()
        if worker_finished_at is not None and not self.is_mini:
            self.log_settings_event("audio_switch_finish_callback", mode=mode, callback_delay_ms=int((finish_started_at - worker_finished_at) * 1000), changed=changed)
        logging.info("audio switch finish mode=%s changed=%s last_state_before=%s", mode, changed, self.last_state)
        previous_state = self.audio_switch_previous_state
        self.audio_switching = False
        self.audio_switch_target = None
        self.audio_switch_previous_state = None
        if self.is_mini or self.widget_exists(getattr(self, "mini_button_frame", None)):
            self.clear_audio_switching_ui(redraw=False)
        if changed:
            self.last_state = mode
            self.current_audio_mode_cache = mode
            self.last_audio_sync_time = time.monotonic()
            if self.is_mini:
                self.update_mini_buttons_ui(mode)
            else:
                self.update_device_controls_ui(mode)
            if on_success:
                on_success()
        else:
            if previous_state in ("speaker", "headset"):
                self.last_state = previous_state
                self.current_audio_mode_cache = previous_state
                self.last_audio_sync_time = time.monotonic()
            if self.is_mini:
                self.update_mini_buttons_ui(self.last_state)
            else:
                self.update_device_controls_ui(self.last_state)
            if on_failure:
                on_failure()
        pending_mode, pending_source = self.consume_pending_audio_switch()
        if pending_mode and pending_mode != self.last_state and self.is_audio_mode_configured(pending_mode):
            logging.info("audio switch starting queued latest mode=%s source=%s", pending_mode, pending_source)
            if not self.is_mini:
                self.log_settings_event("audio_switch_start_pending", mode=pending_mode, source=pending_source)
            self.after_idle(lambda m=pending_mode, s=pending_source: self.request_audio_switch(m, source=s))
        if not self.is_mini:
            self.log_settings_event("audio_switch_finish_end", mode=mode, elapsed_ms=int((time.perf_counter() - finish_started_at) * 1000), pending=pending_mode)

    def finish_monitor_audio_switch(self, target, program_name, icon, changed):
        logging.info("monitor audio switch finish target=%s program=%s changed=%s", target, program_name, changed)
        self.audio_switching = False
        self.audio_switch_target = None
        self.clear_audio_switching_ui(redraw=False)
        if changed:
            self.last_state = target
            self.current_audio_mode_cache = target
            self.last_audio_sync_time = time.monotonic()
            self.update_mini_buttons_ui(target)
            self.show_audio_change_notification(target, program_name, icon)
        else:
            self.update_mini_buttons_ui(self.last_state)

    def finish_restore_speaker_switch(self, changed):
        logging.info("restore speaker finish changed=%s", changed)
        self.audio_switching = False
        self.audio_switch_target = None
        self.clear_audio_switching_ui(redraw=False)
        if changed:
            self.last_state = "speaker"
            self.current_audio_mode_cache = "speaker"
            self.last_audio_sync_time = time.monotonic()
            self.manual_override = False
            self.manual_override_during_detection = False
            self.update_mini_buttons_ui("speaker")
            self.show_audio_change_notification("speaker", self.tr("no_program_detected"), None)
        else:
            self.update_mini_buttons_ui(self.last_state)

    def set_audio(self, mode):
        started_at = time.perf_counter()
        self.last_audio_switch_failure_reason = None
        self.last_audio_switch_failure_target = None
        self.refresh_audio_device_cache_if_stale(force=True)
        target, device_id = self.resolve_audio_mode_target(mode)
        target_is_active = self.is_audio_output_active(target)

        logging.info(
            "set_audio begin mode=%s target=%s device_id_known=%s target_active=%s",
            mode,
            target,
            bool(device_id),
            target_is_active,
        )
        if not target or target == "No audio device found":
            print(f"audio switch failed: no valid {mode} output device selected")
            self.last_audio_switch_failure_target = target
            logging.warning("set_audio failed invalid target mode=%s target=%s", mode, target)
            return False

        if self.set_audio_with_pycaw(target, device_id):
            if not target_is_active:
                self.remember_offline_audio_selection(mode, target)
                logging.info("set_audio accepted offline target via pycaw mode=%s target=%s elapsed_ms=%d", mode, target, int((time.perf_counter() - started_at) * 1000))
                return True
            if self.verify_audio_switch_target(mode, target, device_id):
                self.clear_offline_audio_selection("active pycaw switch succeeded")
                if self.audio_device_id_cache_dirty:
                    self.audio_device_id_cache_dirty = False
                    self.save_config()
                logging.info("set_audio success via pycaw mode=%s target=%s elapsed_ms=%d", mode, target, int((time.perf_counter() - started_at) * 1000))
                return True
            logging.warning("pycaw reported success but output verification failed mode=%s target=%s", mode, target)

        if self.audio_device_id_cache_dirty:
            try:
                self.audio_device_id_cache_dirty = False
                self.save_config()
            except Exception:
                logging.exception("failed to save audio device id cache after switch failure")
        if not target_is_active:
            self.remember_offline_audio_selection(mode, target)
            logging.warning(
                "set_audio deferred unavailable target after switch methods failed mode=%s target=%s elapsed_ms=%d",
                mode,
                target,
                int((time.perf_counter() - started_at) * 1000),
            )
            return True
        logging.warning("set_audio failed all methods mode=%s target=%s elapsed_ms=%d", mode, target, int((time.perf_counter() - started_at) * 1000))
        return False

    def audio_names_equal(self, left, right):
        return bool(left and right and left.strip().casefold() == right.strip().casefold())

    def get_current_output_info(self):
        comtypes_module = initialize_com_for_thread()
        try:
            import warnings

            warnings.filterwarnings("ignore")
            from pycaw.pycaw import AudioUtilities

            device = AudioUtilities.GetSpeakers()
            name = getattr(device, "FriendlyName", None) or getattr(device, "friendly_name", None) or ""
            return name, getattr(device, "id", "") or ""
        except Exception:
            return "", ""
        finally:
            uninitialize_com_for_thread(comtypes_module)

    def get_current_output_name(self):
        name, _ = self.get_current_output_info()
        return name

    def get_current_audio_mode(self):
        current_name, current_id = self.get_current_output_info()
        if not current_name and not current_id:
            return None
        return self.get_audio_mode_for_output(current_name, current_id)

    def get_audio_mode_for_output_name(self, current_name):
        return self.get_audio_mode_for_output(current_name, "")

    def get_audio_mode_for_output(self, current_name, current_id=""):
        speaker_id = self.config_data.get("speaker_id", "")
        headset_id = self.config_data.get("headset_id", "")
        if current_id and speaker_id and current_id == speaker_id:
            return "speaker"
        if current_id and headset_id and current_id == headset_id:
            return "headset"
        if self.audio_names_equal(current_name, self.config_data.get("speaker_name", "")):
            return "speaker"
        if self.audio_names_equal(current_name, self.config_data.get("headset_name", "")):
            return "headset"
        return None

    def verify_audio_switch_target(self, mode, target, device_id=""):
        for attempt in range(6):
            if attempt:
                time.sleep(0.08)
            current_name, current_id = self.get_current_output_info()
            current_mode = self.get_audio_mode_for_output(current_name, current_id)
            id_matches = bool(device_id and current_id and current_id == device_id)
            name_matches = self.audio_names_equal(current_name, target)
            if current_mode == mode or id_matches or name_matches:
                logging.info(
                    "audio switch verified mode=%s target=%s current_name=%s current_id=%s attempt=%s",
                    mode,
                    target,
                    current_name,
                    current_id,
                    attempt,
                )
                return True
        current_name, current_id = self.get_current_output_info()
        logging.warning(
            "audio switch verification failed mode=%s target=%s target_id=%s current_name=%s current_id=%s",
            mode,
            target,
            device_id,
            current_name,
            current_id,
        )
        self.last_audio_switch_failure_target = target
        self.last_audio_switch_failure_reason = "verification_failed"
        return False

    def get_cached_current_audio_mode(self, force=False):
        now = time.monotonic()
        offline_mode = getattr(self, "offline_audio_mode", None)
        if offline_mode in ("speaker", "headset"):
            offline_target = getattr(self, "offline_audio_target", None)
            configured_target = self.audio_mode_target_name(offline_mode)
            if not configured_target or configured_target != offline_target:
                self.clear_offline_audio_selection("configured output changed")
            else:
                self.refresh_audio_device_cache_if_stale(force=False)
                if not self.is_audio_output_active(offline_target):
                    self.current_audio_mode_cache = offline_mode
                    self.last_audio_sync_time = now
                    return offline_mode
                self.clear_offline_audio_selection("output became active")
                force = True
        if not force and self.current_audio_mode_cache and now - self.last_audio_sync_time < CURRENT_AUDIO_SYNC_INTERVAL_SECONDS:
            return self.current_audio_mode_cache
        current_mode = self.get_current_audio_mode()
        self.last_audio_sync_time = now
        if current_mode:
            self.current_audio_mode_cache = current_mode
        return current_mode

    def sync_last_state_with_current_output(self, force=False):
        current_mode = self.get_cached_current_audio_mode(force=force)
        if current_mode and current_mode != self.last_state:
            logging.info("current output sync state=%s -> %s", self.last_state, current_mode)
            self.last_state = current_mode
            self.after(0, lambda state=current_mode: self.update_mini_buttons_ui(state))
        return current_mode

    def force_startup_speaker_output(self):
        if not self.config_data.get("speaker_name"):
            return
        self.refresh_audio_device_cache_if_stale(force=True)
        self.audio_switching = True
        self.audio_switch_target = "speaker"
        try:
            changed = self.set_audio("speaker")
            current_mode = self.get_current_audio_mode()
            if changed or current_mode == "speaker":
                self.last_state = "speaker"
                self.current_audio_mode_cache = "speaker"
                self.last_audio_sync_time = time.monotonic()
                self.manual_override = False
                self.manual_override_during_detection = False
                self.after(0, lambda: self.update_mini_buttons_ui("speaker"))
        finally:
            self.audio_switching = False
            self.audio_switch_target = None

    def normalize_hotkey_name(self, key_name):
        if not key_name:
            return ""
        key_name = key_name.upper()
        aliases = {
            "ESCAPE": "ESC",
            "RETURN": "ENTER",
            "PRIOR": "PAGEUP",
            "NEXT": "PAGEDOWN",
        }
        return aliases.get(key_name, key_name)

    def configure_keyboard_api(self):
        if hasattr(self, "user32") and hasattr(self, "user32_callback") and hasattr(self, "kernel32"):
            return

        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32_callback = ctypes.PyDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        self.user32.SetWindowsHookExW.argtypes = [ctypes.c_int, LOW_LEVEL_KEYBOARD_PROC, HINSTANCE, wintypes.DWORD]
        self.user32.SetWindowsHookExW.restype = HHOOK
        self.user32.CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, WPARAM, LPARAM]
        self.user32.CallNextHookEx.restype = LRESULT
        self.user32_callback.CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, WPARAM, LPARAM]
        self.user32_callback.CallNextHookEx.restype = LRESULT
        self.user32.UnhookWindowsHookEx.argtypes = [HHOOK]
        self.user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel32.GetModuleHandleW.restype = HMODULE

    def install_keyboard_hook(self):
        if self.keyboard_hook:
            return

        self.configure_keyboard_api()

        def keyboard_proc(n_code, w_param, l_param):
            try:
                if n_code == 0:
                    if self.hotkey_capture_active:
                        return self.user32_callback.CallNextHookEx(self.keyboard_hook, n_code, w_param, l_param)
                    event = int(w_param)
                    data = ctypes.cast(ctypes.c_void_p(l_param), ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    output_hotkey = self.config_data.get("output_switch_hotkey", "")
                    output_vk = HOTKEY_VK.get(output_hotkey)
                    is_injected = bool(data.flags & LLKHF_INJECTED)

                    if self.ask_active and not self.ask_resolving and data.vkCode in (VK_RETURN, VK_ESCAPE):
                        if event in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            if self.ask_keyboard_down_vk != data.vkCode and not is_injected:
                                self.ask_keyboard_down_vk = data.vkCode
                                self.keyboard_event_queue.put("ask_accept" if data.vkCode == VK_RETURN else "ask_dismiss")
                            return 1
                        if event in (WM_KEYUP, WM_SYSKEYUP):
                            if self.ask_keyboard_down_vk == data.vkCode:
                                self.ask_keyboard_down_vk = None
                            return 1

                    if output_vk and data.vkCode == output_vk:
                        if event in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            if not self.output_switch_hotkey_down and not is_injected:
                                self.output_switch_hotkey_down = True
                                self.keyboard_event_queue.put("output_switch_hotkey")
                        elif event in (WM_KEYUP, WM_SYSKEYUP):
                            self.output_switch_hotkey_down = False
            except Exception:
                pass
            return self.user32_callback.CallNextHookEx(self.keyboard_hook, n_code, w_param, l_param)

        self.keyboard_hook_proc = LOW_LEVEL_KEYBOARD_PROC(keyboard_proc)
        module_handle = self.kernel32.GetModuleHandleW(None)
        self.keyboard_hook = self.user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self.keyboard_hook_proc,
            module_handle,
            0,
        )
        if not self.keyboard_hook:
            module_error = ctypes.get_last_error()
            self.keyboard_hook = self.user32.SetWindowsHookExW(
                WH_KEYBOARD_LL,
                self.keyboard_hook_proc,
                None,
                0,
            )
        if not self.keyboard_hook:
            hook_error = ctypes.get_last_error()
            self.keyboard_hook_proc = None
            print(f"keyboard hook install failed: error {hook_error or module_error}")

    def sync_keyboard_hook_state(self):
        has_hotkey = bool(self.config_data.get("output_switch_hotkey", "") or self.ask_active)
        if has_hotkey:
            self.install_keyboard_hook()
            self.start_keyboard_event_polling()
            return

        self.uninstall_keyboard_hook()
        self.output_switch_hotkey_down = False
        self.ask_keyboard_down_vk = None
        if self.keyboard_event_after_id:
            try:
                self.after_cancel(self.keyboard_event_after_id)
            except Exception:
                pass
            self.keyboard_event_after_id = None
        while True:
            try:
                self.keyboard_event_queue.get_nowait()
            except queue.Empty:
                break

    def start_keyboard_event_polling(self):
        if self.keyboard_event_after_id is None and self.is_running:
            self.keyboard_event_after_id = self.after(50, self.process_keyboard_events)

    def process_keyboard_events(self):
        self.keyboard_event_after_id = None
        self.repair_stuck_output_hotkey_state()
        processed = 0
        while processed < KEYBOARD_EVENTS_PER_TICK:
            try:
                event_name = self.keyboard_event_queue.get_nowait()
            except queue.Empty:
                break
            processed += 1

            if event_name == "output_switch_hotkey":
                self.handle_output_switch_hotkey_pressed()
            elif event_name == "ask_accept":
                self.handle_ask_enter_key()
            elif event_name == "ask_dismiss":
                self.handle_ask_escape_key()

        if self.is_running and self.keyboard_hook:
            self.keyboard_event_after_id = self.after(50, self.process_keyboard_events)

    def repair_stuck_output_hotkey_state(self):
        if not self.output_switch_hotkey_down:
            return
        output_hotkey = self.config_data.get("output_switch_hotkey", "")
        output_vk = HOTKEY_VK.get(output_hotkey)
        if not output_vk:
            self.output_switch_hotkey_down = False
            return
        try:
            self.configure_keyboard_api()
            if not (self.user32.GetAsyncKeyState(output_vk) & 0x8000):
                logging.info("output switch hotkey down state repaired hotkey=%s", output_hotkey)
                self.output_switch_hotkey_down = False
        except Exception:
            logging.debug("output hotkey state repair skipped", exc_info=True)

    def uninstall_keyboard_hook(self):
        if self.keyboard_hook:
            try:
                self.configure_keyboard_api()
                self.user32.UnhookWindowsHookEx(self.keyboard_hook)
            except Exception:
                pass
            self.keyboard_hook = None
            self.keyboard_hook_proc = None

    def handle_output_switch_hotkey_pressed(self):
        if not self.config_data.get("output_switch_hotkey", ""):
            return
        if self.audio_switching:
            logging.info("output switch hotkey ignored because audio is already switching target=%s", self.audio_switch_target)
            return
        current_mode = self.current_audio_mode_cache or self.last_state
        target = "speaker" if current_mode == "headset" else "headset"
        if not self.is_audio_mode_configured(target):
            logging.info("output switch hotkey skipped unconfigured target=%s device=%s", target, self.audio_mode_target_name(target))
            return
        logging.info("output switch hotkey pressed current=%s target=%s", current_mode, target)
        self.request_audio_switch(target, source="hotkey")

    def set_audio_with_pycaw(self, target, device_id=None):
        comtypes_module = initialize_com_for_thread()
        try:
            import warnings

            warnings.filterwarnings("ignore")
            from pycaw.pycaw import AudioUtilities
            from pycaw.constants import ERole
            from pycaw.utils import AudioDeviceState

            if device_id:
                try:
                    AudioUtilities.SetDefaultDevice(device_id, roles=[ERole.eMultimedia, ERole.eConsole, ERole.eCommunications])
                    logging.info("pycaw default endpoint set by stored id target=%s id=%s", target, device_id)
                    return True
                except Exception as exc:
                    logging.warning("pycaw stored endpoint id failed target=%s id=%s error=%s; retrying by endpoint name", target, device_id, exc)

            for device in AudioUtilities.GetAllDevices():
                if AudioUtilities.GetEndpointDataFlow(device.id) != "eRender":
                    continue
                name = getattr(device, "FriendlyName", None) or getattr(device, "friendly_name", None)
                if self.audio_names_equal(name, target):
                    with self.device_cache_lock:
                        self.audio_device_ids[target] = device.id
                        if getattr(device, "state", None) == AudioDeviceState.Active and target and target not in self.audio_device_names:
                            self.audio_device_names.append(target)
                    for mode_name in ("speaker", "headset"):
                        if self.config_data.get(f"{mode_name}_name") == target and self.config_data.get(f"{mode_name}_id") != device.id:
                            self.config_data[f"{mode_name}_id"] = device.id
                            self.audio_device_id_cache_dirty = True
                    AudioUtilities.SetDefaultDevice(device.id, roles=[ERole.eMultimedia, ERole.eConsole, ERole.eCommunications])
                    logging.info(
                        "pycaw default endpoint set by endpoint name target=%s id=%s state=%s",
                        target,
                        device.id,
                        getattr(device, "state", None),
                    )
                    return True
        except Exception as exc:
            print(f"pycaw audio switch failed: {exc}")
            logging.exception("pycaw audio switch failed target=%s", target)
        finally:
            uninitialize_com_for_thread(comtypes_module)
        return False

    def save_settings(self):
        self.remember_settings_geometry()
        self.apply_settings_device_selection()
        if hasattr(self, "output_switch_hotkey_var"):
            hotkey = self.output_switch_hotkey_var.get()
            self.config_data["output_switch_hotkey"] = "" if hotkey == HOTKEY_NONE_LABEL else hotkey
            self.output_switch_hotkey_down = False
        self.sync_keyboard_hook_state()
        if hasattr(self, "startup_var"):
            self.config_data["start_with_windows"] = bool(self.startup_var.get())
            self.set_startup_enabled(self.config_data["start_with_windows"])
        if hasattr(self, "ask_timeout_var"):
            ask_timeout = self.parse_ask_timeout_seconds(self.ask_timeout_var.get())
            self.config_data["ask_timeout_seconds"] = ask_timeout
            self.ask_timeout_var.set(self.format_ask_timeout_seconds(ask_timeout))
        if hasattr(self, "mini_notification_var"):
            mini_duration = self.parse_mini_notification_seconds(self.mini_notification_var.get())
            self.config_data["mini_notification_seconds"] = mini_duration
            self.mini_notification_var.set(self.format_mini_notification_seconds(mini_duration))
        if hasattr(self, "language_var"):
            self.config_data["language"] = language_code_from_label(self.language_var.get())
            self.language_var.set(language_label_for_code(self.config_data["language"]))
        self.save_config()

    def save_and_close(self):
        self.save_settings()
        self.switch_mode("mini")

    def set_startup_enabled(self, enabled):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, self.get_startup_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception as exc:
            messagebox.showwarning("Auto Audio", f"Startup setting failed:\n{exc}")
            return False

    def get_startup_command(self):
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'

        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        executable = pythonw if os.path.exists(pythonw) else sys.executable
        script = os.path.abspath(__file__)
        return f'"{executable}" "{script}"'

    def open_add_program_menu(self, key):
        menu = ctk.CTkToplevel(self)
        self.prepare_popup(menu, "Add Program", 418, 188, grab=True)

        ctk.CTkLabel(menu, text="Add Program", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", padx=UI_SPACE_LG, pady=(UI_SPACE_LG, UI_SPACE_SM))
        ctk.CTkButton(menu, text="+  Add .exe file", height=UI_CONTROL_HEIGHT, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=UI_RADIUS_CONTROL, font=("Segoe UI", 18), command=lambda: self.choose_add_exe(key, menu)).pack(fill="x", padx=UI_SPACE_LG, pady=(0, UI_SPACE_SM))
        ctk.CTkButton(menu, text="+  Add Running Program", height=UI_CONTROL_HEIGHT, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=UI_RADIUS_CONTROL, font=("Segoe UI", 18), command=lambda: self.choose_running_program(key, menu)).pack(fill="x", padx=UI_SPACE_LG)

    def choose_add_exe(self, key, menu):
        menu.destroy()
        self.add_exe_program(key)

    def choose_running_program(self, key, menu):
        menu.destroy()
        self.open_running_program_picker(key)

    def add_exe_program(self, key):
        path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
        if not path:
            return
        self.add_program(
            key,
            {
                "name": os.path.basename(path),
                "match_type": "process_name",
                "value": os.path.basename(path),
                "path": path,
                "target_audio": "headset",
            },
        )

    def open_running_program_picker(self, key):
        self.window_icon_cache = {}
        picker = ctk.CTkToplevel(self)
        picker.title("Add Running Program")
        picker.geometry(self.center_child_geometry(680, 560))
        picker.transient(self)
        picker.configure(fg_color=WINDOW_BG)
        self.apply_window_icon(picker)
        picker.after(20, lambda: self.apply_window_icon(picker))
        picker.after(50, lambda: self.apply_dark_title_bar(picker))
        picker.after(200, lambda: self.apply_dark_title_bar(picker))
        picker.after(500, lambda: self.apply_dark_title_bar(picker))

        header = ctk.CTkFrame(picker, fg_color="transparent")
        header.pack(fill="x", padx=UI_SPACE_LG, pady=(UI_SPACE_LG, UI_SPACE_SM))
        ctk.CTkLabel(header, text="Running Programs", font=("Segoe UI", 18, "bold")).pack(side="left")

        sort_frame = ctk.CTkFrame(header, fg_color="transparent")
        sort_frame.pack(side="right")
        sort_buttons = {}
        sort_buttons["recent"] = ctk.CTkButton(sort_frame, text="Recent", width=74, height=UI_CONTROL_HEIGHT_COMPACT, corner_radius=UI_RADIUS_CONTROL)
        sort_buttons["recent"].pack(side="left", padx=(0, UI_SPACE_SM))
        sort_buttons["name"] = ctk.CTkButton(sort_frame, text="A-Z", width=58, height=UI_CONTROL_HEIGHT_COMPACT, corner_radius=UI_RADIUS_CONTROL)
        sort_buttons["name"].pack(side="left", padx=(0, UI_SPACE_SM))
        sort_buttons["resource"] = ctk.CTkButton(sort_frame, text="Resource", width=86, height=UI_CONTROL_HEIGHT_COMPACT, corner_radius=UI_RADIUS_CONTROL)
        sort_buttons["resource"].pack(side="left")

        scroll = ctk.CTkScrollableFrame(picker, fg_color=SURFACE_BG, corner_radius=UI_RADIUS_PANEL)
        scroll.pack(fill="both", expand=True, padx=UI_SPACE_LG, pady=(0, UI_SPACE_LG))

        processes = self.list_running_programs()
        sort_buttons["recent"].configure(command=lambda: self.render_running_programs(scroll, processes, key, picker, "recent", sort_buttons))
        sort_buttons["name"].configure(command=lambda: self.render_running_programs(scroll, processes, key, picker, "name", sort_buttons))
        sort_buttons["resource"].configure(command=lambda: self.render_running_programs(scroll, processes, key, picker, "resource", sort_buttons))
        self.render_running_programs(scroll, processes, key, picker, "recent", sort_buttons)

    def render_running_programs(self, scroll, processes, key, picker, sort_mode, sort_buttons=None):
        for widget in scroll.winfo_children():
            widget.destroy()

        if sort_buttons:
            for mode, button in sort_buttons.items():
                is_active = mode == sort_mode
                button.configure(
                    fg_color=ACTIVE_COLOR if is_active else "#333333",
                    hover_color=ACTIVE_HOVER_COLOR if is_active else CONTROL_HOVER,
                    text_color="white",
                )

        if not processes:
            ctk.CTkLabel(scroll, text="No selectable programs found", text_color="#888888").pack(pady=20)
            return

        if sort_mode == "resource":
            processes = sorted(processes, key=lambda item: (item.get("resource_score", 0), item.get("memory_mb", 0)), reverse=True)
        elif sort_mode == "recent":
            processes = sorted(processes, key=running_program_recent_sort_key, reverse=True)
        else:
            processes = sorted(processes, key=lambda item: item["name"].lower())

        for program in processes:
            row = ctk.CTkFrame(scroll, fg_color=PANEL_BG, corner_radius=UI_RADIUS_ROW)
            row.pack(fill="x", padx=UI_SPACE_XS, pady=UI_SPACE_XS)

            icon_source = program.get("path") or ""
            icon = self.get_cached_program_icon(icon_source, size=PROGRAM_ICON_SIZE, use_shell_fallback=False) if icon_source else None
            if icon is None and program.get("window_handle"):
                icon = self.get_cached_window_icon(program["window_handle"], size=PROGRAM_ICON_SIZE)
            ctk.CTkLabel(row, text="" if icon else "APP", image=icon, width=42, height=42, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(8, 4), pady=6)

            text_box = ctk.CTkFrame(row, fg_color="transparent")
            text_box.pack(side="left", fill="x", expand=True, padx=6, pady=6)
            ctk.CTkLabel(text_box, text=program["name"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            detail = f"CPU {program.get('cpu_percent', 0):.1f}%  |  RAM {program.get('memory_mb', 0):.1f} MB"
            ctk.CTkLabel(text_box, text=detail, font=("Segoe UI", 10), text_color="#8F8F8F", anchor="w").pack(fill="x")

            ctk.CTkButton(row, text="Add", width=62, height=UI_CONTROL_HEIGHT_COMPACT, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=UI_RADIUS_CONTROL, command=lambda p=program: self.pick_running_program(key, p, picker)).pack(side="right", padx=UI_SPACE_SM)

    def list_running_programs(self):
        started_at = time.perf_counter()
        current_pid = os.getpid()
        candidates = []
        grouped = {}
        visible_windows = get_visible_window_processes()
        scan_errors = 0
        resource_filtered = 0
        missing_paths = 0

        for process in psutil.process_iter(["pid", "name", "exe", "create_time"]):
            try:
                name = process.info.get("name")
                pid = process.info.get("pid")
                if not name or pid == current_pid or pid == 0 or name.lower() in IGNORED_RUNNING_PROGRAM_NAMES:
                    continue
                process.cpu_percent(None)
                candidates.append(process)
            except Exception:
                scan_errors += 1
                continue

        time.sleep(RUNNING_PROGRAM_CPU_SAMPLE_SECONDS)

        for process in candidates:
            try:
                name = process.info.get("name")
                if not name:
                    continue
                pid = process.info.get("pid")
                path = process.info.get("exe") or ""
                if not path:
                    try:
                        path = process.exe() or ""
                    except Exception:
                        path = query_process_image_path(pid)
                if not path:
                    missing_paths += 1
                memory = process.info.get("memory_info")
                if memory is None:
                    memory = process.memory_info()
                memory_mb = (memory.rss / 1024 / 1024) if memory else 0
                raw_cpu_percent = float(process.cpu_percent(None) or 0)
                cpu_percent = min(100.0, raw_cpu_percent / CPU_CORE_COUNT)
                window_info = visible_windows.get(pid, {})
                has_visible_window = window_info.get("window_rank") is not None
                if not should_include_running_program(cpu_percent, memory_mb, has_visible_window):
                    resource_filtered += 1
                    continue

                item = grouped.setdefault(
                    name.casefold(),
                    {
                        "name": name,
                        "path": path,
                        "cpu_percent": 0,
                        "memory_mb": 0,
                        "resource_score": 0,
                        "create_time": 0,
                        "window_rank": None,
                        "window_handle": None,
                    },
                )
                item["cpu_percent"] += cpu_percent
                item["memory_mb"] += memory_mb
                item["cpu_percent"] = min(100.0, item["cpu_percent"])
                item["create_time"] = max(item["create_time"], float(process.info.get("create_time") or 0))
                if path and not item.get("path"):
                    item["path"] = path
                window_rank = window_info.get("window_rank")
                if window_rank is not None and (item.get("window_rank") is None or window_rank < item["window_rank"]):
                    item["window_rank"] = window_rank
                    item["window_handle"] = window_info.get("window_handle")
                item["resource_score"] = item["cpu_percent"] * 100 + item["memory_mb"]
            except Exception:
                scan_errors += 1
                continue

        results = list(grouped.values())
        logging.info(
            "running program scan complete candidates=%s selectable=%s filtered=%s missing_paths=%s errors=%s elapsed_ms=%s",
            len(candidates),
            len(results),
            resource_filtered,
            missing_paths,
            scan_errors,
            int((time.perf_counter() - started_at) * 1000),
        )
        return sorted(results, key=lambda item: item["name"].lower())

    def pick_running_program(self, key, program, picker):
        icon_path = self.cache_running_program_icon(program)
        self.add_program(
            key,
            {
                "name": program["name"],
                "match_type": "process_name",
                "value": program["name"],
                "path": program.get("path") or "",
                "icon_path": icon_path,
                "target_audio": "headset",
            },
        )
        picker.destroy()

    def edit_program_name(self, key, program):
        index = self.find_program_index(key, program)
        if index is None:
            return

        icon_path_var = ctk.StringVar(value=self.config_data[key][index].get("icon_path", ""))

        editor = ctk.CTkToplevel(self)
        self.prepare_popup(editor, "Edit Program", 418, 264, grab=True)

        ctk.CTkLabel(editor, text="Edit Program", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", padx=UI_SPACE_LG, pady=(UI_SPACE_LG, UI_SPACE_SM))

        icon_row = ctk.CTkFrame(editor, fg_color="transparent")
        icon_row.pack(fill="x", padx=UI_SPACE_LG, pady=(0, UI_SPACE_SM))

        preview_icon = self.get_cached_program_icon(
            self.get_program_icon_source(self.config_data[key][index]),
            size=54,
            source_size=MINI_DETECTED_ICON_SOURCE_SIZE,
            corner_radius=MINI_DETECTED_ICON_CORNER_RADIUS,
        )
        preview_label = ctk.CTkLabel(icon_row, text="" if preview_icon else "APP", image=preview_icon, width=56, height=54, fg_color="#24272B", corner_radius=UI_RADIUS_CONTROL, font=("Segoe UI", 10, "bold"))
        preview_label.pack(side="left", padx=(0, UI_SPACE_SM))

        entry = ctk.CTkEntry(
            icon_row,
            height=54,
            fg_color=FIELD_BG,
            border_color=FIELD_BORDER,
            border_width=2,
            corner_radius=UI_RADIUS_CONTROL,
            font=("Segoe UI", 15),
        )
        entry.pack(side="left", fill="both", expand=True)
        entry.insert(0, self.config_data[key][index].get("name", ""))
        entry.focus_set()
        entry.select_range(0, "end")

        def refresh_icon_preview():
            preview_source = icon_path_var.get() or self.config_data[key][index].get("path", "")
            icon = self.get_cached_program_icon(
                preview_source,
                size=54,
                source_size=MINI_DETECTED_ICON_SOURCE_SIZE,
                corner_radius=MINI_DETECTED_ICON_CORNER_RADIUS,
            )
            preview_label.configure(image=icon, text="" if icon else "APP")

        def choose_custom_image():
            path = filedialog.askopenfilename(
                parent=editor,
                filetypes=[
                    ("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.webp;*.ico"),
                    ("All files", "*.*"),
                ],
            )
            if path:
                icon_path_var.set(path)
                refresh_icon_preview()

        def choose_program_icon():
            path = filedialog.askopenfilename(parent=editor, filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
            if path:
                icon_path_var.set(path)
                refresh_icon_preview()

        icon_button_row = ctk.CTkFrame(editor, fg_color="transparent")
        icon_button_row.pack(fill="x", padx=UI_SPACE_LG, pady=(0, UI_SPACE_MD))
        ctk.CTkButton(icon_button_row, text="Custom Icon", height=UI_CONTROL_HEIGHT, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=UI_RADIUS_CONTROL, font=("Segoe UI", 13), command=choose_custom_image).pack(side="left", fill="x", expand=True, padx=(0, UI_SPACE_XS))
        ctk.CTkButton(icon_button_row, text="Program Icon", height=UI_CONTROL_HEIGHT, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=UI_RADIUS_CONTROL, font=("Segoe UI", 13), command=choose_program_icon).pack(side="left", fill="x", expand=True, padx=(UI_SPACE_XS, 0))

        button_row = ctk.CTkFrame(editor, fg_color="transparent")
        button_row.pack(fill="x", padx=UI_SPACE_LG, pady=(0, UI_SPACE_LG))

        def save_name():
            new_name = entry.get().strip()
            if not new_name:
                return
            self.config_data[key][index]["name"] = new_name
            self.config_data[key][index]["icon_path"] = icon_path_var.get()
            self.save_config()
            editor.destroy()
            self.refresh_program_lists()

        ctk.CTkButton(button_row, text="Save", height=UI_CONTROL_HEIGHT, fg_color=ACTIVE_COLOR, hover_color=ACTIVE_HOVER_COLOR, corner_radius=UI_RADIUS_CONTROL, font=("Segoe UI", 15), command=save_name).pack(side="left", fill="x", expand=True, padx=(0, UI_SPACE_XS))
        ctk.CTkButton(button_row, text="Cancel", height=UI_CONTROL_HEIGHT, fg_color="#991B1B", hover_color="#B91C1C", corner_radius=UI_RADIUS_CONTROL, font=("Segoe UI", 15), command=editor.destroy).pack(side="left", fill="x", expand=True, padx=(UI_SPACE_XS, 0))
        editor.bind("<Return>", lambda event: save_name())
        editor.bind("<Escape>", lambda event: editor.destroy())

    def add_program(self, key, program):
        if self.program_exists_anywhere(program):
            messagebox.showinfo("Auto Audio", "This program rule already exists.")
            return
        self.config_data[key].append(program)
        self.ensure_program_display_order()
        self.save_config()
        self.draw_ui()

    def program_exists_anywhere(self, program):
        return any(self.program_exists(key, program) for key in ("ask_list", "auto_list"))

    def program_exists(self, key, program):
        target = self.normalized_program_rule_key(program)
        return any(
            self.normalized_program_rule_key(item) == target
            for item in self.config_data[key]
        )

    def same_program_rule(self, left, right):
        return bool(
            left
            and right
            and left.get("match_type") == right.get("match_type")
            and left.get("value") == right.get("value")
        )

    def set_program_target(self, key, program, mode):
        program["target_audio"] = mode
        self.save_config()
        self.refresh_program_lists()

    def remove_program(self, key, program):
        name = program.get("name", "this program")
        if not messagebox.askyesno("Delete Program", f"Remove '{name}' from the list?"):
            return
        self.config_data[key] = [item for item in self.config_data[key] if item is not program]
        self.ensure_program_display_order()
        self.save_config()
        self.refresh_program_lists()

    def detection_rules_signature(self):
        return tuple(
            (key, item.get("match_type", "process_name"), item.get("value", ""), item.get("path", ""), item.get("target_audio", "headset"))
            for key in ("auto_list", "ask_list")
            for item in self.config_data.get(key, [])
        )

    def get_detection_rules(self):
        signature = self.detection_rules_signature()
        if signature == getattr(self, "detection_rules_cache_key", None):
            return getattr(self, "detection_rules_cache", [])

        rules = []
        for key in ("auto_list", "ask_list"):
            for program in self.config_data.get(key, []):
                match_type = program.get("match_type", "process_name")
                value = program.get("value", "")
                if not value:
                    continue
                path_value = program.get("path", "")
                rules.append(
                    {
                        "key": key,
                        "program": program,
                        "match_type": match_type,
                        "value": value,
                        "value_norm": value.casefold(),
                        "process_name_norm": self.normalize_process_name(value),
                        "process_stem_norm": self.normalize_process_stem(value),
                        "path_process_name_norm": self.normalize_process_name(path_value),
                        "path_process_stem_norm": self.normalize_process_stem(path_value),
                        "path_norm": os.path.normcase(os.path.abspath(value)) if match_type == "path" else value.casefold(),
                    }
                )
        self.detection_rules_cache_key = signature
        self.detection_rules_cache = rules
        return rules

    def normalize_process_name(self, value):
        text = (value or "").strip().strip('"')
        return os.path.basename(text).casefold()

    def normalize_process_stem(self, value):
        return os.path.splitext(self.normalize_process_name(value))[0]

    def collect_process_candidates(self, need_path=False, need_cmdline=False):
        candidates = []
        try:
            iterator = psutil.process_iter(["pid", "name"])
        except Exception:
            return candidates

        for process in iterator:
            try:
                name = process.info.get("name") or process.name() or ""
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except Exception:
                name = ""
            if not name:
                continue

            path = ""
            if need_path:
                try:
                    path = process.exe() or ""
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                    path = ""
                except Exception:
                    path = ""

            cmdline = ""
            if need_cmdline:
                try:
                    cmdline = " ".join(process.cmdline() or [])
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
                    cmdline = ""
                except Exception:
                    cmdline = ""

            candidates.append(
                {
                    "name": name,
                    "name_norm": self.normalize_process_name(name),
                    "stem_norm": self.normalize_process_stem(name),
                    "path": path,
                    "path_norm": os.path.normcase(os.path.abspath(path)) if path else "",
                    "cmdline": cmdline,
                    "cmdline_norm": cmdline.casefold(),
                }
            )
        return candidates

    def monitor_loop(self):
        self.force_startup_speaker_output()
        while self.is_running:
            if self.audio_switching:
                time.sleep(CHECK_INTERVAL_SECONDS)
                continue
            current_state = self.sync_last_state_with_current_output(force=False) or self.last_state
            found = self.find_matching_program()
            if found:
                list_key, program, process_path = found
                is_new_detection = not self.same_program_rule(self.recent_detected_program, program)
                self.recent_detected_program = program
                self.recent_detected_list_key = list_key
                self.detected_missing_since = None
                if is_new_detection:
                    if self.manual_override and not self.manual_override_during_detection:
                        logging.info("clearing stale manual override for new program detection name=%s", program.get("name"))
                        self.manual_override = False
                    logging.info(
                        "program detected list=%s name=%s match_type=%s value=%s target=%s process_path=%s current_state=%s",
                        list_key,
                        program.get("name"),
                        program.get("match_type"),
                        program.get("value"),
                        program.get("target_audio"),
                        process_path,
                        current_state,
                    )
                icon_source = self.get_program_icon_source(program, process_path)
                icon = self.get_cached_program_icon_if_ready(
                    icon_source,
                    size=MINI_DETECTED_ICON_SIZE,
                    source_size=MINI_DETECTED_ICON_SOURCE_SIZE,
                    corner_radius=MINI_DETECTED_ICON_CORNER_RADIUS,
                )
                target = program.get("target_audio", "headset")
                if icon is None and is_new_detection:
                    self.after(0, lambda p=program, s=icon_source: self.update_detect_ui_with_program_icon(p, s))
                else:
                    self.after(0, lambda p=program, i=icon: self.update_detect_ui(p.get("name", "Unknown"), i))
                if list_key == "ask_list":
                    self.ask_restore_program = program

                if self.manual_override:
                    if is_new_detection:
                        logging.info("program detection suppressed by manual override name=%s during_detection=%s", program.get("name"), self.manual_override_during_detection)
                elif list_key == "ask_list":
                    if current_state != target:
                        current_state = self.sync_last_state_with_current_output(force=False) or current_state
                    if current_state != target:
                        if self.is_audio_mode_configured(target) and self.can_schedule_ask_prompt(program, target):
                            self.after(0, lambda p=program: self.show_ask_prompt(p))
                        elif is_new_detection:
                            logging.info("ask prompt skipped unconfigured or pending target=%s device=%s program=%s", target, self.audio_mode_target_name(target), program.get("name"))
                elif current_state != target:
                    current_state = self.sync_last_state_with_current_output(force=False) or current_state
                    if current_state != target:
                        if self.is_audio_mode_configured(target):
                            self.after(0, lambda t=target: self.show_audio_switching_ui(t))
                            try:
                                changed = self.set_audio(target)
                            except Exception:
                                changed = False
                                self.last_audio_switch_failure_reason = "exception"
                                self.last_audio_switch_failure_target = self.audio_mode_target_name(target)
                                logging.exception("monitor audio switch failed target=%s", target)
                            self.after(0, lambda t=target, p=program, i=icon, c=changed: self.finish_monitor_audio_switch(t, p.get("name", "Program"), i, c))
                        elif is_new_detection:
                            logging.info("auto switch skipped unconfigured target=%s device=%s program=%s", target, self.audio_mode_target_name(target), program.get("name"))
            else:
                ended_list_key = self.recent_detected_list_key
                ended_program = self.recent_detected_program
                if self.recent_detected_program:
                    now = time.monotonic()
                    if self.detected_missing_since is None:
                        self.detected_missing_since = now
                    if now - self.detected_missing_since < PROGRAM_EXIT_GRACE_SECONDS:
                        time.sleep(CHECK_INTERVAL_SECONDS)
                        continue
                    logging.info("program no longer detected name=%s value=%s", self.recent_detected_program.get("name"), self.recent_detected_program.get("value"))
                    if ended_list_key == "auto_list":
                        self.ask_restore_program = ended_program
                        self.ask_restore_prompt_key = None
                        logging.info(
                            "auto program ended; asking before restore target=%s program=%s",
                            self.restore_target_for_program(ended_program),
                            ended_program.get("name"),
                        )
                    self.recent_detected_program = None
                    self.recent_detected_list_key = None
                    self.detected_missing_since = None
                self.pending_prompt_key = None
                current_state = self.sync_last_state_with_current_output(force=False) or self.last_state
                if self.should_prompt_ask_restore(current_state):
                    restore_program = self.ask_restore_program
                    restore_target = self.restore_target_for_program(restore_program)
                    restore_prompt_key = self.program_prompt_key(restore_program, restore_target)
                    self.ask_restore_prompt_key = restore_prompt_key
                    self.after(0, lambda p=restore_program, t=restore_target, k=restore_prompt_key: self.show_ask_prompt(p, target_override=t, prompt_key_override=k))
                    self.after(0, lambda: self.update_detect_ui(self.tr("no_program_detected"), None))
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    continue

                should_restore_speaker = (
                    current_state == "headset"
                    and not self.ask_restore_program
                    and (not self.manual_override or self.manual_override_during_detection)
                )
                if should_restore_speaker:
                    current_state = self.sync_last_state_with_current_output(force=False) or current_state
                    should_restore_speaker = (
                        current_state == "headset"
                        and not self.ask_restore_program
                        and (not self.manual_override or self.manual_override_during_detection)
                    )
                if should_restore_speaker:
                    if self.is_audio_mode_configured("speaker"):
                        self.after(0, lambda: self.show_audio_switching_ui("speaker"))
                        try:
                            changed = self.set_audio("speaker")
                        except Exception:
                            changed = False
                            self.last_audio_switch_failure_reason = "exception"
                            self.last_audio_switch_failure_target = self.audio_mode_target_name("speaker")
                            logging.exception("restore speaker switch failed")
                        self.after(0, lambda c=changed: self.finish_restore_speaker_switch(c))
                    else:
                        logging.info("restore speaker skipped unconfigured device=%s", self.audio_mode_target_name("speaker"))
                        self.manual_override = True
                        self.manual_override_during_detection = False
                        self.after(0, lambda state=current_state: self.update_mini_buttons_ui(state))
                elif self.manual_override_during_detection:
                    self.manual_override = False
                    self.manual_override_during_detection = False
                self.after(0, lambda: self.update_detect_ui(self.tr("no_program_detected"), None))

            time.sleep(CHECK_INTERVAL_SECONDS)

    def find_matching_program(self):
        rules = self.get_detection_rules()
        if not rules:
            return None

        need_window_titles = any(rule["match_type"] == "window_title" for rule in rules)
        need_path = any(rule["match_type"] == "path" for rule in rules)
        need_cmdline = any(rule["match_type"] == "cmdline" for rule in rules)
        active_titles = [title.casefold() for title in self.get_visible_window_titles()] if need_window_titles else []
        candidates = self.collect_process_candidates(need_path=need_path, need_cmdline=need_cmdline)

        name_candidates = {}
        stem_candidates = {}
        for candidate in candidates:
            name_candidates.setdefault(candidate["name_norm"], candidate)
            stem_candidates.setdefault(candidate["stem_norm"], candidate)

        for rule in rules:
            match_type = rule["match_type"]
            program = rule["program"]
            if match_type == "window_title":
                if any(rule["value_norm"] in title for title in active_titles):
                    return rule["key"], program, program.get("path")
                continue

            if match_type == "process_name":
                candidate = name_candidates.get(rule["process_name_norm"]) or stem_candidates.get(rule["process_stem_norm"])
                if not candidate and rule["path_process_name_norm"]:
                    candidate = name_candidates.get(rule["path_process_name_norm"]) or stem_candidates.get(rule["path_process_stem_norm"])
                if candidate:
                    return rule["key"], program, candidate.get("path") or program.get("path")
                continue

            if match_type == "path":
                for candidate in candidates:
                    if candidate.get("path_norm") == rule["path_norm"]:
                        return rule["key"], program, candidate.get("path")
                continue

            if match_type == "cmdline":
                for candidate in candidates:
                    if rule["value_norm"] in candidate.get("cmdline_norm", ""):
                        return rule["key"], program, candidate.get("path") or program.get("path")
        return None

    def get_visible_window_titles(self):
        titles = []

        def collect(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    titles.append(title)

        try:
            win32gui.EnumWindows(collect, None)
        except Exception:
            pass
        return titles

    def program_prompt_key(self, program, target):
        return f"{program.get('match_type')}:{program.get('value')}:{target}"

    def restore_target_for_program(self, program):
        return "speaker" if program.get("target_audio", "headset") == "headset" else "headset"

    def can_schedule_ask_prompt(self, program, target):
        prompt_key = self.program_prompt_key(program, target)
        if self.ask_active or self.pending_prompt_key == prompt_key:
            return False
        return True

    def should_prompt_ask_restore(self, current_state=None):
        if self.ask_active:
            return False
        if not self.ask_restore_program:
            return False
        restore_target = self.restore_target_for_program(self.ask_restore_program)
        if not self.is_audio_mode_configured(restore_target):
            self.log_once(
                ("ask_restore_unconfigured", self.program_prompt_key(self.ask_restore_program, restore_target)),
                "ask restore skipped unconfigured target=%s device=%s program=%s",
                restore_target,
                self.audio_mode_target_name(restore_target),
                self.ask_restore_program.get("name"),
            )
            self.ask_restore_program = None
            self.ask_restore_prompt_key = None
            self.manual_override = True
            self.manual_override_during_detection = False
            return False
        if current_state == restore_target:
            logging.info(
                "ask restore skipped because output already at target=%s program=%s",
                restore_target,
                self.ask_restore_program.get("name"),
            )
            self.ask_restore_program = None
            self.ask_restore_prompt_key = None
            return False
        prompt_key = self.program_prompt_key(self.ask_restore_program, restore_target)
        return self.ask_restore_prompt_key != prompt_key

    def show_ask_prompt(self, program, target_override=None, prompt_key_override=None):
        target = target_override or program.get("target_audio", "headset")
        prompt_key = prompt_key_override or self.program_prompt_key(program, target)
        if self.ask_active:
            self.log_once(
                ("ask_prompt_already_active", prompt_key),
                "ask prompt skipped already active target=%s program=%s",
                target,
                program.get("name"),
            )
            return
        self.cancel_audio_change_notification()
        if self.pending_prompt_key == prompt_key:
            self.log_once(("ask_prompt_duplicate", prompt_key), "ask prompt skipped duplicate key=%s", prompt_key)
            return

        logging.info("ask prompt show target=%s program=%s key=%s", target, program.get("name"), prompt_key)
        self.pending_prompt_key = prompt_key
        self.ask_active = True
        self.ask_resolving = False
        self.ask_program = program
        self.ask_target = target
        self.mini_pinned_by_user = False
        if target == program.get("target_audio", "headset"):
            self.ask_restore_program = program
        self.bind_ask_keyboard_shortcuts()
        self.sync_keyboard_hook_state()
        self.switch_mode("mini", focus=False, animate_mini=True)

        self.ask_remaining = self.get_ask_timeout_seconds()
        self.tick_ask_prompt(program, target)

    def tick_ask_prompt(self, program, target):
        if not self.ask_active:
            return
        if self.widget_exists(getattr(self, "ask_label_canvas", None)):
            self.ask_label_canvas.itemconfigure(self.ask_label_item, text=f"{program.get('name', 'Program')}  |  {self.ask_remaining}s")
        if self.ask_remaining <= 0:
            self.dismiss_ask_prompt()
            return
        self.ask_remaining -= 1
        self.ask_countdown_after_id = self.after(1000, lambda: self.tick_ask_prompt(program, target))

    def accept_ask_prompt(self, target):
        if not self.ask_active or self.ask_resolving:
            return
        self.ask_resolving = True
        logging.info("ask prompt accepted target=%s program=%s", target, self.ask_program.get("name") if self.ask_program else None)
        accepted_program = self.ask_program
        self.dismiss_ask_prompt(hide=False, immediate=True, mark_restore_dismissed=False)
        self.start_audio_switch(target, on_success=lambda: self.finish_accepted_ask_switch(target, accepted_program))

    def finish_accepted_ask_switch(self, target, accepted_program):
        self.last_state = target
        self.manual_override = False
        self.manual_override_during_detection = False
        self.update_mini_buttons_ui(target)
        program_name = accepted_program.get("name", "Program") if accepted_program else "Program"
        icon = self.get_cached_program_icon(
            self.get_program_icon_source(accepted_program),
            size=MINI_DETECTED_ICON_SIZE,
            source_size=MINI_DETECTED_ICON_SOURCE_SIZE,
            corner_radius=MINI_DETECTED_ICON_CORNER_RADIUS,
        ) if accepted_program else None
        if accepted_program and target == self.restore_target_for_program(accepted_program):
            self.ask_restore_program = None
            self.ask_restore_prompt_key = None
        else:
            self.ask_restore_program = accepted_program
            self.ask_restore_prompt_key = None
        self.show_audio_change_notification(target, program_name, icon, animate=False)

    def dismiss_ask_prompt(self, hide=True, immediate=False, mark_restore_dismissed=True):
        if not self.ask_active and not self.ask_resolving:
            return
        self.ask_resolving = True
        logging.info("ask prompt dismissed hide=%s immediate=%s mark_restore=%s target=%s program=%s", hide, immediate, mark_restore_dismissed, self.ask_target, self.ask_program.get("name") if self.ask_program else None)
        dismissed_restore_prompt = (
            mark_restore_dismissed
            and self.ask_restore_program is not None
            and self.ask_target == self.restore_target_for_program(self.ask_restore_program)
        )
        if self.ask_countdown_after_id:
            try:
                self.after_cancel(self.ask_countdown_after_id)
            except Exception:
                pass
            self.ask_countdown_after_id = None
        if dismissed_restore_prompt:
            self.ask_restore_program = None
            self.ask_restore_prompt_key = None
            self.manual_override = True
            self.manual_override_during_detection = False
        self.ask_active = False
        self.ask_resolving = False
        self.ask_program = None
        self.ask_target = None
        self.ask_keyboard_down_vk = None
        self.unbind_ask_keyboard_shortcuts()
        self.sync_keyboard_hook_state()
        if hide and self.is_mini and self.winfo_viewable():
            if self.mini_pinned_by_user:
                logging.info("ask prompt hide overriding pinned mini state")
                self.mini_pinned_by_user = False
            self.animate_mini_out()

    def start_tray(self):
        if self.tray:
            return
        menu = pystray.Menu(
            pystray.MenuItem("Show Mini", self.show_app, default=True),
            pystray.MenuItem("Settings", self.show_settings_from_tray),
            pystray.MenuItem("Quit", self.quit_app),
        )
        self.tray = pystray.Icon("AutoAudio", make_tray_image(), "Auto Audio Switcher", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def hide_to_tray(self):
        logging.info("hide_to_tray is_mini=%s visible=%s ask=%s notification=%s", self.is_mini, self.winfo_viewable(), self.ask_active, self.notification_active)
        self.mini_pinned_by_user = False
        if self.is_mini and self.winfo_viewable():
            self.animate_mini_out()
        else:
            self.cancel_mini_animation()
            self.withdraw()
        self.start_tray()

    def on_window_close(self):
        logging.info("window close requested is_mini=%s", self.is_mini)
        if not self.is_mini:
            self.save_settings()
        self.hide_to_tray()

    def show_app(self, *args):
        self.after(0, lambda: self.switch_mode("mini"))

    def show_settings_from_tray(self, *args):
        self.after(0, lambda: self.switch_mode("settings"))

    def quit_app(self, *args):
        logging.info("quit requested")
        self.is_running = False
        if self.log_cleanup_after_id:
            try:
                self.after_cancel(self.log_cleanup_after_id)
            except Exception:
                pass
            self.log_cleanup_after_id = None
        if self.keyboard_event_after_id:
            try:
                self.after_cancel(self.keyboard_event_after_id)
            except Exception:
                pass
            self.keyboard_event_after_id = None
        self.uninstall_keyboard_hook()
        if self.tray:
            self.tray.stop()
        self.after(0, self.destroy)


if __name__ == "__main__":
    setup_logging()
    if "--diagnostics" in sys.argv:
        diagnostics_dir = command_line_option_value(sys.argv, "--diagnostics-dir") or None
        diagnostics_ok, diagnostics_path = run_runtime_diagnostics(diagnostics_dir)
        logging.info("diagnostics requested result=%s report=%s", diagnostics_ok, diagnostics_path)
        sys.exit(0 if diagnostics_ok else 1)
    configure_windows_app_identity()
    preview_mode = "--ui-preview" in sys.argv
    single_instance_mutex = True if preview_mode else acquire_single_instance_mutex()
    if not single_instance_mutex:
        logging.info("second instance detected; exiting")
        sys.exit(0)

    start_mode = "settings" if preview_mode else "tray"
    if "--show" in sys.argv:
        start_mode = "mini"
    elif "--settings" in sys.argv:
        start_mode = "settings"

    print("Auto Audio Switcher is running.")
    print("Use the tray icon, or run with --show / --settings for visible test mode.")
    logging.info("starting application start_mode=%s argv=%s", start_mode, sys.argv)
    try:
        app = AutoAudioApp(start_mode=start_mode, preview_mode=preview_mode)
        app.mainloop()
    except Exception:
        log_exception("fatal application error")
        raise


