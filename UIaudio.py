import json
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
APP_ICON_FILE = os.path.join(RESOURCE_DIR, "assets", "app_icon.png")
ICON_DIR = os.path.join(RESOURCE_DIR, "assets", "icons")
CHECK_INTERVAL_SECONDS = 2
ASK_TIMEOUT_SECONDS = 25
ASK_TIMEOUT_OPTION_SECONDS = list(range(5, 125, 5))
NOTIFICATION_SECONDS = 4
STARTUP_MINI_POPUP_SECONDS = 3
SHOW_STARTUP_ONBOARDING_EVERY_RUN = False
MINI_WIDTH = 546
MINI_HEIGHT = 94
MINI_ANIMATION_STEPS = 12
MINI_ANIMATION_INTERVAL_MS = 14
SETTINGS_DEFAULT_WIDTH = 592
SETTINGS_DEFAULT_HEIGHT = 966
SETTINGS_MIN_WIDTH = 592
SETTINGS_MIN_HEIGHT = 780
SETTINGS_DEVICE_GAP = 12
SETTINGS_DEVICE_WIDTH = 269
SETTINGS_MIC_HEIGHT = 37
PROGRAM_ICON_SIZE = 32
MINI_DETECTED_ICON_SIZE = 52
MINI_DETECTED_ICON_SOURCE_SIZE = 128
MINI_DETECTED_ICON_CORNER_RADIUS = 7
MINI_DEVICE_BUTTON_WIDTH = 52
MINI_DEVICE_BUTTON_HEIGHT = 42
MINI_DEVICE_BUTTON_GAP = 6
ACTIVE_GRADIENT_START = "#C6FF34"
ACTIVE_GRADIENT_END = "#BBEB41"
MINI_BUTTON_ACTIVE_GRADIENT_START = ACTIVE_GRADIENT_START
MINI_BUTTON_ACTIVE_GRADIENT_END = ACTIVE_GRADIENT_END
MINI_BUTTON_INACTIVE_COLOR = "#20073F"
MINI_BG_GRADIENT_START = "#16123D"
MINI_BG_GRADIENT_END = "#070707"
MINI_BG_FALLBACK = "#0E0B24"
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
SETTINGS_OUTER_BG = "#171717"
SETTINGS_PANEL_BG = "#191919"
SETTINGS_ROW_BG = "#1C1C1C"
SETTINGS_GRADIENT_START = "#282828"
SETTINGS_GRADIENT_END = "#171717"
SETTINGS_DEVICE_ACTIVE_START = ACTIVE_GRADIENT_START
SETTINGS_DEVICE_ACTIVE_END = ACTIVE_GRADIENT_END
SETTINGS_SEPARATOR_COLOR = "#0C131F"
CARD_BG = "#1A1A1A"
CONTROL_BG = "#333333"
CONTROL_HOVER = "#414141"
FIELD_BG = "#303335"
FIELD_BORDER = "#4A4D50"
ACTIVE_COLOR = ACTIVE_GRADIENT_END
ACTIVE_HOVER_COLOR = "#A8D532"
MIC_MUTED_COLOR = "#7F1D1D"
MIC_ACTIVE_COLOR = "#334155"
DEVICE_ACTIVE_COLOR = ACTIVE_GRADIENT_END
DEVICE_INACTIVE_COLOR = "#20073F"
SPI_GETWORKAREA = 0x0030
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2
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


def load_icon_image(kind, black=False, fallback_size=128):
    black_path = os.path.join(ICON_DIR, f"{kind}_b.png")
    path = os.path.join(ICON_DIR, f"{kind}.png")
    if black and os.path.exists(black_path):
        return Image.open(black_path).convert("RGBA")
    try:
        image = Image.open(path).convert("RGBA")
        if black:
            alpha = image.getchannel("A")
            image = Image.new("RGBA", image.size, (0, 0, 0, 255))
            image.putalpha(alpha)
        return image
    except Exception:
        color = (0, 0, 0, 255) if black else (245, 245, 245, 255)
        return draw_ui_icon_image(kind, size=fallback_size, color=color)


def make_ui_icon(kind, size=28, black=False):
    image = load_icon_image(kind, black=black)
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
    return create_linear_gradient(width, height, start_hex, end_hex, angle_degrees=123, solid_until=0.3259)


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


