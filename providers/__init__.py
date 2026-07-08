"""
Provider registry for ScreenMate.

New providers are automatically discovered and registered when their
package is imported.  The registry maps (provider_type, provider_name)
→ provider class, making it trivial to look up a provider at runtime.

Factory methods (:func:`create_vision`, :func:`create_chat`,
:func:`create_tts`) read the configured provider name from :class:`Config`
and return an instantiated provider — no manual lookup needed in routes.
"""

from typing import Optional, Type

from config.settings import Config
from modules.logger.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Registry structure:
# {
#     "vision": {"mock": MockVisionProvider, "openai": OpenAIVisionProvider, ...},
#     "chat":    {"mock": MockChatProvider,    "openai": OpenAIChatProvider,    ...},
#     "tts":     {"mock": MockTTSProvider,     "openai": OpenAITTSProvider,     ...},
# }
# ---------------------------------------------------------------------------
_registry: dict[str, dict[str, Type]] = {
    "vision": {},
    "chat": {},
    "tts": {},
}


# ======================================================================
# Registration
# ======================================================================


def register_provider(provider_type: str, name: str, cls: Type) -> None:
    """Register a provider class.

    Args:
        provider_type: One of ``"vision"``, ``"chat"``, ``"tts"``.
        name: A short name for the provider, e.g. ``"mock"``, ``"openai"``.
        cls: The provider class (must subclass the appropriate base).
    """
    if provider_type not in _registry:
        _registry[provider_type] = {}
    _registry[provider_type][name] = cls
    logger.info("Registered %s provider: %s → %s", provider_type, name, cls.__name__)


# ======================================================================
# Lookup
# ======================================================================


def get_provider(provider_type: str, name: str) -> Type:
    """Look up a provider class by type and name.

    Args:
        provider_type: One of ``"vision"``, ``"chat"``, ``"tts"``.
        name: The provider name as registered.

    Returns:
        The provider class.

    Raises:
        ValueError: If the provider is not found.
    """
    type_registry = _registry.get(provider_type, {})
    if name not in type_registry:
        available = list(type_registry.keys()) or ["(none registered)"]
        raise ValueError(
            f"Unknown {provider_type} provider '{name}'. "
            f"Available: {available}"
        )
    return type_registry[name]


def list_providers(provider_type: str) -> list[str]:
    """Return the names of all registered providers for a given type."""
    return list(_registry.get(provider_type, {}).keys())


def list_all_providers() -> dict[str, list[str]]:
    """Return a dict mapping each provider type to its registered names."""
    return {k: list(v.keys()) for k, v in _registry.items()}


# ======================================================================
# Factory methods — read the configured provider from Config,
# instantiate it, and return the object.  Routes should use these
# instead of :func:`get_provider` + manual instantiation.
# ======================================================================


def create_vision(name: Optional[str] = None):
    """Create a vision provider instance.

    Args:
        name: Provider name.  Defaults to :attr:`Config.VISION_PROVIDER`.

    Returns:
        An instance of :class:`BaseVisionProvider`.

    Raises:
        ValueError: If the requested provider is not registered.
    """
    from providers.base.vision import BaseVisionProvider

    provider_name = name or Config.VISION_PROVIDER
    cls = get_provider("vision", provider_name)
    instance = cls()
    if not isinstance(instance, BaseVisionProvider):
        raise TypeError(
            f"{cls.__name__} does not subclass BaseVisionProvider"
        )
    logger.debug("Factory: created vision provider %s", provider_name)
    return instance


def create_chat(name: Optional[str] = None):
    """Create a chat provider instance.

    Args:
        name: Provider name.  Defaults to :attr:`Config.CHAT_PROVIDER`.

    Returns:
        An instance of :class:`BaseChatProvider`.

    Raises:
        ValueError: If the requested provider is not registered.
    """
    from providers.base.chat import BaseChatProvider

    provider_name = name or Config.CHAT_PROVIDER
    cls = get_provider("chat", provider_name)
    instance = cls()
    if not isinstance(instance, BaseChatProvider):
        raise TypeError(
            f"{cls.__name__} does not subclass BaseChatProvider"
        )
    logger.debug("Factory: created chat provider %s", provider_name)
    return instance


def create_tts(name: Optional[str] = None):
    """Create a TTS provider instance.

    Args:
        name: Provider name.  Defaults to :attr:`Config.TTS_PROVIDER`.

    Returns:
        An instance of :class:`BaseTTSProvider`.

    Raises:
        ValueError: If the requested provider is not registered.
    """
    from providers.base.tts import BaseTTSProvider

    provider_name = name or Config.TTS_PROVIDER
    cls = get_provider("tts", provider_name)
    instance = cls()
    if not isinstance(instance, BaseTTSProvider):
        raise TypeError(
            f"{cls.__name__} does not subclass BaseTTSProvider"
        )
    logger.debug("Factory: created TTS provider %s", provider_name)
    return instance
