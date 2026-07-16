"""
Flask blueprints for page routes and REST API endpoints.

Routes are thin — they delegate all business logic to pipelines and
managers accessed through :mod:`modules.dependencies`.  No route
calls a provider directly.
"""

from typing import Any

from flask import Blueprint, jsonify, render_template, request

from config.settings import Config
from modules.dependencies import (
    get_manual_pipeline,
    get_auto_pipeline,
    get_context_manager,
    get_stats_collector,
    get_settings_manager,
    get_prompt_manager,
    get_log_manager,
)
from modules.logger.logger import get_logger, get_recent_logs, clear_logs

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Blueprints
# ---------------------------------------------------------------------------

pages_bp = Blueprint("pages", __name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")

# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------


@pages_bp.route("/")
def dashboard() -> str:
    """Render the Dashboard page."""
    return render_template("dashboard.html")


@pages_bp.route("/manual")
def manual() -> str:
    """Render the Manual Mode page."""
    return render_template("manual.html")


@pages_bp.route("/auto")
def auto() -> str:
    """Render the Auto Mode page."""
    return render_template("auto.html")


@pages_bp.route("/settings")
def settings() -> str:
    """Render the Settings page."""
    return render_template("settings.html")


@pages_bp.route("/logs")
def logs() -> str:
    """Render the Logs page."""
    return render_template("logs.html")


@pages_bp.route("/about")
def about() -> str:
    """Render the About page."""
    return render_template("about.html")


# ---------------------------------------------------------------------------
# API — Status (uses StatsCollector for real data)
# ---------------------------------------------------------------------------


@api_bp.route("/status")
def api_status() -> Any:
    """Return live system status from the stats collector."""
    stats = get_stats_collector()
    snapshot = stats.get_snapshot_dict()

    from modules.monitor.monitor import AutoMonitor
    from modules.dependencies import get_auto_monitor

    monitor = get_auto_monitor()
    monitor_status = monitor.get_status() if monitor else {"running": False}

    result = {
        "success": True,
        "app": snapshot["app"],
        "uptime_seconds": snapshot["uptime_seconds"],
        "calls": snapshot["calls"],
        "pipelines": snapshot["pipelines"],
        "avg_latency_ms": snapshot["avg_latency_ms"],
        "last_call": snapshot["last_call"],
        "context": snapshot["context"],
        "providers": snapshot["providers"],
        "monitor": monitor_status,
        "log_count": snapshot["log_count"],
        "server_time": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
    }
    return jsonify(result)


# ---------------------------------------------------------------------------
# API — Manual Mode (delegates to ManualPipeline)
# ---------------------------------------------------------------------------


@api_bp.route("/manual", methods=["POST"])
def api_manual() -> Any:
    """Handle a manual-mode request via ManualPipeline."""
    from modules.pipeline.state import PipelineState

    data: dict = request.get_json(silent=True) or {}

    pstate = PipelineState.instance()
    if not pstate.set_running("manual"):
        return jsonify({
            "success": False,
            "message": "Pipeline is already running. Please wait.",
        })

    pipeline = get_manual_pipeline()
    result = pipeline.execute(
        prompt=data.get("prompt", ""),
        template_id=data.get("template_id", ""),
        screenshot_type=data.get("screenshot_type", "fullscreen"),
        vision_provider=data.get("vision_provider", ""),
        enable_tts=data.get("enable_tts", False),
        tts_provider=data.get("tts_provider", ""),
        persona_name=data.get("persona", ""),
    )

    return jsonify(result.to_dict())


# ---------------------------------------------------------------------------
# API — Auto Mode (delegates to AutoPipeline)
# ---------------------------------------------------------------------------


@api_bp.route("/auto/start", methods=["POST"])
def api_auto_start() -> Any:
    """Start auto-mode via AutoPipeline."""
    data: dict = request.get_json(silent=True) or {}
    interval: int = data.get("interval", Config.AUTO_SCREENSHOT_INTERVAL)

    pipeline = get_auto_pipeline()
    result = pipeline.start(interval=interval)

    lm = get_log_manager()
    if lm:
        lm.record_api_call(
            provider="system",
            provider_type="auto_monitor",
            pipeline="auto",
            latency_ms=result.processing_time_ms,
            status="success" if result.success else "error",
            error=result.error,
        )

    return jsonify(result.to_dict())


@api_bp.route("/auto/stop", methods=["POST"])
def api_auto_stop() -> Any:
    """Stop auto-mode via AutoPipeline."""
    pipeline = get_auto_pipeline()
    result = pipeline.stop()

    lm = get_log_manager()
    if lm:
        lm.record_api_call(
            provider="system",
            provider_type="auto_monitor",
            pipeline="auto",
            latency_ms=result.processing_time_ms,
            status="success" if result.success else "error",
            error=result.error,
        )

    return jsonify(result.to_dict())


@api_bp.route("/auto/status")
def api_auto_status() -> Any:
    """Return auto-mode status via AutoPipeline."""
    pipeline = get_auto_pipeline()
    result = pipeline.get_status()
    return jsonify(result.to_dict())


# ---------------------------------------------------------------------------
# API — Settings (uses SettingsManager)
# ---------------------------------------------------------------------------


@api_bp.route("/settings", methods=["GET"])
def api_get_settings() -> Any:
    """Return current settings (API keys masked)."""
    sm = get_settings_manager()
    if sm:
        settings = sm.get_all(include_secrets=False)
    else:
        settings = Config.as_dict(include_secrets=False)
    return jsonify({"success": True, "settings": settings})


@api_bp.route("/settings", methods=["POST"])
def api_save_settings() -> Any:
    """Persist user settings and immediately apply them."""
    data: dict = request.get_json(silent=True) or {}
    sm = get_settings_manager()
    if sm:
        result = sm.save(data)
        if result.success:
            sm.refresh_config()  # Update Config class immediately
            logger.info("Settings saved and Config refreshed")
        return jsonify({
            "success": result.success,
            "message": result.message,
            "data": result.data,
        })
    return jsonify({
        "success": True,
        "message": "Settings received (no persistence manager available).",
    })


@api_bp.route("/settings/reset", methods=["POST"])
def api_reset_settings() -> Any:
    """Reset settings to defaults and apply immediately."""
    sm = get_settings_manager()
    if sm:
        result = sm.reset()
        if result.success:
            sm.refresh_config()
            logger.info("Settings reset to defaults, Config refreshed")
        return jsonify({
            "success": result.success,
            "message": result.message,
        })
    return jsonify({
        "success": True,
        "message": "Settings reset (no persistence manager).",
    })


@api_bp.route("/provider/test", methods=["POST"])
def api_test_provider() -> Any:
    """Test a provider connection.

    For ``vision`` providers this makes a real API call with a tiny
    mock image.  For other types it checks registration only.
    """
    from providers import get_provider

    data: dict = request.get_json(silent=True) or {}
    provider_type: str = data.get("type", "vision")
    provider_name: str = data.get("provider", "mock")

    logger.info("API /provider/test: type=%s name=%s", provider_type, provider_name)

    # Verify registration first
    try:
        _ = get_provider(provider_type, provider_name)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)})

    # For vision providers, make a real test call
    if provider_type == "vision":
        try:
            from providers import create_vision
            vision = create_vision(provider_name or None)

            # Tiny 32x32 solid-blue PNG for a quick test
            import struct, zlib
            W, H = 32, 32
            def _chunk(ct, d):
                c = ct + d
                return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
            ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
            # One filter-byte (0) per row, then RGB pixels
            raw = b""
            for _ in range(H):
                raw += b"\x00"  # filter=None
                for _ in range(W):
                    raw += b"\x00\x00\xff"  # R=0 G=0 B=255 (blue)
            test_png = (
                b"\x89PNG\r\n\x1a\n"
                + _chunk(b"IHDR", ihdr)
                + _chunk(b"IDAT", zlib.compress(raw))
                + _chunk(b"IEND", b"")
            )

            result = vision.analyze(
                test_png,
                prompt="Say 'OK' if you can see this image.",
            )

            if result.success:
                return jsonify({
                    "success": True,
                    "message": f"Connected to {provider_name} ({result.model}). "
                               f"Latency: {result.latency_ms}ms. "
                               f"Response: {result.content[:100]}...",
                    "latency_ms": result.latency_ms,
                    "model": result.model,
                })
            else:
                return jsonify({
                    "success": False,
                    "message": f"Connection failed: {result.error}",
                })
        except ValueError as exc:
            return jsonify({"success": False, "message": str(exc)})
        except Exception as exc:
            return jsonify({
                "success": False,
                "message": f"Connection test error: {exc}",
            })

    # For chat providers, make a real test call
    if provider_type == "chat":
        try:
            from providers import create_chat
            chat = create_chat(provider_name or None)
            result = chat.chat(
                messages=[{"role": "user", "content": "Say 'hello' in one word."}],
            )
            if result.success:
                return jsonify({
                    "success": True,
                    "message": f"Connected to {provider_name} ({result.model}). "
                               f"Latency: {result.latency_ms}ms. "
                               f"Response: {result.content[:100]}",
                    "latency_ms": result.latency_ms,
                    "model": result.model,
                })
            else:
                return jsonify({
                    "success": False,
                    "message": f"Connection failed: {result.error}",
                })
        except ValueError as exc:
            return jsonify({"success": False, "message": str(exc)})
        except Exception as exc:
            return jsonify({
                "success": False,
                "message": f"Connection test error: {exc}",
            })

    # For TTS providers, make a real test call
    if provider_type == "tts":
        try:
            from providers import create_tts
            tts = create_tts(provider_name or None)
            result = tts.synthesize("Hello, this is a test from ScreenMate.")
            if result.success:
                return jsonify({
                    "success": True,
                    "message": f"Connected to {provider_name}. "
                               f"Latency: {result.latency_ms}ms. "
                               f"Audio: {result.content[:80]}",
                    "latency_ms": result.latency_ms,
                })
            else:
                return jsonify({
                    "success": False,
                    "message": f"Connection failed: {result.error}",
                })
        except ValueError as exc:
            return jsonify({"success": False, "message": str(exc)})
        except Exception as exc:
            return jsonify({
                "success": False,
                "message": f"TTS test error: {exc}",
            })

    # For other provider types, just check registration
    return jsonify({
        "success": True,
        "message": f"Provider {provider_name} ({provider_type}) is registered.",
    })


