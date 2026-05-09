import json
import math
import os
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
ICON_DIR = os.path.join(RESOURCE_DIR, "assets", "icons")
CHECK_INTERVAL_SECONDS = 2
ASK_TIMEOUT_SECONDS = 15
NOTIFICATION_SECONDS = 4
STARTUP_MINI_POPUP_SECONDS = 3
MINI_WIDTH = 420
MINI_HEIGHT = 94
MINI_ANIMATION_STEPS = 12
MINI_ANIMATION_INTERVAL_MS = 14
SETTINGS_DEFAULT_WIDTH = 680
SETTINGS_DEFAULT_HEIGHT = 760
SETTINGS_MIN_WIDTH = 680
SETTINGS_MIN_HEIGHT = 700
PROGRAM_ICON_SIZE = 32
MINI_DETECTED_ICON_SIZE = 52
MINI_DETECTED_ICON_SOURCE_SIZE = 128
MINI_DETECTED_ICON_CORNER_RADIUS = 7
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
ACTIVE_COLOR = "#2563EB"
DEVICE_ACTIVE_COLOR = "#3B82F6"
DEVICE_INACTIVE_COLOR = "#1E293B"
SPI_GETWORKAREA = 0x0030
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


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


def make_tray_image():
    image = Image.new("RGBA", (64, 64), (26, 26, 26, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 56, 56), radius=14, fill=(59, 130, 246, 255))
    draw.arc((18, 17, 46, 47), 205, 335, fill=(255, 255, 255, 255), width=5)
    draw.rectangle((17, 29, 25, 39), fill=(255, 255, 255, 255))
    draw.rectangle((39, 29, 47, 39), fill=(255, 255, 255, 255))
    return image


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


