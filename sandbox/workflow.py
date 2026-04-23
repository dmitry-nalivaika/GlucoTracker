"""SandboxWorkflow — orchestrates the GlucoTrack workflow with real-time event emission.

Each step emits structured events that the WebSocket client uses to animate
the pipeline diagram and populate the request/response event log.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from glucotrack.models.base import Base
from glucotrack.repositories.analysis_repository import AnalysisRepository
from glucotrack.services.session_service import SessionService
from glucotrack.storage.local_storage import StorageRepository
from sandbox.mocks import MockAIService, MockMiroService
from sandbox.seed_data import (
    ACTIVITY_DESCRIPTION,
    CGM_SCREENSHOT_BYTES,
    CGM_TELEGRAM_FILE_ID,
    CGM_TIMING_LABEL,
    FOOD_PHOTO_BYTES,
    FOOD_TELEGRAM_FILE_ID,
    SANDBOX_USER_ID,
)

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], Awaitable[None]]

# Temporary storage root for sandbox runs
_SANDBOX_STORAGE_ROOT = "/tmp/glucotrack_sandbox"


def _load_dotenv() -> None:
    """Populate os.environ from .env at project root (best-effort)."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


class SandboxWorkflow:
    """Run the full GlucoTrack session workflow end-to-end.

    Components (AI, Miro) can be real or mock. Events are emitted via the
    ``callback`` coroutine so the WebSocket layer can forward them to the browser.
    """

    def __init__(
        self,
        callback: EventCallback,
        ai_mode: str = "mock",
        miro_mode: str = "mock",
    ) -> None:
        self._cb = callback
        self._ai_mode = ai_mode
        self._miro_mode = miro_mode

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Execute all workflow steps, emitting events at each stage."""
        _load_dotenv()

        await self._info("workflow", "Starting sandbox workflow run", {"user_id": SANDBOX_USER_ID})

        # Create a fresh in-memory database for each run
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_local = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        try:
            async with session_local() as db:
                await self._run_steps(db)
        except Exception as exc:
            logger.exception("Unexpected sandbox workflow error")
            await self._emit(
                "workflow_error",
                "workflow",
                "workflow",
                {"error": str(exc)},
            )
        finally:
            await engine.dispose()
            await self._info("workflow", "Workflow run complete", {})

    # ------------------------------------------------------------------
    # Internal: step orchestration
    # ------------------------------------------------------------------

    async def _run_steps(self, db: AsyncSession) -> None:
        storage = StorageRepository(_SANDBOX_STORAGE_ROOT)
        session_service = SessionService(db=db, storage=storage)
        analysis_repo = AnalysisRepository(db)

        # Build AI service
        ai_service = await self._build_ai_service()
        if ai_service is None:
            return  # error already emitted

        # Build Miro service
        miro_service = await self._build_miro_service()
        if miro_service is None:
            return  # error already emitted

        # ── Step 1: Open Session ─────────────────────────────────────
        await self._step_start("open_session")
        await self._db_call(
            "open_session",
            "session_service → DB",
            {"action": "get_or_create_user + create_session", "user_id": SANDBOX_USER_ID},
        )
        t = time.perf_counter()
        session, is_new = await session_service.get_or_open_session(SANDBOX_USER_ID)
        await self._db_result(
            "open_session",
            "session_service ← DB",
            {"session_id": session.id, "is_new": is_new},
            t,
        )
        await self._step_success(
            "open_session",
            {"session_id": session.id, "is_new": is_new},
        )

        # ── Step 2: Add Food Photo ────────────────────────────────────
        await self._step_start("add_food")
        await self._db_call(
            "add_food",
            "session_service → Storage + DB",
            {
                "action": "save_file + add_food_entry",
                "telegram_file_id": FOOD_TELEGRAM_FILE_ID,
                "file_size_bytes": len(FOOD_PHOTO_BYTES),
                "entry_type": "food",
            },
        )
        t = time.perf_counter()
        await session_service.handle_photo(
            telegram_user_id=SANDBOX_USER_ID,
            file_data=FOOD_PHOTO_BYTES,
            telegram_file_id=FOOD_TELEGRAM_FILE_ID,
            entry_type="food",
        )
        counts = await session_service.get_entry_counts(SANDBOX_USER_ID)
        await self._db_result(
            "add_food",
            "session_service ← DB",
            {"entry_counts": counts},
            t,
        )
        await self._step_success("add_food", {"entry_counts": counts})

        # ── Step 3: Add CGM Screenshot ───────────────────────────────
        await self._step_start("add_cgm")
        await self._db_call(
            "add_cgm",
            "session_service → Storage + DB",
            {
                "action": "save_file + add_cgm_entry",
                "telegram_file_id": CGM_TELEGRAM_FILE_ID,
                "timing_label": CGM_TIMING_LABEL,
                "file_size_bytes": len(CGM_SCREENSHOT_BYTES),
                "entry_type": "cgm",
            },
        )
        t = time.perf_counter()
        await session_service.handle_photo(
            telegram_user_id=SANDBOX_USER_ID,
            file_data=CGM_SCREENSHOT_BYTES,
            telegram_file_id=CGM_TELEGRAM_FILE_ID,
            entry_type="cgm",
            timing_label=CGM_TIMING_LABEL,
        )
        counts = await session_service.get_entry_counts(SANDBOX_USER_ID)
        await self._db_result(
            "add_cgm",
            "session_service ← DB",
            {"entry_counts": counts},
            t,
        )
        await self._step_success("add_cgm", {"entry_counts": counts})

        # ── Step 4: Add Activity Note ────────────────────────────────
        await self._step_start("add_activity")
        await self._db_call(
            "add_activity",
            "session_service → DB",
            {"action": "add_activity_entry", "description": ACTIVITY_DESCRIPTION},
        )
        t = time.perf_counter()
        await session_service.handle_activity(
            telegram_user_id=SANDBOX_USER_ID,
            text=ACTIVITY_DESCRIPTION,
        )
        counts = await session_service.get_entry_counts(SANDBOX_USER_ID)
        await self._db_result(
            "add_activity",
            "session_service ← DB",
            {"entry_counts": counts},
            t,
        )
        await self._step_success("add_activity", {"description": ACTIVITY_DESCRIPTION})

        # ── Step 5: Complete Session ─────────────────────────────────
        await self._step_start("complete_session")
        await self._db_call(
            "complete_session",
            "session_service → DB",
            {"action": "validate_completion + set_status=COMPLETED"},
        )
        t = time.perf_counter()
        completed = await session_service.complete_session(SANDBOX_USER_ID)
        await self._db_result(
            "complete_session",
            "session_service ← DB",
            {"session_id": completed.id, "status": str(completed.status)},
            t,
        )
        await self._step_success(
            "complete_session",
            {"session_id": completed.id, "status": str(completed.status)},
        )

        # ── Step 6: AI Analysis ──────────────────────────────────────
        await self._step_start("ai_analysis")
        food_entries = [
            {"telegram_file_id": FOOD_TELEGRAM_FILE_ID, "file_path": "sandbox/food.jpg"}
        ]
        cgm_entries = [
            {
                "telegram_file_id": CGM_TELEGRAM_FILE_ID,
                "file_path": "sandbox/cgm.jpg",
                "timing_label": CGM_TIMING_LABEL,
            }
        ]
        activity_entries = [{"description": ACTIVITY_DESCRIPTION}]

        api_label = "Anthropic API (MOCK)" if self._ai_mode == "mock" else "Anthropic API (REAL)"
        await self._api_request(
            "ai_analysis",
            api_label,
            {
                "model": "claude-3-5-sonnet-20241022",
                "food_photos": len(food_entries),
                "cgm_screenshots": len(cgm_entries),
                "activity_notes": len(activity_entries),
                "mode": self._ai_mode,
            },
        )

        async def _load_file_bytes(fid: str) -> bytes:
            if fid == CGM_TELEGRAM_FILE_ID:
                return CGM_SCREENSHOT_BYTES
            return FOOD_PHOTO_BYTES

        t = time.perf_counter()
        try:
            ai_result = await ai_service.analyse_session(
                user_id=SANDBOX_USER_ID,
                food_entries=food_entries,
                cgm_entries=cgm_entries,
                activity_entries=activity_entries,
                load_file_bytes=_load_file_bytes,
            )
        except Exception as exc:
            await self._step_error("ai_analysis", f"AI service error: {exc}")
            return

        await self._api_response("ai_analysis", api_label, ai_result, t)

        # Persist analysis
        await self._db_call(
            "ai_analysis",
            "analysis_repo → DB",
            {"action": "save_analysis"},
        )
        t2 = time.perf_counter()
        activity_data = ai_result.get("activity")
        analysis = await analysis_repo.save_analysis(
            user_id=SANDBOX_USER_ID,
            session_id=completed.id,
            nutrition=ai_result.get("nutrition", {}),
            glucose_curve=ai_result.get("glucose_curve", []),
            correlation=ai_result.get("correlation", {}),
            recommendations=ai_result.get("recommendations", []),
            within_target_notes=ai_result.get("target_range_note"),
            raw_response=json.dumps(ai_result),
            activity_json=json.dumps(activity_data) if activity_data is not None else None,
        )
        await db.commit()
        await self._db_result(
            "ai_analysis",
            "analysis_repo ← DB",
            {"analysis_id": analysis.id},
            t2,
        )

        # Emit Telegram message event
        nutrition = ai_result.get("nutrition", {})
        await self._emit(
            "telegram_message",
            "ai_analysis",
            "Telegram → User",
            {
                "action": "send_message",
                "preview": (
                    f"Nutrition: {nutrition.get('carbs_g')}g carbs, "
                    f"{nutrition.get('proteins_g')}g protein, "
                    f"{nutrition.get('fats_g')}g fat | "
                    f"Target range: {ai_result.get('target_range_note', '')}"
                ),
            },
        )

        await self._step_success(
            "ai_analysis",
            {
                "analysis_id": analysis.id,
                "cgm_parseable": ai_result.get("cgm_parseable"),
                "nutrition": ai_result.get("nutrition"),
                "target_range_note": ai_result.get("target_range_note"),
                "recommendations_count": len(ai_result.get("recommendations", [])),
            },
        )

        # ── Step 7: Miro Card ────────────────────────────────────────
        await self._step_start("miro_card")
        miro_label = "Miro API (MOCK)" if self._miro_mode == "mock" else "Miro API (REAL)"
        board_id = getattr(miro_service, "board_id", "unknown")
        # Build session_images for feature 002 enhanced card
        session_images: list[dict[str, Any]] = [
            {
                "type": "food",
                "file_bytes": FOOD_PHOTO_BYTES,
                "telegram_file_id": FOOD_TELEGRAM_FILE_ID,
            },
            {
                "type": "cgm",
                "file_bytes": CGM_SCREENSHOT_BYTES,
                "telegram_file_id": CGM_TELEGRAM_FILE_ID,
            },
        ]
        await self._api_request(
            "miro_card",
            miro_label,
            {
                "action": "POST /boards/{board_id}/frames (enhanced)",
                "board_id": board_id,
                "images": len(session_images),
                "mode": self._miro_mode,
            },
        )
        t = time.perf_counter()
        try:
            if hasattr(miro_service, "create_enhanced_session_card"):
                card_id = await miro_service.create_enhanced_session_card(
                    analysis=analysis, session_images=session_images
                )
            else:
                card_id = await miro_service.create_session_card(analysis=analysis)
            await self._api_response(
                "miro_card",
                miro_label,
                {"frame_id": card_id, "status": 201},
                t,
            )
            await self._step_success("miro_card", {"frame_id": card_id})
        except Exception as exc:
            await self._api_response(
                "miro_card",
                miro_label,
                {"error": str(exc)},
                t,
                is_error=True,
            )
            await self._step_error("miro_card", f"Miro error (non-blocking): {exc}")

    # ------------------------------------------------------------------
    # Internal: service builders
    # ------------------------------------------------------------------

    async def _build_ai_service(self) -> Any:
        if self._ai_mode == "mock":
            await self._info("ai_analysis", "Using MockAIService (no API key needed)", {})
            return MockAIService(latency_seconds=0.5)

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        model = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        if not api_key:
            await self._emit(
                "config_error",
                "ai_analysis",
                "Config",
                {
                    "error": (
                        "ANTHROPIC_API_KEY not found. "
                        "Add it to .env or set as environment variable, "
                        "or switch AI to Mock mode."
                    )
                },
            )
            return None

        from glucotrack.services.ai_service import AIService

        await self._info(
            "ai_analysis",
            f"Using real AIService with model={model}",
            {"model": model},
        )
        return AIService(
            api_key=api_key,
            model=model,
            max_calls_per_user_per_day=100,
            max_tokens_per_session=4000,
        )

    async def _build_miro_service(self) -> Any:
        if self._miro_mode == "mock":
            await self._info("miro_card", "Using MockMiroService (no token needed)", {})
            return MockMiroService(latency_seconds=0.3)

        token = os.environ.get("MIRO_ACCESS_TOKEN", "")
        board_id = os.environ.get("MIRO_BOARD_ID", "")
        if not token or not board_id:
            await self._emit(
                "config_error",
                "miro_card",
                "Config",
                {
                    "error": (
                        "MIRO_ACCESS_TOKEN or MIRO_BOARD_ID not found. "
                        "Add them to .env or set as environment variables, "
                        "or switch Miro to Mock mode."
                    )
                },
            )
            return None

        from glucotrack.services.miro_service import MiroService

        await self._info(
            "miro_card",
            f"Using real MiroService, board_id={board_id}",
            {"board_id": board_id},
        )
        return MiroService(
            access_token=token,
            board_id=board_id,
            _retry_delays=(1.0, 2.0),
        )

    # ------------------------------------------------------------------
    # Internal: event helpers
    # ------------------------------------------------------------------

    async def _emit(
        self,
        event_type: str,
        step: str,
        label: str,
        payload: dict[str, Any],
        *,
        is_error: bool = False,
    ) -> None:
        event: dict[str, Any] = {
            "id": uuid.uuid4().hex[:8],
            "timestamp": datetime.now(UTC).isoformat(),
            "type": event_type,
            "step": step,
            "label": label,
            "payload": payload,
        }
        if is_error:
            event["is_error"] = True
        await self._cb(event)

    async def _step_start(self, step: str) -> None:
        await self._emit("step_start", step, step, {})

    async def _step_success(self, step: str, data: dict[str, Any]) -> None:
        await self._emit("step_success", step, step, data)

    async def _step_error(self, step: str, error: str) -> None:
        await self._emit("step_error", step, step, {"error": error}, is_error=True)

    async def _db_call(self, step: str, label: str, payload: dict[str, Any]) -> None:
        await self._emit("db_request", step, label, payload)

    async def _db_result(self, step: str, label: str, data: dict[str, Any], t_start: float) -> None:
        payload = dict(data)
        payload["latency_ms"] = round((time.perf_counter() - t_start) * 1000)
        await self._emit("db_response", step, label, payload)

    async def _api_request(self, step: str, label: str, payload: dict[str, Any]) -> None:
        await self._emit("api_request", step, label, payload)

    async def _api_response(
        self,
        step: str,
        label: str,
        data: Any,
        t_start: float,
        *,
        is_error: bool = False,
    ) -> None:
        payload: dict[str, Any] = {"latency_ms": round((time.perf_counter() - t_start) * 1000)}
        if isinstance(data, dict):
            payload.update(data)
        else:
            payload["data"] = data
        await self._emit("api_response", step, label, payload, is_error=is_error)

    async def _info(self, step: str, message: str, data: dict[str, Any]) -> None:
        payload = dict(data)
        payload["message"] = message
        await self._emit("info", step, "System", payload)
