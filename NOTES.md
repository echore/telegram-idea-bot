# Notes For The Next Session

## What this project is

This is a standalone Telegram idea capture bot, separate from the startup outreach demo in the parent folder.

The purpose is simple:

- capture ideas from phone or desktop with almost zero friction
- store them in a Notion ideas database
- keep the database properties light
- keep the actual thinking inside each Notion page body

## Current Notion design

The target Notion database is an ideas database named `想法库`.

Key properties:

- `Idea` (title)
- `Status`
- `Category`
- `Created At`

Suggested `Status` values:

- `Raw`
- `Developing`
- `Dormant`
- `Discarded`

Suggested `Category` values:

- `Product`
- `Business`
- `Content`
- `Research`
- `Life`
- `Random`

## Current bot behavior

When a Telegram message arrives:

1. Take the first line or first sentence as the title.
2. Create a Notion page in the ideas database.
3. Set:
   - `Status = Raw`
   - `Category = Random`
4. Write the page body as:

```md
## Raw Capture
<original Telegram message>

把你当下想到的话原样丢进来，不用整理。

## Next Step
如果这个想法值得继续，写一个最小的下一步动作。

## Notes
补充背景、判断、延伸方向。
```

## Critical safety context

- Do not read `.env` by default.
- Do not ask the user to paste secrets into chat.
- This workspace previously contained old tokens that were removed.
- The old tokens are invalid for future use.
- On the next setup attempt, new tokens must be created before the bot can run.
- The user is busy and may not want to create new tokens immediately.

## What to do next if restarting this work

1. Confirm the user still wants this project separate from the parent demo.
2. Remind them that previous tokens are invalid.
3. Ask them to create fresh:
   - `TELEGRAM_BOT_TOKEN`
   - `NOTION_TOKEN`
4. Confirm the Notion integration has access to the ideas database.
5. Run the bot locally or deploy via Render.