def make_ui_icon(kind, size=28):
    path = os.path.join(ICON_DIR, f"{kind}.png")
    try:
        image = Image.open(path).convert("RGBA")
    except Exception:
        image = draw_ui_icon_image(kind, size=128)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))


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
        self.drag_data = None
        self.mini_animation_after_id = None
        self.list_drop_targets = {}
        self.exe_icon_cache = {}
        self.device_controls = {}
        self.tray = None
        ensure_icon_assets()
        self.icons = {
            "speaker": make_ui_icon("speaker", 28),
            "headset": make_ui_icon("headset", 28),
            "gear": make_ui_icon("gear", 22),
            "trash": make_ui_icon("trash", 28),
            "handle": make_ui_icon("handle", 24),
            "minimize": make_ui_icon("minimize", 16),
            "close": make_ui_icon("close", 16),
            "edit": make_ui_icon("edit", 28),
        }
        self.audio_device_names = self.get_output_device_names()

        self.title("Auto Audio Switcher")
        self.protocol("WM_DELETE_WINDOW", self.on_window_close)

        self.set_ui_mode("mini")
        self.draw_ui()
        self.start_tray()

        if start_mode == "settings":
            self.switch_mode("settings")
        elif start_mode == "mini":
            self.switch_mode("mini")
        else:
            self.show_startup_mini_popup()

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def show_startup_mini_popup(self):
        self.switch_mode("mini", focus=False)
        self.after(STARTUP_MINI_POPUP_SECONDS * 1000, self.hide_startup_mini_popup)

    def hide_startup_mini_popup(self):
        if self.is_mini and self.winfo_viewable() and not self.ask_active and not self.notification_active:
            self.hide_to_tray()

    def default_config(self):
        return {
            "headset_name": "Headset",
            "speaker_name": "Speakers",
            "auto_list": [],
            "ask_list": [],
            "start_with_windows": False,
            "settings_geometry": "",
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
        return config

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

            caption_color = ctypes.c_int(0x000000)
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

    def draw_ui(self):
        self.unbind("<FocusOut>")
        for widget in self.winfo_children():
            widget.destroy()

        if self.is_mini:
            self.draw_mini_ui()
        else:
            self.list_drop_targets = {}
            self.draw_settings_ui()

    def create_marquee_label(self, parent, text, font_tuple, text_color, bg_color, height):
        canvas = tk.Canvas(parent, height=height, width=1, bg=bg_color, bd=0, highlightthickness=0, relief="flat")
        canvas._marquee_config = {
            "text": text or "",
            "font": font_tuple,
            "text_color": text_color,
            "bg_color": bg_color,
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
                self.draw_marquee_fade(canvas, config["bg_color"], width, height)
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

    def draw_marquee_fade(self, canvas, bg_color, width, height):
        fade_width = min(MARQUEE_FADE_WIDTH, max(1, width))
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
        self.configure(fg_color="#171717")
        self.bind("<FocusOut>", self.on_mini_focus_out)

        if self.ask_active:
            self.draw_ask_mini_ui()
            return

        header = ctk.CTkFrame(self, fg_color="#101010", height=28, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        header.bind("<ButtonPress-1>", self.start_move)
        header.bind("<B1-Motion>", self.do_move)

        ctk.CTkLabel(header, text="Auto Audio", font=("Segoe UI", 11, "bold"), text_color="#D7D7D7").pack(side="left", padx=12)
        ctk.CTkButton(header, text="", image=self.icons["close"], width=28, height=24, fg_color="transparent", hover_color="#333333", command=self.hide_to_tray).pack(side="right", padx=(0, 4))
        ctk.CTkButton(header, text="", image=self.icons["minimize"], width=28, height=24, fg_color="transparent", hover_color="#333333", command=self.hide_to_tray).pack(side="right", padx=2)
        ctk.CTkButton(header, text="", image=self.icons["gear"], width=34, height=24, fg_color="transparent", hover_color="#333333", command=lambda: self.switch_mode("settings")).pack(side="right", padx=4)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=8)

        self.mini_icon_label = ctk.CTkLabel(content, text="", image=self.current_detected_icon, width=MINI_DETECTED_ICON_SIZE, height=MINI_DETECTED_ICON_SIZE, font=("Segoe UI", 12, "bold"))
        self.mini_icon_label.pack(side="left")

        text_frame = ctk.CTkFrame(content, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, padx=12)

        self.mini_name_canvas = self.create_marquee_label(
            text_frame,
            self.current_detected_name,
            ("Segoe UI", 17, "bold"),
            "white",
            "#171717",
            40,
        )
        self.mini_name_canvas.pack(fill="both", expand=True)

        button_frame = ctk.CTkFrame(content, fg_color="transparent")
        button_frame.pack(side="right")

        self.speaker_btn = ctk.CTkButton(button_frame, text="", image=self.icons["speaker"], width=52, height=42, corner_radius=8, command=lambda: self.manual_set_audio("speaker"))
        self.speaker_btn.pack(side="left", padx=(0, 6))

        self.headset_btn = ctk.CTkButton(button_frame, text="", image=self.icons["headset"], width=52, height=42, corner_radius=8, command=lambda: self.manual_set_audio("headset"))
        self.headset_btn.pack(side="left")

        self.update_mini_buttons_ui(self.last_state)

    def draw_ask_mini_ui(self):
        target = self.ask_target or "headset"
        program_name = self.ask_program.get("name", "Program") if self.ask_program else "Program"

        prompt = ctk.CTkFrame(self, fg_color="#171717", corner_radius=0)
        prompt.pack(fill="both", expand=True, padx=12, pady=10)
        prompt.bind("<ButtonPress-1>", self.start_move)
        prompt.bind("<B1-Motion>", self.do_move)

        top_row = ctk.CTkFrame(prompt, fg_color="transparent")
        top_row.pack(fill="both", expand=True)

        icon = self.icons["headset"] if target == "headset" else self.icons["speaker"]
        ctk.CTkLabel(top_row, text="", image=icon, width=34).pack(side="left")

        text_box = ctk.CTkFrame(top_row, fg_color="transparent")
        text_box.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkLabel(text_box, text=f"Switch to {self.audio_label(target)}?", font=("Segoe UI", 15, "bold"), text_color="white", anchor="w").pack(fill="x")
        self.ask_label = ctk.CTkLabel(text_box, text=program_name, font=("Segoe UI", 11), text_color="#B8B8B8", anchor="w")
        self.ask_label.pack(fill="x")

        button_row = ctk.CTkFrame(top_row, fg_color="transparent")
        button_row.pack(side="right")
        ctk.CTkButton(button_row, text="Yes", width=72, height=42, fg_color=ACTIVE_COLOR, hover_color="#1D4ED8", command=lambda: self.accept_ask_prompt(target)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(button_row, text="No", width=72, height=42, fg_color="#444444", hover_color="#555555", command=self.dismiss_ask_prompt).pack(side="left")

    def draw_settings_ui(self):
        self.configure(fg_color="#171717")
        self.audio_device_names = self.get_output_device_names()
        device_options = self.build_device_options()

        ctk.CTkLabel(self, text="Auto Audio Settings", font=("Segoe UI", 22, "bold"), text_color="white").pack(pady=(22, 14))

        device_frame = ctk.CTkFrame(self, fg_color="transparent")
        device_frame.pack(fill="x", padx=18)

        self.create_device_box(device_frame, "Speaker", "speaker", device_options).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.create_device_box(device_frame, "Headset", "headset", device_options).pack(side="left", fill="x", expand=True, padx=(6, 0))

        ctk.CTkLabel(self, text="Program List", font=("Segoe UI", 16, "bold"), text_color="white").pack(anchor="w", padx=22, pady=(20, 8))
        self.program_list_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.program_list_frame.pack(fill="both", expand=True)
        self.refresh_program_lists()

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=18, pady=18)
        self.startup_var = ctk.BooleanVar(value=bool(self.config_data.get("start_with_windows", False)))
        ctk.CTkCheckBox(
            bottom,
            text="윈도우가 실행되면 자동 실행",
            variable=self.startup_var,
            font=("Segoe UI", 13),
            fg_color=ACTIVE_COLOR,
            hover_color="#1D4ED8",
        ).pack(anchor="w", pady=(0, 12))
        ctk.CTkButton(bottom, text="Save", height=42, fg_color="#2563EB", hover_color="#1D4ED8", command=self.save_and_close).pack(fill="x")

    def build_device_options(self):
        options = [name for name in self.audio_device_names if name]
        for key in ("speaker_name", "headset_name"):
            name = self.config_data.get(key)
            if name and name not in options:
                options.insert(0, name)
        return options or ["No audio device found"]

    def create_device_box(self, parent, title, mode, device_options):
        frame = ctk.CTkFrame(parent, fg_color="#242424", corner_radius=8)
        is_active = self.last_state == mode
        label = title
        icon = self.icons["speaker"] if mode == "speaker" else self.icons["headset"]
        menu_color = DEVICE_ACTIVE_COLOR if is_active else DEVICE_INACTIVE_COLOR
        device_button = ctk.CTkButton(frame, text=label, image=icon, compound="left", height=36, fg_color=menu_color, hover_color="#1D4ED8", command=lambda: self.manual_set_audio(mode))
        device_button.pack(fill="x", padx=10, pady=(10, 8))

        variable = ctk.StringVar(value=self.config_data.get(f"{mode}_name") if self.config_data.get(f"{mode}_name") in device_options else device_options[0])
        if mode == "speaker":
            self.sp_var = variable
        else:
            self.hs_var = variable

        option_menu = ctk.CTkOptionMenu(
            frame,
            values=device_options,
            variable=variable,
            width=210,
            height=30,
            fg_color=menu_color,
            button_color=menu_color,
            button_hover_color="#1D4ED8",
            anchor="center",
        )
        option_menu.pack(fill="x", padx=10, pady=(0, 10))
        self.device_controls[mode] = {"button": device_button, "menu": option_menu}
        return frame

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
        header.pack(fill="x", padx=22, pady=(8, 0))
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 13, "bold"), text_color="#CFCFCF").pack(side="left")

        scroll = ctk.CTkScrollableFrame(section, height=130, fg_color="#101010", border_width=1, border_color="#2A2A2A", corner_radius=8)
        scroll.pack(fill="both", expand=True, padx=18, pady=(6, 8))
        self.list_drop_targets[key] = self.get_scroll_drop_widgets(scroll)

        programs = self.config_data[key]
        if not programs:
            ctk.CTkLabel(scroll, text="No programs yet", text_color="#777777", height=40).pack(fill="x")
        else:
            for program in programs:
                item = ctk.CTkFrame(scroll, fg_color="#1C1C1C", corner_radius=6)
                item.pack(fill="x", pady=4, padx=4)

                handle = ctk.CTkLabel(item, text="", image=self.icons["handle"], width=28, height=42, cursor="hand2")
                handle.pack(side="left", padx=(6, 2), pady=5)
                handle.bind("<ButtonPress-1>", lambda event, k=key, p=program: self.start_program_drag(event, k, p))
                handle.bind("<B1-Motion>", self.update_program_drag)
                handle.bind("<ButtonRelease-1>", self.finish_program_drag)

                icon = self.get_cached_program_icon(self.get_program_icon_source(program), size=PROGRAM_ICON_SIZE)
                icon_label = ctk.CTkLabel(item, text="" if icon else "APP", image=icon, width=42, height=42, font=("Segoe UI", 10, "bold"))
                icon_label.pack(side="left", padx=(8, 4), pady=5)

                text_box = ctk.CTkFrame(item, fg_color="transparent")
                text_box.pack(side="left", fill="both", expand=True, padx=4, pady=5)
                name_canvas = self.create_marquee_label(
                    text_box,
                    program.get("name", "Unknown"),
                    ("Segoe UI", 14, "bold"),
                    "white",
                    "#1C1C1C",
                    42,
                )
                name_canvas.pack(fill="both", expand=True)

                ctk.CTkButton(item, text="", image=self.icons["trash"], width=36, height=30, fg_color="#5B1F1F", hover_color="#7F1D1D", command=lambda p=program, k=key: self.remove_program(k, p)).pack(side="right", padx=(4, 8))
                ctk.CTkButton(item, text="", image=self.icons["headset"], width=36, height=30, fg_color=self.target_color(program, "headset"), hover_color="#2563EB", command=lambda p=program, k=key: self.set_program_target(k, p, "headset")).pack(side="right", padx=4)
                ctk.CTkButton(item, text="", image=self.icons["speaker"], width=36, height=30, fg_color=self.target_color(program, "speaker"), hover_color="#2563EB", command=lambda p=program, k=key: self.set_program_target(k, p, "speaker")).pack(side="right", padx=4)
                ctk.CTkButton(item, text="", image=self.icons["edit"], width=36, height=30, fg_color="#333333", hover_color="#444444", command=lambda p=program, k=key: self.edit_program_name(k, p)).pack(side="right", padx=4)

        ctk.CTkButton(section, text="Add Program", height=34, fg_color="#333333", hover_color="#444444", command=lambda: self.open_add_program_menu(key)).pack(fill="x", padx=22, pady=(0, 12))

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
        return "#2563EB" if program.get("target_audio") == mode else "#3A3A3A"

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
        if self.ask_active or self.notification_active:
            return
        focused = self.focus_get()
        if focused is None:
            self.hide_to_tray()

    def start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def do_move(self, event):
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def audio_label(self, state):
        return "Headset" if state == "headset" else "Speaker"

    def update_mini_buttons_ui(self, state):
        if hasattr(self, "speaker_btn") and self.speaker_btn.winfo_exists():
            active = ACTIVE_COLOR
            inactive = "#424242"
            self.speaker_btn.configure(fg_color=active if state == "speaker" else inactive)
            self.headset_btn.configure(fg_color=active if state == "headset" else inactive)
        self.update_device_controls_ui(state)

    def update_device_controls_ui(self, state):
        for mode, controls in getattr(self, "device_controls", {}).items():
            color = DEVICE_ACTIVE_COLOR if mode == state else DEVICE_INACTIVE_COLOR
            hover = "#1D4ED8" if mode == state else "#334155"
            button = controls.get("button")
            menu = controls.get("menu")
            try:
                if button and button.winfo_exists():
                    button.configure(fg_color=color, hover_color=hover)
                if menu and menu.winfo_exists():
                    menu.configure(fg_color=color, button_color=color, button_hover_color=hover)
            except Exception:
                pass

    def update_detect_ui(self, name, icon=None):
        self.current_detected_name = name
        self.current_detected_icon = icon
        if self.ask_active or self.notification_active:
            return
        if hasattr(self, "mini_name_canvas") and self.mini_name_canvas.winfo_exists():
            display_name = name or "No Program Detected"
            self.set_marquee_text(self.mini_name_canvas, display_name)
        if hasattr(self, "mini_icon_label") and self.mini_icon_label.winfo_exists():
            self.mini_icon_label.configure(image=icon, text="")

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

        if hasattr(self, "mini_icon_label") and self.mini_icon_label.winfo_exists():
            fallback_icon = self.icons["headset"] if target == "headset" else self.icons["speaker"]
            self.mini_icon_label.configure(image=icon or fallback_icon, text="")
        if hasattr(self, "mini_name_canvas") and self.mini_name_canvas.winfo_exists():
            self.set_marquee_text(self.mini_name_canvas, "Audio output changed")
        if animate and not was_visible:
            self.animate_mini_in()
        self.notification_after_id = self.after(NOTIFICATION_SECONDS * 1000, self.finish_audio_change_notification)

    def finish_audio_change_notification(self):
        self.notification_active = False
        self.notification_after_id = None
        if self.is_mini and self.winfo_viewable() and not self.ask_active:
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
        target = self.config_data["headset_name"] if mode == "headset" else self.config_data["speaker_name"]
        if not target or target == "No audio device found":
            return False

        if self.set_audio_with_pycaw(target):
            return True
        return self.set_audio_with_nircmd(target)

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
                    AudioUtilities.SetDefaultDevice(device.id, roles=[ERole.eMultimedia, ERole.eConsole])
                    return True
        except Exception as exc:
            print(f"pycaw audio switch failed: {exc}")
        return False

    def set_audio_with_nircmd(self, target):
        nircmd_path = os.path.join(RESOURCE_DIR, "nircmd.exe")
        if not os.path.exists(nircmd_path):
            return False
        try:
            for role in ("0", "1", "2"):
                subprocess.run([nircmd_path, "setdefaultsounddevice", target, role], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as exc:
            print(f"nircmd audio switch failed: {exc}")
            return False

    def save_settings(self):
        self.remember_settings_geometry()
        if hasattr(self, "sp_var"):
            self.config_data["speaker_name"] = self.sp_var.get()
        if hasattr(self, "hs_var"):
            self.config_data["headset_name"] = self.hs_var.get()
        if hasattr(self, "startup_var"):
            self.config_data["start_with_windows"] = bool(self.startup_var.get())
            self.set_startup_enabled(self.config_data["start_with_windows"])
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
        menu.title("Add Program")
        menu.geometry("360x180+780+280")
        menu.transient(self)
        menu.configure(fg_color="#171717")

        ctk.CTkLabel(menu, text="Add Program", font=("Segoe UI", 18, "bold"), text_color="white").pack(pady=(22, 16))
        ctk.CTkButton(menu, text="Add .exe", height=36, fg_color="#333333", hover_color="#444444", command=lambda: self.choose_add_exe(key, menu)).pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkButton(menu, text="Show Running Program List", height=36, fg_color="#333333", hover_color="#444444", command=lambda: self.choose_running_program(key, menu)).pack(fill="x", padx=24)

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
        picker.configure(fg_color="#171717")

        header = ctk.CTkFrame(picker, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(18, 8))
        ctk.CTkLabel(header, text="Running Programs", font=("Segoe UI", 18, "bold")).pack(side="left")

        sort_frame = ctk.CTkFrame(header, fg_color="transparent")
        sort_frame.pack(side="right")
        sort_buttons = {}
        sort_buttons["name"] = ctk.CTkButton(sort_frame, text="A-Z", width=58, height=28)
        sort_buttons["name"].pack(side="left", padx=(0, 6))
        sort_buttons["resource"] = ctk.CTkButton(sort_frame, text="Resource", width=86, height=28)
        sort_buttons["resource"].pack(side="left", padx=(0, 6))
        sort_buttons["recent"] = ctk.CTkButton(sort_frame, text="Recent", width=74, height=28)
        sort_buttons["recent"].pack(side="left")

        scroll = ctk.CTkScrollableFrame(picker, fg_color="#101010", corner_radius=8)
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
                    hover_color="#1D4ED8" if is_active else "#444444",
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
            row = ctk.CTkFrame(scroll, fg_color="#1C1C1C", corner_radius=6)
            row.pack(fill="x", padx=4, pady=4)

            icon = self.get_cached_program_icon(program.get("path"), size=PROGRAM_ICON_SIZE)
            ctk.CTkLabel(row, text="" if icon else "APP", image=icon, width=42, height=42, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(8, 4), pady=6)

            text_box = ctk.CTkFrame(row, fg_color="transparent")
            text_box.pack(side="left", fill="x", expand=True, padx=6, pady=6)
            ctk.CTkLabel(text_box, text=program["name"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            detail = f"CPU {program.get('cpu_percent', 0):.1f}%  |  RAM {program.get('memory_mb', 0):.1f} MB"
            ctk.CTkLabel(text_box, text=detail, font=("Segoe UI", 10), text_color="#8F8F8F", anchor="w").pack(fill="x")

            ctk.CTkButton(row, text="Add", width=62, height=28, command=lambda p=program: self.pick_running_program(key, p, picker)).pack(side="right", padx=8)

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
        editor.title("Edit Program")
        editor.geometry("420x260+740+260")
        editor.transient(self)
        editor.grab_set()
        editor.configure(fg_color="#171717")

        ctk.CTkLabel(editor, text="Edit Program", font=("Segoe UI", 16, "bold"), text_color="white").pack(anchor="w", padx=18, pady=(18, 8))
        entry = ctk.CTkEntry(editor, height=34)
        entry.pack(fill="x", padx=18)
        entry.insert(0, self.config_data[key][index].get("name", ""))
        entry.focus_set()
        entry.select_range(0, "end")

        icon_row = ctk.CTkFrame(editor, fg_color="transparent")
        icon_row.pack(fill="x", padx=18, pady=(14, 0))

        preview_icon = self.get_cached_program_icon(
            self.get_program_icon_source(self.config_data[key][index]),
            size=PROGRAM_ICON_SIZE,
            source_size=MINI_DETECTED_ICON_SOURCE_SIZE,
            corner_radius=MINI_DETECTED_ICON_CORNER_RADIUS,
        )
        preview_label = ctk.CTkLabel(icon_row, text="" if preview_icon else "APP", image=preview_icon, width=42, height=42, font=("Segoe UI", 10, "bold"))
        preview_label.pack(side="left", padx=(0, 10))

        icon_text = ctk.CTkLabel(icon_row, text=self.icon_source_label(icon_path_var.get()), font=("Segoe UI", 11), text_color="#B8B8B8", anchor="w")
        icon_text.pack(side="left", fill="x", expand=True)

        def refresh_icon_preview():
            preview_source = icon_path_var.get() or self.config_data[key][index].get("path", "")
            icon = self.get_cached_program_icon(
                preview_source,
                size=PROGRAM_ICON_SIZE,
                source_size=MINI_DETECTED_ICON_SOURCE_SIZE,
                corner_radius=MINI_DETECTED_ICON_CORNER_RADIUS,
            )
            preview_label.configure(image=icon, text="" if icon else "APP")
            icon_text.configure(text=self.icon_source_label(icon_path_var.get()))

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
        icon_button_row.pack(fill="x", padx=18, pady=(10, 0))
        ctk.CTkButton(icon_button_row, text="Custom Image", height=32, fg_color="#333333", hover_color="#444444", command=choose_custom_image).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(icon_button_row, text="Program Icon", height=32, fg_color="#333333", hover_color="#444444", command=choose_program_icon).pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkButton(icon_button_row, text="Default", width=82, height=32, fg_color="#333333", hover_color="#444444", command=lambda: (icon_path_var.set(""), refresh_icon_preview())).pack(side="left", padx=(6, 0))

        button_row = ctk.CTkFrame(editor, fg_color="transparent")
        button_row.pack(fill="x", padx=18, pady=16)

        def save_name():
            new_name = entry.get().strip()
            if not new_name:
                return
            self.config_data[key][index]["name"] = new_name
            self.config_data[key][index]["icon_path"] = icon_path_var.get()
            self.save_config()
            editor.destroy()
            self.refresh_program_lists()

        ctk.CTkButton(button_row, text="Cancel", width=92, height=32, fg_color="#333333", hover_color="#444444", command=editor.destroy).pack(side="right")
        ctk.CTkButton(button_row, text="Save", width=92, height=32, fg_color=ACTIVE_COLOR, hover_color="#1D4ED8", command=save_name).pack(side="right", padx=(0, 8))
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
                elif list_key == "ask_list":
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

                should_restore_speaker = self.last_state == "headset" and (not self.manual_override or self.manual_override_during_detection)
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
        if self.pending_prompt_key == prompt_key or self.last_state == target:
            return

        self.pending_prompt_key = prompt_key
        self.ask_active = True
        self.ask_program = program
        self.ask_target = target
        self.switch_mode("mini")
        self.animate_mini_in()

        self.ask_remaining = ASK_TIMEOUT_SECONDS
        self.tick_ask_prompt(program, target)

    def tick_ask_prompt(self, program, target):
        if not self.ask_active:
            return
        if hasattr(self, "ask_label") and self.ask_label.winfo_exists():
            self.ask_label.configure(text=f"{program.get('name', 'Program')}  |  {self.ask_remaining}s")
        if self.ask_remaining <= 0:
            self.dismiss_ask_prompt()
            return
        self.ask_remaining -= 1
        self.ask_countdown_after_id = self.after(1000, lambda: self.tick_ask_prompt(program, target))

    def accept_ask_prompt(self, target):
        accepted_program = self.ask_program
        changed = self.set_audio(target)
        if not changed:
            self.dismiss_ask_prompt()
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
        self.dismiss_ask_prompt(hide=False)
        self.show_audio_change_notification(target, program_name, icon, animate=False)

    def dismiss_ask_prompt(self, hide=True):
        dismissed_restore_prompt = self.ask_target == "speaker" and self.ask_restore_program is not None
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
        if hide and self.is_mini and self.winfo_viewable():
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
