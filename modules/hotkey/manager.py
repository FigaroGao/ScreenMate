"""
Hotkey manager — global keyboard shortcut listener.

Responsible ONLY for:
- Listening for a configured keyboard shortcut
- Calling :meth:`ManualPipeline.execute` when the shortcut is pressed
- Writing progress to :class:`PipelineState`

This module contains NO business logic — it delegates entirely to
:class:`ManualPipeline` and :class:`PipelineState`.
"""

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from config.settings import Config
from modules.logger.logger import get_logger
from modules.pipeline.state import PipelineState, PipelineProgress

logger = get_logger(__name__)

# Default shortcut
DEFAULT_SHORTCUT = "ctrl+shift+a"


@dataclass
class HotkeyInfo:
    """Metadata about the current hotkey configuration."""

    shortcut: str = DEFAULT_SHORTCUT
    enabled: bool = True
    registered: bool = False


class HotkeyManager:
    """Global hotkey listener.

    Listens for a user-configurable keyboard shortcut and triggers
    the manual pipeline when pressed.  Skips if the pipeline is
    already running (busy state).

    Usage::

        hm = HotkeyManager(
            on_trigger=manual_pipeline.execute,
            get_settings=lambda: SettingsManager(),
        )
        hm.start()
    """

    def __init__(
        self,
        on_trigger: Optional[Callable[..., Any]] = None,
        on_get_shortcut: Optional[Callable[[], str]] = None,
        on_get_settings_manager: Optional[Callable[[], Any]] = None,
    ) -> None:
        """Initialise the hotkey manager.

        Args:
            on_trigger: Callable that runs the pipeline.  Receives no
                arguments and returns a PipelineResult-compatible object.
                Defaults to calling ManualPipeline.execute().
            on_get_shortcut: Callable that returns the current shortcut
                string (e.g. ``"ctrl+shift+a"``).  Defaults to reading
                from Config / SettingsManager.
            on_get_settings_manager: Callable returning the SettingsManager
                instance for reading/writing shortcut config.
        """
        self._trigger = on_trigger
        self._get_shortcut = on_get_shortcut or self._default_shortcut_provider
        self._get_settings = on_get_settings_manager

        self._info = HotkeyInfo()
        self._hook_id: Any = None

        self._hotkey_lock = threading.Lock()
        self._keyboard: Any = None

        logger.info("HotkeyManager initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> dict:
        """Register the global hotkey and begin listening.

        Returns:
            A status dict.
        """
        return self.register()

    def stop(self) -> dict:
        """Unregister the hotkey and stop listening.

        Returns:
            A status dict.
        """
        return self.unregister()

    def register(self) -> dict:
        """Register (or re-register) the global hotkey.

        If the ``keyboard`` library is unavailable, returns a failure
        but does NOT crash.

        Returns:
            A status dict.
        """
        with self._hotkey_lock:
            # Unregister existing hook first
            self._unregister_internal()

            shortcut = self._read_shortcut()

            try:
                import keyboard as kb

                self._keyboard = kb
                self._hook_id = kb.add_hotkey(
                    shortcut, self._on_hotkey_pressed,
                )
                self._info.shortcut = shortcut
                self._info.registered = True
                self._info.enabled = True
                logger.info("Hotkey registered: %s", shortcut)
                return {
                    "success": True,
                    "message": f"Hotkey '{shortcut}' registered.",
                    "shortcut": shortcut,
                }
            except ImportError:
                logger.warning("keyboard library not installed")
                return {
                    "success": False,
                    "message": "keyboard library is not installed. "
                               "Run: pip install keyboard",
                }
            except Exception as exc:
                logger.error("Failed to register hotkey '%s': %s", shortcut, exc)
                return {
                    "success": False,
                    "message": f"Failed to register hotkey: {exc}",
                }

    def unregister(self) -> dict:
        """Unregister the current hotkey hook.

        Returns:
            A status dict.
        """
        with self._hotkey_lock:
            self._unregister_internal()
            return {
                "success": True,
                "message": "Hotkey unregistered.",
            }

    def enable(self) -> dict:
        """Enable hotkey listening (re-register if needed).

        Returns:
            A status dict.
        """
        with self._hotkey_lock:
            self._info.enabled = True
            if not self._info.registered:
                return self.register()
            return {"success": True, "message": "Hotkey enabled."}

    def disable(self) -> dict:
        """Disable hotkey listening without unregistering.

        Returns:
            A status dict.
        """
        with self._hotkey_lock:
            self._info.enabled = False
            self._unregister_internal()
            logger.info("Hotkey disabled")
            return {"success": True, "message": "Hotkey disabled."}

    def change_shortcut(self, new_shortcut: str) -> dict:
        """Change the shortcut and re-register.

        Args:
            new_shortcut: e.g. ``"alt+q"`` or ``"ctrl+shift+a"``.

        Returns:
            A status dict.
        """
        if not new_shortcut or not self._validate_shortcut(new_shortcut):
            return {
                "success": False,
                "message": f"Invalid shortcut: '{new_shortcut}'. "
                           f"Expected format: 'ctrl+shift+a'",
            }

        with self._hotkey_lock:
            self._info.shortcut = new_shortcut.strip().lower()
            # Persist to settings
            self._save_shortcut(new_shortcut)
            # Re-register
            return self.register()

    def get_info(self) -> HotkeyInfo:
        """Return current hotkey metadata."""
        with self._hotkey_lock:
            self._info.shortcut = self._read_shortcut()
        return self._info

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_hotkey_pressed(self) -> None:
        """Called by the keyboard library when the shortcut is pressed."""
        if not self._info.enabled:
            return

        pstate = PipelineState.instance()

        # Check busy state — skip if already running
        if pstate.is_busy():
            logger.debug("Hotkey pressed but pipeline is busy — skipping")
            return

        logger.info("Hotkey pressed (%s) — triggering pipeline", self._info.shortcut)

        # Mark pipeline as running
        if not pstate.set_running("hotkey"):
            return  # Another input beat us to it

        # Execute the pipeline
        try:
            if self._trigger is None:
                self._trigger_fallback()
                return

            pstate.set_progress(PipelineProgress.CAPTURING)
            result = self._trigger()
            result_dict = result.to_dict() if hasattr(result, "to_dict") else result

            if result_dict.get("success", True):
                pstate.set_completed(result_dict)
            else:
                pstate.set_failed(result_dict.get("error", "Unknown error"))

        except Exception as exc:
            logger.error("Hotkey pipeline failed: %s", exc)
            pstate.set_failed(str(exc))

    def _trigger_fallback(self) -> None:
        """Fallback: directly call ManualPipeline when no callback set."""
        from config.settings import Config

        pstate = PipelineState.instance()
        try:
            from modules.dependencies import (
                get_manual_pipeline,
                get_context_manager,
            )

            pipeline = get_manual_pipeline()
            if pipeline is None:
                pstate.set_failed("ManualPipeline not available")
                return

            pstate.set_progress(PipelineProgress.ANALYZING)
            ctx = get_context_manager()
            prompt = ctx.get_memory("last_prompt") or "" if ctx else ""

            result = pipeline.execute(
                prompt=prompt,
                template_id=Config.PROMPT_TEMPLATE,
            )
            pstate.set_completed(result.to_dict())

        except Exception as exc:
            pstate.set_failed(str(exc))

    def _unregister_internal(self) -> None:
        """Remove the keyboard hook. Call inside _hotkey_lock."""
        if self._keyboard is not None and self._hook_id is not None:
            try:
                self._keyboard.remove_hotkey(self._hook_id)
            except Exception as exc:
                logger.warning("Error removing hotkey hook: %s", exc)
        self._hook_id = None
        self._info.registered = False

    def _read_shortcut(self) -> str:
        """Read shortcut from settings or config."""
        if self._get_settings:
            try:
                sm = self._get_settings()
                overrides = sm.get_overrides() if sm else {}
                if "HOTKEY_CAPTURE" in overrides:
                    return overrides["HOTKEY_CAPTURE"]
            except Exception:
                pass
        try:
            return getattr(Config, "HOTKEY_CAPTURE", DEFAULT_SHORTCUT)
        except Exception:
            return DEFAULT_SHORTCUT

    def _save_shortcut(self, shortcut: str) -> None:
        """Persist shortcut to settings."""
        if self._get_settings:
            try:
                sm = self._get_settings()
                if sm:
                    sm.save({"HOTKEY_CAPTURE": shortcut})
                    sm.refresh_config()
            except Exception as exc:
                logger.warning("Could not persist shortcut: %s", exc)

    @staticmethod
    def _default_shortcut_provider() -> str:
        """Return the default shortcut."""
        try:
            return getattr(Config, "HOTKEY_CAPTURE", DEFAULT_SHORTCUT)
        except Exception:
            return DEFAULT_SHORTCUT

    @staticmethod
    def _validate_shortcut(shortcut: str) -> bool:
        """Basic validation of a shortcut string."""
        s = shortcut.strip().lower()
        if not s or len(s) < 2:
            return False
        valid_keys = {
            "ctrl", "shift", "alt", "cmd", "win",
            "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
            "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8",
            "f9", "f10", "f11", "f12",
            "space", "enter", "tab", "escape", "backspace",
            "up", "down", "left", "right",
            "+",
        }
        parts = s.replace("+", " ").split()
        if not parts:
            return False
        return all(p in valid_keys for p in parts)
