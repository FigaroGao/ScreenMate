"""
OpenAI-compatible chat provider.

Uses the official ``openai`` SDK.  Works with any endpoint that
implements ``/v1/chat/completions``.
"""

import time
from typing import Any, Optional

from openai import (
    APIError, APITimeoutError, AuthenticationError,
    BadRequestError, OpenAI, PermissionDeniedError, RateLimitError,
)

from config.settings import Config
from providers import register_provider
from providers.base.chat import BaseChatProvider
from providers.response import ProviderResponse
from modules.logger.logger import get_logger

logger = get_logger(__name__)


class OpenAIChatProvider(BaseChatProvider):
    """Chat provider backed by any OpenAI-compatible API."""

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._api_key: str = Config.CHAT_API_KEY
        self._base_url: str = Config.CHAT_BASE_URL
        self._model: str = Config.CHAT_MODEL
        self._max_tokens: int = Config.CHAT_MAX_TOKENS
        self._temperature: float = Config.CHAT_TEMPERATURE
        self._top_p: float = Config.CHAT_TOP_P

    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Send messages to the chat API.

        Args:
            messages: List of ``{"role": "...", "content": "..."}``.
            system_prompt: Optional system instruction prepended to
                           messages.

        Returns:
            :class:`ProviderResponse`.
        """
        t_start = time.perf_counter()

        if not self._api_key:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Chat API key is not configured.",
            )
        if not self._base_url:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Chat Base URL is not configured.",
            )

        # Build full message list
        full_messages: list[dict] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        logger.info(
            "OpenAIChat: calling %s (model=%s, messages=%d)",
            self._base_url, self._model, len(full_messages),
        )

        try:
            client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=kwargs.pop("timeout", 60.0),
            )
            completion = client.chat.completions.create(
                model=self._model,
                messages=full_messages,
                max_tokens=kwargs.pop("max_tokens", self._max_tokens),
                temperature=kwargs.pop("temperature", self._temperature),
                top_p=kwargs.pop("top_p", self._top_p),
                **kwargs,
            )
            latency_ms = (time.perf_counter() - t_start) * 1000
            content = completion.choices[0].message.content or ""
            usage = {}
            if completion.usage:
                usage = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }

            logger.info("OpenAIChat: success — %.1fms", latency_ms)
            return ProviderResponse.ok(
                provider=self.provider_name,
                model=self._model,
                content=content,
                latency_ms=round(latency_ms, 2),
                usage=usage,
            )

        except AuthenticationError:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Authentication failed (401). Check your Chat API key.",
            )
        except PermissionDeniedError:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Permission denied (403).",
            )
        except RateLimitError:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Rate limited (429). Please wait and try again.",
            )
        except BadRequestError as exc:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Bad request (400): {exc}",
            )
        except APITimeoutError:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Request timed out.",
            )
        except APIError as exc:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"API error: {exc}",
            )
        except Exception as exc:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Unexpected error: {exc}",
            )

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model


register_provider("chat", "openai", OpenAIChatProvider)
