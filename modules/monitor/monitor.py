"""
Auto-mode monitor (stub).

In the future this module will run a background thread / coroutine that:
- Periodically captures the screen
- Feeds screenshots to a vision model for summarisation
- Maintains a rolling context window
- Listens for user chat input

For now it provides the API surface that the rest of the app expects.
"""

import threading
import time
from typing import Optional

from config.settings import Config
from modules.logger.logger import get_logger

logger = get_logger(__name__)


class AutoMonitor:
    """Stub monitor for auto-mode.

    Tracks running state and last-screenshot timestamp.
    Real implementation will be swapped in without changing this interface.
    """

    def __init__(self) -> None:
        self._running: bool = False
        self._interval: int = Config.AUTO_SCREENSHOT_INTERVAL
        self._last_screenshot_time: float = 0.0
        self._screenshot_count: int = 0
        self._start_time: float = 0.0
        logger.info("AutoMonitor initialised (stub mode)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, interval: Optional[int] = None) -> dict:
        """Start auto-mode monitoring.

        Args:
            interval: Screenshot interval in seconds.  Defaults to config.

        Returns:
            A status dict.
        """
        if interval is not None:
            self._interval = interval

        if self._running:
            logger.warning("AutoMonitor: already running")
            return {"success": False, "message": "Already running"}

        self._running = True
        self._start_time = time.time()
        logger.info(
            "AutoMonitor: started (interval=%ds) [STUB — no actual monitoring]",
            self._interval,
        )
        return {
            "success": True,
            "message": f"Auto mode started (interval={self._interval}s) [STUB]",
        }

    def stop(self) -> dict:
        """Stop auto-mode monitoring.

        Returns:
            A status dict.
        """
        if not self._running:
            logger.warning("AutoMonitor: not running")
            return {"success": False, "message": "Not running"}

        self._running = False
        elapsed = time.time() - self._start_time
        logger.info(
            "AutoMonitor: stopped (elapsed=%.1fs, screenshots=%d) [STUB]",
            elapsed,
            self._screenshot_count,
        )
        return {
            "success": True,
            "message": f"Auto mode stopped. Ran for {elapsed:.0f}s. [STUB]",
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return the current monitor status."""
        return {
            "running": self._running,
            "interval": self._interval,
            "last_screenshot_time": self._last_screenshot_time,
            "last_screenshot_iso": (
                time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(self._last_screenshot_time),
                )
                if self._last_screenshot_time
                else "never"
            ),
            "screenshot_count": self._screenshot_count,
            "elapsed_seconds": (
                time.time() - self._start_time if self._running else 0
            ),
        }

    def set_interval(self, seconds: int) -> None:
        """Update the screenshot interval."""
        self._interval = max(1, seconds)
        logger.info("AutoMonitor: interval set to %ds", self._interval)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Return whether auto-mode is active."""
        return self._running
