"""
SENTINEL - Network Monitor
Detects suspicious network connections (new open ports, unknown remote IPs).
Uses only psutil — no packet sniffing, no root required.
"""

import threading
import time
from typing import Callable
from utils.logger import get_logger, event_logger

logger = get_logger("network")

# Known/safe ports to ignore
SAFE_PORTS = {80, 443, 53, 123, 67, 68, 22, 5353, 1900}

# Known suspicious ports
SUSPICIOUS_PORTS = {
    4444,   # Metasploit default
    1337,   # Common backdoor
    31337,  # Elite / backdoor
    6666,   # IRC / malware
    12345,  # Common trojan
    54321,  # Reverse shell
    9001,   # Tor / C2
    9090,   # Cockpit / proxy
}


class NetworkMonitor:
    """
    Polls active network connections every N seconds.
    Flags new outbound connections to unknown remote IPs
    and connections on suspicious ports.
    """

    def __init__(
        self,
        interval: int = 15,
        on_suspicious: Callable[[str], None] | None = None,
    ) -> None:
        self._interval = interval
        self._on_suspicious = on_suspicious
        self._running = False
        self._thread: threading.Thread | None = None
        self._baseline_remotes: set[str] = set()

    def start(self) -> None:
        self._running = True
        self._snapshot_baseline()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Network monitor started.")
        event_logger.log_event("NETWORK", "Monitor started", "INFO")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)

    def _snapshot_baseline(self) -> None:
        try:
            import psutil
            conns = psutil.net_connections(kind="inet")
            self._baseline_remotes = {
                f"{c.raddr.ip}:{c.raddr.port}"
                for c in conns
                if c.raddr and c.status == "ESTABLISHED"
            }
        except Exception:
            pass

    def _loop(self) -> None:
        try:
            import psutil
        except ImportError:
            logger.warning("psutil not available — network monitoring disabled.")
            return

        while self._running:
            time.sleep(self._interval)
            try:
                conns = psutil.net_connections(kind="inet")
                current_remotes: set[str] = set()

                for c in conns:
                    if not c.raddr:
                        continue

                    ip = c.raddr.ip
                    port = c.raddr.port
                    key = f"{ip}:{port}"

                    # Check suspicious ports
                    if port in SUSPICIOUS_PORTS:
                        msg = f"Connection on suspicious port {port} → {ip}"
                        logger.warning(msg)
                        event_logger.log_event("SUSPICIOUS_PORT", msg, "WARNING")
                        if self._on_suspicious:
                            self._on_suspicious(msg)

                    # Flag brand-new remote connections
                    if c.status == "ESTABLISHED" and key not in self._baseline_remotes:
                        if port not in SAFE_PORTS and not ip.startswith("127."):
                            msg = f"New outbound connection: {ip}:{port}"
                            logger.info(msg)
                            event_logger.log_event("NEW_CONNECTION", msg, "INFO")

                    if c.status == "ESTABLISHED":
                        current_remotes.add(key)

                self._baseline_remotes = current_remotes

            except Exception as e:
                logger.debug(f"Network monitor tick error: {e}")

    def get_active_connections(self) -> list[dict]:
        """Returns a snapshot of current connections for the GUI."""
        try:
            import psutil
            result = []
            for c in psutil.net_connections(kind="inet"):
                if c.raddr and c.status == "ESTABLISHED":
                    result.append({
                        "local": f"{c.laddr.ip}:{c.laddr.port}",
                        "remote": f"{c.raddr.ip}:{c.raddr.port}",
                        "status": c.status,
                        "pid": c.pid,
                    })
            return result
        except Exception:
            return []
