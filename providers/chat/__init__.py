"""Chat providers for ScreenMate.

Import this package to auto-register all chat providers.
"""

from providers.chat.mock_chat import MockChatProvider      # noqa: F401
from providers.chat.openai_chat import OpenAIChatProvider  # noqa: F401
