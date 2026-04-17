"""PTB Application factory."""
from __future__ import annotations

import logging

from telegram.ext import Application, CommandHandler

from glucotrack.bot.handlers import (
    build_conversation_handler,
    handle_help,
    handle_start,
)
from glucotrack.config import Settings

logger = logging.getLogger(__name__)


def create_application(settings: Settings) -> Application:
    """Build and configure the PTB Application.

    Services are stored in bot_data and injected via context.
    """
    from glucotrack.storage.local_storage import StorageRepository
    from glucotrack.services.session_service import SessionService

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .build()
    )

    # Wire services into bot_data — handlers retrieve them via context.application.bot_data
    storage = StorageRepository(settings.storage_root)

    # SessionService is per-request (needs DB session); stored as factory
    app.bot_data["settings"] = settings
    app.bot_data["storage"] = storage

    # Conversation handler (handles all multi-step flows)
    app.add_handler(build_conversation_handler())

    # Standalone handlers (outside conversation context)
    app.add_handler(CommandHandler("help", handle_help))

    logger.info("PTB Application configured with ConversationHandler.")
    return app
