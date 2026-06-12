# SignalDigest 开源项目设计文档

> 创建时间：2026-06-12  
> 项目名称：SignalDigest  
> 首期产品线：SignalDigest for App Reviews  
> 首期目标：面向 App 团队、独立开发者、ASO / App 增长顾问，做 App Store / Google Play 评论变化监控与每周行动摘要。  
> 后续扩展：在 App 评论分析验证付费后，再扩展到 YouTube / TikTok / B 站等视频站评论分析。

---

## 0. 一句话说明

SignalDigest 是一个开源的 App 评论信号周报系统。

用户输入自己的 App Store / Google Play 链接，再输入 1-3 个竞品 App 链接，系统定期采集评论，识别新增投诉、正向反馈、评分变化、版本影响和竞品动向，并生成一份 `What changed?` 周报，告诉用户下一步应该优先修什么、验证什么、关注什么。

第一版不做复杂 dashboard，主交付物是一封高质量周报。

---

## 1. 为什么首期先做 App 评论分析

我们讨论过两个方向：

1. App 评论分析。
2. 视频站评论分析。

首期推荐先做 App 评论分析，原因如下。

### 1.1 付费用户更清晰

App 团队天然关心评分、留存、发版质量、竞品评论和用户投诉。这些问题能直接影响收入、转化和排名。

用户能快速理解这个价值：

> 每周告诉我用户最近在抱怨什么、竞品哪里被夸、下个版本该优先修什么。

视频站评论分析的用户更分散：个人创作者、MCN、品牌、带货团队、内容运营团队的目标不同，有人要选题，有人要舆情，有人要转化，有人要粉丝画像。第一版容易做散。

### 1.2 数据结构更标准

App Store / Google Play 评论天然包含结构化字段：

```text
app_id / package_name
rating
review title
review body
country
language
app version
review_created_at
```

这比视频评论更适合做趋势、变化检测、低分告警、版本影响和竞品对比。

### 1.3 MVP 更容易自动化

首期可以从 App Store RSS 和 Google Play 评论抓取开始，先跑通：

```text
采集评论 -> 去重 -> AI 分类 -> 每周报告 -> 邮件发送
```

视频站如果只做 YouTube，容易落入已有 “YouTube sentiment analysis” demo 的红海；如果直接做 TikTok / 小红书 / 抖音，又会被采集难度和风控拖住。

### 1.4 竞品关系更稳定

App 的竞品通常是稳定对象，用户可以明确输入 1-3 个竞品 App 并长期跟踪。

视频账号的“竞品”更复杂：品类竞品、选题竞品、人设竞品、带货竞品可能完全不同，报告口径更难统一。

### 1.5 已有商机证据更强

Pain Spotter 数据库里的原始商机是 `App review change-monitoring SaaS`：

- 综合评分：87
- 痛点强度：9
- 付费意愿：8
- 推荐：Build

视频站评论分析是从这个商机外推出来的第二方向，不是最初的强信号。

---

## 2. 产品定位

### 2.1 首期定位

SignalDigest for App Reviews 是一个 App 评论变化监控和周报工具。

它不是简单的情绪分析 dashboard，而是回答：

```text
这周和上周相比，用户反馈发生了什么重要变化？
这些变化对产品、发版、评分和竞品意味着什么？
下一步最应该做哪 3 件事？
```

### 2.2 核心卖点

不要卖：

```text
AI 评论分析
评论情绪 dashboard
自动摘要工具
```

要卖：

```text
不用人工翻评论，也不会错过重要变化。
每周直接告诉你该修什么、该关注什么、竞品哪里变强了。
```

### 2.3 首期目标用户

优先用户：

- 独立 App 开发者。
- 小型移动 App 团队。
- 移动 SaaS / 订阅制 App 团队。
- ASO / App 增长顾问。
- App agency。

强筛选条件：

```text
每月 >= 20 条新评论
有订阅、内购、广告或其他收入
至少有 1-3 个明确竞品
最近 1-2 个月有发版
创始人、PM 或增长负责人会亲自看用户反馈
```

暂不优先：

- 评论极少的早期 App。
- 纯免费、无商业化目标的 App。
- 大企业复杂采购客户。
- 需要所有国家、所有语言、所有平台完整覆盖的高要求客户。

