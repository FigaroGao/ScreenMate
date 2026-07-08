"""Tests for SettingsManager."""

import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import json
import pytest

from modules.settings.persistent import SettingsManager


class TestSettingsManager:
    """Tests for SettingsManager persistence."""

    @pytest.fixture
    def temp_file(self) -> Path:
        """Create a temporary settings file."""
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write("{}")
        yield Path(f.name)
        # Cleanup
        try:
            Path(f.name).unlink()
        except OSError:
            pass

    def test_save_and_read(self, temp_file: Path) -> None:
        sm = SettingsManager(file_path=temp_file)
        result = sm.save({"VISION_PROVIDER": "openai", "CHAT_MODEL": "gpt-4"})
        assert result.success is True

        overrides = sm.get_overrides()
        assert overrides.get("VISION_PROVIDER") == "openai"
        assert overrides.get("CHAT_MODEL") == "gpt-4"

    def test_reset(self, temp_file: Path) -> None:
        sm = SettingsManager(file_path=temp_file)
        sm.save({"VISION_PROVIDER": "openai"})
        result = sm.reset()
        assert result.success is True
        overrides = sm.get_overrides()
        assert overrides == {}

    def test_masked_api_keys(self, temp_file: Path) -> None:
        sm = SettingsManager(file_path=temp_file)
        sm.save({"VISION_API_KEY": "sk-real-key"})
        all_settings = sm.get_all(include_secrets=False)
        assert "***" in all_settings.get("VISION_API_KEY", "")

        # With secrets
        all_with = sm.get_all(include_secrets=True)
        assert all_with.get("VISION_API_KEY") == "sk-real-key"

    def test_masked_placeholder_not_saved(self, temp_file: Path) -> None:
        """Value "***" should not be saved (it's the placeholder)."""
        sm = SettingsManager(file_path=temp_file)
        sm.save({"VISION_API_KEY": "sk-original"})
        sm.save({"VISION_API_KEY": "***"})
        overrides = sm.get_overrides()
        # "***" should be filtered out, keeping the original
        assert overrides.get("VISION_API_KEY") == "sk-original"
