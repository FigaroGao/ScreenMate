"""
ScreenMate — A desktop AI assistant with vision, chat, and TTS capabilities.

This is the Flask application entry point.  Run with::

    python app.py

The app serves the Web UI and REST API.  All AI providers are mocked
in this version; see the README for the roadmap.
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so all imports work
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from flask import Flask

from config.settings import Config
from modules.logger.logger import get_logger, LogManager

# Initialise logger early so startup messages are captured
logger = get_logger("screenmate")

# ---------------------------------------------------------------------------
# Import provider packages to trigger auto-registration
# ---------------------------------------------------------------------------
import providers.vision  # noqa: E402
import providers.chat    # noqa: E402
import providers.tts     # noqa: E402

# ---------------------------------------------------------------------------
# Initialise infrastructure singletons early
# ---------------------------------------------------------------------------
from modules.context.manager import ContextManager          # noqa: E402
from modules.screenshot.capture import ScreenshotCapture     # noqa: E402
from modules.monitor.monitor import AutoMonitor              # noqa: E402
from modules.telemetry.stats import StatsCollector            # noqa: E402
from modules.settings.persistent import SettingsManager       # noqa: E402
from modules.prompts.manager import PromptManager             # noqa: E402

# ---------------------------------------------------------------------------
# Create singletons
# ---------------------------------------------------------------------------

context_manager = ContextManager()
screenshot_capture = ScreenshotCapture()
auto_monitor = AutoMonitor()
stats_collector = StatsCollector.instance()
settings_manager = SettingsManager()
prompt_manager = PromptManager()
log_manager = LogManager.instance()

# Apply saved settings overrides
settings_manager.refresh_config()

# Bind context manager to stats collector so Dashboard can show live counts
stats_collector.bind_context_manager(context_manager)

# Bind log counter for live log count
from modules.logger.logger import _manager as _logger_mgr  # noqa: E402
stats_collector.bind_log_counter(lambda: _logger_mgr.log_count)

# ---------------------------------------------------------------------------
# Import pipelines (depends on singletons above)
# ---------------------------------------------------------------------------
from modules.pipeline.manual_pipeline import ManualPipeline  # noqa: E402
from modules.pipeline.auto_pipeline import AutoPipeline      # noqa: E402

manual_pipeline = ManualPipeline(context_manager, screenshot_capture, stats_collector)
auto_pipeline = AutoPipeline(context_manager, auto_monitor, stats_collector)

# ---------------------------------------------------------------------------
# Initialise HotkeyManager
# ---------------------------------------------------------------------------
from modules.hotkey.manager import HotkeyManager  # noqa: E402

hotkey_manager = HotkeyManager(
    on_trigger=lambda: manual_pipeline.execute(
        prompt="",
        template_id=Config.PROMPT_TEMPLATE,
    ),
    on_get_settings_manager=lambda: settings_manager,
)
# Register hotkey on startup
result = hotkey_manager.register()
logger.info("HotkeyManager: %s", result.get("message", "started"))

# ---------------------------------------------------------------------------
# Wire dependencies for routes
# ---------------------------------------------------------------------------
import modules.dependencies as deps  # noqa: E402

deps.setup(
    manual_pipeline=manual_pipeline,
    auto_pipeline=auto_pipeline,
    context_manager=context_manager,
    screenshot_capture=screenshot_capture,
    auto_monitor=auto_monitor,
    stats_collector=stats_collector,
    settings_manager=settings_manager,
    prompt_manager=prompt_manager,
    log_manager=log_manager,
    hotkey_manager=hotkey_manager,
)

# ---------------------------------------------------------------------------
# Import routes (depends on dependencies being wired)
# ---------------------------------------------------------------------------
from routes.main import pages_bp, api_bp  # noqa: E402


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        A configured Flask instance ready to run.
    """
    app = Flask(
        __name__,
        template_folder=str(_PROJECT_ROOT / "templates"),
        static_folder=str(_PROJECT_ROOT / "static"),
    )

    # Basic config
    app.config["SECRET_KEY"] = Config.APP_SECRET_KEY
    app.config["APP_NAME"] = Config.APP_NAME
    app.config["APP_VERSION"] = Config.APP_VERSION

    # Make Config available in all templates
    @app.context_processor
    def inject_config() -> dict:
        return {"config": Config}

    # Register blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    # Register error handlers
    @app.errorhandler(404)
    def not_found(_error):
        from flask import jsonify, request

        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Not found"}), 404
        return (
            "<h1>404</h1><p>Page not found.</p><a href='/'>Back to Dashboard</a>",
            404,
        )

    @app.errorhandler(500)
    def server_error(error):
        logger.error("Internal server error: %s", error)
        from flask import jsonify, request

        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Internal error"}), 500
        return "<h1>500</h1><p>Internal server error.</p>", 500

    logger.info("Flask app created successfully")
    return app


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == "__main__":
    logger.info(
        "Starting %s v%s on %s:%s",
        Config.APP_NAME,
        Config.APP_VERSION,
        Config.APP_HOST,
        Config.APP_PORT,
    )
    app.run(
        host=Config.APP_HOST,
        port=Config.APP_PORT,
        debug=Config.APP_DEBUG,
    )
