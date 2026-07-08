"""
Mock chat provider — returns canned responses without calling any API.

Replace with a real provider (OpenAI, Claude, Qwen, Ollama, etc.) by
dropping a new file into ``providers/chat/`` that subclasses
:class:`BaseChatProvider` and registers itself.
"""

import time
from typing import Any, Optional

from providers import register_provider
from providers.base.chat import BaseChatProvider
from providers.response import ProviderResponse
from modules.logger.logger import get_logger

logger = get_logger(__name__)


class MockChatProvider(BaseChatProvider):
    """Mock chat provider for development and testing.

    Always returns a successful :class:`ProviderResponse` with placeholder
    content.  Real providers should follow the same return contract.
    """

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Return a mock chat completion.

        Args:
            messages: List of message dicts (``role`` / ``content``).
            system_prompt: Optional system prompt (ignored in mock).
            **kwargs: Ignored.

        Returns:
            A :class:`ProviderResponse` with mock content.
        """
        t0 = time.perf_counter()

        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        logger.info(
            "MockChatProvider.chat: messages=%d, system_prompt=%s",
            len(messages),
            system_prompt[:60] if system_prompt else "(none)",
        )

        latency_ms = (time.perf_counter() - t0) * 1000

        return ProviderResponse.ok(
            provider=self.provider_name,
            model=self.model_name,
            content=(
                f"\U0001f4ac [Mock Chat] This is a simulated response.\n\n"
                f"You said: \"{last_user_msg[:100]}\"\n\n"
                f"As a mock chat provider, I always respond helpfully "
                f"but without any real AI behind me.  Replace me with "
                f"OpenAI, Claude, or your favourite LLM."
            ),
            latency_ms=round(latency_ms, 2),
            usage={"prompt_tokens": 80, "completion_tokens": 55},
            metadata={"message_count": len(messages)},
        )

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-chat-v1"


# Auto-register when the module is imported
register_provider("chat", "mock", MockChatProvider)
