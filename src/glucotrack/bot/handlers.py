"""Telegram bot handlers.

All handlers respond within 2 seconds (SC-002) by sending an immediate
acknowledgement before any slow I/O. Analysis is triggered as a background task.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from glucotrack.bot import formatters
from glucotrack.bot.i18n import t as _t
from glucotrack.domain.session import InsufficientEntriesError
from glucotrack.models.user import SupportedLanguage
from glucotrack.repositories.analysis_repository import InsufficientDataError
from glucotrack.repositories.user_repository import UserRepository, effective_lang

if TYPE_CHECKING:
    from glucotrack.services.session_service import SessionService

logger = logging.getLogger(__name__)

# Conversation states
(
    PHOTO_TYPE_PROMPT,
    CGM_TIMING_PROMPT,
    CGM_CUSTOM_TIMING,
    SESSION_OPEN,
    DISAMBIGUATE_SESSION,
) = range(5)

# Inline keyboard data
_FOOD = "type:food"
_CGM = "type:cgm"
_NOT_SURE = "type:unsure"
_CGM_BEFORE = "timing:before eating"
_CGM_AFTER_IMMEDIATE = "timing:right after eating"
_CGM_1H = "timing:1 hour after"
_CGM_2H = "timing:2 hours after"
_CGM_OTHER = "timing:other"
_CONTINUE_SESSION = "session:continue"
_NEW_SESSION = "session:new"


def _photo_type_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(_t("kb_food_photo", lang), callback_data=_FOOD),
                InlineKeyboardButton(_t("kb_cgm_screenshot", lang), callback_data=_CGM),
            ],
            [InlineKeyboardButton(_t("kb_not_sure", lang), callback_data=_NOT_SURE)],
        ]
    )


def _cgm_timing_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(_t("kb_before_eating", lang), callback_data=_CGM_BEFORE),
                InlineKeyboardButton(
                    _t("kb_right_after", lang), callback_data=_CGM_AFTER_IMMEDIATE
                ),
            ],
            [
                InlineKeyboardButton(_t("kb_1h_after", lang), callback_data=_CGM_1H),
                InlineKeyboardButton(_t("kb_2h_after", lang), callback_data=_CGM_2H),
            ],
            [InlineKeyboardButton(_t("kb_other_label", lang), callback_data=_CGM_OTHER)],
        ]
    )


def _disambiguate_keyboard(lang: str = "en") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[_t("kb_continue_session", lang), _t("kb_new_session", lang)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )


@asynccontextmanager
async def _get_db_session():  # type: ignore[return]
    """Yield a bare AsyncSession (for handlers that need direct DB access)."""
    from glucotrack.db import get_session

    async with get_session() as db:
        yield db


async def _resolve_lang(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Return user's language from user_data cache, falling back to DB on cold start.

    Populates user_data["lang"] so subsequent calls within the same session are instant.
    """
    lang = context.user_data.get("lang")
    if lang is not None:
        return str(lang)
    async with _get_db_session() as db:
        user_repo = UserRepository(db)  # type: ignore[arg-type]
        user = await user_repo.get_by_telegram_id(user_id)
        lang = effective_lang(user)
    context.user_data["lang"] = lang
    return lang


@asynccontextmanager
async def _session_service(
    context: ContextTypes.DEFAULT_TYPE,
) -> AsyncGenerator[SessionService, None]:
    """Async context manager yielding a per-request SessionService with its own DB session."""
    from glucotrack.db import get_session
    from glucotrack.services.session_service import SessionService

    settings = context.application.bot_data["settings"]
    storage = context.application.bot_data["storage"]

    async with get_session() as db:
        yield SessionService(
            db=db,
            storage=storage,
            idle_threshold_minutes=settings.session_idle_threshold_minutes,
            idle_expiry_hours=settings.session_idle_expiry_hours,
        )