# ---------------------------------------------------------------------------
# API — Logs
# ---------------------------------------------------------------------------


@api_bp.route("/logs")
def api_get_logs() -> Any:
    """Return recent log entries."""
    count: int = request.args.get("count", 100, type=int)
    return jsonify({
        "success": True,
        "logs": get_recent_logs(count),
    })


@api_bp.route("/logs/clear", methods=["POST"])
def api_clear_logs() -> Any:
    """Clear the log file and API call records."""
    clear_logs()
    lm = get_log_manager()
    if lm:
        lm.clear()
    logger.info("Logs cleared via API")
    return jsonify({"success": True, "message": "Logs cleared."})


@api_bp.route("/logs/api-calls")
def api_get_api_calls() -> Any:
    """Return recent structured API call records."""
    lm = get_log_manager()
    if lm:
        calls = lm.get_recent_calls(50)
        stats = lm.get_call_stats()
    else:
        calls, stats = [], {"total": 0}
    return jsonify({"success": True, "calls": calls, "stats": stats})


# ---------------------------------------------------------------------------
# API — Context
# ---------------------------------------------------------------------------


@api_bp.route("/context")
def api_get_context() -> Any:
    """Return the current context state."""
    ctx = get_context_manager()
    return jsonify({
        "success": True,
        "state": ctx.get_state(),
        "memory": ctx.list_memory(),
    })


