"""
Auto-mode pipeline (stub).

In the future this will orchestrate the full auto-mode loop:
periodic screenshot → vision summary → context update → chat.
For now it delegates to :class:`AutoMonitor` while recording telemetry.
"""

import time
from typing import Optional

from modules.context.manager import ContextManager
from modules.logger.logger import get_logger
from modules.monitor.monitor import AutoMonitor
from modules.pipeline.pipeline_result import PipelineResult
from modules.telemetry.stats import StatsCollector

logger = get_logger(__name__)


class AutoPipeline:
    """Orchestrate the auto-mode workflow.

    Currently a thin wrapper around :class:`AutoMonitor` with telemetry
    hooks.  The real implementation will drive the full loop:
    screenshot → vision summary → context → chat.

    Usage::

        pipeline = AutoPipeline(context_manager, monitor, stats)
        result = pipeline.start(interval=20)
    """

    def __init__(
        self,
        context_manager: ContextManager,
        monitor: AutoMonitor,
        stats: StatsCollector,
    ) -> None:
        """Initialise the pipeline.

        Args:
            context_manager: Shared context instance.
            monitor: Auto-mode monitor module.
            stats: Telemetry collector.
        """
        self._ctx = context_manager
        self._monitor = monitor
        self._stats = stats
        logger.info("AutoPipeline initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, interval: Optional[int] = None) -> PipelineResult:
        """Start auto-mode monitoring.

        Args:
            interval: Screenshot interval in seconds.

        Returns:
            A :class:`PipelineResult` with the outcome.
        """
        t_start = time.perf_counter()
        self._ctx.set_mode("auto")

        result = self._monitor.start(interval=interval)

        if result.get("success"):
            self._stats.record_pipeline_run("auto")
            logger.info("AutoPipeline: started with interval=%ds", interval or 20)

        elapsed_ms = (time.perf_counter() - t_start) * 1000

        if result.get("success"):
            return PipelineResult.ok(
                message=result.get("message", "Auto mode started"),
                processing_time_ms=round(elapsed_ms, 2),
                data={"monitor_status": self._monitor.get_status()},
            )
        else:
            return PipelineResult.fail(
                error=result.get("message", "Failed to start auto mode"),
                processing_time_ms=round(elapsed_ms, 2),
            )

    def stop(self) -> PipelineResult:
        """Stop auto-mode monitoring.

        Returns:
            A :class:`PipelineResult` with the outcome.
        """
        t_start = time.perf_counter()
        self._ctx.set_mode("manual")

        result = self._monitor.stop()

        elapsed_ms = (time.perf_counter() - t_start) * 1000

        if result.get("success"):
            return PipelineResult.ok(
                message=result.get("message", "Auto mode stopped"),
                processing_time_ms=round(elapsed_ms, 2),
                data={"monitor_status": self._monitor.get_status()},
            )
        else:
            return PipelineResult.fail(
                error=result.get("message", "Failed to stop auto mode"),
                processing_time_ms=round(elapsed_ms, 2),
            )

    def get_status(self) -> PipelineResult:
        """Return the current auto-mode status.

        Returns:
            A :class:`PipelineResult` with monitor status data.
        """
        return PipelineResult.ok(
            message="Auto mode status",
            data={"monitor_status": self._monitor.get_status()},
        )
