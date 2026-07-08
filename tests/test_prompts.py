"""Tests for PromptManager."""

import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import pytest

from modules.prompts.manager import PromptManager


class TestPromptManager:
    """Tests for PromptManager template operations."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary prompts directory."""
        d = Path(tempfile.mkdtemp(prefix="screenmate_prompts_"))
        yield d
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    def test_seeds_defaults_on_empty_dir(self, temp_dir: Path) -> None:
        pm = PromptManager(prompts_dir=temp_dir)
        templates = pm.list_templates()
        # Our built-in templates are seeded
        assert len(templates) >= 6

    def test_get_template_by_id(self, temp_dir: Path) -> None:
        pm = PromptManager(prompts_dir=temp_dir)
        tmpl = pm.get_template("programming")
        assert tmpl is not None
        assert tmpl.id == "programming"
        assert "software engineer" in tmpl.content.lower()

    def test_get_nonexistent_template(self, temp_dir: Path) -> None:
        pm = PromptManager(prompts_dir=temp_dir)
        tmpl = pm.get_template("nonexistent")
        assert tmpl is None

    def test_save_custom_template(self, temp_dir: Path) -> None:
        pm = PromptManager(prompts_dir=temp_dir)
        saved = pm.save_template(
            template_id="my-custom",
            name="My Custom",
            content="Be helpful and concise.",
            description="A custom prompt",
        )
        assert saved.id == "my-custom"
        assert saved.name == "My Custom"
        assert saved.is_builtin is False

        # Verify it can be read back
        tmpl = pm.get_template("my-custom")
        assert tmpl is not None
        assert "helpful and concise" in tmpl.content

    def test_delete_template(self, temp_dir: Path) -> None:
        pm = PromptManager(prompts_dir=temp_dir)
        pm.save_template("to-delete", "Delete Me", "content")
        assert pm.get_template("to-delete") is not None

        assert pm.delete_template("to-delete") is True
        assert pm.get_template("to-delete") is None
        assert pm.delete_template("to-delete") is False

    def test_get_template_content_fallback(self, temp_dir: Path) -> None:
        pm = PromptManager(prompts_dir=temp_dir)
        content = pm.get_template_content("nonexistent")
        # Falls back to default from Config
        assert len(content) > 0
        assert "ScreenMate" in content