---

## 3. MVP 范围

### 3.1 MVP 必须做

MVP 只做一条完整闭环：

1. 用户添加自己的 App Store / Google Play 链接。
2. 用户添加 1-3 个竞品 App 链接。
3. 系统定期采集最近评论。
4. 系统按周对比当前周期与上一周期。
5. LLM 生成 `What changed?` 周报。
6. 报告通过邮件发送。
7. 用户可在网页或 Notion 查看报告详情和证据评论。

### 3.2 MVP 报告内容

每周报告固定包含：

- 本周一句话摘要。
- 新增或变多的投诉主题。
- 新增或变多的正向反馈。
- 评分变化与低分评论原因。
- 发版后异常反馈。
- 竞品新增被夸 / 被骂主题。
- 下个版本建议优先处理的 3 件事。
- 每个结论背后的证据评论。
- 低样本量或低置信度提示。

### 3.3 MVP 不做

- 不做复杂实时 dashboard。
- 不做多团队权限。
- 不做所有国家全量覆盖。
- 不做复杂 BI 图表。
- 不做自动回复评论。
- 不做移动端 App。
- 不做视频站评论分析。
- 不做 App Store Connect / Google Play Console 官方授权的完整接入。

### 3.4 Dashboard 的角色

Dashboard 不是第一版核心。

第一版 dashboard 只作为 drill-down：

- 查看已监控 App。
- 查看最近评论。
- 查看周报历史。
- 点击 AI 结论查看证据评论。

主交付物仍然是邮件周报。

---

## 4. 数据采集方案

### 4.1 首期采集策略

| 平台 | 自己 App | 竞品 App | MVP 策略 |
|---|---|---|---|
| App Store | 公开 RSS / App Store Connect API | 公开 RSS | 先用 RSS |
| Google Play | Google Play Developer API / 第三方抓取 | 第三方抓取 | 先用第三方或 best-effort 抓取 |

### 4.2 App Store RSS

App Store 公开 RSS 是首期最快路径。

URL 形式：

```text
https://itunes.apple.com/{country}/rss/customerreviews/page=1/id={app_id}/sortby=mostrecent/json
```

示例：

```text
https://itunes.apple.com/us/rss/customerreviews/page=1/id=123456789/sortby=mostrecent/json
```

优点：

- 无需用户授权。
- 可采集竞品公开评论。
- 适合低成本 MVP。

缺点：

- 按国家分散。
- 稳定性弱于官方 API。
- 可能存在分页、延迟和地区覆盖限制。

首期决策：

- 默认抓 `us`。
- 支持配置国家列表，如 `us,gb,ca,au,jp`。
- 每天抓一次，按 review_id 去重。

### 4.3 App Store Connect API

官方 API 适合后续增强，用于采集用户自己的 App。

接口：

```text
GET /v1/customerReviews?filter[app]=APP_ID&sort=-createdAt&include=responses
```

限制：

- 需要 App Store Connect API Key。
- 只能读取用户账号名下的 App。
- 不能读取竞品。

首期不强制接入，作为 P1/P2 高稳定数据源。

### 4.4 Google Play 评论

官方 Google Play Developer API：

```text
GET https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{packageName}/reviews
```

支持参数：

```text
maxResults=100
token=nextPageToken
translationLanguage=en
```

认证 scope：

```text
https://www.googleapis.com/auth/androidpublisher
```

限制：

- 只能读取自己开发者账号下的 App。
- 不能读取竞品。

首期建议：

- 开源版提供 `google-play-scraper` 或第三方数据源适配器。
- 商业托管版可接 Apify / 第三方 Review API。
- 官方 API 作为已付费用户的高稳定选项。

### 4.5 采集频率

默认：

```text
普通监控：每天 1 次
发版窗口：每天 2-4 次
周报生成：每周 1 次
```

发版窗口定义：

```text
release_date 后 7 天
```

发版窗口内提高采集频率和告警敏感度。

---

## 5. 系统架构

### 5.1 总体架构

