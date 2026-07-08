"""
Lightweight service locator for ScreenMate singletons.

Populated once during app startup (in ``app.py``).  Routes and other
modules import from here to avoid circular imports with ``app.py``.
"""

from typing import Any, Optional

# -- Pipelines --
_manual_pipeline: Any = None
_auto_pipeline: Any = None

# -- Core modules --
_context_manager: Any = None
_screenshot_capture: Any = None
_auto_monitor: Any = None

# -- Infrastructure --
_stats_collector: Any = None
_settings_manager: Any = None
_prompt_manager: Any = None
_log_manager: Any = None


# ======================================================================
# Setters (called once from app.py)
# ======================================================================


def setup(
    *,
    manual_pipeline: Any = None,
    auto_pipeline: Any = None,
    context_manager: Any = None,
    screenshot_capture: Any = None,
    auto_monitor: Any = None,
    stats_collector: Any = None,
    settings_manager: Any = None,
    prompt_manager: Any = None,
    log_manager: Any = None,
) -> None:
    """Wire all singletons into the locator."""
    globals().update({
        "_manual_pipeline": manual_pipeline or _manual_pipeline,
        "_auto_pipeline": auto_pipeline or _auto_pipeline,
        "_context_manager": context_manager or _context_manager,
        "_screenshot_capture": screenshot_capture or _screenshot_capture,
        "_auto_monitor": auto_monitor or _auto_monitor,
        "_stats_collector": stats_collector or _stats_collector,
        "_settings_manager": settings_manager or _settings_manager,
        "_prompt_manager": prompt_manager or _prompt_manager,
        "_log_manager": log_manager or _log_manager,
    })


# ======================================================================
# Getters (used by routes and other modules)
# ======================================================================


def get_manual_pipeline() -> Any:
    return _manual_pipeline


def get_auto_pipeline() -> Any:
    return _auto_pipeline


def get_context_manager() -> Any:
    return _context_manager


def get_screenshot_capture() -> Any:
    return _screenshot_capture


def get_auto_monitor() -> Any:
    return _auto_monitor


def get_stats_collector() -> Any:
    return _stats_collector


def get_settings_manager() -> Any:
    return _settings_manager


def get_prompt_manager() -> Any:
    return _prompt_manager


def get_log_manager() -> Any:
    return _log_manager
