# SignalDigest

> [English](README.md) | **简体中文**

> 一句话：开源的 **App 评论信号周报系统**。用户输入自己的 App Store / Google Play 链接与 1-3 个竞品链接，系统定期采集评论，识别投诉、好评、评分变化、发版影响与竞品动向，并生成 **What changed?** 周报，告诉用户下一步该优先修什么、关注什么。

首期产品线：**SignalDigest for App Reviews**。主交付物是一封高质量周报，而不是复杂 dashboard。

完整设计见 [`doc/signaldigest-open-source-design-20260612.md`](doc/signaldigest-open-source-design-20260612.md)。

---

## 项目说明

**SignalDigest 是一个面向「App 评论变化监控与周报」方向的框架型项目**，不是开箱即用的商业成品。

它提供可运行的脚手架：后端流水线（采集 → 分类 → 对比 → LLM 周报 → 审核 → 邮件）、管理后台、以及可扩展的数据源适配接口。**后续功能会逐步迭代**，部分模块目前是桩实现或 MVP 质量。

可用于自部署、学习架构，或作为二次开发的起点。

**有定制化需求（私有部署、额外数据源、品牌报告、系统集成等）？** 联系：[paininsight40@outlook.com](mailto:paininsight40@outlook.com)

---

## 1. 当前状态

**Phase 1（App Store MVP）框架** 已搭好并在持续完善：

- 后端：双平台采集、规则 + LLM 分类、评论重点、周报生成、邮件投递、调度器、运行配置 API（持久化到 `.env`）。
- 前端：Next.js 管理后台（监控 / 评论 / 周报审核发送 / 设置页）。详见 [`frontend/README.md`](frontend/README.md)。
- 桩实现或尚未生产就绪：App Store Connect、Apify、Notion 导出（设置页已可配）、Alembic 迁移、计费。

> 本仓库会**逐步更新**，欢迎 Star / Watch 关注该方向进展。

---

## 2. 项目结构

```text
signal-digest/
├── README.md                 # 英文文档（默认）
├── README.zh-CN.md           # 本文件：中文说明
├── doc/                      # 设计文档
├── backend/                  # 后端（对应设计文档第 5.3 的 data-service）
│   ├── pyproject.toml        # uv 管理的依赖
│   ├── .env.example          # 环境变量样例
│   └── app/
│       ├── main.py           # FastAPI 入口 + lifespan（建表 / 启动调度）
│       ├── config.py         # pydantic-settings 配置
│       ├── db.py             # 引擎 / 会话 / 建表
│       ├── core/logging.py   # 统一日志
│       ├── models/           # SQLModel 数据模型（第 6 章）
│       ├── schemas/          # API 请求 / 响应模型
│       ├── api/              # 路由：apps / competitors / reviews / digests（第 10 章）
│       ├── services/         # 业务服务
│       │   ├── ingestion/    # 采集适配器（base + app_store_rss + 其余桩 + registry）
│       │   ├── url_parser.py
│       │   ├── review_normalizer.py
│       │   ├── review_classifier.py
│       │   ├── change_detector.py
│       │   ├── digest_generator.py
│       │   ├── digest_delivery.py
│       │   └── notion_exporter.py
│       ├── prompts/          # LLM Prompt（第 9 章）
│       └── scheduler/        # APScheduler 定时任务
└── frontend/                 # Next.js 管理后台（App Router + TS + Tailwind）
    ├── app/                  # 概览 / monitor / reports / settings
    ├── components/           # UI 基础组件 + 侧边导航 + App 详情标签页
    └── lib/                  # api client / 类型 / hooks / 格式化
```

> 命名说明：设计文档第 5.3 称后端为 `data-service`，因其实际承载 API + 调度 + LLM + 邮件，本仓库改用更直观的 `backend/`。

---

## 3. 技术栈

| 层 | 选型 |
|---|---|
| 后端框架 | FastAPI + SQLModel |
| 数据库 | SQLite（开发）/ PostgreSQL（生产）|
| 调度 | APScheduler（内嵌后台调度）|
| LLM | LiteLLM（OpenAI / Claude / DeepSeek / Gemini 通用）|
| 邮件 | SMTP / Resend / console |
| 采集 | App Store RSS + Google Play；外网代理在设置页配置（采集与 LLM 共用）|
| 包管理 | uv |
| 前端 | Next.js 16（App Router + TypeScript + Tailwind）|

---

## 4. 快速开始

