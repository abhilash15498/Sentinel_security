"""
SENTINEL - Screen Watcher
Periodically captures screenshots during active sessions.
Stores them for audit trails. Can detect screen content changes.
"""

import threading
import time
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Callable

from utils.config import Config
from utils.logger import get_logger, event_logger

logger = get_logger("screen_watcher")


class ScreenWatcher:
    """
    Periodic screen monitor that:
    - Captures screenshots at configurable intervals
    - Detects significant screen content changes
    - Logs activity to audit trail
    - Fires callback on large visual changes (possible screen swap / remote access)
    """

    def __init__(
        self,
        interval_seconds: int = 30,
        change_threshold: float = 0.25,
        on_change: Callable[[Path], None] | None = None,
        audit_mode: bool = False,
    ) -> None:
        """
        Args:
            interval_seconds: How often to capture (seconds)
            change_threshold: Fraction of pixels changed to trigger alert (0–1)
            on_change: Callback fired when significant change detected
            audit_mode: If True, saves EVERY periodic screenshot (audit trail)
        """
        self._interval = interval_seconds
        self._threshold = change_threshold
        self._on_change = on_change
        self._audit_mode = audit_mode
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_frame: np.ndarray | None = None

        self._shots_dir = Config.LOGS_DIR / "screen_audit"
        if audit_mode:
            self._shots_dir.mkdir(parents=True, exist_ok=True)

    # ─── Control ──────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info(f"Screen watcher started (interval={self._interval}s, audit={self._audit_mode})")
        event_logger.log_event("SCREEN_WATCHER", "Started", "INFO")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Screen watcher stopped.")

    # ─── Main loop ────────────────────────────────────────────

    def _watch_loop(self) -> None:
        while self._running:
            try:
                frame = self._capture()
                if frame is not None:
                    self._process(frame)
            except Exception as e:
                logger.warning(f"Screen watcher error: {e}")
            time.sleep(self._interval)

    def _capture(self) -> np.ndarray | None:
        try:
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                img = sct.grab(monitor)
                # Convert to small numpy array for comparison
                import PIL.Image
                pil = PIL.Image.frombytes("RGB", img.size, img.rgb)
                pil_small = pil.resize((320, 180))  # thumbnail for diff
                arr = np.array(pil_small, dtype=np.float32)
                return arr
        except Exception as e:
            logger.debug(f"Capture failed: {e}")
            return None

    def _process(self, frame: np.ndarray) -> None:
        if self._last_frame is None:
            self._last_frame = frame
            if self._audit_mode:
                self._save_audit_shot(frame)
            return

        # Compute pixel-wise change fraction
        diff = np.abs(frame - self._last_frame)
        changed_pixels = np.mean(diff > 15)  # threshold per channel

        if changed_pixels >= self._threshold:
            logger.warning(
                f"Significant screen change detected: {changed_pixels:.1%} pixels changed"
            )
            event_logger.log_event(
                "SCREEN_CHANGE",
                f"{changed_pixels:.1%} pixel change detected",
                "WARNING",
            )
            if self._on_change:
                # Save a full-res screenshot for the callback
                shot = self._save_full_shot()
                if shot and self._on_change:
                    self._on_change(shot)

        elif self._audit_mode:
            self._save_audit_shot(frame)

        self._last_frame = frame

    def _save_full_shot(self) -> Path | None:
        try:
            import mss
            import mss.tools
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self._shots_dir / f"change_{ts}.png"
            with mss.mss() as sct:
                mon = sct.monitors[0]
                img = sct.grab(mon)
                mss.tools.to_png(img.rgb, img.size, output=str(path))
            return path
        except Exception as e:
            logger.warning(f"Full screenshot failed: {e}")
            return None

    def _save_audit_shot(self, _frame: np.ndarray) -> None:
        """Save full-res screenshot for audit trail."""
        try:
            import mss
            import mss.tools
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self._shots_dir / f"audit_{ts}.png"
            with mss.mss() as sct:
                mon = sct.monitors[0]
                img = sct.grab(mon)
                mss.tools.to_png(img.rgb, img.size, output=str(path))
        except Exception as e:
            logger.debug(f"Audit screenshot failed: {e}")
