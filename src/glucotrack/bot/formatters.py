"""Telegram MarkdownV2 message formatters.

All user-facing strings are defined here — no string literals in handlers.
Raw stack traces MUST NOT appear (Constitution V).
"""

from __future__ import annotations

import json
import re

from glucotrack.models.analysis import AIAnalysis


def _escape(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(r"([" + re.escape(special) + r"])", r"\\\1", str(text))


def fmt_welcome(username: str | None = None) -> str:
    name = username or "there"
    return (
        f"👋 Welcome to *GlucoTrack*, {_escape(name)}\\!\n\n"
        "I help you log meal sessions and analyse your glucose response\\.\n\n"
        "*What to do:*\n"
        "1\\. Send a food photo\n"
        "2\\. Send your CGM screenshot\\(s\\)\n"
        "3\\. Optionally describe your activity\n"
        "4\\. Type /done to get your AI analysis\n\n"
        "Type /help for full instructions\\."
    )


def fmt_photo_type_prompt() -> str:
    return "📷 Got your image\\! Is this a *food photo* or a *CGM screenshot*?"


def fmt_cgm_timing_prompt() -> str:
    return "⏱️ When was this CGM screenshot taken?\n\n" "Choose a timing or type your own label:"


def fmt_food_ack(description: str | None = None) -> str:
    note = f" \\({_escape(description)}\\)" if description else ""
    return f"✅ Food photo{note} saved to your session\\."


def fmt_cgm_ack(timing_label: str) -> str:
    return f"✅ CGM screenshot \\({_escape(timing_label)}\\) saved to your session\\."


def fmt_activity_ack(text: str) -> str:
    return f"✅ Activity logged: _{_escape(text)}_"


def fmt_session_status(food: int, cgm: int, activity: int) -> str:
    return (
        f"📋 *Current session:*\n"
        f"• Food photos: {food}\n"
        f"• CGM screenshots: {cgm}\n"
        f"• Activity entries: {activity}\n\n"
        f"Type /done when you\\'re ready to get your analysis\\."
    )


def fmt_analysis_queued() -> str:
    return "⏳ Session complete\\! *Analysis in progress\\.\\.\\.* \\(up to 30 seconds\\)"


def fmt_session_cancelled() -> str:
    return "🗑️ Session cancelled\\. Your data has been discarded\\. Use /new to start fresh\\."


def fmt_disambiguation_prompt(last_input_ago_minutes: float) -> str:
    mins = int(last_input_ago_minutes)
    return (
        f"You have an open session from *{mins} minutes ago*\\.\n\n"
        "Would you like to *continue* that session or *start a new one*?"
    )


def fmt_insufficient_entries(food: int, cgm: int) -> str:
    msg = "⚠️ Please add "
    parts = []
    if food < 1:
        parts.append("at least one *food photo*")
    if cgm < 1:
        parts.append("at least one *CGM screenshot*")
    return msg + " and ".join(_escape(p) for p in parts) + " before completing\\."


def fmt_analysis_result(analysis: AIAnalysis) -> str:
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
        "🍽️ *GlucoTrack Analysis*",
        "",
        "*Nutrition Estimate*",
        f"Carbs: {carbs}g \\| Protein: {proteins}g \\| Fat: {fats}g",
        f"Glycaemic Index estimate: \\~{gi}",
    ]
    if nutrition_notes:
        lines.append(f"_{_escape(nutrition_notes)}_")

    # Activity section (FR-010) — shown when activity_json is present
    if analysis.activity_json:
        try:
            activity = json.loads(analysis.activity_json)
            description = activity.get("description")
            modulation = activity.get("glucose_modulation", "")
            effect = activity.get("effect_summary", "")
            lines += ["", "*Activity*"]
            if description:
                lines.append(_escape(description))
            else:
                lines.append("No activity logged")
            if modulation and modulation != "No activity logged.":
                lines.append(_escape(modulation))
            if effect and effect != "No activity to analyse.":
                lines.append(_escape(effect))
        except (json.JSONDecodeError, TypeError):
            pass

    lines += ["", "*Glucose Curve*"]
    lines.extend(curve_lines or ["  _No data available_"])

    lines += ["", "*Food–Glucose Correlation*", _escape(correlation.get("summary", "N/A"))]

    lines += ["", "*Recommendations*"]
    lines.extend(rec_lines or ["  _No recommendations_"])

    if target_note:
        lines += ["", f"_{_escape(target_note)}_"]

    return "\n".join(lines)


def fmt_cgm_unparseable() -> str:
    return (
        "⚠️ I couldn't read your CGM screenshot clearly\\.\n\n"
        "Your session data is saved\\. Please send a clearer screenshot and use /done to retry\\."
    )


def fmt_analysis_error() -> str:
    return (
        "😔 Analysis failed\\. Your session data is preserved\\.\n\n"
        "Use /done to retry, or /cancel to discard the session\\."
    )


def fmt_no_session() -> str:
    return "ℹ️ You don't have an open session\\. Send a food photo or use /new to start one\\."


def fmt_trend_insufficient(current: int, required: int) -> str:
    needed = required - current
    return (
        f"📊 You need at least *{required} analysed sessions* for trend analysis\\.\n"
        f"You have *{current}* — log *{needed} more* session\\(s\\) first\\."
    )


def fmt_trend_coming_soon(session_count: int) -> str:
    return (
        f"📊 Trend analysis is coming soon\\!\n"
        f"You have *{session_count} analysed session\\(s\\)* ready\\."
    )


def fmt_generic_error() -> str:
    return "Something went wrong\\. Please try again or use /cancel to reset your session\\."


def fmt_help() -> str:
    return (
        "*GlucoTrack Help*\n\n"
        "*/start* — welcome message\n"
        "*/new* — start a new session\n"
        "*/done* — complete session and get AI analysis\n"
        "*/status* — show current session progress\n"
        "*/trend* — request trend analysis\n"
        "*/cancel* — discard current session\n"
        "*/help* — show this message\n\n"
        "📸 Send a food photo or CGM screenshot to begin logging\\."
    )
