# Developer Setup Guide

## Prerequisites

- Python 3.11 or newer
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- An Anthropic API key (from [console.anthropic.com](https://console.anthropic.com))
- A Miro developer access token and board ID (from [developers.miro.com](https://developers.miro.com))

## 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd GlucoTrack
python3 -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows
```

## 2. Install dependencies

```bash
pip install -e ".[dev]"          # runtime + dev tools
```

For the visual sandbox too:

```bash
pip install -e ".[dev,sandbox]"
```

## 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in all required values:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
ANTHROPIC_API_KEY=your_anthropic_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022   # optional override
MIRO_ACCESS_TOKEN=your_miro_token_here
MIRO_BOARD_ID=your_board_id_here

# Optional — defaults shown
STORAGE_ROOT=./data
DATABASE_URL=sqlite+aiosqlite:///./data/glucotrack.db
SESSION_IDLE_THRESHOLD_MINUTES=30
SESSION_IDLE_EXPIRY_HOURS=24
AI_MAX_CALLS_PER_USER_PER_DAY=10
AI_MAX_TOKENS_PER_SESSION=4000
```

## 4. Initialise the database

```bash
python -m glucotrack.db init     # creates tables via SQLAlchemy metadata
# or run Alembic migrations:
alembic upgrade head
```

## 5. Run the bot

```bash
source .venv/bin/activate         # activate venv first — `python` is not on system PATH
python -m glucotrack              # starts Telegram long-polling
```

## 6. Run tests

```bash
pytest tests/ -v                  # all tests
pytest tests/unit/ -v             # unit only
pytest tests/integration/ -v      # integration only (in-memory DB)
pytest tests/ --cov-fail-under=80 # enforce coverage gate
```

## 7. Lint, format, type-check

```bash
ruff check src/ tests/
black src/ tests/
mypy src/
bandit -r src/ -ll                # security scan
```

## 8. Run the sandbox (optional)

Visual workflow inspector — lets you test the full pipeline without a real Telegram chat:

```bash
python -m sandbox.main
# Open http://localhost:8765
```

Toggle each component (Claude AI, Miro) between mock and real mode. Click "Run Workflow" to execute and watch all 7 steps animate with live request/response payloads.

## Directory layout

```
src/glucotrack/
├── bot/            handlers, formatters, PTB application wiring
├── domain/         state machines, pure business rules
├── models/         SQLAlchemy ORM mapped classes
├── repositories/   data access layer (all queries scoped by user_id)
├── services/       orchestration (session, AI analysis, Miro)
├── storage/        file I/O behind StorageRepository
├── config.py       pydantic-settings env loading
├── db.py           async engine factory, init_db()
└── __main__.py     entry point

sandbox/            visual developer sandbox (FastAPI + WebSocket)
tests/
├── unit/           fast, in-memory, no network
├── integration/    in-memory SQLite, mocked external APIs
└── contract/       schema validation for Claude and Miro API contracts

specs/001-telegram-mvp-session-logging/
    spec.md, plan.md, tasks.md, data-model.md, contracts/
```
