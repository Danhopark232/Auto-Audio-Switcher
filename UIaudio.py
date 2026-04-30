import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import os
import psutil
import threading
import time
import json
from PIL import Image
import win32gui
import win32ui
import win32con
import pystray

# --- 설정 파일 경로 ---
CONFIG_FILE = "config.json"

# --- 아이콘 추출 함수 ---
def get_icon_from_exe(exe_path, size=32):
    try:
        if not exe_path or not os.path.exists(exe_path): return None
        ico_x, ico_y = win32gui.ExtractIconEx(exe_path, 0)
        if not ico_x: return None
        
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, size, size)
        hdc = hdc.CreateCompatibleDC()
        hdc.SelectObject(hbmp)
        
        win32gui.DrawIconEx(hdc.GetSafeHdc(), 0, 0, ico_x[0], size, size, 0, 0, win32con.DI_NORMAL)
        win32gui.DestroyIcon(ico_x[0])
        for h in ico_y: win32gui.DestroyIcon(h)
        
        bmpinfo = hbmp.GetInfo()
        bmpstr = hbmp.GetBitmapBits(True)
        img = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except:
        return None

class AutoAudioApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. 초기 데이터 로드
        self.load_config()
        self.is_mini = True
        self.is_running = True
        self.last_state = "speaker"  # 기본값 스피커 시작
        self.audio_device_names = self.get_output_device_names()

        # 2. 메인 윈도우 기본 설정
        self.title("Auto Audio")
        self.attributes("-topmost", True)  # 항상 위 설정
        self.set_ui_mode("mini")

        # 3. UI 그리기
        self.draw_ui()

        # 4. 감시 스레드 시작
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

        # 종료 시 트레이로 숨기기 설정
        self.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

    # --- 설정 관리 ---
    def load_config(self):
        default_config = {
            "headset_name": "Artics 7+",
            "speaker_name": "2 - Pebble V2",
            "auto_list": {},
            "ask_list": {}
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
                    # 누락된 키 보강
                    for key, val in default_config.items():
                        if key not in self.config: self.config[key] = val
            except:
                self.config = default_config
        else:
            self.config = default_config

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    # --- UI 모드 제어 ---
    def set_ui_mode(self, mode):
        if mode == "mini":
            self.is_mini = True
            self.overrideredirect(True) # 타이틀바 제거
            # 1920x1080 기준 우측 하단 배치
            self.geometry("380x85+1530+940")
        else:
            self.is_mini = False
            self.overrideredirect(False) # 타이틀바 복구
            self.geometry("420x700+750+150") # 중앙 배치

    def get_output_device_names(self):
        try:
            import warnings
            warnings.filterwarnings("ignore")
            from pycaw.pycaw import AudioUtilities

            output_devices = []
            for dev in AudioUtilities.GetAllDevices():
                try:
                    if AudioUtilities.GetEndpointDataFlow(dev.id) == "eRender":
                        name = getattr(dev, "FriendlyName", None) or getattr(dev, "friendly_name", None)
                        if name and name not in output_devices:
                            output_devices.append(name)
                except:
                    pass
            return output_devices
        except:
            return []

    def adjust_settings_geometry(self):
        self.update_idletasks()
        width = max(self.winfo_reqwidth(), 420)
        height = min(self.winfo_reqheight(), self.winfo_screenheight() - 100)
        x = min(750, self.winfo_screenwidth() - width)
        y = min(150, self.winfo_screenheight() - height)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def start_move(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def do_move(self, event):
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def draw_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        if self.is_mini:
            self.draw_mini_ui()
        else:
            self.draw_settings_ui()
            self.after(0, self.adjust_settings_geometry)

    # --- [UI] 미니 모드 레이아웃 ---
    def draw_mini_ui(self):
        self.configure(fg_color="#1A1A1A")
        
        # 헤더 바
        header = ctk.CTkFrame(self, fg_color="#121212", height=28, corner_radius=0)
        header.pack(fill="x")
        header.bind("<ButtonPress-1>", self.start_move)
        header.bind("<B1-Motion>", self.do_move)
        ctk.CTkLabel(header, text="■ Auto Audio", font=("Arial", 11), text_color="#CCCCCC").pack(side="left", padx=12)
        ctk.CTkButton(header, text="✕", width=25, height=25, fg_color="transparent", hover_color="#333333",
                      command=self.hide_to_tray).pack(side="right", padx=(0, 5))
        ctk.CTkButton(header, text="_", width=25, height=25, fg_color="transparent", hover_color="#333333",
                      command=self.iconify).pack(side="right", padx=(0, 5))
        ctk.CTkButton(header, text="⚙", width=25, height=25, fg_color="transparent", hover_color="#333333",
                      command=lambda: self.switch_mode("settings")).pack(side="right", padx=5)

        # 정보 컨텐츠
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=15)

        self.mini_icon_label = ctk.CTkLabel(content, text="🔍", width=45, height=45, font=("Arial", 20))
        self.mini_icon_label.pack(side="left")

        self.mini_name_label = ctk.CTkLabel(content, text="No Program", font=("Pretendard", 15, "bold"), text_color="white")
        self.mini_name_label.pack(side="left", padx=15)

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(side="right")

        self.speaker_btn = ctk.CTkButton(btn_frame, text="🔊", width=45, height=45, corner_radius=25,
                                         font=("Arial", 18), command=lambda: self.manual_set_audio("speaker"))
        self.speaker_btn.pack(side="left", padx=(0, 5))

        self.headset_btn = ctk.CTkButton(btn_frame, text="🎧", width=45, height=45, corner_radius=25,
                                         font=("Arial", 18), command=lambda: self.manual_set_audio("headset"))
        self.headset_btn.pack(side="left")

        self.update_mini_buttons_ui(self.last_state)

    # --- [UI] 상세 설정창 레이아웃 ---
    def draw_settings_ui(self):
        self.configure(fg_color="#1A1A1A")
        
        ctk.CTkLabel(self, text="Audio Setting", font=("Pretendard", 22, "bold"), text_color="white").pack(pady=(25, 15))

        self.audio_device_names = self.get_output_device_names()
        device_options = [name for name in self.audio_device_names if name]
        if self.config["headset_name"] and self.config["headset_name"] not in device_options:
            device_options.insert(0, self.config["headset_name"])
        if self.config["speaker_name"] and self.config["speaker_name"] not in device_options:
            device_options.insert(0, self.config["speaker_name"])
        if not device_options:
            device_options = ["No audio device found"]

        # 장치 설정 영역
        dev_frame = ctk.CTkFrame(self, fg_color="transparent")
        dev_frame.pack(fill="x", padx=20)

        # 헤드셋 박스
        hs_box = ctk.CTkFrame(dev_frame, fg_color="#2B2B2B", width=180, height=90)
        hs_box.pack(side="left", expand=True, padx=5)
        ctk.CTkLabel(hs_box, text="🎧 Headset", font=("Arial", 12)).pack(pady=5)
        self.hs_var = ctk.StringVar(value=self.config["headset_name"] if self.config["headset_name"] in device_options else device_options[0])
        self.hs_menu = ctk.CTkOptionMenu(hs_box, values=device_options, variable=self.hs_var, width=150, height=28)
        self.hs_menu.pack(pady=5)

        # 스피커 박스 (이미지처럼 파란색 강조)
        sp_box = ctk.CTkFrame(dev_frame, fg_color="#3B8ED0", width=180, height=90)
        sp_box.pack(side="left", expand=True, padx=5)
        ctk.CTkLabel(sp_box, text="🔊 Speaker", font=("Arial", 12, "bold"), text_color="white").pack(pady=5)
        self.sp_var = ctk.StringVar(value=self.config["speaker_name"] if self.config["speaker_name"] in device_options else device_options[0])
        self.sp_menu = ctk.CTkOptionMenu(sp_box, values=device_options, variable=self.sp_var, width=150, height=28)
        self.sp_menu.pack(pady=5)

        # 프로그램 리스트 타이틀
        ctk.CTkLabel(self, text="Program List", font=("Pretendard", 16, "bold")).pack(anchor="w", padx=25, pady=(25, 5))

        # 리스트 섹션 생성
        self.create_list_ui("Auto Change", self.config["auto_list"])
        self.create_list_ui("Ask Before Change", self.config["ask_list"])

        # 하단 저장 버튼
        ctk.CTkButton(self, text="저장 후 미니모드 전환", font=("Pretendard", 14, "bold"), height=45,
                      fg_color="#333333", hover_color="#444444", command=self.save_and_close).pack(side="bottom", fill="x", padx=30, pady=25)

    def create_list_ui(self, title, data_dict):
        ctk.CTkLabel(self, text=f"• {title}", font=("Arial", 12), text_color="#888888").pack(anchor="w", padx=25)
        
        scroll = ctk.CTkScrollableFrame(self, height=140, fg_color="#121212", border_width=1, border_color="#252525")
        scroll.pack(fill="x", padx=20, pady=5)

        for name, path in data_dict.items():
            item = ctk.CTkFrame(scroll, fg_color="transparent")
            item.pack(fill="x", pady=3)
            
            icon = get_icon_from_exe(path, size=24)
            ctk.CTkLabel(item, text="", image=icon if icon else None).pack(side="left", padx=5)
            ctk.CTkLabel(item, text=name, font=("Arial", 12)).pack(side="left", padx=5)
            
            ctk.CTkButton(item, text="移除", width=40, height=22, fg_color="#442222", hover_color="#662222",
                          command=lambda n=name, t=title: self.remove_prog(t, n)).pack(side="right", padx=5)

        ctk.CTkButton(self, text="⊕ Add Program", height=32, fg_color="#252525", hover_color="#333333",
                      command=lambda t=title: self.add_prog(t)).pack(fill="x", padx=25, pady=(0, 15))

    # --- 로직 함수 (안전성 강화) ---
    def switch_mode(self, target):
        self.set_ui_mode(target)
        self.draw_ui()

    def update_mini_buttons_ui(self, state):
        """Active mini mode button styling."""
        if hasattr(self, 'speaker_btn') and self.speaker_btn.winfo_exists() and \
           hasattr(self, 'headset_btn') and self.headset_btn.winfo_exists():
            try:
                if state == "headset":
                    self.headset_btn.configure(fg_color="#3B82F6", hover_color="#2563EB", text_color="white")
                    self.speaker_btn.configure(fg_color="#555555", hover_color="#666666", text_color="white")
                else:
                    self.speaker_btn.configure(fg_color="#3B82F6", hover_color="#2563EB", text_color="white")
                    self.headset_btn.configure(fg_color="#555555", hover_color="#666666", text_color="white")
            except: pass

    def update_detect_ui(self, name, icon=None):
        """라벨 존재 여부 확인 후 업데이트 (에러 방지)"""
        if hasattr(self, 'mini_name_label') and self.mini_name_label.winfo_exists():
            try:
                self.mini_name_label.configure(text=name[:15] + ".." if len(name)>15 else name)
                if hasattr(self, 'mini_icon_label') and self.mini_icon_label.winfo_exists():
                    self.mini_icon_label.configure(image=icon if icon else None, text="" if icon else "🔍")
            except: pass

    def manual_set_audio(self, mode):
        self.set_audio(mode)
        self.last_state = mode
        self.update_mini_buttons_ui(mode)

    def set_audio(self, mode):
        target = self.config["headset_name"] if mode == "headset" else self.config["speaker_name"]
        try:
            subprocess.run(["nircmd.exe", "setdefaultsounddevice", target], shell=True)
        except: pass

    def save_and_close(self):
        self.config["headset_name"] = self.hs_var.get()
        self.config["speaker_name"] = self.sp_var.get()
        self.save_config()
        self.switch_mode("mini")

    def add_prog(self, title):
        path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
        if path:
            name = os.path.basename(path)
            key = "auto_list" if title == "Auto Change" else "ask_list"
            self.config[key][name] = path
            self.save_config()
            self.draw_ui()

    def remove_prog(self, title, name):
        key = "auto_list" if title == "Auto Change" else "ask_list"
        if name in self.config[key]:
            del self.config[key][name]
            self.save_config()
            self.draw_ui()

    def monitor_loop(self):
        while self.is_running:
            found_name, found_path, is_ask = None, None, False
            
            # 프로세스 스캔
            try:
                for proc in psutil.process_iter(['name', 'exe']):
                    name = proc.info['name']
                    if name in self.config["auto_list"]:
                        found_name, found_path, is_ask = name, proc.info['exe'], False
                        break
                    elif name in self.config["ask_list"]:
                        found_name, found_path, is_ask = name, proc.info['exe'], True
                        break
            except: pass

            if found_name:
                icon = get_icon_from_exe(found_path, size=40)
                if is_ask:
                    if self.last_state != "headset":
                        # 질문 모드는 메인 쓰레드에서 팝업 실행
                        self.after(0, lambda n=found_name: self.ask_switch(n))
                else:
                    if self.last_state != "headset":
                        self.set_audio("headset")
                        self.last_state = "headset"
                        self.after(0, lambda: self.update_mini_buttons_ui("headset"))
                
                self.after(0, lambda n=found_name, i=icon: self.update_detect_ui(n, i))
            else:
                if self.last_state == "headset":
                    self.set_audio("speaker")
                    self.last_state = "speaker"
                    self.after(0, lambda: self.update_mini_buttons_ui("speaker"))
                self.after(0, lambda: self.update_detect_ui("No Program", None))

            time.sleep(5)

    def ask_switch(self, prog_name):
        if messagebox.askyesno("Audio Switch", f"[{prog_name}] 감지됨.\n헤드셋으로 전환할까요?"):
            self.set_audio("headset")
            self.last_state = "headset"
            self.update_mini_buttons_ui("headset")

    # --- 트레이 아이콘 기능 ---
    def hide_to_tray(self):
        self.withdraw()
        image = Image.new('RGB', (64, 64), color=(30, 30, 30)) # 임시 로고
        menu = pystray.Menu(pystray.MenuItem('열기', self.show_app), pystray.MenuItem('종료', self.quit_app))
        self.tray = pystray.Icon("AutoAudio", image, "Auto Audio Switcher", menu)
        threading.Thread(target=self.tray.run, daemon=True).start()

    def show_app(self):
        self.tray.stop()
        self.after(0, self.deiconify)

    def quit_app(self):
        self.is_running = False
        if hasattr(self, 'tray'): self.tray.stop()
        self.destroy()

if __name__ == "__main__":
    app = AutoAudioApp()
    app.mainloop()