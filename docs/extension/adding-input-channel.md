# Adding a New Input Channel

GlucoTrack's architecture separates the *input channel* (how users interact) from the *domain and service layers* (what the system does). Telegram is the current input channel. This guide explains how to add a second channel — for example a REST API, a WhatsApp integration, or a CLI.

## What "input channel" means

An input channel is responsible for:
1. Receiving user input (text, images, commands)
2. Calling the appropriate *service* method
3. Sending the response back to the user

It does **not** contain business logic. All decisions about session state, analysis, and data storage live in the service layer.

## How the current Telegram channel works

```
PTB Application (bot/application.py)
  └─ ConversationHandler
       └─ handlers.py (one handler per user action)
            └─ SessionService / AnalysisService (shared business logic)
```

`handlers.py` is the *only* Telegram-specific code. Everything below it is reusable.

## Adding a new channel — step by step

### 1. Create a new adapter module

Create a directory for your channel, e.g. `src/glucotrack/api/` for a REST API.

```
src/glucotrack/
└── api/
    ├── __init__.py
    ├── router.py      ← FastAPI routes (equivalent of handlers.py)
    └── schemas.py     ← request/response Pydantic models
```

### 2. Initialise the same services

Your adapter needs the same services as the Telegram channel:

```python
from glucotrack.config import get_settings
from glucotrack.db import get_async_session
from glucotrack.services.session_service import SessionService
from glucotrack.services.analysis_service import AnalysisService
from glucotrack.storage.local_storage import StorageRepository

async def get_session_service(db: AsyncSession = Depends(get_async_session)) -> SessionService:
    settings = get_settings()
    return SessionService(
        db=db,
        storage=StorageRepository(settings.storage_root),
        idle_threshold_minutes=settings.session_idle_threshold_minutes,
        idle_expiry_hours=settings.session_idle_expiry_hours,
    )
```

### 3. Call service methods directly

Your handlers call exactly the same methods as the Telegram handlers:

```python
@router.post("/sessions/{user_id}/food")
async def upload_food_photo(
    user_id: int,
    file: UploadFile,
    svc: SessionService = Depends(get_session_service),
) -> dict:
    data = await file.read()
    await svc.handle_photo(
        telegram_user_id=user_id,   # or rename the parameter in SessionService
        file_data=data,
        telegram_file_id=file.filename,
        entry_type="food",
    )
    counts = await svc.get_entry_counts(user_id)
    return {"status": "saved", "entry_counts": counts}

@router.post("/sessions/{user_id}/done")
async def complete_session(
    user_id: int,
    background_tasks: BackgroundTasks,
    svc: SessionService = Depends(get_session_service),
    analysis_svc: AnalysisService = Depends(get_analysis_service),
) -> dict:
    session = await svc.complete_session(user_id)
    background_tasks.add_task(
        analysis_svc.run_analysis,
        user_id=user_id,
        session_id=session.id,
        chat_id=user_id,    # or a webhook callback URL
        bot=your_notifier,  # any object with async send_message()
    )
    return {"status": "completed", "session_id": session.id}
```

### 4. Implement the notifier interface

`AnalysisService.run_analysis()` expects a `bot` object with:

```python
async def send_message(self, chat_id: int, text: str, parse_mode: str | None = None) -> None:
    ...
```

For a REST API, this could push to a webhook, write to a database, or send an email. Implement a class with this method signature and pass it to `run_analysis`.

### 5. Wire it into the entry point

In `src/glucotrack/__main__.py` (or a new entrypoint), import and mount your adapter alongside or instead of the Telegram bot.

### 6. Update configuration if needed

If your new channel needs additional config (e.g. a webhook URL), add fields to `src/glucotrack/config.py`:

```python
class Settings(BaseSettings):
    ...
    api_webhook_url: str | None = Field(default=None, description="REST API webhook for analysis results")
```

## What you do NOT need to change

- All models (`models/`)
- All repositories (`repositories/`)
- `SessionService`, `AIService`, `AnalysisService`, `MiroService`
- Storage layer (`storage/`)
- Database setup (`db.py`)

These are all channel-agnostic by design.

## Renaming `telegram_user_id`

`SessionService` uses `telegram_user_id: int` as its user identifier. If your new channel uses a different user ID scheme, you have two options:

1. **Pass a derived integer** — hash or map your user ID to a stable `int`
2. **Add a `user_id_type` field** to `User` model and update `get_or_create_user()` to look up by the appropriate field

Option 1 is simpler; option 2 is cleaner for multi-channel deployments.
