# Telegram Idea Library Implementation Guide

## Goal

Build a low-friction system where any spontaneous idea can be sent from Telegram to Notion and stored in a structured, reviewable way.

The design goal is not heavy classification at capture time. The design goal is:

1. capture instantly
2. organize later
3. develop only the ideas that survive review

## Final workflow

### 1. Capture

The user sends any free-form text message to a Telegram bot.

Examples:

```text
做一个给学生筛选北美 early-stage startup internship 的信息流
```

```text
做一期内容，讲为什么大多数学生不会真正找教授，而只是在搜项目
```

### 2. Create a Notion page

The bot creates a new page inside the ideas database.

Database properties stay intentionally light:

- title property: `Idea`
- status property: `Status`
- category property: `Category`

Default values:

- `Status = Raw`
- `Category = Random`

### 3. Write the page body

The bot writes a standard page structure:

```md
## Raw Capture
<original Telegram message>

把你当下想到的话原样丢进来，不用整理。

## Next Step
如果这个想法值得继续，写一个最小的下一步动作。

## Notes
补充背景、判断、延伸方向。
```

This keeps the database clean while preserving room for deeper thinking inside each page.

### 4. Review later in Notion

The user does not classify everything during capture.

Later, they review `Raw` items and move them into:

- `Developing`
- `Dormant`
- `Discarded`

This is the key workflow principle: separate capture from judgment.

## Why this design is different from a social media material collector

A link collector is input-constrained:

- input is a URL
- fields are predictable
- enrichment happens later

An idea library is different:

- input is messy free text
- the first version is often incomplete
- preserving the original wording matters
- most of the value is in later review, not initial formatting

So the bot should not behave like a metadata collector. It should behave like an idea inbox.

## How AI assisted the build

AI helped in four ways:

### 1. Product framing

AI helped distinguish between:

- a link-saving workflow
- an idea-capture workflow

That led to a simpler and more suitable design.

### 2. Notion structure design

AI proposed a minimal database model with:

- a small set of statuses
- a small set of categories
- detailed thinking stored in the page body instead of many database properties

### 3. Bot implementation

AI wrote the Python bot that:

- reads Telegram text messages
- generates a short title
- creates a Notion page
- writes the standard page structure

### 4. Deployment packaging

AI split the bot into a dedicated folder with:

- isolated dependencies
- a clean `.env.example`
- Render deployment config
- handoff documents for future sessions

## Setup checklist

1. Create a Telegram bot using `@BotFather`
2. Create a fresh Notion integration
3. Share the ideas database with that integration
4. Fill `.env` from `.env.example`
5. Install dependencies
6. Run locally or deploy to Render

## Security rules for future work

1. Do not read `.env` by default.
2. Do not read token files by default.
3. Do not ask the user to paste secrets into chat.
4. If tokens were previously removed, assume the old setup is broken until fresh tokens are created.
