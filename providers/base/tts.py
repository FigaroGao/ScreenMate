"""
Abstract base class for text-to-speech providers.

Every TTS provider (mock, OpenAI, Azure, Edge, etc.) must subclass
:class:`BaseTTSProvider` and implement :meth:`synthesize`.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTTSProvider(ABC):
    """Abstract TTS provider.

    Subclasses implement the actual text-to-speech API call.  The
    interface accepts text and returns audio data or a file path.
    """

    def __init__(self, config: Any = None) -> None:
        """Initialise the provider.

        Args:
            config: Optional configuration object (e.g. :class:`Config`).
        """
        self.config = config

    @abstractmethod
    def synthesize(self, text: str, **kwargs: Any) -> dict:
        """Convert text to speech.

        Args:
            text: The text to speak.
            **kwargs: Additional parameters (voice, speed, etc.).

        Returns:
            A dict of the form::

                {
                    "success": True,
                    "audio_path": "/static/audio/output.mp3",
                    "format": "mp3",
                    "duration_ms": 1234,
                }
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a human-readable provider name (e.g. ``"openai"``)."""
        ...

    @property
    @abstractmethod
    def voice(self) -> str:
        """Return the current voice name."""
        ...
