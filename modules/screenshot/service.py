"""
Real screenshot capture using ``mss``.

:class:`ScreenshotService` captures the screen and returns PNG bytes
along with metadata.  It is wrapped by :class:`ScreenshotCapture` so
that existing code requires zero changes.
"""

import base64
import io
import time
from typing import Optional

from modules.logger.logger import get_logger

logger = get_logger(__name__)


class ScreenshotService:
    """Capture the screen using the ``mss`` library.

    Usage::

        svc = ScreenshotService()
        result = svc.capture_fullscreen()
        # result["image_bytes"]  → PNG bytes
        # result["base64"]       → Base64-encoded PNG string
        # result["width"]        → screen width
        # result["height"]       → screen height
    """

    def __init__(self) -> None:
        """Initialise the MSS screenshot service."""
        import mss

        self._mss = mss
        self._sct: Optional["mss.MSS"] = None
        logger.info("ScreenshotService initialised (mss backend)")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture_fullscreen(self) -> dict:
        """Capture every monitor and return a stitched image.

        Returns:
            A dict with keys ``image_bytes``, ``base64``, ``width``,
            ``height``, ``timestamp``, ``monitor_count``.
        """
        t0 = time.perf_counter()
        sct = self._get_sct()

        try:
            monitors = sct.monitors
            # monitors[0] is the "all-in-one" virtual monitor
            all_mon = monitors[0]

            # Capture
            img = sct.grab(all_mon)
            # img is a ScreenShot object; raw BGRA pixels
            png_bytes = self._to_png(img)

            b64 = base64.b64encode(png_bytes).decode("ascii")
            elapsed = (time.perf_counter() - t0) * 1000

            logger.info(
                "Screenshot captured: %dx%d, %.1fms, %d monitors",
                img.width,
                img.height,
                elapsed,
                len(monitors) - 1,  # exclude virtual monitor
            )

            return {
                "success": True,
                "image_bytes": png_bytes,
                "base64": b64,
                "width": img.width,
                "height": img.height,
                "timestamp": time.time(),
                "monitor_count": len(monitors) - 1,
                "capture_ms": round(elapsed, 2),
            }
        except Exception as exc:
            logger.error("Screenshot capture failed: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "timestamp": time.time(),
            }

    def capture_region(
        self,
        left: int = 0,
        top: int = 0,
        width: int = 800,
        height: int = 600,
    ) -> dict:
        """Capture a region of the primary monitor.

        This is a stub — returns the full screen for now.  Region
        capture will be fully implemented in a future version.

        Args:
            left: Left pixel coordinate.
            top: Top pixel coordinate.
            width: Region width.
            height: Region height.

        Returns:
            Same structure as :meth:`capture_fullscreen`.
        """
        logger.info(
            "ScreenshotService.capture_region (stub): %d,%d %dx%d",
            left, top, width, height,
        )
        return self.capture_fullscreen()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_sct(self):
        """Return (or create) the MSS instance."""
        if self._sct is None:
            self._sct = self._mss.MSS()
        return self._sct

    @staticmethod
    def _to_png(sct_img) -> bytes:
        """Convert an MSS ScreenShot to PNG bytes.

        MSS provides ``rgb`` attribute with raw RGB pixels.  We use
        PIL to convert to PNG.  If PIL is not available, returns the
        raw BMP data as a fallback.
        """
        try:
            from PIL import Image
        except ImportError:
            # Fallback: return raw BMP constructed from sct_img
            logger.warning("PIL not available — returning raw BMP")
            return sct_img.rgb

        pil_img = Image.frombytes(
            "RGB",
            (sct_img.width, sct_img.height),
            sct_img.rgb,
        )
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        return buf.getvalue()
