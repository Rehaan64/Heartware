import os
import sys

# --- PYINSTALLER TCL/TK FIX ---
# This forces the bundled executable to locate its Tcl/Tk libraries dynamically.
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    for folder in ['tcl_data', 'tcl']:
        tcl_path = os.path.join(base_path, folder)
        if os.path.exists(tcl_path):
            os.environ['TCL_LIBRARY'] = tcl_path
            break
    for folder in ['tk_data', 'tk']:
        tk_path = os.path.join(base_path, folder)
        if os.path.exists(tk_path):
            os.environ['TK_LIBRARY'] = tk_path
            break
# -----------------------------

import threading
import time
import tkinter as tk
from tkinter import ttk
import datetime
import random
import psutil

# Configuration Constants
COLLAPSED_SIZE = 80
EXPANDED_WIDTH = 260
EXPANDED_HEIGHT = 180

THEMES = {
    "Default": {"bg": "#111827", "text": "white", "sub": "#9ca3af", "border": None},
    "Cyberpunk": {"bg": "#0f051d", "text": "#f3e8ff", "sub": "#c084fc", "border": "#d946ef"},
    "Matrix": {"bg": "#022c22", "text": "#d1fae5", "sub": "#6ee7b7", "border": "#10b981"}
}


class SettingsWindow:
    """Control Center GUI to customize settings before launching."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Heartware")
        self.root.geometry("320x340")
        self.root.resizable(False, False)

        self.root.configure(bg="#1f2937")
        style = ttk.Style()
        style.theme_use("clam")

        title_label = tk.Label(self.root, text="Heartware Settings", bg="#1f2937", fg="white",
                               font=("Helvetica", 12, "bold"))
        title_label.pack(pady=15)

        self.face_var = tk.BooleanVar(value=True)
        self.glitch_var = tk.BooleanVar(value=True)
        self.time_var = tk.BooleanVar(value=True)
        self.theme_var = tk.StringVar(value="Default")

        frame = tk.Frame(self.root, bg="#1f2937")
        frame.pack(padx=20, anchor="w")

        tk.Checkbutton(frame, text="Enable Tamagotchi Face", variable=self.face_var, bg="#1f2937", fg="white",
                       selectcolor="#374151", activebackground="#1f2937", activeforeground="white").pack(anchor="w",
                                                                                                         pady=5)
        tk.Checkbutton(frame, text="Enable Stress Glitch Effect", variable=self.glitch_var, bg="#1f2937", fg="white",
                       selectcolor="#374151", activebackground="#1f2937", activeforeground="white").pack(anchor="w",
                                                                                                         pady=5)
        tk.Checkbutton(frame, text="Enable Time-Aware Moods", variable=self.time_var, bg="#1f2937", fg="white",
                       selectcolor="#374151", activebackground="#1f2937", activeforeground="white").pack(anchor="w",
                                                                                                         pady=5)

        theme_frame = tk.Frame(self.root, bg="#1f2937")
        theme_frame.pack(pady=15, padx=20, fill="x")
        tk.Label(theme_frame, text="Starting Skin/Theme:", bg="#1f2937", fg="#9ca3af", font=("Helvetica", 9)).pack(
            anchor="w")

        theme_dropdown = ttk.Combobox(theme_frame, textvariable=self.theme_var, values=list(THEMES.keys()),
                                      state="readonly")
        theme_dropdown.pack(fill="x", pady=5)

        launch_btn = tk.Button(self.root, text="Launch Heartware", command=self.launch_widget, bg="#3b82f6", fg="white",
                               font=("Helvetica", 10, "bold"), relief="flat", cursor="hand2")
        launch_btn.pack(pady=10, ipadx=10, ipady=5)

    def launch_widget(self):
        config = {
            "face": self.face_var.get(),
            "glitch": self.glitch_var.get(),
            "time": self.time_var.get(),
            "theme": self.theme_var.get()
        }
        self.root.destroy()

        widget_root = tk.Tk()
        HeartwareApp(widget_root, config)
        widget_root.mainloop()


class HeartwareApp:
    def __init__(self, root, config):
        self.root = root
        self.config = config
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.93)

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.x_pos = screen_width - COLLAPSED_SIZE - 40
        self.y_pos = screen_height - COLLAPSED_SIZE - 60
        self.root.geometry(f"{COLLAPSED_SIZE}x{COLLAPSED_SIZE}+{self.x_pos}+{self.y_pos}")

        self.canvas = tk.Canvas(root, width=EXPANDED_WIDTH, height=EXPANDED_HEIGHT, bg='black', highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        try:
            self.root.attributes("-transparentcolor", "black")
        except Exception:
            pass

        self.bpm = 60
        self.load_score = 0
        self.cpu_usage = 0
        self.ram_usage = 0
        self.temp_val = 45.0
        self.mood = "Chill"
        self.face = "( _ )"
        self.animating = True
        self.expanded = False
        self.copy_notification = False

        self.theme_names = list(THEMES.keys())
        self.current_theme_idx = self.theme_names.index(config["theme"]) if config["theme"] in THEMES else 0

        self.drag_data = {"x": 0, "y": 0}
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Double-Button-1>", self.cycle_theme)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<Escape>", lambda e: self.quit_app())

        # Start background threads for system monitoring and hover checking
        threading.Thread(target=self.monitor_system, daemon=True).start()
        threading.Thread(target=self.check_hover_state, daemon=True).start()

        self.animate_pulse(radius=22, growing=True)

    def monitor_system(self):
        while self.animating:
            self.cpu_usage = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            self.ram_usage = mem.percent

            self.temp_val = 45.0
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    core_temps = [e.current for entries in temps.values() for e in entries if e.current]
                    if core_temps:
                        self.temp_val = sum(core_temps) / len(core_temps)
            except Exception:
                pass

            temp_score = max(0, min(100, (self.temp_val - 40) / 45 * 100))
            self.load_score = (self.cpu_usage * 0.4) + (self.ram_usage * 0.4) + (temp_score * 0.2)
            self.bpm = int(60 + (self.load_score * 1.0))

            current_hour = datetime.datetime.now().hour
            uptime_hours = (time.time() - psutil.boot_time()) / 3600

            is_late_night = (current_hour >= 23 or current_hour < 5)

            if self.config["time"] and uptime_hours > 6 and self.load_score > 50:
                self.mood = "Cranky (Rest Needed)"
                self.face = "(>_<)"
            elif self.config["time"] and is_late_night:
                if self.load_score > 40:
                    self.mood = "Insomnia"
                    self.face = "(@_@)"
                else:
                    self.mood = "Sleepy Late-Night"
                    self.face = "(-_-) zzz"
            else:
                if self.load_score < 30:
                    self.mood = "Chill"
                    self.face = "(^_^) ~"
                elif self.load_score < 60:
                    self.mood = "Focused"
                    self.face = "(o_o) .."
                elif self.load_score < 85:
                    self.mood = "Sweating"
                    self.face = "(#_#) ;;"
                else:
                    self.mood = "Exhausted"
                    self.face = "(X_X)"

    def check_hover_state(self):
        while self.animating:
            try:
                mx = self.root.winfo_pointerx()
                my = self.root.winfo_pointery()

                current_w = EXPANDED_WIDTH if self.expanded else COLLAPSED_SIZE
                current_h = EXPANDED_HEIGHT if self.expanded else COLLAPSED_SIZE

                in_bounds = (self.x_pos <= mx <= self.x_pos + current_w) and (
                            self.y_pos <= my <= self.y_pos + current_h)

                if in_bounds and not self.expanded:
                    self.expanded = True
                    self.root.after(0, self.update_window_geometry)
                elif not in_bounds and self.expanded:
                    self.expanded = False
                    self.root.after(0, self.update_window_geometry)
            except Exception:
                pass
            time.sleep(0.1)

    def get_color(self):
        score = min(100, max(0, self.load_score))
        if score < 40:
            return "#3b82f6"
        elif score < 70:
            return "#f59e0b"
        else:
            return "#ef4444"

    def on_click(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def cycle_theme(self, event=None):
        self.current_theme_idx = (self.current_theme_idx + 1) % len(self.theme_names)

    def copy_status_log(self, event=None):
        log_text = f"[Heartware Status] Skin: {self.theme_names[self.current_theme_idx]} | Metabolism: {self.bpm} BPM | CPU: {self.cpu_usage}% | RAM: {self.ram_usage}% | Mood: {self.mood}"
        self.root.clipboard_clear()
        self.root.clipboard_append(log_text)
        self.copy_notification = True
        self.root.after(1500, lambda: setattr(self, 'copy_notification', False))

    def show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0, bg="#1f2937", fg="white", activebackground="#3b82f6", activeforeground="white")
        menu.add_command(label="Copy Log", command=self.copy_status_log)
        menu.add_command(label="Cycle Theme", command=self.cycle_theme)
        menu.add_separator()
        menu.add_command(label="Exit", command=self.quit_app)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def update_window_geometry(self):
        current_w = EXPANDED_WIDTH if self.expanded else COLLAPSED_SIZE
        current_h = EXPANDED_HEIGHT if self.expanded else COLLAPSED_SIZE
        self.root.geometry(f"{current_w}x{current_h}+{self.x_pos}+{self.y_pos}")

    def on_drag(self, event):
        deltax = event.x - self.drag_data["x"]
        deltay = event.y - self.drag_data["y"]
        self.x_pos += deltax
        self.y_pos += deltay
        self.update_window_geometry()

    def quit_app(self):
        self.animating = False
        self.root.destroy()

    def animate_pulse(self, radius, growing):
        if not self.animating:
            return

        self.canvas.delete("all")
        color = self.get_color()
        theme = THEMES[self.theme_names[self.current_theme_idx]]

        should_glitch = self.config["glitch"] and self.load_score > 90
        gx = random.randint(-2, 2) if should_glitch else 0
        gy = random.randint(-2, 2) if should_glitch else 0

        if not self.expanded:
            center = COLLAPSED_SIZE // 2
            self.canvas.create_oval(
                center - radius - 5, center - radius - 5,
                center + radius + 5, center + radius + 5,
                outline="", fill=color, stipple="gray25"
            )
            self.canvas.create_oval(
                center - radius, center - radius,
                center + radius, center + radius,
                outline="", fill=color
            )
            self.canvas.create_text(
                center, center,
                text=f"{self.bpm}\nBPM",
                fill="white",
                font=("Helvetica", 9, "bold"),
                justify="center"
            )
        else:
            border_color = theme["border"] if theme["border"] else color
            self.canvas.create_rectangle(
                5 + gx, 5 + gy, EXPANDED_WIDTH - 5 + gx, EXPANDED_HEIGHT - 5 + gy,
                outline=border_color, width=2, fill=theme["bg"]
            )

            if self.config["face"]:
                self.canvas.create_rectangle(
                    15 + gx, 15 + gy, 85 + gx, 55 + gy,
                    outline=color, width=1, fill="#000000"
                )
                self.canvas.create_text(
                    50 + gx, 35 + gy,
                    text=self.face, fill=color, font=("Courier", 10, "bold"), anchor="center"
                )
                text_x_offset = 95
            else:
                text_x_offset = 20

            self.canvas.create_text(
                text_x_offset + gx, 22 + gy,
                text=f"METABOLISM: {self.bpm} BPM",
                fill=theme["text"], font=("Helvetica", 9, "bold"), anchor="w"
            )
            self.canvas.create_text(
                text_x_offset + gx, 40 + gy,
                text=f"Skin: {self.theme_names[self.current_theme_idx]}",
                fill=theme["sub"], font=("Helvetica", 8), anchor="w"
            )

            self.canvas.create_text(
                20 + gx, 72 + gy,
                text=f"• CPU Load:  {self.cpu_usage}%",
                fill=theme["sub"], font=("Helvetica", 9), anchor="w"
            )
            self.canvas.create_text(
                20 + gx, 92 + gy,
                text=f"• RAM Use:   {self.ram_usage}%",
                fill=theme["sub"], font=("Helvetica", 9), anchor="w"
            )
            self.canvas.create_text(
                20 + gx, 112 + gy,
                text=f"• Temp:      {self.temp_val:.1f}°C",
                fill=theme["sub"], font=("Helvetica", 9), anchor="w"
            )
            self.canvas.create_text(
                20 + gx, 132 + gy,
                text=f"• Mood:      {self.mood}",
                fill=color, font=("Helvetica", 9, "bold"), anchor="w"
            )

            if self.copy_notification:
                self.canvas.create_rectangle(15, 155, EXPANDED_WIDTH - 15, EXPANDED_HEIGHT - 5, fill="#10b981",
                                             outline="")
                self.canvas.create_text(EXPANDED_WIDTH / 2, 166, text="Status Log Copied!", fill="white",
                                        font=("Helvetica", 8, "bold"))
            else:
                self.canvas.create_text(EXPANDED_WIDTH / 2, 166, text="Right-click for options",
                                        fill="#4b5563", font=("Helvetica", 7, "italic"))

        step = 1.2 if self.bpm < 90 else 2.5
        max_r = 26 if self.bpm < 90 else 32
        min_r = 16

        if growing:
            radius += step
            if radius >= max_r:
                growing = False
        else:
            radius -= step
            if radius <= min_r:
                growing = True

        delay = int(60000 / (self.bpm * 35))
        if self.animating:
            self.root.after(max(15, delay), lambda: self.animate_pulse(radius, growing))


if __name__ == "__main__":
    app = SettingsWindow()
    app.root.mainloop()