@api_bp.route("/context/clear", methods=["POST"])
def api_clear_context() -> Any:
    """Clear the conversation context (preserves memory)."""
    ctx = get_context_manager()
    ctx.clear()
    return jsonify({"success": True, "message": "Context cleared."})


@api_bp.route("/context/memory", methods=["GET"])
def api_get_memory() -> Any:
    """Return persistent memory entries."""
    ctx = get_context_manager()
    return jsonify({"success": True, "memory": ctx.list_memory()})


@api_bp.route("/context/memory", methods=["POST"])
def api_set_memory() -> Any:
    """Store a persistent memory entry."""
    data: dict = request.get_json(silent=True) or {}
    key: str = data.get("key", "")
    value: str = data.get("value", "")
    if not key:
        return jsonify({"success": False, "message": "Key is required."})
    ctx = get_context_manager()
    ctx.set_memory(key, value)
    return jsonify({"success": True, "message": f"Memory '{key}' stored."})


# ---------------------------------------------------------------------------
# API — Prompts
# ---------------------------------------------------------------------------


@api_bp.route("/prompts")
def api_get_prompts() -> Any:
    """Return all prompt templates."""
    pm = get_prompt_manager()
    if pm:
        templates = pm.list_templates()
        return jsonify({
            "success": True,
            "prompts": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "content": t.content,
                    "is_builtin": t.is_builtin,
                }
                for t in templates
            ],
        })
    return jsonify({"success": True, "prompts": []})


@api_bp.route("/prompts/<template_id>")
def api_get_prompt(template_id: str) -> Any:
    """Return a single prompt template."""
    pm = get_prompt_manager()
    if pm:
        tmpl = pm.get_template(template_id)
        if tmpl:
            return jsonify({
                "success": True,
                "prompt": {
                    "id": tmpl.id,
                    "name": tmpl.name,
                    "description": tmpl.description,
                    "content": tmpl.content,
                    "is_builtin": tmpl.is_builtin,
                },
            })
    return jsonify({"success": False, "message": "Template not found."}), 404


# ---------------------------------------------------------------------------
# API — Pipeline State (generic — works for manual, hotkey, auto)
# ---------------------------------------------------------------------------


@api_bp.route("/pipeline/status")
def api_pipeline_status() -> Any:
    """Return the current pipeline state.

    Frontend polls this to show progress from any source (button, hotkey, auto).
    """
    from modules.pipeline.state import PipelineState

    pstate = PipelineState.instance()
    return jsonify({"success": True, "pipeline": pstate.get_status()})


