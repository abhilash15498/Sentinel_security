"""
SENTINEL - Configuration Manager
Loads and validates environment/config settings centrally.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv(Path(__file__).parent.parent / ".env")


class Config:
    """Central configuration object for all Sentinel modules."""

    # ─── Paths ────────────────────────────────────────────────
    BASE_DIR = Path(__file__).parent.parent
    LOGS_DIR = BASE_DIR / "logs"
    ASSETS_DIR = BASE_DIR / "assets"
    MODELS_DIR = BASE_DIR / "models"
    KNOWN_FACES_DIR = BASE_DIR / "models" / "known_faces"

    # ─── Email ────────────────────────────────────────────────
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_RECEIVER: str = os.getenv("EMAIL_RECEIVER", "")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))

    # ─── Telegram ─────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # ─── Detection ────────────────────────────────────────────

    FACE_RECOGNITION_MODE: str = os.getenv("FACE_RECOGNITION_MODE", "deepface")
    ALERT_COOLDOWN_SECONDS: int = int(os.getenv("ALERT_COOLDOWN_SECONDS", "30"))
    FACE_CONFIDENCE_THRESHOLD: float = float(os.getenv("FACE_CONFIDENCE_THRESHOLD", "0.6"))

    # ─── Features ─────────────────────────────────────────────
    SCREENSHOT_ON_INTRUSION: bool = (
        os.getenv("SCREENSHOT_ON_INTRUSION", "true").lower() == "true"
    )
    TTS_ENABLED: bool = os.getenv("TTS_ENABLED", "true").lower() == "true"
    SOUND_ALARM_ENABLED: bool = (
        os.getenv("SOUND_ALARM_ENABLED", "true").lower() == "true"
    )
    USB_MONITOR_ENABLED: bool = (
        os.getenv("USB_MONITOR_ENABLED", "true").lower() == "true"
    )

    # ─── Logging ──────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("SENTINEL_LOG_LEVEL", "INFO")

    @classmethod
    def ensure_dirs(cls) -> None:
        """Create all required directories if they don't exist."""
        for d in [cls.LOGS_DIR, cls.KNOWN_FACES_DIR, cls.ASSETS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def email_configured(cls) -> bool:
        return bool(cls.EMAIL_SENDER and cls.EMAIL_PASSWORD and cls.EMAIL_RECEIVER)

    @classmethod
    def telegram_configured(cls) -> bool:
        return bool(cls.TELEGRAM_BOT_TOKEN and cls.TELEGRAM_CHAT_ID)


# Ensure directories exist at import time
Config.ensure_dirs()
