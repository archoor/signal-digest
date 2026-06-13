# SignalDigest 前端

SignalDigest 的管理后台（设计文档第 11 章）。基于 **Next.js (App Router) + TypeScript + Tailwind CSS v4**，对接后端 FastAPI 的 `/api` 接口，提供 App 监控配置、评论浏览、周报审核与发送等管理能力。

> 主交付物仍是每周邮件周报；本后台用于配置监控、人工审核与触发任务。

## 技术栈

| 项目 | 选择 |
|---|---|
| 框架 | Next.js 16（App Router）|
| 语言 | TypeScript |
| 样式 | Tailwind CSS v4 |
| 数据获取 | 浏览器 `fetch` + 自封装 API client（`lib/api.ts`）|
| 包管理 | npm |

## 快速开始

需要 Node.js 18+（建议 20/22）。命令使用 PowerShell。

```powershell
cd frontend
copy .env.example .env.local   # 配置后端地址，默认 http://127.0.0.1:8000
npm install
npm run dev
```

访问 http://localhost:3000 。

> 前提：后端已启动（见根目录 README）。后端默认放行 `localhost:3000` 跨域；
> 如改了前端端口，请同步后端 `.env` 的 `CORS_ORIGINS`。

### 常用命令

```powershell
npm run dev     # 开发服务器
npm run build   # 生产构建（含类型检查）
npm run start   # 运行生产构建
npm run lint    # ESLint
```

## 环境变量

| 变量 | 说明 | 默认 |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` | 后端 API 基址 | `http://127.0.0.1:8000` |

## 页面

| 路径 | 说明 |
|---|---|
| `/` | 概览：监控数、待审核周报数、最近 App / 周报 |
| `/monitor` | 监控 App 列表 |
| `/monitor/new` | 添加自己的 App + 1-3 个竞品（自动解析 App ID / 包名）|
| `/monitor/[id]` | App 详情：采集 / 分类 / 生成周报；评论、竞品、设置三个标签页 |
| `/reports` | 周报列表（可按 App 过滤）|
| `/reports/[id]` | 周报详情：像邮件一样呈现 + 证据评论 + 审核状态流转 + 发送 + 导出 Markdown |
| `/settings` | 运行配置：LLM / 邮件 / Notion / 采集与网络 / 调度（写入 `backend/.env` 并热重载）|

## 目录结构

```text
frontend/
├── app/
│   ├── layout.tsx          # 根布局 + 侧边导航
│   ├── page.tsx            # 概览
│   ├── monitor/            # App 监控（列表 / 新建 / 详情）
│   ├── reports/            # 周报（列表 / 详情）
│   └── settings/           # 设置 / 用量
├── components/
│   ├── ui.tsx              # 基础 UI（按钮、卡片、徽章、表单等）
│   ├── Sidebar.tsx         # 侧边导航
│   └── monitor/            # App 详情子组件（评论 / 竞品 / 设置）
└── lib/
    ├── api.ts              # 后端 API client（对应设计文档第 10 章）
    ├── types.ts            # 与后端模型 / 枚举对应的 TS 类型
    ├── useApi.ts           # 数据加载 Hook（loading / error / refetch）
    ├── format.ts           # 日期 / 平台等格式化工具
    └── digestMarkdown.ts   # 周报 → Markdown 导出
```

## 管理能力一览

- **App 监控**：新增 App、编辑配置、暂停/恢复、立即采集、补跑分类（规则+后台 LLM enrich）、生成周报。
- **竞品**：每个 App 添加 / 删除 1-3 个竞品（链接自动识别平台）。
- **评论**：最近评论、高优先级（P0/P1）、**评论重点**（好评/差评分栏 + LLM 分析摘要）。
- **周报**：列表与详情、审核状态流转（草稿 → 待审核 → 已审核）、发送邮件（仅「已审核」可发）、导出 Markdown、逐条查看证据评论原文。

## 与后端的对接

所有请求经 `lib/api.ts` 发送：浏览器走同源 `/api`（Next.js rewrite 到后端，避免系统代理拦截 localhost）；SSR 直连 `NEXT_PUBLIC_API_BASE`。
为支持周报审核流转，后端新增了 `PATCH /api/digests/{id}`（更新 status / title / summary）。
