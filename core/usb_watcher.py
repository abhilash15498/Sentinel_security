"""
SENTINEL - USB Watcher
Cross-platform USB device insertion/removal monitoring.
Linux: pyudev | Windows: WMI/psutil polling | macOS: psutil polling
"""

import threading
import time
import platform
from typing import Callable
from utils.logger import get_logger, event_logger

logger = get_logger("usb_watcher")

OS = platform.system()  # "Linux" | "Windows" | "Darwin"


class USBWatcher:
    """
    Monitors for USB device connect/disconnect events.
    Fires callbacks on change.
    """

    def __init__(
        self,
        on_connect: Callable[[str], None] | None = None,
        on_disconnect: Callable[[str], None] | None = None,
    ) -> None:
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._running = True
        if OS == "Linux":
            self._thread = threading.Thread(
                target=self._watch_linux, daemon=True
            )
        else:
            # macOS and Windows: polling via psutil
            self._thread = threading.Thread(
                target=self._watch_psutil, daemon=True
            )
        self._thread.start()
        logger.info(f"USB watcher started (mode: {OS}).")
        event_logger.log_event("USB_WATCHER", f"Started on {OS}", "INFO")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("USB watcher stopped.")

    # ─── Linux (udev) ─────────────────────────────────────────

    def _watch_linux(self) -> None:
        try:
            import pyudev
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem="usb")

            for device in iter(monitor.poll, None):
                if not self._running:
                    break
                action = device.action
                desc = device.get("ID_MODEL", "USB Device")
                vendor = device.get("ID_VENDOR", "Unknown")
                full = f"{vendor} {desc}"

                if action == "add":
                    logger.warning(f"USB connected: {full}")
                    event_logger.log_event("USB_CONNECT", full, "WARNING")
                    if self._on_connect:
                        self._on_connect(full)
                elif action == "remove":
                    logger.info(f"USB removed: {full}")
                    event_logger.log_event("USB_DISCONNECT", full, "INFO")
                    if self._on_disconnect:
                        self._on_disconnect(full)

        except ImportError:
            logger.warning("pyudev not available. Falling back to psutil polling.")
            self._watch_psutil()
        except Exception as e:
            logger.error(f"Linux USB watcher error: {e}")

    # ─── macOS / Windows (polling) ────────────────────────────

    def _watch_psutil(self) -> None:
        try:
            import psutil

            def get_disks() -> set[str]:
                return {p.device for p in psutil.disk_partitions(all=False)}

            known = get_disks()

            while self._running:
                time.sleep(2)
                current = get_disks()

                added = current - known
                removed = known - current

                for dev in added:
                    logger.warning(f"USB/Disk connected: {dev}")
                    event_logger.log_event("USB_CONNECT", dev, "WARNING")
                    if self._on_connect:
                        self._on_connect(dev)

                for dev in removed:
                    logger.info(f"USB/Disk removed: {dev}")
                    event_logger.log_event("USB_DISCONNECT", dev, "INFO")
                    if self._on_disconnect:
                        self._on_disconnect(dev)

                known = current

        except Exception as e:
            logger.error(f"psutil USB watcher error: {e}")
