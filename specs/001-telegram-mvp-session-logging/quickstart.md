# Quickstart: GlucoTrack Telegram MVP

**Feature**: 001-telegram-mvp-session-logging | **Date**: 2026-04-17

---

## Prerequisites

- Python 3.11+
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- An Anthropic API key (from [console.anthropic.com](https://console.anthropic.com))
- A Miro developer access token and board ID (from [developers.miro.com](https://developers.miro.com))

---

## 1. Clone & Install

```bash
git clone <repo>
cd GlucoTrack
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2. Configure Environment

Copy the example env file and fill in values:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Miro
MIRO_ACCESS_TOKEN=your_miro_token_here
MIRO_BOARD_ID=your_miro_board_id_here

# Storage
STORAGE_ROOT=./data
DATABASE_URL=sqlite:///./data/glucotrack.db

# Session settings
SESSION_IDLE_THRESHOLD_MINUTES=30
SESSION_IDLE_EXPIRY_HOURS=24
SESSION_DISAMBIGUATE_TIMEOUT_HOURS=2

# Rate limits (Constitution VII)
AI_MAX_CALLS_PER_USER_PER_DAY=10
AI_MAX_TOKENS_PER_SESSION=4000
```

---

## 3. Initialise Database

```bash
python -m glucotrack.db init
```

---

## 4. Run the Bot

```bash
python -m glucotrack
```

The bot starts in polling mode. Send `/start` to your bot in Telegram to verify it responds.

---

## 5. Run Tests

```bash
# All tests with coverage
pytest tests/ -v --cov=src/glucotrack --cov-report=term-missing --cov-fail-under=80

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Contract tests only
pytest tests/contract/ -v
```

---

## 6. Lint & Format

```bash
ruff check src/ tests/
black --check src/ tests/
mypy src/
```

---

## 7. Full Session Flow (Manual Verification)

1. Open Telegram, find your bot
2. Send `/start` → expect welcome message
3. Send a food photo → expect type prompt (Food/CGM)
4. Choose "Food photo" → expect acknowledgement
5. Send a CGM screenshot → expect type prompt
6. Choose "CGM screenshot" → expect timing prompt
7. Choose "1 hour after" → expect acknowledgement
8. Send `/done` → expect "Analysis in progress…"
9. Wait up to 30 seconds → expect structured analysis
10. Check your Miro board → expect a new card within 5 seconds of analysis

---

## 8. Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from BotFather |
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `ANTHROPIC_MODEL` | No | `claude-3-5-sonnet-20241022` | Claude model to use |
| `MIRO_ACCESS_TOKEN` | Yes | — | Miro developer access token |
| `MIRO_BOARD_ID` | Yes | — | Target Miro board ID |
| `STORAGE_ROOT` | No | `./data` | Root directory for file storage |
| `DATABASE_URL` | No | `sqlite:///./data/glucotrack.db` | SQLAlchemy connection string |
| `SESSION_IDLE_THRESHOLD_MINUTES` | No | `30` | Minutes of inactivity before disambiguation prompt |
| `SESSION_IDLE_EXPIRY_HOURS` | No | `24` | Hours before abandoned session auto-expires |
| `SESSION_DISAMBIGUATE_TIMEOUT_HOURS` | No | `2` | Hours to wait for disambiguation response before auto-closing |
| `AI_MAX_CALLS_PER_USER_PER_DAY` | No | `10` | Rate limit: max analysis calls per user per day |
| `AI_MAX_TOKENS_PER_SESSION` | No | `4000` | Max output tokens per Claude API call |
