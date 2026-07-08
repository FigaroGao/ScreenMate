"""Tests for PipelineState shared state."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from modules.pipeline.state import PipelineState, PipelineProgress


class TestPipelineState:
    """Unit tests for PipelineState singleton."""

    def setup_method(self) -> None:
        PipelineState.instance().reset()

    def test_singleton(self) -> None:
        a = PipelineState.instance()
        b = PipelineState.instance()
        assert a is b

    def test_initial_idle(self) -> None:
        ps = PipelineState.instance()
        status = ps.get_status()
        assert status["running"] is False
        assert status["progress"] == "idle"
        assert status["source"] == ""
        assert status["pipeline_runs"] == 0

    def test_set_running(self) -> None:
        ps = PipelineState.instance()
        ok = ps.set_running("manual")
        assert ok is True
        status = ps.get_status()
        assert status["running"] is True
        assert status["progress"] == "capturing"
        assert status["source"] == "manual"

    def test_busy_rejects_second_start(self) -> None:
        ps = PipelineState.instance()
        assert ps.set_running("manual") is True
        assert ps.is_busy() is True
        assert ps.set_running("hotkey") is False  # should reject

    def test_progress_transitions(self) -> None:
        ps = PipelineState.instance()
        ps.set_running("manual")
        assert ps.get_status()["progress"] == "capturing"

        ps.set_progress(PipelineProgress.ANALYZING)
        assert ps.get_status()["progress"] == "analyzing"

    def test_set_completed(self) -> None:
        ps = PipelineState.instance()
        ps.set_running("manual")
        ps.set_completed({"success": True, "message": "done"})

        status = ps.get_status()
        assert status["running"] is False
        assert status["progress"] == "completed"
        assert status["last_result"] == {"success": True, "message": "done"}
        assert status["pipeline_runs"] == 1

    def test_set_failed(self) -> None:
        ps = PipelineState.instance()
        ps.set_running("hotkey")
        ps.set_failed("Something broke")

        status = ps.get_status()
        assert status["running"] is False
        assert status["progress"] == "failed"
        assert status["last_error"] == "Something broke"

    def test_reset(self) -> None:
        ps = PipelineState.instance()
        ps.set_running("manual")
        ps.set_completed({"ok": True})
        ps.reset()

        status = ps.get_status()
        assert status["running"] is False
        assert status["progress"] == "idle"
        assert status["pipeline_runs"] == 0
