"""Vision providers for ScreenMate.

Import this package to auto-register all vision providers.
"""

from providers.vision.mock_vision import MockVisionProvider      # noqa: F401
from providers.vision.openai_vision import OpenAIVisionProvider  # noqa: F401