```text
┌────────────────────┐
│ Frontend / Admin UI │
└─────────┬──────────┘
          │
┌─────────▼──────────┐
│ FastAPI Backend     │
│ - apps              │
│ - competitors       │
│ - reviews           │
│ - digests           │
└─────────┬──────────┘
          │
┌─────────▼──────────┐
│ Scheduler / Workers │
│ - ingestion         │
│ - dedup             │
│ - analysis          │
│ - digest generation │
│ - email delivery    │
└─────────┬──────────┘
          │
┌─────────▼──────────┐
│ Data Stores         │
│ - SQLite/Postgres   │
│ - optional Notion   │
└────────────────────┘
```

### 5.2 技术栈建议

沿用当前项目的技术路线：

- 后端：FastAPI + SQLModel。
- 数据库：SQLite 开发，PostgreSQL 生产。
- 调度：APScheduler。
- LLM：LiteLLM，支持 OpenAI / Claude / DeepSeek / Gemini。
- 邮件：Resend / Postmark / SMTP。
- 前端：Next.js。
- 可选人工工作台：Notion。
- 可选采集外包：Apify / 第三方 Review API。

### 5.3 模块划分

```text
signaldigest/
├── data-service/
│   └── app/
│       ├── api/
│       │   ├── monitored_apps.py
│       │   ├── app_reviews.py
│       │   ├── digest_reports.py
│       │   └── billing.py
│       ├── models/
│       │   ├── monitored_app.py
│       │   ├── app_review.py
│       │   ├── digest_report.py
│       │   └── digest_delivery.py
│       ├── services/
│       │   ├── ingestion/
│       │   │   ├── base.py
│       │   │   ├── app_store_rss.py
│       │   │   ├── app_store_connect.py
│       │   │   ├── google_play.py
│       │   │   └── apify_adapter.py
│       │   ├── review_normalizer.py
│       │   ├── review_classifier.py
│       │   ├── change_detector.py
│       │   ├── digest_generator.py
│       │   ├── digest_delivery.py
│       │   └── notion_exporter.py
│       └── prompts/
│           └── app_review_digest.py
└── frontend/
    └── app/
        ├── monitor/
        ├── reports/
        └── settings/
```

---

## 6. 数据模型

### 6.1 MonitoredApp

```text
MonitoredApp
  id: int
  owner_email: str | None
  name: str
  app_store_id: str | None
  google_play_package: str | None
  app_store_url: str | None
  google_play_url: str | None
  country_codes: list[str]
  status: str               # active | paused | error
  last_ingested_at: datetime | None
  created_at / updated_at
```

### 6.2 CompetitorApp

```text
CompetitorApp
  id: int
  monitored_app_id: int
  name: str
  app_store_id: str | None
  google_play_package: str | None
  app_store_url: str | None
  google_play_url: str | None
  created_at / updated_at
```

### 6.3 AppReview

```text
AppReview
  id: int
  monitored_app_id: int | None
  competitor_app_id: int | None
  source_kind: str           # own | competitor
  platform: str              # app_store | google_play
  external_review_id: str
  rating: int | None
  title: str | None
  body: str
  author_hash: str | None
  country: str | None
  language: str | None
  app_version: str | None
  source_created_at: datetime
  fetched_at: datetime
  raw_payload: JSON | None
```

唯一键：

```text
platform + external_review_id
```

如果平台没有稳定 review_id：

```text
sha256(platform + app_identifier + body + source_created_at)
```

### 6.4 ReviewInsight

```text
ReviewInsight
  id: int
  review_id: int
  sentiment: str             # positive | neutral | negative | urgent
  intent: str                # bug | feature_request | pricing | usability | praise | competitor_comparison | other
  feature_area: str | None
  priority: str              # P0 | P1 | P2 | P3 | none
  summary: str | None
  created_at
```

### 6.5 DigestReport

```text
DigestReport
  id: int
  monitored_app_id: int
  period_start: datetime
  period_end: datetime
  status: str                # draft | needs_review | approved | sent | failed
  title: str
  summary: str
  sections: JSON
  evidence_review_ids: JSON
  llm_model: str
  tokens_used: int
  notion_page_url: str | None
  sent_at: datetime | None
  created_at / updated_at
```

`sections` 固定结构：

```json
{
  "top_changes": [],
  "new_complaints": [],
  "new_praise": [],
  "rating_movement": [],
  "release_impact": [],
  "competitor_moves": [],
  "recommended_actions": [],
  "confidence_notes": []
}
```

