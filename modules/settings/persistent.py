"""
Settings persistence manager.

User overrides are stored in ``config/settings.json``.  On startup:
``.env`` → ``settings.json`` override → final ``Config``.

Routes call :meth:`SettingsManager.save` and
:meth:`SettingsManager.reset` — they never touch files directly.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from config.settings import Config
from modules.logger.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SettingsResult:
    """Result of a settings operation."""

    success: bool = True
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class SettingsManager:
    """Manage user settings persistence.

    Writes to ``config/settings.json``.  Does NOT modify ``.env``.

    Usage::

        sm = SettingsManager()
        result = sm.save({"VISION_PROVIDER": "openai"})
        current = sm.get_all()
        sm.reset()
    """

    def __init__(self, file_path: Optional[Path] = None) -> None:
        """Initialise the settings manager.

        Args:
            file_path: Path to the settings JSON file.  Defaults to
                ``<project_root>/config/settings.json``.
        """
        if file_path is None:
            file_path = Config.get_project_root() / "config" / "settings.json"
        self._file = Path(file_path)
        self._ensure_file()
        logger.info("SettingsManager initialised (file=%s)", self._file)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all(self, include_secrets: bool = False) -> dict[str, Any]:
        """Return the effective settings (Config defaults merged with
        user overrides).

        Args:
            include_secrets: If False, mask API keys.
        """
        base = Config.as_dict(include_secrets=include_secrets)
        overrides = self._read_overrides()

        # Merge: overrides on top of defaults
        merged = {**base, **overrides}
        if not include_secrets:
            for k in list(merged.keys()):
                if "_API_KEY" in k:
                    merged[k] = "***" if merged.get(k) else ""
        return merged

    def get_overrides(self) -> dict[str, Any]:
        """Return only the user's saved overrides."""
        return self._read_overrides()

    def save(self, data: dict[str, Any]) -> SettingsResult:
        """Save user settings overrides.

        Args:
            data: Key-value pairs to persist.

        Returns:
            A :class:`SettingsResult` indicating success or failure.
        """
        try:
            current = self._read_overrides()
            # Strip API key placeholders to avoid saving masked values
            cleaned = {}
            for k, v in data.items():
                if isinstance(v, str) and v == "***":
                    continue  # Don't save masked placeholder
                cleaned[k] = v

            current.update(cleaned)
            self._write_overrides(current)
            logger.info("Settings saved: %d keys persisted", len(cleaned))
            return SettingsResult(
                success=True,
                message=f"Settings saved ({len(cleaned)} keys).",
                data={"saved_keys": list(cleaned.keys())},
            )
        except Exception as exc:
            logger.error("Failed to save settings: %s", exc)
            return SettingsResult(
                success=False,
                message=f"Failed to save settings: {exc}",
            )

    def reset(self) -> SettingsResult:
        """Clear all user overrides, restoring Config defaults.

        Returns:
            A :class:`SettingsResult`.
        """
        try:
            self._write_overrides({})
            logger.info("Settings reset to defaults")
            return SettingsResult(
                success=True,
                message="Settings restored to defaults.",
            )
        except Exception as exc:
            logger.error("Failed to reset settings: %s", exc)
            return SettingsResult(
                success=False,
                message=f"Failed to reset settings: {exc}",
            )

    def refresh_config(self) -> None:
        """Re-apply saved overrides to the Config class.

        After calling this, :class:`Config` attributes reflect the
        merged state (defaults + user overrides).

        String values are automatically cast to match the existing
        Config attribute type (int, float, bool) so that providers
        receive correctly typed values.
        """
        overrides = self._read_overrides()
        for key, value in overrides.items():
            if not (hasattr(Config, key) and key.isupper()):
                continue
            # Cast string values to match the Config attribute type
            existing = getattr(Config, key)
            cast_value = self._cast_to_type(value, type(existing))
            setattr(Config, key, cast_value)
        logger.info("Config refreshed with %d overrides", len(overrides))

    @staticmethod
    def _cast_to_type(value: object, target_type: type) -> object:
        """Cast *value* to *target_type* if it is a string and the
        target is int, float, or bool.  Returns the original value
        unchanged when conversion is not applicable or fails.
        """
        if not isinstance(value, str):
            return value
        if target_type is int:
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        if target_type is float:
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        if target_type is bool:
            return value.lower() in ("true", "1", "yes", "on")
        return value

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ensure_file(self) -> None:
        """Create settings.json with an empty dict if it doesn't exist."""
        if not self._file.exists():
            self._file.parent.mkdir(parents=True, exist_ok=True)
            self._write_overrides({})

    def _read_overrides(self) -> dict[str, Any]:
        """Read the JSON file, returning {} on any error."""
        try:
            text = self._file.read_text(encoding="utf-8")
            data = json.loads(text) if text.strip() else {}
            if not isinstance(data, dict):
                return {}
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read settings.json: %s", exc)
            return {}

    def _write_overrides(self, data: dict[str, Any]) -> None:
        """Atomically write the override dict to JSON."""
        temp = self._file.with_suffix(".tmp")
        temp.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temp.replace(self._file)
