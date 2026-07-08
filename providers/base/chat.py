"""
Abstract base class for chat / text-generation providers.

Every chat provider (mock, OpenAI, Qwen, Claude, etc.) must subclass
:class:`BaseChatProvider` and implement :meth:`chat`.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseChatProvider(ABC):
    """Abstract chat provider.

    Subclasses implement the actual LLM chat API call.  The interface
    accepts a list of messages and returns a standardised response dict.
    """

    def __init__(self, config: Any = None) -> None:
        """Initialise the provider.

        Args:
            config: Optional configuration object (e.g. :class:`Config`).
        """
        self.config = config

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> dict:
        """Send messages to the chat model and return the response.

        Args:
            messages: A list of message dicts, each with ``"role"`` and
                ``"content"`` keys.
            system_prompt: Optional system-level instruction.
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
