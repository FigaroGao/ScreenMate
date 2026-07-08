"""Tests for OpenAIVisionProvider (API calls are mocked)."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import pytest
from unittest.mock import patch, MagicMock

from providers.vision.openai_vision import OpenAIVisionProvider
from providers.response import ProviderResponse


# Tiny valid 1x1 PNG for testing
_MOCK_PNG = (
    b"\x89PNG\r\n\x1a\n"           # header
    b"\x00\x00\x00\r"              # chunk len
    b"IHDR"                        # chunk type
    b"\x00\x00\x00\x01"            # width=1
    b"\x00\x00\x00\x01"            # height=1
    b"\x08\x02\x00\x00\x00"        # bit depth, color type, etc.
    b"\x90wS\xde"                  # crc
    b"\x00\x00\x00\x0b"            # chunk len
    b"IDAT"                        # chunk type
    b"x\x9cc\x00\x01\x00\x00\x05\x00\x01"  # compressed pixel
    b"\r\xe0\xc9\x80"              # crc
    b"\x00\x00\x00\x00"            # chunk len
    b"IEND"                        # chunk type
    b"\xaeB`\x82"                  # crc
)


class TestOpenAIVisionProviderRegistration:
    """Verify the provider is registered."""

    def test_is_registered(self) -> None:
        from providers import get_provider
        cls = get_provider("vision", "openai")
        assert cls is OpenAIVisionProvider

    def test_provider_name(self) -> None:
        provider = OpenAIVisionProvider()
        assert provider.provider_name == "openai"


class TestOpenAIVisionProviderErrors:
    """Verify error handling without network."""

    def test_no_api_key_returns_failure(self) -> None:
        provider = OpenAIVisionProvider()
        # Override with empty key
        provider._api_key = ""
        result = provider.analyze(_MOCK_PNG, prompt="test")
        assert isinstance(result, ProviderResponse)
        assert result.success is False
        assert "key" in result.error.lower()

    def test_no_base_url_returns_failure(self) -> None:
        provider = OpenAIVisionProvider()
        provider._api_key = "sk-test"
        provider._base_url = ""
        result = provider.analyze(_MOCK_PNG, prompt="test")
        assert isinstance(result, ProviderResponse)
        assert result.success is False
        assert "base url" in result.error.lower()


class TestOpenAIVisionProviderSuccessfulCall:
    """Verify successful API call with mocked OpenAI client."""

    def test_successful_call(self) -> None:
        provider = OpenAIVisionProvider()
        provider._api_key = "sk-test"
        provider._base_url = "https://api.openai.com/v1"

        mock_choice = MagicMock()
        mock_choice.message.content = "I see a red pixel."

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = mock_usage

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch(
            "providers.vision.openai_vision.OpenAI",
            return_value=mock_client,
        ):
            result = provider.analyze(
                _MOCK_PNG,
                prompt="What color is this?",
                system_prompt="You are a color expert.",
            )

        assert isinstance(result, ProviderResponse)
        assert result.success is True
        assert result.content == "I see a red pixel."
        assert result.model == provider.model_name
        assert result.usage["prompt_tokens"] == 100
        assert result.usage["completion_tokens"] == 50
        assert result.usage["total_tokens"] == 150
        assert result.latency_ms >= 0

    def test_passes_system_prompt(self) -> None:
        provider = OpenAIVisionProvider()
        provider._api_key = "sk-test"
        provider._base_url = "https://api.openai.com/v1"

        mock_choice = MagicMock()
        mock_choice.message.content = "OK"

        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_completion.usage = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        with patch(
            "providers.vision.openai_vision.OpenAI",
            return_value=mock_client,
        ):
            result = provider.analyze(
                _MOCK_PNG,
                prompt="test",
                system_prompt="SYSTEM: be brief.",
            )

        assert result.success is True
        # Verify the call args included the system prompt
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert messages[0]["role"] == "system"
        assert "SYSTEM: be brief." in messages[0]["content"]


class TestOpenAIVisionProviderHTTPErrors:
    """Verify HTTP error handling."""

    def _setup_provider(self):
        provider = OpenAIVisionProvider()
        provider._api_key = "sk-test"
        provider._base_url = "https://api.openai.com/v1"
        return provider

    def test_authentication_error(self) -> None:
        from openai import AuthenticationError

        provider = self._setup_provider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = AuthenticationError(
            "Invalid API key",
            response=MagicMock(),
            body=None,
        )
        with patch(
            "providers.vision.openai_vision.OpenAI",
            return_value=mock_client,
        ):
            result = provider.analyze(_MOCK_PNG)
        assert result.success is False
        assert "401" in result.error or "Authentication" in result.error

    def test_rate_limit_error(self) -> None:
        from openai import RateLimitError

        provider = self._setup_provider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RateLimitError(
            "Too many requests",
            response=MagicMock(),
            body=None,
        )
        with patch(
            "providers.vision.openai_vision.OpenAI",
            return_value=mock_client,
        ):
            result = provider.analyze(_MOCK_PNG)
        assert result.success is False
        assert "429" in result.error or "Rate" in result.error

    def test_permission_denied_error(self) -> None:
        from openai import PermissionDeniedError

        provider = self._setup_provider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = PermissionDeniedError(
            "Forbidden",
            response=MagicMock(),
            body=None,
        )
        with patch(
            "providers.vision.openai_vision.OpenAI",
            return_value=mock_client,
        ):
            result = provider.analyze(_MOCK_PNG)
        assert result.success is False
        assert "403" in result.error or "Permission" in result.error

    def test_timeout_error(self) -> None:
        from openai import APITimeoutError

        provider = self._setup_provider()
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = APITimeoutError(
            "Request timed out"
        )
        with patch(
            "providers.vision.openai_vision.OpenAI",
            return_value=mock_client,
        ):
            result = provider.analyze(_MOCK_PNG)
        assert result.success is False
        assert "timed out" in result.error.lower()
