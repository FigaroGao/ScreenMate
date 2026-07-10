"""
Persona manager — CRUD + JSON persistence for AI personas.

Personas define the assistant's identity, tone, and behavior.
They are separate from Prompt Templates — a persona represents
a stable character, while templates are task-specific instructions.

Stored in ``data/personas/personas.json``.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import Config
from modules.logger.logger import get_logger

logger = get_logger(__name__)

# Default personas shipped with the project
_DEFAULTS = [
    {
        "name": "Assistant",
        "description": "A helpful, concise desktop AI assistant",
        "system_prompt": (
            "You are ScreenMate, a desktop AI assistant. "
            "You are looking at the user's screen. "
            "Answer naturally and concisely based on what you see. "
            "Use Markdown formatting when helpful. "
            "Be friendly and supportive."
        ),
    },
    {
        "name": "Senior Developer",
        "description": "Experienced software engineer who reviews code and gives technical advice",
        "system_prompt": (
            "You are a senior software engineer with 15 years of experience. "
            "You are reviewing code and content on the user's screen. "
            "Provide clear, actionable technical advice. "
            "Point out potential bugs, suggest improvements, and explain your reasoning. "
            "Use proper technical terminology. Be direct but constructive."
        ),
    },
    {
        "name": "Teacher",
        "description": "Patient tutor who explains concepts clearly for learning",
        "system_prompt": (
            "You are a patient and encouraging teacher. "
            "The user is showing you their screen to learn. "
            "Explain concepts step by step, using simple language first, "
            "then building up to more detail. "
            "Ask questions to check understanding. "
            "Use analogies and examples. Never make the user feel stupid."
        ),
    },
    {
        "name": "Senpai",
        "description": "Anime-style senior student, warm and slightly teasing",
        "system_prompt": (
            "You are 'Senpai' — a warm, slightly teasing senior student. "
            "You've been through all this before and you're here to help your "
            "kouhai (junior). Speak in a friendly, casual tone. "
            "Occasionally use phrases like 'Good job!' or 'Let me show you~'. "
            "Be encouraging but also gently push the user to improve. "
            "Keep the anime references light and natural."
        ),
    },
]


@dataclass
class Persona:
    """A single persona definition."""

    name: str
    description: str = ""
    system_prompt: str = ""
    is_default: bool = False


@dataclass
class PersonaListResult:
    """Result wrapper for persona listing."""

    success: bool = True
    personas: list[Persona] = field(default_factory=list)
    message: str = ""


class PersonaManager:
    """CRUD manager for personas with JSON file persistence.

    Usage::

        pm = PersonaManager()
        pm.create("My Bot", "A custom bot", "You are...")
        personas = pm.list_all()
        current = pm.get("My Bot")
        pm.delete("My Bot")
    """

    def __init__(self, file_path: Optional[Path] = None) -> None:
        """Initialise the persona manager.

        Args:
            file_path: Path to personas JSON file.
                Defaults to ``<project_root>/data/personas/personas.json``.
        """
        if file_path is None:
            file_path = Config.get_project_root() / "data" / "personas" / "personas.json"
        self._file = Path(file_path)
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._seed_defaults()
        logger.info("PersonaManager initialised (%s)", self._file)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_all(self) -> PersonaListResult:
        """Return all personas."""
        personas = self._read_all()
        return PersonaListResult(
            success=True,
            personas=personas,
            message=f"{len(personas)} personas loaded.",
        )

    def get(self, name: str) -> Optional[Persona]:
        """Return a persona by name, or ``None``."""
        for p in self._read_all():
            if p.name == name:
                return p
        return None

    def create(
        self,
        name: str,
        description: str = "",
        system_prompt: str = "",
    ) -> dict:
        """Create a new persona.

        Args:
            name: Unique name.
            description: Short description for the UI.
            system_prompt: Full system prompt text.

        Returns:
            A status dict.
        """
        if not name.strip():
            return {"success": False, "message": "Persona name is required."}

        personas = self._read_all()
        if any(p.name == name.strip() for p in personas):
            return {"success": False, "message": f"Persona '{name}' already exists."}

        personas.append(Persona(
            name=name.strip(),
            description=description.strip(),
            system_prompt=system_prompt.strip(),
            is_default=False,
        ))
        self._write_all(personas)
        logger.info("Persona created: %s", name)
        return {"success": True, "message": f"Persona '{name}' created."}

    def update(
        self,
        name: str,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """Update an existing persona. ``name`` identifies the persona
        and can also be changed via a ``new_name`` field in future.

        Args:
            name: Existing persona name.
            description: New description (``None`` = keep current).
            system_prompt: New system prompt (``None`` = keep current).

        Returns:
            A status dict.
        """
        personas = self._read_all()
        for i, p in enumerate(personas):
            if p.name == name:
                if description is not None:
                    personas[i].description = description.strip()
                if system_prompt is not None:
                    personas[i].system_prompt = system_prompt.strip()
                self._write_all(personas)
                logger.info("Persona updated: %s", name)
                return {"success": True, "message": f"Persona '{name}' updated."}
        return {"success": False, "message": f"Persona '{name}' not found."}

    def delete(self, name: str) -> dict:
        """Delete a persona. Default personas cannot be deleted.

        Args:
            name: Persona name to delete.

        Returns:
            A status dict.
        """
        personas = self._read_all()
        for p in personas:
            if p.name == name and p.is_default:
                return {"success": False, "message": "Cannot delete default persona."}
        new_list = [p for p in personas if p.name != name]
        if len(new_list) == len(personas):
            return {"success": False, "message": f"Persona '{name}' not found."}
        self._write_all(new_list)
        logger.info("Persona deleted: %s", name)
        return {"success": True, "message": f"Persona '{name}' deleted."}

    def get_system_prompt(self, name: str) -> str:
        """Return the system prompt for a persona, or a default."""
        p = self.get(name)
        if p:
            return p.system_prompt
        # Fallback: default Assistant persona
        for p in self._read_all():
            if p.name == "Assistant":
                return p.system_prompt
        return "You are ScreenMate, a helpful desktop AI assistant."

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _seed_defaults(self) -> None:
        """Write default personas if the file doesn't exist."""
        if self._file.exists():
            return
        personas = [
            Persona(
                name=d["name"],
                description=d["description"],
                system_prompt=d["system_prompt"],
                is_default=True,
            )
            for d in _DEFAULTS
        ]
        self._write_all(personas)
        logger.info("Seeded %d default personas", len(personas))

    def _read_all(self) -> list[Persona]:
        """Read all personas from the JSON file."""
        try:
            if not self._file.exists():
                return []
            data = json.loads(self._file.read_text(encoding="utf-8"))
            return [
                Persona(
                    name=d.get("name", ""),
                    description=d.get("description", ""),
                    system_prompt=d.get("system_prompt", ""),
                    is_default=d.get("is_default", False),
                )
                for d in data
                if isinstance(d, dict) and d.get("name")
            ]
        except Exception as exc:
            logger.error("Failed to read personas: %s", exc)
            return []

    def _write_all(self, personas: list[Persona]) -> None:
        """Write all personas to the JSON file."""
        data = [
            {
                "name": p.name,
                "description": p.description,
                "system_prompt": p.system_prompt,
                "is_default": p.is_default,
            }
            for p in personas
        ]
        tmp = self._file.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._file)
