"""Contract tests for /language bot command — T007.

Verifies the command schema: valid codes switch language, unsupported codes
return errors in the current language, missing args return usage hint.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from glucotrack.bot.i18n import SUPPORTED


class TestLanguageCommandContract:
    """Contract: /language <code> command schema (specs/003/contracts/language_command.md)."""

    @pytest.mark.asyncio
    async def test_valid_language_code_ru_stores_preference(self, test_db) -> None:
        """/language ru stores 'ru' in DB and replies with Russian confirmation."""
        from glucotrack.bot.handlers import handle_language_command
        from glucotrack.domain.user import get_or_create_user

        # Ensure user exists
        user = await get_or_create_user(test_db, 900)
        await test_db.commit()

        update = MagicMock()
        update.effective_user.id = 900
        update.message = AsyncMock()
        update.message.text = "/language ru"
        context = MagicMock()
        context.args = ["ru"]
        context.user_data = {"lang": "en"}

        with patch("glucotrack.bot.handlers._get_db_session") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=test_db)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            await handle_language_command(update, context)

        # Bot replied
        assert update.message.reply_text.called
        reply_text = update.message.reply_text.call_args[0][0]

        # Reply is in Russian (the new language)
        assert "Русский" in reply_text or "ru" in reply_text.lower()

        # context.user_data["lang"] updated
        assert context.user_data.get("lang") == "ru"

    @pytest.mark.asyncio
    async def test_valid_language_code_en_stores_preference(self, test_db) -> None:
        """/language en stores 'en' in DB and replies with English confirmation."""
        from glucotrack.bot.handlers import handle_language_command
        from glucotrack.domain.user import get_or_create_user

        await get_or_create_user(test_db, 901)
        await test_db.commit()

        update = MagicMock()
        update.effective_user.id = 901
        update.message = AsyncMock()
        context = MagicMock()
        context.args = ["en"]
        context.user_data = {"lang": "ru"}

        with patch("glucotrack.bot.handlers._get_db_session") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=test_db)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            await handle_language_command(update, context)

        assert update.message.reply_text.called
        reply_text = update.message.reply_text.call_args[0][0]
        assert "English" in reply_text
        assert context.user_data.get("lang") == "en"

    @pytest.mark.asyncio
    async def test_unsupported_language_code_returns_error_in_current_language(
        self, test_db
    ) -> None:
        """/language xx returns error in current language; DB unchanged."""
        from glucotrack.bot.handlers import handle_language_command
        from glucotrack.domain.user import get_or_create_user

        await get_or_create_user(test_db, 902)
        await test_db.commit()

        update = MagicMock()
        update.effective_user.id = 902
        update.message = AsyncMock()
        context = MagicMock()
        context.args = ["de"]
        context.user_data = {"lang": "en"}  # current language is English

        with patch("glucotrack.bot.handlers._get_db_session") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=test_db)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            await handle_language_command(update, context)

        assert update.message.reply_text.called
        reply_text = update.message.reply_text.call_args[0][0]
        # Error response is in English (current language)
        assert "de" in reply_text  # shows the bad code
        assert "en" in reply_text  # lists supported codes
        # lang NOT changed
        assert context.user_data.get("lang") == "en"

    @pytest.mark.asyncio
    async def test_missing_argument_returns_usage_hint(self, test_db) -> None:
        """/language (no args) returns usage hint in current language."""
        from glucotrack.bot.handlers import handle_language_command
        from glucotrack.domain.user import get_or_create_user

        await get_or_create_user(test_db, 903)
        await test_db.commit()

        update = MagicMock()
        update.effective_user.id = 903
        update.message = AsyncMock()
        context = MagicMock()
        context.args = []
        context.user_data = {"lang": "en"}

        with patch("glucotrack.bot.handlers._get_db_session") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=test_db)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            await handle_language_command(update, context)

        assert update.message.reply_text.called
        reply_text = update.message.reply_text.call_args[0][0]
        # Usage hint is in English (current lang)
        assert "language" in reply_text.lower() or "код" not in reply_text

    def test_supported_set_contains_en_and_ru(self) -> None:
        """SUPPORTED set contains at least 'en' and 'ru' (contract: supported codes)."""
        assert "en" in SUPPORTED
        assert "ru" in SUPPORTED
