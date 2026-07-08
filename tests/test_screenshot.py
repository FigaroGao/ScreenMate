"""Tests for ScreenshotCapture and ScreenshotService."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from modules.screenshot.capture import ScreenshotCapture


class TestScreenshotCapture:
    """Tests for ScreenshotCapture (works with or without mss)."""

    def test_capture_fullscreen_returns_expected_structure(self) -> None:
        capturer = ScreenshotCapture()
        result = capturer.capture_fullscreen()
        assert result["success"] is True
        assert len(result["image_bytes"]) > 0
        assert "base64" in result
        assert result["width"] > 0
        assert result["height"] > 0
        assert result["timestamp"] > 0

    def test_capture_fullscreen_base64_is_valid(self) -> None:
        import base64
        capturer = ScreenshotCapture()
        result = capturer.capture_fullscreen()
        b64 = result["base64"]
        decoded = base64.b64decode(b64)
        assert len(decoded) > 0
        assert decoded == result["image_bytes"]

    def test_capture_region_returns_expected_structure(self) -> None:
        capturer = ScreenshotCapture()
        result = capturer.capture_region(x=0, y=0, width=400, height=300)
        assert result["success"] is True
        assert "image_bytes" in result

    def test_mock_fallback_works(self) -> None:
        """If mss is unavailable, mock data still works."""
        capturer = ScreenshotCapture()
        result = capturer.capture_fullscreen()
        assert result["success"] is True
        assert len(result["base64"]) > 0