def make_setting_device_header_image(kind, text, active, width=269, height=39):
    background = create_css_like_gradient(width, height, SETTINGS_DEVICE_ACTIVE_START, SETTINGS_DEVICE_ACTIVE_END) if active else Image.new("RGBA", (width, height), DEVICE_INACTIVE_COLOR)

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, width - 1, height + 5), radius=5, fill=255)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    image.alpha_composite(background)
    image.putalpha(mask)

    icon = load_icon_image(kind, black=active)
    icon.thumbnail((24, 24), Image.LANCZOS)

    text_font = get_pil_text_font(18)

    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), text, font=text_font)
    content_width = icon.width + 8 + bbox[2] - bbox[0]
    x = (width - content_width) // 2
    y = (height - icon.height) // 2
    image.alpha_composite(icon, (x, y))
    text_fill = (0, 0, 0, 255) if active else (255, 255, 255, 255)
    draw.text((x + icon.width + 8, (height - (bbox[3] - bbox[1])) / 2 - 1), text, fill=text_fill, font=text_font)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_setting_device_dropdown_image(text, active, width=269, height=37):
    image = create_css_like_gradient(width, height, SETTINGS_DEVICE_ACTIVE_START, SETTINGS_DEVICE_ACTIVE_END) if active else Image.new("RGBA", (width, height), DEVICE_INACTIVE_COLOR)
    mask = Image.new("L", (width, height), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle((0, -6, width - 1, height - 1), radius=5, fill=255)
    image.putalpha(mask)

    text_font = get_pil_text_font(12)

    draw = ImageDraw.Draw(image)
    display_text = text if len(text) <= 28 else text[:25] + "..."
    bbox = draw.textbbox((0, 0), display_text, font=text_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_fill = (0, 0, 0, 255) if active else (255, 255, 255, 255)
    draw.text(((width - text_width) / 2 - 8, (height - text_height) / 2 - 1), display_text, fill=text_fill, font=text_font)
    triangle = [(width - 24, height // 2 - 3), (width - 12, height // 2 - 3), (width - 18, height // 2 + 4)]
    draw.polygon(triangle, fill=text_fill)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_settings_segment_image(text, width, height=37, icon_kind=None, rounded_left=False, rounded_right=False):
    image = Image.new("RGBA", (width, height), CONTROL_BG)
    mask = Image.new("L", (width, height), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle((0, 0, width - 1, height - 1), radius=5, fill=255)
    if not rounded_left:
        draw_mask.rectangle((0, 0, 6, height), fill=255)
    if not rounded_right:
        draw_mask.rectangle((width - 7, 0, width, height), fill=255)
    image.putalpha(mask)

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
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_settings_dropdown_segment_image(text, width, height=37):
    image = Image.new("RGBA", (width, height), CONTROL_BG)

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
    mask_draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=5, fill=255)
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
    draw.line((arrow_x - 5, arrow_y - 2, arrow_x, arrow_y + 3, arrow_x + 5, arrow_y - 2), fill=(0, 0, 0, 255), width=2)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(width, height))


def make_settings_gradient_image(width, height):
    return ImageTk.PhotoImage(create_linear_gradient(max(1, width), max(1, height), SETTINGS_GRADIENT_START, SETTINGS_GRADIENT_END, angle_degrees=160, solid_until=0.0071))


def make_mini_button_image(kind, active=False, muted=False):
    width = MINI_DEVICE_BUTTON_WIDTH
    height = MINI_DEVICE_BUTTON_HEIGHT
    if muted:
        background = Image.new("RGBA", (width, height), MIC_MUTED_COLOR)
    elif active:
        background = create_css_like_gradient(width, height, MINI_BUTTON_ACTIVE_GRADIENT_START, MINI_BUTTON_ACTIVE_GRADIENT_END)
    else:
        background = Image.new("RGBA", (width, height), MINI_BUTTON_INACTIVE_COLOR)

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=4, fill=255)
    button = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    button.alpha_composite(background)
    button.putalpha(mask)

    icon = load_icon_image(kind, black=active)
    icon.thumbnail((28, 28), Image.LANCZOS)
    x = (width - icon.width) // 2
    y = (height - icon.height) // 2
    button.alpha_composite(icon, (x, y))
    return ctk.CTkImage(light_image=button, dark_image=button, size=(width, height))


def make_ask_button_photo(text, fill_color, width=72, height=42, text_color=(255, 255, 255, 255), bold=False):
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=5, fill=fill_color)
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

    yes = Image.new("RGBA", (82, 42), ACTIVE_COLOR)
    yes_mask = Image.new("L", (82, 42), 0)
    ImageDraw.Draw(yes_mask).rounded_rectangle((0, 0, 81, 41), radius=5, fill=255)
    yes.putalpha(yes_mask)
    yes_draw = ImageDraw.Draw(yes)
    yes_font = get_pil_text_font(14, bold=True)
    bbox = yes_draw.textbbox((0, 0), "Yes", font=yes_font)
    yes_draw.text(((82 - (bbox[2] - bbox[0])) / 2, (42 - (bbox[3] - bbox[1])) / 2 - bbox[1]), "Yes", fill=(0, 0, 0, 255), font=yes_font)
    image.alpha_composite(yes, (width - 190, prompt_y + 16))

    no = Image.new("RGBA", (82, 42), (68, 68, 68, 255))
    no_mask = Image.new("L", (82, 42), 0)
    ImageDraw.Draw(no_mask).rounded_rectangle((0, 0, 81, 41), radius=5, fill=255)
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
        self.notification_active = False
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
        self.exe_icon_cache = {}
        self.device_controls = {}
        self.tray = None
        ensure_icon_assets()
        self.icons = {
            "app": make_app_icon(18),
            "speaker": make_ui_icon("speaker", 28),
            "speaker_b": make_ui_icon("speaker", 28, black=True),
            "headset": make_ui_icon("headset", 28),
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
            "mic_muted": make_mini_button_image("mic_muted", muted=True),
            "speaker_active": make_mini_button_image("speaker", active=True),
            "speaker_inactive": make_mini_button_image("speaker", active=False),
            "headset_active": make_mini_button_image("headset", active=True),
            "headset_inactive": make_mini_button_image("headset", active=False),
        }
        self.current_detected_icon = self.icons["no_app"]
        self.audio_device_names = self.get_output_device_names()
        self.sync_audio_config_with_devices(save_changes=True)

        self.title("Auto Audio Switcher")
        self.iconphoto(True, self.app_window_icon_photo)
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)

        self.set_ui_mode("mini")
        self.draw_ui()
        self.start_tray()
        self.install_keyboard_hook()
        self.start_keyboard_event_polling()

        if start_mode == "settings":
            self.switch_mode("settings")
        elif start_mode == "mini":
            self.switch_mode("mini")
        else:
            self.show_startup_mini_popup()
        self.after(250, self.show_startup_onboarding_popups)

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def show_startup_mini_popup(self):
        self.switch_mode("mini", focus=False)
        self.after(STARTUP_MINI_POPUP_SECONDS * 1000, self.hide_startup_mini_popup)

    def hide_startup_mini_popup(self):
        if self.is_mini and self.winfo_viewable() and not self.ask_active and not self.notification_active and not self.onboarding_active and not self.mini_pinned_by_user:
            self.hide_to_tray()

    def restore_mini_focus_after_onboarding(self):
        if not self.is_mini or not self.winfo_viewable():
            return
        self.mini_pinned_by_user = False
        self.bind("<FocusOut>", self.on_mini_focus_out)
        self.deiconify()
        self.lift()
        self.focus_force()
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
            text_color="black",
            corner_radius=6,
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
            text_color="black",
            corner_radius=6,
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
            self.maxsize(0, 0)
            self.minsize(SETTINGS_MIN_WIDTH, SETTINGS_MIN_HEIGHT)
            self.resizable(True, True)
            self.overrideredirect(False)
            self.attributes("-topmost", False)
            self.set_settings_geometry()
            self.after(50, self.apply_dark_title_bar)

    def set_mini_geometry(self, extra_height=0):
        width, height, x, y = self.get_mini_geometry_parts(extra_height=extra_height)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def get_mini_geometry_parts(self, extra_height=0, y_offset=0):
        left, top, right, bottom = self.get_work_area()
        height = MINI_HEIGHT + extra_height
        x = max(left, right - MINI_WIDTH)
        y = max(top, bottom - height + y_offset)
        return MINI_WIDTH, height, x, y

    def get_mini_hidden_y(self, extra_height=0):
        _, _, _, bottom = self.get_work_area()
        return bottom + extra_height

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
        self.cancel_mini_animation()
        width, height, x, final_y = self.get_mini_geometry_parts()
        start_y = self.get_mini_hidden_y()
        self.geometry(f"{width}x{height}+{x}+{start_y}")
        self.deiconify()
        self.lift()
        self.animate_mini_to(x, start_y, final_y, 0, hide_after=False)

    def animate_mini_out(self):
        if not self.is_mini or not self.winfo_viewable():
            self.withdraw()
            return
        self.cancel_mini_animation()
        width, height, x, final_y = self.get_mini_geometry_parts()
        start_y = self.winfo_y()
        end_y = self.get_mini_hidden_y()
        self.geometry(f"{width}x{height}+{x}+{start_y}")
        self.animate_mini_to(x, start_y, end_y, 0, hide_after=True)

    def animate_mini_to(self, x, start_y, end_y, step, hide_after):
        width, height, _, _ = self.get_mini_geometry_parts()
        progress = min(1, step / MINI_ANIMATION_STEPS)
        eased = 1 - (1 - progress) ** 3
        y = round(start_y + (end_y - start_y) * eased)
        self.geometry(f"{width}x{height}+{x}+{y}")

        if progress >= 1:
            self.mini_animation_after_id = None
            if hide_after:
                self.withdraw()
            return

        self.mini_animation_after_id = self.after(
            MINI_ANIMATION_INTERVAL_MS,
            lambda: self.animate_mini_to(x, start_y, end_y, step + 1, hide_after),
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
        width = max(SETTINGS_MIN_WIDTH, int(width_text))
        height = max(SETTINGS_MIN_HEIGHT, int(height_text))
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

    def apply_dark_title_bar(self):
        try:
            hwnd = wintypes.HWND(self.winfo_id())
            enabled = ctypes.c_int(1)
            for attribute in (DWMWA_USE_IMMERSIVE_DARK_MODE, DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1):
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(enabled), ctypes.sizeof(enabled))

            corner_preference = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(corner_preference), ctypes.sizeof(corner_preference))

            caption_color = ctypes.c_int(0x282828)
            text_color = ctypes.c_int(0xFFFFFF)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(caption_color), ctypes.sizeof(caption_color))
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_TEXT_COLOR, ctypes.byref(text_color), ctypes.sizeof(text_color))
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
        self.settings_bg_label = tk.Label(self, bd=0, highlightthickness=0)
        self.settings_bg_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.settings_bg_label.lower()
        self.bind("<Configure>", self.update_settings_background, add="+")
        self.after(0, self.update_settings_background)

    def update_settings_background(self, event=None):
        if self.is_mini or not hasattr(self, "settings_bg_label"):
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

    def get_output_device_names(self):
        try:
            import warnings

            warnings.filterwarnings("ignore")
            from pycaw.pycaw import AudioUtilities
            from pycaw.utils import AudioDeviceState

            output_devices = []
            for device in AudioUtilities.GetAllDevices():
                try:
                    if AudioUtilities.GetEndpointDataFlow(device.id) != "eRender":
                        continue
                    if getattr(device, "state", None) != AudioDeviceState.Active:
                        continue
                    name = getattr(device, "FriendlyName", None) or getattr(device, "friendly_name", None)
                    if name and name not in output_devices:
                        output_devices.append(name)
                except Exception:
                    continue
            return output_devices
        except Exception:
            return []

    def get_input_device_names(self):
        try:
            import warnings

            warnings.filterwarnings("ignore")
            from pycaw.pycaw import AudioUtilities
            from pycaw.utils import AudioDeviceState

            input_devices = []
            for device in AudioUtilities.GetAllDevices():
                try:
                    if AudioUtilities.GetEndpointDataFlow(device.id) != "eCapture":
                        continue
                    if getattr(device, "state", None) != AudioDeviceState.Active:
                        continue
                    name = getattr(device, "FriendlyName", None) or getattr(device, "friendly_name", None)
                    if name and name not in input_devices:
                        input_devices.append(name)
                except Exception:
                    continue
            return input_devices
        except Exception:
            return []

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
        mini_canvas.create_window(MINI_WIDTH - 12, 62, window=button_frame, anchor="e", width=(MINI_DEVICE_BUTTON_WIDTH * 3) + (MINI_DEVICE_BUTTON_GAP * 2), height=MINI_DEVICE_BUTTON_HEIGHT)

        self.mic_btn = ctk.CTkLabel(button_frame, text="", image=self.mini_button_images["mic"], width=MINI_DEVICE_BUTTON_WIDTH, height=MINI_DEVICE_BUTTON_HEIGHT)
        self.mic_btn.bind("<Button-1>", lambda event: self.toggle_microphone_mute())
        self.mic_btn.pack(side="left", padx=(0, MINI_DEVICE_BUTTON_GAP))

        self.speaker_btn = ctk.CTkLabel(button_frame, text="", image=self.mini_button_images["speaker_inactive"], width=MINI_DEVICE_BUTTON_WIDTH, height=MINI_DEVICE_BUTTON_HEIGHT)
        self.speaker_btn.bind("<Button-1>", lambda event: self.manual_set_audio("speaker"))
        self.speaker_btn.pack(side="left", padx=(0, MINI_DEVICE_BUTTON_GAP))

        self.headset_btn = ctk.CTkLabel(button_frame, text="", image=self.mini_button_images["headset_inactive"], width=MINI_DEVICE_BUTTON_WIDTH, height=MINI_DEVICE_BUTTON_HEIGHT)
        self.headset_btn.bind("<Button-1>", lambda event: self.manual_set_audio("headset"))
        self.headset_btn.pack(side="left")

        self.update_mini_buttons_ui(self.last_state)
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

        self.ask_yes_button_photo = make_ask_button_photo("Yes", ACTIVE_COLOR, text_color=(0, 0, 0, 255), bold=True)
        self.ask_no_button_photo = make_ask_button_photo("No", "#444444")
        yes_button = mini_canvas.create_image(355, 49, image=self.ask_yes_button_photo)
        no_button = mini_canvas.create_image(433, 49, image=self.ask_no_button_photo)
        mini_canvas.tag_bind(yes_button, "<Button-1>", lambda event: self.accept_ask_prompt(target))
        mini_canvas.tag_bind(no_button, "<Button-1>", lambda event: self.dismiss_ask_prompt(immediate=True))

    def draw_settings_ui(self):
        self.configure(fg_color=SETTINGS_GRADIENT_END)
        self.install_settings_background()
        self.audio_device_names = self.get_output_device_names()
        self.sync_audio_config_with_devices(save_changes=True)
        device_options = self.build_device_options()
        self.microphone_device_names = self.get_input_device_names()
        microphone_options = self.build_microphone_options()

        output_panel = ctk.CTkFrame(self, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_GRADIENT_START, corner_radius=8)
        output_panel.pack(fill="x", padx=8, pady=(8, 7))

        ctk.CTkLabel(output_panel, text="Audio Output Setting", font=("Segoe UI", 22, "bold"), text_color="white").pack(anchor="w", padx=13, pady=(11, 8))

        device_frame = ctk.CTkFrame(output_panel, fg_color="transparent")
        device_frame.pack(fill="x", padx=13)
        device_frame.grid_columnconfigure(0, weight=1, uniform="device")
        device_frame.grid_columnconfigure(1, weight=1, uniform="device")

        self.create_device_box(device_frame, "Speaker", "speaker", device_options).grid(row=0, column=0, sticky="ew", padx=(0, SETTINGS_DEVICE_GAP // 2))
        self.create_device_box(device_frame, "Headset", "headset", device_options).grid(row=0, column=1, sticky="ew", padx=(SETTINGS_DEVICE_GAP // 2, 0))

        self.create_microphone_settings(output_panel, microphone_options)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=0, pady=(0, 0))
        self.startup_var = ctk.BooleanVar(value=bool(self.config_data.get("start_with_windows", False)))
        bottom_options = ctk.CTkFrame(bottom, fg_color="transparent")
        bottom_options.pack(fill="x", padx=8, pady=(3, 7))
        ctk.CTkCheckBox(
            bottom_options,
            text="Run on Start up",
            variable=self.startup_var,
            font=("Segoe UI", 14),
            fg_color=ACTIVE_COLOR,
            hover_color=ACTIVE_HOVER_COLOR,
        ).pack(side="left", anchor="w")

        timeout_options = [self.format_ask_timeout_seconds(seconds) for seconds in ASK_TIMEOUT_OPTION_SECONDS]
        self.ask_timeout_var = ctk.StringVar(value=self.format_ask_timeout_seconds())
        ask_timeout_frame = ctk.CTkFrame(bottom_options, fg_color="transparent")
        ask_timeout_frame.pack(side="right")
        ctk.CTkLabel(
            ask_timeout_frame,
            text="Ask duration",
            font=("Segoe UI", 13),
            text_color="#B8B8B8",
        ).pack(side="left", padx=(0, 8))
        self.ask_timeout_combo = ctk.CTkComboBox(
            ask_timeout_frame,
            values=timeout_options,
            variable=self.ask_timeout_var,
            width=96,
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
        self.ask_timeout_combo.pack(side="left")
        self.ask_timeout_combo.bind("<FocusOut>", lambda event: self.ask_timeout_var.set(self.format_ask_timeout_seconds(self.ask_timeout_var.get())))
        self.ask_timeout_combo.bind("<Return>", lambda event: self.ask_timeout_var.set(self.format_ask_timeout_seconds(self.ask_timeout_var.get())))
        ctk.CTkButton(bottom, text="Save", height=39, fg_color=ACTIVE_COLOR, hover_color=ACTIVE_HOVER_COLOR, text_color="black", corner_radius=8, command=self.save_and_close).pack(fill="x", padx=8, pady=(0, 8))

        program_panel = ctk.CTkFrame(self, fg_color=SETTINGS_PANEL_BG, bg_color=SETTINGS_GRADIENT_END, corner_radius=8, border_width=0)
        program_panel.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        ctk.CTkLabel(program_panel, text="Program List", font=("Segoe UI", 22, "bold"), text_color="white").pack(anchor="w", padx=13, pady=(6, 2))
        self.program_list_frame = ctk.CTkFrame(program_panel, fg_color="transparent")
        self.program_list_frame.pack(fill="both", expand=True)
        self.refresh_program_lists()


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

    def create_device_box(self, parent, title, mode, device_options):
        header_width = SETTINGS_DEVICE_WIDTH
        frame = ctk.CTkFrame(parent, fg_color="transparent", width=header_width, height=77, corner_radius=5)
        frame.pack_propagate(False)
        frame.grid_propagate(False)
        is_active = self.last_state == mode
        header_image = make_setting_device_header_image(mode, title, is_active, width=header_width)
        device_button = ctk.CTkLabel(frame, text="", image=header_image, width=header_width, height=39, cursor="hand2")
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
        option_menu = ctk.CTkLabel(frame, text="", image=dropdown_image, width=header_width, height=37, cursor="hand2")
        option_menu._settings_dropdown_image = dropdown_image
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
            header = make_setting_device_header_image(mode, title, active, width=current_width)
            dropdown = make_setting_device_dropdown_image(variable.get(), active, width=current_width)
            device_button._settings_header_image = header
            option_menu._settings_dropdown_image = dropdown
            device_button.configure(image=header, width=current_width)
            option_menu.configure(image=dropdown, width=current_width)
            dropdown_menu.configure(background=DEVICE_ACTIVE_COLOR if active else DEVICE_INACTIVE_COLOR)

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

        option_menu.bind("<Button-1>", open_dropdown)
        option_menu.pack(fill="x", pady=(1, 0))
        variable.trace_add("write", lambda *_: refresh_visuals())
        frame.bind("<Configure>", lambda event: refresh_visuals())
        self.device_controls[mode] = {"button": device_button, "menu": dropdown_menu, "dropdown": option_menu, "title": title, "variable": variable, "refresh": refresh_visuals}
        return frame

    def create_microphone_settings(self, parent, microphone_options):
        frame = ctk.CTkFrame(parent, fg_color=SETTINGS_SEPARATOR_COLOR, corner_radius=5, height=SETTINGS_MIC_HEIGHT)
        frame.pack(fill="x", padx=13, pady=(8, 14))
        frame.pack_propagate(False)

        top_row = ctk.CTkFrame(frame, fg_color=SETTINGS_SEPARATOR_COLOR, height=SETTINGS_MIC_HEIGHT)
        top_row.pack(fill="both", expand=True)
        top_row.pack_propagate(False)

        mic_image = make_settings_segment_image("Mic", 97, height=SETTINGS_MIC_HEIGHT, icon_kind="mic", rounded_left=True, rounded_right=False)
        mic_button = ctk.CTkLabel(
            top_row,
            text="",
            image=mic_image,
            width=97,
            height=SETTINGS_MIC_HEIGHT,
            cursor="hand2",
        )
        mic_button._segment_image = mic_image
        mic_button.bind("<Button-1>", lambda event: self.toggle_microphone_mute())
        mic_button.pack(side="left", fill="y")
        ctk.CTkFrame(top_row, fg_color=SETTINGS_SEPARATOR_COLOR, width=1, height=SETTINGS_MIC_HEIGHT).pack(side="left")

        selected_microphone = self.config_data.get("microphone_name") if self.config_data.get("microphone_name") in microphone_options else microphone_options[0]
        self.mic_var = ctk.StringVar(value=selected_microphone)
        mic_menu_label = ctk.CTkLabel(top_row, text="", width=220, height=SETTINGS_MIC_HEIGHT, cursor="hand2")
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
            width = max(120, mic_menu_label.winfo_width() or 220)
            image = make_settings_dropdown_segment_image(self.mic_var.get(), width, SETTINGS_MIC_HEIGHT)
            mic_menu_label._dropdown_image = image
            mic_menu_label.configure(image=image, width=width, height=SETTINGS_MIC_HEIGHT)

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
        mic_menu_label.pack(side="left", fill="both", expand=True)
        ctk.CTkFrame(top_row, fg_color=SETTINGS_SEPARATOR_COLOR, width=1, height=SETTINGS_MIC_HEIGHT).pack(side="left")

        current_hotkey = self.config_data.get("microphone_mute_hotkey", "") or HOTKEY_NONE_LABEL
        self.mic_hotkey_var = ctk.StringVar(value=current_hotkey if current_hotkey in HOTKEY_OPTIONS else HOTKEY_NONE_LABEL)
        hotkey_menu_label = ctk.CTkLabel(top_row, text="", width=96, height=SETTINGS_MIC_HEIGHT, cursor="hand2")
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
            image = make_settings_dropdown_segment_image(self.mic_hotkey_var.get(), 96, SETTINGS_MIC_HEIGHT)
            hotkey_menu_label._dropdown_image = image
            hotkey_menu_label.configure(image=image, width=96, height=SETTINGS_MIC_HEIGHT)

        def open_hotkey_menu(event=None):
            try:
                hotkey_menu.tk_popup(hotkey_menu_label.winfo_rootx(), hotkey_menu_label.winfo_rooty() + hotkey_menu_label.winfo_height())
            finally:
                try:
                    hotkey_menu.grab_release()
                except Exception:
                    pass

        hotkey_menu_label.bind("<Button-1>", open_hotkey_menu)
        self.mic_hotkey_var.trace_add("write", lambda *_: refresh_hotkey_menu())
        hotkey_menu_label.pack(side="left", fill="y")
        ctk.CTkFrame(top_row, fg_color=SETTINGS_SEPARATOR_COLOR, width=1, height=SETTINGS_MIC_HEIGHT).pack(side="left")

        detect_image = make_settings_segment_image("Detect Key", 100, height=SETTINGS_MIC_HEIGHT, rounded_left=False, rounded_right=True)
        detect_button = ctk.CTkLabel(
            top_row,
            text="",
            image=detect_image,
            width=100,
            height=SETTINGS_MIC_HEIGHT,
            cursor="hand2",
        )
        detect_button._segment_image = detect_image
        detect_button.bind("<Button-1>", lambda event: self.open_microphone_hotkey_capture())
        detect_button.pack(side="left", fill="y")
        self.after(0, refresh_mic_menu)
        self.after(0, refresh_hotkey_menu)

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
        for widget in self.program_list_frame.winfo_children():
            widget.destroy()
        self.create_list_ui(self.program_list_frame, "Ask Before Change", "ask_list")
        self.create_list_ui(self.program_list_frame, "Auto Change", "auto_list")

    def create_list_ui(self, parent, title, key):
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.pack(fill="both", expand=True)

        header = ctk.CTkFrame(section, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(4, 2))
        ctk.CTkFrame(header, fg_color="#636363", width=2, height=15, corner_radius=4).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 14), text_color="white").pack(side="left")

        scroll = ctk.CTkScrollableFrame(section, height=211, fg_color=SURFACE_BG, border_width=1, border_color="#080808", corner_radius=9)
        scroll.pack(fill="both", expand=True, padx=13, pady=(0, 8))
        self.list_drop_targets[key] = self.get_scroll_drop_widgets(scroll)

        programs = self.config_data[key]
        if not programs:
            ctk.CTkLabel(scroll, text="No programs yet", text_color="#777777", height=40).pack(fill="x")
        else:
            for program in programs:
                item = ctk.CTkFrame(scroll, fg_color=SETTINGS_ROW_BG, corner_radius=7, height=51)
                item.pack(fill="x", pady=2, padx=4)
                item.pack_propagate(False)

                handle = ctk.CTkLabel(item, text="", image=self.icons["handle"], width=34, height=51, cursor="hand2")
                handle.pack(side="left", padx=(4, 0), pady=0)
                handle.bind("<ButtonPress-1>", lambda event, k=key, p=program: self.start_program_drag(event, k, p))
                handle.bind("<B1-Motion>", self.update_program_drag)
                handle.bind("<ButtonRelease-1>", self.finish_program_drag)

                icon = self.get_cached_program_icon(self.get_program_icon_source(program), size=PROGRAM_ICON_SIZE)
                icon_label = ctk.CTkLabel(item, text="" if icon else "APP", image=icon, width=38, height=38, fg_color="#272A2F", corner_radius=4, font=("Segoe UI", 9, "bold"))
                icon_label.pack(side="left", padx=(8, 8), pady=6)

                text_box = ctk.CTkFrame(item, fg_color="transparent")
                text_box.pack(side="left", fill="both", expand=True, padx=0, pady=5)
                name_canvas = self.create_marquee_label(
                    text_box,
                    program.get("name", "Unknown"),
                    ("Segoe UI", 14),
                    "white",
                    SETTINGS_ROW_BG,
                    42,
                )
                name_canvas.pack(fill="both", expand=True)

                headset_active = program.get("target_audio") == "headset"
                speaker_active = program.get("target_audio") == "speaker"
                ctk.CTkButton(item, text="", image=self.icons["trash"], width=38, height=39, fg_color="#991B1B", hover_color="#B91C1C", corner_radius=4, command=lambda p=program, k=key: self.remove_program(k, p)).pack(side="right", padx=(3, 6))
                ctk.CTkButton(item, text="", image=self.icons["headset_b" if headset_active else "headset"], width=38, height=39, fg_color=self.target_color(program, "headset"), hover_color=ACTIVE_HOVER_COLOR, corner_radius=4, command=lambda p=program, k=key: self.set_program_target(k, p, "headset")).pack(side="right", padx=2)
                ctk.CTkButton(item, text="", image=self.icons["speaker_b" if speaker_active else "speaker"], width=38, height=39, fg_color=self.target_color(program, "speaker"), hover_color=ACTIVE_HOVER_COLOR, corner_radius=4, command=lambda p=program, k=key: self.set_program_target(k, p, "speaker")).pack(side="right", padx=2)
                ctk.CTkButton(item, text="", image=self.icons["edit"], width=39, height=39, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=4, command=lambda p=program, k=key: self.edit_program_name(k, p)).pack(side="right", padx=2)

        ctk.CTkButton(section, text="+  Add Program", height=39, fg_color=CONTROL_BG, hover_color=CONTROL_HOVER, corner_radius=13, font=("Segoe UI", 14), command=lambda: self.open_add_program_menu(key)).pack(fill="x", padx=13, pady=(0, 6))

    def get_program_icon_source(self, program, process_path=None):
        return program.get("icon_path") or process_path or program.get("path") or ""

    def get_cached_program_icon(self, path, size=PROGRAM_ICON_SIZE, source_size=None, corner_radius=0):
        cache_key = (path or "", size, source_size or size, corner_radius)
        if cache_key not in self.exe_icon_cache:
            extension = os.path.splitext(path or "")[1].lower()
            if extension in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".ico"):
                icon = get_icon_from_image(path, size=size, source_size=source_size, corner_radius=corner_radius)
            else:
                icon = get_icon_from_exe(path, size=size, source_size=source_size, corner_radius=corner_radius)
            self.exe_icon_cache[cache_key] = icon
        return self.exe_icon_cache[cache_key]

    def start_program_drag(self, event, source_key, program):
        self.drag_data = {
            "source_key": source_key,
            "program": program,
            "start_x": event.x_root,
            "start_y": event.y_root,
        }
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
        self.drag_data = None
        self.destroy_drag_preview()

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
        self.refresh_program_lists()
        self.update_idletasks()

    def target_color(self, program, mode):
        return ACTIVE_COLOR if program.get("target_audio") == mode else CONTROL_BG

    def switch_mode(self, target, focus=True):
        self.cancel_mini_animation()
        was_visible = self.winfo_viewable()
        if target == "settings" and was_visible:
            self.withdraw()
        self.set_ui_mode(target)
        self.draw_ui()
        self.update_idletasks()
        if target == "settings" and not self.config_data.get("settings_geometry"):
            self.fit_settings_geometry_to_content()
        self.deiconify()
        self.lift()
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
        if hasattr(self, "speaker_btn") and self.speaker_btn.winfo_exists():
            self.speaker_btn.configure(image=self.mini_button_images["speaker_active" if state == "speaker" else "speaker_inactive"])
            self.headset_btn.configure(image=self.mini_button_images["headset_active" if state == "headset" else "headset_inactive"])
        self.update_microphone_button_ui()
        self.update_device_controls_ui(state)

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

    def show_audio_change_notification(self, target, program_name=None, icon=None, animate=True):
        if self.notification_after_id:
            try:
                self.after_cancel(self.notification_after_id)
            except Exception:
                pass
            self.notification_after_id = None

        self.notification_active = True
        self.ask_active = False
        self.pending_prompt_key = None
        self.current_detected_icon = icon
        was_visible = self.is_mini and self.winfo_viewable()
        current_y = self.winfo_y() if was_visible else None
        self.switch_mode("mini", focus=False)
        if was_visible and current_y is not None:
            width, height, x, _ = self.get_mini_geometry_parts()
            self.geometry(f"{width}x{height}+{x}+{current_y}")
        self.update_mini_buttons_ui(target)

        fallback_icon = self.icons.get("no_app") if program_name == "No Program Detected" else self.icons["headset"] if target == "headset" else self.icons["speaker"]
        self.update_mini_detect_canvas("Audio output changed", icon or fallback_icon)
        if animate and not was_visible:
            self.animate_mini_in()
        self.notification_after_id = self.after(NOTIFICATION_SECONDS * 1000, self.finish_audio_change_notification)

    def finish_audio_change_notification(self):
        self.notification_active = False
        self.notification_after_id = None
        if self.is_mini and self.winfo_viewable() and not self.ask_active and not self.mini_pinned_by_user:
            self.animate_mini_out()

    def manual_set_audio(self, mode):
        if not self.set_audio(mode):
            return
        detected = self.find_matching_program()
        self.last_state = mode
        self.manual_override = True
        self.manual_override_during_detection = detected is not None
        if detected and detected[0] == "ask_list" and mode == "headset":
            self.ask_restore_program = detected[1]
            self.ask_restore_prompt_key = None
        self.update_mini_buttons_ui(mode)

    def set_audio(self, mode):
        self.audio_device_names = self.get_output_device_names()
        self.sync_audio_config_with_devices(save_changes=True)
        target = self.config_data["headset_name"] if mode == "headset" else self.config_data["speaker_name"]
        if not target or target == "No audio device found" or target not in self.audio_device_names:
            print(f"audio switch failed: no valid {mode} output device selected")
            return False

        if self.set_audio_with_pycaw(target):
            return True
        return self.set_audio_with_nircmd(target)

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
            return

        muted = self.get_microphone_muted()
        if muted is None:
            return
        self.set_microphone_muted(not muted)

    def refresh_microphone_mute_ui(self):
        if self.config_data.get("microphone_mute_hotkey", ""):
            self.update_microphone_button_ui()
            return

        muted = self.get_microphone_muted()
        if muted is not None:
            self.mic_muted = muted
        self.update_microphone_button_ui()

    def update_microphone_button_ui(self):
        if hasattr(self, "mic_btn") and self.mic_btn.winfo_exists():
            muted = bool(self.mic_muted)
            self.mic_btn.configure(
                image=self.mini_button_images["mic_muted"] if muted else self.mini_button_images["mic"]
            )

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

        if self.is_running:
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

    def set_audio_with_pycaw(self, target):
        try:
            import warnings

            warnings.filterwarnings("ignore")
            from pycaw.pycaw import AudioUtilities
            from pycaw.constants import ERole

            for device in AudioUtilities.GetAllDevices():
                if AudioUtilities.GetEndpointDataFlow(device.id) != "eRender":
                    continue
                name = getattr(device, "FriendlyName", None) or getattr(device, "friendly_name", None)
                if name == target:
                    AudioUtilities.SetDefaultDevice(device.id, roles=[ERole.eMultimedia, ERole.eConsole, ERole.eCommunications])
                    return True
        except Exception as exc:
            print(f"pycaw audio switch failed: {exc}")
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
            return False
        try:
            results = []
            for role in ("0", "1", "2"):
                completed = subprocess.run(
                    [nircmd_path, "setdefaultsounddevice", target, role],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                results.append(completed.returncode)
            return all(code == 0 for code in results)
        except Exception as exc:
            print(f"nircmd audio switch failed: {exc}")
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
        sort_buttons["name"] = ctk.CTkButton(sort_frame, text="A-Z", width=58, height=28, corner_radius=4)
        sort_buttons["name"].pack(side="left", padx=(0, 6))
        sort_buttons["resource"] = ctk.CTkButton(sort_frame, text="Resource", width=86, height=28, corner_radius=4)
        sort_buttons["resource"].pack(side="left", padx=(0, 6))
        sort_buttons["recent"] = ctk.CTkButton(sort_frame, text="Recent", width=74, height=28, corner_radius=4)
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
                    text_color="black" if is_active else "white",
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

    def monitor_loop(self):
        while self.is_running:
            found = self.find_matching_program()
            if found:
                list_key, program, process_path = found
                icon = self.get_cached_program_icon(
                    self.get_program_icon_source(program, process_path),
                    size=MINI_DETECTED_ICON_SIZE,
                    source_size=MINI_DETECTED_ICON_SOURCE_SIZE,
                    corner_radius=MINI_DETECTED_ICON_CORNER_RADIUS,
                )
                target = program.get("target_audio", "headset")
                self.after(0, lambda p=program, i=icon: self.update_detect_ui(p.get("name", "Unknown"), i))

                if self.manual_override:
                    pass
                elif list_key == "ask_list" and self.last_state != target:
                    self.ask_restore_prompt_key = None
                    self.after(0, lambda p=program: self.show_ask_prompt(p))
                elif self.last_state != target:
                    if self.set_audio(target):
                        self.last_state = target
                        self.after(0, lambda t=target: self.update_mini_buttons_ui(t))
                        self.after(0, lambda t=target, p=program, i=icon: self.show_audio_change_notification(t, p.get("name", "Program"), i))
            else:
                self.pending_prompt_key = None
                if self.should_prompt_ask_restore():
                    restore_program = self.ask_restore_program
                    self.ask_restore_prompt_key = self.program_prompt_key(restore_program, "speaker")
                    self.after(0, lambda p=restore_program: self.show_ask_prompt(p, target_override="speaker", prompt_key_override=self.ask_restore_prompt_key))
                    self.after(0, lambda: self.update_detect_ui("No Program Detected", None))
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    continue

                should_restore_speaker = self.last_state == "headset" and not self.ask_restore_program and (not self.manual_override or self.manual_override_during_detection)
                if should_restore_speaker:
                    if self.set_audio("speaker"):
                        self.last_state = "speaker"
                        self.manual_override = False
                        self.manual_override_during_detection = False
                        self.after(0, lambda: self.update_mini_buttons_ui("speaker"))
                        self.after(0, lambda: self.show_audio_change_notification("speaker", "No Program Detected", None))
                elif self.manual_override_during_detection:
                    self.manual_override = False
                    self.manual_override_during_detection = False
                self.after(0, lambda: self.update_detect_ui("No Program Detected", None))

            time.sleep(CHECK_INTERVAL_SECONDS)

    def find_matching_program(self):
        active_titles = self.get_visible_window_titles()
        candidates = []
        try:
            for process in psutil.process_iter(["name", "exe", "cmdline"]):
                try:
                    candidates.append(
                        {
                            "name": process.info.get("name") or "",
                            "path": process.info.get("exe") or "",
                            "cmdline": " ".join(process.info.get("cmdline") or []),
                        }
                    )
                except Exception:
                    continue
        except Exception:
            return None

        for key in ("auto_list", "ask_list"):
            for program in self.config_data[key]:
                match_type = program.get("match_type", "process_name")
                value = program.get("value", "")
                if not value:
                    continue
                if match_type == "window_title" and any(value.lower() in title.lower() for title in active_titles):
                    return key, program, program.get("path")
                for candidate in candidates:
                    if self.program_matches(candidate, match_type, value):
                        return key, program, candidate.get("path")
        return None

    def program_matches(self, candidate, match_type, value):
        value = value.lower()
        if match_type == "path":
            return candidate.get("path", "").lower() == value
        if match_type == "cmdline":
            return value in candidate.get("cmdline", "").lower()
        return candidate.get("name", "").lower() == value

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

    def should_prompt_ask_restore(self):
        if self.ask_active or self.notification_active:
            return False
        if not self.ask_restore_program or self.last_state != "headset":
            return False
        prompt_key = self.program_prompt_key(self.ask_restore_program, "speaker")
        return self.ask_restore_prompt_key != prompt_key

    def show_ask_prompt(self, program, target_override=None, prompt_key_override=None):
        target = target_override or program.get("target_audio", "headset")
        prompt_key = prompt_key_override or self.program_prompt_key(program, target)
        if self.ask_active or self.notification_active:
            return
        if self.pending_prompt_key == prompt_key:
            return

        self.pending_prompt_key = prompt_key
        self.ask_active = True
        self.ask_program = program
        self.ask_target = target
        if target == "headset" and self.last_state == "headset":
            self.ask_restore_program = program
            self.ask_restore_prompt_key = None
        self.switch_mode("mini")
        self.animate_mini_in()

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
        accepted_program = self.ask_program
        self.dismiss_ask_prompt(hide=True, immediate=True, mark_restore_dismissed=False)
        changed = self.set_audio(target)
        if not changed:
            return
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
        if target == "speaker":
            self.ask_restore_program = None
            self.ask_restore_prompt_key = None
        else:
            self.ask_restore_program = accepted_program
            self.ask_restore_prompt_key = None
        self.show_audio_change_notification(target, program_name, icon, animate=False)

    def dismiss_ask_prompt(self, hide=True, immediate=False, mark_restore_dismissed=True):
        dismissed_restore_prompt = mark_restore_dismissed and self.ask_target == "speaker" and self.ask_restore_program is not None
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
            if immediate:
                self.cancel_mini_animation()
                self.withdraw()
                self.update_idletasks()
            else:
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
        self.mini_pinned_by_user = False
        self.cancel_mini_animation()
        self.withdraw()
        self.start_tray()

    def on_window_close(self):
        if not self.is_mini:
            self.save_settings()
        self.hide_to_tray()

    def show_app(self, *args):
        self.after(0, lambda: self.switch_mode("mini"))

    def show_settings_from_tray(self, *args):
        self.after(0, lambda: self.switch_mode("settings"))

    def quit_app(self, *args):
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
    start_mode = "tray"
    if "--show" in sys.argv:
        start_mode = "mini"
    elif "--settings" in sys.argv:
        start_mode = "settings"

    print("Auto Audio Switcher is running.")
    print("Use the tray icon, or run with --show / --settings for visible test mode.")
    app = AutoAudioApp(start_mode=start_mode)
    app.mainloop()

