"""
Unified logger for ScreenMate.

All modules should import ``get_logger`` from here rather than using
the standard library ``logging`` directly.  This ensures:
- Consistent formatting
- Log file rotation
- Centralised level control via Config

Additionally, :class:`LogManager` provides structured API call logging
that the Dashboard can query.
"""

import logging
import sys
import time
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from config.settings import Config


# ======================================================================
# LoggerManager (underlying loggers)
# ======================================================================


class LoggerManager:
    """Singleton-style manager that creates and caches named loggers.

    Every logger returned by :meth:`get_logger` shares the same
    handlers (console + rotating file), format, and level.
    """

    _instance: Optional["LoggerManager"] = None
    _loggers: dict[str, logging.Logger] = {}

    def __new__(cls) -> "LoggerManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._log_dir = Config.get_log_dir()
        self._log_dir.mkdir(parents=True, exist_ok=True)

        self._level = getattr(logging, Config.LOG_LEVEL.upper(), logging.DEBUG)
        self._formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Ensure the root logger doesn't propagate to third-party noise
        logging.getLogger().setLevel(logging.WARNING)

    def get_logger(self, name: str) -> logging.Logger:
        """Return (or create) a logger with the given *name*.

        Args:
            name: Typically ``__name__`` from the calling module.

        Returns:
            A configured :class:`logging.Logger` instance.
        """
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(self._level)
        logger.propagate = False

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._level)
        console_handler.setFormatter(self._formatter)
        logger.addHandler(console_handler)

        # Rotating file handler
        log_file = self._log_dir / "screenmate.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=Config.LOG_MAX_FILES,
            encoding="utf-8",
        )
        file_handler.setLevel(self._level)
        file_handler.setFormatter(self._formatter)
        logger.addHandler(file_handler)

        self._loggers[name] = logger
        return logger

    def get_recent_logs(self, count: int = 100) -> list[dict]:
        """Return the most recent *count* log lines from the log file."""
        log_file = self._log_dir / "screenmate.log"
        if not log_file.exists():
            return []
        lines: list[dict] = []
        with open(log_file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                parts = line.split("|")
                if len(parts) >= 4:
                    lines.append({
                        "timestamp": parts[0].strip(),
                        "level": parts[1].strip(),
                        "module": parts[2].strip(),
                        "message": "|".join(parts[3:]).strip(),
                    })
                else:
                    lines.append({
                        "timestamp": "",
                        "level": "INFO",
                        "module": "",
                        "message": line,
                    })
        return lines[-count:]

    def clear_logs(self) -> None:
        """Truncate the log file."""
        log_file = self._log_dir / "screenmate.log"
        if log_file.exists():
            log_file.write_text("", encoding="utf-8")

    @property
    def log_count(self) -> int:
        """Return the current number of log lines."""
        log_file = self._log_dir / "screenmate.log"
        if not log_file.exists():
            return 0
        with open(log_file, "r", encoding="utf-8") as fh:
            return sum(1 for _ in fh)


# ======================================================================
# LogManager — structured API call logger
# ======================================================================


class LogManager:
    """Structured logger for API / pipeline calls.

    Stores call records in a memory buffer so the Dashboard can display
    recent provider invocations without parsing the flat log file.

    Usage::

        lm = LogManager.instance()
        lm.record_api_call(
            provider="openai",
            provider_type="vision",
            pipeline="manual",
            latency_ms=1234.5,
            status="success",
            error=None,
        )
    """

    _instance: Optional["LogManager"] = None
    _max_records: int = 200

    def __new__(cls) -> "LogManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._records: deque[dict] = deque(maxlen=self._max_records)
        self._api_logger = get_logger("api_calls")

    @classmethod
    def instance(cls) -> "LogManager":
        """Return the singleton instance."""
        return cls()

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_api_call(
        self,
        provider: str,
        provider_type: str,
        pipeline: str,
        latency_ms: float,
        status: str = "success",
        error: Optional[str] = None,
    ) -> None:
        """Record a structured API call entry.

        Args:
            provider: Provider name (e.g. ``"mock"``).
            provider_type: ``"vision"``, ``"chat"``, or ``"tts"``.
            pipeline: ``"manual"`` or ``"auto"``.
            latency_ms: Wall-clock time in milliseconds.
            status: ``"success"`` or ``"error"``.
            error: Error message if status is ``"error"``.
        """
        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "provider": provider,
            "provider_type": provider_type,
            "pipeline": pipeline,
            "latency_ms": round(latency_ms, 2),
            "status": status,
            "error": error,
        }
        self._records.append(record)

        # Also write a structured line to the standard log
        msg = (
            f"API | {provider_type}/{provider} | {pipeline} | "
            f"{status} | {latency_ms:.1f}ms"
        )
        if error:
            msg += f" | error={error}"
        if status == "error":
            self._api_logger.error(msg)
        else:
            self._api_logger.info(msg)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_recent_calls(self, count: int = 50) -> list[dict]:
        """Return the most recent API call records.

        Args:
            count: Maximum number of records.

        Returns:
            A list of call dicts, newest last.
        """
        records = list(self._records)
        return records[-count:]

    def get_call_stats(self) -> dict:
        """Return aggregate statistics across all recorded calls."""
        records = list(self._records)
        if not records:
            return {"total": 0}

        success = sum(1 for r in records if r["status"] == "success")
        failed = sum(1 for r in records if r["status"] == "error")
        latencies = [r["latency_ms"] for r in records]

        return {
            "total": len(records),
            "success": success,
            "failed": failed,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
            "min_latency_ms": round(min(latencies), 1),
            "max_latency_ms": round(max(latencies), 1),
        }

    def clear(self) -> None:
        """Clear all recorded API calls."""
        self._records.clear()
        self._api_logger.info("API call log cleared")


# ======================================================================
# Module-level convenience
# ======================================================================

_manager = LoggerManager()


def get_logger(name: str) -> logging.Logger:
    """Convenience function to obtain a named logger.

    Usage::

        from modules.logger.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Hello from my module")
    """
    return _manager.get_logger(name)


def get_recent_logs(count: int = 100) -> list[dict]:
    """Convenience wrapper around LoggerManager.get_recent_logs."""
    return _manager.get_recent_logs(count)


def clear_logs() -> None:
    """Convenience wrapper around LoggerManager.clear_logs."""
    return _manager.clear_logs()
