import json
import math
import os
import subprocess
import sys
import threading
import time
import winreg
import ctypes
from ctypes import wintypes
from tkinter import filedialog, messagebox

import customtkinter as ctk
import psutil
import pystray
import win32con
import win32gui
import win32process
import win32ui
from PIL import Image, ImageDraw


APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
ICON_DIR = os.path.join(APP_DIR, "assets", "icons")
CHECK_INTERVAL_SECONDS = 2
ASK_TIMEOUT_SECONDS = 15
NOTIFICATION_SECONDS = 4
MINI_WIDTH = 420
MINI_HEIGHT = 94
PROGRAM_ICON_SIZE = 32
APP_NAME = "AutoAudioSwitcher"
ACTIVE_COLOR = "#2563EB"
INACTIVE_BLUE = "#1E293B"
SPI_GETWORKAREA = 0x0030


def get_icon_from_exe(exe_path, size=32):
    try:
        if not exe_path or not os.path.exists(exe_path):
            return None

        large_icons, small_icons = win32gui.ExtractIconEx(exe_path, 0)
        icons = (large_icons or small_icons) if size >= 32 else (small_icons or large_icons)
        if not icons:
            return None

        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(hdc, size, size)
        memory_dc = hdc.CreateCompatibleDC()
        memory_dc.SelectObject(bitmap)

        win32gui.DrawIconEx(memory_dc.GetSafeHdc(), 0, 0, icons[0], size, size, 0, 0, win32con.DI_NORMAL)
        for icon in large_icons + small_icons:
            win32gui.DestroyIcon(icon)

        bmpinfo = bitmap.GetInfo()
        bmpstr = bitmap.GetBitmapBits(True)
        image = Image.frombuffer("RGBA", (bmpinfo["bmWidth"], bmpinfo["bmHeight"]), bmpstr, "raw", "BGRA", 0, 1)
        return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
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

    return image


