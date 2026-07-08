"""
Manual-mode pipeline.

Orchestrates: screenshot → prompt composition → vision → (TTS stub)
→ context → stats → log.

Routes call :meth:`ManualPipeline.execute` and receive a
:class:`PipelineResult` — they never interact with providers directly.
"""

import time
from typing import Optional

from config.settings import Config
from modules.context.manager import ContextManager
from modules.logger.logger import get_logger, LogManager
from modules.pipeline.pipeline_result import PipelineResult
from modules.screenshot.capture import ScreenshotCapture
from modules.telemetry.stats import StatsCollector
from providers import create_vision, create_tts

logger = get_logger(__name__)


class ManualPipeline:
    """Execute the manual-mode workflow.

    Usage::

        pipeline = ManualPipeline(context_manager, screenshot, stats)
        result = pipeline.execute(
            prompt="What's on my screen?",
            template_id="programming",
            screenshot_type="fullscreen",
            vision_provider="openai",
        )
    """

    def __init__(
        self,
        context_manager: ContextManager,
        screenshot: ScreenshotCapture,
        stats: StatsCollector,
    ) -> None:
        """Initialise the pipeline.

        Args:
            context_manager: Shared context instance.
            screenshot: Screenshot capture module.
            stats: Telemetry collector.
        """
        self._ctx = context_manager
        self._screenshot = screenshot
        self._stats = stats
        logger.info("ManualPipeline initialised")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        prompt: str = "",
        template_id: str = "",
        screenshot_type: str = "fullscreen",
        vision_provider: str = "",
        enable_tts: bool = False,
        tts_provider: str = "",
    ) -> PipelineResult:
        """Run the full manual-mode workflow.

        Args:
            prompt: User prompt text.
            template_id: Prompt template ID (e.g. ``"programming"``).
                Empty → use default from Config.
            screenshot_type: ``"fullscreen"`` or ``"region"``.
            vision_provider: Provider name (empty → use config).
            enable_tts: Whether to synthesise speech.
            tts_provider: Provider name for TTS (empty → use config).

        Returns:
            A :class:`PipelineResult` with the outcome.
        """
        t_start = time.perf_counter()
        effective_vision = vision_provider or Config.VISION_PROVIDER

        logger.info(
            "ManualPipeline: prompt_len=%d, template=%s, type=%s, vision=%s, tts=%s",
            len(prompt),
            template_id or Config.PROMPT_TEMPLATE,
            screenshot_type,
            effective_vision,
            enable_tts,
        )

        # ---- Step 1: Screenshot ----
        shot = None
        try:
            if screenshot_type == "fullscreen":
                shot = self._screenshot.capture_fullscreen()
            else:
                shot = self._screenshot.capture_region()

            if not shot.get("success", True):
                return PipelineResult.fail(
                    error=f"Screenshot failed: {shot.get('error', 'unknown')}",
                    processing_time_ms=(time.perf_counter() - t_start) * 1000,
                )

            self._stats.record_call(
                provider_type="screenshot",
                provider_name="mss",
                model="screen",
                latency_ms=shot.get("capture_ms", 0),
                success=True,
                pipeline="manual",
            )
        except Exception as exc:
            logger.error("Screenshot failed: %s", exc)
            self._stats.record_pipeline_run("manual")
            return PipelineResult.fail(
                error=f"Screenshot error: {exc}",
                processing_time_ms=(time.perf_counter() - t_start) * 1000,
            )

        # ---- Step 2: Compose prompt from template ----
        system_prompt, final_user_prompt = self._compose_prompt(
            prompt, template_id
        )

        # ---- Step 3: Vision analysis ----
        vision_response = None
        try:
            vision = create_vision(effective_vision or None)
            vision_response = vision.analyze(
                shot["image_bytes"],
                prompt=final_user_prompt,
                system_prompt=system_prompt,
            )

            self._stats.record_call(
                provider_type="vision",
                provider_name=vision_response.provider,
                model=vision_response.model,
                latency_ms=vision_response.latency_ms,
                success=vision_response.success,
                pipeline="manual",
            )

            # Record structured API log
            self._log_api_call(
                provider=vision_response.provider,
                provider_type="vision",
                pipeline="manual",
                latency_ms=vision_response.latency_ms,
                status="success" if vision_response.success else "error",
                error=vision_response.error,
                metadata={
                    "model": vision_response.model,
                    "usage": vision_response.usage,
                },
            )

            if not vision_response.success:
                self._stats.record_pipeline_run("manual")
                return PipelineResult.fail(
                    error=vision_response.error or "Vision analysis failed",
                    processing_time_ms=(time.perf_counter() - t_start) * 1000,
                    vision_response=vision_response,
                )

        except Exception as exc:
            logger.error("Vision step failed: %s", exc)
            self._stats.record_pipeline_run("manual")
            return PipelineResult.fail(
                error=f"Vision provider error: {exc}",
                processing_time_ms=(time.perf_counter() - t_start) * 1000,
            )

        # ---- Step 4: TTS (optional) ----
        tts_response = None
        if enable_tts:
            try:
                tts = create_tts(tts_provider or None)
                tts_response = tts.synthesize(vision_response.content)
                self._stats.record_call(
                    provider_type="tts",
                    provider_name=tts_response.provider,
                    model=tts_response.model,
                    latency_ms=tts_response.latency_ms,
                    success=tts_response.success,
                    pipeline="manual",
                )
            except Exception as exc:
                logger.warning("TTS step failed (non-fatal): %s", exc)

        # ---- Step 5: Update context ----
        display_prompt = prompt or "(screenshot analysis)"
        self._ctx.add_message("user", display_prompt)
        self._ctx.add_message("assistant", vision_response.content)

        # ---- Step 6: Telemetry ----
        self._stats.record_pipeline_run("manual")

        elapsed_ms = (time.perf_counter() - t_start) * 1000

        return PipelineResult.ok(
            message="Manual mode completed",
            processing_time_ms=round(elapsed_ms, 2),
            vision_response=vision_response,
            tts_response=tts_response,
            data={
                "screenshot": {
                    "width": shot["width"],
                    "height": shot["height"],
                    "timestamp": shot["timestamp"],
                    "base64": shot.get("base64", ""),
                },
                "prompt": {
                    "template_id": template_id or Config.PROMPT_TEMPLATE,
                    "user_prompt": prompt,
                },
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compose_prompt(
        user_prompt: str, template_id: str
    ) -> tuple[str, str]:
        """Build (system_prompt, user_prompt) from PromptManager.

        Args:
            user_prompt: The user's raw input.
            template_id: Prompt template identifier.

        Returns:
            A ``(system_prompt, final_user_prompt)`` tuple.
        """
        effective_template = template_id or Config.PROMPT_TEMPLATE

        # Load template from PromptManager
        template_content = Config.SYSTEM_PROMPT
        try:
            from modules.dependencies import get_prompt_manager
            pm = get_prompt_manager()
            if pm:
                template_content = pm.get_template_content(effective_template)
        except Exception:
            pass

        system_prompt = template_content

        # Combine template guidance with user prompt
        if user_prompt.strip():
            final_prompt = user_prompt
        else:
            final_prompt = "Please analyze this screenshot and describe what you see."

        return system_prompt, final_prompt

    @staticmethod
    def _log_api_call(
        provider: str,
        provider_type: str,
        pipeline: str,
        latency_ms: float,
        status: str,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record a structured API call via LogManager."""
        try:
            lm = LogManager.instance()
            lm.record_api_call(
                provider=provider,
                provider_type=provider_type,
                pipeline=pipeline,
                latency_ms=latency_ms,
                status=status,
                error=error,
            )
            if metadata:
                logger.debug("API call metadata: %s", metadata)
        except Exception:
            pass  # LogManager is best-effort
