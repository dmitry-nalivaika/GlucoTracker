# Extending the AI Analysis Pipeline

GlucoTrack's AI pipeline is isolated in `AIService` and orchestrated by `AnalysisService`. This guide explains how to add new data sources (e.g. wearable heart-rate data), new prompt sections (e.g. sleep quality analysis), or swap the underlying LLM provider.

## How the current pipeline works

```
AnalysisService.run_analysis()
  └─ builds food_entries, cgm_entries, activity_entries lists
  └─ builds load_file_bytes() closure  ← reads files from StorageRepository
  └─ AIService.analyse_session(
         user_id, food_entries, cgm_entries, activity_entries, load_file_bytes
     )
       └─ Anthropic Claude API  ← vision + text messages
       └─ returns structured JSON dict
  └─ persists AIAnalysis row
  └─ delivers Telegram message via formatters.fmt_analysis_result()
```

The JSON contract between `AIService` and `AnalysisService` is defined by `SESSION_ANALYSIS_SYSTEM_PROMPT` in `src/glucotrack/services/ai_service.py` and validated by `tests/contract/test_claude_api_schema.py`.

## Adding a new data source (e.g. heart-rate data)

### 1. Add the model

Add a new ORM model in `src/glucotrack/models/`, e.g. `HeartRateEntry`, mirroring `FoodEntry` / `CGMEntry`. Follow the pattern in `models/entries.py` — include `user_id`, `session_id`, and `created_at`.

### 2. Add the repository method

In `src/glucotrack/repositories/session_repository.py`, add:

```python
async def add_heart_rate_entry(
    self, user_id: int, session_id: str, bpm: int, recorded_at: datetime
) -> HeartRateEntry:
    await self._verify_session_ownership(user_id, session_id)
    entry = HeartRateEntry(session_id=session_id, user_id=user_id, bpm=bpm, recorded_at=recorded_at)
    self._db.add(entry)
    await self._db.flush()
    return entry
```

All repository methods **must** include `user_id` in the WHERE clause (Constitution II).

### 3. Add a Telegram handler for the new input

Add a handler in `src/glucotrack/bot/handlers.py` that captures the new data type from the user and calls the new repository method via `SessionService`. Update `build_conversation_handler()` to add the new state/entry point.

### 4. Pass the new data to AIService

In `AnalysisService.run_analysis()`, load the new entries alongside existing ones and pass them to `AIService.analyse_session`:

```python
heart_rate_entries = [
    {"bpm": e.bpm, "recorded_at": e.recorded_at.isoformat()}
    for e in session.heart_rate_entries
]

result = await self._ai.analyse_session(
    user_id=user_id,
    food_entries=food_entries,
    cgm_entries=cgm_entries,
    activity_entries=activity_entries,
    heart_rate_entries=heart_rate_entries,   # new
    load_file_bytes=load_file_bytes,
)
```

Remember to eager-load the new relationship in the `selectinload` chain.

### 5. Update the AIService prompt and schema

In `src/glucotrack/services/ai_service.py`:

1. Update `SESSION_ANALYSIS_SYSTEM_PROMPT` to include a `heart_rate` section in the JSON schema.
2. Pass the new entries as a user message to `analyse_session`.
3. Update the response parsing to extract the new section.

Update `tests/contract/test_claude_api_schema.py` to assert the new field is present in valid responses.

## Adding a new output section to the analysis message

### 1. Add a field to AIAnalysis model

In `src/glucotrack/models/analysis.py`, add a new column, e.g.:

```python
heart_rate_json: Mapped[str] = mapped_column(Text, nullable=True)
```

### 2. Update AnalysisRepository.save_analysis

Add the new field to `save_analysis()` in `src/glucotrack/repositories/analysis_repository.py`.

### 3. Update the formatter

In `src/glucotrack/bot/formatters.py`, add a new section to `fmt_analysis_result()`.  The function receives the persisted `AIAnalysis` ORM object — access the new column and format it.

### 4. Update the system prompt

Extend `SESSION_ANALYSIS_SYSTEM_PROMPT` to request the new section in the JSON response. Keep the JSON contract in sync with the contract test.

## Swapping the LLM provider

`AIService` is the only class that imports `anthropic`. To use a different provider:

1. Create `src/glucotrack/services/openai_ai_service.py` (or similar) with the same public interface:

   ```python
   class OpenAIAIService:
       async def analyse_session(
           self,
           user_id: int,
           food_entries: list[dict],
           cgm_entries: list[dict],
           activity_entries: list[dict],
           load_file_bytes: Callable,
       ) -> dict: ...
   ```

2. Wire the new service in `src/glucotrack/bot/application.py` in place of `AIService`.

3. Write contract tests for the new provider's response schema.

`AnalysisService` accepts `ai_service: Any` and calls `ai_service.analyse_session(...)` — it is provider-agnostic by design.

## Cost guard (Constitution VII)

Any new data source that calls the Claude API must:
- Respect the existing `ai_max_calls_per_user_per_day` rate limit in `AIService._check_rate_limit`
- Respect the `ai_max_tokens_per_session` budget
- Not add new Claude API call sites outside `AIService`

If you add a new AI call type (e.g. a dedicated heart-rate analysis call), add it to `AIService` and include it in the rate-limit counter.

## What you do NOT need to change

- `SessionService` (session lifecycle is data-source agnostic)
- `MiroService` / `AnalysisService._create_miro_card_safe` (visualisation is separate)
- `StorageRepository` (file storage is entry-type agnostic)
- Database engine and session management (`db.py`)
