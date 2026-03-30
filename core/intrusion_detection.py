"""
SENTINEL - Intrusion Detection Module
Monitors keyboard/mouse activity and system idle time.
Detects unauthorized access patterns.
"""

import threading
import time
from typing import Callable
from utils.config import Config
from utils.logger import get_logger, event_logger

logger = get_logger("intrusion")


class ActivityMonitor:
    """
    Monitors keyboard and mouse activity.
    Reports idle/active transitions to callbacks.
    """

    def __init__(
        self,
        on_activity: Callable[[str], None] | None = None,
        idle_threshold_seconds: int = 60,
    ) -> None:
        self._on_activity = on_activity
        self._idle_threshold = idle_threshold_seconds
        self._last_event_time: float = time.time()
        self._running = False
        self._listener = None
        self._idle_notified = False
        self._key_count = 0
        self._click_count = 0

    @property
    def key_count(self) -> int:
        return self._key_count

    @property
    def click_count(self) -> int:
        return self._click_count

    def start(self) -> None:
        self._running = True
        threading.Thread(target=self._start_pynput, daemon=True).start()
        threading.Thread(target=self._idle_watchdog, daemon=True).start()
        logger.info("Activity monitor started.")

    def stop(self) -> None:
        self._running = False
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass

    def _start_pynput(self) -> None:
        try:
            from pynput import keyboard, mouse

            def on_key(key):
                self._key_count += 1
                self._record_activity("KEY_PRESS")

            def on_click(x, y, button, pressed):
                if pressed:
                    self._click_count += 1
                    self._record_activity("MOUSE_CLICK")

            kb_listener = keyboard.Listener(on_press=on_key)
            ms_listener = mouse.Listener(on_click=on_click)
            kb_listener.start()
            ms_listener.start()
            self._listener = kb_listener
            while self._running:
                time.sleep(1)
            kb_listener.stop()
            ms_listener.stop()

        except ImportError:
            logger.warning("pynput not available — activity monitoring limited.")
        except Exception as e:
            logger.error(f"pynput error: {e}")

    def _record_activity(self, event_type: str) -> None:
        self._last_event_time = time.time()
        self._idle_notified = False
        if self._on_activity:
            self._on_activity(event_type)

    def _idle_watchdog(self) -> None:
        while self._running:
            time.sleep(5)
            idle = time.time() - self._last_event_time
            if idle >= self._idle_threshold and not self._idle_notified:
                self._idle_notified = True
                logger.info(f"System idle for {idle:.0f}s")
                event_logger.log_event("IDLE", f"System idle {idle:.0f}s", "INFO")

    def seconds_idle(self) -> float:
        return time.time() - self._last_event_time


class ProcessMonitor:
    """
    Monitors running processes for suspicious or new entries.
    Flags processes that were not present at baseline.
    """

    def __init__(
        self,
        on_suspicious: Callable[[str, int], None] | None = None,
        suspicious_names: list[str] | None = None,
    ) -> None:
        self._on_suspicious = on_suspicious
        self._suspicious_names = [n.lower() for n in (suspicious_names or [
            "wireshark", "tcpdump", "keylogger", "netcat", "nmap",
            "metasploit", "msfconsole", "ettercap",
        ])]
        self._baseline: set[int] = set()
        self._running = False

    def start(self) -> None:
        self._running = True
        self._snapshot_baseline()
        threading.Thread(target=self._monitor_loop, daemon=True).start()
        logger.info("Process monitor started.")

    def stop(self) -> None:
        self._running = False

    def _snapshot_baseline(self) -> None:
        try:
            import psutil
            self._baseline = {p.pid for p in psutil.process_iter()}
        except Exception:
            pass

    def _monitor_loop(self) -> None:
        try:
            import psutil
            while self._running:
                time.sleep(10)
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        pid = proc.info["pid"]
                        name = (proc.info["name"] or "").lower()
                        if pid not in self._baseline:
                            self._baseline.add(pid)
                            if any(s in name for s in self._suspicious_names):
                                logger.warning(f"Suspicious process: {name} (PID {pid})")
                                event_logger.log_event(
                                    "SUSPICIOUS_PROCESS",
                                    f"{name} PID={pid}",
                                    "WARNING",
                                )
                                if self._on_suspicious:
                                    self._on_suspicious(name, pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
        except ImportError:
            logger.warning("psutil not available — process monitoring disabled.")


class IntrusionEngine:
    """
    Orchestrates all intrusion detection sub-modules.
    Central point for starting/stopping monitoring.
    """

    def __init__(
        self,
        on_intrusion: Callable[[str, str], None] | None = None,
    ) -> None:
        self._on_intrusion = on_intrusion

        self.activity = ActivityMonitor(
            on_activity=lambda e: None,  # quiet — just tracks stats
        )

        self.processes = ProcessMonitor(
            on_suspicious=lambda name, pid: self._fire(
                "PROCESS", f"Suspicious process detected: {name} (PID {pid})"
            )
        )

    def _fire(self, category: str, detail: str) -> None:
        logger.warning(f"INTRUSION [{category}]: {detail}")
        if self._on_intrusion:
            self._on_intrusion(category, detail)

    def start(self) -> None:
        self.activity.start()
        self.processes.start()
        logger.info("Intrusion engine started.")
        event_logger.log_event("ENGINE", "Intrusion detection engine started", "INFO")

    def stop(self) -> None:
        self.activity.stop()
        self.processes.stop()
        logger.info("Intrusion engine stopped.")
