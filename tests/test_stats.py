"""Tests for StatsCollector (telemetry / dashboard data)."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from modules.telemetry.stats import StatsCollector


class TestStatsCollector:
    """Tests for the StatsCollector singleton."""

    def setup_method(self) -> None:
        StatsCollector.instance().reset()

    def test_singleton(self) -> None:
        a = StatsCollector.instance()
        b = StatsCollector.instance()
        assert a is b

    def test_initial_snapshot(self) -> None:
        stats = StatsCollector.instance()
        snapshot = stats.get_snapshot()
        assert snapshot.vision_calls == 0
        assert snapshot.chat_calls == 0
        assert snapshot.tts_calls == 0
        assert snapshot.total_calls == 0
        assert snapshot.manual_mode_runs == 0
        assert snapshot.uptime_seconds >= 0

    def test_record_vision_call(self) -> None:
        stats = StatsCollector.instance()
        stats.record_call("vision", "mock", "mock-v1", 42.0, True, "manual")
        snapshot = stats.get_snapshot()
        assert snapshot.vision_calls == 1
        assert snapshot.total_calls == 1
        assert snapshot.last_call is not None
        assert snapshot.last_call["provider_type"] == "vision"
        assert snapshot.last_call["provider_name"] == "mock"

    def test_record_multiple_types(self) -> None:
        stats = StatsCollector.instance()
        stats.reset()  # Ensure clean slate (singleton shared across test modules)
        stats.record_call("vision", "mock", "v1", 10.0, True, "manual")
        stats.record_call("chat", "mock", "c1", 20.0, True, "manual")
        stats.record_call("tts", "mock", "t1", 30.0, True, "manual")
        stats.record_call("screenshot", "mss", "screen", 5.0, True, "manual")
        snapshot = stats.get_snapshot()
        assert snapshot.vision_calls == 1
        assert snapshot.chat_calls == 1
        assert snapshot.tts_calls == 1
        assert snapshot.screenshot_count == 1
        assert snapshot.total_calls == 4

    def test_failed_calls_tracked(self) -> None:
        stats = StatsCollector.instance()
        stats.reset()
        stats.record_call("vision", "mock", "v1", 10.0, False, "manual")
        snapshot = stats.get_snapshot()
        # Vision still counted even on failure
        assert snapshot.vision_calls == 1
        assert snapshot.total_calls == 1

    def test_record_pipeline_runs(self) -> None:
        stats = StatsCollector.instance()
        stats.record_pipeline_run("manual")
        stats.record_pipeline_run("manual")
        stats.record_pipeline_run("auto")
        snapshot = stats.get_snapshot()
        assert snapshot.manual_mode_runs == 2
        assert snapshot.auto_mode_runs == 1

    def test_snapshot_dict(self) -> None:
        stats = StatsCollector.instance()
        stats.record_call("vision", "mock", "v1", 50.0, True)
        d = stats.get_snapshot_dict()
        assert "calls" in d
        assert "pipelines" in d
        assert "uptime_seconds" in d
        assert d["calls"]["vision"] == 1

    def test_bind_context_manager(self) -> None:
        stats = StatsCollector.instance()

        class FakeCtx:
            message_count = 5
            _mode = "auto"

        stats.bind_context_manager(FakeCtx())
        snapshot = stats.get_snapshot()
        assert snapshot.context_message_count == 5
        assert snapshot.context_mode == "auto"

    def test_bind_log_counter(self) -> None:
        stats = StatsCollector.instance()
        stats.bind_log_counter(lambda: 42)
        snapshot = stats.get_snapshot()
        assert snapshot.log_count == 42

    def test_reset(self) -> None:
        stats = StatsCollector.instance()
        stats.record_call("vision", "mock", "v1", 10.0, True)
        stats.reset()
        snapshot = stats.get_snapshot()
        assert snapshot.total_calls == 0
        assert snapshot.vision_calls == 0
