import tkinter as tk
from tkinter import messagebox
import time
import json
import os
from datetime import datetime

# ------------------------------
# 配置
# ------------------------------
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pomodoro_config.json")

DEFAULT_CONFIG = {
    "work_minutes": 25,
    "short_break_minutes": 5,
    "long_break_minutes": 15,
    "pomodoros_before_long_break": 4,
    "always_on_top": True,
    "theme": "dark",
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return {**DEFAULT_CONFIG, **cfg}
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ------------------------------
# 主题颜色
# ------------------------------
THEMES = {
    "dark": {
        "bg": "#1a1a2e",
        "card_bg": "#16213e",
        "fg": "#e0e0e0",
        "accent": "#e94560",
        "accent2": "#0f3460",
        "success": "#4ecca3",
        "warning": "#ffc107",
        "button_bg": "#0f3460",
        "button_fg": "#ffffff",
        "button_hover": "#1a4a7a",
        "progress_bg": "#2a2a4a",
        "progress_fg": "#e94560",
        "text_secondary": "#8888aa",
    },
    "light": {
        "bg": "#f5f5f5",
        "card_bg": "#ffffff",
        "fg": "#333333",
        "accent": "#e94560",
        "accent2": "#4a90d9",
        "success": "#2ecc71",
        "warning": "#f39c12",
        "button_bg": "#4a90d9",
        "button_fg": "#ffffff",
        "button_hover": "#357abd",
        "progress_bg": "#e0e0e0",
        "progress_fg": "#e94560",
        "text_secondary": "#999999",
    },
}

# ------------------------------
# 主应用
# ------------------------------
class PomodoroApp:
    def __init__(self):
        self.config = load_config()
        self.theme = THEMES[self.config.get("theme", "dark")]

        # 计时状态
        self.mode = "work"  # work, short_break, long_break
        self.remaining = self._get_mode_seconds()
        self.total_seconds = self.remaining
        self.running = False
        self.paused = False
        self.completed_pomodoros = 0
        self.session_history = []

        # 创建窗口
        self.root = tk.Tk()
        self.root.title("番茄钟")
        self.root.configure(bg=self.theme["bg"])
        self.root.resizable(False, False)

        # 置顶
        self.root.attributes("-topmost", self.config["always_on_top"])

        # 窗口居中
        win_w, win_h = 400, 580
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - win_w) // 2
        y = (sh - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self._build_ui()
        self._update_display()
        self._bind_events()

        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- 工具方法 ----
    def _get_mode_seconds(self):
        if self.mode == "work":
            return self.config["work_minutes"] * 60
        elif self.mode == "short_break":
            return self.config["short_break_minutes"] * 60
        else:
            return self.config["long_break_minutes"] * 60

    def _format_time(self, seconds):
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    # ---- UI 构建 ----
    def _build_ui(self):
        t = self.theme

        # 主容器
        self.main_frame = tk.Frame(self.root, bg=t["bg"])
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # 标题
        self.title_label = tk.Label(
            self.main_frame,
            text="🍅 番茄钟",
            font=("Segoe UI", 18, "bold"),
            bg=t["bg"],
            fg=t["fg"],
        )
        self.title_label.pack(pady=(0, 5))

        # 模式标签
        self.mode_label = tk.Label(
            self.main_frame,
            text=self._get_mode_name(),
            font=("Segoe UI", 12),
            bg=t["bg"],
            fg=t["accent"],
        )
        self.mode_label.pack(pady=(0, 15))

        # ---- 圆形进度 ----
        self.canvas = tk.Canvas(
            self.main_frame,
            width=260,
            height=260,
            bg=t["bg"],
            highlightthickness=0,
        )
        self.canvas.pack(pady=(0, 10))

        self.center_x = 130
        self.center_y = 130
        self.radius = 110

        # 背景圆
        self.canvas.create_oval(
            self.center_x - self.radius,
            self.center_y - self.radius,
            self.center_x + self.radius,
            self.center_y + self.radius,
            outline=t["progress_bg"],
            width=8,
        )

        # 进度弧（初始为完整圆）
        self.progress_arc = self.canvas.create_arc(
            self.center_x - self.radius,
            self.center_y - self.radius,
            self.center_x + self.radius,
            self.center_y + self.radius,
            start=90,
            extent=360,
            outline=t["progress_fg"],
            width=8,
            style="arc",
        )

        # 计时文字
        self.timer_text = self.canvas.create_text(
            self.center_x,
            self.center_y - 12,
            text=self._format_time(self.remaining),
            font=("Segoe UI", 48, "bold"),
            fill=t["fg"],
        )

        # 状态小字
        self.status_text = self.canvas.create_text(
            self.center_x,
            self.center_y + 40,
            text="就绪",
            font=("Segoe UI", 11),
            fill=t["text_secondary"],
        )

        # ---- 按钮区域 ----
        btn_frame = tk.Frame(self.main_frame, bg=t["bg"])
        btn_frame.pack(pady=5)

        # 开始/暂停
        self.start_btn = self._make_button(
            btn_frame, "▶  开始启动", self._toggle_start, t["success"], "#27ae60"
        )
        self.start_btn.pack(side="left", padx=5)

        # 重置
        self.reset_btn = self._make_button(
            btn_frame, "↻  重置", self._reset, t["warning"], "#d68910"
        )
        self.reset_btn.pack(side="left", padx=5)

        # 模式切换行
        mode_frame = tk.Frame(self.main_frame, bg=t["bg"])
        mode_frame.pack(pady=(10, 5))

        self.work_btn = self._make_small_button(
            mode_frame, "工作", lambda: self._switch_mode("work"), active=True
        )
        self.work_btn.pack(side="left", padx=3)

        self.short_btn = self._make_small_button(
            mode_frame, "短休", lambda: self._switch_mode("short_break"), active=False
        )
        self.short_btn.pack(side="left", padx=3)

        self.long_btn = self._make_small_button(
            mode_frame, "长休", lambda: self._switch_mode("long_break"), active=False
        )
        self.long_btn.pack(side="left", padx=3)

        # ---- 番茄计数 ----
        self.counter_frame = tk.Frame(self.main_frame, bg=t["bg"])
        self.counter_frame.pack(pady=(10, 5))

        self.tomato_label = tk.Label(
            self.counter_frame,
            text="",
            font=("Segoe UI", 14),
            bg=t["bg"],
            fg=t["accent"],
        )
        self.tomato_label.pack()

        # ---- 设置按钮 ----
        settings_frame = tk.Frame(self.main_frame, bg=t["bg"])
        settings_frame.pack(pady=(5, 0))

        self.settings_btn = tk.Label(
            settings_frame,
            text="⚙  设置",
            font=("Segoe UI", 10),
            bg=t["bg"],
            fg=t["text_secondary"],
            cursor="hand2",
        )
        self.settings_btn.pack()

        # ---- 设置面板（隐藏） ----
        self._build_settings()

        self._update_tomato_display()

    def _build_settings(self):
        t = self.theme
        self.settings_frame = tk.Frame(self.main_frame, bg=t["card_bg"], relief="ridge", bd=1)
        # 不立即 pack

        row = 0
        self._setting_row(row, "工作时间 (分)", "work_minutes"); row += 1
        self._setting_row(row, "短休时间 (分)", "short_break_minutes"); row += 1
        self._setting_row(row, "长休时间 (分)", "long_break_minutes"); row += 1
        self._setting_row(row, "长休间隔 (个)", "pomodoros_before_long_break"); row += 1

        # 置顶选项
        top_frame = tk.Frame(self.settings_frame, bg=t["card_bg"])
        top_frame.pack(fill="x", padx=10, pady=3)
        self.always_on_top_var = tk.BooleanVar(value=self.config["always_on_top"])
        tk.Label(top_frame, text="窗口置顶", bg=t["card_bg"], fg=t["fg"],
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Checkbutton(top_frame, variable=self.always_on_top_var,
                       bg=t["card_bg"], fg=t["fg"], selectcolor=t["card_bg"],
                       activebackground=t["card_bg"],
                       command=self._toggle_on_top).pack(side="right")

        # 保存按钮
        save_btn = tk.Button(
            self.settings_frame,
            text="保存设置",
            bg=t["success"],
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            cursor="hand2",
            command=self._save_settings,
        )
        save_btn.pack(pady=(5, 8))

    def _setting_row(self, row, label, key):
        t = self.theme
        f = tk.Frame(self.settings_frame, bg=t["card_bg"])
        f.pack(fill="x", padx=10, pady=3)
        tk.Label(f, text=label, bg=t["card_bg"], fg=t["fg"],
                 font=("Segoe UI", 10)).pack(side="left")
        v = tk.StringVar(value=str(self.config[key]))
        e = tk.Entry(f, textvariable=v, width=6,
                     font=("Segoe UI", 10), justify="center",
                     bg=t["bg"], fg=t["fg"], relief="flat",
                     insertbackground=t["fg"])
        e.pack(side="right")
        setattr(self, f"_setting_{key}", v)

    def _toggle_on_top(self):
        self.config["always_on_top"] = self.always_on_top_var.get()
        self.root.attributes("-topmost", self.config["always_on_top"])

    def _save_settings(self):
        try:
            for key in ["work_minutes", "short_break_minutes", "long_break_minutes"]:
                v = int(getattr(self, f"_setting_{key}").get())
                if v < 1 or v > 999:
                    raise ValueError
                self.config[key] = v
            v = int(self._setting_pomodoros_before_long_break.get())
            if v < 1:
                raise ValueError
            self.config["pomodoros_before_long_break"] = v
        except ValueError:
            messagebox.showwarning("输入错误", "请输入有效的正整数")
            return

        save_config(self.config)

        # 更新当前模式时间
        if not self.running:
            self.total_seconds = self._get_mode_seconds()
            self.remaining = self.total_seconds
            self._update_display()

        self._toggle_settings()
        messagebox.showinfo("提示", "设置已保存")

    def _toggle_settings(self):
        """展开/收起设置面板"""
        if self.settings_frame.winfo_ismapped():
            self.settings_frame.pack_forget()
            self.settings_btn.config(text="⚙  设置")
        else:
            self.settings_frame.pack(fill="x", pady=(5, 0), after=self.settings_btn.master)
            self.settings_btn.config(text="⚙  收起设置")

    def _make_button(self, parent, text, cmd, color, hover_color):
        t = self.theme
        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 12, "bold"),
            bg=color,
            fg="#ffffff",
            activebackground=hover_color,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=18,
            pady=6,
            cursor="hand2",
            command=cmd,
        )
        return btn

    def _make_small_button(self, parent, text, cmd, active):
        t = self.theme
        bg = t["accent"] if active else t["button_bg"]
        btn = tk.Button(
            parent,
            text=text,
            font=("Segoe UI", 10),
            bg=bg,
            fg=t["button_fg"],
            activebackground=t["accent"],
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=12,
            pady=4,
            cursor="hand2",
            command=cmd,
        )
        return btn

    def _get_mode_name(self):
        names = {
            "work": "🔴 工作时间",
            "short_break": "🟢 短休息",
            "long_break": "🔵 长休息",
        }
        return names.get(self.mode, "")

    # ---- 事件绑定 ----
    def _bind_events(self):
        self.settings_btn.bind("<Button-1>", lambda e: self._toggle_settings())

    # ---- 核心逻辑 ----
    def _toggle_start(self):
        if self.paused or not self.running:
            self._start()
        else:
            self._pause()

    def _start(self):
        self.running = True
        self.paused = False
        self.start_btn.config(text="⏸  暂停", bg=self.theme["warning"],
                              activebackground="#d68910")
        self.canvas.itemconfig(self.status_text, text="进行中...")
        self._tick()

    def _pause(self):
        self.paused = True
        self.running = False
        self.start_btn.config(text="▶  继续", bg=self.theme["success"],
                              activebackground="#27ae60")
        self.canvas.itemconfig(self.status_text, text="已暂停")

    def _reset(self):
        self.running = False
        self.paused = False
        self.remaining = self._get_mode_seconds()
        self.total_seconds = self.remaining
        self.start_btn.config(text="▶  开始启动", bg=self.theme["success"],
                              activebackground="#27ae60")
        self._update_display()
        self.canvas.itemconfig(self.status_text, text="就绪")

    def _switch_mode(self, mode):
        if self.running or self.paused:
            return  # 运行时不允许切换
        self.mode = mode
        self.total_seconds = self._get_mode_seconds()
        self.remaining = self.total_seconds
        self.mode_label.config(text=self._get_mode_name())

        # 更新按钮高亮
        for btn, m in [(self.work_btn, "work"), (self.short_btn, "short_break"),
                        (self.long_btn, "long_break")]:
            btn.config(bg=self.theme["accent"] if m == mode else self.theme["button_bg"])

        self._update_display()
        self.canvas.itemconfig(self.status_text, text="就绪")

    def _tick(self):
        if not self.running or self.paused:
            return

        self.remaining -= 1
        self._update_display()

        if self.remaining <= 0:
            self._on_time_up()
            return

        # 更新状态文字（运行时）
        if self.running and not self.paused:
            self.canvas.itemconfig(self.status_text, text="专注中...")

        self.root.after(1000, self._tick)

    def _update_display(self):
        """更新计时显示和进度"""
        self.timer_label_text = self._format_time(self.remaining)
        self.canvas.itemconfig(self.timer_text, text=self.timer_label_text)

        # 更新进度弧
        ratio = self.remaining / self.total_seconds if self.total_seconds > 0 else 0
        extent = 360 * ratio
        self.canvas.itemconfig(self.progress_arc, extent=extent)

        # 窗口标题更新
        self.root.title(f"🍅 {self.timer_label_text} - {self._get_mode_name()}")

    def _update_tomato_display(self):
        """更新番茄计数"""
        count = self.completed_pomodoros
        tomatos = "🍅" * min(count, 10)
        if count > 10:
            tomatos += f" ×{count}"
        self.tomato_label.config(text=tomatos if tomatos else "今天还没完成番茄呢")

    def _on_time_up(self):
        self.running = False
        self.paused = False

        # 播放声音
        self._play_sound()

        if self.mode == "work":
            self.completed_pomodoros += 1
            self._record_session()
            self._update_tomato_display()

            # 决定是短休还是长休
            if self.completed_pomodoros % self.config["pomodoros_before_long_break"] == 0:
                next_mode = "long_break"
            else:
                next_mode = "short_break"
        else:
            next_mode = "work"

        # 显示提示
        mode_names = {
            "work": "工作时间",
            "short_break": "短休息",
            "long_break": "长休息",
        }
        next_names = {
            "work": "工作时间",
            "short_break": "短休息",
            "long_break": "长休息",
        }

        msg = f"{mode_names[self.mode]}结束！\n即将进入{next_names[next_mode]}。"
        self._show_notification("时间到！", msg)

        # 自动切换到下个模式
        self.mode = next_mode
        self.total_seconds = self._get_mode_seconds()
        self.remaining = self.total_seconds
        self.mode_label.config(text=self._get_mode_name())
        self.start_btn.config(text="▶  开始启动", bg=self.theme["success"],
                              activebackground="#27ae60")

        # 更新模式按钮高亮
        for btn, m in [(self.work_btn, "work"), (self.short_btn, "short_break"),
                        (self.long_btn, "long_break")]:
            btn.config(bg=self.theme["accent"] if m == self.mode else self.theme["button_bg"])

        self._update_display()
        self.canvas.itemconfig(self.status_text, text="已完成")

    def _play_sound(self):
        """播放提示音"""
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            # 额外蜂鸣
            for _ in range(3):
                winsound.Beep(880, 200)
                time.sleep(0.05)
        except Exception:
            pass  # 非 Windows 或无声音

    def _show_notification(self, title, message):
        """显示通知"""
        try:
            # Windows 原生通知
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40 | 0x1000)
        except Exception:
            self.root.after(100, lambda: messagebox.showinfo(title, message))

    def _record_session(self):
        """记录完成的番茄到历史"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.session_history.append({
            "time": now,
            "duration": self.config["work_minutes"],
        })

    # ---- 窗口关闭 ----
    def _on_close(self):
        self.running = False
        save_config(self.config)
        self.root.destroy()

    # ---- 启动 ----
    def run(self):
        self.root.mainloop()


# ------------------------------
# 入口
# ------------------------------
if __name__ == "__main__":
    app = PomodoroApp()
    app.run()
