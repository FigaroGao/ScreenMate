"""
OpenAI-compatible TTS provider.

Uses the OpenAI SDK's ``audio.speech`` endpoint.  Works with any
endpoint that implements ``/v1/audio/speech``.
"""

import io
import time
import base64 as _base64
import json as _json
from typing import Any

from openai import (
    APIConnectionError, APIError, APITimeoutError,
    AuthenticationError, BadRequestError, OpenAI,
    PermissionDeniedError, RateLimitError,
)

from config.settings import Config
from providers import register_provider
from providers.base.tts import BaseTTSProvider
from providers.response import ProviderResponse
from modules.logger.logger import get_logger

logger = get_logger(__name__)


class OpenAITTSProvider(BaseTTSProvider):
    """TTS provider backed by any OpenAI-compatible audio speech API."""

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._api_key: str = Config.TTS_API_KEY
        self._base_url: str = Config.TTS_BASE_URL
        self._voice: str = Config.TTS_VOICE
        self._speed: float = Config.TTS_SPEED

    def synthesize(self, text: str, **kwargs: Any) -> ProviderResponse:
        """Convert text to speech.

        Args:
            text: Text to speak.
            **kwargs: Additional params (voice, speed, format, etc.).

        Returns:
            ProviderResponse with base64 audio in ``content`` field.
        """
        t_start = time.perf_counter()

        if not self._api_key:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="TTS API key is not configured.",
            )
        if not self._base_url:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="TTS Base URL is not configured.",
            )

        voice = kwargs.pop("voice", self._voice)
        speed = kwargs.pop("speed", self._speed)
        fmt = kwargs.pop("response_format", "mp3")

        # Merge custom params
        custom = self._parse_params(Config.TTS_CUSTOM_PARAMS)
        custom.update(kwargs)

        logger.info(
            "OpenAITTS: calling %s (voice=%s, text_len=%d)",
            self._base_url, voice, len(text),
        )

        try:
            client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=60.0,
            )
            response = client.audio.speech.create(
                model=custom.pop("model", "tts-1"),
                voice=voice,
                input=text,
                speed=speed,
                response_format=fmt,
                extra_body=custom if custom else None,
            )

            latency_ms = (time.perf_counter() - t_start) * 1000
            buf = io.BytesIO()
            response.write_to_file(buf)
            audio_bytes = buf.getvalue()
            b64 = _base64.b64encode(audio_bytes).decode("ascii")

            logger.info("OpenAITTS: success — %.1fms, %d bytes", latency_ms, len(audio_bytes))

            return ProviderResponse.ok(
                provider=self.provider_name,
                model=f"tts:{voice}",
                content=f"data:audio/{fmt};base64,{b64[:80]}...",
                latency_ms=round(latency_ms, 2),
                metadata={
                    "audio_size_bytes": len(audio_bytes),
                    "format": fmt,
                    "voice": voice,
                    "text_length": len(text),
                    "base64": b64,
                },
            )

        except APIConnectionError as exc:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Connection failed. Cannot reach {self._base_url}. ({exc})",
            )
        except AuthenticationError:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Authentication failed (401). Check your TTS API key.",
            )
        except PermissionDeniedError:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Permission denied (403).",
            )
        except RateLimitError:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Rate limited (429).",
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
    def voice(self) -> str:
        return self._voice

    @staticmethod
    def _parse_params(raw: str) -> dict:
        if not raw:
            return {}
        try:
            items = _json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(items, list):
                return {}
            result = {}
            for p in items:
                name = p.get("name", "").strip()
                val = p.get("value", "")
                if not name:
                    continue
                if isinstance(val, str):
                    if val.lower() in ("true", "false"):
                        val = (val.lower() == "true")
                    else:
                        try:
                            val = float(val) if "." in val else int(val)
                        except ValueError:
                            pass
                result[name] = val
            return result
        except (_json.JSONDecodeError, TypeError):
            return {}


register_provider("tts", "openai", OpenAITTSProvider)
