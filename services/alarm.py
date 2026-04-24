"""
SENTINEL - Alarm Service
Plays sound alarms and/or text-to-speech warnings.
No external audio files required — generates beep via pygame.
"""

import threading
import time
from utils.config import Config
from utils.logger import get_logger, event_logger

logger = get_logger("alarm")


class AlarmService:
    """
    Handles audio alarms and text-to-speech alerts.
    Thread-safe; alarm plays in background thread.
    """

    def __init__(self) -> None:
        self._tts_engine = None
        self._pygame_ready = False
        self._lock = threading.Lock()
        self._alarm_active = False
        self._init_pygame()
        self._init_tts()

    # ─── Init ─────────────────────────────────────────────────

    def _init_pygame(self) -> None:
        if not Config.SOUND_ALARM_ENABLED:
            return
        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self._pygame = pygame
            self._pygame_ready = True
            logger.info("Pygame audio initialized.")
        except Exception as e:
            logger.warning(f"Pygame not available: {e}")

    def _init_tts(self) -> None:
        # TTS will be initialized on-demand in its own thread to avoid COM apartment issues on Windows
        pass

    # ─── Sound ────────────────────────────────────────────────

    def _generate_beep(self, frequency: int = 880, duration_ms: int = 500) -> None:
        """Generates a pure sine-wave beep using numpy + pygame."""
        if not self._pygame_ready:
            return
        try:
            import numpy as np
            sample_rate = 44100
            n_samples = int(sample_rate * duration_ms / 1000)
            t = np.linspace(0, duration_ms / 1000, n_samples, endpoint=False)
            wave = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)
            stereo_wave = np.column_stack((wave, wave))
            sound = self._pygame.sndarray.make_sound(stereo_wave)
            sound.play()
            self._pygame.time.wait(duration_ms)
        except Exception as e:
            logger.warning(f"Beep generation failed: {e}")

    def play_alarm(self, repeat: int = 3) -> None:
        """Play an intrusion alarm in a background thread."""
        def _alarm_loop():
            with self._lock:
                self._alarm_active = True
            for _ in range(repeat):
                if not self._alarm_active:
                    break
                self._generate_beep(frequency=1200, duration_ms=300)
                time.sleep(0.1)
                self._generate_beep(frequency=800, duration_ms=300)
                time.sleep(0.1)
            with self._lock:
                self._alarm_active = False

        t = threading.Thread(target=_alarm_loop, daemon=True)
        t.start()
        event_logger.log_event("ALARM", "Sound alarm triggered", "WARNING")

    def stop_alarm(self) -> None:
        with self._lock:
            self._alarm_active = False
        if self._pygame_ready:
            try:
                self._pygame.mixer.stop()
            except Exception:
                pass

    # ─── TTS ──────────────────────────────────────────────────

    def speak(self, message: str) -> None:
        """Speak a message using TTS in a background thread."""
        if not Config.TTS_ENABLED:
            return

        def _speak():
            try:
                import pyttsx3
                # Initialize in-thread for Windows compatibility
                engine = pyttsx3.init()
                engine.setProperty("rate", 160)
                engine.setProperty("volume", 1.0)
                engine.say(message)
                engine.runAndWait()
                # Clean up
                del engine
            except Exception as e:
                logger.warning(f"TTS speak failed: {e}")

        t = threading.Thread(target=_speak, daemon=True)
        t.start()

    # ─── Combined Alert ───────────────────────────────────────

    def trigger_intrusion_alert(self, reason: str = "Unknown intrusion detected") -> None:
        logger.warning(f"INTRUSION ALERT: {reason}")
        self.play_alarm()
        self.speak(f"Warning! {reason}. Security alert activated.")
