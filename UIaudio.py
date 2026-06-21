import json
import logging
import math
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
import winreg
import ctypes
from ctypes import wintypes
from logging.handlers import RotatingFileHandler
from tkinter import filedialog, font, messagebox

import customtkinter as ctk
import psutil
import pystray
import win32con
import win32gui
import win32process
import win32ui
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageTk


APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
LOG_DIR = os.path.join(APP_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "auto_audio_switcher.log")
APP_ICON_FILE = os.path.join(RESOURCE_DIR, "assets", "app_icon.png")
APP_ICON_ICO_FILE = os.path.join(RESOURCE_DIR, "assets", "app_icon.ico")
ICON_DIR = os.path.join(RESOURCE_DIR, "assets", "icons")
WINDOWS_APP_ID = "AutoAudioSwitcher.AutoAudioSwitcher"
SINGLE_INSTANCE_MUTEX_NAME = "Local\\AutoAudioSwitcher.SingleInstance"
ERROR_ALREADY_EXISTS = 183
CHECK_INTERVAL_SECONDS = 1
CURRENT_AUDIO_SYNC_INTERVAL_SECONDS = 5
PROGRAM_EXIT_GRACE_SECONDS = 1
ASK_TIMEOUT_SECONDS = 25
ASK_TIMEOUT_OPTION_SECONDS = list(range(5, 125, 5))
NOTIFICATION_SECONDS = 4
AUTO_CHANGE_NOTIFICATION_SECONDS = 5
MICROPHONE_NOTIFICATION_SECONDS = 3
STARTUP_MINI_POPUP_SECONDS = 3
SHOW_STARTUP_ONBOARDING_EVERY_RUN = False
AUDIO_SWITCH_VERIFY_TIMEOUT_SECONDS = 0.6
AUDIO_SWITCH_VERIFY_INTERVAL_SECONDS = 0.1
MINI_WIDTH = 546
MINI_HEIGHT = 94
MINI_ANIMATION_STEPS = 12
MINI_ANIMATION_INTERVAL_MS = 14
SETTINGS_DEFAULT_WIDTH = 1560
SETTINGS_DEFAULT_HEIGHT = 640
SETTINGS_MIN_WIDTH = 1560
SETTINGS_MIN_HEIGHT = 640
SETTINGS_DEVICE_GAP = 12
SETTINGS_LEFT_WIDTH = 300
SETTINGS_RIGHT_WIDTH = 1235
SETTINGS_DEVICE_WIDTH = 272
SETTINGS_MIC_HEIGHT = 37
SETTINGS_MIC_LABEL_WIDTH = 60
SETTINGS_MIC_HOTKEY_WIDTH = 58
SETTINGS_MIC_DETECT_WIDTH = 76
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
MINI_BUTTON_INACTIVE_COLOR = "#20073F"
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
IGNORED_RUNNING_PROGRAM_NAMES = {
    "idle",
    "system idle process",
}
APP_NAME = "AutoAudioSwitcher"
WINDOW_BG = "#171717"
TITLE_BAR_BG = "#0D0D0D"
SURFACE_BG = "#101010"
PANEL_BG = "#111111"
SETTINGS_OUTER_BG = "#212121"
SETTINGS_PANEL_BG = "#181818"
SETTINGS_PANEL_RADIUS = 8
SETTINGS_ROW_BG = "#1C1C1C"
SETTINGS_GRADIENT_END = SETTINGS_OUTER_BG
SETTINGS_GRADIENT_START = SETTINGS_GRADIENT_END
SETTINGS_DEVICE_ACTIVE_START = ACTIVE_GRADIENT_START
SETTINGS_DEVICE_ACTIVE_END = ACTIVE_GRADIENT_END
SETTINGS_SEPARATOR_COLOR = "#0C131F"
CARD_BG = "#1A1A1A"
CONTROL_BG = "#333333"
CONTROL_HOVER = "#414141"
FIELD_BG = "#303335"
FIELD_BORDER = "#4A4D50"
ACTIVE_COLOR = ACTIVE_GRADIENT_START
ACTIVE_HOVER_COLOR = "#1D4ED8"
MIC_MUTED_COLOR = "#7F1D1D"
MIC_ACTIVE_COLOR = "#334155"
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
WH_KEYBOARD_LL = 13
INPUT_KEYBOARD = 1
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
LLKHF_INJECTED = 0x10
KEYEVENTF_KEYUP = 0x0002
MAPVK_VK_TO_VSC = 0
DEFAULT_MICROPHONE_LABEL = "Default Microphone"
HOTKEY_NONE_LABEL = "None"
HOTKEY_OPTIONS = [HOTKEY_NONE_LABEL] + [f"F{index}" for index in range(1, 25)] + [chr(code) for code in range(ord("A"), ord("Z") + 1)]
HOTKEY_VK = {
    **{f"F{index}": 0x6F + index for index in range(1, 13)},
    **{f"F{index}": 0x7B + (index - 12) for index in range(13, 25)},
    **{chr(code): code for code in range(ord("A"), ord("Z") + 1)},
}
HHOOK = getattr(wintypes, "HHOOK", wintypes.HANDLE)
HINSTANCE = getattr(wintypes, "HINSTANCE", wintypes.HANDLE)
HMODULE = getattr(wintypes, "HMODULE", wintypes.HANDLE)
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
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


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


def apply_rounded_corners(image, radius):
    if radius <= 0:
        return image

    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=radius, fill=255)
    image = image.copy()
    image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
    return image


def get_icon_from_exe(exe_path, size=32, source_size=None, corner_radius=0):
    try:
        if not exe_path or not os.path.exists(exe_path):
            return None

        source_size = max(source_size or size, size)
        large_icons, small_icons = win32gui.ExtractIconEx(exe_path, 0)
        icons = (large_icons or small_icons) if size >= 32 else (small_icons or large_icons)
        if not icons:
            return None

        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(hdc, source_size, source_size)
        memory_dc = hdc.CreateCompatibleDC()
        memory_dc.SelectObject(bitmap)

        win32gui.DrawIconEx(memory_dc.GetSafeHdc(), 0, 0, icons[0], source_size, source_size, 0, 0, win32con.DI_NORMAL)
        for icon in large_icons + small_icons:
            win32gui.DestroyIcon(icon)

        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)
        image = Image.frombuffer("RGBA", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRA", 0, 1)
        source_corner_radius = int(corner_radius * source_size / size) if size else corner_radius
        image = apply_rounded_corners(image, source_corner_radius)
        return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
    except Exception:
        return None


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


def setup_logging():
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)s] %(threadName)s %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
        logging.info("logging started app_dir=%s resource_dir=%s frozen=%s", APP_DIR, RESOURCE_DIR, getattr(sys, "frozen", False))
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
    elif kind == "mic":
        draw.rounded_rectangle((size * 0.36, size * 0.16, size * 0.64, size * 0.58), radius=width, outline=c, width=width)
        draw.arc((size * 0.24, size * 0.34, size * 0.76, size * 0.78), 0, 180, fill=c, width=width)
        draw.line((size * 0.50, size * 0.76, size * 0.50, size * 0.90), fill=c, width=width)
        draw.line((size * 0.34, size * 0.90, size * 0.66, size * 0.90), fill=c, width=width)
    elif kind == "mic_muted":
        draw.rounded_rectangle((size * 0.36, size * 0.16, size * 0.64, size * 0.58), radius=width, outline=c, width=width)
        draw.arc((size * 0.24, size * 0.34, size * 0.76, size * 0.78), 0, 180, fill=c, width=width)
        draw.line((size * 0.50, size * 0.76, size * 0.50, size * 0.90), fill=c, width=width)
        draw.line((size * 0.34, size * 0.90, size * 0.66, size * 0.90), fill=c, width=width)
        draw.line((size * 0.20, size * 0.22, size * 0.80, size * 0.82), fill=c, width=width)
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
    for name in ("speaker", "headset", "gear", "trash", "handle", "minimize", "close", "edit", "mic", "mic_muted"):
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


def make_ui_icon_photo(kind, size=28):
    image = load_icon_image(kind)
    image.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(image, ((size - image.width) // 2, (size - image.height) // 2))
    return ImageTk.PhotoImage(canvas)


def ctk_image_to_photo(image, appearance_mode="dark"):
    if isinstance(image, ctk.CTkImage):
        return image.create_scaled_photo_image(1, appearance_mode)
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


def make_inactive_button_surface(width, height, radius=4, rounded_top=True, rounded_bottom=True, hover=False):
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


def make_mini_background_image():
    image = create_linear_gradient(MINI_WIDTH, MINI_HEIGHT, MINI_BG_GRADIENT_START, MINI_BG_GRADIENT_END, angle_degrees=91)
    return ImageTk.PhotoImage(image)


def make_mini_background_slice(width, height, x, y):
    background = create_linear_gradient(MINI_WIDTH, MINI_HEIGHT, MINI_BG_GRADIENT_START, MINI_BG_GRADIENT_END, angle_degrees=91)
    image = background.crop((x, y, x + width, y + height))
    return ImageTk.PhotoImage(image)


def make_setting_device_header_image(kind, text, active, width=269, height=39, hover=False):
    image = Image.new("RGBA", (width, height), SETTINGS_PANEL_BG)
    if active:
        background = create_css_like_gradient(width, height, SETTINGS_DEVICE_ACTIVE_START, SETTINGS_DEVICE_ACTIVE_END)
    else:
        background = make_inactive_button_surface(width, height, radius=4, rounded_bottom=False, hover=hover)

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, width - 1, height + 5), radius=8 if active else 5, fill=255)
    if active:
        background.putalpha(mask)
    image.alpha_composite(background)

    icon = load_icon_image(kind, black=False, inactive_gradient=not active, hover_gradient=hover)
    icon.thumbnail((24, 24), Image.LANCZOS)

    text_font = get_pil_text_font(18)

    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), text, font=text_font)
    content_width = icon.width + 8 + bbox[2] - bbox[0]
    x = (width - content_width) // 2
    y = (height - icon.height) // 2
    image.alpha_composite(icon, (x, y))
    text_fill = (255, 255, 255, 255)
    draw.text((x + icon.width + 8, (height - (bbox[3] - bbox[1])) / 2 - 1), text, fill=text_fill, font=text_font)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_setting_device_dropdown_image(text, active, width=269, height=37, hover=False, rounded_bottom=True):
    image = Image.new("RGBA", (width, height), SETTINGS_PANEL_BG)
    background = (
        create_css_like_gradient(width, height, SETTINGS_DEVICE_ACTIVE_START, SETTINGS_DEVICE_ACTIVE_END)
        if active
        else make_inactive_button_surface(width, height, radius=4, rounded_top=False, rounded_bottom=rounded_bottom, hover=hover)
    )
    image.alpha_composite(background)
    mask = Image.new("L", (width, height), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle((0, -6, width - 1, height - 1), radius=8 if active else 5, fill=255)
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
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=8, fill=255)
        background.putalpha(mask)
    else:
        background = make_inactive_button_surface(width, height, radius=4, hover=hover)
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
):
    surface = create_rgba_linear_gradient(
        width,
        height,
        INACTIVE_BUTTON_HOVER_GRADIENT_START if hover else INACTIVE_BUTTON_GRADIENT_START,
        INACTIVE_BUTTON_HOVER_GRADIENT_END if hover else INACTIVE_BUTTON_GRADIENT_END,
        angle_degrees=135,
    )
    mask = Image.new("L", (width, height), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = 4
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
):
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
    )
    image.alpha_composite(segment)

    text_font = get_pil_text_font(13)

    draw = ImageDraw.Draw(image)
    display_text = text
    max_text_width = max(24, width - 48)
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
    x = max(8, (width - text_width) // 2 - 8)
    y = (height - text_height) / 2 - bbox[1]
    draw.text((x, y), display_text, fill=(255, 255, 255, 255), font=text_font)

    arrow_x = width - 18
    arrow_y = height // 2
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
    mask_draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=8, fill=255)
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


def make_mini_button_image(kind, active=False, muted=False, hover=False):
    width = MINI_DEVICE_BUTTON_WIDTH
    height = MINI_DEVICE_BUTTON_HEIGHT
    if muted:
        background = Image.new("RGBA", (width, height), MIC_MUTED_COLOR)
    elif active:
        background = create_css_like_gradient(width, height, MINI_BUTTON_ACTIVE_GRADIENT_START, MINI_BUTTON_ACTIVE_GRADIENT_END)
    else:
        background = make_inactive_button_surface(width, height, radius=4, hover=hover)

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=8 if active else 4, fill=255)
    button = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    button.alpha_composite(background)
    if active or muted:
        button.putalpha(mask)

    icon = load_icon_image(kind, black=False, inactive_gradient=not active and not muted, hover_gradient=hover)
    icon.thumbnail((28, 28), Image.LANCZOS)
    x = (width - icon.width) // 2
    y = (height - icon.height) // 2
    button.alpha_composite(icon, (x, y))
    return ctk.CTkImage(light_image=button, dark_image=button, size=(width, height))