def ensure_icon_assets():
    os.makedirs(ICON_DIR, exist_ok=True)
    for name in ("speaker", "headset", "gear", "trash", "handle"):
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
        self.current_detected_name = "No Program"
        self.current_detected_icon = None
        self.pending_prompt_key = None
        self.ask_countdown_after_id = None
        self.notification_after_id = None
        self.ask_active = False
        self.ask_program = None
        self.ask_target = None
        self.notification_active = False
        self.drag_data = None
        self.list_drop_targets = {}
        self.exe_icon_cache = {}
        self.tray = None
        ensure_icon_assets()
        self.icons = {
            "speaker": make_ui_icon("speaker", 28),
            "headset": make_ui_icon("headset", 28),
            "gear": make_ui_icon("gear", 22),
            "trash": make_ui_icon("trash", 28),
            "handle": make_ui_icon("handle", 24),
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
            self.withdraw()

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def default_config(self):
        return {
            "headset_name": "Headset",
            "speaker_name": "Speakers",
            "auto_list": [],
            "ask_list": [],
            "start_with_windows": False,
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
            self.overrideredirect(True)
            self.attributes("-topmost", True)
            self.set_mini_geometry()
        else:
            self.is_mini = False
            self.overrideredirect(False)
            self.attributes("-topmost", False)
            self.set_settings_geometry()

    def set_mini_geometry(self, extra_height=0):
        left, top, right, bottom = self.get_work_area()
        height = MINI_HEIGHT + extra_height
        x = max(left, right - MINI_WIDTH)
        y = max(top, bottom - height)
        self.geometry(f"{MINI_WIDTH}x{height}+{x}+{y}")

    def get_work_area(self):
        rect = wintypes.RECT()
        try:
            ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
            return rect.left, rect.top, rect.right, rect.bottom
        except Exception:
            return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()

    def set_settings_geometry(self):
        self.geometry("600x200")

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
        ctk.CTkButton(header, text="x", width=28, height=24, fg_color="transparent", hover_color="#333333", command=self.hide_to_tray).pack(side="right", padx=(0, 4))
        ctk.CTkButton(header, text="-", width=28, height=24, fg_color="transparent", hover_color="#333333", command=self.hide_to_tray).pack(side="right", padx=2)
        ctk.CTkButton(header, text="", image=self.icons["gear"], width=34, height=24, fg_color="transparent", hover_color="#333333", command=lambda: self.switch_mode("settings")).pack(side="right", padx=4)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=12, pady=8)

        self.mini_icon_label = ctk.CTkLabel(content, text="APP", image=self.current_detected_icon, width=42, height=42, font=("Segoe UI", 12, "bold"))
        self.mini_icon_label.pack(side="left")

        text_frame = ctk.CTkFrame(content, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, padx=12)

        self.mini_name_label = ctk.CTkLabel(text_frame, text=self.current_detected_name, font=("Segoe UI", 14, "bold"), text_color="white", anchor="w")
        self.mini_name_label.pack(fill="x")

        self.mini_state_label = ctk.CTkLabel(text_frame, text=f"Output: {self.audio_label(self.last_state)}", font=("Segoe UI", 11), text_color="#B8B8B8", anchor="w")
        self.mini_state_label.pack(fill="x", pady=(2, 0))

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
        button_row.pack(side="right", fill="y")
        ctk.CTkButton(button_row, text="Yes", width=86, height=34, fg_color=ACTIVE_COLOR, hover_color="#1D4ED8", command=lambda: self.accept_ask_prompt(target)).pack(fill="x", pady=(0, 5))
        ctk.CTkButton(button_row, text="No", width=86, height=34, fg_color="#444444", hover_color="#555555", command=self.dismiss_ask_prompt).pack(fill="x")

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
        self.program_list_frame.pack(fill="x")
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
        menu_color = ACTIVE_COLOR if is_active else INACTIVE_BLUE
        ctk.CTkButton(frame, text=label, image=icon, compound="left", height=36, fg_color=menu_color, hover_color="#1D4ED8", command=lambda: self.manual_set_audio(mode)).pack(fill="x", padx=10, pady=(10, 8))

        variable = ctk.StringVar(value=self.config_data.get(f"{mode}_name") if self.config_data.get(f"{mode}_name") in device_options else device_options[0])
        if mode == "speaker":
            self.sp_var = variable
        else:
            self.hs_var = variable

        ctk.CTkOptionMenu(
            frame,
            values=device_options,
            variable=variable,
            width=210,
            height=30,
            fg_color=menu_color,
            button_color=menu_color,
            button_hover_color="#1D4ED8",
        ).pack(fill="x", padx=10, pady=(0, 10))
        return frame

    def refresh_program_lists(self):
        if not hasattr(self, "program_list_frame") or not self.program_list_frame.winfo_exists():
            return
        self.list_drop_targets = {}
        for widget in self.program_list_frame.winfo_children():
            widget.destroy()
        self.create_list_ui(self.program_list_frame, "Auto Change", "auto_list")
        self.create_list_ui(self.program_list_frame, "Ask Before Change", "ask_list")

    def create_list_ui(self, parent, title, key):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(8, 0))
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 13, "bold"), text_color="#CFCFCF").pack(side="left")

        scroll = ctk.CTkScrollableFrame(parent, height=130, fg_color="#101010", border_width=1, border_color="#2A2A2A", corner_radius=8)
        scroll.pack(fill="x", padx=18, pady=(6, 8))
        self.list_drop_targets[key] = scroll

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

                icon = self.get_cached_program_icon(program.get("path"), size=PROGRAM_ICON_SIZE)
                icon_label = ctk.CTkLabel(item, text="" if icon else "APP", image=icon, width=42, height=42, font=("Segoe UI", 10, "bold"))
                icon_label.pack(side="left", padx=(8, 4), pady=5)

                label_text = program.get("name", "Unknown")
                detail = f"{program.get('match_type', 'process_name')}: {program.get('value', '')}"
                text_box = ctk.CTkFrame(item, fg_color="transparent")
                text_box.pack(side="left", fill="x", expand=True, padx=4)
                name_label = ctk.CTkLabel(text_box, text=label_text, font=("Segoe UI", 12, "bold"), anchor="w")
                name_label.pack(fill="x")
                detail_label = ctk.CTkLabel(text_box, text=detail, font=("Segoe UI", 10), text_color="#8F8F8F", anchor="w")
                detail_label.pack(fill="x")

                ctk.CTkButton(item, text="", image=self.icons["trash"], width=36, height=30, fg_color="#5B1F1F", hover_color="#7F1D1D", command=lambda p=program, k=key: self.remove_program(k, p)).pack(side="right", padx=(4, 8))
                ctk.CTkButton(item, text="", image=self.icons["headset"], width=36, height=30, fg_color=self.target_color(program, "headset"), hover_color="#2563EB", command=lambda p=program, k=key: self.set_program_target(k, p, "headset")).pack(side="right", padx=4)
                ctk.CTkButton(item, text="", image=self.icons["speaker"], width=36, height=30, fg_color=self.target_color(program, "speaker"), hover_color="#2563EB", command=lambda p=program, k=key: self.set_program_target(k, p, "speaker")).pack(side="right", padx=4)

        ctk.CTkButton(parent, text="Add Program", height=34, fg_color="#333333", hover_color="#444444", command=lambda: self.open_add_program_menu(key)).pack(fill="x", padx=22, pady=(0, 12))

    def get_cached_program_icon(self, path, size=PROGRAM_ICON_SIZE):
        cache_key = (path or "", size)
        if cache_key not in self.exe_icon_cache:
            self.exe_icon_cache[cache_key] = get_icon_from_exe(path, size=size)
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
        target_key = self.get_drop_target_key(event.x_root, event.y_root)
        program = self.drag_data["program"]
        self.drag_data = None
        self.destroy_drag_preview()

        if not target_key or target_key == source_key:
            return
        self.move_program_between_lists(source_key, target_key, program)

    def get_drop_target_key(self, x, y):
        for key, frame in self.list_drop_targets.items():
            if not frame.winfo_exists():
                continue
            left = frame.winfo_rootx()
            top = frame.winfo_rooty()
            right = left + frame.winfo_width()
            bottom = top + frame.winfo_height()
            if left <= x <= right and top <= y <= bottom:
                return key
        return None

    def move_program_between_lists(self, source_key, target_key, program):
        if program not in self.config_data[source_key]:
            return
        if self.program_exists(target_key, program):
            messagebox.showinfo("Auto Audio", "This program rule already exists in the target list.")
            return
        self.config_data[source_key].remove(program)
        self.config_data[target_key].append(program)
        self.save_config()
        self.refresh_program_lists()
        self.update_idletasks()

    def target_color(self, program, mode):
        return "#2563EB" if program.get("target_audio") == mode else "#3A3A3A"

    def switch_mode(self, target, focus=True):
        was_visible = self.winfo_viewable()
        if target == "settings" and was_visible:
            self.withdraw()
        self.set_ui_mode(target)
        self.draw_ui()
        self.update_idletasks()
        if target == "settings":
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
        if hasattr(self, "mini_state_label") and self.mini_state_label.winfo_exists():
            self.mini_state_label.configure(text=f"Output: {self.audio_label(state)}")

    def update_detect_ui(self, name, icon=None):
        self.current_detected_name = name
        self.current_detected_icon = icon
        if self.ask_active or self.notification_active:
            return
        if hasattr(self, "mini_name_label") and self.mini_name_label.winfo_exists():
            shown = name[:24] + ".." if len(name) > 26 else name
            self.mini_name_label.configure(text=shown)
        if hasattr(self, "mini_icon_label") and self.mini_icon_label.winfo_exists():
            self.mini_icon_label.configure(image=icon, text="" if icon else "APP")

    def show_audio_change_notification(self, target, program_name=None, icon=None):
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
        self.switch_mode("mini", focus=False)
        self.update_mini_buttons_ui(target)

        if hasattr(self, "mini_icon_label") and self.mini_icon_label.winfo_exists():
            fallback_icon = self.icons["headset"] if target == "headset" else self.icons["speaker"]
            self.mini_icon_label.configure(image=icon or fallback_icon, text="")
        if hasattr(self, "mini_name_label") and self.mini_name_label.winfo_exists():
            self.mini_name_label.configure(text="Audio output changed")
        if hasattr(self, "mini_state_label") and self.mini_state_label.winfo_exists():
            source = f"{program_name}  |  " if program_name else ""
            self.mini_state_label.configure(text=f"{source}Output: {self.audio_label(target)}")

        self.notification_after_id = self.after(NOTIFICATION_SECONDS * 1000, self.finish_audio_change_notification)

    def finish_audio_change_notification(self):
        self.notification_active = False
        self.notification_after_id = None
        if self.is_mini and self.winfo_viewable() and not self.ask_active:
            self.hide_to_tray()

    def manual_set_audio(self, mode):
        self.set_audio(mode)
        self.last_state = mode
        self.manual_override = True
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
        nircmd_path = os.path.join(APP_DIR, "nircmd.exe")
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
        sort_buttons["resource"].pack(side="left")

        scroll = ctk.CTkScrollableFrame(picker, fg_color="#101010", corner_radius=8)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        processes = self.list_running_programs()
        sort_buttons["name"].configure(command=lambda: self.render_running_programs(scroll, processes, key, picker, "name", sort_buttons))
        sort_buttons["resource"].configure(command=lambda: self.render_running_programs(scroll, processes, key, picker, "resource", sort_buttons))
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
        seen = set()
        results = []
        for process in psutil.process_iter(["name", "exe", "cpu_percent", "memory_info"]):
            try:
                name = process.info.get("name")
                if not name or name in seen:
                    continue
                path = process.info.get("exe") or ""
                memory = process.info.get("memory_info")
                memory_mb = (memory.rss / 1024 / 1024) if memory else 0
                cpu_percent = float(process.info.get("cpu_percent") or 0)
                seen.add(name)
                results.append(
                    {
                        "name": name,
                        "path": path,
                        "cpu_percent": cpu_percent,
                        "memory_mb": memory_mb,
                        "resource_score": cpu_percent * 100 + memory_mb,
                    }
                )
            except Exception:
                continue
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
                icon = self.get_cached_program_icon(process_path or program.get("path"), size=40)
                target = program.get("target_audio", "headset")
                self.after(0, lambda p=program, i=icon: self.update_detect_ui(p.get("name", "Unknown"), i))

                if list_key == "ask_list":
                    self.after(0, lambda p=program: self.show_ask_prompt(p))
                elif self.last_state != target:
                    self.manual_override = False
                    if self.set_audio(target):
                        self.last_state = target
                        self.after(0, lambda t=target: self.update_mini_buttons_ui(t))
                        self.after(0, lambda t=target, p=program, i=icon: self.show_audio_change_notification(t, p.get("name", "Program"), i))
                else:
                    self.manual_override = False
            else:
                self.pending_prompt_key = None
                if self.last_state == "headset" and not self.manual_override:
                    if self.set_audio("speaker"):
                        self.last_state = "speaker"
                        self.after(0, lambda: self.update_mini_buttons_ui("speaker"))
                        self.after(0, lambda: self.show_audio_change_notification("speaker", "No Program", None))
                self.after(0, lambda: self.update_detect_ui("No Program", None))

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

    def show_ask_prompt(self, program):
        target = program.get("target_audio", "headset")
        prompt_key = f"{program.get('match_type')}:{program.get('value')}:{target}"
        if self.pending_prompt_key == prompt_key or self.last_state == target:
            return

        self.pending_prompt_key = prompt_key
        self.ask_active = True
        self.ask_program = program
        self.ask_target = target
        self.switch_mode("mini")
        self.deiconify()
        self.lift()

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
        changed = self.set_audio(target)
        if not changed:
            self.dismiss_ask_prompt()
            return
        self.last_state = target
        self.manual_override = False
        self.update_mini_buttons_ui(target)
        program_name = self.ask_program.get("name", "Program") if self.ask_program else "Program"
        icon = self.get_cached_program_icon(self.ask_program.get("path"), size=40) if self.ask_program else None
        self.dismiss_ask_prompt(hide=False)
        self.show_audio_change_notification(target, program_name, icon)

    def dismiss_ask_prompt(self, hide=True):
        if self.ask_countdown_after_id:
            try:
                self.after_cancel(self.ask_countdown_after_id)
            except Exception:
                pass
            self.ask_countdown_after_id = None
        self.ask_active = False
        self.ask_program = None
        self.ask_target = None
        if hide and self.is_mini and self.winfo_viewable():
            self.hide_to_tray()

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
