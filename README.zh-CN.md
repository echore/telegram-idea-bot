# 想法收件箱 — Telegram 存进 Notion

[English](README.md) · **中文**

在 Telegram 里发一句话，几分钟后它已经躺在你的 Notion 数据库里，标题和页面
结构都写好了，全程不用打开 Notion。

**永久免费。** 不用服务器，不用订阅，不用信用卡。

<!-- 截图 1（首图）：左边 Telegram 对话，右边生成的 Notion 页面 -->

## 为什么做这个

想法总在你没准备好的时候冒出来。走路的时候，地铁上，开会前两分钟。它们也
走得很快，而丢掉的那些你根本看不见，所以你永远不知道自己丢了多少。

有一个专门存想法的地方，只解决了一半问题。Notion 很适合当这个地方。难的是
另一半：怎么把想法**放进去**。在手机上要解锁、找到 App、等它加载、翻到那个
数据库、点新建、再等一下，然后才开始打字。念头和记录之间隔着六步，每一步都
可能让你算了。

重点不是 Telegram，是把步骤去掉。

以前存一个想法要点六下，还要等两次加载。现在只要一下：你发一条消息。剩下
那些本来要你手动做的事，起标题、设状态、选数据库、把页面分成几段，在你把
手机塞回口袋的时候已经做完了。你全程不用打开 Notion，条目照样按你定好的
格式进库。

## 它怎么工作

```
你 ──▶ Telegram bot
             │
             │   每 15 分钟，GitHub Actions 醒一次
             ▼
        拉取你上次运行之后发的消息
             │
             ▼
        逐条写进你的 Notion 数据库
             │
             ▼
        在 Telegram 回你一个页面链接，然后退出
```

没有服务器。GitHub Actions 的定时任务跑一遍脚本，队列空了就退出。

用到的东西全是免费的：GitHub Actions、Telegram bot、Notion API。

这个设计带来三件事，装之前值得先知道：

- **捕捉是即时的，入库不是。** 消息发出去那一刻就安全了，但 Notion 页面要等
  下一次运行：通常 15 分钟内，GitHub 排队的时候偶尔到 25 分钟。
- **两次运行之间不会丢消息。** Telegram 会在自己服务器上保留未取走的消息 24
  小时，bot 醒来时直接把积压的一起处理掉。
- **东西都是你自己的。** 你的 fork、你的 bot token、你的 Notion 数据库。中间
  没有第三方服务，也没有别人能看到你发了什么。

## Notion 里会得到什么

一条消息变成一个页面。第一句话作为标题，`Status` 设成 `Raw`，`Category` 设成
`Random`，正文按三段写好，方便你以后回来慢慢想：

```md
## Raw Capture
<你的原始消息，一字不改>

## Next Step
如果这个想法值得继续，写一个最小的下一步动作。

## Notes
补充背景、判断、延伸方向。
```

思路是先存下来，之后再整理。在捕捉的当下让你选分类，恰恰是这个工具要消除的
摩擦，所以 bot 不问你任何问题。

<!-- 截图 2：bot 真实生成的 Notion 页面，能看到三个小标题和属性栏 -->

## 怎么装（大约 10 分钟）

需要 Telegram、Notion、GitHub 三个账号。不用写代码，不用服务器，不用信用卡。

### 1. 准备 Notion 数据库

在 Notion 里建一个数据库，包含三个属性：

| 属性 | 类型 | 用途 |
|---|---|---|
| `Idea` | Title | 自动生成的标题 |
| `Status` | Select | 这个想法走到哪一步了 |
| `Category` | Multi-select | 粗略分组 |

`Status` 建议的选项：`Raw`、`Developing`、`Dormant`、`Discarded`。
`Category` 建议的选项：`Product`、`Business`、`Content`、`Research`、`Life`、
`Random`。属性名后面可以改配置，你也可以用自己的一套。

<!-- TODO: Notion 模板发布后，在这里加一键复制链接 -->

从数据库的 URL 里，复制 workspace 名和 `?` 之间那串 32 位字符，这就是你的
**database ID**，第 4 步要用。

