"""
SENTINEL - Main Dashboard GUI
Built with CustomTkinter for a modern, clean interface.
Panels: Live Camera | Status | Events Log | Settings | Enrollment
"""

import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import queue
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING
from utils.config import Config
from utils.logger import get_logger, event_logger

if TYPE_CHECKING:
    from main import SentinelApp

# ─── Theme ────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Custom color palette
ACCENT = "#00d4ff"
DANGER = "#ff3b3b"
SUCCESS = "#00e676"
WARNING = "#ffb300"
BG_DARK = "#0d1117"
BG_CARD = "#161b22"
BG_PANEL = "#1c2128"
TEXT_DIM = "#8b949e"


class StatusCard(ctk.CTkFrame):
    """A small metric card widget."""

    def __init__(self, parent, label: str, value: str = "—", color: str = ACCENT, **kw):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=10, **kw)
        self._label = ctk.CTkLabel(
            self, text=label.upper(), font=("Courier New", 10, "bold"),
            text_color=TEXT_DIM,
        )
        self._label.pack(anchor="w", padx=14, pady=(10, 0))
        self._value = ctk.CTkLabel(
            self, text=value, font=("Courier New", 22, "bold"),
            text_color=color,
        )
        self._value.pack(anchor="w", padx=14, pady=(0, 10))

    def update_value(self, value: str, color: str | None = None) -> None:
        self._value.configure(text=value)
        if color:
            self._value.configure(text_color=color)


class EventRow(ctk.CTkFrame):
    """Single event log row."""

    SEVERITY_COLORS = {
        "CRITICAL": DANGER,
        "WARNING": WARNING,
        "INFO": ACCENT,
    }

    def __init__(self, parent, event: dict, **kw):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=8, **kw)

        sev = event.get("severity", "INFO")
        color = self.SEVERITY_COLORS.get(sev, ACCENT)

        indicator = ctk.CTkFrame(self, width=4, fg_color=color, corner_radius=2)
        indicator.pack(side="left", fill="y", padx=(6, 8), pady=6)

        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)

        top_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(
            top_row, text=event.get("type", "EVENT"),
            font=("Courier New", 12, "bold"), text_color=color,
        ).pack(side="left")

        ctk.CTkLabel(
            top_row, text=event.get("timestamp", "")[:19],
            font=("Courier New", 10), text_color=TEXT_DIM,
        ).pack(side="right", padx=8)

        ctk.CTkLabel(
            info_frame, text=event.get("detail", ""),
            font=("Courier New", 11), text_color="#cdd9e5",
            wraplength=400, justify="left",
        ).pack(anchor="w")


