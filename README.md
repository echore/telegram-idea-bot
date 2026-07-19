# Telegram → Notion 想法捕获 bot

在 Telegram 随手发一段文字，几分钟内自动存进你的 Notion 想法库，
自动生成标题和页面结构。跑在 GitHub Actions 上，永久免费，无需服务器。

## 它怎么工作
GitHub Actions 每 15 分钟触发一次，拉取这段时间你发的消息，逐条写进
Notion，然后退出。不是实时的——通常几分钟到二十几分钟内进库。

## 自助部署（约 10 分钟）

1. **建 Telegram bot**：Telegram 里找 @BotFather，发 `/newbot`，
   按提示拿到 bot token。
2. **建 Notion integration**：https://www.notion.so/my-integrations
   新建 integration，复制 secret。建一个数据库（至少含标题、Status、
   Category 字段），在数据库右上 ··· → Connections 里把 integration
   连上，复制数据库 ID（URL 里那段 32 位字符）。
3. **Fork 本仓库**。
4. **填 Secrets**：仓库 Settings → Secrets and variables → Actions，
   新建三个：`TELEGRAM_BOT_TOKEN`、`NOTION_TOKEN`、
   `IDEA_NOTION_DATABASE_ID`。
5. **启用 Actions**：仓库 Actions 页，点 "I understand... enable"。
6. **测试**：给你的 bot 发一段话，最多 15 分钟看 Notion。也可以到
   Actions 页手动点 "Run workflow" 立即触发一次。

## 自定义字段名
若你的 Notion 字段不叫 Idea/Status/Category，可在 Secrets 里额外设
`IDEA_TITLE_PROPERTY` / `IDEA_STATUS_PROPERTY` / `IDEA_CATEGORY_PROPERTY`
等（见 `.env.example`）。

## 已知限制
- cron 高峰期可能延迟 5–20 分钟。
- 仓库 60 天无提交，GitHub 会自动暂停定时任务并发邮件，点一下即可恢复。

## 本地开发
复制 `.env.example` 为 `.env` 填入真实值，然后 `pip install -r
requirements.txt && python bot.py`。`.env` 已被 `.gitignore` 忽略。