def _get_analysis_service(context: ContextTypes.DEFAULT_TYPE):  # type: ignore[return]
    return context.application.bot_data.get("analysis_service")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start — welcome and ensure user is created."""
    assert update.effective_user and update.message
    async with _session_service(context) as service:
        try:
            await service.get_or_open_session(update.effective_user.id, force_new=False)
        except Exception:
            pass
    lang = await _resolve_lang(update.effective_user.id, context)
    await update.message.reply_text(
        formatters.fmt_welcome(update.effective_user.first_name, lang=lang),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    return SESSION_OPEN


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    assert update.effective_user and update.message
    lang = await _resolve_lang(update.effective_user.id, context)
    await update.message.reply_text(
        formatters.fmt_help(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
    )
    return SESSION_OPEN


async def handle_new_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /new — force-open a new session."""
    assert update.effective_user and update.message
    lang = await _resolve_lang(update.effective_user.id, context)
    try:
        async with _session_service(context) as service:
            await service.get_or_open_session(update.effective_user.id, force_new=True)
        await update.message.reply_text(
            _t("new_session_started", lang),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as exc:
        logger.exception("handle_new_session error: %s", exc)
        await update.message.reply_text(
            formatters.fmt_generic_error(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
        )
    return SESSION_OPEN


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming photo — prompt user to classify it."""
    assert update.effective_user and update.message

    # Store file_id in user_data for later use
    photo = update.message.photo[-1] if update.message.photo else None
    doc = update.message.document
    if photo:
        context.user_data["pending_file_id"] = photo.file_id
    elif doc:
        context.user_data["pending_file_id"] = doc.file_id
    else:
        return SESSION_OPEN

    lang = await _resolve_lang(update.effective_user.id, context)

    try:
        from glucotrack.services.session_service import IdleGapDetected

        async with _session_service(context) as service:
            try:
                await service.get_or_open_session(update.effective_user.id)
            except IdleGapDetected as idle:
                context.user_data["idle_session"] = idle.session
                await update.message.reply_text(
                    formatters.fmt_disambiguation_prompt(idle.idle_minutes, lang=lang),
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=_disambiguate_keyboard(lang),
                )
                return DISAMBIGUATE_SESSION

        await update.message.reply_text(
            formatters.fmt_photo_type_prompt(lang=lang),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=_photo_type_keyboard(lang),
        )
        return PHOTO_TYPE_PROMPT
    except Exception as exc:
        logger.exception("handle_photo error: %s", exc)
        await update.message.reply_text(
            formatters.fmt_generic_error(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
        )
        return SESSION_OPEN


async def handle_photo_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle inline keyboard choice: food / cgm / unsure."""
    assert update.callback_query and update.effective_user
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    file_id = context.user_data.get("pending_file_id", "")
    lang = await _resolve_lang(user_id, context)

    try:
        # Download photo bytes
        file = await context.bot.get_file(file_id)
        file_bytes = await file.download_as_bytearray()

        if query.data == _CGM:
            context.user_data["pending_file_bytes"] = bytes(file_bytes)
            await query.edit_message_text(
                formatters.fmt_cgm_timing_prompt(lang=lang),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=_cgm_timing_keyboard(lang),
            )
            return CGM_TIMING_PROMPT

        async with _session_service(context) as service:
            if query.data == _FOOD:
                await service.handle_photo(user_id, bytes(file_bytes), file_id, entry_type="food")
                await query.edit_message_text(
                    formatters.fmt_food_ack(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
                )
            else:  # _NOT_SURE
                await service.handle_photo(
                    user_id,
                    bytes(file_bytes),
                    file_id,
                    entry_type="food",
                    description="[unclassified — user unsure]",
                )
                await query.edit_message_text(
                    _t("image_saved_clarify", lang),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )

    except Exception as exc:
        logger.exception("handle_photo_type_callback error: %s", exc)
        await query.edit_message_text(
            formatters.fmt_generic_error(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
        )

    return SESSION_OPEN


async def handle_cgm_timing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle CGM timing selection."""
    assert update.callback_query and update.effective_user
    query = update.callback_query
    await query.answer()

    lang = await _resolve_lang(update.effective_user.id, context)

    if query.data == _CGM_OTHER:
        await query.edit_message_text(
            _t("cgm_timing_label_prompt", lang),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return CGM_CUSTOM_TIMING

    timing_label = query.data.replace("timing:", "")
    return await _save_cgm(update, context, timing_label, lang=lang)


async def handle_cgm_custom_timing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle free-text CGM timing label."""
    assert update.message and update.effective_user
    lang = await _resolve_lang(update.effective_user.id, context)
    timing_label = (update.message.text or "").strip()[:100]
    if not timing_label:
        await update.message.reply_text(
            _t("cgm_timing_label_required", lang), parse_mode=ParseMode.MARKDOWN_V2
        )
        return CGM_CUSTOM_TIMING
    return await _save_cgm(update, context, timing_label, lang=lang)


async def _save_cgm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    timing_label: str,
    lang: str = "en",
) -> int:
    """Save CGM entry and acknowledge."""
    assert update.effective_user
    user_id = update.effective_user.id
    file_bytes = context.user_data.get("pending_file_bytes", b"")
    file_id = context.user_data.get("pending_file_id", "")

    try:
        async with _session_service(context) as service:
            await service.handle_photo(
                user_id, file_bytes, file_id, entry_type="cgm", timing_label=timing_label
            )
        msg = formatters.fmt_cgm_ack(timing_label, lang=lang)
        if update.callback_query:
            await update.callback_query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN_V2)
        elif update.message:
            await update.message.reply_text(
                msg, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=ReplyKeyboardRemove()
            )
    except Exception as exc:
        logger.exception("_save_cgm error: %s", exc)
        if update.message:
            await update.message.reply_text(
                formatters.fmt_generic_error(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
            )

    return SESSION_OPEN


async def handle_activity_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle plain text messages as activity descriptions."""
    assert update.message and update.effective_user and update.message.text
    text = update.message.text.strip()

    # Ignore command-like text
    if text.startswith("/"):
        return SESSION_OPEN

    lang = await _resolve_lang(update.effective_user.id, context)

    try:
        async with _session_service(context) as service:
            await service.handle_activity(update.effective_user.id, text)
        await update.message.reply_text(
            formatters.fmt_activity_ack(text, lang=lang), parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as exc:
        logger.exception("handle_activity_text error: %s", exc)
        await update.message.reply_text(
            formatters.fmt_generic_error(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
        )
    return SESSION_OPEN


async def handle_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /done — complete session and fire background analysis."""
    assert update.effective_user and update.message
    analysis_service = _get_analysis_service(context)
    user_id = update.effective_user.id
    lang = await _resolve_lang(user_id, context)

    try:
        async with _session_service(context) as service:
            try:
                session = await service.complete_session(user_id)
            except InsufficientEntriesError:
                counts = await service.get_entry_counts(user_id)
                await update.message.reply_text(
                    formatters.fmt_insufficient_entries(counts["food"], counts["cgm"], lang=lang),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                return SESSION_OPEN
            except ValueError:
                await update.message.reply_text(
                    formatters.fmt_no_session(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
                )
                return SESSION_OPEN
    except Exception as exc:
        logger.exception("handle_done error: %s", exc)
        await update.message.reply_text(
            formatters.fmt_generic_error(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
        )
        return SESSION_OPEN

    # Immediate acknowledgement < 2s (SC-002)
    await update.message.reply_text(
        formatters.fmt_analysis_queued(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
    )

    # Fire background analysis task
    if analysis_service:
        asyncio.create_task(
            analysis_service.run_analysis(
                user_id=user_id,
                session_id=session.id,
                chat_id=update.effective_chat.id if update.effective_chat else user_id,
                bot=context.bot,
            )
        )

    return SESSION_OPEN


async def handle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /status — show current session entry counts."""
    assert update.effective_user and update.message
    lang = await _resolve_lang(update.effective_user.id, context)
    async with _session_service(context) as service:
        counts = await service.get_entry_counts(update.effective_user.id)
    await update.message.reply_text(
        formatters.fmt_session_status(counts["food"], counts["cgm"], counts["activity"], lang=lang),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    return SESSION_OPEN


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /cancel — expire the open session."""
    assert update.effective_user and update.message
    lang = await _resolve_lang(update.effective_user.id, context)
    async with _session_service(context) as service:
        session = await service._sess_repo.get_open_session(update.effective_user.id)
        if session:
            await service._sess_repo.expire_session(update.effective_user.id, session.id)
    await update.message.reply_text(
        formatters.fmt_session_cancelled(lang=lang),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def handle_trend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /trend — return trend analysis stub or insufficient-data message."""
    assert update.effective_user and update.message
    from glucotrack.repositories.session_repository import SessionRepository

    lang = await _resolve_lang(update.effective_user.id, context)

    try:
        async with _session_service(context) as service:
            sess_repo = SessionRepository(service._db)
            sessions = await sess_repo.get_analysed_sessions_for_trend(
                user_id=update.effective_user.id, min_count=3
            )
        await update.message.reply_text(
            formatters.fmt_trend_coming_soon(len(sessions), lang=lang),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except InsufficientDataError as exc:
        await update.message.reply_text(
            formatters.fmt_trend_insufficient(exc.current_count, exc.required_count, lang=lang),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except Exception as exc:
        logger.exception("handle_trend error: %s", exc)
        await update.message.reply_text(
            formatters.fmt_generic_error(lang=lang), parse_mode=ParseMode.MARKDOWN_V2
        )
    return SESSION_OPEN


async def handle_disambiguate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user's response to idle-gap disambiguation prompt (FR-013).

    NOTE: The 2-hour auto-close for unanswered disambiguation prompts (FR-013) is
    deferred to a follow-up iteration — it requires a persistent scheduler (APScheduler
    or Celery) out of scope for the MVP. Unanswered prompts are handled by the 24-hour
    idle expiry job instead. See specs/001-telegram-mvp-session-logging/spec.md and
    GitHub issue #3.
    """
    assert update.message and update.effective_user and update.message.text
    lang = await _resolve_lang(update.effective_user.id, context)
    choice = update.message.text.strip().lower()

    # Match "new" for English ("Start new session") and "нов" for Russian ("Новая сессия")
    if "new" in choice or "нов" in choice:
        async with _session_service(context) as service:
            await service.get_or_open_session(update.effective_user.id, force_new=True)
        await update.message.reply_text(
            _t("new_session_started", lang),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        # Continue — re-prompt for photo type if there's a pending file
        await update.message.reply_text(
            _t("continuing_session", lang),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )
        if context.user_data.get("pending_file_id"):
            await update.message.reply_text(
                formatters.fmt_photo_type_prompt(lang=lang),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=_photo_type_keyboard(lang),
            )
            return PHOTO_TYPE_PROMPT

    return SESSION_OPEN


async def handle_language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /language <code> — persist and apply user language preference (FR-001, FR-002)."""
    assert update.effective_user and update.message
    user_id = update.effective_user.id
    current_lang = await _resolve_lang(user_id, context)

    args = context.args or []
    if not args:
        await update.message.reply_text(
            formatters.fmt_language_usage(lang=current_lang),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return SESSION_OPEN

    requested = args[0].strip().lower()
    if requested not in {m.value for m in SupportedLanguage}:
        await update.message.reply_text(
            formatters.fmt_language_error(requested, lang=current_lang),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return SESSION_OPEN

    async with _get_db_session() as db:
        user_repo = UserRepository(db)
        await user_repo.update_language(user_id, requested)

    context.user_data["lang"] = requested
    await update.message.reply_text(
        formatters.fmt_language_changed(requested),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    return SESSION_OPEN


def build_conversation_handler() -> ConversationHandler:
    """Build and return the main ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", handle_start),
            CommandHandler("new", handle_new_session),
            CommandHandler("language", handle_language_command),
            MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_activity_text),
        ],
        states={
            SESSION_OPEN: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_photo),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_activity_text),
                CommandHandler("done", handle_done),
                CommandHandler("cancel", handle_cancel),
                CommandHandler("status", handle_status),
                CommandHandler("trend", handle_trend),
                CommandHandler("help", handle_help),
                CommandHandler("new", handle_new_session),
                CommandHandler("language", handle_language_command),
            ],
            PHOTO_TYPE_PROMPT: [
                CallbackQueryHandler(handle_photo_type_callback, pattern=r"^type:"),
            ],
            CGM_TIMING_PROMPT: [
                CallbackQueryHandler(handle_cgm_timing_callback, pattern=r"^timing:"),
            ],
            CGM_CUSTOM_TIMING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cgm_custom_timing),
            ],
            DISAMBIGUATE_SESSION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_disambiguate),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", handle_cancel),
            CommandHandler("start", handle_start),
        ],
        allow_reentry=True,
    )
