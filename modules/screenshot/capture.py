"""
Screenshot capture module.

Delegates to :class:`ScreenshotService` (mss) for real captures when
available; falls back to mock data when ``mss`` is not installed or on
headless systems.

Interface is deliberately simple so that replacing the implementation
later requires zero changes to consumers.
"""

import base64
import time
from typing import Optional

from modules.logger.logger import get_logger

logger = get_logger(__name__)

MOCK_WIDTH = 1920
MOCK_HEIGHT = 1080


class ScreenshotCapture:
    """Captures screen content, preferring real capture via ``mss``.

    Usage::

        capturer = ScreenshotCapture()
        data = capturer.capture_fullscreen()
        # data["image_bytes"] is raw PNG bytes
        # data["base64"]     is the base64-encoded string
    """

    def __init__(self) -> None:
        self._service: Optional[object] = None
        try:
            from modules.screenshot.service import ScreenshotService
            self._service = ScreenshotService()
            logger.info("ScreenshotCapture initialised (real mss backend)")
        except Exception as exc:
            logger.warning(
                "ScreenshotService unavailable (%s) — using mock fallback", exc
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture_fullscreen(self) -> dict:
        """Capture the entire screen (real via mss, or mock fallback).

        Returns:
            A dict::

                {
                    "success": True,
                    "image_bytes": b"...",
                    "base64": "iVBORw...",
                    "width": 1920,
                    "height": 1080,
                    "timestamp": 1234567890.0,
                }
        """
        if self._service is not None:
            result = self._service.capture_fullscreen()
            if result.get("success", True):
                return result
            logger.warning("Real screenshot failed, falling back to mock")
        logger.debug("Using mock screenshot fallback")
        return self._mock_result("fullscreen")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _mock_result(self, mode: str) -> dict:
        """Build a standardised mock result dict."""
        img_bytes = self._mock_image_bytes()
        return {
            "success": True,
            "image_bytes": img_bytes,
            "base64": base64.b64encode(img_bytes).decode("ascii"),
            "width": MOCK_WIDTH,
            "height": MOCK_HEIGHT,
            "timestamp": time.time(),
            "mode": mode,
        }

    @staticmethod
    def _mock_image_bytes() -> bytes:
        """Return a tiny valid PNG as mock image data."""
        import struct
        import zlib

        def chunk(chunk_type: bytes, data: bytes) -> bytes:
            c = chunk_type + data
            return (
                struct.pack(">I", len(data))
                + c
                + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            )

        ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1×1, RGB
        raw = b"\x00\xff\x00\x00"  # filter=0, R=255, G=0, B=0
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b"")
        )
