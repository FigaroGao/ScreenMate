"""
Prompt template manager.

Loads prompt templates from ``data/prompts/*.md`` and provides CRUD
operations.  Each template is a Markdown file where the first ``# Title``
line defines the template name.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import Config
from modules.logger.logger import get_logger

logger = get_logger(__name__)

# Default templates shipped with the project.
_BUILTIN_TEMPLATES = [
    {
        "id": "assistant",
        "name": "Assistant",
        "description": "General-purpose desktop assistant",
        "content": (
            "You are ScreenMate, a helpful desktop AI assistant with "
            "vision capabilities.  Answer questions about the user's "
            "screen, help with tasks, and be concise."
        ),
    },
    {
        "id": "programming",
        "name": "Programming Assistant",
        "description": "Help with coding and debugging",
        "content": (
            "You are a senior software engineer.  Review the code or "
            "error message visible on the screen.  Provide clear, "
            "actionable advice.  Suggest improvements and explain "
            "your reasoning."
        ),
    },
    {
        "id": "game",
        "name": "Game Assistant",
        "description": "Help with games visible on screen",
        "content": (
            "You are a game strategy advisor.  Look at the game on "
            "the screen and provide tips, strategies, or hints.  "
            "Be encouraging and avoid spoilers when possible."
        ),
    },
    {
        "id": "study",
        "name": "Study",
        "description": "Help with studying and learning",
        "content": (
            "You are a patient tutor.  The screen shows study "
            "material.  Explain concepts clearly, break down "
            "complex ideas, and quiz the user to reinforce learning."
        ),
    },
    {
        "id": "ocr",
        "name": "OCR",
        "description": "Extract and format text from the screen",
        "content": (
            "You are an OCR specialist.  Extract all text visible "
            "on the screen.  Preserve the original formatting as "
            "much as possible.  If the text is in a table, output "
            "it in Markdown table format."
        ),
    },
    {
        "id": "translator",
        "name": "Translator",
        "description": "Translate text visible on screen",
        "content": (
            "You are a professional translator.  Translate the text "
            "visible on the screen to the user's preferred language. "
            "Preserve formatting and tone.  If you are unsure about "
            "the source language, ask."
        ),
    },
    {
        "id": "custom",
        "name": "Custom",
        "description": "User-defined prompt template",
        "content": (
            "You are ScreenMate, a helpful desktop AI assistant.  "
            "Follow the user's instructions carefully."
        ),
    },
]


@dataclass
class PromptTemplate:
    """A single prompt template."""

    id: str
    name: str
    description: str = ""
    content: str = ""
    is_builtin: bool = True


@dataclass
class PromptTemplateList:
    """Wrapper for serialising the template list."""

    templates: list[PromptTemplate] = field(default_factory=list)


class PromptManager:
    """Manage prompt templates.

    Templates are stored as Markdown files in ``data/prompts/``.
    Built-in templates are seeded on first access if the files don't exist.

    Usage::

        pm = PromptManager()
        tmpl = pm.get_template("programming")
        all_templates = pm.list_templates()
    """

    def __init__(self, prompts_dir: Optional[Path] = None) -> None:
        """Initialise the prompt manager.

        Args:
            prompts_dir: Directory for prompt files.  Defaults to
                ``<project_root>/data/prompts``.
        """
        if prompts_dir is None:
            prompts_dir = Config.get_project_root() / "data" / "prompts"
        self._dir = Path(prompts_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._seed_defaults()
        logger.info("PromptManager initialised (dir=%s)", self._dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Return a single template by ID, or ``None`` if not found.

        Args:
            template_id: The template identifier (e.g. ``"programming"``).
        """
        file_path = self._dir / f"{template_id}.md"
        if not file_path.exists():
            logger.warning("Prompt template not found: %s", template_id)
            return None
        return self._read_file(file_path, template_id)

    def list_templates(self) -> list[PromptTemplate]:
        """Return all available templates."""
        templates: list[PromptTemplate] = []
        for f in sorted(self._dir.glob("*.md")):
            tid = f.stem
            templates.append(self._read_file(f, tid))
        return templates

    def save_template(
        self,
        template_id: str,
        name: str,
        content: str,
        description: str = "",
    ) -> PromptTemplate:
        """Create or update a template.

        Args:
            template_id: Unique identifier (used as filename stem).
            name: Human-readable name.
            content: The system-prompt text.
            description: Short description for the UI.

        Returns:
            The saved :class:`PromptTemplate`.
        """
        file_path = self._dir / f"{template_id}.md"
        header = f"# {name}\n\n"
        if description:
            header += f"> {description}\n\n"
        file_path.write_text(header + content, encoding="utf-8")
        logger.info("Prompt template saved: %s (%s)", template_id, name)
        return PromptTemplate(
            id=template_id,
            name=name,
            description=description,
            content=content,
            is_builtin=False,
        )

    def delete_template(self, template_id: str) -> bool:
        """Delete a template file.

        Args:
            template_id: The template to delete.

        Returns:
            ``True`` if deleted, ``False`` if not found.
        """
        file_path = self._dir / f"{template_id}.md"
        if not file_path.exists():
            return False
        file_path.unlink()
        logger.info("Prompt template deleted: %s", template_id)
        return True

    def get_template_content(self, template_id: str) -> str:
        """Return just the content string (for injection into prompts).

        Args:
            template_id: The template identifier.

        Returns:
            The template content string, or the default system prompt
            if the template is not found.
        """
        tmpl = self.get_template(template_id)
        if tmpl is None:
            return Config.SYSTEM_PROMPT
        return tmpl.content

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _seed_defaults(self) -> None:
        """Write built-in templates if the prompts directory is empty."""
        existing = list(self._dir.glob("*.md"))
        if existing:
            return  # User already has templates — don't overwrite

        for t in _BUILTIN_TEMPLATES:
            self.save_template(
                template_id=t["id"],
                name=t["name"],
                content=t["content"],
                description=t.get("description", ""),
            )
        logger.info("Seeded %d default prompt templates", len(_BUILTIN_TEMPLATES))

    def _read_file(self, file_path: Path, template_id: str) -> PromptTemplate:
        """Parse a Markdown template file into a PromptTemplate."""
        text = file_path.read_text(encoding="utf-8")
        lines = text.strip().split("\n")

        name = template_id.title()
        description = ""
        content_start = 0

        for i, line in enumerate(lines):
            if line.startswith("# "):
                name = line[2:].strip()
                continue
            if line.startswith("> "):
                description = line[2:].strip()
                continue
            if line.strip() == "":
                continue
            content_start = i
            break

        content = "\n".join(lines[content_start:]).strip()

        return PromptTemplate(
            id=template_id,
            name=name,
            description=description,
            content=content,
            is_builtin=template_id
            in {t["id"] for t in _BUILTIN_TEMPLATES},
        )
