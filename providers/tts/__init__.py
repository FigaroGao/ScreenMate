"""TTS providers for ScreenMate.

Import this package to auto-register all TTS providers.
"""

from providers.tts.mock_tts import MockTTSProvider      # noqa: F401
from providers.tts.custom_tts import CustomTTSProvider  # noqa: F401