# ---------------------------------------------------------------------------
# API — Hotkey (input layer control)
# ---------------------------------------------------------------------------


@api_bp.route("/hotkey/start", methods=["POST"])
def api_hotkey_start() -> Any:
    """Start the hotkey listener."""
    from modules.dependencies import get_hotkey_manager

    hm = get_hotkey_manager()
    if hm is None:
        return jsonify({"success": False, "message": "HotkeyManager not available."})
    result = hm.start()
    return jsonify(result)


@api_bp.route("/hotkey/stop", methods=["POST"])
def api_hotkey_stop() -> Any:
    """Stop the hotkey listener."""
    from modules.dependencies import get_hotkey_manager

    hm = get_hotkey_manager()
    if hm is None:
        return jsonify({"success": False, "message": "HotkeyManager not available."})
    result = hm.stop()
    return jsonify(result)


@api_bp.route("/hotkey/status")
def api_hotkey_info() -> Any:
    """Return current hotkey configuration."""
    from modules.dependencies import get_hotkey_manager

    hm = get_hotkey_manager()
    if hm is None:
        return jsonify({
            "success": True,
            "hotkey": {"shortcut": "", "enabled": False, "registered": False},
        })
    info = hm.get_info()
    return jsonify({
        "success": True,
        "hotkey": {
            "shortcut": info.shortcut,
            "enabled": info.enabled,
            "registered": info.registered,
        },
    })


@api_bp.route("/hotkey/change", methods=["POST"])
def api_hotkey_change() -> Any:
    """Change the hotkey shortcut."""
    from modules.dependencies import get_hotkey_manager

    data: dict = request.get_json(silent=True) or {}
    shortcut: str = data.get("shortcut", "")

    hm = get_hotkey_manager()
    if hm is None:
        return jsonify({"success": False, "message": "HotkeyManager not available."})
    result = hm.change_shortcut(shortcut)
    return jsonify(result)


# ---------------------------------------------------------------------------
# API — Pipeline: set current persona
# ---------------------------------------------------------------------------


@api_bp.route("/pipeline/persona", methods=["POST"])
def api_set_persona() -> Any:
    """Set the active persona for pipeline runs."""
    from modules.pipeline.state import PipelineState
    data: dict = request.get_json(silent=True) or {}
    name: str = data.get("persona", "")
    PipelineState.instance().set_current_persona(name)
    return jsonify({"success": True, "persona": name})


# ---------------------------------------------------------------------------
# Page — Persona
# ---------------------------------------------------------------------------


@pages_bp.route("/persona")
def persona_page() -> str:
    """Render the Persona management page."""
    return render_template("persona.html")


# ---------------------------------------------------------------------------
# API — Personas
# ---------------------------------------------------------------------------


@api_bp.route("/personas")
def api_get_personas() -> Any:
    """Return all personas."""
    from modules.dependencies import get_persona_manager
    pm = get_persona_manager()
    if pm is None:
        return jsonify({"success": False, "message": "PersonaManager not available."})
    result = pm.list_all()
    return jsonify({
        "success": True,
        "personas": [
            {"name": p.name, "description": p.description,
             "system_prompt": p.system_prompt, "is_default": p.is_default}
            for p in result.personas
        ],
    })


@api_bp.route("/personas/create", methods=["POST"])
def api_create_persona() -> Any:
    """Create a new persona."""
    from modules.dependencies import get_persona_manager
    data: dict = request.get_json(silent=True) or {}
    pm = get_persona_manager()
    if pm is None:
        return jsonify({"success": False, "message": "PersonaManager not available."})
    result = pm.create(
        name=data.get("name", ""),
        description=data.get("description", ""),
        system_prompt=data.get("system_prompt", ""),
    )
    return jsonify(result)


@api_bp.route("/personas/update", methods=["POST"])
def api_update_persona() -> Any:
    """Update an existing persona."""
    from modules.dependencies import get_persona_manager
    data: dict = request.get_json(silent=True) or {}
    pm = get_persona_manager()
    if pm is None:
        return jsonify({"success": False, "message": "PersonaManager not available."})
    result = pm.update(
        name=data.get("name", ""),
        description=data.get("description"),
        system_prompt=data.get("system_prompt"),
    )
    return jsonify(result)


@api_bp.route("/personas/delete", methods=["POST"])
def api_delete_persona() -> Any:
    """Delete a persona."""
    from modules.dependencies import get_persona_manager
    data: dict = request.get_json(silent=True) or {}
    pm = get_persona_manager()
    if pm is None:
        return jsonify({"success": False, "message": "PersonaManager not available."})
    result = pm.delete(name=data.get("name", ""))
    return jsonify(result)
