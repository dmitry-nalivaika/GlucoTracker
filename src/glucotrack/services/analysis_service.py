"""AnalysisService — orchestrates AI analysis pipeline.

Flow: completed session → AIService → persist AIAnalysis → send Telegram message
      → fire-and-forget Miro card creation.

Miro failure MUST NOT block Telegram delivery (FR-009, Constitution II).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from telegram.constants import ParseMode

from glucotrack.bot import formatters
from glucotrack.models.miro import MiroCard, MiroCardSourceType, MiroCardStatus
from glucotrack.models.session import Session
from glucotrack.repositories.analysis_repository import AnalysisRepository
from glucotrack.repositories.session_repository import SessionRepository
from glucotrack.services.ai_service import AIService, AnalysisError
from glucotrack.storage.local_storage import StorageRepository

logger = logging.getLogger(__name__)


class AnalysisService:
    """Orchestrates the full analysis pipeline for a completed session."""

    def __init__(
        self,
        db: AsyncSession,
        ai_service: AIService,
        miro_service: Any,
        storage_root: str,
    ) -> None:
        self._db = db
        self._ai = ai_service
        self._miro = miro_service
        self._storage = StorageRepository(storage_root)
        self._sess_repo = SessionRepository(db)
        self._analysis_repo = AnalysisRepository(db)

    async def run_analysis(
        self,
        user_id: int,
        session_id: str,
        chat_id: int,
        bot: Any,
    ) -> None:
        """Run full analysis pipeline for a completed session.

        Sends "Analysis in progress" ack is sent by handle_done before calling this.
        This method delivers the final result.
        """
        try:
            # Load session with all entries eagerly to avoid lazy load in async context
            result = await self._db.execute(
                select(Session)
                .where(and_(Session.id == session_id, Session.user_id == user_id))
                .options(
                    selectinload(Session.food_entries),
                    selectinload(Session.cgm_entries),
                    selectinload(Session.activity_entries),
                )
            )
            session = result.scalar_one_or_none()
            if session is None:
                logger.error("Session %s not found for user %d", session_id, user_id)
                return

            food_entries = [
                {"telegram_file_id": e.telegram_file_id, "file_path": e.file_path}
                for e in session.food_entries
            ]
            cgm_entries = [
                {
                    "telegram_file_id": e.telegram_file_id,
                    "file_path": e.file_path,
                    "timing_label": e.timing_label,
                }
                for e in session.cgm_entries
            ]
            activity_entries = [{"description": e.description} for e in session.activity_entries]

            # Build lookup: telegram_file_id → relative file path
            _file_lookup: dict[str, str] = {
                str(e["telegram_file_id"]): str(e["file_path"]) for e in food_entries + cgm_entries
            }

            async def load_file_bytes(telegram_file_id: str) -> bytes:
                file_path = _file_lookup.get(telegram_file_id, "")
                if not file_path:
                    return b""
                try:
                    data: bytes = self._storage.load_file(file_path)
                    return data
                except (FileNotFoundError, OSError):
                    logger.warning(
                        "File not found: telegram_file_id=%s path=%s",
                        telegram_file_id,
                        file_path,
                    )
                    return b""

            try:
                result = await self._ai.analyse_session(
                    user_id=user_id,
                    food_entries=food_entries,
                    cgm_entries=cgm_entries,
                    activity_entries=activity_entries,
                    load_file_bytes=load_file_bytes,
                )
            except AnalysisError as exc:
                logger.error("Analysis failed for session %s: %s", session_id, exc)
                await bot.send_message(
                    chat_id=chat_id,
                    text=formatters.fmt_analysis_error(),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                return

            # Handle CGM unparseable (FR-011)
            if not result.get("cgm_parseable", True):
                await bot.send_message(
                    chat_id=chat_id,
                    text=formatters.fmt_cgm_unparseable(),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                return

            # Persist analysis
            activity_data = result.get("activity")
            analysis = await self._analysis_repo.save_analysis(
                user_id=user_id,
                session_id=session_id,
                nutrition=result.get("nutrition", {}),
                glucose_curve=result.get("glucose_curve", []),
                correlation=result.get("correlation", {}),
                recommendations=result.get("recommendations", []),
                within_target_notes=result.get("target_range_note"),
                raw_response=json.dumps(result),
                activity_json=json.dumps(activity_data) if activity_data is not None else None,
            )
            await self._db.commit()

            # Mark session as analysed
            await self._sess_repo.mark_analysed(user_id, session_id)
            await self._db.commit()

            # Deliver result to Telegram (SC-003: within 30s of session completion)
            await bot.send_message(
                chat_id=chat_id,
                text=formatters.fmt_analysis_result(analysis),
                parse_mode=ParseMode.MARKDOWN_V2,
            )

            # Persist MiroCard record synchronously before firing task (T046)
            miro_card: MiroCard | None = None
            if self._miro is not None:
                raw_board_id = getattr(self._miro, "board_id", None)
                miro_board_id = raw_board_id if isinstance(raw_board_id, str) else ""
                miro_card = MiroCard(
                    user_id=user_id,
                    source_type=MiroCardSourceType.ANALYSIS,
                    source_id=analysis.id,
                    miro_board_id=miro_board_id,
                    status=MiroCardStatus.PENDING,
                )
                self._db.add(miro_card)
                await self._db.commit()

            # Fire-and-forget Miro card creation (FR-009: Miro failure must not block)
            if self._miro is not None and miro_card is not None:
                asyncio.create_task(self._create_miro_card_safe(analysis, miro_card.id))

        except Exception as exc:
            logger.exception("Unexpected error in run_analysis (session=%s): %s", session_id, exc)
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=formatters.fmt_generic_error(),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
            except Exception:
                pass

    async def _create_miro_card_safe(self, analysis: Any, miro_card_id: str) -> None:
        """Call Miro API; log outcome but never raise (FR-009).

        MiroCard record was already persisted by run_analysis — this
        background task only performs the network call and logs the result.
        DB status update is best-effort to avoid racing with session lifecycle.
        """
        try:
            card_id = await self._miro.create_session_card(analysis=analysis)
            logger.info("Miro card created: %s (record=%s)", card_id, miro_card_id)
        except Exception as exc:
            logger.error(
                "Miro card creation failed (non-blocking, record=%s): %s", miro_card_id, exc
            )
