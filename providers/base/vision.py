"""
Abstract base class for vision providers.

Every vision provider (mock, OpenAI, Qwen, Gemini, etc.) must subclass
:class:`BaseVisionProvider` and implement :meth:`analyze`.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseVisionProvider(ABC):
    """Abstract vision provider.

    Subclasses implement the actual vision API call.  The interface
    accepts an image (as bytes or a file path) plus an optional user
    prompt and returns a standardised response dict.
    """

    def __init__(self, config: Any = None) -> None:
        """Initialise the provider.

        Args:
            config: Optional configuration object (e.g. :class:`Config`).
        """
        self.config = config

    @abstractmethod
    def analyze(
        self,
        image_data: bytes,
        prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> dict:
        """Analyze an image and return a structured response.

        Args:
            image_data: Raw image bytes.
            prompt: Optional user prompt to guide the analysis.
            **kwargs: Additional provider-specific parameters.

        Returns:
            A dict of the form::

                {
                    "success": True,
                    "content": "The model's response text.",
                    "model": "model-name",
                    "usage": {"prompt_tokens": 0, "completion_tokens": 0},
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
    def model_name(self) -> str:
        """Return the model name used by this provider."""
        ...
