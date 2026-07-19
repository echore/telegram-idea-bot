# Telegram → Notion 想法捕获 bot 设计文档

日期：2026-07-18
状态：已确认，待实现

## 目标
在 Telegram 发任意文字 → 几小时内（实际约 5–25 分钟）自动存进 Notion
想法库，自动生成标题和页面结构。无需打开 Notion 手动操作。
定位：通用受众，公开发布，别人可自助免费部署自己的版本。

## 非目标
- 不做秒回 / 实时响应
- 不做多轮对话、编辑、删除
- 不做多用户托管服务（每个人部署自己的实例）

## 架构：无状态定时轮询
运行在 GitHub Actions cron 上，每 15 分钟触发一次性脚本：

    定时触发 (cron */15)
      → getUpdates 拉取积压消息
      → 逐条: 解析文字 → 写 Notion 页面 → 回确认/报错给用户
      → getUpdates(offset=最后update_id+1) 标记该批已消费
      → 退出

无需外部数据库存 offset——Telegram 服务器负责保留未确认的消息。

## 关键设计决策
- **无状态 offset**：靠 Telegram 的 getUpdates offset 机制去重，
  不自己存状态。
- **失败也推进 offset**：某条写 Notion 失败 → 回一条错误提示给用户，
  但仍推进 offset，避免"毒消息"反复重试堵死后续消息。用户看到提示
  可手动补发。
- **崩溃容忍**：整批处理完才确认 offset；中途崩溃最坏是下次重复处理
  （低概率，可接受）。
- **并发保护**：workflow 设 concurrency group，防两次运行同时抢
  getUpdates。

## 🔀 本仓库处理逻辑（想法库）
- 一段文字 → 取首句/首行当标题（复用现有 summarize_title）
- 建 Notion 页面，页面体含 Raw Capture / Next Step / Notes 结构
- 属性名可通过环境变量配置（Idea / Status / Category），
  适配别人不同的表头

## 密钥安全
- 真实 token 绝不进代码、绝不进仓库
- 本地 .env（被 .gitignore 忽略），线上 GitHub Secrets
- workflow 通过 ${{ secrets.* }} 注入环境变量

## 环境变量
- TELEGRAM_BOT_TOKEN
- NOTION_TOKEN
- NOTION_DATABASE_ID (或 IDEA_NOTION_DATABASE_ID)
- 可选：IDEA_TITLE_PROPERTY / IDEA_STATUS_PROPERTY / IDEA_CATEGORY_PROPERTY
  / IDEA_DEFAULT_STATUS / IDEA_DEFAULT_CATEGORY

## 仓库结构
    .github/workflows/poll.yml   # cron 每15分钟
    bot.py                       # 一次性 getUpdates → 写 Notion
    requirements.txt
    .env.example
    .gitignore                   # 忽略 .env
    README.md                    # 部署教程 + Notion 建表说明

## 已知限制
- cron 高峰期延迟 5–20 分钟（对本需求可接受）
- 仓库 60 天无提交，GitHub 自动停用定时 workflow，需手动点一下恢复
  （README 说明）

## 别人部署步骤（写进 README）
1. BotFather 建 bot 拿 token
2. 建 Notion integration 拿 secret，建库、邀请 integration、复制 database ID
3. Fork 本仓库
4. Settings → Secrets 填 3 个值
5. Actions 页点 Enable
6. 发消息测试，最多 15 分钟看结果
