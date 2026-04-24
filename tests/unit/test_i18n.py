"""Unit tests for i18n catalogue and t() helper — T006."""

from __future__ import annotations

import pytest

from glucotrack.bot.i18n import DEFAULT_LANG, STRINGS, SUPPORTED, t


class TestTHelper:
    """Tests for the t(key, lang, **kwargs) translation helper."""

    def test_english_key_lookup(self) -> None:
        """t() returns English value for lang='en'."""
        result = t("language_changed", "en")
        assert "English" in result

    def test_russian_key_lookup(self) -> None:
        """t() returns Russian value for lang='ru'."""
        result = t("language_changed", "ru")
        assert "Русский" in result

    def test_fallback_to_default_lang_for_unknown_code(self) -> None:
        """t() falls back to DEFAULT_LANG ('en') for unsupported lang codes."""
        result = t("language_changed", "de")
        assert result == t("language_changed", DEFAULT_LANG)

    def test_format_kwargs_applied(self) -> None:
        """t() applies format kwargs to the translated template."""
        result = t("welcome", "en", name="Alice")
        assert "Alice" in result

    def test_format_kwargs_applied_russian(self) -> None:
        """t() applies format kwargs in Russian locale."""
        result = t("welcome", "ru", name="Алиса")
        assert "Алиса" in result

    def test_missing_key_raises_key_error(self) -> None:
        """t() raises KeyError for a key not in STRINGS."""
        with pytest.raises(KeyError):
            t("nonexistent_key_xyz", "en")

    def test_no_kwargs_returns_template_unchanged(self) -> None:
        """t() without kwargs returns the raw template (no format call)."""
        result = t("generic_error", "en")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_all_keys_have_english_and_russian(self) -> None:
        """Every key in STRINGS has both 'en' and 'ru' entries."""
        for key, translations in STRINGS.items():
            assert "en" in translations, f"Key '{key}' missing 'en' translation"
            assert "ru" in translations, f"Key '{key}' missing 'ru' translation"

    def test_supported_contains_en_and_ru(self) -> None:
        """SUPPORTED frozenset contains at least 'en' and 'ru'."""
        assert "en" in SUPPORTED
        assert "ru" in SUPPORTED

    def test_default_lang_is_en(self) -> None:
        """DEFAULT_LANG is 'en'."""
        assert DEFAULT_LANG == "en"
