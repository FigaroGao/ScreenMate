"""TTS providers for ScreenMate.

Import this package to auto-register all TTS providers.
"""

from providers.tts.mock_tts import MockTTSProvider      # noqa: F401
from providers.tts.openai_tts import OpenAITTSProvider  # noqa: F401
from providers.tts.vocu_tts import VokuTTSProvider      # noqa: F401
