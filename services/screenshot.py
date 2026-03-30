"""
SENTINEL - Screenshot Service
Captures the full screen using mss (cross-platform, fast).
"""

from datetime import datetime
from pathlib import Path

from utils.config import Config
from utils.logger import get_logger, event_logger

logger = get_logger("screenshot")


class ScreenshotService:
    """Captures and saves screenshots of intrusion events."""

    def __init__(self) -> None:
        self._shots_dir = Config.LOGS_DIR / "screenshots"
        self._shots_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, label: str = "intrusion") -> Path | None:
        """
        Capture the full screen and save to the logs/screenshots directory.
        Returns the Path to the saved file, or None on failure.
        """
        if not Config.SCREENSHOT_ON_INTRUSION:
            return None

        try:
            import mss
            import mss.tools

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self._shots_dir / f"{label}_{timestamp}.png"

            with mss.mss() as sct:
                monitor = sct.monitors[0]  # All monitors combined
                img = sct.grab(monitor)
                mss.tools.to_png(img.rgb, img.size, output=str(filename))

            logger.info(f"Screenshot saved: {filename}")
            event_logger.log_event("SCREENSHOT", str(filename), "INFO")
            return filename

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
