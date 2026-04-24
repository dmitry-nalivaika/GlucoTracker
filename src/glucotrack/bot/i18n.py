"""Internationalisation catalogue for GlucoTrack bot messages.

All user-visible bot strings live here — one entry per language per key.
Adding a new language requires only:
  1. A new value for each key in STRINGS
  2. A new member in SupportedLanguage (FR-009)

MarkdownV2 special characters MUST already be escaped in the string values.
"""

from __future__ import annotations

SUPPORTED: frozenset[str] = frozenset({"en", "ru"})
DEFAULT_LANG: str = "en"

# ---------------------------------------------------------------------------
# Translation catalogue
# Keys match the logical message name; values are MarkdownV2-ready templates.
# Use {placeholder} for runtime-substituted values.
# ---------------------------------------------------------------------------
STRINGS: dict[str, dict[str, str]] = {
    # /start
    "welcome": {
        "en": (
            "👋 Welcome to *GlucoTrack*, {name}\\!\n\n"
            "I help you log meal sessions and analyse your glucose response\\.\n\n"
            "*What to do:*\n"
            "1\\. Send a food photo\n"
            "2\\. Send your CGM screenshot\\(s\\)\n"
            "3\\. Optionally describe your activity\n"
            "4\\. Type /done to get your AI analysis\n\n"
            "Type /help for full instructions\\."
        ),
        "ru": (
            "👋 Добро пожаловать в *GlucoTrack*, {name}\\!\n\n"
            "Я помогу вам вести журнал приёмов пищи и анализировать реакцию глюкозы\\.\n\n"
            "*Что делать:*\n"
            "1\\. Отправьте фото еды\n"
            "2\\. Отправьте скриншот\\(ы\\) CGM\n"
            "3\\. Опционально опишите активность\n"
            "4\\. Введите /done для AI\\-анализа\n\n"
            "Введите /help для полных инструкций\\."
        ),
    },
    # Photo type prompt
    "photo_type_prompt": {
        "en": "📷 Got your image\\! Is this a *food photo* or a *CGM screenshot*?",
        "ru": "📷 Изображение получено\\! Это *фото еды* или *скриншот CGM*?",
    },
    # CGM timing prompt
    "cgm_timing_prompt": {
        "en": "⏱️ When was this CGM screenshot taken?\n\nChoose a timing or type your own label:",
        "ru": "⏱️ Когда был сделан этот скриншот CGM?\n\nВыберите время или введите свой вариант:",
    },
    # Food acknowledgement
    "food_ack": {
        "en": "✅ Food photo{note} saved to your session\\.",
        "ru": "✅ Фото еды{note} сохранено в сессию\\.",
    },
    # CGM acknowledgement
    "cgm_ack": {
        "en": "✅ CGM screenshot \\({timing}\\) saved to your session\\.",
        "ru": "✅ Скриншот CGM \\({timing}\\) сохранён в сессию\\.",
    },
    # Activity acknowledgement
    "activity_ack": {
        "en": "✅ Activity logged: _{text}_",
        "ru": "✅ Активность записана: _{text}_",
    },
    # /status
    "session_status": {
        "en": (
            "📋 *Current session:*\n"
            "• Food photos: {food}\n"
            "• CGM screenshots: {cgm}\n"
            "• Activity entries: {activity}\n\n"
            "Type /done when you\\'re ready to get your analysis\\."
        ),
        "ru": (
            "📋 *Текущая сессия:*\n"
            "• Фото еды: {food}\n"
            "• Скриншоты CGM: {cgm}\n"
            "• Записи активности: {activity}\n\n"
            "Введите /done, когда будете готовы получить анализ\\."
        ),
    },
    # Analysis queued
    "analysis_queued": {
        "en": "⏳ Session complete\\! *Analysis in progress\\.\\.\\.* \\(up to 30 seconds\\)",
        "ru": "⏳ Сессия завершена\\! *Анализ выполняется\\.\\.\\.* \\(до 30 секунд\\)",
    },
    # Session cancelled
    "session_cancelled": {
        "en": "🗑️ Session cancelled\\. Your data has been discarded\\. Use /new to start fresh\\.",
        "ru": "🗑️ Сессия отменена\\. Ваши данные удалены\\. Используйте /new для новой сессии\\.",
    },
    # Disambiguation prompt
    "disambiguation_prompt": {
        "en": (
            "You have an open session from *{mins} minutes ago*\\.\n\n"
            "Would you like to *continue* that session or *start a new one*?"
        ),
        "ru": (
            "У вас открыта сессия *{mins} минут назад*\\.\n\n"
            "Хотите *продолжить* её или *начать новую*?"
        ),
    },
    # Insufficient entries
    "insufficient_entries_prefix": {
        "en": "⚠️ Please add ",
        "ru": "⚠️ Пожалуйста, добавьте ",
    },
    "insufficient_food": {
        "en": "at least one *food photo*",
        "ru": "хотя бы одно *фото еды*",
    },
    "insufficient_cgm": {
        "en": "at least one *CGM screenshot*",
        "ru": "хотя бы один *скриншот CGM*",
    },
    "insufficient_suffix": {
        "en": " before completing\\.",
        "ru": " перед завершением\\.",
    },
    # Analysis result section headers
    "analysis_header": {
        "en": "🍽️ *GlucoTrack Analysis*",
        "ru": "🍽️ *Анализ GlucoTrack*",
    },
    "nutrition_header": {
        "en": "*Nutrition Estimate*",
        "ru": "*Оценка питания*",
    },
    "activity_header": {
        "en": "*Activity*",
        "ru": "*Активность*",
    },
    "no_activity": {
        "en": "No activity logged",
        "ru": "Активность не записана",
    },
    "glucose_curve_header": {
        "en": "*Glucose Curve*",
        "ru": "*Кривая глюкозы*",
    },
    "no_glucose_data": {
        "en": "  _No data available_",
        "ru": "  _Нет данных_",
    },
    "correlation_header": {
        "en": "*Food\\–Glucose Correlation*",
        "ru": "*Корреляция еда\\–глюкоза*",
    },
    "recommendations_header": {
        "en": "*Recommendations*",
        "ru": "*Рекомендации*",
    },
    "no_recommendations": {
        "en": "  _No recommendations_",
        "ru": "  _Нет рекомендаций_",
    },
    # CGM unparseable
    "cgm_unparseable": {
        "en": (
            "⚠️ I couldn't read your CGM screenshot clearly\\.\n\n"
            "Your session data is saved\\. Please send a clearer screenshot "
            "and use /done to retry\\."
        ),
        "ru": (
            "⚠️ Не удалось чётко прочитать скриншот CGM\\.\n\n"
            "Данные сессии сохранены\\. Пожалуйста, отправьте более чёткий скриншот "
            "и используйте /done\\."
        ),
    },
    # Analysis error
    "analysis_error": {
        "en": (
            "😔 Analysis failed\\. Your session data is preserved\\.\n\n"
            "Use /done to retry, or /cancel to discard the session\\."
        ),
        "ru": (
            "😔 Анализ не выполнен\\. Данные сессии сохранены\\.\n\n"
            "Используйте /done для повтора или /cancel для отмены сессии\\."
        ),
    },
    # No session
    "no_session": {
        "en": "ℹ️ You don't have an open session\\. Send a food photo or use /new to start one\\.",
        "ru": "ℹ️ У вас нет открытой сессии\\. Отправьте фото еды или используйте /new\\.",
    },
    # Trend insufficient
    "trend_insufficient": {
        "en": (
            "📊 You need at least *{required} analysed sessions* for trend analysis\\.\n"
            "You have *{current}* — log *{needed} more* session\\(s\\) first\\."
        ),
        "ru": (
            "📊 Для анализа тенденций нужно не менее *{required} проанализированных сессий*\\.\n"
            "У вас *{current}* — зарегистрируйте ещё *{needed}* сессию\\(й\\)\\."
        ),
    },
    # Trend coming soon
    "trend_coming_soon": {
        "en": (
            "📊 Trend analysis is coming soon\\!\n"
            "You have *{session_count} analysed session\\(s\\)* ready\\."
        ),
        "ru": (
            "📊 Анализ тенденций скоро будет доступен\\!\n"
            "У вас *{session_count} проанализированных сессий*\\."
        ),
    },
    # Generic error
    "generic_error": {
        "en": "Something went wrong\\. Please try again or use /cancel to reset your session\\.",
        "ru": (
            "Что\\-то пошло не так\\. Попробуйте ещё раз "
            "или используйте /cancel для сброса сессии\\."
        ),
    },
    # /help
    "help": {
        "en": (
            "*GlucoTrack Help*\n\n"
            "*/start* — welcome message\n"
            "*/new* — start a new session\n"
            "*/done* — complete session and get AI analysis\n"
            "*/status* — show current session progress\n"
            "*/trend* — request trend analysis\n"
            "*/cancel* — discard current session\n"
            "*/language* — change output language\n"
            "*/help* — show this message\n\n"
            "📸 Send a food photo or CGM screenshot to begin logging\\."
        ),
        "ru": (
            "*Справка GlucoTrack*\n\n"
            "*/start* — приветственное сообщение\n"
            "*/new* — начать новую сессию\n"
            "*/done* — завершить сессию и получить AI\\-анализ\n"
            "*/status* — показать прогресс текущей сессии\n"
            "*/trend* — запросить анализ тенденций\n"
            "*/cancel* — отменить текущую сессию\n"
            "*/language* — изменить язык вывода\n"
            "*/help* — показать это сообщение\n\n"
            "📸 Отправьте фото еды или скриншот CGM, чтобы начать запись\\."
        ),
    },
    # /language command responses
    "language_changed": {
        "en": "✅ Language changed to: *English*",
        "ru": "✅ Язык изменён на: *Русский*",
    },
    "language_error": {
        "en": (
            "⚠️ Unsupported language code: `{code}`\n"
            "Supported languages: `en` \\(English\\), `ru` \\(Русский\\)\n"
            "Usage: `/language <code>`"
        ),
        "ru": (
            "⚠️ Неподдерживаемый код языка: `{code}`\n"
            "Поддерживаемые языки: `en` \\(English\\), `ru` \\(Русский\\)\n"
            "Использование: `/language <code>`"
        ),
    },
    "language_usage": {
        "en": (
            "⚠️ Please specify a language code\\.\n"
            "Supported languages: `en` \\(English\\), `ru` \\(Русский\\)\n"
            "Usage: `/language <code>`"
        ),
        "ru": (
            "⚠️ Пожалуйста, укажите код языка\\.\n"
            "Поддерживаемые языки: `en` \\(English\\), `ru` \\(Русский\\)\n"
            "Использование: `/language <code>`"
        ),
    },
    # Miro section headers (used in miro_service.py)
    "miro_food_header": {
        "en": "**Food**",
        "ru": "**Питание**",
    },
    "miro_activity_header": {
        "en": "**Activity**",
        "ru": "**Активность**",
    },
    "miro_glucose_header": {
        "en": "**Glucose Curve**",
        "ru": "**Кривая глюкозы**",
    },
    "miro_correlation_header": {
        "en": "**Correlation**",
        "ru": "**Корреляция**",
    },
    "miro_recommendations_header": {
        "en": "**Recommendations**",
        "ru": "**Рекомендации**",
    },
    # Miro fallback / empty-state strings (plain text, no MarkdownV2 escaping needed)
    "miro_no_activity": {
        "en": "No activity logged",
        "ru": "Активность не записана",
    },
    "miro_no_recommendations": {
        "en": "No specific recommendations for this session.",
        "ru": "Рекомендации для этой сессии не сгенерированы.",
    },
    "miro_cgm_unreadable": {
        "en": "⚠️ CGM unreadable: {err}. Please re-submit a clearer screenshot.",
        "ru": "⚠️ CGM нечитаем: {err}. Отправьте более чёткий скриншот.",
    },
    # Guided conversational flow next-step hints (feature 004)
    "food_ack_next_step": {
        "en": " Send another food photo, a CGM screenshot, or tap /done when ready\\.",
        "ru": " Отправьте ещё фото еды, скриншот CGM или нажмите /done\\.",
    },
    "cgm_ack_next_step": {
        "en": " Add another CGM screenshot, describe your activity, or tap /done\\.",
        "ru": " Добавьте ещё скриншот CGM, опишите активность или нажмите /done\\.",
    },
    "activity_ack_next_step": {
        "en": " Add more photos if needed, or tap /done for your analysis\\.",
        "ru": " При необходимости добавьте фото, или нажмите /done для анализа\\.",
    },
    "session_start_prompt": {
        "en": "📷 Send me a *food photo* to start logging your meal\\.",
        "ru": "📷 Отправьте *фото еды*, чтобы начать запись приёма пищи\\.",
    },
    # Bot online / offline broadcast messages (feature 004)
    "bot_online": {
        "en": "🟢 *GlucoTrack* is online and ready\\! Send /new to start a session\\.",
        "ru": "🟢 *GlucoTrack* онлайн и готов к работе\\! Отправьте /new для новой сессии\\.",
    },
    "bot_offline": {
        "en": "⏸️ *GlucoTrack* is going offline briefly\\. Sessions are preserved\\.",
        "ru": "⏸️ *GlucoTrack* временно недоступен\\. Ваши данные сохранены\\.",
    },
    # Miro executive summary / encouragement section headers (feature 004)
    "miro_summary_header": {
        "en": "**Session Summary**",
        "ru": "**Итоги сессии**",
    },
    "miro_summary_unavailable": {
        "en": "Summary not available for this session.",
        "ru": "Итог недоступен для этой сессии.",
    },
    "miro_encouragement_unavailable": {
        "en": "Keep up the great work tracking your glucose!",
        "ru": "Продолжайте вести мониторинг глюкозы — вы молодец!",
    },
    # Inline keyboard button labels
    "kb_food_photo": {"en": "🍽️ Food photo", "ru": "🍽️ Фото еды"},
    "kb_cgm_screenshot": {"en": "📈 CGM screenshot", "ru": "📈 Скриншот CGM"},
    "kb_not_sure": {"en": "🤷 Not sure", "ru": "🤷 Не уверен"},
    "kb_before_eating": {"en": "Before eating", "ru": "До еды"},
    "kb_right_after": {"en": "Right after", "ru": "Сразу после"},
    "kb_1h_after": {"en": "1 hour after", "ru": "Через 1 час"},
    "kb_2h_after": {"en": "2 hours after", "ru": "Через 2 часа"},
    "kb_other_label": {"en": "Other (type label)", "ru": "Другое (введите)"},
    # Flat CGM button labels (shown in combined food/CGM keyboard, feature 004)
    "kb_cgm_flat_before": {"en": "📈 CGM · before", "ru": "📈 CGM · до еды"},
    "kb_cgm_flat_after": {"en": "📈 CGM · right after", "ru": "📈 CGM · сразу после"},
    "kb_cgm_flat_1h": {"en": "📈 CGM · 1h after", "ru": "📈 CGM · через 1ч"},
    "kb_cgm_flat_2h": {"en": "📈 CGM · 2h after", "ru": "📈 CGM · через 2ч"},
    "kb_continue_session": {"en": "Continue session", "ru": "Продолжить сессию"},
    "kb_new_session": {"en": "Start new session", "ru": "Новая сессия"},
    # Hardcoded handler messages (MarkdownV2-escaped)
    "new_session_started": {
        "en": "✅ New session started\\. Send a food photo to begin\\.",
        "ru": "✅ Новая сессия начата\\. Отправьте фото еды, чтобы начать\\.",
    },
    "image_saved_clarify": {
        "en": "✅ Image saved\\. You can clarify its type when you use /done\\.",
        "ru": "✅ Изображение сохранено\\. Уточните тип при использовании /done\\.",
    },
    "continuing_session": {
        "en": "✅ Continuing your existing session\\.",
        "ru": "✅ Продолжаем текущую сессию\\.",
    },
    "cgm_timing_label_prompt": {
        "en": "Type your timing label \\(e\\.g\\. _3 hours after_, _fasting_\\):",
        "ru": "Введите метку времени \\(напр\\. _через 3 часа_, _натощак_\\):",
    },
    "cgm_timing_label_required": {
        "en": "Please provide a timing label\\.",
        "ru": "Пожалуйста, укажите метку времени\\.",
    },
    # Settings panel (feature 004)
    "settings_prompt": {
        "en": "⚙️ *Settings*\n\nChoose a language for bot messages:",
        "ru": "⚙️ *Настройки*\n\nВыберите язык сообщений бота:",
    },
    "kb_lang_en": {"en": "🇺🇸 English", "ru": "🇺🇸 English"},
    "kb_lang_ru": {"en": "🇷🇺 Русский", "ru": "🇷🇺 Русский"},
    "language_set": {
        "en": "✅ Language set to *English*\\.",
        "ru": "✅ Язык изменён на *Русский*\\.",
    },
}


def t(key: str, lang: str, **kwargs: object) -> str:
    """Translate *key* to *lang*, falling back to DEFAULT_LANG.

    Raises KeyError if the key does not exist in the catalogue.
    """
    locale = lang if lang in SUPPORTED else DEFAULT_LANG
    template = STRINGS[key][locale]
    return template.format(**kwargs) if kwargs else template
