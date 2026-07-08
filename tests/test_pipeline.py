"""Tests for ManualPipeline and AutoPipeline."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import pytest

# Trigger provider registration and initialise infrastructure
import providers.vision  # noqa: E402
import providers.chat    # noqa: E402
import providers.tts     # noqa: E402

from modules.context.manager import ContextManager       # noqa: E402
from modules.screenshot.capture import ScreenshotCapture  # noqa: E402
from modules.monitor.monitor import AutoMonitor            # noqa: E402
from modules.telemetry.stats import StatsCollector          # noqa: E402
from modules.pipeline.manual_pipeline import ManualPipeline # noqa: E402
from modules.pipeline.auto_pipeline import AutoPipeline     # noqa: E402
from modules.pipeline.pipeline_result import PipelineResult # noqa: E402


class TestPipelineResult:
    """Unit tests for PipelineResult."""

    def test_ok_factory(self) -> None:
        r = PipelineResult.ok(message="Done", processing_time_ms=99.0)
        assert r.success is True
        assert r.message == "Done"
        assert r.processing_time_ms == 99.0

    def test_fail_factory(self) -> None:
        r = PipelineResult.fail(error="Boom")
        assert r.success is False
        assert r.error == "Boom"

    def test_to_dict(self) -> None:
        r = PipelineResult.ok(message="OK", data={"key": "val"})
        d = r.to_dict()
        assert d["success"] is True
        assert d["message"] == "OK"
        assert d["key"] == "val"

    def test_to_dict_with_error(self) -> None:
        r = PipelineResult.fail(error="err")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "err"


class TestManualPipeline:
    """Integration tests for ManualPipeline."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        StatsCollector.instance().reset()

    def test_execute_success(self) -> None:
        ctx = ContextManager()
        ss = ScreenshotCapture()
        stats = StatsCollector.instance()
        pipeline = ManualPipeline(ctx, ss, stats)

        result = pipeline.execute(
            prompt="What do you see?",
            screenshot_type="fullscreen",
            vision_provider="mock",
            enable_tts=False,
        )

        assert result.success is True
        assert result.vision_response is not None
        assert result.vision_response.success is True
        assert "Mock Vision" in result.vision_response.content
        assert result.processing_time_ms >= 0
        assert ctx.message_count == 2  # user + assistant

    def test_execute_with_tts(self) -> None:
        ctx = ContextManager()
        ss = ScreenshotCapture()
        stats = StatsCollector.instance()
        pipeline = ManualPipeline(ctx, ss, stats)

        result = pipeline.execute(
            prompt="test",
            enable_tts=True,
        )

        assert result.success is True
        assert result.tts_response is not None
        assert result.tts_response.success is True
        assert "placeholder.mp3" in result.tts_response.content

    def test_execute_records_stats(self) -> None:
        ctx = ContextManager()
        ss = ScreenshotCapture()
        stats = StatsCollector.instance()
        stats.reset()
        pipeline = ManualPipeline(ctx, ss, stats)

        pipeline.execute(prompt="hi")
        snapshot = stats.get_snapshot()
        assert snapshot.vision_calls >= 1
        assert snapshot.manual_mode_runs >= 1
        assert snapshot.total_calls >= 1

    def test_invalid_vision_provider_returns_failure(self) -> None:
        ctx = ContextManager()
        ss = ScreenshotCapture()
        stats = StatsCollector.instance()
        pipeline = ManualPipeline(ctx, ss, stats)

        result = pipeline.execute(
            prompt="test",
            vision_provider="nonexistent",
        )
        assert result.success is False
        assert result.error is not None


class TestAutoPipeline:
    """Integration tests for AutoPipeline."""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        StatsCollector.instance().reset()

    def test_start_stop(self) -> None:
        ctx = ContextManager()
        monitor = AutoMonitor()
        stats = StatsCollector.instance()
        pipeline = AutoPipeline(ctx, monitor, stats)

        # Start
        result = pipeline.start(interval=10)
        assert result.success is True
        assert "started" in result.message.lower()

        # Verify monitor state
        assert monitor.is_running is True

        # Stop
        result = pipeline.stop()
        assert result.success is True
        assert "stopped" in result.message.lower()
        assert monitor.is_running is False

    def test_get_status(self) -> None:
        ctx = ContextManager()
        monitor = AutoMonitor()
        stats = StatsCollector.instance()
        pipeline = AutoPipeline(ctx, monitor, stats)

        result = pipeline.get_status()
        assert result.success is True
        assert "monitor_status" in result.data