class CameraPanel(ctk.CTkFrame):
    """Live camera feed panel with PIL/CTkImage rendering."""

    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=12, **kw)
        self._frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self._running = False

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            header, text="● LIVE FEED",
            font=("Courier New", 12, "bold"), text_color=SUCCESS,
        ).pack(side="left")

        self._status_lbl = ctk.CTkLabel(
            header, text="CAMERA OFF",
            font=("Courier New", 10), text_color=TEXT_DIM,
        )
        self._status_lbl.pack(side="right")

        self._canvas = tk.Canvas(
            self, bg="#0a0e14", highlightthickness=0,
            width=560, height=420,
        )
        self._canvas.pack(padx=8, pady=(0, 8))
        self._canvas.create_text(
            280, 210, text="[ NO SIGNAL ]",
            fill=TEXT_DIM, font=("Courier New", 16, "bold"),
        )

    def push_frame(self, frame_bgr) -> None:
        """Called from camera thread — put frame in queue."""
        try:
            self._frame_queue.put_nowait(frame_bgr)
        except queue.Full:
            pass  # Drop frame if UI is slow

    def refresh(self) -> None:
        """Called on main thread tick to update canvas."""
        if self._frame_queue.empty():
            return
        try:
            import cv2
            from PIL import Image, ImageTk
            frame = self._frame_queue.get_nowait()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            img = img.resize((560, 420), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._canvas.delete("all")
            self._canvas.create_image(0, 0, anchor="nw", image=photo)
            self._canvas._photo_ref = photo  # prevent GC
            self._status_lbl.configure(
                text=datetime.now().strftime("%H:%M:%S"), text_color=SUCCESS
            )
        except Exception:
            pass


class SentinelDashboard(ctk.CTk):
    """
    Main Sentinel application window.
    Hosts: Camera panel, status cards, event log, settings, enrollment.
    """

    def __init__(self, app_controller=None):
        super().__init__()
        self._app = app_controller
        self._setup_window()
        self._build_ui()
        self._last_stats_update = 0
        self._start_tick()

    # ─── Window Setup ─────────────────────────────────────────

    def _setup_window(self) -> None:
        self.title("SENTINEL  ·  Security System")
        self.geometry("1200x780")
        self.minsize(1000, 680)
        self.configure(fg_color=BG_DARK)

    # ─── UI Construction ──────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Title Bar ─────────────────────────────────────────
        titlebar = ctk.CTkFrame(self, fg_color=BG_CARD, height=52, corner_radius=0)
        titlebar.pack(fill="x", side="top")
        titlebar.pack_propagate(False)

        ctk.CTkLabel(
            titlebar,
            text="  🛡  SENTINEL",
            font=("Courier New", 20, "bold"),
            text_color=ACCENT,
        ).pack(side="left", padx=16)

        self._system_badge = ctk.CTkLabel(
            titlebar,
            text="● SYSTEM ARMED",
            font=("Courier New", 11, "bold"),
            text_color=SUCCESS,
        )
        self._system_badge.pack(side="right", padx=16)

        self._clock_lbl = ctk.CTkLabel(
            titlebar, text="",
            font=("Courier New", 11), text_color=TEXT_DIM,
        )
        self._clock_lbl.pack(side="right", padx=8)

        # ── Side Nav ──────────────────────────────────────────
        nav = ctk.CTkFrame(self, fg_color=BG_PANEL, width=200, corner_radius=0)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)

        ctk.CTkLabel(
            nav, text="NAVIGATION",
            font=("Courier New", 9, "bold"), text_color=TEXT_DIM,
        ).pack(anchor="w", padx=16, pady=(20, 8))

        self._content = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self._content.pack(side="right", fill="both", expand=True)

        nav_items = [
            ("🎥  Live Monitor", self._show_monitor),
            ("📋  Event Log", self._show_events),
            ("👤  Enrollment", self._show_enrollment),
            ("⚙️  Settings", self._show_settings),
        ]

        self._nav_btns = []
        for label, cmd in nav_items:
            btn = ctk.CTkButton(
                nav, text=label, command=cmd,
                font=("Courier New", 12),
                fg_color="transparent",
                hover_color=BG_CARD,
                text_color="#cdd9e5",
                anchor="w",
                height=40,
                corner_radius=8,
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_btns.append(btn)

        # Quick controls
        ctk.CTkFrame(nav, height=1, fg_color="#30363d").pack(
            fill="x", padx=12, pady=16
        )

        self._arm_btn = ctk.CTkButton(
            nav, text="🔴  DISARM",
            command=self._toggle_arm,
            font=("Courier New", 12, "bold"),
            fg_color=DANGER, hover_color="#c62828",
            height=40, corner_radius=8,
        )
        self._arm_btn.pack(fill="x", padx=8, pady=2)

        self._cam_btn = ctk.CTkButton(
            nav, text="📷  Start Camera",
            command=self._toggle_camera,
            font=("Courier New", 12),
            fg_color="#1f6feb", hover_color="#1158c7",
            height=40, corner_radius=8,
        )
        self._cam_btn.pack(fill="x", padx=8, pady=2)

        # ── Build all panels ──────────────────────────────────
        self._panels: dict[str, ctk.CTkFrame] = {}
        self._build_monitor_panel()
        self._build_events_panel()
        self._build_enrollment_panel()
        self._build_settings_panel()
        self._show_monitor()

    # ─── Monitor Panel ────────────────────────────────────────

    def _build_monitor_panel(self) -> None:
        panel = ctk.CTkFrame(self._content, fg_color="transparent")
        self._panels["monitor"] = panel

        # Status cards row
        cards_row = ctk.CTkFrame(panel, fg_color="transparent")
        cards_row.pack(fill="x", padx=16, pady=(16, 8))

        self._card_status = StatusCard(cards_row, "System Status", "ARMED", SUCCESS)
        self._card_status.pack(side="left", expand=True, fill="both", padx=(0, 6))

        self._card_faces = StatusCard(cards_row, "Faces Known", "0")
        self._card_faces.pack(side="left", expand=True, fill="both", padx=6)

        self._card_events = StatusCard(cards_row, "Events Today", "0", WARNING)
        self._card_events.pack(side="left", expand=True, fill="both", padx=6)

        self._card_idle = StatusCard(cards_row, "Idle Time", "0s", TEXT_DIM)
        self._card_idle.pack(side="left", expand=True, fill="both", padx=(6, 0))

        # Camera + sidebar
        main_row = ctk.CTkFrame(panel, fg_color="transparent")
        main_row.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.camera_panel = CameraPanel(main_row)
        self.camera_panel.pack(side="left", fill="both", expand=True)

        # Right sidebar
        sidebar = ctk.CTkFrame(main_row, fg_color="transparent", width=260)
        sidebar.pack(side="right", fill="y", padx=(10, 0))
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar, text="RECENT ALERTS",
            font=("Courier New", 10, "bold"), text_color=TEXT_DIM,
        ).pack(anchor="w", pady=(0, 6))

        self._alert_scroll = ctk.CTkScrollableFrame(
            sidebar, fg_color=BG_CARD, corner_radius=10,
        )
        self._alert_scroll.pack(fill="both", expand=True)

        self._alert_rows: list[ctk.CTkLabel] = []

    def _add_alert_badge(self, text: str, color: str = DANGER) -> None:
        """Prepend an alert badge to the sidebar."""
        lbl = ctk.CTkLabel(
            self._alert_scroll,
            text=f"⚡ {datetime.now().strftime('%H:%M:%S')}  {text}",
            font=("Courier New", 10),
            text_color=color,
            wraplength=220,
            justify="left",
            anchor="w",
        )
        lbl.pack(fill="x", anchor="w", pady=2)
        self._alert_rows.append(lbl)

    # ─── Events Panel ─────────────────────────────────────────

    def _build_events_panel(self) -> None:
        panel = ctk.CTkFrame(self._content, fg_color="transparent")
        self._panels["events"] = panel

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))

        ctk.CTkLabel(
            header, text="EVENT LOG",
            font=("Courier New", 16, "bold"), text_color=ACCENT,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="↻  Refresh",
            command=self._refresh_events,
            font=("Courier New", 11),
            width=100, height=32, corner_radius=6,
            fg_color="#238636", hover_color="#2ea043",
        ).pack(side="right")

        self._events_scroll = ctk.CTkScrollableFrame(
            panel, fg_color="transparent",
        )
        self._events_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def _refresh_events(self) -> None:
        from utils.logger import event_logger
        for w in self._events_scroll.winfo_children():
            w.destroy()
        events = event_logger.read_events(last_n=80)
        for ev in events:
            row = EventRow(self._events_scroll, ev)
            row.pack(fill="x", pady=3)

    # ─── Enrollment Panel ─────────────────────────────────────

    def _build_enrollment_panel(self) -> None:
        panel = ctk.CTkFrame(self._content, fg_color="transparent")
        self._panels["enrollment"] = panel

        ctk.CTkLabel(
            panel, text="FACE ENROLLMENT",
            font=("Courier New", 16, "bold"), text_color=ACCENT,
        ).pack(anchor="w", padx=20, pady=(20, 4))

        ctk.CTkLabel(
            panel,
            text="Register known users so Sentinel can identify them.\n"
                 "Face capture uses your live camera feed.",
            font=("Courier New", 11),
            text_color=TEXT_DIM,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 16))

        form = ctk.CTkFrame(panel, fg_color=BG_CARD, corner_radius=12)
        form.pack(fill="x", padx=20, pady=(0, 12))

        ctk.CTkLabel(
            form, text="Person Name",
            font=("Courier New", 11, "bold"), text_color=TEXT_DIM,
        ).pack(anchor="w", padx=16, pady=(14, 2))

        self._enroll_name_entry = ctk.CTkEntry(
            form, placeholder_text="e.g. Abhi",
            font=("Courier New", 13),
            height=38, corner_radius=8,
        )
        self._enroll_name_entry.pack(fill="x", padx=16, pady=(0, 12))

        btn_row = ctk.CTkFrame(form, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkButton(
            btn_row, text="📷  Capture from Camera",
            command=self._enroll_from_camera,
            font=("Courier New", 12, "bold"),
            height=40, corner_radius=8,
            fg_color="#1f6feb", hover_color="#1158c7",
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="🖼  Load from File",
            command=self._enroll_from_file,
            font=("Courier New", 12),
            height=40, corner_radius=8,
            fg_color=BG_PANEL, hover_color="#2d333b",
        ).pack(side="right", expand=True, fill="x", padx=(6, 0))

        self._enroll_status = ctk.CTkLabel(
            panel, text="",
            font=("Courier New", 11),
            text_color=SUCCESS,
        )
        self._enroll_status.pack(anchor="w", padx=20)

        # Known persons list
        ctk.CTkLabel(
            panel, text="ENROLLED PERSONS",
            font=("Courier New", 10, "bold"), text_color=TEXT_DIM,
        ).pack(anchor="w", padx=20, pady=(20, 6))

        self._persons_scroll = ctk.CTkScrollableFrame(
            panel, fg_color=BG_CARD, corner_radius=10,
        )
        self._persons_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self._refresh_persons_list()

    def _refresh_persons_list(self) -> None:
        from utils.config import Config
        for w in self._persons_scroll.winfo_children():
            w.destroy()
        known_dir = Config.KNOWN_FACES_DIR
        if not known_dir.exists():
            return
        persons = [d.name for d in known_dir.iterdir() if d.is_dir()]
        if not persons:
            ctk.CTkLabel(
                self._persons_scroll,
                text="No persons enrolled yet.",
                font=("Courier New", 11), text_color=TEXT_DIM,
            ).pack(pady=16)
            return
        for name in sorted(persons):
            count = len(list((known_dir / name).glob("*.jpg")))
            row = ctk.CTkFrame(self._persons_scroll, fg_color=BG_PANEL, corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)
            ctk.CTkLabel(
                row, text=f"👤  {name}",
                font=("Courier New", 12, "bold"),
            ).pack(side="left", padx=12, pady=8)
            ctk.CTkLabel(
                row, text=f"{count} sample(s)",
                font=("Courier New", 10), text_color=TEXT_DIM,
            ).pack(side="right", padx=12)

    def _get_enroll_name(self) -> str | None:
        name = self._enroll_name_entry.get().strip()
        if not name:
            messagebox.showwarning("Input Required", "Please enter a person name.")
            return None
        return name

    def _enroll_from_camera(self) -> None:
        name = self._get_enroll_name()
        if not name:
            return
        if self._app and hasattr(self._app, "enroll_face_from_camera"):
            self._app.enroll_face_from_camera(name, self._on_enroll_done)
        else:
            messagebox.showinfo("Info", "Camera not running. Start camera first.")

    def _enroll_from_file(self) -> None:
        name = self._get_enroll_name()
        if not name:
            return
        path = filedialog.askopenfilename(
            title="Select Face Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")],
        )
        if not path:
            return
        if self._app and hasattr(self._app, "enroll_face_from_file"):
            self._app.enroll_face_from_file(name, path, self._on_enroll_done)

    def _on_enroll_done(self, success: bool, msg: str) -> None:
        color = SUCCESS if success else DANGER
        self._enroll_status.configure(text=msg, text_color=color)
        self._refresh_persons_list()

    # ─── Settings Panel ───────────────────────────────────────

    def _build_settings_panel(self) -> None:
        panel = ctk.CTkFrame(self._content, fg_color="transparent")
        self._panels["settings"] = panel

        ctk.CTkLabel(
            panel, text="SETTINGS",
            font=("Courier New", 16, "bold"), text_color=ACCENT,
        ).pack(anchor="w", padx=20, pady=(20, 4))

        scroll = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self._setting_vars: dict[str, ctk.Variable] = {}

        settings_defs = [
            ("Sound Alarm", "sound_alarm", True),
            ("Text-to-Speech Alerts", "tts", True),
            ("Screenshot on Intrusion", "screenshot", True),
            ("USB Device Monitoring", "usb", True),
            ("Email Alerts", "email", False),
            ("Telegram Alerts", "telegram", False),
            ("Process Monitoring", "processes", True),
        ]

        ctk.CTkLabel(
            scroll, text="MONITORING FEATURES",
            font=("Courier New", 10, "bold"), text_color=TEXT_DIM,
        ).pack(anchor="w", pady=(8, 6))

        for label, key, default in settings_defs:
            row = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row, text=label,
                font=("Courier New", 12),
            ).pack(side="left", padx=14, pady=10)
            var = ctk.BooleanVar(value=default)
            self._setting_vars[key] = var
            ctk.CTkSwitch(
                row, text="", variable=var,
                button_color=ACCENT, progress_color=ACCENT,
            ).pack(side="right", padx=14)

        # Confidence threshold
        ctk.CTkLabel(
            scroll, text="DETECTION SENSITIVITY",
            font=("Courier New", 10, "bold"), text_color=TEXT_DIM,
        ).pack(anchor="w", pady=(20, 6))

        thresh_row = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8)
        thresh_row.pack(fill="x", pady=3)
        ctk.CTkLabel(
            thresh_row, text="Face Confidence Threshold",
            font=("Courier New", 12),
        ).pack(side="left", padx=14, pady=10)
        
        # Load from Config
        current_thresh = Config.FACE_CONFIDENCE_THRESHOLD
        self._thresh_var = ctk.DoubleVar(value=current_thresh)
        self._thresh_lbl = ctk.CTkLabel(
            thresh_row, text=f"{int(current_thresh*100)}%",
            font=("Courier New", 11), text_color=ACCENT,
        )
        self._thresh_lbl.pack(side="right", padx=8)
        
        def _on_thresh_change(v):
            self._thresh_lbl.configure(text=f"{int(v*100)}%")
            Config.FACE_CONFIDENCE_THRESHOLD = float(v)
            
        ctk.CTkSlider(
            thresh_row, from_=0.4, to=0.99,
            variable=self._thresh_var,
            command=_on_thresh_change,
            button_color=ACCENT, progress_color=ACCENT,
        ).pack(side="right", padx=8, pady=8)

    # ─── Panel Navigation ─────────────────────────────────────

    def _show_panel(self, name: str) -> None:
        for pname, panel in self._panels.items():
            if pname == name:
                panel.pack(fill="both", expand=True)
            else:
                panel.pack_forget()

    def _show_monitor(self) -> None:
        self._show_panel("monitor")

    def _show_events(self) -> None:
        self._show_panel("events")
        self._refresh_events()

    def _show_enrollment(self) -> None:
        self._show_panel("enrollment")
        self._refresh_persons_list()

    def _show_settings(self) -> None:
        self._show_panel("settings")

    # ─── Controls ─────────────────────────────────────────────

    def _toggle_arm(self) -> None:
        if self._app:
            armed = self._app.toggle_arm()
            if armed:
                self._arm_btn.configure(text="🔴  DISARM", fg_color=DANGER)
                self._system_badge.configure(text="● SYSTEM ARMED", text_color=SUCCESS)
                self._card_status.update_value("ARMED", SUCCESS)
            else:
                self._arm_btn.configure(text="🟢  ARM", fg_color="#238636")
                self._system_badge.configure(text="○ SYSTEM DISARMED", text_color=DANGER)
                self._card_status.update_value("DISARMED", DANGER)

    def _toggle_camera(self) -> None:
        if self._app:
            running = self._app.toggle_camera()
            self._cam_btn.configure(
                text="📷  Stop Camera" if running else "📷  Start Camera"
            )

    # ─── UI Tick ──────────────────────────────────────────────

    def _start_tick(self) -> None:
        self.after(33, self._tick)  # ~30 fps

    def _tick(self) -> None:
        try:
            # Update clock
            self._clock_lbl.configure(
                text=datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
            )
            # Refresh camera
            self.camera_panel.refresh()
            
            # Update stats less frequently (every 2 seconds) to prevent GUI freezing
            now = time.time()
            if now - self._last_stats_update >= 2.0:
                self._last_stats_update = now
                if self._app:
                    self._update_stats()
        except Exception:
            pass
        finally:
            self.after(33, self._tick)

    def _update_stats(self) -> None:
        try:
            from utils.config import Config
            from utils.logger import event_logger
            # Known faces count
            kf_dir = Config.KNOWN_FACES_DIR
            count = len([d for d in kf_dir.iterdir() if d.is_dir()]) if kf_dir.exists() else 0
            self._card_faces.update_value(str(count))
            # Events today
            events = event_logger.read_events(200)
            today = datetime.now().strftime("%Y-%m-%d")
            today_events = [e for e in events if e["timestamp"].startswith(today)]
            self._card_events.update_value(str(len(today_events)))
            # Idle time
            if hasattr(self._app, "intrusion_engine"):
                idle = int(self._app.intrusion_engine.activity.seconds_idle())
                self._card_idle.update_value(f"{idle}s")
        except Exception:
            pass

    # ─── Public notification hooks ────────────────────────────

    def show_intrusion_alert(self, message: str) -> None:
        """Called from app controller when intrusion detected."""
        self._add_alert_badge(message, DANGER)
        self._system_badge.configure(text="⚠ INTRUSION!", text_color=DANGER)
        # Flash title
        original = self.title()
        self.title("⚠ INTRUSION DETECTED ⚠")
        self.after(3000, lambda: self.title(original))

    def show_info(self, message: str) -> None:
        self._add_alert_badge(message, ACCENT)
