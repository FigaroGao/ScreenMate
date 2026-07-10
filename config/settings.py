"""
Unified configuration system for ScreenMate.

Reads all settings from environment variables (via python-dotenv).
Provides a single source of truth for all configuration values.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from the config directory (parent relative to this file)
_ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(_ENV_FILE)


class Config:
    """Singleton-style configuration class backed by environment variables.

    All future providers and modules read their configuration from here,
    so there is a single source of truth for API keys, model names, etc.

    Usage:
        from config.settings import Config
        api_key = Config.VISION_API_KEY
    """

    # ---- App ----
    APP_NAME: str = os.getenv("APP_NAME", "ScreenMate")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.2.0")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT: int = int(os.getenv("APP_PORT", "5000"))
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "true").lower() == "true"
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "screenmate-dev-secret")

    # ---- Vision Provider ----
    VISION_PROVIDER: str = os.getenv("VISION_PROVIDER", "mock")
    VISION_API_KEY: str = os.getenv("VISION_API_KEY", "")
    VISION_BASE_URL: str = os.getenv("VISION_BASE_URL", "")
    VISION_MODEL_NAME: str = os.getenv("VISION_MODEL_NAME", "mock-vision-v1")
    VISION_MAX_TOKENS: int = int(os.getenv("VISION_MAX_TOKENS", "1024"))
    VISION_TEMPERATURE: float = float(os.getenv("VISION_TEMPERATURE", "0.7"))
    VISION_TOP_P: float = float(os.getenv("VISION_TOP_P", "0.9"))

    # ---- Chat Provider ----
    CHAT_PROVIDER: str = os.getenv("CHAT_PROVIDER", "mock")
    CHAT_API_KEY: str = os.getenv("CHAT_API_KEY", "")
    CHAT_BASE_URL: str = os.getenv("CHAT_BASE_URL", "")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "mock-chat-v1")
    CHAT_MAX_TOKENS: int = int(os.getenv("CHAT_MAX_TOKENS", "2048"))
    CHAT_TEMPERATURE: float = float(os.getenv("CHAT_TEMPERATURE", "0.7"))
    CHAT_TOP_P: float = float(os.getenv("CHAT_TOP_P", "0.9"))

    # ---- TTS Provider ----
    TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "mock")
    TTS_API_KEY: str = os.getenv("TTS_API_KEY", "")
    TTS_BASE_URL: str = os.getenv("TTS_BASE_URL", "")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "default")
    TTS_SPEED: float = float(os.getenv("TTS_SPEED", "1.0"))

    # ---- System Prompt ----
    SYSTEM_PROMPT: str = os.getenv(
        "SYSTEM_PROMPT", "You are ScreenMate, a helpful desktop AI assistant."
    )
    PROMPT_TEMPLATE: str = os.getenv("PROMPT_TEMPLATE", "assistant")

    # ---- Auto Mode ----
    AUTO_SCREENSHOT_INTERVAL: int = int(os.getenv("AUTO_SCREENSHOT_INTERVAL", "20"))
    AUTO_SUMMARY_ENABLED: bool = (
        os.getenv("AUTO_SUMMARY_ENABLED", "true").lower() == "true"
    )
    AUTO_CHAT_ENABLED: bool = (
        os.getenv("AUTO_CHAT_ENABLED", "true").lower() == "true"
    )
    AUTO_CONTEXT_MAX_LENGTH: int = int(os.getenv("AUTO_CONTEXT_MAX_LENGTH", "50"))

    # ---- Hotkey ----
    HOTKEY_CAPTURE: str = os.getenv("HOTKEY_CAPTURE", "ctrl+shift+a")

    # ---- Logging ----
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    LOG_DIR: str = os.getenv("LOG_DIR", "data/logs")
    LOG_MAX_FILES: int = int(os.getenv("LOG_MAX_FILES", "7"))

    # ---- Project root ----
    @classmethod
    def get_project_root(cls) -> Path:
        """Return the absolute path to the project root directory."""
        return Path(__file__).parent.parent.resolve()

    @classmethod
    def get_log_dir(cls) -> Path:
        """Return the absolute path to the log directory."""
        return cls.get_project_root() / cls.LOG_DIR

    @classmethod
    def as_dict(cls, include_secrets: bool = False) -> dict:
        """Return all non-private config values as a dictionary.

        Args:
            include_secrets: If False, mask API keys. Defaults to False.
        """
        result: dict = {}
        for key in dir(cls):
            if key.startswith("_") or not key.isupper():
                continue
            value = getattr(cls, key)
            if callable(value):
                continue
            # Mask secrets unless explicitly requested
            if not include_secrets and "_API_KEY" in key:
                value = "***" if value else ""
            result[key] = value
        return result
