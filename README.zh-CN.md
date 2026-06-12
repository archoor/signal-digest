# SignalDigest

> [English](README.md) | **简体中文**

> 一句话：开源的 **App 评论信号周报系统**。用户输入自己的 App Store / Google Play 链接与 1-3 个竞品链接，系统定期采集评论，识别投诉、好评、评分变化、发版影响与竞品动向，并生成 **What changed?** 周报，告诉用户下一步该优先修什么、关注什么。

首期产品线：**SignalDigest for App Reviews**。主交付物是一封高质量周报，而不是复杂 dashboard。

完整设计见 [`doc/signaldigest-open-source-design-20260612.md`](doc/signaldigest-open-source-design-20260612.md)。

---

## 1. 当前状态

项目处于 **Phase 1（App Store MVP）脚手架** 阶段：

- 后端架构已初始化，可启动、可建表、可手动采集 App Store RSS 评论、可调 API 生成周报草稿。
- 部分能力为带接口的桩（Google Play 采集、App Store Connect、Apify、Notion 导出），便于按路线图逐步补齐。
- 前端（Next.js）为 Phase 3 内容，当前仅占位。

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
└── frontend/                 # Next.js 前端（Phase 3，当前占位）
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
| 采集 | App Store 公开 RSS（首期）；Google Play / Apify / 官方 API 后续 |
| 包管理 | uv |
| 前端 | Next.js（Phase 3）|

---

## 4. 快速开始（后端）

前置：已安装 [uv](https://docs.astral.sh/uv/)。所有命令在 PowerShell 下执行。

```powershell
cd backend
copy .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

启动后：

- 健康检查：http://127.0.0.1:8000/health
- 交互式 API 文档（Swagger）：http://127.0.0.1:8000/docs

### 最小闭环体验

1. 添加一个监控 App（解析 app_store_id）：

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/apps -ContentType 'application/json' -Body '{"name":"Demo","app_store_url":"https://apps.apple.com/us/app/id389801252","country_codes":["us"]}'
```

2. 手动采集评论：`POST /api/apps/{id}/ingest`（自动分类新评论）
3. 生成周报草稿：`POST /api/digests/generate?app_id={id}`（需配置 `LLM_API_KEY`）
4. 查看周报：`GET /api/digests?app_id={id}`

---

## 5. API 一览（第 10 章）

| 模块 | 方法 | 路径 |
|---|---|---|
| Apps | GET / POST | `/api/apps` |
| Apps | GET / PATCH | `/api/apps/{id}` |
| Apps | POST | `/api/apps/{id}/ingest` |
| Apps | POST | `/api/apps/{id}/classify` |
| Competitors | GET / POST | `/api/apps/{id}/competitors` |
| Competitors | DELETE | `/api/competitors/{id}` |
| Reviews | GET | `/api/reviews?app_id=` |
| Reviews | GET | `/api/reviews/stats?app_id=` |
| Reviews | GET | `/api/reviews/urgent?app_id=` |
| Digests | GET | `/api/digests` / `/api/digests/{id}` |
| Digests | POST | `/api/digests/generate` / `/api/digests/{id}/send` |

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

## 7. 路线图

- **Phase 0**：手工验证付费意愿（做免费报告、收试点）。
- **Phase 1（进行中）**：App Store MVP 闭环。
- **Phase 2**：Google Play 支持（best-effort / 第三方 / 官方 API）。
- **Phase 3**：产品化（前端 onboarding、周报详情页、Stripe、多 App、发版告警、PDF 导出）。
- **Phase 4**：复用架构扩展到视频站评论分析。

---

## 8. 待补齐（TODO）

- [x] LiteLLM 评论分类（批量调用 + 规则降级 + 成本控制）
- [x] 邮件真实投递（SMTP / Resend / console）
- [ ] Google Play 采集器（`ingestion/google_play.py`）
- [ ] Notion 导出（`notion_exporter.py`）
- [ ] Alembic 迁移替代 `create_all`
- [ ] 前端（Next.js）

### 已实现细节

**评论分类（第 6.4 / 9.4）**
- `ENABLE_LLM_CLASSIFICATION=true` 且配置了 `LLM_API_KEY` 时，按 `CLASSIFIER_BATCH_SIZE` 分批调 LiteLLM。
- 未配置 Key 或单批调用失败时，自动降级为基于评分的规则分类。
- 采集后自动分类；也可 `POST /api/apps/{id}/classify` 补跑。

**邮件投递（第 7.3）**
- `EMAIL_PROVIDER` 支持 `smtp`、`resend`、`console`（本地开发只打日志）。
- 仅 `status=approved` 的周报会真正发送；成功置 `sent`，失败置 `failed`。
