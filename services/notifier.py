"""
SENTINEL - Notification Service
Desktop popups, email, and Telegram alerts with screenshot attachment.
"""

import smtplib
import threading
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime

from utils.config import Config
from utils.logger import get_logger, event_logger

logger = get_logger("notifier")


class NotificationService:
    """Dispatches alerts via desktop, email, and Telegram."""

    def __init__(self) -> None:
        self._last_alert_time: dict[str, float] = {}
        self._cooldown = Config.ALERT_COOLDOWN_SECONDS

    # ─── Cooldown guard ───────────────────────────────────────

    def _can_alert(self, channel: str) -> bool:
        import time
        now = time.time()
        last = self._last_alert_time.get(channel, 0)
        if now - last >= self._cooldown:
            self._last_alert_time[channel] = now
            return True
        return False

    # ─── Desktop Popup ────────────────────────────────────────

    def desktop_popup(self, title: str, message: str) -> None:
        """System notification popup (cross-platform via plyer)."""
        def _notify():
            try:
                from plyer import notification
                notification.notify(
                    title=title,
                    message=message,
                    app_name="SENTINEL Security",
                    timeout=8,
                )
            except Exception as e:
                logger.warning(f"Desktop notification failed: {e}")

        threading.Thread(target=_notify, daemon=True).start()
        event_logger.log_event("NOTIFICATION", f"Desktop: {title} - {message}", "INFO")

    # ─── Email ────────────────────────────────────────────────

    def send_email(
        self,
        subject: str,
        body: str,
        screenshot_path: Path | None = None,
    ) -> None:
        """Send an email alert, optionally with a screenshot attached."""
        if not Config.email_configured():
            logger.warning("Email not configured — skipping email alert.")
            return
        if not self._can_alert("email"):
            logger.debug("Email alert suppressed (cooldown).")
            return

        def _send():
            try:
                msg = MIMEMultipart()
                msg["From"] = Config.EMAIL_SENDER
                msg["To"] = Config.EMAIL_RECEIVER
                msg["Subject"] = f"[SENTINEL] {subject}"

                html_body = f"""
                <html><body>
                <h2 style="color:#e53935;">🔐 SENTINEL Security Alert</h2>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Event:</strong> {body}</p>
                <hr>
                <small>Sent automatically by SENTINEL Security System</small>
                </body></html>
                """
                msg.attach(MIMEText(html_body, "html"))

                if screenshot_path and screenshot_path.exists():
                    with open(screenshot_path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={screenshot_path.name}",
                    )
                    msg.attach(part)

                with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                    server.starttls()
                    server.login(Config.EMAIL_SENDER, Config.EMAIL_PASSWORD)
                    server.send_message(msg)

                logger.info(f"Email alert sent: {subject}")
                event_logger.log_event("ALERT_EMAIL", subject, "WARNING")

            except Exception as e:
                logger.error(f"Email send failed: {e}")

        threading.Thread(target=_send, daemon=True).start()

    # ─── Telegram ─────────────────────────────────────────────

    def send_telegram(
        self,
        message: str,
        screenshot_path: Path | None = None,
    ) -> None:
        """Send a Telegram bot message with optional photo."""
        if not Config.telegram_configured():
            logger.debug("Telegram not configured — skipping.")
            return
        if not self._can_alert("telegram"):
            return

        def _send():
            try:
                import requests
                token = Config.TELEGRAM_BOT_TOKEN
                chat_id = Config.TELEGRAM_CHAT_ID
                text = f"🔐 *SENTINEL ALERT*\n\n{message}\n\n_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"

                if screenshot_path and screenshot_path.exists():
                    with open(screenshot_path, "rb") as photo:
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendPhoto",
                            data={"chat_id": chat_id, "caption": text, "parse_mode": "Markdown"},
                            files={"photo": photo},
                            timeout=10,
                        )
                else:
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                        timeout=10,
                    )

                logger.info("Telegram alert sent.")
                event_logger.log_event("ALERT_TELEGRAM", message[:80], "WARNING")

            except Exception as e:
                logger.error(f"Telegram send failed: {e}")

        threading.Thread(target=_send, daemon=True).start()

    # ─── Combined Dispatch ────────────────────────────────────

    def dispatch_all(
        self,
        title: str,
        body: str,
        screenshot_path: Path | None = None,
    ) -> None:
        """Fire all configured notification channels at once."""
        self.desktop_popup(title, body)
        self.send_email(title, body, screenshot_path)
        self.send_telegram(body, screenshot_path)
