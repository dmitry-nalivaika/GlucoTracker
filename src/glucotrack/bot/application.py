"""PTB Application factory."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler

from glucotrack.bot import formatters
from glucotrack.bot.handlers import (
    build_conversation_handler,
    handle_help,
)
from glucotrack.config import Settings

logger = logging.getLogger(__name__)


async def _broadcast_online(bot: Any) -> None:
    """Send the online message to all users with a stored chat_id (feature 004, AC2.1).

    Fire-and-forget: individual send errors are swallowed (AC2.2).
    """
    from glucotrack.db import get_session
    from glucotrack.repositories.user_repository import UserRepository, effective_lang

    try:
        async with get_session() as db:
            repo = UserRepository(db)
            users = await repo.get_all_with_chat_id()
    except Exception:
        logger.exception("_broadcast_online: failed to load users")
        return

    async def _send_one(chat_id: int, lang: str) -> None:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=formatters.fmt_bot_online(lang=lang),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except Exception:
            logger.warning("_broadcast_online: failed to send to chat_id=%d", chat_id)

    tasks = [_send_one(u.chat_id, effective_lang(u)) for u in users if u.chat_id is not None]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


class _AnalysisServiceRunner:
    """Adapts AnalysisService for use as a long-lived bot_data singleton.

    AnalysisService requires a per-request AsyncSession.  This runner
    creates a fresh session for each run_analysis call so the instance
    can be stored once in bot_data and safely invoked from background
    asyncio tasks that outlive the original handler.
    """

    def __init__(self, ai_service: Any, miro_service: Any, storage_root: str) -> None:
        self._ai = ai_service
        self._miro = miro_service
        self._storage_root = storage_root

    async def run_analysis(
        self,
        user_id: int,
        session_id: str,
        chat_id: int,
        bot: Any,
    ) -> None:
        from glucotrack.db import get_session
        from glucotrack.services.analysis_service import AnalysisService

        async with get_session() as db:
            service = AnalysisService(
                db=db,
                ai_service=self._ai,
                miro_service=self._miro,
                storage_root=self._storage_root,
            )
            await service.run_analysis(
                user_id=user_id,
                session_id=session_id,
                chat_id=chat_id,
                bot=bot,
            )


async def _expire_idle_sessions_job(context: Any) -> None:
    """PTB JobQueue callback — expires sessions idle beyond threshold (FR-012)."""
    from glucotrack.db import get_session
    from glucotrack.services.session_service import SessionService

    settings = context.application.bot_data["settings"]
    storage = context.application.bot_data["storage"]
    async with get_session() as db:
        service = SessionService(
            db=db,
            storage=storage,
            idle_threshold_minutes=settings.session_idle_threshold_minutes,
            idle_expiry_hours=settings.session_idle_expiry_hours,
        )
        count = await service.expire_idle_sessions()
        if count:
            logger.info("Expired %d idle session(s).", count)


def create_application(settings: Settings) -> Application:
    """Build and configure the PTB Application.

    Services are stored in bot_data and injected via context.
    """
    from glucotrack.services.ai_service import AIService
    from glucotrack.services.miro_service import MiroService
    from glucotrack.storage.local_storage import StorageRepository

    async def _post_init(application: Application) -> None:  # type: ignore[type-arg]
        """Broadcast online message after bot initialises (AC2.1)."""
        asyncio.create_task(_broadcast_online(application.bot))

    app = Application.builder().token(settings.telegram_bot_token).post_init(_post_init).build()

    # Singleton services
    storage = StorageRepository(settings.storage_root)
    ai_service = AIService(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        max_calls_per_user_per_day=settings.ai_max_calls_per_user_per_day,
        max_tokens_per_session=settings.ai_max_tokens_per_session,
    )
    miro_service = MiroService(
        access_token=settings.miro_access_token,
        board_id=settings.miro_board_id,
    )

    # Wire services into bot_data — handlers retrieve them via context.application.bot_data
    app.bot_data["settings"] = settings
    app.bot_data["storage"] = storage
    # _AnalysisServiceRunner creates a fresh AsyncSession per run_analysis call (FR-007–009)
    app.bot_data["analysis_service"] = _AnalysisServiceRunner(
        ai_service=ai_service,
        miro_service=miro_service,
        storage_root=settings.storage_root,
    )

    # Conversation handler (handles all multi-step flows)
    app.add_handler(build_conversation_handler())

    # Standalone handlers (outside conversation context)
    app.add_handler(CommandHandler("help", handle_help))

    # Background job: expire idle sessions every 30 minutes (FR-012)
    if app.job_queue is not None:
        app.job_queue.run_repeating(
            _expire_idle_sessions_job,
            interval=30 * 60,  # 30 minutes in seconds
            first=60,  # first run 60 seconds after startup
            name="expire_idle_sessions",
        )
        logger.info("Idle-session expiry job scheduled (every 30 min).")
    else:
        logger.warning(
            "JobQueue not available — idle session expiry (FR-012) will not run. "
            "Install python-telegram-bot[job-queue] to enable it."
        )

    logger.info("PTB Application configured with ConversationHandler and AnalysisService.")
    return app
