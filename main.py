"""
╔═══════════════════════════════════════════════════════════════╗
║          S E N T I N E L  Security System v1.0               ║
║  Real-time intrusion detection · Face recognition · Alerts   ║
║  Python 3.14+ · No dlib · No C++ compiler required          ║
╚═══════════════════════════════════════════════════════════════╝

Entry point: python main.py
"""

import sys
import threading
from pathlib import Path

# ─── Ensure project root is on path ───────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import Config
from utils.logger import get_logger, event_logger

logger = get_logger("sentinel.main")


class SentinelApp:
    """
    Top-level application controller.
    Wires together: GUI ↔ CameraMonitor ↔ IntrusionEngine
                   ↔ USBWatcher ↔ AlarmService ↔ NotificationService
    """

    def __init__(self) -> None:
        self._armed = True
        self._camera_running = False

        # ── Services ──────────────────────────────────────────
        from services.alarm import AlarmService
        from services.notifier import NotificationService
        from services.screenshot import ScreenshotService

        self.alarm = AlarmService()
        self.notifier = NotificationService()
        self.screenshots = ScreenshotService()

        # ── Core modules ──────────────────────────────────────
        from core.face_recognition import CameraMonitor
        from core.intrusion_detection import IntrusionEngine
        from core.usb_watcher import USBWatcher

        self.camera = CameraMonitor(
            on_unknown=self._on_unknown_face,
            on_known=self._on_known_face,
            on_frame=self._on_camera_frame,
        )

        self.intrusion_engine = IntrusionEngine(
            on_intrusion=self._on_intrusion_event,
        )

        self.usb_watcher = USBWatcher(
            on_connect=self._on_usb_connect,
            on_disconnect=self._on_usb_disconnect,
        )

        from core.screen_watcher import ScreenWatcher
        from core.network_monitor import NetworkMonitor

        self.screen_watcher = ScreenWatcher(
            interval_seconds=30,
            change_threshold=0.30,
            on_change=self._on_screen_change,
            audit_mode=False,
        )

        self.network_monitor = NetworkMonitor(
            interval=20,
            on_suspicious=self._on_suspicious_network,
        )

        # ── GUI (created last) ────────────────────────────────
        from ui.dashboard import SentinelDashboard
        self.dashboard = SentinelDashboard(app_controller=self)

    # ─── Arm/Disarm ───────────────────────────────────────────

    def toggle_arm(self) -> bool:
        self._armed = not self._armed
        status = "ARMED" if self._armed else "DISARMED"
        logger.info(f"System {status}.")
        event_logger.log_event("SYSTEM", f"System {status}", "INFO")
        return self._armed

    # ─── Camera ───────────────────────────────────────────────

    def toggle_camera(self) -> bool:
        if not self._camera_running:
            ok = self.camera.start(camera_index=0)
            if ok:
                self._camera_running = True
                logger.info("Camera started.")
        else:
            self.camera.stop()
            self._camera_running = False
        return self._camera_running

    def _on_camera_frame(self, frame) -> None:
        """Relay annotated frame to GUI camera panel."""
        if hasattr(self, "dashboard"):
            self.dashboard.camera_panel.push_frame(frame)

    # ─── Face Events ──────────────────────────────────────────

    def _on_unknown_face(self, face_crop, face_meta: dict) -> None:
        if not self._armed:
            return
        logger.warning("UNKNOWN FACE detected!")
        shot = self.screenshots.capture("unknown_face")
        self.alarm.trigger_intrusion_alert("Unknown person detected at camera")
        self.notifier.dispatch_all(
            "Unknown Person Detected",
            "An unrecognized face was detected by the camera.",
            shot,
        )
        if hasattr(self, "dashboard"):
            self.dashboard.after(0, lambda: self.dashboard.show_intrusion_alert("Unknown face detected"))

    def _on_known_face(self, name: str, crop) -> None:
        logger.info(f"Known person identified: {name}")
        event_logger.log_event("FACE_KNOWN", f"Identified: {name}", "INFO")

    # ─── Face Enrollment ──────────────────────────────────────

    def enroll_face_from_camera(self, name: str, callback) -> None:
        """Capture a burst of camera frames and enroll them."""
        if not self._camera_running:
            callback(False, "Camera is not running. Start it first.")
            return

        def _burst():
            import time
            captured = 0
            # Burst capture 15 frames over ~3 seconds
            for _ in range(60):
                frame = self.camera.get_latest_frame()
                if frame is None:
                    time.sleep(0.05)
                    continue

                faces = self.camera._detector.detect(frame)
                if faces:
                    faces.sort(key=lambda f: f["bbox"][2] * f["bbox"][3], reverse=True)
                    x, y, w, h = faces[0]["bbox"]
                    y1, y2 = max(0, y), min(frame.shape[0], y + h)
                    x1, x2 = max(0, x), min(frame.shape[1], x + w)
                    crop = frame[y1:y2, x1:x2]

                    if crop.size > 0:
                        # Save image without forcing internal cache reload each time
                        self.camera.recognizer.enroll_face(crop, name, reload=False)
                        captured += 1
                        if captured >= 15:
                            break
                time.sleep(0.05)

            if captured > 0:
                # Reload the compiled embeddings directory once at the very end
                self.camera.recognizer.load_known_faces()
                # Run callback safely back on the main thread
                if hasattr(self, "dashboard"):
                    self.dashboard.after(0, lambda: callback(True, f"✓ Enrolled '{name}' with {captured} shots."))
            else:
                if hasattr(self, "dashboard"):
                    self.dashboard.after(0, lambda: callback(False, "Enrollment failed — no face clearly detected."))

        threading.Thread(target=_burst, daemon=True).start()
        # Immediately display a wait message
        callback(True, f"Capturing burst for '{name}'... please wait.")

    def enroll_face_from_file(self, name: str, path: str, callback) -> None:
        import cv2
        img = cv2.imread(path)
        if img is None:
            callback(False, f"Could not read image: {path}")
            return
            
        faces = self.camera._detector.detect(img)
        if not faces:
            callback(False, "No face found in the image.")
            return
            
        faces.sort(key=lambda f: f["bbox"][2] * f["bbox"][3], reverse=True)
        x, y, w, h = faces[0]["bbox"]
        y1, y2 = max(0, y), min(img.shape[0], y + h)
        x1, x2 = max(0, x), min(img.shape[1], x + w)
        crop = img[y1:y2, x1:x2]

        ok = self.camera.recognizer.enroll_face(crop, name)
        if ok:
            callback(True, f"✓ Enrolled '{name}' from file.")
        else:
            callback(False, "Enrollment failed — check logs.")

    # ─── Intrusion Events ─────────────────────────────────────

    def _on_intrusion_event(self, category: str, detail: str) -> None:
        if not self._armed:
            return
        shot = self.screenshots.capture(category.lower())
        self.alarm.trigger_intrusion_alert(detail)
        self.notifier.dispatch_all(f"Intrusion: {category}", detail, shot)
        if hasattr(self, "dashboard"):
            self.dashboard.after(0, lambda: self.dashboard.show_intrusion_alert(f"[{category}] {detail}"))

    # ─── USB Events ───────────────────────────────────────────

    def _on_usb_connect(self, device: str) -> None:
        msg = f"USB device connected: {device}"
        logger.warning(msg)
        if self._armed:
            self.notifier.desktop_popup("USB Device Detected", msg)
            self.alarm.speak(f"Warning! USB device connected: {device}")
        if hasattr(self, "dashboard"):
            self.dashboard.after(0, lambda: self.dashboard.show_info(f"USB: {device}"))

    def _on_usb_disconnect(self, device: str) -> None:
        logger.info(f"USB device removed: {device}")

    def _on_screen_change(self, screenshot_path) -> None:
        if not self._armed:
            return
        msg = "Significant screen content change detected"
        logger.warning(msg)
        self.notifier.dispatch_all("Screen Change Alert", msg, screenshot_path)
        if hasattr(self, "dashboard"):
            self.dashboard.after(0, lambda: self.dashboard.show_intrusion_alert(msg))

    def _on_suspicious_network(self, detail: str) -> None:
        if not self._armed:
            return
        logger.warning(f"Suspicious network activity: {detail}")
        self.notifier.desktop_popup("Suspicious Network Activity", detail)
        if hasattr(self, "dashboard"):
            self.dashboard.after(0, lambda: self.dashboard.show_intrusion_alert(f"[NET] {detail}"))

    # ─── Startup ──────────────────────────────────────────────

    def start(self) -> None:
        logger.info("═" * 55)
        logger.info("  SENTINEL Security System  –  Starting up")
        logger.info("═" * 55)
        event_logger.log_event("SYSTEM", "Sentinel started", "INFO")

        # Start background services
        self.intrusion_engine.start()

        if Config.USB_MONITOR_ENABLED:
            self.usb_watcher.start()

        self.screen_watcher.start()
        self.network_monitor.start()

        # Start camera automatically
        self.toggle_camera()

        # Run GUI (blocking — main thread)
        self.dashboard.mainloop()

        # Cleanup on window close
        self._shutdown()

    def _shutdown(self) -> None:
        logger.info("Shutting down Sentinel...")
        event_logger.log_event("SYSTEM", "Sentinel stopped", "INFO")
        self.camera.stop()
        self.intrusion_engine.stop()
        self.usb_watcher.stop()
        self.screen_watcher.stop()
        self.network_monitor.stop()
        self.alarm.stop_alarm()


# ─── Entry Point ──────────────────────────────────────────────

def main() -> None:
    try:
        app = SentinelApp()
        app.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
