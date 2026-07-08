"""
Context Manager for ScreenMate.

Manages conversation history, memory, and summaries using an in-memory
``collections.deque``.  Future versions will support SQLite, Redis, and
RAG backends — the public API is designed to remain stable across those
changes.

Concepts:
    **Session** — a labelled interaction period (e.g. "morning coding").
    **Conversation** — the full message history (deque).
    **Summary** — a condensed version of recent context.
    **Memory** — key-value facts that persist across sessions.
"""

import time as _time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from config.settings import Config
from modules.logger.logger import get_logger

logger = get_logger(__name__)


# ======================================================================
# Dataclasses
# ======================================================================


@dataclass
class ContextMessage:
    """A single message in the conversation history."""

    role: str  # "system", "user", "assistant"
    content: str
    timestamp: float = 0.0


@dataclass
class ContextState:
    """Snapshot of the current context state (for API responses)."""

    total_messages: int = 0
    max_length: int = 50
    has_summary: bool = False
    summary_length: int = 0
    mode: str = "manual"
    session_name: str = ""
    memory_count: int = 0
    recent_messages: list[dict] = field(default_factory=list)


# ======================================================================
# ContextManager
# ======================================================================


class ContextManager:
    """Manages conversation context for ScreenMate.

    Currently backed by an in-memory deque.  Supports:

    - Session management (named interaction periods)
    - Conversation history (add / retrieve / clear)
    - Summary generation (mock for now)
    - Persistent memory (key-value store in memory)

    All methods are synchronous; future async backends can be added
    without changing the public API.
    """

    def __init__(self, max_length: Optional[int] = None) -> None:
        """Initialise the context manager.

        Args:
            max_length: Maximum number of messages to retain.
                Defaults to :attr:`Config.AUTO_CONTEXT_MAX_LENGTH`.
        """
        self._max_length = max_length or Config.AUTO_CONTEXT_MAX_LENGTH
        self._history: deque[ContextMessage] = deque(maxlen=self._max_length)
        self._summary: str = ""
        self._mode: str = "manual"

        # ---- Session ----
        self._session_name: str = ""
        self._session_start: float = 0.0

        # ---- Memory (key-value store persisting across clears) ----
        self._memory: dict[str, str] = {}

        logger.info(
            "ContextManager initialised (max_length=%d, backend=memory)",
            self._max_length,
        )

    # ==================================================================
    # Conversation
    # ==================================================================

    def add_message(self, role: str, content: str) -> None:
        """Append a message to the conversation history.

        Args:
            role: ``"system"``, ``"user"``, or ``"assistant"``.
            content: The message body.
        """
        msg = ContextMessage(role=role, content=content, timestamp=_time.time())
        self._history.append(msg)
        logger.debug("Context: added %s message (len=%d chars)", role, len(content))

    def get_history(self, limit: Optional[int] = None) -> list[dict]:
        """Return recent conversation history.

        Args:
            limit: If set, return only the most recent *limit* messages.

        Returns:
            A list of message dicts with ``role`` and ``content`` keys.
        """
        messages = list(self._history)
        if limit:
            messages = messages[-limit:]
        return [{"role": m.role, "content": m.content} for m in messages]

    def get_history_for_api(self) -> list[dict]:
        """Return history formatted for an LLM API call."""
        return self.get_history()

    def get_conversation(self) -> dict:
        """Return the full conversation as a structured dict."""
        return {
            "session_name": self._session_name or "(unnamed)",
            "session_elapsed_s": (
                round(_time.time() - self._session_start, 1)
                if self._session_start
                else 0
            ),
            "message_count": len(self._history),
            "messages": self.get_history(),
        }

    # ==================================================================
    # Summary
    # ==================================================================

    def generate_summary(self) -> str:
        """Generate a (mock) summary of the current context.

        In the future this will call a real LLM to summarise.
        """
        msg_count = len(self._history)
        if msg_count == 0:
            self._summary = "(empty context)"
        else:
            total_chars = sum(len(m.content) for m in self._history)
            self._summary = (
                f"[Mock Summary] {msg_count} messages, "
                f"~{total_chars} chars total. "
                f"Last message from: {self._history[-1].role}."
            )
        logger.info("Context: generated summary (%d chars)", len(self._summary))
        return self._summary

    def get_summary(self) -> str:
        """Return the current summary (generates one if needed)."""
        if not self._summary:
            self.generate_summary()
        return self._summary

    def clear_summary(self) -> None:
        """Clear only the summary, keeping conversation intact."""
        self._summary = ""
        logger.debug("Context: summary cleared")

    # ==================================================================
    # Session
    # ==================================================================

    def start_session(self, name: str = "") -> dict:
        """Begin a named session.

        Args:
            name: Label for this session (e.g. "morning coding").

        Returns:
            A dict with session metadata.
        """
        self._session_name = name
        self._session_start = _time.time()
        logger.info("Context: session started '%s'", name or "(unnamed)")
        return {
            "name": self._session_name or "(unnamed)",
            "start_time": self._session_start,
        }

    def end_session(self) -> dict:
        """End the current session and return its summary.

        Returns:
            A dict with session metadata.
        """
        elapsed = _time.time() - self._session_start if self._session_start else 0
        name = self._session_name or "(unnamed)"
        logger.info("Context: session ended '%s' (elapsed=%.1fs)", name, elapsed)
        self._session_name = ""
        self._session_start = 0.0
        return {
            "name": name,
            "elapsed_seconds": round(elapsed, 1),
            "message_count": len(self._history),
        }

    def get_session_info(self) -> dict:
        """Return the current session metadata."""
        return {
            "name": self._session_name or "(unnamed)",
            "elapsed_seconds": (
                round(_time.time() - self._session_start, 1)
                if self._session_start
                else 0
            ),
        }

    # ==================================================================
    # Memory (persistent key-value store)
    # ==================================================================

    def set_memory(self, key: str, value: str) -> None:
        """Store a fact in persistent memory.

        Memory entries survive :meth:`clear` / :meth:`clear_history`.

        Args:
            key: Unique key for this memory item.
            value: The value to store.
        """
        self._memory[key] = value
        logger.debug("Context memory set: %s", key)

    def get_memory(self, key: str) -> Optional[str]:
        """Retrieve a fact from persistent memory.

        Args:
            key: The memory key.

        Returns:
            The stored value, or ``None`` if not found.
        """
        return self._memory.get(key)

    def delete_memory(self, key: str) -> bool:
        """Delete a memory entry.

        Args:
            key: The memory key.

        Returns:
            ``True`` if deleted, ``False`` if not found.
        """
        if key in self._memory:
            del self._memory[key]
            logger.debug("Context memory deleted: %s", key)
            return True
        return False

    def list_memory(self) -> dict[str, str]:
        """Return all memory entries."""
        return dict(self._memory)

    def clear_memory(self) -> None:
        """Clear all persistent memory entries."""
        self._memory.clear()
        logger.info("Context: memory cleared")

    # ==================================================================
    # Bulk operations
    # ==================================================================

    def get_context_string(self) -> str:
        """Return the full context as a single formatted string.

        Useful for injecting into prompts.
        """
        parts: list[str] = []
        if self._summary:
            parts.append(f"[Summary]\n{self._summary}\n")
        if self._memory:
            parts.append("[Memory]")
            for k, v in self._memory.items():
                parts.append(f"  {k}: {v}")
            parts.append("")
        for m in self._history:
            parts.append(f"[{m.role.upper()}]\n{m.content}\n")
        return "\n".join(parts)

    def clear(self) -> None:
        """Clear all history and summary.

        Memory entries are preserved — use :meth:`clear_memory`
        to remove those as well.
        """
        self._history.clear()
        self._summary = ""
        logger.info("Context: cleared history and summary")

    def clear_history(self) -> None:
        """Clear only conversation history (alias)."""
        self.clear()

    def clear_all(self) -> None:
        """Clear everything: history, summary, and memory."""
        self._history.clear()
        self._summary = ""
        self._memory.clear()
        logger.info("Context: cleared everything")

    def set_mode(self, mode: str) -> None:
        """Set the current context mode (``"manual"`` or ``"auto"``).

        Args:
            mode: The new mode name.
        """
        self._mode = mode
        logger.info("Context: mode set to %s", mode)

    # ==================================================================
    # State snapshot
    # ==================================================================

    def get_state(self) -> ContextState:
        """Return a snapshot of the current context state."""
        recent = [
            {"role": m.role, "content": m.content[:200]}
            for m in list(self._history)[-5:]
        ]
        return ContextState(
            total_messages=len(self._history),
            max_length=self._max_length,
            has_summary=bool(self._summary),
            summary_length=len(self._summary),
            mode=self._mode,
            session_name=self._session_name or "(unnamed)",
            memory_count=len(self._memory),
            recent_messages=recent,
        )

    # ==================================================================
    # Properties
    # ==================================================================

    @property
    def message_count(self) -> int:
        """Return the number of messages in history."""
        return len(self._history)

    @property
    def max_length(self) -> int:
        """Return the maximum history length."""
        return self._max_length

    @property
    def mode(self) -> str:
        """Return the current context mode."""
        return self._mode