---

## 7. 核心流程

### 7.1 Onboarding

```text
用户输入自己的 App URL
  -> 解析 app_store_id / google_play_package
  -> 用户添加 1-3 个竞品 URL
  -> 系统抓最近评论做 baseline
  -> 生成第一份样例报告
  -> 引导用户订阅或进入 4 周试点
```

### 7.2 每日采集

```text
每天：
  读取 active MonitoredApp
  采集 own app 评论
  采集 competitor app 评论
  标准化字段
  按 external_review_id 去重
  写入 AppReview
  调轻量分类器或 LLM 做 ReviewInsight
```

### 7.3 每周报告

```text
每周：
  current_window = 最近 7 天评论
  previous_window = 上一个 7 天评论
  聚合主题、评分、情绪、竞品变化
  找出变化最大的主题
  组装 evidence
  调 LLM 生成 digest JSON
  保存 DigestReport
  可选写入 Notion
  人工审核后发送邮件
```

### 7.4 发版窗口

用户可以手动输入 release date，或后续通过 App Store / Google Play 版本信息自动识别。

发版后 7 天：

- 提高采集频率。
- 提高低分评论优先级。
- 报告中增加 `Release impact` 段。
- 如果评分明显下降或同类投诉激增，触发告警。

---

## 8. Notion 在 MVP 中的角色

Notion 不作为正式数据库，而作为轻量后台和人工审核工作台。

推荐分工：

```text
SQLite/PostgreSQL：存原始评论、去重、历史数据、报告 JSON
Notion：存精选高优先级评论、周报页面、客户状态、人工审核结果
```

### 8.1 Notion Database

建议建立：

```text
Apps
High Priority Reviews
Weekly Reports
Customers
```

### 8.2 写入 Notion 的内容

不要把所有原始评论都写进 Notion。

只写：

- P0/P1 评论。
- 每周报告。
- 需要人工确认的 AI 结论。
- 客户试点状态。

### 8.3 周报审核流程

```text
DigestReport.status = draft
  -> 导出到 Notion Weekly Reports
  -> 人工审核并改成 Approved
  -> 程序扫描 Approved
  -> 发送邮件
  -> status = sent
```

这样可以在没有完整 admin 后台的情况下，快速支持人工交付。

---

## 9. LLM 报告生成

### 9.1 报告原则

LLM 不是为了写长文，而是为了辅助决策。

每条结论必须回答：

- 发生了什么变化？
- 为什么重要？
- 证据是什么？
- 下一步做什么？
- 置信度如何？

### 9.2 App Review Digest 骨架

```text
1. Executive Summary
2. What changed this week
3. Complaints gaining momentum
4. Praise gaining momentum
5. Rating and sentiment movement
6. Release impact
7. Competitor movement
8. Recommended actions
9. Evidence and confidence notes
```

### 9.3 Prompt 约束

输出 JSON：

```json
{
  "title": "",
  "summary": "",
  "top_changes": [],
  "new_complaints": [],
  "new_praise": [],
  "rating_movement": [],
  "release_impact": [],
  "competitor_moves": [],
  "recommended_actions": [],
  "confidence_notes": []
}
```

硬约束：

- 不夸大低样本数据。
- 不编造不存在的竞品变化。
- 每个 insight 必须绑定 evidence review ids。
- 如果评论量太少，明确输出 `confidence low`。
- recommended actions 必须具体到产品、支持、增长或 ASO 动作。

### 9.4 成本控制

- 每个 App 每周只生成 1 份完整报告。
- 每日分类可以用便宜模型或规则。
- 先聚类和抽样，再喂给 LLM。
- 保存中间结果，避免重复生成。

---

## 10. API 设计

### 10.1 Apps

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/apps` | 监控 App 列表 |
| POST | `/api/apps` | 添加自己的 App |
| GET | `/api/apps/{id}` | App 详情 |
| PATCH | `/api/apps/{id}` | 修改配置 |
| POST | `/api/apps/{id}/ingest` | 手动触发采集 |

### 10.2 Competitors

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/apps/{id}/competitors` | 竞品列表 |
| POST | `/api/apps/{id}/competitors` | 添加竞品 App |
| DELETE | `/api/competitors/{id}` | 删除竞品 |

