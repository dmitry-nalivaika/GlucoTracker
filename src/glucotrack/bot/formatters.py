"""Telegram MarkdownV2 message formatters.

All user-facing strings are defined here — no string literals in handlers.
Raw stack traces MUST NOT appear (Constitution V).

Every public fmt_* function accepts an optional `lang: str = "en"` keyword
argument. Pass the user's stored language code to localise the message.
"""

from __future__ import annotations

import json
import re

from glucotrack.bot import i18n
from glucotrack.models.analysis import AIAnalysis


def _escape(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(r"([" + re.escape(special) + r"])", r"\\\1", str(text))


def fmt_welcome(username: str | None = None, *, lang: str = "en") -> str:
    name = _escape(username or "there")
    return i18n.t("welcome", lang, name=name)


def fmt_photo_type_prompt(*, lang: str = "en") -> str:
    return i18n.t("photo_type_prompt", lang)


def fmt_cgm_timing_prompt(*, lang: str = "en") -> str:
    return i18n.t("cgm_timing_prompt", lang)


def fmt_food_ack(description: str | None = None, *, lang: str = "en", guided: bool = False) -> str:
    note = f" \\({_escape(description)}\\)" if description else ""
    msg = i18n.t("food_ack", lang, note=note)
    if guided:
        msg += i18n.t("food_ack_next_step", lang)
    return msg


def fmt_cgm_ack(timing_label: str, *, lang: str = "en", guided: bool = False) -> str:
    msg = i18n.t("cgm_ack", lang, timing=_escape(timing_label))
    if guided:
        msg += i18n.t("cgm_ack_next_step", lang)
    return msg


def fmt_activity_ack(text: str, *, lang: str = "en", guided: bool = False) -> str:
    msg = i18n.t("activity_ack", lang, text=_escape(text))
    if guided:
        msg += i18n.t("activity_ack_next_step", lang)
    return msg


def fmt_session_start_prompt(*, lang: str = "en") -> str:
    """Guided prompt telling user to send a food photo after session starts."""
    return i18n.t("session_start_prompt", lang)


def fmt_bot_online(*, lang: str = "en") -> str:
    """Broadcast message when bot comes online."""
    return i18n.t("bot_online", lang)


def fmt_bot_offline(*, lang: str = "en") -> str:
    """Broadcast message when bot goes offline."""
    return i18n.t("bot_offline", lang)


def fmt_session_status(food: int, cgm: int, activity: int, *, lang: str = "en") -> str:
    return i18n.t("session_status", lang, food=food, cgm=cgm, activity=activity)


def fmt_analysis_queued(*, lang: str = "en") -> str:
    return i18n.t("analysis_queued", lang)


def fmt_session_cancelled(*, lang: str = "en") -> str:
    return i18n.t("session_cancelled", lang)


def fmt_disambiguation_prompt(last_input_ago_minutes: float, *, lang: str = "en") -> str:
    mins = int(last_input_ago_minutes)
    return i18n.t("disambiguation_prompt", lang, mins=mins)


def fmt_insufficient_entries(food: int, cgm: int, *, lang: str = "en") -> str:
    prefix = i18n.t("insufficient_entries_prefix", lang)
    suffix = i18n.t("insufficient_suffix", lang)
    parts = []
    if food < 1:
        parts.append(i18n.t("insufficient_food", lang))
    if cgm < 1:
        parts.append(i18n.t("insufficient_cgm", lang))
    connector = " and " if lang == "en" else " и "
    return prefix + connector.join(_escape(p) for p in parts) + suffix


def fmt_analysis_result(analysis: AIAnalysis, *, lang: str = "en") -> str:
    """Format a structured analysis message for Telegram MarkdownV2."""
    nutrition = json.loads(analysis.nutrition_json)
    glucose_curve = json.loads(analysis.glucose_curve_json)
    correlation = json.loads(analysis.correlation_json)
    recommendations = json.loads(analysis.recommendations_json)
    target_note = analysis.within_target_notes or ""

    carbs = nutrition.get("carbs_g", "?")
    proteins = nutrition.get("proteins_g", "?")
    fats = nutrition.get("fats_g", "?")
    gi = nutrition.get("gi_estimate", "?")
    nutrition_notes = nutrition.get("notes", "")

    # Glucose curve bullets
    curve_lines = []
    for point in glucose_curve:
        label = _escape(point.get("timing_label", "?"))
        value = point.get("estimated_value_mg_dl", "?")
        in_range = point.get("in_range")
        indicator = "✅" if in_range is True else ("⚠️" if in_range is False else "")
        curve_lines.append(f"  • {label}: {value} mg/dL {indicator}")

    # Recommendations numbered list
    rec_lines = []
    sorted_recs = sorted(recommendations, key=lambda r: r.get("priority", 99))
    for i, rec in enumerate(sorted_recs, 1):
        rec_lines.append(f"{i}\\. {_escape(rec.get('text', ''))}")

    lines = [
        i18n.t("analysis_header", lang),
        "",
        i18n.t("nutrition_header", lang),
        f"Carbs: {carbs}g \\| Protein: {proteins}g \\| Fat: {fats}g",
        f"Glycaemic Index estimate: \\~{gi}",
    ]
    if nutrition_notes:
        lines.append(f"_{_escape(nutrition_notes)}_")

    # Activity section — shown when activity_json is present
    if analysis.activity_json:
        try:
            activity = json.loads(analysis.activity_json)
            description = activity.get("description")
            modulation = activity.get("glucose_modulation", "")
            effect = activity.get("effect_summary", "")
            lines += ["", i18n.t("activity_header", lang)]
            if description:
                lines.append(_escape(description))
            else:
                lines.append(i18n.t("no_activity", lang))
            if modulation and modulation != "No activity logged.":
                lines.append(_escape(modulation))
            if effect and effect != "No activity to analyse.":
                lines.append(_escape(effect))
        except (json.JSONDecodeError, TypeError):
            pass

    lines += ["", i18n.t("glucose_curve_header", lang)]
    lines.extend(curve_lines or [i18n.t("no_glucose_data", lang)])

    lines += ["", i18n.t("correlation_header", lang), _escape(correlation.get("summary", "N/A"))]

    lines += ["", i18n.t("recommendations_header", lang)]
    lines.extend(rec_lines or [i18n.t("no_recommendations", lang)])

    if target_note:
        lines += ["", f"_{_escape(target_note)}_"]

    return "\n".join(lines)


def fmt_cgm_unparseable(*, lang: str = "en") -> str:
    return i18n.t("cgm_unparseable", lang)


def fmt_analysis_error(*, lang: str = "en") -> str:
    return i18n.t("analysis_error", lang)


def fmt_no_session(*, lang: str = "en") -> str:
    return i18n.t("no_session", lang)


def fmt_trend_insufficient(current: int, required: int, *, lang: str = "en") -> str:
    needed = required - current
    return i18n.t("trend_insufficient", lang, current=current, required=required, needed=needed)


def fmt_trend_coming_soon(session_count: int, *, lang: str = "en") -> str:
    return i18n.t("trend_coming_soon", lang, session_count=session_count)


def fmt_generic_error(*, lang: str = "en") -> str:
    return i18n.t("generic_error", lang)


def fmt_help(*, lang: str = "en") -> str:
    return i18n.t("help", lang)


def fmt_language_changed(lang: str = "en") -> str:
    """Confirmation message after a successful /language command."""
    return i18n.t("language_changed", lang)


def fmt_language_error(unsupported_code: str, *, lang: str = "en") -> str:
    """Error response for an unsupported language code."""
    return i18n.t("language_error", lang, code=_escape(unsupported_code))


def fmt_language_usage(*, lang: str = "en") -> str:
    """Usage hint when /language is called with no argument."""
    return i18n.t("language_usage", lang)
