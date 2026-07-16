"""
Voku TTS provider.

Calls the Voku TTS API directly via HTTP POST — no URL path appending.
"""

import io
import time
import base64 as _base64
import json as _json
from typing import Any

import requests

from config.settings import Config
from providers import register_provider
from providers.base.tts import BaseTTSProvider
from providers.response import ProviderResponse
from modules.logger.logger import get_logger

logger = get_logger(__name__)

# Default Voku endpoint
VOKU_DEFAULT_URL = "https://v1.vocu.ai/api/tts/simple-generate"


class VokuTTSProvider(BaseTTSProvider):
    """TTS provider for Voku.ai API."""

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._api_key: str = Config.TTS_API_KEY
        self._base_url: str = Config.TTS_BASE_URL or VOKU_DEFAULT_URL

    def synthesize(self, text: str, **kwargs: Any) -> ProviderResponse:
        """Convert text to speech via Voku API.

        Args:
            text: Text to speak.
            **kwargs: Override request body fields.

        Returns:
            ProviderResponse with base64 MP3 in ``metadata.base64``.
        """
        t_start = time.perf_counter()

        if not self._api_key:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="TTS API key is not configured.",
            )

        # Build request body from custom params + kwargs
        body = self._build_body(text, **kwargs)

        logger.info(
            "VokuTTS: calling %s (text_len=%d, voiceId=%s)",
            self._base_url, len(text), body.get("voiceId", "?"),
        )

        try:
            resp = requests.post(
                self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=60,
            )
            latency_ms = (time.perf_counter() - t_start) * 1000

            if not resp.ok:
                logger.error("VokuTTS: HTTP %d — %s", resp.status_code, resp.text[:200])
                return ProviderResponse.fail(
                    provider=self.provider_name,
                    error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    latency_ms=round(latency_ms, 2),
                )

            # Voku returns audio binary directly
            audio_bytes = resp.content
            if not audio_bytes:
                # Maybe JSON response with URL?
                try:
                    data = resp.json()
                    audio_url = data.get("audioUrl") or data.get("url") or ""
                    if audio_url:
                        # Fetch audio from URL
                        r2 = requests.get(audio_url, timeout=30)
                        audio_bytes = r2.content
                except Exception:
                    pass

            if not audio_bytes:
                return ProviderResponse.fail(
                    provider=self.provider_name,
                    error="TTS returned empty response.",
                )

            b64 = _base64.b64encode(audio_bytes).decode("ascii")

            logger.info("VokuTTS: success — %.1fms, %d bytes", latency_ms, len(audio_bytes))

            return ProviderResponse.ok(
                provider=self.provider_name,
                model=body.get("voiceId", "voku"),
                content=f"data:audio/mp3;base64,{b64[:80]}...",
                latency_ms=round(latency_ms, 2),
                metadata={
                    "audio_size_bytes": len(audio_bytes),
                    "format": "mp3",
                    "voice_id": body.get("voiceId", ""),
                    "text_length": len(text),
                    "base64": b64,
                },
            )

        except requests.exceptions.Timeout:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="Request timed out.",
            )
        except requests.exceptions.ConnectionError as exc:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Connection failed. Cannot reach {self._base_url}. ({exc})",
            )
        except Exception as exc:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Unexpected error: {exc}",
            )

    @property
    def provider_name(self) -> str:
        return "vocu"

    @property
    def voice(self) -> str:
        return self._base_url

    # ------------------------------------------------------------------
    # Body builder
    # ------------------------------------------------------------------

    def _build_body(self, text: str, **kwargs: Any) -> dict:
        """Build the Voku request body from custom params + overrides."""
        # Defaults
        body: dict = {
            "voiceId": "",
            "text": text,
            "promptId": "default",
            "preset": "balance",
            "break_clone": True,
            "language": "auto",
            "vivid": False,
            "emo_switch": [0, 0, 0, 0, 0],
            "speechRate": 1,
            "flash": False,
            "stream": False,
            "seed": -1,
            "srt": False,
        }

        # Load custom params from Config
        custom = self._parse_params(Config.TTS_CUSTOM_PARAMS)

        # voiceId can come from Config.TTS_VOICE
        if Config.TTS_VOICE and not custom.get("voiceId"):
            body["voiceId"] = Config.TTS_VOICE

        body.update(custom)
        body.update(kwargs)
        body["text"] = text  # always use the passed text

        return body

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


register_provider("tts", "vocu", VokuTTSProvider)
