import json
import os
import subprocess
import threading
import time
from tkinter import filedialog, messagebox

import customtkinter as ctk
import psutil
import pystray
import win32con
import win32gui
import win32process
import win32ui
from PIL import Image, ImageDraw


CONFIG_FILE = "config.json"
CHECK_INTERVAL_SECONDS = 5
ASK_TIMEOUT_SECONDS = 15
MINI_WIDTH = 420
MINI_HEIGHT = 94


def get_icon_from_exe(exe_path, size=32):
    try:
        if not exe_path or not os.path.exists(exe_path):
            return None

        large_icons, small_icons = win32gui.ExtractIconEx(exe_path, 0)
        icons = small_icons or large_icons
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


class AutoAudioApp(ctk.CTk):
    def __init__(self):
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
        self.tray = None
        self.audio_device_names = self.get_output_device_names()

        self.title("Auto Audio Switcher")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        self.set_ui_mode("mini")
        self.draw_ui()
        self.withdraw()
        self.start_tray()

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def default_config(self):
        return {
            "headset_name": "Headset",
            "speaker_name": "Speakers",
            "auto_list": [],
            "ask_list": [],
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
            self.set_mini_geometry()
        else:
            self.is_mini = False
            self.overrideredirect(False)
            self.geometry("560x760+720+120")

    def set_mini_geometry(self, extra_height=0):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        height = MINI_HEIGHT + extra_height
        x = max(0, screen_width - MINI_WIDTH - 16)
        y = max(0, screen_height - height - 70)
        self.geometry(f"{MINI_WIDTH}x{height}+{x}+{y}")

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
        for widget in self.winfo_children():
            widget.destroy()

        if self.is_mini:
            self.draw_mini_ui()
        else:
            self.draw_settings_ui()

    def draw_mini_ui(self):
        self.configure(fg_color="#171717")

        header = ctk.CTkFrame(self, fg_color="#101010", height=28, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        header.bind("<ButtonPress-1>", self.start_move)
        header.bind("<B1-Motion>", self.do_move)

        ctk.CTkLabel(header, text="Auto Audio", font=("Segoe UI", 11, "bold"), text_color="#D7D7D7").pack(side="left", padx=12)
        ctk.CTkButton(header, text="x", width=28, height=24, fg_color="transparent", hover_color="#333333", command=self.hide_to_tray).pack(side="right", padx=(0, 4))
        ctk.CTkButton(header, text="-", width=28, height=24, fg_color="transparent", hover_color="#333333", command=self.hide_to_tray).pack(side="right", padx=2)
        ctk.CTkButton(header, text="Settings", width=70, height=24, fg_color="transparent", hover_color="#333333", command=lambda: self.switch_mode("settings")).pack(side="right", padx=4)

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

        self.speaker_btn = ctk.CTkButton(button_frame, text="SPK", width=52, height=42, corner_radius=8, font=("Segoe UI", 12, "bold"), command=lambda: self.manual_set_audio("speaker"))
        self.speaker_btn.pack(side="left", padx=(0, 6))

        self.headset_btn = ctk.CTkButton(button_frame, text="HDS", width=52, height=42, corner_radius=8, font=("Segoe UI", 12, "bold"), command=lambda: self.manual_set_audio("headset"))
        self.headset_btn.pack(side="left")

        self.update_mini_buttons_ui(self.last_state)

    def draw_settings_ui(self):
        self.configure(fg_color="#171717")
        self.audio_device_names = self.get_output_device_names()
        device_options = self.build_device_options()

        ctk.CTkLabel(self, text="Auto Audio Settings", font=("Segoe UI", 22, "bold"), text_color="white").pack(pady=(22, 14))

        device_frame = ctk.CTkFrame(self, fg_color="transparent")
        device_frame.pack(fill="x", padx=18)

        self.create_device_box(device_frame, "Speaker", "speaker", device_options).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.create_device_box(device_frame, "Headset", "headset", device_options).pack(side="left", fill="x", expand=True, padx=(6, 0))

        ctk.CTkLabel(self, text="Program Rules", font=("Segoe UI", 16, "bold"), text_color="white").pack(anchor="w", padx=22, pady=(20, 8))
        self.create_list_ui("Auto Change", "auto_list")
        self.create_list_ui("Ask Before Change", "ask_list")

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=18, pady=18)
        ctk.CTkButton(bottom, text="Save and Mini Mode", height=42, fg_color="#2563EB", hover_color="#1D4ED8", command=self.save_and_close).pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(bottom, text="Hide", height=42, fg_color="#333333", hover_color="#444444", command=self.hide_to_tray).pack(side="left", fill="x", expand=True, padx=(6, 0))

    def build_device_options(self):
        options = [name for name in self.audio_device_names if name]
        for key in ("speaker_name", "headset_name"):
            name = self.config_data.get(key)
            if name and name not in options:
                options.insert(0, name)
        return options or ["No audio device found"]

    def create_device_box(self, parent, title, mode, device_options):
        frame = ctk.CTkFrame(parent, fg_color="#242424", corner_radius=8)
        ctk.CTkButton(frame, text=title, height=36, fg_color="#3B82F6" if mode == "speaker" else "#374151", hover_color="#2563EB", command=lambda: self.manual_set_audio(mode)).pack(fill="x", padx=10, pady=(10, 8))

        variable = ctk.StringVar(value=self.config_data.get(f"{mode}_name") if self.config_data.get(f"{mode}_name") in device_options else device_options[0])
        if mode == "speaker":
            self.sp_var = variable
        else:
            self.hs_var = variable

        ctk.CTkOptionMenu(frame, values=device_options, variable=variable, width=210, height=30).pack(fill="x", padx=10, pady=(0, 10))
        return frame

    def create_list_ui(self, title, key):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(8, 0))
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 13, "bold"), text_color="#CFCFCF").pack(side="left")
        ctk.CTkButton(header, text="Add EXE", width=78, height=26, fg_color="#333333", hover_color="#444444", command=lambda: self.add_exe_program(key)).pack(side="right", padx=(6, 0))
        ctk.CTkButton(header, text="Running", width=82, height=26, fg_color="#333333", hover_color="#444444", command=lambda: self.open_running_program_picker(key)).pack(side="right", padx=(6, 0))
        ctk.CTkButton(header, text="Active", width=74, height=26, fg_color="#333333", hover_color="#444444", command=lambda: self.add_active_window_program(key)).pack(side="right")

        scroll = ctk.CTkScrollableFrame(self, height=152, fg_color="#101010", border_width=1, border_color="#2A2A2A", corner_radius=8)
        scroll.pack(fill="x", padx=18, pady=(6, 8))

        programs = self.config_data[key]
        if not programs:
            ctk.CTkLabel(scroll, text="No programs yet", text_color="#777777", height=40).pack(fill="x")
            return

        for program in programs:
            item = ctk.CTkFrame(scroll, fg_color="#1C1C1C", corner_radius=6)
            item.pack(fill="x", pady=4, padx=4)

            icon = get_icon_from_exe(program.get("path"), size=24)
            ctk.CTkLabel(item, text="" if icon else "APP", image=icon, width=34, height=34, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(8, 4), pady=5)

            label_text = program.get("name", "Unknown")
            detail = f"{program.get('match_type', 'process_name')}: {program.get('value', '')}"
            text_box = ctk.CTkFrame(item, fg_color="transparent")
            text_box.pack(side="left", fill="x", expand=True, padx=4)
            ctk.CTkLabel(text_box, text=label_text, font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            ctk.CTkLabel(text_box, text=detail, font=("Segoe UI", 10), text_color="#8F8F8F", anchor="w").pack(fill="x")

            ctk.CTkButton(item, text="Del", width=42, height=26, fg_color="#5B1F1F", hover_color="#7F1D1D", command=lambda p=program, k=key: self.remove_program(k, p)).pack(side="right", padx=(4, 8))
            ctk.CTkButton(item, text="HDS", width=42, height=26, fg_color=self.target_color(program, "headset"), hover_color="#2563EB", command=lambda p=program, k=key: self.set_program_target(k, p, "headset")).pack(side="right", padx=4)
            ctk.CTkButton(item, text="SPK", width=42, height=26, fg_color=self.target_color(program, "speaker"), hover_color="#2563EB", command=lambda p=program, k=key: self.set_program_target(k, p, "speaker")).pack(side="right", padx=4)

    def target_color(self, program, mode):
        return "#2563EB" if program.get("target_audio") == mode else "#3A3A3A"

    def switch_mode(self, target):
        self.set_ui_mode(target)
        self.draw_ui()
        self.deiconify()
        self.lift()

    def start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def do_move(self, event):
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def audio_label(self, state):
        return "Headset" if state == "headset" else "Speaker"

    def update_mini_buttons_ui(self, state):
        if hasattr(self, "speaker_btn") and self.speaker_btn.winfo_exists():
            active = "#2563EB"
            inactive = "#424242"
            self.speaker_btn.configure(fg_color=active if state == "speaker" else inactive)
            self.headset_btn.configure(fg_color=active if state == "headset" else inactive)
        if hasattr(self, "mini_state_label") and self.mini_state_label.winfo_exists():
            self.mini_state_label.configure(text=f"Output: {self.audio_label(state)}")

    def update_detect_ui(self, name, icon=None):
        self.current_detected_name = name
        self.current_detected_icon = icon
        if hasattr(self, "mini_name_label") and self.mini_name_label.winfo_exists():
            shown = name[:24] + ".." if len(name) > 26 else name
            self.mini_name_label.configure(text=shown)
        if hasattr(self, "mini_icon_label") and self.mini_icon_label.winfo_exists():
            self.mini_icon_label.configure(image=icon, text="" if icon else "APP")

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
        nircmd_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nircmd.exe")
        if not os.path.exists(nircmd_path):
            return False
        try:
            for role in ("0", "1", "2"):
                subprocess.run([nircmd_path, "setdefaultsounddevice", target, role], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as exc:
            print(f"nircmd audio switch failed: {exc}")
            return False

    def save_and_close(self):
        self.config_data["speaker_name"] = self.sp_var.get()
        self.config_data["headset_name"] = self.hs_var.get()
        self.save_config()
        self.switch_mode("mini")

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
        picker.geometry("620x540+650+180")
        picker.attributes("-topmost", True)
        picker.transient(self)

        ctk.CTkLabel(picker, text="Running Programs", font=("Segoe UI", 18, "bold")).pack(pady=(18, 8))
        scroll = ctk.CTkScrollableFrame(picker, fg_color="#101010", corner_radius=8)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        processes = self.list_running_programs()
        if not processes:
            ctk.CTkLabel(scroll, text="No selectable programs found", text_color="#888888").pack(pady=20)
            return

        for program in processes:
            row = ctk.CTkFrame(scroll, fg_color="#1C1C1C", corner_radius=6)
            row.pack(fill="x", padx=4, pady=4)
            ctk.CTkLabel(row, text=program["name"], font=("Segoe UI", 12, "bold"), anchor="w").pack(side="left", fill="x", expand=True, padx=10, pady=8)
            ctk.CTkButton(row, text="Add", width=62, height=28, command=lambda p=program: self.pick_running_program(key, p, picker)).pack(side="right", padx=8)

    def list_running_programs(self):
        seen = set()
        results = []
        for process in psutil.process_iter(["name", "exe"]):
            try:
                name = process.info.get("name")
                if not name or name in seen:
                    continue
                path = process.info.get("exe") or ""
                seen.add(name)
                results.append({"name": name, "path": path})
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
        self.draw_ui()

    def remove_program(self, key, program):
        self.config_data[key] = [item for item in self.config_data[key] if item is not program]
        self.save_config()
        self.draw_ui()

    def monitor_loop(self):
        while self.is_running:
            found = self.find_matching_program()
            if found:
                list_key, program, process_path = found
                icon = get_icon_from_exe(process_path or program.get("path"), size=40)
                target = program.get("target_audio", "headset")
                self.after(0, lambda p=program, i=icon: self.update_detect_ui(p.get("name", "Unknown"), i))

                if list_key == "ask_list":
                    self.after(0, lambda p=program: self.show_ask_prompt(p))
                elif self.last_state != target:
                    self.manual_override = False
                    self.set_audio(target)
                    self.last_state = target
                    self.after(0, lambda t=target: self.update_mini_buttons_ui(t))
                else:
                    self.manual_override = False
            else:
                self.pending_prompt_key = None
                if self.last_state == "headset" and not self.manual_override:
                    self.set_audio("speaker")
                    self.last_state = "speaker"
                    self.after(0, lambda: self.update_mini_buttons_ui("speaker"))
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
        self.switch_mode("mini")
        self.deiconify()
        self.lift()
        self.set_mini_geometry(extra_height=44)

        if hasattr(self, "ask_frame") and self.ask_frame.winfo_exists():
            self.ask_frame.destroy()
        if self.is_mini:
            self.set_mini_geometry()

        self.ask_remaining = ASK_TIMEOUT_SECONDS
        self.ask_frame = ctk.CTkFrame(self, fg_color="#262626", corner_radius=0)
        self.ask_frame.pack(fill="x", side="bottom")
        self.ask_label = ctk.CTkLabel(self.ask_frame, text="", font=("Segoe UI", 11), text_color="white")
        self.ask_label.pack(side="left", padx=10, pady=6)
        ctk.CTkButton(self.ask_frame, text="Yes", width=48, height=26, command=lambda: self.accept_ask_prompt(target)).pack(side="right", padx=(4, 8), pady=6)
        ctk.CTkButton(self.ask_frame, text="No", width=44, height=26, fg_color="#444444", hover_color="#555555", command=self.dismiss_ask_prompt).pack(side="right", padx=4, pady=6)
        self.tick_ask_prompt(program, target)

    def tick_ask_prompt(self, program, target):
        if not hasattr(self, "ask_frame") or not self.ask_frame.winfo_exists():
            return
        self.ask_label.configure(text=f"{program.get('name', 'Program')} -> {self.audio_label(target)}? {self.ask_remaining}s")
        if self.ask_remaining <= 0:
            self.dismiss_ask_prompt()
            return
        self.ask_remaining -= 1
        self.ask_countdown_after_id = self.after(1000, lambda: self.tick_ask_prompt(program, target))

    def accept_ask_prompt(self, target):
        self.set_audio(target)
        self.last_state = target
        self.manual_override = False
        self.update_mini_buttons_ui(target)
        self.dismiss_ask_prompt()

    def dismiss_ask_prompt(self):
        if self.ask_countdown_after_id:
            try:
                self.after_cancel(self.ask_countdown_after_id)
            except Exception:
                pass
            self.ask_countdown_after_id = None
        if hasattr(self, "ask_frame") and self.ask_frame.winfo_exists():
            self.ask_frame.destroy()

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
    app = AutoAudioApp()
    app.mainloop()
