"""
Custom / Generic TTS provider.

Takes a user-provided URL, API key, and custom request body.
Works with ANY TTS API — just paste the curl command body into the
Custom Parameters in Settings, and we'll do the rest.

- ``TTS_BASE_URL`` → full endpoint URL (no path appending)
- ``TTS_API_KEY`` → ``Authorization: Bearer <key>`` header
- ``TTS_CUSTOM_PARAMS`` → JSON body fields, ``{text}`` is replaced
  with the text to speak
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


class CustomTTSProvider(BaseTTSProvider):
    """Generic TTS provider — user configures URL, key, and body.

    No provider-specific code.  Works with Voku, Aliyun Bailian,
    or any other TTS API that accepts JSON POST with Bearer auth.
    """

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self._api_key: str = Config.TTS_API_KEY
        self._base_url: str = Config.TTS_BASE_URL

    def synthesize(self, text: str, **kwargs: Any) -> ProviderResponse:
        """Send text to the configured TTS endpoint.

        Custom parameters from Settings become the request body.
        The special placeholder ``{text}`` in any field value is
        replaced with the actual text to speak.
        """
        t_start = time.perf_counter()

        if not self._base_url:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error="TTS Base URL is not configured.",
            )

        body = self._build_body(text, **kwargs)

        logger.info(
            "CustomTTS: POST %s (text_len=%d, body_keys=%s)",
            self._base_url, len(text), list(body.keys()),
        )
        logger.debug("CustomTTS body: %s", _json.dumps(body, ensure_ascii=False)[:500])

        try:
            headers = {"Content-Type": "application/json"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

            resp = requests.post(
                self._base_url,
                headers=headers,
                json=body,
                timeout=120,
            )
            latency_ms = (time.perf_counter() - t_start) * 1000

            if not resp.ok:
                logger.error("CustomTTS: HTTP %d — %s", resp.status_code, resp.text[:300])
                return ProviderResponse.fail(
                    provider=self.provider_name,
                    error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    latency_ms=round(latency_ms, 2),
                )

            # Try to extract audio: raw bytes, or JSON with audioUrl/url
            audio_bytes = resp.content
            content_type = resp.headers.get("Content-Type", "")

            if "json" in content_type or not audio_bytes or len(audio_bytes) < 100:
                try:
                    data = resp.json()
                    url = CustomTTSProvider._find_audio_url(data)
                    if url:
                        logger.info("CustomTTS: fetching audio from %s", url[:120])
                        r2 = requests.get(url, timeout=60)
                        audio_bytes = r2.content
                except Exception:
                    audio_bytes = resp.content

            if not audio_bytes or len(audio_bytes) < 100:
                return ProviderResponse.fail(
                    provider=self.provider_name,
                    error=f"Could not extract audio from response ({len(resp.content)} bytes).",
                )

            b64 = _base64.b64encode(audio_bytes).decode("ascii")
            fmt = self._detect_format(audio_bytes)

            logger.info("CustomTTS: success — %.1fms, %d bytes", latency_ms, len(audio_bytes))

            return ProviderResponse.ok(
                provider=self.provider_name,
                model="custom",
                content=f"data:audio/{fmt};base64,{b64[:80]}...",
                latency_ms=round(latency_ms, 2),
                metadata={
                    "audio_size_bytes": len(audio_bytes),
                    "format": fmt,
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
                error=f"Connection failed. Cannot reach {self._base_url}.",
            )
        except Exception as exc:
            return ProviderResponse.fail(
                provider=self.provider_name,
                error=f"Unexpected error: {exc}",
            )

    @property
    def provider_name(self) -> str:
        return "custom"

    @property
    def voice(self) -> str:
        return "custom"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_body(self, text: str, **kwargs: Any) -> dict:
        """Build request body from custom params, substituting {text}."""
        custom = self._parse_params(Config.TTS_CUSTOM_PARAMS)
        custom.update(kwargs)

        if not custom:
            # If no custom params, use minimal defaults
            return {"text": text}

        return self._substitute_text(custom, text)

    @staticmethod
    def _substitute_text(obj: Any, text: str) -> Any:
        """Recursively replace ``{text}`` in string values."""
        if isinstance(obj, str):
            return obj.replace("{text}", text)
        if isinstance(obj, dict):
            return {k: CustomTTSProvider._substitute_text(v, text) for k, v in obj.items()}
        if isinstance(obj, list):
            return [CustomTTSProvider._substitute_text(v, text) for v in obj]
        return obj

    @staticmethod
    def _parse_params(raw: str) -> dict:
        if not raw:
            return {}
        try:
            items = _json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(items, list):
                result = {}
                for p in items:
                    name = p.get("name", "").strip()
                    val = p.get("value", "")
                    if not name:
                        continue
                    val = CustomTTSProvider._coerce_value(val)
                    if "." in name:
                        parts = name.split(".")
                        d = result
                        for part in parts[:-1]:
                            d = d.setdefault(part, {})
                        d[parts[-1]] = val
                    else:
                        result[name] = val
                return result
            if isinstance(items, dict):
                return items
            return {}
        except (_json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _coerce_value(val):
        """Coerce a string value to a typed Python value.

        Handles: JSON arrays/objects, booleans, numbers, null, plain strings.
        """
        if not isinstance(val, str):
            return val
        s = val.strip()
        # JSON array or object
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
            try:
                return _json.loads(s)
            except (_json.JSONDecodeError, ValueError):
                pass
        # Booleans
        if s.lower() in ("true", "false"):
            return s.lower() == "true"
        # Null
        if s.lower() == "null":
            return None
        # Numbers
        try:
            return float(s) if "." in s else int(s)
        except ValueError:
            pass
        return s

    @staticmethod
    def _detect_format(data: bytes) -> str:
        if data[:4] == b"RIFF":
            return "wav"
        if data[:3] == b"ID3" or data[:2] == b"\xff\xfb":
            return "mp3"
        if data[:4] == b"fLaC":
            return "flac"
        if data[:4] == b"OggS":
            return "ogg"
        return "mp3"


    @staticmethod
    def _find_audio_url(data: Any) -> str:
        """Recursively search nested JSON for an audio URL.

        Checks known key names: audio, audioUrl, url, audio_url, streamUrl.
        Handles responses like Voku's ``{"data": {"audio": "https://..."}}``.
        """
        if isinstance(data, dict):
            for key in ("audio", "audioUrl", "url", "audio_url", "streamUrl"):
                val = data.get(key)
                if isinstance(val, str) and (val.startswith("http://") or val.startswith("https://")):
                    return val
            # Recurse into nested objects
            for v in data.values():
                result = CustomTTSProvider._find_audio_url(v)
                if result:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = CustomTTSProvider._find_audio_url(item)
                if result:
                    return result
        return ""


register_provider("tts", "custom", CustomTTSProvider)
