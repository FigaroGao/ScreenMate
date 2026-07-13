"""
Pipeline state — thread-safe shared state for all pipeline entry points.

Manual Mode, Hotkey, and future Auto Mode all read/write the same
singleton :class:`PipelineState`.  Frontend polls ``GET /api/pipeline/status``
to receive updates regardless of which entry point triggered the pipeline.
"""

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PipelineProgress(str, Enum):
    """Pipeline execution phase."""

    IDLE = "idle"
    CAPTURING = "capturing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class _State:
    running: bool = False
    progress: PipelineProgress = PipelineProgress.IDLE
    source: str = ""               # "manual", "hotkey", "auto"
    started_at: float = 0.0
    last_result: Optional[dict] = None  # PipelineResult.to_dict()
    last_error: Optional[str] = None
    last_completed_at: float = 0.0
    pipeline_runs: int = 0
    history: list = field(default_factory=list)
    current_persona: str = ""


class PipelineState:
    """Thread-safe singleton that tracks pipeline execution state.

    All entry points (Route, HotkeyManager, future Auto monitor)
    write to the same instance.  Frontend reads via API polling.

    Usage::

        state = PipelineState.instance()
        state.set_running("manual")
        # ... pipeline executes ...
        state.set_completed(result)
    """

    _instance: Optional["PipelineState"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "PipelineState":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    _MAX_HISTORY = 50

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._state = _State()
        self._load_history()

    # ------------------------------------------------------------------
    # History persistence
    # ------------------------------------------------------------------

    def _history_file(self) -> "Path":
        from pathlib import Path
        from config.settings import Config
        return Config.get_project_root() / "data" / "history.json"

    def _load_history(self) -> None:
        """Load saved history from disk."""
        try:
            f = self._history_file()
            if f.exists():
                import json
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self._state.history = data[-self._MAX_HISTORY:]
        except Exception:
            pass

    def _save_history(self) -> None:
        """Persist history to disk as JSON."""
        try:
            import json
            f = self._history_file()
            f.parent.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self._state.history, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(f)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def instance(cls) -> "PipelineState":
        """Return the singleton instance."""
        return cls()

    # ------------------------------------------------------------------
    # Writer API (called by ManualPipeline / AutoPipeline / HotkeyManager)
    # ------------------------------------------------------------------

    def set_running(self, source: str) -> bool:
        """Mark the pipeline as running.

        Args:
            source: ``"manual"``, ``"hotkey"``, or ``"auto"``.

        Returns:
            ``True`` if the state was set (was idle).  ``False`` if the
            pipeline was already running (busy — caller should skip).
        """
        with self._lock:
            if self._state.running:
                return False  # Busy — caller should abort
            self._state.running = True
            self._state.progress = PipelineProgress.CAPTURING
            self._state.source = source
            self._state.started_at = time.time()
            self._state.last_error = None
            self._state.last_result = None
            # Desktop notification
            _notify("ScreenMate", "Capturing & analyzing screen...")
            return True

    def set_progress(self, progress: PipelineProgress) -> None:
        """Update the current phase.

        Args:
            progress: The new phase.
        """
        with self._lock:
            self._state.progress = progress

    def set_completed(self, result: dict) -> None:
        """Mark the pipeline as successfully completed.

        Args:
            result: The ``PipelineResult.to_dict()`` dict.
        """
        with self._lock:
            self._state.running = False
            self._state.progress = PipelineProgress.COMPLETED
            self._state.last_result = result
            self._state.last_completed_at = time.time()
            self._state.pipeline_runs += 1
            # Desktop notification
            model = result.get("vision", {}).get("model", "")
            lat = result.get("processing_time_ms", 0)
            _notify("ScreenMate — Analysis Complete",
                     f"Model: {model}  |  {lat:.0f}ms")
            # Add to history
            self._state.history.append({
                "timestamp": time.strftime("%H:%M:%S"),
                "vision_content": result.get("vision", {}).get("content", ""),
                "persona_content": result.get("chat", {}).get("content", ""),
                "vision_model": result.get("vision", {}).get("model", ""),
                "persona_name": result.get("persona", ""),
                "latency_ms": result.get("processing_time_ms", 0),
                "source": self._state.source,
                "prompt": result.get("prompt", {}).get("user_prompt", ""),
            })
            if len(self._state.history) > self._MAX_HISTORY:
                self._state.history = self._state.history[-self._MAX_HISTORY:]
            self._save_history()

    def set_failed(self, error: str) -> None:
        """Mark the pipeline as failed.

        Args:
            error: Human-readable error description.
        """
        with self._lock:
            self._state.running = False
            self._state.progress = PipelineProgress.FAILED
            self._state.last_error = error
            self._state.last_completed_at = time.time()
            self._state.pipeline_runs += 1
            _notify("ScreenMate — Failed", error[:120])

    # ------------------------------------------------------------------
    # Reader API (called by Routes — GET /api/pipeline/status)
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return a JSON-safe snapshot of the current pipeline state.

        Frontend polls this at ~500ms interval.
        """
        with self._lock:
            s = self._state
            elapsed = (
                time.time() - s.started_at if s.running and s.started_at else 0
            )
            return {
                "running": s.running,
                "progress": s.progress.value,
                "source": s.source,
                "elapsed_seconds": round(elapsed, 1),
                "last_result": s.last_result,
                "last_error": s.last_error,
                "last_completed_at": (
                    time.strftime(
                        "%H:%M:%S", time.localtime(s.last_completed_at)
                    )
                    if s.last_completed_at
                    else None
                ),
                "pipeline_runs": s.pipeline_runs,
                "history": list(s.history),
                "current_persona": s.current_persona,
            }

    def set_current_persona(self, name: str) -> None:
        """Set the active persona (persists across runs)."""
        with self._lock:
            self._state.current_persona = name

    def get_current_persona(self) -> str:
        """Get the active persona name."""
        with self._lock:
            return self._state.current_persona

    def is_busy(self) -> bool:
        """Return ``True`` if a pipeline is currently executing."""
        with self._lock:
            return self._state.running

    # ------------------------------------------------------------------
    # Reset (for tests)
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset to initial idle state."""
        with self._lock:
            self._state = _State()


# ------------------------------------------------------------------
# Module-level helper
# ------------------------------------------------------------------

def _notify(title: str, message: str) -> None:
    """Fire-and-forget desktop notification."""
    try:
        from modules.notifications.toaster import show
        show(title, message)
    except Exception:
        pass