```
https://www.notion.so/myworkspace/8f4c1a2b3d5e6f708192a3b4c5d6e7f8?v=...
                                  └────────── database ID ──────────┘
```

<!-- 截图 3：建好三个属性的数据库，以及 URL 里高亮出 database ID 的位置 -->

### 2. 建 Telegram bot

在 Telegram 里找 [@BotFather](https://t.me/BotFather)，发 `/newbot`，回答两个
问题：显示名称，然后一个以 `bot` 结尾的用户名。BotFather 会回你一个
**bot token**，长得像 `123456789:AAF...`。

这个 token 不要外传，拿到它的人可以用你的 bot 发消息。

<!-- 截图 4：BotFather 对话，token 打码 -->

### 3. 把 Notion 连给 bot

去 [notion.so/my-integrations](https://www.notion.so/my-integrations)，点
**New integration**，名字随便取，复制 **Internal Integration Secret**。

然后打开第 1 步的数据库，点右上角 `···` → **Connections → Connect to**，选中
刚建的 integration。**这一步不做，Notion 会返回 404**，bot 看不见这个数据库。

<!-- 截图 5：数据库页面上的 Connections 菜单 -->

### 4. Fork 仓库并填入密钥

点本页顶部的 **Fork**。在你的 fork 里进 **Settings → Secrets and variables →
Actions → New repository secret**，加三个：

| 名称 | 值 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | 第 2 步的 token |
| `NOTION_TOKEN` | 第 3 步的 integration secret |
| `IDEA_NOTION_DATABASE_ID` | 第 1 步的 database ID |

GitHub 会加密保存，之后谁都看不到明文，包括你自己。别人浏览你的 fork 也看
不到。

<!-- 截图 6：Actions secrets 页面，能看到三个名字 -->

### 5. 启用 Actions 并测试

打开你 fork 的 **Actions** 标签页，点那个确认按钮。fork 出来的仓库默认禁用
定时任务，所以这步必须做。

现在给你的 bot 随便发一句话。15 分钟内 Notion 里会出现页面，bot 也会回你一个
链接。不想等的话，进 **Actions → poll-telegram → Run workflow** 立即触发一次。

## 自定义

如果你的数据库字段名不一样，加更多 secret 覆盖默认值就行。
[`.env.example`](.env.example) 里的每个变量都可以当 secret 用：

| Secret | 默认值 | 作用 |
|---|---|---|
| `IDEA_TITLE_PROPERTY` | `Idea` | 标题字段名 |
| `IDEA_STATUS_PROPERTY` | `Status` | 状态字段名 |
| `IDEA_CATEGORY_PROPERTY` | `Category` | 分类字段名 |
| `IDEA_DEFAULT_STATUS` | `Raw` | 新页面的状态 |
| `IDEA_DEFAULT_CATEGORY` | `Random` | 新页面的分类 |
| `IDEA_MAX_TITLE_LENGTH` | `60` | 标题超过多长就截断 |

想改运行频率，编辑 [`.github/workflows/poll.yml`](.github/workflows/poll.yml)
里的 cron。GitHub 最短接受 5 分钟，但实际到货并不会比 15 分钟更快。

## 已知限制

GitHub 的定时任务是尽力而为：负载高的时候会延迟；仓库 60 天没有新提交，
GitHub 会暂停定时任务并给你发邮件，点一下就能恢复。

知道你 bot 用户名的人都能给它发消息，这些消息会进你的数据库。这个项目不会把
用户名公开到任何地方，但如果你自己分享出去，就要当作谁拿到链接谁都能写。

目前只处理文字。图片、语音、转发的文件会收到一句提示，让你改发文字。

## 本地运行

```bash
git clone https://github.com/YOUR_USERNAME/idea-to-notion.git
cd idea-to-notion
pip install -r requirements.txt
cp .env.example .env    # 填进你的三个值
python bot.py
```

`bot.py` 会把当前排队的消息处理完然后退出，和定时任务做的事完全一样。
`.env` 已被 gitignore。跑测试用 `pytest`。
