# Adding a New Visualisation Layer

GlucoTrack's visualisation layer is an output channel: it receives a completed `AIAnalysis` object and renders it somewhere useful. Miro is the current default. This guide explains how to add a second visualisation target — for example a PDF export, a Grafana dashboard push, or a custom web chart.

## What "visualisation layer" means

A visualisation layer is responsible for:
1. Receiving a completed `AIAnalysis` model (nutrition, glucose curve, correlation, recommendations)
2. Rendering or exporting that data in a visual format
3. Optionally returning a reference (URL, card ID, file path) that can be stored

It does **not** decide when to run. That is the responsibility of `AnalysisService`.

## How the current Miro layer works

```
AnalysisService.run_analysis()
  └─ MiroService.create_session_card(analysis)   ← isolated output adapter
       └─ POST /v2/boards/{board_id}/cards        ← Miro REST API
```

`MiroService` is the only Miro-specific code. Everything that calls it (`AnalysisService`) is reusable. The contract is defined in `contracts/miro-api-schema.md`.

**Key rule (FR-009 / Constitution II)**: Miro failure must never block the Telegram response. `AnalysisService` uses `asyncio.create_task` + a `_safe` wrapper for the Miro call. Any new visualisation layer must follow the same fire-and-forget pattern.

## Adding a new layer — step by step

### 1. Create a service module

Create `src/glucotrack/services/my_vis_service.py`:

```python
"""MyVisService — render AIAnalysis to <target>."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MyVisService:
    """Renders analysis results to <target>.

    Must not raise exceptions that propagate to callers — log and absorb.
    """

    def __init__(self, api_key: str, endpoint: str) -> None:
        self._api_key = api_key
        self._endpoint = endpoint

    async def create_session_card(self, analysis: Any) -> str:
        """Render analysis and return a reference ID or URL."""
        # ... implementation ...
        return "some-reference-id"
```

Keep the same method signature as `MiroService.create_session_card` — `AnalysisService` calls it duck-typed via `Any`.

### 2. Add configuration

Add fields to `src/glucotrack/config.py`:

```python
class Settings(BaseSettings):
    ...
    my_vis_api_key: str | None = Field(default=None, description="MyVis API key")
    my_vis_endpoint: str | None = Field(default=None, description="MyVis endpoint URL")
```

### 3. Persist a record before the async call

Before firing the background task, persist a `MiroCard`-equivalent record synchronously. This ensures the DB record is created even if the background task never runs. See `AnalysisService.run_analysis` lines 161–178 for the Miro pattern.

If your layer needs a different record type, add a new model under `src/glucotrack/models/`.

### 4. Wire the service into AnalysisService (fire-and-forget)

`AnalysisService.__init__` already accepts `miro_service: Any`. You can:

**Option A — replace Miro**: pass your new service as `miro_service` and it will be called in place of Miro.

**Option B — run alongside Miro**: add a second `vis_service: Any` parameter to `AnalysisService.__init__` and add a second fire-and-forget task in `run_analysis`:

```python
if self._vis is not None and vis_card is not None:
    asyncio.create_task(self._create_vis_card_safe(analysis, vis_card.id))
```

### 5. Wire the service into create_application()

In `src/glucotrack/bot/application.py`, instantiate your service alongside `MiroService` and pass it to `_AnalysisServiceRunner`:

```python
my_vis_service = MyVisService(
    api_key=settings.my_vis_api_key,
    endpoint=settings.my_vis_endpoint,
)
app.bot_data["analysis_service"] = _AnalysisServiceRunner(
    ai_service=ai_service,
    miro_service=miro_service,
    vis_service=my_vis_service,   # added
    storage_root=settings.storage_root,
)
```

### 6. Write a contract test

Add `tests/contract/test_my_vis_api_schema.md` (schema) and `tests/contract/test_my_vis_api_schema.py` (contract test) mirroring `test_miro_api_schema.py`. Contract tests verify that your service's HTTP calls conform to the documented schema, independently of the Miro tests.

## What you do NOT need to change

- All models (`models/`)
- All repositories (`repositories/`)
- `SessionService`, `AIService`
- Storage layer (`storage/`)
- Database setup (`db.py`)
- Telegram handlers

## Fire-and-forget pattern summary

```python
# Always persist the record before firing the background task
record = MyVisRecord(user_id=user_id, ...)
db.add(record)
await db.commit()

# Fire task — failure must never reach the user
asyncio.create_task(self._create_vis_safe(analysis, record.id))
```

```python
async def _create_vis_safe(self, analysis: Any, record_id: str) -> None:
    try:
        ref = await self._vis.create_session_card(analysis=analysis)
        logger.info("Vis card created: %s (record=%s)", ref, record_id)
    except Exception as exc:
        logger.error("Vis card creation failed (non-blocking, record=%s): %s", record_id, exc)
```
