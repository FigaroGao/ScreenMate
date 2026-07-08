"""
Basic smoke tests for provider registration and mock responses.

Run with::

    python -m pytest tests/ -v
"""

import sys
from pathlib import Path

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import pytest

# Import provider packages to trigger registration
import providers.vision  # noqa: E402
import providers.chat    # noqa: E402
import providers.tts     # noqa: E402

from providers import list_providers, get_provider  # noqa: E402
from providers import create_vision, create_chat, create_tts  # noqa: E402
from providers.base.vision import BaseVisionProvider  # noqa: E402
from providers.base.chat import BaseChatProvider  # noqa: E402
from providers.base.tts import BaseTTSProvider  # noqa: E402
from providers.response import ProviderResponse  # noqa: E402


class TestProviderRegistry:
    """Ensure all mock providers are registered."""

    def test_vision_providers_registered(self) -> None:
        names = list_providers("vision")
        assert "mock" in names, f"Expected 'mock' in vision providers, got {names}"

    def test_chat_providers_registered(self) -> None:
        names = list_providers("chat")
        assert "mock" in names, f"Expected 'mock' in chat providers, got {names}"

    def test_tts_providers_registered(self) -> None:
        names = list_providers("tts")
        assert "mock" in names, f"Expected 'mock' in TTS providers, got {names}"

    def test_openai_vision_registered(self) -> None:
        names = list_providers("vision")
        assert "openai" in names, f"Expected 'openai' in vision providers, got {names}"

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ValueError):
            get_provider("vision", "nonexistent")


class TestMockVisionProvider:
    """Verify mock vision provider contract."""

    def test_is_subclass(self) -> None:
        cls = get_provider("vision", "mock")
        assert issubclass(cls, BaseVisionProvider)

    def test_analyze_returns_expected_structure(self) -> None:
        cls = get_provider("vision", "mock")
        provider = cls()
        result = provider.analyze(b"fake-image-data", prompt="What do you see?")
        assert result.success is True
        assert result.content
        assert result.model
        assert result.usage

    def test_provider_name_and_model_name(self) -> None:
        cls = get_provider("vision", "mock")
        provider = cls()
        assert provider.provider_name == "mock"
        assert len(provider.model_name) > 0


class TestMockChatProvider:
    """Verify mock chat provider contract."""

    def test_is_subclass(self) -> None:
        cls = get_provider("chat", "mock")
        assert issubclass(cls, BaseChatProvider)

    def test_chat_returns_expected_structure(self) -> None:
        cls = get_provider("chat", "mock")
        provider = cls()
        messages = [{"role": "user", "content": "Hello!"}]
        result = provider.chat(messages)
        assert result.success is True
        assert result.content
        assert result.model


class TestMockTTSProvider:
    """Verify mock TTS provider contract."""

    def test_is_subclass(self) -> None:
        cls = get_provider("tts", "mock")
        assert issubclass(cls, BaseTTSProvider)

    def test_synthesize_returns_expected_structure(self) -> None:
        cls = get_provider("tts", "mock")
        provider = cls()
        result = provider.synthesize("Hello world")
        assert result.success is True
        assert "placeholder.mp3" in result.content
        assert "duration_ms" in result.metadata


class TestProviderFactory:
    """Verify that factory methods create working instances."""

    def test_create_vision(self) -> None:
        provider = create_vision("mock")
        assert isinstance(provider, BaseVisionProvider)
        result = provider.analyze(b"data")
        assert isinstance(result, ProviderResponse)
        assert result.success is True

    def test_create_chat(self) -> None:
        provider = create_chat("mock")
        assert isinstance(provider, BaseChatProvider)
        result = provider.chat([{"role": "user", "content": "hi"}])
        assert isinstance(result, ProviderResponse)
        assert result.success is True

    def test_create_tts(self) -> None:
        provider = create_tts("mock")
        assert isinstance(provider, BaseTTSProvider)
        result = provider.synthesize("hello")
        assert isinstance(result, ProviderResponse)
        assert result.success is True

    def test_create_vision_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            create_vision("nonexistent")
