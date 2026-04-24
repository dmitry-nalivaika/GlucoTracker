# Quickstart / Test Scenarios: 004 — Bot UX: Guided Flow, Action Keyboard, Status Messages & Miro Card Enhancements

## Manual Acceptance Scenarios

### Scenario 1: Guided Flow + Action Keyboard

1. Send `/new` to the bot.
2. **Expect**: Bot replies "✅ New session started. Send a food photo to begin."
   AND a reply keyboard appears with `/done`, `/cancel`, `/status` buttons.
3. Send a food photo.
4. Select "🍽️ Food photo" on the inline keyboard.
5. **Expect**: Ack message includes next-step hint (e.g. "Send another food photo, or
   send your CGM screenshot, or tap /done when ready."). Reply keyboard still present.
6. Send a photo. Select "📈 CGM screenshot". Select "1 hour after".
7. **Expect**: CGM ack includes next-step hint. Reply keyboard still present.
8. Send text "walked 20 minutes".
9. **Expect**: Activity ack includes next-step hint. Reply keyboard still present.
10. Tap the `/done` button on the keyboard.
11. **Expect**: Analysis queued message. Reply keyboard removed.

### Scenario 2: Bot Online Broadcast

1. Restart the bot process.
2. **Expect**: Within a few seconds, users with stored `chat_id` receive
   "🟢 GlucoTrack is online and ready!" in their language.

### Scenario 3: RAG Badge in Miro Card

1. Complete a session with CGM screenshots where all readings are in range (70–140).
2. Trigger `/done` and wait for analysis.
3. Open Miro board.
4. **Expect**: The glucose sticky note header shows `🟢 Green — all readings in range`.

### Scenario 4: Executive Summary Sticky Note

1. Complete a session with food + CGM.
2. After analysis, open Miro board.
3. **Expect**: A grey sticky note at the bottom of the frame contains a 2-3 sentence
   executive summary and an encouragement sentence.

### Scenario 5: Single-Row Photo Layout

1. Complete a session with 2 food photos + 2 CGM screenshots.
2. After analysis, open Miro board.
3. **Expect**: All 4 photos appear in ONE horizontal row (food photos first, CGM second).
   The frame is wider than the 1200 px default to accommodate 4 images.

---

## Local Test Commands

```bash
source .venv/bin/activate
pytest tests/unit/test_formatters.py -v -k "guided"
pytest tests/unit/test_miro_service.py -v -k "rag or summary or single_row"
pytest tests/unit/test_user_repository.py -v -k "chat_id"
pytest tests/integration/test_bot_status.py -v
pytest tests/contract/test_ai_contract.py -v -k "executive"
pytest tests/ -q --cov-fail-under=80
ruff check src/ tests/ && black --check src/ tests/ && mypy src/
```
