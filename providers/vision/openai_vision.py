"""
OpenAI-compatible vision provider.

Uses the official ``openai`` Python SDK to call any OpenAI-compatible
Vision API (OpenAI, OpenRouter, SiliconFlow, NewAPI, OneAPI, Qwen,
local llama.cpp, Ollama, etc.).

All errors are caught and returned as :class:`ProviderResponse` — this
provider never raises exceptions to the caller.
"""

import base64
import time
from typing import Any, Optional

from openai import (
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from config.settings import Config
from providers import register_provider
from providers.base.vision import BaseVisionProvider
from providers.response import ProviderResponse
from modules.logger.logger import get_logger
import json

logger = get_logger(__name__)


class OpenAIVisionProvider(BaseVisionProvider):
    """Vision provider backed by any OpenAI-compatible API.

    Works with any endpoint that implements the
    ``/v1/chat/completions`` interface with vision support,
    including:
    - OpenAI (gpt-4o, gpt-4-turbo)
    - OpenRouter
    - SiliconFlow
    - NewAPI / OneAPI
    - Ollama (with vision models)
    - LM Studio (with vision models)
    """

    def __init__(self, config: Any = None) -> None:
        """Initialise the provider from Config.

        Args:
            config: Optional config override (defaults to :class:`Config`).
        """
        super().__init__(config)
        self._api_key: str = Config.VISION_API_KEY
        self._base_url: str = Config.VISION_BASE_URL
        self._model: str = Config.VISION_MODEL_NAME
        self._max_tokens: int = Config.VISION_MAX_TOKENS
        self._temperature: float = Config.VISION_TEMPERATURE
        self._top_p: float = Config.VISION_TOP_P

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        image_data: bytes,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> ProviderResponse:
        """Analyze an image using the OpenAI-compatible Vision API.

        Args:
            image_data: Raw image bytes (PNG/JPEG).
            prompt: User prompt text.  Defaults to "Describe this image."
            system_prompt: Optional system-level instruction.
            **kwargs: Additional parameters passed through to the API.

        Returns:
            A :class:`ProviderResponse` — always, even on failure.
        """
        t_start = time.perf_counter()

        # Validate minimal config
        if not self._api_key:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Vision API key is not configured.  Set VISION_API_KEY in .env.",
            )
        if not self._base_url:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Vision Base URL is not configured.  Set VISION_BASE_URL in .env.",
            )

        # Build the image payload
        try:
            b64 = base64.b64encode(image_data).decode("ascii")
            mime = self._detect_mime(image_data)
            image_url = f"data:{mime};base64,{b64}"
        except Exception as exc:
            logger.error("Failed to encode image: %s", exc)
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Image encoding failed: {exc}",
            )

        # Build messages
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_content: list[dict] = [
            {"type": "text", "text": prompt or "Describe this image."},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
        messages.append({"role": "user", "content": user_content})

        logger.info(
            "OpenAIVision: calling %s (model=%s, image=%d bytes, prompt_len=%d)",
            self._base_url,
            self._model,
            len(image_data),
            len(prompt or ""),
        )

        # Call the API
        try:
            client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=kwargs.pop("timeout", 60.0),
            )

            # Merge custom params
            custom = self._parse_custom_params(Config.VISION_CUSTOM_PARAMS)
            for k, v in custom.items():
                kwargs.setdefault(k, v)

            completion = client.chat.completions.create(
                model=self._model,
                messages=messages,
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

            logger.info(
                "OpenAIVision: success — %.1fms, tokens=%s",
                latency_ms,
                usage.get("total_tokens", "?"),
            )

            return ProviderResponse.ok(
                provider=self.provider_name,
                model=self._model,
                content=content,
                latency_ms=round(latency_ms, 2),
                usage=usage,
                metadata={
                    "image_size_bytes": len(image_data),
                    "mime_type": mime,
                },
            )

        # ---- Error handling: every OpenAI error → ProviderResponse.fail ----

        except AuthenticationError as exc:
            latency_ms = (time.perf_counter() - t_start) * 1000
            logger.error("OpenAIVision: authentication failed (401)")
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Authentication failed (401). Check your API key.",
                latency_ms=round(latency_ms, 2),
            )

        except PermissionDeniedError as exc:
            latency_ms = (time.perf_counter() - t_start) * 1000
            logger.error("OpenAIVision: permission denied (403)")
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Permission denied (403). Your API key may not have access to this model.",
                latency_ms=round(latency_ms, 2),
            )

        except RateLimitError as exc:
            latency_ms = (time.perf_counter() - t_start) * 1000
            logger.error("OpenAIVision: rate limited (429)")
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Rate limited (429). Please wait and try again.",
                latency_ms=round(latency_ms, 2),
            )

        except BadRequestError as exc:
            latency_ms = (time.perf_counter() - t_start) * 1000
            logger.error("OpenAIVision: bad request (400): %s", exc)
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Bad request (400): {exc}",
                latency_ms=round(latency_ms, 2),
            )

        except APITimeoutError:
            latency_ms = (time.perf_counter() - t_start) * 1000
            logger.error("OpenAIVision: request timed out")
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Request timed out. The API did not respond in time.",
                latency_ms=round(latency_ms, 2),
            )

        except APIError as exc:
            latency_ms = (time.perf_counter() - t_start) * 1000
            status = getattr(exc, "status_code", "?")
            logger.error("OpenAIVision: API error (HTTP %s): %s", status, exc)
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"API error (HTTP {status}): {exc}",
                latency_ms=round(latency_ms, 2),
            )

        except Exception as exc:
            latency_ms = (time.perf_counter() - t_start) * 1000
            logger.error("OpenAIVision: unexpected error: %s", exc)
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Unexpected error: {exc}",
                latency_ms=round(latency_ms, 2),
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_mime(data: bytes) -> str:
        """Detect MIME type from magic bytes."""
        if data[:4] == b"\x89PNG":
            return "image/png"
        if data[:2] == b"\xff\xd8":
            return "image/jpeg"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        return "image/png"  # fallback


# Auto-register
    @staticmethod
    def _parse_custom_params(raw: str) -> dict:
        """Parse custom params JSON and auto-convert types."""
        if not raw:
            return {}
        try:
            items = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(items, list):
                return {}
            result = {}
            for p in items:
                name = p.get("name", "").strip()
                val = p.get("value", "")
                if not name:
                    continue
                # Auto-convert numeric and boolean values
                if isinstance(val, str):
                    if val.lower() in ("true", "false"):
                        val = val.lower() == "true"
                    else:
                        try:
                            if "." in val:
                                val = float(val)
                            else:
                                val = int(val)
                        except ValueError:
                            pass
                result[name] = val
            return result
        except (json.JSONDecodeError, TypeError):
            return {}


register_provider("vision", "openai", OpenAIVisionProvider)