### 10.3 Reviews

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/reviews?app_id=` | 评论列表 |
| GET | `/api/reviews/stats?app_id=` | 评论统计 |
| GET | `/api/reviews/urgent?app_id=` | 高优先级评论 |

### 10.4 Digests

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/digests` | 周报列表 |
| GET | `/api/digests/{id}` | 周报详情 |
| POST | `/api/digests/generate` | 手动生成周报 |
| POST | `/api/digests/{id}/send` | 手动发送周报 |

---

## 11. 前端页面

### 11.1 MVP 页面

| 页面 | 说明 |
|---|---|
| `/monitor/new` | 添加自己的 App 和竞品 |
| `/monitor` | 已监控 App 列表 |
| `/monitor/{id}` | App 详情、采集状态、评论趋势 |
| `/reports` | 周报列表 |
| `/reports/{id}` | 周报详情和证据评论 |
| `/settings/billing` | 订阅和用量 |

### 11.2 周报详情页

周报详情页应像邮件，不像 BI 面板：

- 顶部一句话摘要。
- 3-5 个最重要变化。
- 每个变化配证据评论。
- 明确下一步行动。
- 低置信度提示。
- 可导出 Markdown / PDF。

---

## 12. 获客与付费验证

### 12.1 不先大规模投放

第一阶段目标不是注册量，而是确认：

- 谁真痛。
- 痛到什么程度。
- 是否愿意付费。
- 报告是否会被打开、回复、转发。

### 12.2 手工获客

渠道：

- Reddit：`r/indiehackers`、`r/SaaS`、`r/iOSProgramming`、`r/androiddev`。
- Indie Hackers。
- Product Hunt 新发布 App。
- App Store / Google Play 中评分 3.5-4.5 且评论增长中的 App。
- ASO / App marketing agency。

私信话术：

```text
我在做一个 App 评论变化监控服务。
可以免费帮你做一份过去 30 天 App Store / Google Play 评论变化报告：

- 新增投诉
- 用户最近开始夸什么
- 竞品最近被夸/被骂什么
- 你下个版本优先修什么

如果这份报告有用，再聊是否每周持续做。
```

### 12.3 付费验证漏斗

```text
20 个免费报告
-> 8 个认真反馈
-> 5 个愿意试点
-> 3 个付费试点
-> 1-2 个转月订阅
```

如果达不到这个漏斗，不建议继续扩大开发范围。

### 12.4 试点定价

先卖服务，再自动化：

- `$29`：一次 App 评论变化报告。
- `$29`：4 周试点，1 个 App + 3 个竞品。
- `$19/月`：1 个 App + 3 个竞品 + 每周摘要。
- `$49/月`：3 个 App + 8 个竞品 + 发版告警 + 证据追溯。
- `$99-$299/月`：Agency 多 App 监控和白标报告。

---

## 13. 商业化路径

### 13.1 开源版

开源版提供：

- 自部署。
- 单用户/小团队。
- App Store RSS adapter。
- Google Play best-effort adapter。
- SQLite/PostgreSQL。
- 基础 AI 周报。
- 邮件发送。
- Notion 导出。

### 13.2 商业托管版

商业版提供：

- 免部署托管。
- 更稳定的数据源。
- App Store Connect / Google Play Console 官方授权。
- 更多国家和语言覆盖。
- 多 App / 多团队。
- Slack / 飞书 / Notion 集成。
- 发版窗口告警。
- PDF / 白标报告。
- Agency 多客户管理。

### 13.3 关键付费触发点

- 添加竞品。
- 开启每周 digest。
- 查看证据评论。
- 添加多个 App。
- 开启发版后告警。
- 导出 PDF / 白标报告。
- 接入 Slack / 飞书。

---

## 14. 和现有开源项目的差异

调研过的相近项目包括：

- `Ed321-max/n8n-app-feedback-monitoring`
- `a9181873/App_review_monitoring`
- `Shrinet82/audiencepulse`
- `Faizan-Khan12/Review-Intelligence`
- 多个 YouTube comment sentiment analysis demo

SignalDigest 的差异：

