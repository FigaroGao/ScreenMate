"""Tests for ContextManager (session, conversation, summary, memory)."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from modules.context.manager import ContextManager


class TestContextConversation:
    """Tests for conversation history."""

    def test_add_and_get_messages(self) -> None:
        ctx = ContextManager(max_length=100)
        ctx.add_message("user", "Hello")
        ctx.add_message("assistant", "Hi there")
        history = ctx.get_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_limit(self) -> None:
        ctx = ContextManager(max_length=100)
        for i in range(10):
            ctx.add_message("user", f"msg {i}")
        limited = ctx.get_history(limit=3)
        assert len(limited) == 3

    def test_clear(self) -> None:
        ctx = ContextManager(max_length=100)
        ctx.add_message("user", "test")
        ctx.clear()
        assert ctx.message_count == 0


class TestContextSession:
    """Tests for session management."""

    def test_start_and_end_session(self) -> None:
        ctx = ContextManager()
        info = ctx.start_session("coding")
        assert info["name"] == "coding"

        session_info = ctx.get_session_info()
        assert session_info["name"] == "coding"

        end_info = ctx.end_session()
        assert end_info["name"] == "coding"
        assert end_info["elapsed_seconds"] >= 0

    def test_unnamed_session(self) -> None:
        ctx = ContextManager()
        info = ctx.start_session()
        assert "(unnamed)" in info["name"]


class TestContextMemory:
    """Tests for persistent memory."""

    def test_set_and_get_memory(self) -> None:
        ctx = ContextManager()
        ctx.set_memory("user_name", "Alice")
        assert ctx.get_memory("user_name") == "Alice"
        assert ctx.get_memory("nonexistent") is None

    def test_delete_memory(self) -> None:
        ctx = ContextManager()
        ctx.set_memory("key1", "val1")
        assert ctx.delete_memory("key1") is True
        assert ctx.delete_memory("key1") is False

    def test_memory_survives_clear(self) -> None:
        ctx = ContextManager()
        ctx.add_message("user", "hello")
        ctx.set_memory("persistent", "value")
        ctx.clear()  # clears history, NOT memory
        assert ctx.message_count == 0
        assert ctx.get_memory("persistent") == "value"

    def test_list_memory(self) -> None:
        ctx = ContextManager()
        ctx.set_memory("a", "1")
        ctx.set_memory("b", "2")
        mem = ctx.list_memory()
        assert mem == {"a": "1", "b": "2"}

    def test_clear_all(self) -> None:
        ctx = ContextManager()
        ctx.add_message("user", "test")
        ctx.set_memory("key", "val")
        ctx.clear_all()
        assert ctx.message_count == 0
        assert ctx.get_memory("key") is None


class TestContextSummary:
    """Tests for context summary."""

    def test_generate_summary_empty(self) -> None:
        ctx = ContextManager()
        summary = ctx.generate_summary()
        assert "empty" in summary.lower()

    def test_generate_summary_with_messages(self) -> None:
        ctx = ContextManager()
        ctx.add_message("user", "Hello")
        ctx.add_message("assistant", "Hi")
        summary = ctx.generate_summary()
        assert "2 messages" in summary


class TestContextState:
    """Tests for ContextState snapshot."""

    def test_state_snapshot(self) -> None:
        ctx = ContextManager()
        ctx.add_message("user", "test")
        ctx.set_memory("key", "val")
        state = ctx.get_state()
        assert state.total_messages == 1
        assert state.memory_count == 1
        assert state.mode == "manual"