前置：[uv](https://docs.astral.sh/uv/) 与 Node.js 18+。命令在 PowerShell 下执行。

### 后端

```powershell
cd backend
copy .env.example .env
# .env 仅保留数据库、跨域等基础设施；LLM / 邮件 / Notion / 代理 / 调度在管理后台「设置」页配置
uv sync
uv run uvicorn app.main:app --reload
```

- 健康检查：http://127.0.0.1:8000/health
- Swagger 文档：http://127.0.0.1:8000/docs
- **外网代理**：**设置 → 采集与网络**（留空=直连）。采集、App 搜索与 **LLM 调用**共用；支持 `socks5://127.0.0.1:12080` 或带认证 URL，可先点 **测试连通性** 再保存。

### 前端（管理后台）

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

- 管理后台：http://localhost:3000

### 最小闭环体验

1. 在管理后台 **监控 → 添加** 按 App 名称搜索并点选（或 API）：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/apps/search?q=Notion&country=us"

Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/apps -ContentType 'application/json' -Body '{"name":"Demo","app_store_id":"389801252","google_play_package":"notion.id","country_codes":["us"]}'
```

在 **设置页** 配置 LLM API Key、周报收件邮箱、Notion、默认国家/超时、外网代理、调度等（保存后写入 `backend/.env` 管理段）。

2. 采集评论：`POST /api/apps/{id}/ingest`（不阻塞 LLM，避免超时）
3. 补跑分类：`POST /api/apps/{id}/classify` 或详情页 **补跑分类**（规则分类立即返回；好评/差评深度分析后台按批执行）
4. 生成周报：`POST /api/digests/generate?app_id={id}`（需设置页配置 LLM）
5. 查看周报：`GET /api/digests?app_id={id}`；**评论重点** 在 enrich 完成后刷新可见

---

## 5. API 一览（第 10 章）

| 模块 | 方法 | 路径 |
|---|---|---|
| Apps | GET | `/api/apps/search?q=` |
| Apps | GET / POST | `/api/apps` |
| Apps | GET / PATCH | `/api/apps/{id}` |
| Apps | POST | `/api/apps/{id}/ingest` |
| Apps | POST | `/api/apps/{id}/classify` |
| Competitors | GET / POST | `/api/apps/{id}/competitors` |
| Competitors | DELETE | `/api/competitors/{id}` |
| Reviews | GET | `/api/reviews?app_id=&platform=` |
| Reviews | GET | `/api/reviews/stats?app_id=&platform=` |
| Reviews | GET | `/api/reviews/urgent?app_id=&platform=` |
| Reviews | GET | `/api/reviews/highlights?app_id=&platform=` |
| Digests | GET | `/api/digests` / `/api/digests/{id}` |
| Digests | PATCH | `/api/digests/{id}`（status/title/summary；支持审核流转）|
| Digests | POST | `/api/digests/generate` / `/api/digests/{id}/send` |
| Settings | GET / PATCH | `/api/settings`（LLM / 邮件 / Notion / 采集 / 代理 / 调度 → `.env`）|
| Settings | POST | `/api/settings/proxy-test`（代理连通性测试，无需先保存）|

**`.env` 约定：** `.env.example` 仅含基础设施（数据库、跨域等）；业务配置均在 **设置页** 维护，保存后自动写入 `.env`。

前端跨域由 `.env` 的 `CORS_ORIGINS` 控制，默认放行 `http://localhost:3000`。

---

## 6. 核心数据流

```text
采集评论 -> 标准化去重入库 -> 分类(ReviewInsight) -> 周期对比 -> LLM 生成周报 -> 人工审核 -> 邮件发送
```

- 采集：`services/ingestion/*`（统一 `ReviewIngestor` 接口，新数据源 1 天可接入）
- 入库去重：`platform + external_review_id`（无稳定 id 时用 sha256 兜底）
- 周报：`DigestReport.sections` 为固定 JSON 结构，每条结论绑定 evidence review ids
- 审核：`status` 走 `draft -> approved -> sent`，仅 approved 才发送

---

## 7. 后续功能开发计划

本框架的迭代路线图（优先级可能调整，已完成项以 git 历史为准）。

### Phase 1 — App Store MVP 框架 *(主体已完成，持续打磨)*

| 功能 | 状态 | 说明 |
|---|---|---|
| App Store RSS 采集 | 已完成 | 默认 `us`，可配置多国家 |
| 评论标准化与去重 | 已完成 | `platform + external_review_id` |
| LLM 分类 + 规则降级 | 已完成 | LiteLLM 批量 + 成本控制 |
| 周环比变化检测 | 已完成 | 输入周报生成 |
| LLM 周报（固定 JSON sections）| 已完成 | 每条结论绑定证据 review id |
| 邮件投递（SMTP / Resend / console）| 已完成 | 仅 `approved` 可发送 |
| 周报审核流（draft → sent）| 已完成 | 管理后台 + 状态流转校验 |
| 定时调度（每日采集 / 每周周报）| 已完成 | 设置页可配置并热重载 |
| 管理后台（监控 / 周报 / 设置）| 已完成 | Next.js + 图标化审核操作 |
| Alembic 数据库迁移 | 计划中 | 替代 `create_all`，便于生产 |

### Phase 2 — 覆盖范围与数据可靠性

| 功能 | 状态 | 说明 |
|---|---|---|
| Google Play 采集器 | 已完成 | `google-play-scraper`；双平台并行采集 |
| App Store Connect API（自有 App）| 计划中 | 提高稳定性 |
| Google Play Developer API（自有 App）| 计划中 | 官方授权路径 |
| Apify / 第三方 Review API | 计划中 | 桩位于 `ingestion/apify_adapter.py` |
| 竞品评论采集闭环 | 计划中 | 调度任务接入竞品 App |
| Notion 导出（人工审核台）| 进行中 | 设置页可配 Integration；`notion_exporter.py` + 导出 API 已有 |
| 多国家采集策略优化 | 计划中 | 默认策略与配额控制 |

### Phase 3 — 产品化与运维

| 功能 | 状态 | 说明 |
|---|---|---|
| 用户注册 / 登录 / 多租户 | 计划中 | 团队与权限 |
| Stripe 订阅与套餐 | 计划中 | 见设计文档定价 |
| 发版窗口告警 | 计划中 | 发版后提高采集频率 |
| PDF / 白标报告导出 | 计划中 | Agency 场景 |
| Slack / 飞书 / Webhook 通知 | 计划中 | 邮件之外的通知通道 |
| 可观测性（指标、任务面板）| 计划中 | 采集 / 周报失败告警 |
| Docker Compose 与部署文档 | 计划中 | 一键自部署 |

### Phase 4 — 平台扩展 *(架构已预留)*

| 功能 | 状态 | 说明 |
|---|---|---|
| YouTube / TikTok / B 站评论周报 | 计划中 | 复用 `source_type=creator` |
| Agency 多客户工作区 | 计划中 | 多 App、多收件人 |
| Trust Score / 品牌安全信号 | 计划中 | 参考 audiencepulse 思路 |

**定制化开发**（私有部署、额外数据源、品牌报告、系统集成）：[paininsight40@outlook.com](mailto:paininsight40@outlook.com)

---

## 8. 待补齐（近期 TODO）

- [x] LiteLLM 评论分类（批量调用 + 规则降级 + 成本控制）
- [x] 邮件真实投递（SMTP / Resend / console）
- [x] Google Play 采集器（`ingestion/google_play.py`）
- [x] App 名称搜索添加（iTunes + Google Play）
- [x] 全局周报接收邮箱（设置页）
- [x] 评论重点（好评/差评分析分栏）
- [x] Notion 集成配置（设置页：API Key / 数据库 ID）
- [ ] Notion 导出完整流程（`notion_exporter.py`）
- [ ] Alembic 迁移替代 `create_all`
- [x] 前端（Next.js 管理后台：监控 / 评论 / 周报审核与发送）

### 已实现细节

**评论分类（第 6.4 / 9.4）**
- 两阶段：**规则分类**（情绪/优先级，秒级）→ **LLM enrich**（后台线程，按批生成「好在哪里/痛点」）。
- 有效字数 ≥ `CLASSIFIER_MIN_BODY_CHARS`（默认 20）的好评/差评才进入 LLM；过短评论仅规则分类。
- 采集后不自动跑 LLM；请点 **补跑分类**，完成后刷新 **评论重点**。
- LLM 与采集共用设置页中的外网代理。

**邮件投递（第 7.3）**
- `EMAIL_PROVIDER` 支持 `smtp`、`resend`、`console`（本地开发只打日志）。
- 仅 `status=approved` 的周报会真正发送；成功置 `sent`，失败置 `failed`。

---

## 9. 联系方式

| 用途 | 联系 |
|---|---|
| 定制功能、私有部署、系统集成 | [paininsight40@outlook.com](mailto:paininsight40@outlook.com) |
| Bug 与功能建议 | GitHub Issues（仓库公开后）|

欢迎对该框架方向提出反馈；商业或定制项目可通过邮件沟通。