- 专注 `What changed?`，不是静态情绪分析。
- 周报优先，不是 dashboard 优先。
- 自己 App + 竞品 App 持续对比。
- 每个结论绑定证据评论。
- 把发版影响作为核心场景。
- 首期只做 App review，避免产品发散。
- 后续可复用架构扩展到视频站评论分析。

可借鉴：

- 从 n8n 项目借鉴 Notion 工作流、低分告警、weekly report。
- 从 App_review_monitoring 借鉴 App Store RSS + App Store Connect API 双路线、Docker + cron、Email/Teams 通知。
- 从 `Shrinet82/audiencepulse` 借鉴后续创作者方向的 Trust Score、Brand Safety、Campaign Workspace、PDF 报告。
- 从 Amazon Review Intelligence 借鉴 FastAPI + Next.js + export 的产品化结构。

---

## 15. 合规与风险

### 15.1 数据合规原则

- 优先采集公开评论或用户授权账号下的数据。
- 不存储可识别个人信息，作者名默认 hash。
- 报告中展示必要证据，避免大规模公开转载评论原文。
- 对 best-effort 抓取的数据源标注稳定性和 ToS 风险。
- 用户可删除 App，同时删除相关评论和报告。

### 15.2 产品风险

- 低评论量导致洞察不稳定。
- Google Play 竞品评论采集稳定性不足。
- LLM 可能过度推断。
- 用户觉得报告有趣但不改变行动。
- 报告如果没有行动建议，留存会差。

### 15.3 风险应对

- 评论量低时输出 confidence warning。
- 每条结论绑定 evidence review ids。
- 报告限制在 3-5 个重点变化，不堆信息。
- 第一批报告人工复核。
- 先收费验证，再大规模自动化。

---

## 16. 路线图

### Phase 0：手工验证

目标：确认用户愿意为报告付费。

- 找 50 个潜在 App 客户。
- 做 10-20 份免费报告。
- 收 3 个付费试点。
- 验证打开率、回复率、转发率。

### Phase 1：App Store MVP

目标：跑通 App Store 评论周报闭环。

- App URL 解析。
- App Store RSS 采集。
- 竞品 App 配置。
- 评论去重入库。
- AI 分类。
- 每周 digest。
- 邮件发送。
- Notion 审核导出。

### Phase 2：Google Play 支持

目标：提高 Android 覆盖。

- Google Play best-effort adapter。
- 第三方数据源 / Apify adapter。
- Google Play Developer API 官方授权预研。

### Phase 3：产品化

目标：从验证工具变成可收费 SaaS。

- 前端 onboarding。
- 周报详情页。
- Stripe 订阅。
- 多 App 监控。
- 发版窗口告警。
- PDF / Markdown 导出。

### Phase 4：视频站评论分析

目标：在 App 评论方向验证后，复用同一架构扩展。

- YouTube channel / video adapter。
- 视频评论周报。
- 竞品账号选题变化。
- MCN 多账号报告。
- Trust Score / Brand Safety。

---

## 17. 成功指标

### 17.1 产品指标

- 周报打开率 >= 60%。
- 报告证据点击率 >= 30%。
- 用户回复率 >= 20%。
- 30 天留存 >= 50%。
- 每份报告生成成本可控。

### 17.2 付费指标

- 20 份免费报告中至少 3 个付费试点。
- 付费试点中至少 1-2 个转月订阅。
- 首批用户可接受 `$19-$49/月`。
- Agency 用户可接受 `$99-$299/月`。

### 17.3 开源指标

- 1 周内可本地启动。
- App Store RSS adapter 可独立运行。
- 新数据源 adapter 可在 1 天内接入。
- 文档能让开发者独立完成部署。
- 有真实 demo 报告可查看。

---

## 18. 决策总结

首期只做 App 评论分析，不做视频站评论分析。

项目名使用 `SignalDigest`，但产品线明确为：

```text
SignalDigest for App Reviews
```

架构上保留未来扩展能力：

```text
source_type = app | creator
platform = app_store | google_play | youtube | tiktok
```

但首期只启用：

```text
source_type = app
platform = app_store | google_play
```

核心判断：

> 评论数据本身不值钱，用户愿意付费的是：不用人工读评论，也不会错过重要变化，并且知道下一步做什么。

