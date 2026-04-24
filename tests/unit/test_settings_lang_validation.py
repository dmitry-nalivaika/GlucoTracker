"""Unit tests for B3 fix — SupportedLanguage whitelist guard in handle_language_setting_callback.

Telegram callback data is user-controlled and can be crafted with arbitrary values.
handle_language_setting_callback must reject unsupported language codes before
persisting to the DB, matching the guard in handle_language_command.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_callback_update(data: str, user_id: int = 5001) -> MagicMock:
    mock_cq = MagicMock()
    mock_cq.data = data
    mock_cq.answer = AsyncMock()
    mock_cq.edit_message_text = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = user_id
    mock_update = MagicMock()
    mock_update.callback_query = mock_cq
    mock_update.message = None
    mock_update.effective_user = mock_user
    return mock_update


def _make_context(lang: str = "en") -> MagicMock:
    ctx = MagicMock()
    ctx.user_data = {"lang": lang}
    return ctx


class TestLanguageSettingValidation:
    """handle_language_setting_callback must validate lang against SupportedLanguage."""

    @pytest.mark.asyncio
    async def test_valid_en_is_accepted_and_persisted(self) -> None:
        """lang_set:en must be persisted — 'en' is a SupportedLanguage."""
        from glucotrack.bot.handlers import handle_language_setting_callback

        mock_update = _make_callback_update("lang_set:en")
        mock_context = _make_context("ru")

        with patch("glucotrack.bot.handlers._get_db_session") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo = AsyncMock()
            mock_repo.update_language = AsyncMock()
            with patch("glucotrack.bot.handlers.UserRepository", return_value=mock_repo):
                await handle_language_setting_callback(mock_update, mock_context)

        mock_repo.update_language.assert_awaited_once()
        assert mock_context.user_data["lang"] == "en"

    @pytest.mark.asyncio
    async def test_valid_ru_is_accepted_and_persisted(self) -> None:
        """lang_set:ru must be persisted — 'ru' is a SupportedLanguage."""
        from glucotrack.bot.handlers import handle_language_setting_callback

        mock_update = _make_callback_update("lang_set:ru")
        mock_context = _make_context("en")

        with patch("glucotrack.bot.handlers._get_db_session") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo = AsyncMock()
            mock_repo.update_language = AsyncMock()
            with patch("glucotrack.bot.handlers.UserRepository", return_value=mock_repo):
                await handle_language_setting_callback(mock_update, mock_context)

        mock_repo.update_language.assert_awaited_once()
        assert mock_context.user_data["lang"] == "ru"

    @pytest.mark.asyncio
    async def test_crafted_unsupported_lang_is_rejected(self) -> None:
        """Crafted callback 'lang_set:hax0r' must NOT be persisted to DB."""
        from glucotrack.bot.handlers import handle_language_setting_callback

        mock_update = _make_callback_update("lang_set:hax0r")
        mock_context = _make_context("en")

        with patch("glucotrack.bot.handlers._get_db_session") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo = AsyncMock()
            mock_repo.update_language = AsyncMock()
            with patch("glucotrack.bot.handlers.UserRepository", return_value=mock_repo):
                await handle_language_setting_callback(mock_update, mock_context)

        mock_repo.update_language.assert_not_awaited(), (
            "DB update_language must NOT be called for unsupported lang code"
        )
        assert (
            mock_context.user_data.get("lang") == "en"
        ), "user_data lang must NOT be changed for invalid callback data"

    @pytest.mark.asyncio
    async def test_empty_lang_code_is_rejected(self) -> None:
        """Crafted 'lang_set:' (empty lang) must NOT be persisted."""
        from glucotrack.bot.handlers import handle_language_setting_callback

        mock_update = _make_callback_update("lang_set:")
        mock_context = _make_context("en")

        with patch("glucotrack.bot.handlers._get_db_session") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_repo = AsyncMock()
            mock_repo.update_language = AsyncMock()
            with patch("glucotrack.bot.handlers.UserRepository", return_value=mock_repo):
                await handle_language_setting_callback(mock_update, mock_context)

        mock_repo.update_language.assert_not_awaited()
