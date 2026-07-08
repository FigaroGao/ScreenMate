"""
Event type definitions for ScreenMate.

These are lightweight dataclasses / type definitions only.  No
listener registration or dispatch logic exists — the current
version calls pipelines directly.  Future versions (Agent Mode,
plugin system) can add a real event bus that publishes these events.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EventType(str, Enum):
    """All event types in the ScreenMate system."""

    HOTKEY_PRESSED = "hotkey_pressed"
    CAPTURE_STARTED = "capture_started"
    CAPTURE_FINISHED = "capture_finished"
    ANALYSIS_STARTED = "analysis_started"
    ANALYSIS_FINISHED = "analysis_finished"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"


@dataclass
class Event:
    """An event emitted during system operation.

    This is a data-only struct.  The event bus implementation is
    reserved for a future version.
    """

    type: EventType
    source: str = ""           # "manual", "hotkey", "auto"
    timestamp: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
