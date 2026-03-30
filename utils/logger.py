"""
SENTINEL - Logging Module
Structured, colored console + rotating file logging.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False

from utils.config import Config


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance for the given module name.
    Logs to both console (colored) and a rotating file.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured — avoid duplicate handlers
        return logger

    level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    # ─── Console Handler ──────────────────────────────────────
    if HAS_COLORLOG:
        console_handler = logging.StreamHandler()
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s[%(asctime)s] [%(name)s] %(levelname)s%(reset)s  %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
        console_handler.setFormatter(formatter)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(name)s] %(levelname)s  %(message)s",
                              datefmt="%H:%M:%S")
        )
    logger.addHandler(console_handler)

    # ─── File Handler (rotating) ──────────────────────────────
    log_file = Config.LOGS_DIR / f"sentinel_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [%(name)s] %(levelname)s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_handler)

    return logger


# ─── Event Logger (JSON-style structured logs) ────────────────
class EventLogger:
    """Logs security events to a dedicated structured log file."""

    def __init__(self) -> None:
        self._log_path = Config.LOGS_DIR / "events.log"

    def log_event(self, event_type: str, detail: str, severity: str = "INFO") -> None:
        timestamp = datetime.now().isoformat()
        line = f"{timestamp} | {severity} | {event_type} | {detail}\n"
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_events(self, last_n: int = 100) -> list[dict]:
        if not self._log_path.exists():
            return []
        events = []
        with open(self._log_path, "r", encoding="utf-8") as f:
            for line in f.readlines()[-last_n:]:
                parts = line.strip().split(" | ")
                if len(parts) == 4:
                    events.append({
                        "timestamp": parts[0],
                        "severity": parts[1],
                        "type": parts[2],
                        "detail": parts[3],
                    })
        return list(reversed(events))


# Singleton event logger
event_logger = EventLogger()
