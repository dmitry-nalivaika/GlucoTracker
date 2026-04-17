"""Unit tests for glucotrack.config — T019."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from glucotrack.config import Settings


class TestSettings:
    """Tests for Settings pydantic model."""

    def _base_env(self) -> dict[str, str]:
        # pydantic-settings v2: direct init kwargs use field names (lowercase)
        return {
            "telegram_bot_token": "test_token",
            "anthropic_api_key": "test_key",
            "miro_access_token": "test_miro",
            "miro_board_id": "test_board",
        }

    def test_all_required_fields_load(self) -> None:
        s = Settings(**self._base_env())  # type: ignore[arg-type]
        assert s.telegram_bot_token == "test_token"
        assert s.anthropic_api_key == "test_key"
        assert s.miro_access_token == "test_miro"
        assert s.miro_board_id == "test_board"

    def test_defaults_are_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Isolate from shell env so default values are exercised
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        monkeypatch.delenv("STORAGE_ROOT", raising=False)
        monkeypatch.delenv("SESSION_IDLE_THRESHOLD_MINUTES", raising=False)
        monkeypatch.delenv("SESSION_IDLE_EXPIRY_HOURS", raising=False)
        monkeypatch.delenv("SESSION_DISAMBIGUATE_TIMEOUT_HOURS", raising=False)
        s = Settings(**self._base_env())  # type: ignore[arg-type]
        assert s.anthropic_model == "claude-3-5-sonnet-20241022"
        assert s.storage_root == "./data"
        assert s.session_idle_threshold_minutes == 30
        assert s.session_idle_expiry_hours == 24
        assert s.session_disambiguate_timeout_hours == 2
        assert isinstance(s.ai_max_calls_per_user_per_day, int)
        assert isinstance(s.ai_max_tokens_per_session, int)

    def test_missing_telegram_token_raises(self) -> None:
        env = self._base_env()
        del env["telegram_bot_token"]
        with pytest.raises(ValidationError):
            Settings(**env)  # type: ignore[arg-type]

    def test_missing_anthropic_key_raises(self) -> None:
        env = self._base_env()
        del env["anthropic_api_key"]
        with pytest.raises(ValidationError):
            Settings(**env)  # type: ignore[arg-type]

    def test_missing_miro_token_raises(self) -> None:
        env = self._base_env()
        del env["miro_access_token"]
        with pytest.raises(ValidationError):
            Settings(**env)  # type: ignore[arg-type]

    def test_missing_miro_board_raises(self) -> None:
        env = self._base_env()
        del env["miro_board_id"]
        with pytest.raises(ValidationError):
            Settings(**env)  # type: ignore[arg-type]

    def test_empty_telegram_token_raises(self) -> None:
        env = {**self._base_env(), "telegram_bot_token": ""}
        with pytest.raises(ValidationError):
            Settings(**env)  # type: ignore[arg-type]

    def test_empty_anthropic_key_raises(self) -> None:
        env = {**self._base_env(), "anthropic_api_key": ""}
        with pytest.raises(ValidationError):
            Settings(**env)  # type: ignore[arg-type]

    def test_custom_model_overrides_default(self) -> None:
        env = {**self._base_env(), "anthropic_model": "claude-3-opus-20240229"}
        s = Settings(**env)  # type: ignore[arg-type]
        assert s.anthropic_model == "claude-3-opus-20240229"

    def test_custom_rate_limits(self) -> None:
        env = {
            **self._base_env(),
            "ai_max_calls_per_user_per_day": 5,
            "ai_max_tokens_per_session": 2000,
        }
        s = Settings(**env)  # type: ignore[arg-type]
        assert s.ai_max_calls_per_user_per_day == 5
        assert s.ai_max_tokens_per_session == 2000
