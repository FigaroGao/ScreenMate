"""
Manual-mode pipeline.

Orchestrates: screenshot → vision → persona/chat → (TTS) → context → stats.
"""

import time
from typing import Optional

from config.settings import Config
from modules.context.manager import ContextManager
from modules.logger.logger import get_logger, LogManager
from modules.pipeline.pipeline_result import PipelineResult
from modules.pipeline.state import PipelineState, PipelineProgress
from modules.screenshot.capture import ScreenshotCapture
from modules.telemetry.stats import StatsCollector
from providers import create_vision, create_chat, create_tts

logger = get_logger(__name__)


class ManualPipeline:
    """Execute the manual-mode workflow.

    Flow: screenshot → vision → persona/chat → (tts) → context → stats.
    """

    def __init__(
        self,
        context_manager: ContextManager,
        screenshot: ScreenshotCapture,
        stats: StatsCollector,
    ) -> None:
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
        persona_name: str = "",
    ) -> PipelineResult:
        """Run the manual-mode workflow.

        Args:
            prompt: User prompt text.
            template_id: Prompt template ID.
            screenshot_type: ``"fullscreen"``.
            vision_provider: Provider name (empty → use config).
            enable_tts: Whether to synthesise speech.
            tts_provider: Provider name for TTS.
            persona_name: Persona name for styled Chat response.
        """
        t_start = time.perf_counter()
        effective_vision = vision_provider or Config.VISION_PROVIDER

        logger.info(
            "ManualPipeline: prompt_len=%d, template=%s, vision=%s, persona=%s",
            len(prompt), template_id or Config.PROMPT_TEMPLATE,
            effective_vision, persona_name or "(none)",
        )

        # ---- Step 1: Screenshot ----
        PipelineState.instance().set_progress(PipelineProgress.CAPTURING)
        try:
            shot = self._screenshot.capture_fullscreen()
            if not shot.get("success", True):
                PipelineState.instance().set_failed(
                    f"Screenshot failed: {shot.get('error', 'unknown')}")
                self._stats.record_pipeline_run("manual")
                return PipelineResult.fail(
                    error=f"Screenshot failed: {shot.get('error', 'unknown')}",
                    processing_time_ms=(time.perf_counter() - t_start) * 1000,
                )
            self._stats.record_call(
                provider_type="screenshot", provider_name="mss", model="screen",
                latency_ms=shot.get("capture_ms", 0), success=True, pipeline="manual",
            )
        except Exception as exc:
            logger.error("Screenshot failed: %s", exc)
            PipelineState.instance().set_failed(f"Screenshot error: {exc}")
            self._stats.record_pipeline_run("manual")
            return PipelineResult.fail(
                error=f"Screenshot error: {exc}",
                processing_time_ms=(time.perf_counter() - t_start) * 1000,
            )

        # ---- Step 2: Compose prompt ----
        system_prompt, final_user_prompt = self._compose_prompt(prompt, template_id)

        # ---- Step 3: Vision ----
        PipelineState.instance().set_progress(PipelineProgress.ANALYZING)
        try:
            vision = create_vision(effective_vision or None)
            vision_response = vision.analyze(
                shot["image_bytes"], prompt=final_user_prompt,
                system_prompt=system_prompt,
            )
            self._stats.record_call(
                provider_type="vision", provider_name=vision_response.provider,
                model=vision_response.model, latency_ms=vision_response.latency_ms,
                success=vision_response.success, pipeline="manual",
            )
            self._log_api_call(
                provider=vision_response.provider, provider_type="vision",
                pipeline="manual", latency_ms=vision_response.latency_ms,
                status="success" if vision_response.success else "error",
                error=vision_response.error,
                metadata={"model": vision_response.model, "usage": vision_response.usage},
            )
            if not vision_response.success:
                self._stats.record_pipeline_run("manual")
                PipelineState.instance().set_failed(
                    vision_response.error or "Vision analysis failed")
                return PipelineResult.fail(
                    error=vision_response.error or "Vision analysis failed",
                    processing_time_ms=(time.perf_counter() - t_start) * 1000,
                    vision_response=vision_response,
                )
        except Exception as exc:
            logger.error("Vision step failed: %s", exc)
            PipelineState.instance().set_failed(f"Vision provider error: {exc}")
            self._stats.record_pipeline_run("manual")
            return PipelineResult.fail(
                error=f"Vision provider error: {exc}",
                processing_time_ms=(time.perf_counter() - t_start) * 1000,
            )

        # ---- Step 4: Persona / Chat (optional) ----
        chat_response = None
        if persona_name:
            PipelineState.instance().set_progress(PipelineProgress.ANALYZING)
            try:
                persona_prompt = self._get_persona_prompt(persona_name)
                chat_provider = create_chat(Config.CHAT_PROVIDER or None)
                chat_response = chat_provider.chat(
                    messages=[{
                        "role": "user",
                        "content": (
                            f"Here is a description of what I see on the screen:\n\n"
                            f"{vision_response.content}\n\n"
                            f"The user asked: \"{prompt or 'Describe this.'}\"\n\n"
                            f"Please respond according to your persona."
                        ),
                    }],
                    system_prompt=persona_prompt,
                )
                self._stats.record_call(
                    provider_type="chat", provider_name=chat_response.provider,
                    model=chat_response.model, latency_ms=chat_response.latency_ms,
                    success=chat_response.success, pipeline="manual",
                )
            except Exception as exc:
                logger.warning("Persona/chat step failed (non-fatal): %s", exc)

        # ---- Step 5: TTS (optional) ----
        tts_response = None
        if enable_tts:
            try:
                tts = create_tts(tts_provider or None)
                tts_response = tts.synthesize(vision_response.content)
                self._stats.record_call(
                    provider_type="tts", provider_name=tts_response.provider,
                    model=tts_response.model, latency_ms=tts_response.latency_ms,
                    success=tts_response.success, pipeline="manual",
                )
            except Exception as exc:
                logger.warning("TTS step failed (non-fatal): %s", exc)

        # ---- Step 6: Context ----
        self._ctx.add_message("user", prompt or "(screenshot analysis)")
        self._ctx.add_message("assistant", vision_response.content)

        # ---- Step 7: Stats ----
        self._stats.record_pipeline_run("manual")
        elapsed_ms = (time.perf_counter() - t_start) * 1000

        final_result = PipelineResult.ok(
            message="Manual mode completed",
            processing_time_ms=round(elapsed_ms, 2),
            vision_response=vision_response,
            tts_response=tts_response,
            chat_response=chat_response,
            data={
                "screenshot": {
                    "width": shot["width"], "height": shot["height"],
                    "timestamp": shot["timestamp"], "base64": shot.get("base64", ""),
                },
                "prompt": {
                    "template_id": template_id or Config.PROMPT_TEMPLATE,
                    "user_prompt": prompt,
                },
                "persona": persona_name or "",
            },
        )

        PipelineState.instance().set_completed(final_result.to_dict())
        return final_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_persona_prompt(persona_name: str) -> str:
        """Load system prompt for a persona."""
        try:
            from modules.dependencies import get_persona_manager
            pm = get_persona_manager()
            if pm:
                return pm.get_system_prompt(persona_name)
        except Exception:
            pass
        return "You are a helpful assistant."

    @staticmethod
    def _compose_prompt(user_prompt: str, template_id: str) -> tuple[str, str]:
        effective_template = template_id or Config.PROMPT_TEMPLATE
        template_content = Config.SYSTEM_PROMPT
        try:
            from modules.dependencies import get_prompt_manager
            pm = get_prompt_manager()
            if pm:
                template_content = pm.get_template_content(effective_template)
        except Exception:
            pass
        if user_prompt.strip():
            final_prompt = user_prompt
        else:
            final_prompt = "Please analyze this screenshot and describe what you see."
        return template_content, final_prompt

    @staticmethod
    def _log_api_call(
        provider: str, provider_type: str, pipeline: str,
        latency_ms: float, status: str, error: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        try:
            lm = LogManager.instance()
            lm.record_api_call(
                provider=provider, provider_type=provider_type,
                pipeline=pipeline, latency_ms=latency_ms,
                status=status, error=error,
            )
            if metadata:
                logger.debug("API call metadata: %s", metadata)
        except Exception:
            pass
