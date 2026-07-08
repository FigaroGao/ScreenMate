"""
Statistics collector for ScreenMate.

A thread-safe singleton that tracks every provider call, pipeline
execution, and mode transition.  The Dashboard reads live data from
this collector rather than displaying hard-coded placeholders.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from modules.logger.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CallRecord:
    """A single recorded call."""

    timestamp: float = 0.0
    provider_type: str = ""  # "vision", "chat", "tts"
    provider_name: str = ""
    model: str = ""
    latency_ms: float = 0.0
    success: bool = True
    pipeline: str = ""  # "manual", "auto"


@dataclass
class DashboardSnapshot:
    """All statistics needed by the Dashboard page."""

    app_name: str = ""
    app_version: str = ""
    uptime_seconds: float = 0.0

    vision_calls: int = 0
    chat_calls: int = 0
    tts_calls: int = 0
    screenshot_count: int = 0
    manual_mode_runs: int = 0
    auto_mode_runs: int = 0

    avg_latency_ms: float = 0.0
    total_calls: int = 0

    last_call: Optional[dict] = None
    context_message_count: int = 0
    context_mode: str = "manual"
    active_providers: dict[str, list[str]] = field(default_factory=dict)
    log_count: int = 0


class StatsCollector:
    """Thread-safe singleton that collects runtime statistics.

    Usage::

        stats = StatsCollector.instance()
        stats.record_call("vision", "mock", "mock-v1", 42.0, True, "manual")
        snapshot = stats.get_snapshot()
    """

    _instance: Optional["StatsCollector"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "StatsCollector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._start_time: float = time.time()
        self._records: list[CallRecord] = []
        self._max_records: int = 500

        # Counters
        self._vision_calls: int = 0
        self._chat_calls: int = 0
        self._tts_calls: int = 0
        self._screenshot_count: int = 0
        self._failed_calls: int = 0
        self._manual_runs: int = 0
        self._auto_runs: int = 0

        # Accumulated latency for averaging
        self._total_latency_ms: float = 0.0
        self._total_calls: int = 0

        # External references (set by app.py after init)
        self._context_manager: Optional[object] = None
        self._log_count_provider: Optional[callable] = None

        logger.info("StatsCollector initialised")

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def instance(cls) -> "StatsCollector":
        """Return the singleton instance (creates one if needed)."""
        return cls()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_call(
        self,
        provider_type: str,
        provider_name: str,
        model: str,
        latency_ms: float,
        success: bool,
        pipeline: str = "manual",
    ) -> None:
        """Record a single provider call.

        Args:
            provider_type: ``"vision"``, ``"chat"``, or ``"tts"``.
            provider_name: e.g. ``"mock"``, ``"openai"``.
            model: The model identifier used.
            latency_ms: Wall-clock time in milliseconds.
            success: Whether the call succeeded.
            pipeline: ``"manual"`` or ``"auto"``.
        """
        record = CallRecord(
            timestamp=time.time(),
            provider_type=provider_type,
            provider_name=provider_name,
            model=model,
            latency_ms=latency_ms,
            success=success,
            pipeline=pipeline,
        )
        with self._lock:
            self._records.append(record)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]

            # Increment typed counters
            if provider_type == "vision":
                self._vision_calls += 1
            elif provider_type == "chat":
                self._chat_calls += 1
            elif provider_type == "tts":
                self._tts_calls += 1
            elif provider_type == "screenshot":
                self._screenshot_count += 1

            if not success:
                self._failed_calls += 1

            self._total_latency_ms += latency_ms
            self._total_calls += 1

        logger.debug(
            "Stats: recorded %s call (%s/%s, %.1fms)",
            provider_type, provider_name, model, latency_ms,
        )

    def record_pipeline_run(self, pipeline: str) -> None:
        """Increment the counter for a pipeline type.

        Args:
            pipeline: ``"manual"`` or ``"auto"``.
        """
        with self._lock:
            if pipeline == "manual":
                self._manual_runs += 1
            elif pipeline == "auto":
                self._auto_runs += 1

    # ------------------------------------------------------------------
    # Snapshot (for Dashboard / API)
    # ------------------------------------------------------------------

    def get_snapshot(self) -> DashboardSnapshot:
        """Return a complete dashboard snapshot."""
        from config.settings import Config
        from providers import list_all_providers

        with self._lock:
            avg_lat = (
                round(self._total_latency_ms / self._total_calls, 1)
                if self._total_calls > 0
                else 0.0
            )

            last_call: Optional[dict] = None
            if self._records:
                r = self._records[-1]
                last_call = {
                    "timestamp": time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(r.timestamp)
                    ),
                    "provider_type": r.provider_type,
                    "provider_name": r.provider_name,
                    "model": r.model,
                    "latency_ms": r.latency_ms,
                    "success": r.success,
                    "pipeline": r.pipeline,
                }

            # Gather context info if available
            ctx_count = 0
            ctx_mode = "manual"
            if self._context_manager is not None:
                try:
                    ctx_count = self._context_manager.message_count
                    ctx_mode = getattr(self._context_manager, "_mode", "manual")
                except Exception:
                    pass

            # Log count
            log_count = 0
            if self._log_count_provider is not None:
                try:
                    log_count = self._log_count_provider()
                except Exception:
                    pass

        return DashboardSnapshot(
            app_name=Config.APP_NAME,
            app_version=Config.APP_VERSION,
            uptime_seconds=round(time.time() - self._start_time, 1),
            vision_calls=self._vision_calls,
            chat_calls=self._chat_calls,
            tts_calls=self._tts_calls,
            screenshot_count=self._screenshot_count,
            manual_mode_runs=self._manual_runs,
            auto_mode_runs=self._auto_runs,
            avg_latency_ms=avg_lat,
            total_calls=self._total_calls,
            last_call=last_call,
            context_message_count=ctx_count,
            context_mode=ctx_mode,
            active_providers=list_all_providers(),
            log_count=log_count,
        )

    def get_snapshot_dict(self) -> dict:
        """Return the snapshot as a JSON-safe dict."""
        s = self.get_snapshot()
        return {
            "app": {
                "name": s.app_name,
                "version": s.app_version,
            },
            "uptime_seconds": s.uptime_seconds,
            "calls": {
                "vision": s.vision_calls,
                "chat": s.chat_calls,
                "tts": s.tts_calls,
                "screenshots": s.screenshot_count,
                "total": s.total_calls,
            },
            "pipelines": {
                "manual_runs": s.manual_mode_runs,
                "auto_runs": s.auto_mode_runs,
            },
            "avg_latency_ms": s.avg_latency_ms,
            "last_call": s.last_call,
            "context": {
                "message_count": s.context_message_count,
                "mode": s.context_mode,
            },
            "providers": s.active_providers,
            "log_count": s.log_count,
        }

    # ------------------------------------------------------------------
    # External bindings (called once during app init)
    # ------------------------------------------------------------------

    def bind_context_manager(self, ctx_manager: object) -> None:
        """Bind the context manager for live message counts."""
        self._context_manager = ctx_manager

    def bind_log_counter(self, fn: callable) -> None:
        """Bind a function that returns the current log line count."""
        self._log_count_provider = fn

    # ------------------------------------------------------------------
    # Reset (for tests)
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all counters and records (useful in tests)."""
        with self._lock:
            self._start_time = time.time()
            self._records.clear()
            self._vision_calls = 0
            self._chat_calls = 0
            self._tts_calls = 0
            self._screenshot_count = 0
            self._failed_calls = 0
            self._manual_runs = 0
            self._auto_runs = 0
            self._total_latency_ms = 0.0
            self._total_calls = 0
        logger.info("StatsCollector reset")
