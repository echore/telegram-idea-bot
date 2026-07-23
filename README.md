# Idea Inbox — Telegram to Notion

**English** · [中文](README.zh-CN.md)

Send a thought to a Telegram bot. A few minutes later it is sitting in your
Notion database, titled and structured, without you opening Notion at all.

**Free to run, permanently.** No server, no subscription, no credit card.

<!-- SCREENSHOT 1 (hero): Telegram chat on the left, the resulting Notion page on the right -->

## Why This Exists

Ideas show up when you are not ready for them. Walking somewhere, on the train,
two minutes before a meeting starts. They also leave quickly, and the ones you
lose are invisible to you, so you never learn how many there were.

A dedicated place to keep ideas solves half of the problem. Notion works well
for that. Getting an idea *into* Notion is the other half, and on a phone it is
slow: unlock, find the app, wait for it to load, navigate to the right database,
tap New, wait again, then finally type. Six steps stand between the thought and
the record, and any one of them is a place to give up.

Telegram is not the point. Removing the steps is.

Saving an idea used to cost six taps and two loading screens. Now it costs one:
you send a message. The work you would have done by hand afterwards, writing a
title, setting the status, picking the database, laying the page out into
sections, gets done for you while you put the phone back in your pocket. You
never open Notion, and the entry still arrives in exactly the format you set up.

## How It Works

```
you ──▶ Telegram bot
             │
             │   every 15 minutes, GitHub Actions wakes up
             ▼
        fetch the messages you sent since the last run
             │
             ▼
        for each one: write a page into your Notion database
             │
             ▼
        reply in Telegram with the page link, then exit
```

There is no server. A scheduled GitHub Actions job runs the script, and the job
exits as soon as the queue is empty.

Every piece of this is free: GitHub Actions, the Telegram bot, the Notion API.

Three things follow from the design, and they are worth knowing before you set
it up:

- **Capture is instant, saving is not.** Your message is safe the moment you
  send it, but the Notion page appears on the next run: usually within 15
  minutes, occasionally 25 when GitHub's scheduler is busy.
- **Nothing is lost between runs.** Telegram holds undelivered messages on its
  own servers for 24 hours, so the bot picks up the backlog when it wakes.
- **You own all of it.** Your fork, your bot token, your Notion database. No
  third-party service sits in the middle, and no one else can read what you send.

## What Lands in Notion

Each message becomes one page. The first sentence becomes the title, `Status` is
set to `Raw`, `Category` to `Random`, and the body arrives pre-sectioned so that
the page is ready to think in later:

```md
## Raw Capture
<your original message, untouched>

## Next Step
If this idea is worth continuing, write the smallest possible next action.

## Notes
Background, judgement, directions to extend.
```

The intent is to capture now and organize later. Sorting ideas at the moment of
capture is exactly the friction this tool removes, so the bot never asks you to
pick a category.

<!-- SCREENSHOT 2: a real Notion page created by the bot, showing the three sections and the property bar -->

## Set It Up (About 10 Minutes)

You need a Telegram account, a Notion account, and a GitHub account. No
programming, no server, no credit card.

### 1. Prepare the Notion Database

Create a database in Notion with three properties:

| Property | Type | Purpose |
|---|---|---|
| `Idea` | Title | the generated title |
| `Status` | Select | how far the idea has gotten |
| `Category` | Multi-select | rough grouping |

Suggested `Status` options are `Raw`, `Developing`, `Dormant`, and `Discarded`.
Suggested `Category` options are `Product`, `Business`, `Content`, `Research`,
`Life`, and `Random`. Property names are configurable later, so use your own if
you prefer.

<!-- TODO: add one-click template link here once the Notion template is published -->

From the database URL, copy the 32-character block between your workspace name
and the `?`. That is your **database ID**, and you will paste it in step 4.

```
https://www.notion.so/myworkspace/8f4c1a2b3d5e6f708192a3b4c5d6e7f8?v=...
                                  └────────── database ID ──────────┘
```

<!-- SCREENSHOT 3: the database with its three properties, plus the URL with the database ID highlighted -->

### 2. Create the Telegram Bot

In Telegram, open a chat with [@BotFather](https://t.me/BotFather) and send
`/newbot`. Answer the two questions, a display name and then a username ending
in `bot`. BotFather replies with a **bot token** that looks like
`123456789:AAF...`.

Keep that token private. Anyone holding it can post as your bot.

<!-- SCREENSHOT 4: the BotFather conversation, token blurred -->

### 3. Connect Notion to the Bot

Go to [notion.so/my-integrations](https://www.notion.so/my-integrations), click
**New integration**, name it anything, and copy the **Internal Integration
Secret**.

Then open the database from step 1, click the `···` menu in the top right,
choose **Connections → Connect to**, and pick the integration you just made.
Without this step Notion returns a 404 and the bot cannot see the database.

<!-- SCREENSHOT 5: the Connections menu on the database page -->

### 4. Fork This Repository and Add Your Keys

Click **Fork** at the top of this page. In your fork, go to **Settings → Secrets
and variables → Actions → New repository secret** and add three:

| Name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | the token from step 2 |
| `NOTION_TOKEN` | the integration secret from step 3 |
| `IDEA_NOTION_DATABASE_ID` | the database ID from step 1 |

GitHub encrypts these and never shows them again, including to you. They stay
invisible to anyone browsing your fork.

<!-- SCREENSHOT 6: the Actions secrets page listing the three names -->

### 5. Turn On Actions and Test

Open the **Actions** tab in your fork and click the button confirming that you
want workflows to run. Forked repositories start with scheduled jobs disabled,
so this step is required.

Now send your bot any message in Telegram. Within 15 minutes the page appears in
Notion and the bot replies with a link. If you would rather not wait, open
**Actions → poll-telegram → Run workflow** to trigger a run immediately.

## Customizing

If your database uses different property names, add more secrets to override the
defaults. Every variable in [`.env.example`](.env.example) works as a repository
secret:

| Secret | Default | What It Sets |
|---|---|---|
| `IDEA_TITLE_PROPERTY` | `Idea` | the title property |
| `IDEA_STATUS_PROPERTY` | `Status` | the status property |
| `IDEA_CATEGORY_PROPERTY` | `Category` | the category property |
| `IDEA_DEFAULT_STATUS` | `Raw` | status given to new pages |
| `IDEA_DEFAULT_CATEGORY` | `Random` | category given to new pages |
| `IDEA_MAX_TITLE_LENGTH` | `60` | where long titles get truncated |

To change how often the bot runs, edit the cron line in
[`.github/workflows/poll.yml`](.github/workflows/poll.yml). Five minutes is the
shortest interval GitHub accepts, and in practice it delivers no faster than 15.

## Limits Worth Knowing

Scheduled jobs on GitHub are best-effort. Runs are delayed under load, and
GitHub pauses the schedule after 60 days without a commit to the repository. You
receive an email when that happens, and one click restores it.

Anyone who knows your bot's username can message it, and those messages land in
your database. This project does not publish your username anywhere, but if you
share it, treat the bot as open to whoever has the link.

Only text is handled today. Photos, voice notes, and forwarded files get a short
reply asking for text instead.

## Running It Locally

```bash
git clone https://github.com/YOUR_USERNAME/idea-to-notion.git
cd idea-to-notion
pip install -r requirements.txt
cp .env.example .env    # fill in your three values
python bot.py
```

`bot.py` processes whatever is waiting and exits, which is the same thing the
scheduled job does. `.env` is gitignored. Run the tests with `pytest`.
