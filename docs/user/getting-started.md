# Getting Started with GlucoTrack

GlucoTrack is a Telegram bot that helps you understand how food affects your glucose levels. You log a meal and your CGM (continuous glucose monitor) readings in a single *session*, and the bot delivers an AI-powered analysis.

## Quick start

1. Find the bot on Telegram and send `/start`
2. The bot opens a new session and explains the next steps
3. Log your meal, CGM data, and any activity notes
4. Send `/done` to trigger analysis
5. Read your personalised 4-section report

---

## Step-by-step walkthrough

### 1. Start a session

Send `/start` (or just start a new conversation).

> **Bot:** "Welcome to GlucoTrack! Send me a photo of your food or CGM reading to begin a session."

A session groups everything related to one meal event: food photos, CGM screenshots, and activity notes.

### 2. Log a food photo

Take a photo of your meal and send it to the bot.

> **Bot:** "Food photo saved ✓ (1 food · 0 CGM · 0 activity)"

You can send multiple food photos for the same meal.

### 3. Log a CGM screenshot

Take a screenshot of your CGM app (Dexcom, Libre, etc.) and send it.

The bot will ask you to choose the timing:
- **Fasting** — before eating
- **30 min after meal**
- **1 hour after meal**
- **2 hours after meal**

Select the option that matches when the reading was taken.

> **Bot:** "CGM screenshot saved ✓ (1 food · 1 CGM · 0 activity)"

You can add multiple CGM screenshots with different timings to show the full glucose curve.

### 4. Add an activity note (optional)

Send a text message describing any physical activity — for example:

> "30 min brisk walk before lunch"

The AI uses activity context when analysing your glucose response.

### 5. Check session status

Send `/status` at any time to see a summary of what's in your current session.

### 6. Complete the session and get your analysis

Send `/done` when you're ready for analysis.

> **Bot:** "Session completed! Analysis in progress… (this takes up to 30 seconds)"

The bot then sends a 4-section report:

#### 🥗 Nutrition estimate
Estimated carbs, protein, fat, and glycaemic index for the meal based on the food photo.

#### 📈 Glucose curve
Each CGM reading you provided, with a note on whether the value is within the healthy 70–140 mg/dL target range.

#### 🔗 Correlation
How the meal likely drove your glucose response — spikes, dips, and stable zones.

#### 💡 Recommendations
1–2 prioritised, actionable suggestions personalised to your meal and response pattern.

---

## Other commands

| Command | Description |
|---|---|
| `/start` | Open a new session (or restart) |
| `/done` | Complete the current session and request analysis |
| `/status` | Show current session entry counts |
| `/cancel` | Cancel the current session without analysis |
| `/trend` | See how many analysed sessions you have (trend analysis coming soon) |

---

## Tips

- **Multiple CGM screenshots** give the AI more data and produce better analysis. Try to capture fasting, 1h, and 2h readings.
- **Activity notes help** — even a short walk before a meal can change your glucose curve significantly.
- **If the CGM screenshot is unreadable**, the bot will let you know and ask you to send a clearer screenshot.
- **Sessions expire after 24 hours** of inactivity. If you haven't sent `/done`, the session is automatically closed.
- **Rate limit** — the AI can analyse up to 10 sessions per day per user.