def make_audio_switching_button_image(width=AUDIO_SWITCHING_BUTTON_WIDTH, height=MINI_DEVICE_BUTTON_HEIGHT):
    image = Image.new("RGBA", (width, height), CONTROL_BG)
    mask = Image.new("L", (width, height), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle((0, 0, width - 1, height - 1), radius=8, fill=255)
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


def make_ask_button_photo(text, fill_color, width=72, height=42, text_color=(255, 255, 255, 255), bold=False):
    if fill_color == ACTIVE_COLOR:
        image = create_css_like_gradient(width, height, ACTIVE_GRADIENT_START, ACTIVE_GRADIENT_END)
    else:
        image = Image.new("RGBA", (width, height), fill_color)
    draw = ImageDraw.Draw(image)
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width - 1, height - 1), radius=8, fill=255)
    image.putalpha(ImageChops.multiply(image.getchannel("A"), mask))
    text_font = get_pil_text_font(13, bold=bold)
    bbox = draw.textbbox((0, 0), text, font=text_font)
    draw.text(
        ((width - (bbox[2] - bbox[0])) / 2, (height - (bbox[3] - bbox[1])) / 2 - bbox[1] - 1),
        text,
        fill=text_color,
        font=text_font,
    )
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
    ImageDraw.Draw(yes_mask).rounded_rectangle((0, 0, 81, 41), radius=8, fill=255)
    yes.putalpha(yes_mask)
    yes_draw = ImageDraw.Draw(yes)
    yes_font = get_pil_text_font(14, bold=True)
    bbox = yes_draw.textbbox((0, 0), "Yes", font=yes_font)
    yes_draw.text(((82 - (bbox[2] - bbox[0])) / 2, (42 - (bbox[3] - bbox[1])) / 2 - bbox[1]), "Yes", fill=(255, 255, 255, 255), font=yes_font)
    image.alpha_composite(yes, (width - 190, prompt_y + 16))

    no = Image.new("RGBA", (82, 42), (68, 68, 68, 255))
    no_mask = Image.new("L", (82, 42), 0)
    ImageDraw.Draw(no_mask).rounded_rectangle((0, 0, 81, 41), radius=8, fill=255)
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
    def __init__(self, start_mode="tray"):
        super().__init__()
        logging.info("AutoAudioApp init start_mode=%s", start_mode)

        ctk.set_appearance_mode("dark")
        self.config_data = self.load_config()
        self.is_mini = True
        self.is_running = True
        self.last_state = "speaker"
        self.manual_override = False
        self.manual_override_during_detection = False
        self.mic_muted = False
        self.current_detected_name = "No Program Detected"
        self.current_detected_icon = None
        self.pending_prompt_key = None
        self.ask_countdown_after_id = None
        self.notification_after_id = None
        self.ask_active = False
        self.ask_program = None
        self.ask_target = None
        self.ask_restore_program = None
        self.ask_restore_prompt_key = None
        self.recent_detected_program = None
        self.detected_missing_since = None
        self.notification_active = False
        self.current_audio_mode_cache = None
        self.last_audio_sync_time = 0
        self.detection_rules_cache_key = None
        self.detection_rules_cache = []
        self.onboarding_active = False
        self.drag_data = None
        self.mini_animation_after_id = None
        self.mini_pinned_by_user = False
        self.keyboard_hook = None
        self.keyboard_hook_proc = None
        self.keyboard_event_queue = queue.SimpleQueue()
        self.keyboard_event_after_id = None
        self.microphone_hotkey_down = False
        self.list_drop_targets = {}
        self.program_list_scrolls = {}
        self.program_row_widgets = {}
        self.exe_icon_cache = {}
        self.program_icon_preload_queue = []
        self.audio_device_ids = {}
        self.microphone_device_names = []
        self.device_cache_lock = threading.Lock()
        self.audio_switching = False
        self.audio_switch_target = None
        self.settings_device_refresh_active = False
        self.device_controls = {}
        self.mic_controls = None
        self.settings_bg_bound = False
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
            "mic": make_ui_icon("mic", 28),
            "mic_muted": make_ui_icon("mic_muted", 28),
            "no_app": make_ui_icon("NoAppDetected", MINI_DETECTED_ICON_SIZE),
        }
        self.app_window_icon_photo = ImageTk.PhotoImage(make_app_icon_image(64))
        self.mini_button_images = {
            "mic": make_mini_button_image("mic", active=False),
            "mic_hover": make_mini_button_image("mic", active=False, hover=True),
            "mic_muted": make_mini_button_image("mic_muted", muted=True),
            "speaker_active": make_mini_button_image("speaker", active=True),
            "speaker_inactive": make_mini_button_image("speaker", active=False),
            "speaker_hover": make_mini_button_image("speaker", active=False, hover=True),
            "headset_active": make_mini_button_image("headset", active=True),
            "headset_inactive": make_mini_button_image("headset", active=False),
            "headset_hover": make_mini_button_image("headset", active=False, hover=True),
            "switching": make_audio_switching_button_image(),
        }
        self.current_detected_icon = self.icons["no_app"]
        self.audio_device_names = []
        self.refresh_audio_device_cache(include_input=False)
        self.sync_audio_config_with_devices(save_changes=True)

        self.title("Auto Audio Switcher")
        self.apply_window_icon(self)
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)

        self.set_ui_mode("mini")
        self.draw_ui()
        self.start_tray()
        self.sync_keyboard_hook_state()
        self.after(800, self.preload_program_icon_cache)

        if start_mode == "settings":
            self.switch_mode("settings")
        elif start_mode == "mini":
            self.switch_mode("mini")
        else:
            self.show_startup_mini_popup()
        self.after(250, self.show_startup_onboarding_popups)

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        logging.info("monitor thread started")

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
        # Development mode: keep showing these every launch. Later set
        # SHOW_STARTUP_ONBOARDING_EVERY_RUN to False to make this first-run only.
        if not SHOW_STARTUP_ONBOARDING_EVERY_RUN and self.config_data.get("onboarding_completed"):
            return
        self.onboarding_active = True
        self.show_audio_output_setup_popup()

    def show_audio_output_setup_popup(self):
        self.audio_device_names = self.get_output_device_names()
        device_options = self.build_device_options()
        speaker_default = self.config_data.get("speaker_name") if self.config_data.get("speaker_name") in device_options else device_options[0]
        headset_default = self.config_data.get("headset_name") if self.config_data.get("headset_name") in device_options else device_options[0]

        popup = ctk.CTkToplevel(self)

        def finish():
            if device_options and device_options[0] != "No audio device found":
                self.config_data["speaker_name"] = speaker_var.get()
                self.config_data["headset_name"] = headset_var.get()
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
        body.pack(fill="both", expand=True, padx=18, pady=14)

        ctk.CTkLabel(body, text="Choose audio outputs", font=("Segoe UI", 22, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(
            body,
            text="Select which Windows output device should be used for each mode.",
            font=("Segoe UI", 13),
            text_color="#B8B8B8",
            anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(4, 14))

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
            corner_radius=8,
            command=finish,
        ).pack(fill="x", pady=(0, 0))
        popup.after(100, popup.focus_force)

    def create_onboarding_device_dropdown(self, parent, variable, values):
        width = 484
        label = ctk.CTkLabel(parent, text="", width=width, height=38, cursor="hand2")
        menu = tk.Menu(
            label,
            tearoff=0,
            background=SURFACE_BG,
            foreground="white",
            activebackground=CONTROL_HOVER,
            activeforeground="white",
        )

        def refresh():
            image = make_onboarding_dropdown_image(variable.get(), width)
            label._onboarding_dropdown_image = image
            label.configure(image=image)

        def select(value):
            variable.set(value)
            refresh()

        for value in values:
            menu.add_command(label=value, command=lambda selected=value: select(selected))

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
            500,
            grab=False,
            close_command=finish,
            allow_minimize=False,
            center_on_screen=True,
        )
        popup.protocol("WM_DELETE_WINDOW", finish)

        body = ctk.CTkFrame(popup, fg_color=WINDOW_BG, corner_radius=0)
        body.pack(fill="both", expand=True, padx=18, pady=16)

        ctk.CTkLabel(body, text="How program rules work", font=("Segoe UI", 22, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(
            body,
            text="Use these two lists depending on how much control you want.",
            font=("Segoe UI", 13),
            text_color="#B8B8B8",
            anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(4, 16))

        for title, description in (
            ("Auto Change", "When a matching program is detected, the audio output changes immediately."),
            ("Ask Before Change", "When a matching program is detected, a small prompt asks before switching."),
        ):
            card = ctk.CTkFrame(body, fg_color=PANEL_BG, corner_radius=8)
            card.pack(fill="x", pady=(0, 10))
            ctk.CTkLabel(card, text=title, font=("Segoe UI", 15, "bold"), text_color="white").pack(anchor="w", padx=14, pady=(12, 2))
            ctk.CTkLabel(card, text=description, font=("Segoe UI", 12), text_color="#B8B8B8", anchor="w", justify="left", wraplength=470).pack(anchor="w", padx=14, pady=(0, 12))
            if title == "Ask Before Change":
                self.ask_before_change_preview_image = make_ask_before_change_preview_image()
                ctk.CTkLabel(card, text="", image=self.ask_before_change_preview_image).pack(fill="x", padx=14, pady=(0, 14))

        ctk.CTkButton(
            body,
            text="Got it",
            height=40,
            fg_color=ACTIVE_COLOR,
            hover_color=ACTIVE_HOVER_COLOR,
            text_color="white",
            corner_radius=8,
            command=finish,
        ).pack(fill="x", pady=(2, 0))
        popup.after(100, popup.focus_force)

    def default_config(self):
        return {
            "headset_name": "",
            "speaker_name": "",
            "auto_list": [],
            "ask_list": [],
            "start_with_windows": False,
            "settings_geometry": "",
            "microphone_name": DEFAULT_MICROPHONE_LABEL,
            "microphone_mute_hotkey": "",
            "ask_timeout_seconds": ASK_TIMEOUT_SECONDS,
            "onboarding_completed": False,
        }

    def load_config(self):
        config = self.default_config()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                    loaded = json.load(file)
                if isinstance(loaded, dict):
                    config.update(loaded)
            except Exception:
                pass

        config["auto_list"] = self.normalize_program_list(config.get("auto_list", []))
        config["ask_list"] = self.normalize_program_list(config.get("ask_list", []))
        config["ask_timeout_seconds"] = self.parse_ask_timeout_seconds(config.get("ask_timeout_seconds", ASK_TIMEOUT_SECONDS))
        return config

    def parse_ask_timeout_seconds(self, value):
        if isinstance(value, str):
            cleaned = value.strip().lower()
            for suffix in ("seconds", "second", "secs", "sec", "s"):
                cleaned = cleaned.replace(suffix, "")
            value = cleaned.strip()
        try:
            seconds = int(float(value))
        except (TypeError, ValueError):
            seconds = ASK_TIMEOUT_SECONDS
        return max(1, seconds)

    def get_ask_timeout_seconds(self):
        return self.parse_ask_timeout_seconds(self.config_data.get("ask_timeout_seconds", ASK_TIMEOUT_SECONDS))

    def format_ask_timeout_seconds(self, seconds=None):
        return f"{self.parse_ask_timeout_seconds(seconds if seconds is not None else self.get_ask_timeout_seconds())}s"

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

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(self.config_data, file, indent=4, ensure_ascii=False)

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
            self.resizable(True, True)
            self.overrideredirect(False)
            self.attributes("-topmost", False)
            self.set_settings_geometry()
            self.apply_window_icon(self)
            self.after(20, self.apply_window_icon)
            self.after(50, self.apply_dark_title_bar)
            self.after(200, self.apply_dark_title_bar)
            self.after(500, self.apply_dark_title_bar)

    def set_mini_geometry(self, extra_height=0):
        width, height, x, y = self.get_mini_geometry_parts(extra_height=extra_height)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def get_mini_geometry_parts(self, extra_height=0, y_offset=0):
        left, top, right, bottom = self.get_work_area()
        height = MINI_HEIGHT + extra_height
        x = max(left, right - MINI_WIDTH)
        y = max(top, bottom - height + y_offset)
        return MINI_WIDTH, height, x, y

    def get_mini_hidden_x(self):
        _, _, right, _ = self.get_work_area()
        return right

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

    def animate_mini_in(self):
        if not self.is_mini:
            return
        logging.info("mini animate in start visible=%s pinned=%s ask=%s notification=%s", self.winfo_viewable(), self.mini_pinned_by_user, self.ask_active, self.notification_active)
        self.cancel_mini_animation()
        width, height, final_x, y = self.get_mini_geometry_parts()
        start_y = self.get_mini_hidden_y()
        self.geometry(f"{width}x{height}+{final_x}+{start_y}")
        self.deiconify()
        self.lift()
        self.animate_mini_to(final_x, final_x, start_y, y, 0, hide_after=False)

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
        start_y = self.winfo_y()
        end_y = self.get_mini_hidden_y()
        self.geometry(f"{width}x{height}+{start_x}+{start_y}")
        self.animate_mini_to(start_x, start_x, start_y, end_y, 0, hide_after=True, on_complete=on_complete)

    def animate_mini_to(self, start_x, end_x, start_y, end_y, step, hide_after, on_complete=None):
        width, height, _, _ = self.get_mini_geometry_parts()
        progress = min(1, step / MINI_ANIMATION_STEPS)
        eased = 4 * progress ** 3 if progress < 0.5 else 1 - ((-2 * progress + 2) ** 3) / 2
        x = round(start_x + (end_x - start_x) * eased)
        y = round(start_y + (end_y - start_y) * eased)
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
            lambda: self.animate_mini_to(start_x, end_x, start_y, end_y, step + 1, hide_after, on_complete=on_complete),
        )

    def get_work_area(self):
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
        if "+" in geometry:
            return f"{width}x{height}+{parts[1]}"
        return self.center_settings_geometry_string(width, height)

    def center_settings_geometry(self, width, height):
        self.geometry(self.center_settings_geometry_string(width, height))

    def center_settings_geometry_string(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def remember_settings_geometry(self):
        if not self.is_mini:
            self.update_idletasks()
            width = max(SETTINGS_MIN_WIDTH, self.winfo_width())
            height = max(SETTINGS_MIN_HEIGHT, self.winfo_height())
            self.config_data["settings_geometry"] = f"{width}x{height}+{self.winfo_x()}+{self.winfo_y()}"

    def get_window_frame_handle(self):
        self.update_idletasks()
        raw_handle = None
        try:
            raw_handle = self.frame()
        except Exception:
            pass
        if not raw_handle:
            raw_handle = self.winfo_id()

        try:
            hwnd_value = int(raw_handle, 0) if isinstance(raw_handle, str) else int(raw_handle)
        except Exception:
            hwnd_value = int(self.winfo_id())

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

    def apply_dark_title_bar(self):
        try:
            hwnd = self.get_window_frame_handle()
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

    def fit_settings_geometry_to_content(self):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = max(600, self.winfo_reqwidth())
        height = min(self.winfo_reqheight() + 24, screen_height - 80)
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def install_settings_background(self):
        try:
            self.tk.call(self._w, "configure", "-background", SETTINGS_GRADIENT_END)
        except Exception:
            pass
        self.settings_bg_label = tk.Label(self, bd=0, highlightthickness=0, bg=SETTINGS_GRADIENT_END)
        self.settings_bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.settings_bg_label.lower()
        self._settings_bg_size = None
        if not self.settings_bg_bound:
            self.bind("<Configure>", self.update_settings_background, add="+")
            self.settings_bg_bound = True
        self.update_settings_background()

    def update_settings_background(self, event=None):
        if self.is_mini or not hasattr(self, "settings_bg_label"):
            return
        if not self.settings_bg_label.winfo_exists():
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
        x = parent_x + max(0, (parent_width - width) // 2)
        y = parent_y + max(0, (parent_height - height) // 2)
        return f"{width}x{height}+{x}+{y}"

    def center_screen_geometry(self, width, height):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        return f"{width}x{height}+{x}+{y}"

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

    def refresh_audio_device_cache(self, include_input=True):
        try:
            import warnings

            warnings.filterwarnings("ignore")
            from pycaw.pycaw import AudioUtilities
            from pycaw.utils import AudioDeviceState

            output_devices = []
            output_ids = {}
            input_devices = []
            for device in AudioUtilities.GetAllDevices():
                try:
                    if getattr(device, "state", None) != AudioDeviceState.Active:
                        continue
                    name = getattr(device, "FriendlyName", None) or getattr(device, "friendly_name", None)
                    if not name:
                        continue
                    flow = AudioUtilities.GetEndpointDataFlow(device.id)
                    if flow == "eRender" and name not in output_devices:
                        output_devices.append(name)
                        output_ids[name] = device.id
                    elif include_input and flow == "eCapture" and name not in input_devices:
                        input_devices.append(name)
                except Exception:
                    continue
            with self.device_cache_lock:
                self.audio_device_names = output_devices
                self.audio_device_ids = output_ids
                if include_input:
                    self.microphone_device_names = input_devices
            return output_devices, input_devices
        except Exception:
            with self.device_cache_lock:
                return list(getattr(self, "audio_device_names", [])), list(getattr(self, "microphone_device_names", []))

    def get_output_device_names(self, force=False):
        if force or not getattr(self, "audio_device_names", None):
            self.refresh_audio_device_cache(include_input=False)
        with self.device_cache_lock:
            return list(self.audio_device_names)

    def get_input_device_names(self, force=False):
        if force or not getattr(self, "microphone_device_names", None):
            self.refresh_audio_device_cache(include_input=True)
        with self.device_cache_lock:
            return list(self.microphone_device_names)

    def pick_audio_device(self, mode, devices, exclude=None):
        devices = [name for name in devices if name and name != "No audio device found"]
        if not devices:
            return ""
        excluded = {exclude} if exclude else set()
        candidates = [name for name in devices if name not in excluded] or devices
        hints = (
            ("headset", "headphone", "headphones", "earbuds", "earphone", "arctis", "razer", "logitech", "wireless")
            if mode == "headset"
            else ("speaker", "speakers", "realtek", "monitor", "display", "hdmi", "pebble")
        )
        for name in candidates:
            lowered = name.lower()
            if any(hint in lowered for hint in hints):
                return name
        return candidates[0]

    def sync_audio_config_with_devices(self, save_changes=False):
        devices = [name for name in getattr(self, "audio_device_names", []) if name]
        if not devices:
            return False

        changed = False
        speaker = self.config_data.get("speaker_name") or ""
        headset = self.config_data.get("headset_name") or ""

        if speaker not in devices:
            speaker = self.pick_audio_device("speaker", devices)
            self.config_data["speaker_name"] = speaker
            changed = True

        if headset not in devices or (len(devices) > 1 and headset == speaker):
            headset = self.pick_audio_device("headset", devices, exclude=speaker)
            self.config_data["headset_name"] = headset
            changed = True

        if changed and save_changes:
            self.save_config()
        return changed

    def draw_ui(self):
        self.unbind("<FocusOut>")
        self.settings_mic_header_refresh = None
        self.mic_controls = None
        for widget in self.winfo_children():
            widget.destroy()

        if self.is_mini:
            self.draw_mini_ui()
        else:
            self.list_drop_targets = {}
            self.draw_settings_ui()

    def create_marquee_label(self, parent, text, font_tuple, text_color, bg_color, height, bg_origin=None):
        canvas = tk.Canvas(parent, height=height, width=1, bg=bg_color, bd=0, highlightthickness=0, relief="flat")
        canvas._marquee_config = {
            "text": text or "",
            "font": font_tuple,
            "text_color": text_color,
            "bg_color": bg_color,
            "bg_origin": bg_origin,
            "height": height,
            "offset": 0,
            "direction": 1,
            "pause": MARQUEE_EDGE_PAUSE_TICKS,
            "job": None,
        }
        canvas.bind("<Configure>", lambda event, c=canvas: self.reset_marquee(c))
        self.render_marquee(canvas)
        return canvas

    def set_marquee_text(self, canvas, text):
        if not canvas or not canvas.winfo_exists():
            return
        config = canvas._marquee_config
        config["text"] = text or ""
        config["offset"] = 0
        config["direction"] = 1
        config["pause"] = MARQUEE_EDGE_PAUSE_TICKS
        self.cancel_marquee(canvas)
        self.render_marquee(canvas)

    def reset_marquee(self, canvas):
        if not canvas or not canvas.winfo_exists():
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
            if not canvas.winfo_exists():
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
                photo = make_mini_background_slice(width, height, bg_x, bg_y)
                canvas._marquee_bg_photo = photo
                canvas.create_image(0, 0, image=photo, anchor="nw")

            text_font = config["font"]
            text_width = self.measure_text(text, text_font)
            max_offset = max(0, text_width - width + MARQUEE_FADE_WIDTH)
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
            if not canvas.winfo_exists():
                return
            config = canvas._marquee_config
            width = canvas.winfo_width()
            max_offset = max(0, self.measure_text(config["text"], config["font"]) - width + MARQUEE_FADE_WIDTH)
            if max_offset <= 0:
                self.render_marquee(canvas)
                return

            if config["pause"] > 0:
                config["pause"] -= 1
            else:
                config["offset"] += config["direction"] * MARQUEE_STEP_PX
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
        if not hasattr(self, "mini_canvas") or not self.mini_canvas.winfo_exists():
            return
        display_name = name or "No Program Detected"
        display_icon = icon or self.icons.get("no_app")
        font_tuple = ("Segoe UI", 17, "bold")
        max_text_width = max(40, MINI_WIDTH - 76 - 168 - 30)
        self.mini_canvas.itemconfigure(self.mini_name_item, text=self.fit_text_to_width(display_name, font_tuple, max_text_width))
        self.mini_detected_photo = ctk_image_to_photo(display_icon)
        self.mini_canvas.itemconfigure(self.mini_icon_item, image=self.mini_detected_photo)

    def draw_marquee_fade(self, canvas, bg_color, width, height, bg_origin=None):
        fade_width = min(MARQUEE_FADE_WIDTH, max(1, width))
        if bg_origin:
            bg_x, bg_y = bg_origin
            background = create_linear_gradient(MINI_WIDTH, MINI_HEIGHT, MINI_BG_GRADIENT_START, MINI_BG_GRADIENT_END, angle_degrees=91)
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

        mini_canvas = tk.Canvas(self, width=MINI_WIDTH, height=MINI_HEIGHT, highlightthickness=0, bd=0, bg=MINI_BG_FALLBACK)
        self.mini_canvas = mini_canvas
        mini_canvas.pack(fill="both", expand=True)
        self.mini_bg_photo = make_mini_background_image()
        mini_canvas.create_image(0, 0, image=self.mini_bg_photo, anchor="nw")
        mini_canvas.bind("<ButtonPress-1>", self.start_move)
        mini_canvas.bind("<B1-Motion>", self.do_move)

        header = ctk.CTkFrame(mini_canvas, fg_color="transparent", height=28, corner_radius=0)
        mini_canvas.create_window(0, 0, window=header, anchor="nw", width=MINI_WIDTH, height=28)
        header.pack_propagate(False)
        header.bind("<ButtonPress-1>", self.start_move)
        header.bind("<B1-Motion>", self.do_move)

        ctk.CTkLabel(header, text="", image=self.icons["app"], width=18, height=18).pack(side="left", padx=(7, 7), pady=5)
        ctk.CTkLabel(header, text="Auto Audio", font=("Segoe UI", 11), text_color="#E8E8E8").pack(side="left")
        ctk.CTkButton(header, text="", image=self.icons["close"], width=28, height=24, fg_color="transparent", hover_color="#333333", command=self.hide_to_tray).pack(side="right", padx=(0, 4))
        ctk.CTkButton(header, text="", image=self.icons["minimize"], width=28, height=24, fg_color="transparent", hover_color="#333333", command=self.hide_to_tray).pack(side="right", padx=2)
        ctk.CTkButton(header, text="", image=self.icons["gear"], width=34, height=24, fg_color="transparent", hover_color="#333333", command=lambda: self.switch_mode("settings")).pack(side="right", padx=4)

        self.mini_detected_photo = ctk_image_to_photo(self.current_detected_icon)
        self.mini_icon_item = mini_canvas.create_image(38, 62, image=self.mini_detected_photo)
        self.mini_name_item = mini_canvas.create_text(76, 62, text="", fill="white", font=("Segoe UI", 17, "bold"), anchor="w")
        self.update_mini_detect_canvas(self.current_detected_name, self.current_detected_icon)

        button_frame = ctk.CTkFrame(mini_canvas, fg_color="transparent", bg_color="transparent")
        self.mini_button_frame = button_frame
        mini_canvas.create_window(MINI_WIDTH - 12, 62, window=button_frame, anchor="e", width=(MINI_DEVICE_BUTTON_WIDTH * 3) + (MINI_DEVICE_BUTTON_GAP * 2), height=MINI_DEVICE_BUTTON_HEIGHT)

        self.mic_btn = ctk.CTkLabel(button_frame, text="", image=self.mini_button_images["mic"], width=MINI_DEVICE_BUTTON_WIDTH, height=MINI_DEVICE_BUTTON_HEIGHT)
        self.mic_btn.bind("<Button-1>", lambda event: self.toggle_microphone_mute())
        self.mic_btn.bind("<Enter>", lambda event: self.set_mic_button_hover(True))
        self.mic_btn.bind("<Leave>", lambda event: self.set_mic_button_hover(False))
        self.mic_btn.pack(side="left", padx=(0, MINI_DEVICE_BUTTON_GAP))

        self.speaker_btn = ctk.CTkLabel(button_frame, text="", image=self.mini_button_images["speaker_inactive"], width=MINI_DEVICE_BUTTON_WIDTH, height=MINI_DEVICE_BUTTON_HEIGHT)
        self.speaker_btn.bind("<Button-1>", lambda event: self.manual_set_audio("speaker"))
        self.speaker_btn.pack(side="left", padx=(0, MINI_DEVICE_BUTTON_GAP))

        self.headset_btn = ctk.CTkLabel(button_frame, text="", image=self.mini_button_images["headset_inactive"], width=MINI_DEVICE_BUTTON_WIDTH, height=MINI_DEVICE_BUTTON_HEIGHT)
        self.headset_btn.bind("<Button-1>", lambda event: self.manual_set_audio("headset"))
        self.headset_btn.pack(side="left")

        self.update_mini_buttons_ui(self.last_state)
        if self.audio_switching:
            self.show_audio_switching_ui(self.audio_switch_target, redraw=False)
        self.refresh_microphone_mute_ui()

    def draw_ask_mini_ui(self):
        self.configure(fg_color=MINI_BG_FALLBACK)
        target = self.ask_target or "headset"
        program_name = self.ask_program.get("name", "Program") if self.ask_program else "Program"

        mini_canvas = tk.Canvas(self, width=MINI_WIDTH, height=MINI_HEIGHT, highlightthickness=0, bd=0, bg=MINI_BG_FALLBACK)
        mini_canvas.pack(fill="both", expand=True)
        self.ask_mini_bg_photo = make_mini_background_image()
        mini_canvas.create_image(0, 0, image=self.ask_mini_bg_photo, anchor="nw")
        mini_canvas.bind("<ButtonPress-1>", self.start_move)
        mini_canvas.bind("<B1-Motion>", self.do_move)

        self.ask_icon_photo = make_ui_icon_photo(target, 28)
        mini_canvas.create_image(91, 47, image=self.ask_icon_photo)
        mini_canvas.create_text(117, 32, text=f"Switch to {self.audio_label(target)}?", fill="white", font=("Segoe UI", 15, "bold"), anchor="w")
        self.ask_label_canvas = mini_canvas
        self.ask_label_item = mini_canvas.create_text(117, 62, text=program_name, fill="#B8B8B8", font=("Segoe UI", 11), anchor="w")

        self.ask_yes_button_photo = make_ask_button_photo("Yes", ACTIVE_COLOR, text_color=(255, 255, 255, 255), bold=True)
        self.ask_no_button_photo = make_ask_button_photo("No", "#444444")
        yes_button = mini_canvas.create_image(355, 49, image=self.ask_yes_button_photo)
        no_button = mini_canvas.create_image(433, 49, image=self.ask_no_button_photo)
        mini_canvas.tag_bind(yes_button, "<Button-1>", lambda event: self.accept_ask_prompt(target))
        mini_canvas.tag_bind(no_button, "<Button-1>", lambda event: self.dismiss_ask_prompt(immediate=True))

    def draw_settings_ui(self):
        self.configure(fg_color=SETTINGS_GRADIENT_END)
        self.device_controls = {}
        self.mic_controls = None
        self.settings_mic_header_refresh = None
        self.install_settings_background()
        device_options = self.build_device_options()
        microphone_options = self.build_microphone_options()

        bottom = ctk.CTkFrame(self, fg_color="transparent", bg_color=SETTINGS_GRADIENT_END)
        bottom.pack(side="bottom", fill="x", padx=0, pady=(0, 0))
        ctk.CTkButton(bottom, text="Save", height=39, fg_color=ACTIVE_COLOR, hover_color=ACTIVE_HOVER_COLOR, text_color="white", corner_radius=8, command=self.save_and_close).pack(fill="x", padx=8, pady=(0, 8))

        body = ctk.CTkFrame(self, fg_color="transparent", bg_color=SETTINGS_GRADIENT_END, corner_radius=0)
        body.pack(fill="both", expand=True, padx=8, pady=(8, 8))
        body.grid_columnconfigure(0, weight=0, minsize=SETTINGS_LEFT_WIDTH)
        body.grid_columnconfigure(1, weight=1, minsize=SETTINGS_RIGHT_WIDTH)
        body.grid_rowconfigure(0, weight=1)

        left_column = ctk.CTkFrame(body, fg_color="transparent", bg_color=SETTINGS_GRADIENT_END, corner_radius=0, width=SETTINGS_LEFT_WIDTH)
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left_column.grid_propagate(False)
        left_column.pack_propagate(False)

        right_column = ctk.CTkFrame(body, fg_color="transparent", bg_color=SETTINGS_GRADIENT_END, corner_radius=0)
        right_column.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        settings_panel = ctk.CTkFrame(left_column, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_GRADIENT_END, corner_radius=SETTINGS_PANEL_RADIUS, border_width=0)
        settings_panel.pack(fill="x", padx=0, pady=(0, 8))
        settings_content = ctk.CTkFrame(settings_panel, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        settings_content.pack(fill="x", padx=14, pady=8)

        ctk.CTkLabel(settings_content, text="Settings", font=("Segoe UI", 22, "bold"), text_color="white", fg_color="transparent", bg_color="transparent").pack(anchor="w", padx=0, pady=(0, 8))

        device_frame = ctk.CTkFrame(settings_content, fg_color="transparent", bg_color="transparent")
        device_frame.pack(fill="x", padx=0)
        device_frame.grid_columnconfigure(0, weight=1)

        self.create_device_box(device_frame, "Speaker", "speaker", device_options).grid(row=0, column=0, sticky="ew")
        self.create_device_box(device_frame, "Headset", "headset", device_options).grid(row=1, column=0, sticky="ew", pady=(SETTINGS_DEVICE_GAP, 0))

        self.create_microphone_settings(settings_content, microphone_options)

        self.startup_var = ctk.BooleanVar(value=bool(self.config_data.get("start_with_windows", False)))
        bottom_options = ctk.CTkFrame(settings_content, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        bottom_options.pack(fill="x", padx=0, pady=(16, 0))
        timeout_options = [self.format_ask_timeout_seconds(seconds) for seconds in ASK_TIMEOUT_OPTION_SECONDS]
        self.ask_timeout_var = ctk.StringVar(value=self.format_ask_timeout_seconds())
        ask_timeout_frame = ctk.CTkFrame(bottom_options, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        ask_timeout_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(
            ask_timeout_frame,
            text="Ask duration",
            font=("Segoe UI", 13),
            text_color="#B8B8B8",
            anchor="w",
        ).pack(fill="x", pady=(0, 5))
        self.ask_timeout_combo = ctk.CTkComboBox(
            ask_timeout_frame,
            values=timeout_options,
            variable=self.ask_timeout_var,
            width=SETTINGS_DEVICE_WIDTH,
            height=30,
            fg_color=CONTROL_BG,
            border_color=FIELD_BORDER,
            button_color=DEVICE_INACTIVE_COLOR,
            button_hover_color=CONTROL_HOVER,
            dropdown_fg_color=SURFACE_BG,
            dropdown_hover_color=CONTROL_HOVER,
            text_color="white",
            dropdown_text_color="white",
            font=("Segoe UI", 13),
            dropdown_font=("Segoe UI", 13),
        )
        self.ask_timeout_combo.pack(fill="x")
        self.ask_timeout_combo.bind("<FocusOut>", lambda event: self.ask_timeout_var.set(self.format_ask_timeout_seconds(self.ask_timeout_var.get())))
        self.ask_timeout_combo.bind("<Return>", lambda event: self.ask_timeout_var.set(self.format_ask_timeout_seconds(self.ask_timeout_var.get())))

        ctk.CTkCheckBox(
            bottom_options,
            text="Run on Start up",
            variable=self.startup_var,
            font=("Segoe UI", 14),
            fg_color=ACTIVE_COLOR,
            hover_color=ACTIVE_HOVER_COLOR,
        ).pack(anchor="w", pady=(0, 14))

        program_panel = ctk.CTkFrame(right_column, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_GRADIENT_END, corner_radius=SETTINGS_PANEL_RADIUS, border_width=0)
        program_panel.pack(fill="both", expand=False, padx=0, pady=(0, 0))
        program_content = ctk.CTkFrame(program_panel, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        program_content.pack(fill="both", expand=True, padx=14, pady=8)
        ctk.CTkLabel(program_content, text="Program List", font=("Segoe UI", 22, "bold"), text_color="white", fg_color="transparent", bg_color="transparent").pack(anchor="w", padx=0, pady=(0, 2))
        self.program_list_frame = ctk.CTkFrame(program_content, fg_color="transparent", bg_color="transparent", corner_radius=0)
        self.program_list_frame.pack(fill="both", expand=True)
        self.refresh_program_lists()
        program_panel.pack_propagate(False)

        def sync_program_panel_height():
            try:
                self.update_idletasks()
                target_height = max(1, settings_panel.winfo_height() or settings_panel.winfo_reqheight())
                program_panel.configure(height=target_height)
            except Exception:
                pass

        self.after(0, sync_program_panel_height)
        self.refresh_settings_devices_async()


    def build_device_options(self):
        options = [name for name in self.audio_device_names if name]
        return options or ["No audio device found"]

    def build_microphone_options(self):
        options = [DEFAULT_MICROPHONE_LABEL]
        for name in self.microphone_device_names:
            if name and name not in options:
                options.append(name)
        selected = self.config_data.get("microphone_name") or DEFAULT_MICROPHONE_LABEL
        if selected and selected not in options:
            options.append(selected)
        return options

    def refresh_settings_devices_async(self):
        if self.settings_device_refresh_active:
            return
        self.settings_device_refresh_active = True

        def worker():
            before_outputs = tuple(self.audio_device_names)
            before_inputs = tuple(self.microphone_device_names)
            self.refresh_audio_device_cache(include_input=True)
            self.sync_audio_config_with_devices(save_changes=True)
            changed = before_outputs != tuple(self.audio_device_names) or before_inputs != tuple(self.microphone_device_names)
            self.after(0, lambda: self.finish_settings_device_refresh(changed))

        threading.Thread(target=worker, daemon=True).start()

    def finish_settings_device_refresh(self, changed):
        self.settings_device_refresh_active = False
        if changed and not self.is_mini and self.winfo_viewable():
            self.update_settings_device_options()

    def replace_menu_commands(self, menu, options, command):
        menu.delete(0, "end")
        for option in options:
            menu.add_command(label=option, command=lambda value=option: command(value))

    def update_settings_device_options(self):
        device_options = self.build_device_options()
        for mode, controls in getattr(self, "device_controls", {}).items():
            variable = controls.get("variable")
            menu = controls.get("menu")
            if not variable or not menu:
                continue
            configured = self.config_data.get(f"{mode}_name")
            if variable.get() not in device_options:
                variable.set(configured if configured in device_options else device_options[0])
            self.replace_menu_commands(menu, device_options, variable.set)
            refresh = controls.get("refresh")
            if refresh:
                refresh()

        microphone_options = self.build_microphone_options()
        controls = getattr(self, "mic_controls", None)
        if controls:
            variable = controls.get("variable")
            menu = controls.get("menu")
            if variable and menu:
                configured = self.config_data.get("microphone_name")
                if variable.get() not in microphone_options:
                    variable.set(configured if configured in microphone_options else microphone_options[0])
                self.replace_menu_commands(menu, microphone_options, variable.set)
                refresh = controls.get("refresh")
                if refresh:
                    refresh()

    def create_device_box(self, parent, title, mode, device_options):
        header_width = SETTINGS_DEVICE_WIDTH
        frame = ctk.CTkFrame(parent, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, width=header_width, height=77, corner_radius=0)
        frame.pack_propagate(False)
        frame.grid_propagate(False)
        is_active = self.last_state == mode
        header_image = make_setting_device_header_image(mode, title, is_active, width=header_width)
        device_button = ctk.CTkLabel(frame, text="", image=header_image, width=header_width, height=39, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, cursor="hand2")
        device_button.configure(image=header_image)
        device_button._settings_header_image = header_image
        device_button.bind("<Button-1>", lambda event: self.manual_set_audio(mode))
        device_button.pack(fill="x")

        variable = ctk.StringVar(value=self.config_data.get(f"{mode}_name") if self.config_data.get(f"{mode}_name") in device_options else device_options[0])
        if mode == "speaker":
            self.sp_var = variable
        else:
            self.hs_var = variable

        selected_device = self.config_data.get(f"{mode}_name") if self.config_data.get(f"{mode}_name") in device_options else device_options[0]
        dropdown_image = make_setting_device_dropdown_image(selected_device, is_active, width=header_width)
        option_menu = ctk.CTkLabel(frame, text="", image=dropdown_image, width=header_width, height=37, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, cursor="hand2")
        option_menu._settings_dropdown_image = dropdown_image
        hover_state = {"header": False, "dropdown": False}
        dropdown_menu = tk.Menu(
            option_menu,
            tearoff=0,
            background=DEVICE_ACTIVE_COLOR if is_active else DEVICE_INACTIVE_COLOR,
            foreground="white",
            activebackground=ACTIVE_HOVER_COLOR,
            activeforeground="white",
        )
        for device_name in device_options:
            dropdown_menu.add_command(label=device_name, command=lambda value=device_name: variable.set(value))

        def refresh_visuals():
            current_width = max(120, frame.winfo_width() or header_width)
            active = self.last_state == mode
            header = make_setting_device_header_image(mode, title, active, width=current_width, hover=hover_state["header"])
            dropdown = make_setting_device_dropdown_image(variable.get(), active, width=current_width, hover=hover_state["dropdown"])
            device_button._settings_header_image = header
            option_menu._settings_dropdown_image = dropdown
            device_button.configure(image=header, width=current_width)
            option_menu.configure(image=dropdown, width=current_width)
            dropdown_menu.configure(background=DEVICE_ACTIVE_COLOR if active else DEVICE_INACTIVE_COLOR)

        def set_header_hover(is_hovered):
            hover_state["header"] = is_hovered
            if self.last_state != mode:
                refresh_visuals()

        def set_dropdown_hover(is_hovered):
            hover_state["dropdown"] = is_hovered
            if self.last_state != mode:
                refresh_visuals()

        def open_dropdown(event=None):
            try:
                dropdown_menu.tk_popup(option_menu.winfo_rootx(), option_menu.winfo_rooty() + option_menu.winfo_height())
            except Exception:
                pass
            finally:
                try:
                    dropdown_menu.grab_release()
                except Exception:
                    pass

        device_button.bind("<Enter>", lambda event: set_header_hover(True))
        device_button.bind("<Leave>", lambda event: set_header_hover(False))
        option_menu.bind("<Button-1>", open_dropdown)
        option_menu.bind("<Enter>", lambda event: set_dropdown_hover(True))
        option_menu.bind("<Leave>", lambda event: set_dropdown_hover(False))
        option_menu.pack(fill="x", pady=(1, 0))
        variable.trace_add("write", lambda *_: refresh_visuals())
        frame.bind("<Configure>", lambda event: refresh_visuals())
        self.device_controls[mode] = {"button": device_button, "menu": dropdown_menu, "dropdown": option_menu, "title": title, "variable": variable, "refresh": refresh_visuals}
        return frame

    def create_microphone_settings(self, parent, microphone_options):
        frame = ctk.CTkFrame(parent, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        frame.pack(fill="x", padx=0, pady=(12, 0))

        header_width = SETTINGS_DEVICE_WIDTH
        selected_microphone = self.config_data.get("microphone_name") if self.config_data.get("microphone_name") in microphone_options else microphone_options[0]
        self.mic_var = ctk.StringVar(value=selected_microphone)
        mic_box = ctk.CTkFrame(frame, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, width=header_width, height=77, corner_radius=0)
        mic_box.pack(fill="x")
        mic_box.pack_propagate(False)
        mic_box.grid_propagate(False)

        mic_header_image = make_setting_device_header_image("mic_muted" if self.mic_muted else "mic", "Mic", False, width=header_width)
        mic_header_label = ctk.CTkLabel(
            mic_box,
            text="",
            image=mic_header_image,
            width=header_width,
            height=39,
            fg_color=SETTINGS_PANEL_BG,
            bg_color=SETTINGS_PANEL_BG,
            cursor="hand2",
        )
        mic_header_label._settings_header_image = mic_header_image
        mic_header_label.bind("<Button-1>", lambda event: self.toggle_microphone_mute())
        mic_header_label.pack(fill="x")

        mic_dropdown_image = make_setting_device_dropdown_image(selected_microphone, False, width=header_width, rounded_bottom=False)
        mic_menu_label = ctk.CTkLabel(mic_box, text="", image=mic_dropdown_image, width=header_width, height=SETTINGS_MIC_HEIGHT, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, cursor="hand2")
        mic_menu_label._settings_dropdown_image = mic_dropdown_image
        mic_menu = tk.Menu(
            mic_menu_label,
            tearoff=0,
            background=CONTROL_BG,
            foreground="white",
            activebackground=CONTROL_HOVER,
            activeforeground="white",
        )
        for microphone_name in microphone_options:
            mic_menu.add_command(label=microphone_name, command=lambda value=microphone_name: self.mic_var.set(value))

        def refresh_mic_menu():
            try:
                if not (mic_box.winfo_exists() and mic_header_label.winfo_exists() and mic_menu_label.winfo_exists()):
                    self.settings_mic_header_refresh = None
                    return
                width = max(120, mic_box.winfo_width() or header_width)
                header = make_setting_device_header_image("mic_muted" if self.mic_muted else "mic", "Mic", False, width=width)
                image = make_setting_device_dropdown_image(self.mic_var.get(), False, width=width, rounded_bottom=False)
                mic_header_label._settings_header_image = header
                mic_menu_label._dropdown_image = image
                mic_header_label.configure(image=header, width=width)
                mic_menu_label.configure(image=image, width=width, height=SETTINGS_MIC_HEIGHT)
            except tk.TclError:
                self.settings_mic_header_refresh = None

        def open_mic_menu(event=None):
            try:
                mic_menu.tk_popup(mic_menu_label.winfo_rootx(), mic_menu_label.winfo_rooty() + mic_menu_label.winfo_height())
            finally:
                try:
                    mic_menu.grab_release()
                except Exception:
                    pass

        mic_menu_label.bind("<Button-1>", open_mic_menu)
        mic_menu_label.bind("<Configure>", lambda event: refresh_mic_menu())
        self.mic_var.trace_add("write", lambda *_: refresh_mic_menu())
        mic_menu_label.pack(fill="x", pady=(1, 0))
        self.settings_mic_header_refresh = refresh_mic_menu

        current_hotkey = self.config_data.get("microphone_mute_hotkey", "") or HOTKEY_NONE_LABEL
        self.mic_hotkey_var = ctk.StringVar(value=current_hotkey if current_hotkey in HOTKEY_OPTIONS else HOTKEY_NONE_LABEL)
        hotkey_row = ctk.CTkFrame(frame, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        hotkey_row.pack(fill="x", pady=(0, 0))
        hotkey_width = SETTINGS_DEVICE_WIDTH // 2
        detect_width = SETTINGS_DEVICE_WIDTH - hotkey_width
        hotkey_menu_label = ctk.CTkLabel(hotkey_row, text="", height=SETTINGS_MIC_HEIGHT, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, cursor="hand2")
        hotkey_menu = tk.Menu(
            hotkey_menu_label,
            tearoff=0,
            background=CONTROL_BG,
            foreground="white",
            activebackground=CONTROL_HOVER,
            activeforeground="white",
        )
        for hotkey_name in HOTKEY_OPTIONS:
            hotkey_menu.add_command(label=hotkey_name, command=lambda value=hotkey_name: self.mic_hotkey_var.set(value))

        def refresh_hotkey_menu():
            width = max(80, hotkey_menu_label.winfo_width() or hotkey_width)
            image = make_settings_dropdown_segment_image(
                self.mic_hotkey_var.get(),
                width,
                SETTINGS_MIC_HEIGHT,
                rounded_bottom_left=True,
                separator_right=True,
                stroke_top=False,
                stroke_right=False,
            )
            hotkey_menu_label._dropdown_image = image
            hotkey_menu_label.configure(image=image, width=width, height=SETTINGS_MIC_HEIGHT)

        def open_hotkey_menu(event=None):
            try:
                hotkey_menu.tk_popup(hotkey_menu_label.winfo_rootx(), hotkey_menu_label.winfo_rooty() + hotkey_menu_label.winfo_height())
            finally:
                try:
                    hotkey_menu.grab_release()
                except Exception:
                    pass

        hotkey_menu_label.bind("<Button-1>", open_hotkey_menu)
        hotkey_menu_label.bind("<Configure>", lambda event: refresh_hotkey_menu())
        self.mic_hotkey_var.trace_add("write", lambda *_: refresh_hotkey_menu())
        hotkey_menu_label.pack(side="left", fill="x", expand=True, padx=(0, 0))

        detect_image = make_settings_segment_image(
            "Detect",
            detect_width,
            height=SETTINGS_MIC_HEIGHT,
            rounded_bottom_right=True,
            stroke_top=False,
            stroke_left=False,
        )
        detect_button = ctk.CTkLabel(
            hotkey_row,
            text="",
            image=detect_image,
            width=detect_width,
            height=SETTINGS_MIC_HEIGHT,
            fg_color=SETTINGS_PANEL_BG,
            bg_color=SETTINGS_PANEL_BG,
            cursor="hand2",
        )
        detect_button._segment_image = detect_image
        detect_button.bind("<Button-1>", lambda event: self.open_microphone_hotkey_capture())
        detect_button.pack(side="left")
        self.after(0, refresh_mic_menu)
        self.after(0, refresh_hotkey_menu)
        self.mic_controls = {"variable": self.mic_var, "menu": mic_menu, "refresh": refresh_mic_menu}
        self.create_output_switch_hotkey_settings(parent)

    def create_output_switch_hotkey_settings(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        frame.pack(fill="x", padx=0, pady=(16, 0))

        header_width = SETTINGS_DEVICE_WIDTH
        header_image = make_setting_device_header_image("speaker", "Output Switch Hotkey", False, width=header_width)
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

        self.output_switch_hotkey_var = ctk.StringVar(value=HOTKEY_NONE_LABEL)
        row = ctk.CTkFrame(frame, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        row.pack(fill="x", pady=(1, 0))
        hotkey_width = SETTINGS_DEVICE_WIDTH // 2
        detect_width = SETTINGS_DEVICE_WIDTH - hotkey_width
        hotkey_label = ctk.CTkLabel(row, text="", height=SETTINGS_MIC_HEIGHT, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG, cursor="hand2")
        hotkey_menu = tk.Menu(
            hotkey_label,
            tearoff=0,
            background=CONTROL_BG,
            foreground="white",
            activebackground=CONTROL_HOVER,
            activeforeground="white",
        )
        for hotkey_name in HOTKEY_OPTIONS:
            hotkey_menu.add_command(label=hotkey_name, command=lambda value=hotkey_name: self.output_switch_hotkey_var.set(value))

        def refresh_output_header():
            width = max(120, frame.winfo_width() or header_width)
            image = make_setting_device_header_image("speaker", "Output Switch Hotkey", False, width=width)
            header_label._settings_header_image = image
            header_label.configure(image=image, width=width)

        def refresh_output_hotkey_menu():
            width = max(80, hotkey_label.winfo_width() or hotkey_width)
            image = make_settings_dropdown_segment_image(
                self.output_switch_hotkey_var.get(),
                width,
                SETTINGS_MIC_HEIGHT,
                rounded_bottom_left=True,
                separator_right=True,
                stroke_top=False,
                stroke_right=False,
            )
            hotkey_label._dropdown_image = image
            hotkey_label.configure(image=image, width=width, height=SETTINGS_MIC_HEIGHT)

        def open_output_hotkey_menu(event=None):
            try:
                hotkey_menu.tk_popup(hotkey_label.winfo_rootx(), hotkey_label.winfo_rooty() + hotkey_label.winfo_height())
            finally:
                try:
                    hotkey_menu.grab_release()
                except Exception:
                    pass

        header_label.bind("<Configure>", lambda event: refresh_output_header())
        hotkey_label.bind("<Button-1>", open_output_hotkey_menu)
        hotkey_label.bind("<Configure>", lambda event: refresh_output_hotkey_menu())
        self.output_switch_hotkey_var.trace_add("write", lambda *_: refresh_output_hotkey_menu())
        hotkey_label.pack(side="left", fill="x", expand=True, padx=(0, 0))

        detect_image = make_settings_segment_image(
            "Detect",
            detect_width,
            height=SETTINGS_MIC_HEIGHT,
            rounded_bottom_right=True,
            stroke_top=False,
            stroke_left=False,
        )
        detect_button = ctk.CTkLabel(
            row,
            text="",
            image=detect_image,
            width=detect_width,
            height=SETTINGS_MIC_HEIGHT,
            fg_color=SETTINGS_PANEL_BG,
            bg_color=SETTINGS_PANEL_BG,
        )
        detect_button._segment_image = detect_image
        detect_button.pack(side="left")
        self.after(0, refresh_output_header)
        self.after(0, refresh_output_hotkey_menu)

    def open_microphone_hotkey_capture(self):
        capture = ctk.CTkToplevel(self)
        capture.title("Detect Hotkey")
        capture.geometry("320x140+800+340")
        capture.transient(self)
        capture.grab_set()
        capture.configure(fg_color="#171717")

        ctk.CTkLabel(capture, text="Press a key", font=("Segoe UI", 16, "bold"), text_color="white").pack(pady=(24, 6))
        ctk.CTkLabel(capture, text="F13-F24 can be selected from the dropdown.", font=("Segoe UI", 11), text_color="#B8B8B8").pack()

        def capture_key(event):
            key_name = self.normalize_hotkey_name(event.keysym)
            if key_name in HOTKEY_VK:
                self.mic_hotkey_var.set(key_name)
                capture.destroy()

        capture.bind("<KeyPress>", capture_key)
        capture.after(100, capture.focus_force)

    def refresh_program_lists(self):
        if not hasattr(self, "program_list_frame") or not self.program_list_frame.winfo_exists():
            return
        self.list_drop_targets = {}
        self.program_list_scrolls = {}
        self.program_row_widgets = {}
        for widget in self.program_list_frame.winfo_children():
            widget.destroy()
        self.program_list_frame.grid_columnconfigure(0, weight=1, uniform="program_list")
        self.program_list_frame.grid_columnconfigure(1, weight=1, uniform="program_list")
        self.program_list_frame.grid_rowconfigure(0, weight=1)
        self.create_list_ui(self.program_list_frame, "Ask Before Change", "ask_list", row=0, column=0, padx=(0, 6))
        self.create_list_ui(self.program_list_frame, "Auto Change", "auto_list", row=0, column=1, padx=(6, 0))

    def create_list_ui(self, parent, title, key, row=None, column=None, padx=0):
        section = ctk.CTkFrame(parent, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        if row is None or column is None:
            section.pack(fill="both", expand=True)
        else:
            section.grid(row=row, column=column, sticky="nsew", padx=padx)
        section.grid_rowconfigure(1, weight=1)
        section.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(section, fg_color="transparent", bg_color=SETTINGS_PANEL_BG, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=(4, 2))
        ctk.CTkFrame(header, fg_color="#636363", width=2, height=15, corner_radius=4).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 14), text_color="white", fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_PANEL_BG).pack(side="left")

        scroll_shell = ctk.CTkFrame(section, fg_color=SURFACE_BG, bg_color=SETTINGS_PANEL_BG, border_width=1, border_color="#080808", corner_radius=SETTINGS_PANEL_RADIUS)
        scroll_shell.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))
        scroll_shell.pack_propagate(False)
        scroll = ctk.CTkScrollableFrame(scroll_shell, fg_color=SURFACE_BG, bg_color=SURFACE_BG, border_width=0, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=4, pady=4)
        self.normalize_scrollable_background(scroll, SURFACE_BG)
        self.program_list_scrolls[key] = scroll
        self.list_drop_targets[key] = self.get_scroll_drop_widgets(scroll)

        programs = self.config_data[key]
        if not programs:
            placeholder = ctk.CTkLabel(scroll, text="No programs yet", text_color="#777777", height=40)
            placeholder._empty_placeholder = True
            placeholder.pack(fill="x")
        else:
            for program in programs:
                self.create_program_row(scroll, key, program)

        ctk.CTkButton(section, text="+  Add Program", height=39, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=13, font=("Segoe UI", 14), command=lambda: self.open_add_program_menu(key)).grid(row=2, column=0, sticky="ew", padx=0, pady=(0, 6))

    def create_program_row(self, parent, key, program):
        item = ctk.CTkFrame(parent, fg_color=SETTINGS_ROW_BG, corner_radius=7, height=51)
        item.pack(fill="x", pady=2, padx=4)
        item.pack_propagate(False)
        self.program_row_widgets[(key, self.program_key(program))] = item

        handle = ctk.CTkLabel(item, text="", image=self.icons["handle"], width=34, height=51, cursor="hand2")
        handle.pack(side="left", padx=(4, 0), pady=0)
        handle.bind("<ButtonPress-1>", lambda event, k=key, p=program: self.start_program_drag(event, k, p))
        handle.bind("<B1-Motion>", self.update_program_drag)
        handle.bind("<ButtonRelease-1>", self.finish_program_drag)

        icon_source = self.get_program_icon_source(program)
        icon = self.get_cached_program_icon_if_ready(icon_source, size=PROGRAM_ICON_SIZE)
        icon_label = ctk.CTkLabel(item, text="" if icon else "APP", image=icon, width=38, height=38, fg_color="#272A2F", corner_radius=4, font=("Segoe UI", 9, "bold"))
        icon_label.pack(side="left", padx=(8, 8), pady=6)
        if not icon and icon_source:
            self.after(20, lambda label=icon_label, source=icon_source: self.load_program_icon_into_label(label, source, PROGRAM_ICON_SIZE))

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

        ctk.CTkButton(item, text="", image=self.icons["trash"], width=38, height=39, fg_color="#991B1B", hover_color="#B91C1C", corner_radius=4, command=lambda p=program, k=key: self.remove_program(k, p)).pack(side="right", padx=(3, 6))
        self.create_program_target_button(item, key, program, "headset").pack(side="right", padx=2)
        self.create_program_target_button(item, key, program, "speaker").pack(side="right", padx=2)
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
        self.get_cached_program_icon(source, size=PROGRAM_ICON_SIZE)
        self.after(80, self.preload_next_program_icon)

    def program_icon_cache_key(self, path, size=PROGRAM_ICON_SIZE, source_size=None, corner_radius=0):
        return (path or "", size, source_size or size, corner_radius)

    def get_cached_program_icon_if_ready(self, path, size=PROGRAM_ICON_SIZE, source_size=None, corner_radius=0):
        return self.exe_icon_cache.get(self.program_icon_cache_key(path, size, source_size, corner_radius))

    def load_program_icon_into_label(self, label, path, size=PROGRAM_ICON_SIZE):
        if not label.winfo_exists():
            return
        icon = self.get_cached_program_icon(path, size=size)
        if label.winfo_exists() and icon:
            label.configure(image=icon, text="")

    def get_cached_program_icon(self, path, size=PROGRAM_ICON_SIZE, source_size=None, corner_radius=0):
        cache_key = self.program_icon_cache_key(path, size, source_size, corner_radius)
        if cache_key not in self.exe_icon_cache:
            extension = os.path.splitext(path or "")[1].lower()
            if extension in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico"):
                icon = get_icon_from_image(path, size=size, source_size=source_size, corner_radius=corner_radius)
            else:
                icon = get_icon_from_exe(path, size=size, source_size=source_size, corner_radius=corner_radius)
            self.exe_icon_cache[cache_key] = icon
        return self.exe_icon_cache[cache_key]

    def update_detect_ui_with_program_icon(self, program, icon_source):
        icon = self.get_cached_program_icon(
            icon_source,
            size=MINI_DETECTED_ICON_SIZE,
            source_size=MINI_DETECTED_ICON_SOURCE_SIZE,
            corner_radius=MINI_DETECTED_ICON_CORNER_RADIUS,
        ) if icon_source else None
        self.update_detect_ui(program.get("name", "Unknown"), icon)

    def start_program_drag(self, event, source_key, program):
        self.drag_data = {
            "source_key": source_key,
            "program": program,
            "start_x": event.x_root,
            "start_y": event.y_root,
        }
        row = self.program_row_widgets.get((source_key, self.program_key(program)))
        if row and row.winfo_exists():
            self.drag_data["row"] = row
            self.set_program_row_dragging(row, True)
        self.show_drag_preview(program, event.x_root, event.y_root)

    def show_drag_preview(self, program, x, y):
        self.destroy_drag_preview()
        preview = ctk.CTkToplevel(self)
        preview.overrideredirect(True)
        preview.attributes("-topmost", True)
        preview.configure(fg_color="#202020")
        ctk.CTkLabel(
            preview,
            text=program.get("name", "Program"),
            font=("Segoe UI", 12, "bold"),
            text_color="white",
        ).pack(padx=12, pady=6)
        self.drag_preview = preview
        self.move_drag_preview(x, y)

    def set_program_row_dragging(self, row, dragging):
        try:
            row.configure(fg_color="#252525" if dragging else SETTINGS_ROW_BG)
        except Exception:
            pass

    def update_program_drag(self, event):
        if not self.drag_data:
            return
        self.move_drag_preview(event.x_root, event.y_root)

    def move_drag_preview(self, x, y):
        if hasattr(self, "drag_preview") and self.drag_preview.winfo_exists():
            self.drag_preview.geometry(f"+{x + 14}+{y + 14}")

    def destroy_drag_preview(self):
        if hasattr(self, "drag_preview") and self.drag_preview.winfo_exists():
            self.drag_preview.destroy()

    def finish_program_drag(self, event):
        if not self.drag_data:
            return

        source_key = self.drag_data["source_key"]
        self.update_idletasks()
        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        target_key = self.get_drop_target_key(x, y) or self.get_drop_target_key(event.x_root, event.y_root)
        program = self.drag_data["program"]
        row = self.drag_data.get("row")
        self.drag_data = None
        self.destroy_drag_preview()
        if row and row.winfo_exists():
            self.set_program_row_dragging(row, False)

        if not target_key or target_key == source_key:
            return
        self.move_program_between_lists(source_key, target_key, program)

    def get_scroll_drop_widgets(self, scroll):
        widgets = [scroll]
        for attr in ("_parent_canvas", "_parent_frame", "_scrollbar"):
            widget = getattr(scroll, attr, None)
            if widget is not None:
                widgets.append(widget)
        return widgets

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

    def get_drop_target_key(self, x, y):
        for key, widgets in self.list_drop_targets.items():
            for widget in widgets:
                if self.point_inside_widget(widget, x, y):
                    return key
        return None

    def point_inside_widget(self, widget, x, y):
        try:
            if not widget.winfo_exists():
                return False
            left = widget.winfo_rootx()
            top = widget.winfo_rooty()
            right = left + widget.winfo_width()
            bottom = top + widget.winfo_height()
            return left <= x <= right and top <= y <= bottom
        except Exception:
            return False

    def program_key(self, program):
        return program.get("match_type"), program.get("value")

    def find_program_index(self, key, program):
        target = self.program_key(program)
        for index, item in enumerate(self.config_data[key]):
            if self.program_key(item) == target:
                return index
        return None

    def move_program_between_lists(self, source_key, target_key, program):
        source_index = self.find_program_index(source_key, program)
        if source_index is None:
            return
        if self.program_exists(target_key, program):
            messagebox.showinfo("Auto Audio", "This program rule already exists in the target list.")
            return
        moved_program = self.config_data[source_key].pop(source_index)
        self.config_data[target_key].append(moved_program)
        self.save_config()
        if not self.move_program_row_widget(source_key, target_key, moved_program):
            self.refresh_program_lists()
        self.update_idletasks()

    def move_program_row_widget(self, source_key, target_key, program):
        row_key = self.program_key(program)
        row = self.program_row_widgets.pop((source_key, row_key), None)
        target_scroll = getattr(self, "program_list_scrolls", {}).get(target_key)
        if not target_scroll:
            return False
        try:
            if not target_scroll.winfo_exists():
                return False
            if row and row.winfo_exists():
                row.destroy()
            self.create_program_row(target_scroll, target_key, program)
            self.update_empty_list_placeholders_after_move(source_key, target_key)
            return True
        except Exception:
            return False

    def update_empty_list_placeholders_after_move(self, source_key, target_key):
        for key in (source_key, target_key):
            scroll = getattr(self, "program_list_scrolls", {}).get(key)
            if not scroll or not scroll.winfo_exists():
                continue
            for child in scroll.winfo_children():
                if getattr(child, "_empty_placeholder", False):
                    child.destroy()
            if not self.config_data[key]:
                placeholder = ctk.CTkLabel(scroll, text="No programs yet", text_color="#777777", height=40)
                placeholder._empty_placeholder = True
                placeholder.pack(fill="x")

    def target_color(self, program, mode):
        return ACTIVE_COLOR if program.get("target_audio") == mode else CONTROL_BG

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

    def switch_mode(self, target, focus=True, animate_mini=None):
        self.cancel_mini_animation()
        was_visible = self.winfo_viewable()
        was_mini = self.is_mini
        should_animate_mini = target == "mini" and (animate_mini if animate_mini is not None else not (was_visible and was_mini))
        logging.info("switch_mode target=%s was_visible=%s was_mini=%s focus=%s animate_mini=%s should_animate=%s", target, was_visible, was_mini, focus, animate_mini, should_animate_mini)

        if target == "settings" and was_visible and was_mini:
            self.animate_mini_out(on_complete=lambda: self.switch_mode("settings", focus=focus))
            return

        if target == "settings" and was_visible:
            self.withdraw()
        elif should_animate_mini and was_visible:
            self.withdraw()
        self.set_ui_mode(target)
        self.draw_ui()
        self.update_idletasks()
        if target == "settings" and not self.config_data.get("settings_geometry"):
            self.fit_settings_geometry_to_content()
        if should_animate_mini:
            self.animate_mini_in()
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
        return "Headset" if state == "headset" else "Speaker"

    def update_mini_buttons_ui(self, state):
        if self.audio_switching:
            self.show_audio_switching_ui(self.audio_switch_target, redraw=False)
            return
        self.clear_audio_switching_ui(redraw=False)
        if hasattr(self, "speaker_btn") and self.speaker_btn.winfo_exists():
            self.speaker_btn.configure(image=self.mini_button_images["speaker_active" if state == "speaker" else "speaker_inactive"])
            self.headset_btn.configure(image=self.mini_button_images["headset_active" if state == "headset" else "headset_inactive"])
            self.speaker_btn.bind("<Enter>", lambda event: self.set_mini_device_button_hover("speaker", True))
            self.speaker_btn.bind("<Leave>", lambda event: self.set_mini_device_button_hover("speaker", False))
            self.headset_btn.bind("<Enter>", lambda event: self.set_mini_device_button_hover("headset", True))
            self.headset_btn.bind("<Leave>", lambda event: self.set_mini_device_button_hover("headset", False))
        self.update_microphone_button_ui()
        self.update_device_controls_ui(state)

    def set_mini_device_button_hover(self, mode, is_hovered):
        if self.audio_switching or self.last_state == mode:
            return
        button = getattr(self, f"{mode}_btn", None)
        if button and button.winfo_exists():
            image_key = f"{mode}_hover" if is_hovered else f"{mode}_inactive"
            button.configure(image=self.mini_button_images[image_key])

    def set_mic_button_hover(self, is_hovered):
        if self.mic_muted:
            return
        if hasattr(self, "mic_btn") and self.mic_btn.winfo_exists():
            self.mic_btn.configure(image=self.mini_button_images["mic_hover" if is_hovered else "mic"])

    def show_audio_switching_ui(self, target=None, redraw=True):
        self.audio_switching = True
        self.audio_switch_target = target
        if redraw:
            self.update_mini_detect_canvas("Changing audio output...", self.icons.get("speaker" if target == "speaker" else "headset"))
        if not hasattr(self, "mini_button_frame") or not self.mini_button_frame.winfo_exists():
            return
        for button_name in ("speaker_btn", "headset_btn"):
            button = getattr(self, button_name, None)
            if button and button.winfo_exists():
                button.pack_forget()
        label = getattr(self, "audio_switching_btn", None)
        if not label or not label.winfo_exists():
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
        if label and label.winfo_exists() and label.winfo_ismapped():
            label.pack_forget()
        if hasattr(self, "speaker_btn") and self.speaker_btn.winfo_exists() and not self.speaker_btn.winfo_ismapped():
            self.speaker_btn.pack(side="left", padx=(0, MINI_DEVICE_BUTTON_GAP))
        if hasattr(self, "headset_btn") and self.headset_btn.winfo_exists() and not self.headset_btn.winfo_ismapped():
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

    def show_audio_change_notification(self, target, program_name=None, icon=None, animate=True, duration_seconds=NOTIFICATION_SECONDS):
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
        current_y = self.winfo_y() if was_mini_visible else None
        self.switch_mode("mini", focus=False, animate_mini=not was_mini_visible)
        if was_mini_visible and current_y is not None:
            width, height, x, _ = self.get_mini_geometry_parts()
            self.geometry(f"{width}x{height}+{x}+{current_y}")
        self.update_mini_buttons_ui(target)

        fallback_icon = self.icons.get("no_app") if program_name == "No Program Detected" else self.icons["headset"] if target == "headset" else self.icons["speaker"]
        self.update_mini_detect_canvas("Audio output changed", icon or fallback_icon)
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

    def show_microphone_change_notification(self):
        if self.ask_active:
            logging.info("microphone notification skipped because ask prompt is active muted=%s", self.mic_muted)
            return
        if self.notification_after_id:
            try:
                self.after_cancel(self.notification_after_id)
            except Exception:
                pass
            self.notification_after_id = None

        self.notification_active = True
        self.pending_prompt_key = None
        self.mini_pinned_by_user = False
        icon = self.icons["mic_muted" if self.mic_muted else "mic"]
        text = "Microphone muted" if self.mic_muted else "Microphone unmuted"
        self.current_detected_icon = icon
        was_mini_visible = self.is_mini and self.winfo_viewable()
        logging.info("microphone notification show muted=%s was_mini_visible=%s", self.mic_muted, was_mini_visible)
        self.switch_mode("mini", focus=False, animate_mini=not was_mini_visible)
        self.update_mini_buttons_ui(self.last_state)
        self.update_mini_detect_canvas(text, icon)
        self.notification_after_id = self.after(MICROPHONE_NOTIFICATION_SECONDS * 1000, self.finish_audio_change_notification)

    def manual_set_audio(self, mode):
        logging.info("manual audio requested mode=%s last_state=%s switching=%s", mode, self.last_state, self.audio_switching)
        self.start_audio_switch(mode, on_success=lambda: self.finish_manual_audio_switch(mode))

    def finish_manual_audio_switch(self, mode):
        detected = self.find_matching_program()
        self.last_state = mode
        self.manual_override = True
        self.manual_override_during_detection = detected is not None
        if detected and detected[0] == "ask_list" and mode == "headset":
            self.ask_restore_program = detected[1]
            self.ask_restore_prompt_key = None
        self.update_mini_buttons_ui(mode)

    def start_audio_switch(self, mode, on_success=None, on_failure=None):
        if self.audio_switching:
            logging.info("audio switch ignored because already switching requested=%s current_target=%s", mode, self.audio_switch_target)
            return
        logging.info("audio switch start mode=%s is_mini=%s visible=%s", mode, self.is_mini, self.winfo_viewable())
        if self.is_mini and not self.winfo_viewable():
            self.switch_mode("mini", focus=False, animate_mini=True)
        if self.is_mini:
            self.show_audio_switching_ui(mode)
        else:
            self.audio_switching = True
            self.audio_switch_target = mode

        def worker():
            changed = self.set_audio(mode)
            self.after(0, lambda: self.finish_audio_switch(mode, changed, on_success, on_failure))

        threading.Thread(target=worker, daemon=True).start()

    def finish_audio_switch(self, mode, changed, on_success=None, on_failure=None):
        logging.info("audio switch finish mode=%s changed=%s last_state_before=%s", mode, changed, self.last_state)
        self.audio_switching = False
        self.audio_switch_target = None
        self.clear_audio_switching_ui(redraw=False)
        if changed:
            self.last_state = mode
            self.current_audio_mode_cache = mode
            self.last_audio_sync_time = time.monotonic()
            self.update_mini_buttons_ui(mode)
            if on_success:
                on_success()
        else:
            self.update_mini_buttons_ui(self.last_state)
            if on_failure:
                on_failure()

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
            self.show_audio_change_notification(target, program_name, icon, duration_seconds=AUTO_CHANGE_NOTIFICATION_SECONDS)
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
            self.show_audio_change_notification("speaker", "No Program Detected", None, duration_seconds=AUTO_CHANGE_NOTIFICATION_SECONDS)
        else:
            self.update_mini_buttons_ui(self.last_state)

    def set_audio(self, mode):
        target = self.config_data["headset_name"] if mode == "headset" else self.config_data["speaker_name"]
        with self.device_cache_lock:
            device_id = self.audio_device_ids.get(target)
            known_devices = set(self.audio_device_names)

        logging.info("set_audio begin mode=%s target=%s device_id_known=%s known_devices=%s", mode, target, bool(device_id), len(known_devices))
        if not target or target == "No audio device found":
            print(f"audio switch failed: no valid {mode} output device selected")
            logging.warning("set_audio failed invalid target mode=%s target=%s", mode, target)
            return False
        if target not in known_devices or not device_id:
            logging.info("set_audio refreshing device cache mode=%s target_in_known=%s device_id_known=%s", mode, target in known_devices, bool(device_id))
            self.refresh_audio_device_cache(include_input=False)
            self.sync_audio_config_with_devices(save_changes=True)
            with self.device_cache_lock:
                device_id = self.audio_device_ids.get(target)
                known_devices = set(self.audio_device_names)
            if target not in known_devices or not device_id:
                print(f"audio switch failed: no valid {mode} output device selected")
                logging.warning("set_audio failed after refresh mode=%s target=%s known_devices=%s device_id_known=%s", mode, target, len(known_devices), bool(device_id))
                return False

        if self.set_audio_with_pycaw(target, device_id):
            if self.wait_for_audio_mode(mode):
                logging.info("set_audio success via pycaw mode=%s target=%s", mode, target)
                return True
            print(f"pycaw reported success, but {mode} output was not confirmed")
            logging.warning("set_audio pycaw unconfirmed mode=%s target=%s current=%s", mode, target, self.get_current_output_name())

        if self.set_audio_with_nircmd(target):
            confirmed = self.wait_for_audio_mode(mode)
            logging.info("set_audio nircmd result mode=%s target=%s confirmed=%s", mode, target, confirmed)
            return confirmed
        logging.warning("set_audio failed all methods mode=%s target=%s", mode, target)
        return False

    def audio_names_equal(self, left, right):
        return bool(left and right and left.strip().casefold() == right.strip().casefold())

    def get_current_output_name(self):
        try:
            import warnings

            warnings.filterwarnings("ignore")
            from pycaw.pycaw import AudioUtilities

            device = AudioUtilities.GetSpeakers()
            return getattr(device, "FriendlyName", None) or getattr(device, "friendly_name", None) or ""
        except Exception:
            return ""

    def get_current_audio_mode(self):
        current_name = self.get_current_output_name()
        if not current_name:
            return None
        if self.audio_names_equal(current_name, self.config_data.get("speaker_name", "")):
            return "speaker"
        if self.audio_names_equal(current_name, self.config_data.get("headset_name", "")):
            return "headset"
        return None

    def get_cached_current_audio_mode(self, force=False):
        now = time.monotonic()
        if not force and self.current_audio_mode_cache and now - self.last_audio_sync_time < CURRENT_AUDIO_SYNC_INTERVAL_SECONDS:
            return self.current_audio_mode_cache
        current_mode = self.get_current_audio_mode()
        self.last_audio_sync_time = now
        if current_mode:
            self.current_audio_mode_cache = current_mode
        return current_mode

    def wait_for_audio_mode(self, mode):
        deadline = time.monotonic() + AUDIO_SWITCH_VERIFY_TIMEOUT_SECONDS
        observed_known_mode = False
        while time.monotonic() < deadline:
            current_mode = self.get_current_audio_mode()
            if current_mode == mode:
                self.current_audio_mode_cache = mode
                self.last_audio_sync_time = time.monotonic()
                return True
            if current_mode is not None:
                observed_known_mode = True
            time.sleep(AUDIO_SWITCH_VERIFY_INTERVAL_SECONDS)
        return not observed_known_mode

    def sync_last_state_with_current_output(self, force=False):
        current_mode = self.get_cached_current_audio_mode(force=force)
        if current_mode and current_mode != self.last_state:
            self.last_state = current_mode
            self.after(0, lambda state=current_mode: self.update_mini_buttons_ui(state))
        return current_mode

    def force_startup_speaker_output(self):
        if not self.config_data.get("speaker_name"):
            return
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

    def get_microphone_volume(self, name=None):
        try:
            import comtypes
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            if not name or name == DEFAULT_MICROPHONE_LABEL:
                device = AudioUtilities.GetMicrophone()
                if not device:
                    return None
                interface = device.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
                return interface.QueryInterface(IAudioEndpointVolume)

            for device in AudioUtilities.GetAllDevices():
                try:
                    if AudioUtilities.GetEndpointDataFlow(device.id) != "eCapture":
                        continue
                    friendly_name = getattr(device, "FriendlyName", None) or getattr(device, "friendly_name", None)
                    if friendly_name == name:
                        return device.EndpointVolume
                except Exception:
                    continue
        except Exception as exc:
            print(f"microphone lookup failed: {exc}")
        return None

    def get_selected_microphone_name(self):
        return self.config_data.get("microphone_name") or DEFAULT_MICROPHONE_LABEL

    def get_microphone_muted(self):
        volume = self.get_microphone_volume(self.get_selected_microphone_name())
        if volume is None:
            return None
        try:
            return bool(volume.GetMute())
        except Exception as exc:
            print(f"microphone mute read failed: {exc}")
            return None

    def set_microphone_muted(self, muted):
        volume = self.get_microphone_volume(self.get_selected_microphone_name())
        if volume is None:
            return False
        try:
            volume.SetMute(1 if muted else 0, None)
            self.mic_muted = bool(muted)
            self.update_microphone_button_ui()
            return True
        except Exception as exc:
            print(f"microphone mute switch failed: {exc}")
            return False

    def toggle_microphone_mute(self):
        hotkey = self.config_data.get("microphone_mute_hotkey", "")
        if hotkey:
            if self.send_hotkey(hotkey):
                self.mic_muted = not self.mic_muted
                self.update_microphone_button_ui()
                self.show_microphone_change_notification()
                logging.info("microphone toggled via hotkey muted=%s hotkey=%s", self.mic_muted, hotkey)
            else:
                logging.warning("microphone hotkey send failed hotkey=%s", hotkey)
            return

        muted = self.get_microphone_muted()
        if muted is None:
            logging.warning("microphone toggle failed: current mute state unavailable")
            return
        if self.set_microphone_muted(not muted):
            self.show_microphone_change_notification()
            logging.info("microphone toggled via endpoint muted=%s", self.mic_muted)

    def refresh_microphone_mute_ui(self):
        if self.config_data.get("microphone_mute_hotkey", ""):
            self.update_microphone_button_ui()
            return

        muted = self.get_microphone_muted()
        if muted is not None:
            self.mic_muted = muted
        self.update_microphone_button_ui()

    def update_microphone_button_ui(self):
        muted = bool(self.mic_muted)
        if hasattr(self, "mic_btn") and self.mic_btn.winfo_exists():
            self.mic_btn.configure(
                image=self.mini_button_images["mic_muted"] if muted else self.mini_button_images["mic"]
            )
        refresh_settings_mic = getattr(self, "settings_mic_header_refresh", None)
        if refresh_settings_mic:
            try:
                refresh_settings_mic()
            except tk.TclError:
                self.settings_mic_header_refresh = None

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
        self.user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        self.user32.SendInput.restype = wintypes.UINT
        self.user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
        self.user32.MapVirtualKeyW.restype = wintypes.UINT

        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel32.GetModuleHandleW.restype = HMODULE

    def send_hotkey(self, hotkey):
        hotkey = self.normalize_hotkey_name(hotkey)
        vk = HOTKEY_VK.get(hotkey)
        if not vk:
            return False
        try:
            self.configure_keyboard_api()
            scan_code = self.user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
            inputs = (INPUT * 2)()
            inputs[0].type = INPUT_KEYBOARD
            inputs[0].union.ki = KEYBDINPUT(vk, scan_code, 0, 0, 0)
            inputs[1].type = INPUT_KEYBOARD
            inputs[1].union.ki = KEYBDINPUT(vk, scan_code, KEYEVENTF_KEYUP, 0, 0)

            sent = self.user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
            if sent != 2:
                print(f"hotkey send failed: SendInput sent {sent}/2, error {ctypes.get_last_error()}")
                return False
            return True
        except Exception as exc:
            print(f"hotkey send failed: {exc}")
            return False

    def install_keyboard_hook(self):
        if self.keyboard_hook:
            return

        self.configure_keyboard_api()

        def keyboard_proc(n_code, w_param, l_param):
            try:
                if n_code == 0:
                    event = int(w_param)
                    data = ctypes.cast(ctypes.c_void_p(l_param), ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    configured_hotkey = self.config_data.get("microphone_mute_hotkey", "")
                    configured_vk = HOTKEY_VK.get(configured_hotkey)

                    if configured_vk and data.vkCode == configured_vk:
                        if event in (WM_KEYDOWN, WM_SYSKEYDOWN):
                            if not self.microphone_hotkey_down and not (data.flags & LLKHF_INJECTED):
                                self.microphone_hotkey_down = True
                                self.keyboard_event_queue.put("microphone_hotkey")
                        elif event in (WM_KEYUP, WM_SYSKEYUP):
                            self.microphone_hotkey_down = False
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
        has_hotkey = bool(self.config_data.get("microphone_mute_hotkey", ""))
        if has_hotkey:
            self.install_keyboard_hook()
            self.start_keyboard_event_polling()
            return

        self.uninstall_keyboard_hook()
        self.microphone_hotkey_down = False
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
        while True:
            try:
                event_name = self.keyboard_event_queue.get_nowait()
            except queue.Empty:
                break

            if event_name == "microphone_hotkey":
                self.handle_microphone_hotkey_pressed()

        if self.is_running and self.keyboard_hook:
            self.keyboard_event_after_id = self.after(50, self.process_keyboard_events)

    def uninstall_keyboard_hook(self):
        if self.keyboard_hook:
            try:
                self.configure_keyboard_api()
                self.user32.UnhookWindowsHookEx(self.keyboard_hook)
            except Exception:
                pass
            self.keyboard_hook = None
            self.keyboard_hook_proc = None

    def handle_microphone_hotkey_pressed(self):
        if not self.config_data.get("microphone_mute_hotkey", ""):
            return
        self.mic_muted = not self.mic_muted
        self.update_microphone_button_ui()
        self.show_microphone_change_notification()
        logging.info("microphone toggled by keyboard hook muted=%s", self.mic_muted)

    def set_audio_with_pycaw(self, target, device_id=None):
        try:
            import warnings

            warnings.filterwarnings("ignore")
            from pycaw.pycaw import AudioUtilities
            from pycaw.constants import ERole

            if device_id:
                AudioUtilities.SetDefaultDevice(device_id, roles=[ERole.eMultimedia, ERole.eConsole, ERole.eCommunications])
                return True

            for device in AudioUtilities.GetAllDevices():
                if AudioUtilities.GetEndpointDataFlow(device.id) != "eRender":
                    continue
                name = getattr(device, "FriendlyName", None) or getattr(device, "friendly_name", None)
                if name == target:
                    AudioUtilities.SetDefaultDevice(device.id, roles=[ERole.eMultimedia, ERole.eConsole, ERole.eCommunications])
                    return True
        except Exception as exc:
            print(f"pycaw audio switch failed: {exc}")
            logging.exception("pycaw audio switch failed target=%s", target)
        return False

    def set_audio_with_nircmd(self, target):
        nircmd_path = next(
            (
                path
                for path in (
                    os.path.join(APP_DIR, "nircmd.exe"),
                    os.path.join(RESOURCE_DIR, "nircmd.exe"),
                    os.path.join(RESOURCE_DIR, "_internal", "nircmd.exe"),
                )
                if os.path.exists(path)
            ),
            "",
        )
        if not os.path.exists(nircmd_path):
            logging.warning("nircmd missing target=%s", target)
            return False
        try:
            processes = []
            for role in ("0", "1", "2"):
                processes.append(subprocess.Popen(
                    [nircmd_path, "setdefaultsounddevice", target, role],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                ))
            result = all(process.wait() == 0 for process in processes)
            logging.info("nircmd switch target=%s path=%s result=%s", target, nircmd_path, result)
            return result
        except Exception as exc:
            print(f"nircmd audio switch failed: {exc}")
            logging.exception("nircmd audio switch failed target=%s path=%s", target, nircmd_path)
            return False

    def save_settings(self):
        self.remember_settings_geometry()
        if hasattr(self, "sp_var"):
            speaker_name = self.sp_var.get()
            if speaker_name in self.audio_device_names:
                self.config_data["speaker_name"] = speaker_name
        if hasattr(self, "hs_var"):
            headset_name = self.hs_var.get()
            if headset_name in self.audio_device_names:
                self.config_data["headset_name"] = headset_name
        if hasattr(self, "mic_var"):
            self.config_data["microphone_name"] = self.mic_var.get()
        if hasattr(self, "mic_hotkey_var"):
            hotkey = self.mic_hotkey_var.get()
            self.config_data["microphone_mute_hotkey"] = "" if hotkey == HOTKEY_NONE_LABEL else hotkey
            self.microphone_hotkey_down = False
            self.sync_keyboard_hook_state()
        if hasattr(self, "startup_var"):
            self.config_data["start_with_windows"] = bool(self.startup_var.get())
            self.set_startup_enabled(self.config_data["start_with_windows"])
        if hasattr(self, "ask_timeout_var"):
            ask_timeout = self.parse_ask_timeout_seconds(self.ask_timeout_var.get())
            self.config_data["ask_timeout_seconds"] = ask_timeout
            self.ask_timeout_var.set(self.format_ask_timeout_seconds(ask_timeout))
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
        self.prepare_popup(menu, "Add Program", 418, 180, grab=True)

        ctk.CTkLabel(menu, text="Add Program", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", padx=14, pady=(12, 6))
        ctk.CTkButton(menu, text="+  Add .exe file", height=38, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=4, font=("Segoe UI", 18), command=lambda: self.choose_add_exe(key, menu)).pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkButton(menu, text="+  Add Running Program", height=38, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=4, font=("Segoe UI", 18), command=lambda: self.choose_running_program(key, menu)).pack(fill="x", padx=14)

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

    def add_active_window_program(self, key):
        hwnd = self.find_external_foreground_window()
        if not hwnd:
            messagebox.showinfo("Auto Audio", "No active window found.")
            return

        title = win32gui.GetWindowText(hwnd).strip()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process = psutil.Process(pid)
            name = process.name()
            path = process.exe()
        except Exception:
            name = title or "Active Window"
            path = ""

        display_name = title or name
        match_value = title if title else name
        match_type = "window_title" if title else "process_name"
        self.add_program(
            key,
            {
                "name": display_name,
                "match_type": match_type,
                "value": match_value,
                "path": path,
                "target_audio": "headset",
            },
        )

    def find_external_foreground_window(self):
        own_pid = os.getpid()
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and self.is_external_window(hwnd, own_pid):
            return hwnd

        windows = []

        def collect(candidate, _):
            if self.is_external_window(candidate, own_pid):
                windows.append(candidate)

        try:
            win32gui.EnumWindows(collect, None)
        except Exception:
            pass
        return windows[0] if windows else None

    def is_external_window(self, hwnd, own_pid):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return False
            if not win32gui.GetWindowText(hwnd).strip():
                return False
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return pid != own_pid
        except Exception:
            return False

    def open_running_program_picker(self, key):
        picker = ctk.CTkToplevel(self)
        picker.title("Add Running Program")
        picker.geometry("680x560+620+160")
        picker.transient(self)
        picker.configure(fg_color=WINDOW_BG)

        header = ctk.CTkFrame(picker, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(18, 8))
        ctk.CTkLabel(header, text="Running Programs", font=("Segoe UI", 18, "bold")).pack(side="left")

        sort_frame = ctk.CTkFrame(header, fg_color="transparent")
        sort_frame.pack(side="right")
        sort_buttons = {}
        sort_buttons["name"] = ctk.CTkButton(sort_frame, text="A-Z", width=58, height=28, corner_radius=8)
        sort_buttons["name"].pack(side="left", padx=(0, 6))
        sort_buttons["resource"] = ctk.CTkButton(sort_frame, text="Resource", width=86, height=28, corner_radius=8)
        sort_buttons["resource"].pack(side="left", padx=(0, 6))
        sort_buttons["recent"] = ctk.CTkButton(sort_frame, text="Recent", width=74, height=28, corner_radius=8)
        sort_buttons["recent"].pack(side="left")

        scroll = ctk.CTkScrollableFrame(picker, fg_color=SURFACE_BG, corner_radius=6)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        processes = self.list_running_programs()
        sort_buttons["name"].configure(command=lambda: self.render_running_programs(scroll, processes, key, picker, "name", sort_buttons))
        sort_buttons["resource"].configure(command=lambda: self.render_running_programs(scroll, processes, key, picker, "resource", sort_buttons))
        sort_buttons["recent"].configure(command=lambda: self.render_running_programs(scroll, processes, key, picker, "recent", sort_buttons))
        self.render_running_programs(scroll, processes, key, picker, "name", sort_buttons)

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
            processes = sorted(processes, key=lambda item: item.get("create_time", 0), reverse=True)
        else:
            processes = sorted(processes, key=lambda item: item["name"].lower())

        for program in processes:
            row = ctk.CTkFrame(scroll, fg_color=PANEL_BG, corner_radius=4)
            row.pack(fill="x", padx=4, pady=4)

            icon = self.get_cached_program_icon(program.get("path"), size=PROGRAM_ICON_SIZE)
            ctk.CTkLabel(row, text="" if icon else "APP", image=icon, width=42, height=42, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(8, 4), pady=6)

            text_box = ctk.CTkFrame(row, fg_color="transparent")
            text_box.pack(side="left", fill="x", expand=True, padx=6, pady=6)
            ctk.CTkLabel(text_box, text=program["name"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            detail = f"CPU {program.get('cpu_percent', 0):.1f}%  |  RAM {program.get('memory_mb', 0):.1f} MB"
            ctk.CTkLabel(text_box, text=detail, font=("Segoe UI", 10), text_color="#8F8F8F", anchor="w").pack(fill="x")

            ctk.CTkButton(row, text="Add", width=62, height=28, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=4, command=lambda p=program: self.pick_running_program(key, p, picker)).pack(side="right", padx=8)

    def list_running_programs(self):
        current_pid = os.getpid()
        candidates = []
        grouped = {}

        for process in psutil.process_iter(["pid", "name", "exe", "create_time"]):
            try:
                name = process.info.get("name")
                pid = process.info.get("pid")
                if not name or pid == current_pid or pid == 0 or name.lower() in IGNORED_RUNNING_PROGRAM_NAMES:
                    continue
                process.cpu_percent(None)
                candidates.append(process)
            except Exception:
                continue

        time.sleep(RUNNING_PROGRAM_CPU_SAMPLE_SECONDS)

        for process in candidates:
            try:
                name = process.info.get("name")
                if not name:
                    continue
                path = process.info.get("exe") or ""
                memory = process.info.get("memory_info")
                if memory is None:
                    memory = process.memory_info()
                memory_mb = (memory.rss / 1024 / 1024) if memory else 0
                raw_cpu_percent = float(process.cpu_percent(None) or 0)
                cpu_percent = min(100.0, raw_cpu_percent / CPU_CORE_COUNT)
                if cpu_percent < MIN_RUNNING_PROGRAM_CPU_PERCENT and memory_mb < MIN_RUNNING_PROGRAM_MEMORY_MB:
                    continue

                item = grouped.setdefault(
                    name,
                    {
                        "name": name,
                        "path": path,
                        "cpu_percent": 0,
                        "memory_mb": 0,
                        "resource_score": 0,
                        "create_time": 0,
                    },
                )
                item["cpu_percent"] += cpu_percent
                item["memory_mb"] += memory_mb
                item["cpu_percent"] = min(100.0, item["cpu_percent"])
                item["create_time"] = max(item["create_time"], float(process.info.get("create_time") or 0))
                if path and not item.get("path"):
                    item["path"] = path
                item["resource_score"] = item["cpu_percent"] * 100 + item["memory_mb"]
            except Exception:
                continue

        results = list(grouped.values())
        return sorted(results, key=lambda item: item["name"].lower())

    def pick_running_program(self, key, program, picker):
        self.add_program(
            key,
            {
                "name": program["name"],
                "match_type": "process_name",
                "value": program["name"],
                "path": program.get("path") or "",
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
        self.prepare_popup(editor, "Edit Program", 418, 244, grab=True)

        ctk.CTkLabel(editor, text="Edit Program", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", padx=14, pady=(12, 6))

        icon_row = ctk.CTkFrame(editor, fg_color="transparent")
        icon_row.pack(fill="x", padx=14, pady=(0, 8))

        preview_icon = self.get_cached_program_icon(
            self.get_program_icon_source(self.config_data[key][index]),
            size=54,
            source_size=MINI_DETECTED_ICON_SOURCE_SIZE,
            corner_radius=MINI_DETECTED_ICON_CORNER_RADIUS,
        )
        preview_label = ctk.CTkLabel(icon_row, text="" if preview_icon else "APP", image=preview_icon, width=56, height=54, fg_color="#24272B", corner_radius=4, font=("Segoe UI", 10, "bold"))
        preview_label.pack(side="left", padx=(0, 8))

        entry = ctk.CTkEntry(
            icon_row,
            height=54,
            fg_color=FIELD_BG,
            border_color=FIELD_BORDER,
            border_width=2,
            corner_radius=6,
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
        icon_button_row.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkButton(icon_button_row, text="Custom Icon", height=32, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=4, font=("Segoe UI", 13), command=choose_custom_image).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(icon_button_row, text="Program Icon", height=32, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=4, font=("Segoe UI", 13), command=choose_program_icon).pack(side="left", fill="x", expand=True, padx=(5, 0))

        button_row = ctk.CTkFrame(editor, fg_color="transparent")
        button_row.pack(fill="x", padx=14, pady=(0, 14))

        def save_name():
            new_name = entry.get().strip()
            if not new_name:
                return
            self.config_data[key][index]["name"] = new_name
            self.config_data[key][index]["icon_path"] = icon_path_var.get()
            self.save_config()
            editor.destroy()
            self.refresh_program_lists()

        ctk.CTkButton(button_row, text="Save", height=38, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=4, font=("Segoe UI", 15), command=save_name).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(button_row, text="Cancel", height=38, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=4, font=("Segoe UI", 15), command=editor.destroy).pack(side="left", fill="x", expand=True, padx=(5, 0))
        editor.bind("<Return>", lambda event: save_name())
        editor.bind("<Escape>", lambda event: editor.destroy())

    def icon_source_label(self, path):
        if not path:
            return "Default program icon"
        return os.path.basename(path)

    def add_program(self, key, program):
        if self.program_exists(key, program):
            messagebox.showinfo("Auto Audio", "This program rule already exists.")
            return
        self.config_data[key].append(program)
        self.save_config()
        self.draw_ui()

    def program_exists(self, key, program):
        return any(
            item.get("match_type") == program.get("match_type") and item.get("value") == program.get("value")
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
        self.save_config()
        self.refresh_program_lists()

    def detection_rules_signature(self):
        return tuple(
            (key, item.get("match_type", "process_name"), item.get("value", ""), item.get("target_audio", "headset"))
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
                rules.append(
                    {
                        "key": key,
                        "program": program,
                        "match_type": match_type,
                        "value": value,
                        "value_norm": value.casefold(),
                        "process_name_norm": self.normalize_process_name(value),
                        "process_stem_norm": self.normalize_process_stem(value),
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
                self.detected_missing_since = None
                if is_new_detection:
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
                elif list_key == "auto_list" and is_new_detection and target == "headset" and current_state == "headset":
                    self.ask_restore_program = program
                    self.ask_restore_prompt_key = None

                if self.manual_override:
                    pass
                elif list_key == "ask_list":
                    if current_state != target:
                        current_state = self.sync_last_state_with_current_output(force=True) or current_state
                    if current_state != target:
                        self.after(0, lambda p=program: self.show_ask_prompt(p))
                elif current_state != target:
                    current_state = self.sync_last_state_with_current_output(force=True) or current_state
                    if current_state != target:
                        self.after(0, lambda t=target: self.show_audio_switching_ui(t))
                        changed = self.set_audio(target)
                        self.after(0, lambda t=target, p=program, i=icon, c=changed: self.finish_monitor_audio_switch(t, p.get("name", "Program"), i, c))
            else:
                if self.recent_detected_program:
                    now = time.monotonic()
                    if self.detected_missing_since is None:
                        self.detected_missing_since = now
                    if now - self.detected_missing_since < PROGRAM_EXIT_GRACE_SECONDS:
                        time.sleep(CHECK_INTERVAL_SECONDS)
                        continue
                    logging.info("program no longer detected name=%s value=%s", self.recent_detected_program.get("name"), self.recent_detected_program.get("value"))
                    self.recent_detected_program = None
                    self.detected_missing_since = None
                self.pending_prompt_key = None
                current_state = self.sync_last_state_with_current_output(force=False) or self.last_state
                if self.should_prompt_ask_restore():
                    restore_program = self.ask_restore_program
                    restore_target = self.restore_target_for_program(restore_program)
                    restore_prompt_key = self.program_prompt_key(restore_program, restore_target)
                    self.ask_restore_prompt_key = restore_prompt_key
                    self.after(0, lambda p=restore_program, t=restore_target, k=restore_prompt_key: self.show_ask_prompt(p, target_override=t, prompt_key_override=k))
                    self.after(0, lambda: self.update_detect_ui("No Program Detected", None))
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    continue

                should_restore_speaker = current_state == "headset" and not self.ask_restore_program and (not self.manual_override or self.manual_override_during_detection)
                if should_restore_speaker:
                    current_state = self.sync_last_state_with_current_output(force=True) or current_state
                    should_restore_speaker = current_state == "headset" and not self.ask_restore_program and (not self.manual_override or self.manual_override_during_detection)
                if should_restore_speaker:
                    self.after(0, lambda: self.show_audio_switching_ui("speaker"))
                    changed = self.set_audio("speaker")
                    self.after(0, lambda c=changed: self.finish_restore_speaker_switch(c))
                elif self.manual_override_during_detection:
                    self.manual_override = False
                    self.manual_override_during_detection = False
                self.after(0, lambda: self.update_detect_ui("No Program Detected", None))

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

    def program_matches(self, candidate, match_type, value):
        value = value.casefold()
        if match_type == "path":
            return os.path.normcase(os.path.abspath(candidate.get("path", ""))) == os.path.normcase(os.path.abspath(value))
        if match_type == "cmdline":
            return value in candidate.get("cmdline", "").casefold()
        return self.normalize_process_name(candidate.get("name", "")) == self.normalize_process_name(value) or self.normalize_process_stem(candidate.get("name", "")) == self.normalize_process_stem(value)

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

    def should_prompt_ask_restore(self):
        if self.ask_active:
            return False
        if not self.ask_restore_program:
            return False
        prompt_key = self.program_prompt_key(self.ask_restore_program, self.restore_target_for_program(self.ask_restore_program))
        return self.ask_restore_prompt_key != prompt_key

    def show_ask_prompt(self, program, target_override=None, prompt_key_override=None):
        target = target_override or program.get("target_audio", "headset")
        prompt_key = prompt_key_override or self.program_prompt_key(program, target)
        if self.ask_active:
            logging.info("ask prompt skipped already active target=%s program=%s", target, program.get("name"))
            return
        self.cancel_audio_change_notification()
        if self.pending_prompt_key == prompt_key:
            logging.info("ask prompt skipped duplicate key=%s", prompt_key)
            return

        logging.info("ask prompt show target=%s program=%s key=%s", target, program.get("name"), prompt_key)
        self.pending_prompt_key = prompt_key
        self.ask_active = True
        self.ask_program = program
        self.ask_target = target
        if target == program.get("target_audio", "headset"):
            self.ask_restore_program = program
        self.switch_mode("mini", focus=False, animate_mini=True)

        self.ask_remaining = self.get_ask_timeout_seconds()
        self.tick_ask_prompt(program, target)

    def tick_ask_prompt(self, program, target):
        if not self.ask_active:
            return
        if hasattr(self, "ask_label_canvas") and self.ask_label_canvas.winfo_exists():
            self.ask_label_canvas.itemconfigure(self.ask_label_item, text=f"{program.get('name', 'Program')}  |  {self.ask_remaining}s")
        if self.ask_remaining <= 0:
            self.dismiss_ask_prompt()
            return
        self.ask_remaining -= 1
        self.ask_countdown_after_id = self.after(1000, lambda: self.tick_ask_prompt(program, target))

    def accept_ask_prompt(self, target):
        logging.info("ask prompt accepted target=%s program=%s", target, self.ask_program.get("name") if self.ask_program else None)
        accepted_program = self.ask_program
        self.dismiss_ask_prompt(hide=True, immediate=True, mark_restore_dismissed=False)
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
        self.ask_program = None
        self.ask_target = None
        if hide and self.is_mini and self.winfo_viewable() and not self.mini_pinned_by_user:
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
    configure_windows_app_identity()
    single_instance_mutex = acquire_single_instance_mutex()
    if not single_instance_mutex:
        logging.info("second instance detected; exiting")
        sys.exit(0)

    start_mode = "tray"
    if "--show" in sys.argv:
        start_mode = "mini"
    elif "--settings" in sys.argv:
        start_mode = "settings"

    print("Auto Audio Switcher is running.")
    print("Use the tray icon, or run with --show / --settings for visible test mode.")
    logging.info("starting application start_mode=%s argv=%s", start_mode, sys.argv)
    try:
        app = AutoAudioApp(start_mode=start_mode)
        app.mainloop()
    except Exception:
        log_exception("fatal application error")
        raise

