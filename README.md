# SignalDigest

> **English** | [简体中文](README.zh-CN.md)

> One-liner: an open-source **App review signal weekly digest** system. Add your App Store / Google Play links plus 1–3 competitor apps; the system ingests reviews on a schedule, detects complaints, praise, rating shifts, release impact, and competitor moves, then delivers a **What changed?** weekly report with prioritized next actions.

First product line: **SignalDigest for App Reviews**. The primary deliverable is a high-quality weekly email—not a complex dashboard.

Full design doc: [`doc/signaldigest-open-source-design-20260612.md`](doc/signaldigest-open-source-design-20260612.md).

---

## About This Project

**SignalDigest is a framework project** for the *App review change-monitoring & weekly digest* direction—not a finished commercial product.

It provides a runnable scaffold: backend pipeline (ingest → classify → diff → LLM digest → review → email), admin UI, and extension points for new data sources. **Features will be added incrementally**; some modules are stubs or MVP-quality by design.

Use it to self-host, learn the architecture, or as a starting point for customization.

**Custom development or enterprise needs?** Contact: [paininsight40@outlook.com](mailto:paininsight40@outlook.com)

---

## 1. Current Status

**Phase 1 (App Store MVP) framework** is in place and evolving:

- Backend: dual-platform ingest (App Store + Google Play), rule + LLM classification, review highlights, digest generation, email delivery, scheduler, runtime settings API (persists to `.env`).
- Frontend: Next.js admin UI (monitor / reviews / digest review & send / runtime settings). See [`frontend/README.md`](frontend/README.md).
- Stubs or not yet production-ready: App Store Connect, Apify, Notion export (config UI ready), Alembic migrations, billing.

> This repo will be **updated step by step**. Star or watch if you follow this direction.

---

## 2. Project Structure

```text
signal-digest/
├── README.md                 # This file (English)
├── README.zh-CN.md           # Chinese documentation
├── doc/                      # Design documents
├── backend/                  # API + scheduler + LLM + email (design doc: data-service)
│   ├── pyproject.toml
│   ├── .env.example
│   └── app/
│       ├── main.py           # FastAPI entry + lifespan (DB init / scheduler)
│       ├── config.py
│       ├── db.py
│       ├── core/logging.py
│       ├── models/           # SQLModel entities (design doc §6)
│       ├── schemas/
│       ├── api/              # apps / competitors / reviews / digests (design doc §10)
│       ├── services/
│       │   ├── ingestion/    # Adapters: app_store_rss + stubs + registry
│       │   ├── review_normalizer.py
│       │   ├── review_classifier.py
│       │   ├── change_detector.py
│       │   ├── digest_generator.py
│       │   ├── digest_delivery.py
│       │   └── notion_exporter.py
│       ├── prompts/
│       └── scheduler/
└── frontend/                 # Next.js admin UI (App Router + TS + Tailwind)
    ├── app/                  # 概览 / monitor / reports / settings
    ├── components/           # UI primitives + Sidebar + monitor tabs
    └── lib/                  # api client / types / hooks / formatters
```

> Naming note: the design doc calls the backend `data-service`; this repo uses `backend/` because it owns API, scheduling, LLM, and email—not just data.

---

## 3. Tech Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + SQLModel |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Scheduler | APScheduler (in-process) |
| LLM | LiteLLM (OpenAI / Claude / DeepSeek / Gemini) |
| Email | SMTP / Resend / console |
| Ingestion | App Store RSS + Google Play (`google-play-scraper`); SOCKS5/HTTP proxy via settings |
| Package manager | uv |
| Frontend | Next.js 16 (App Router + TypeScript + Tailwind) |

---

## 4. Quick Start

Requires [uv](https://docs.astral.sh/uv/) and Node.js 18+. Commands use PowerShell.

### Backend

```powershell
cd backend
copy .env.example .env
# .env keeps infra only (DB, CORS, etc.); configure LLM / email / Notion / proxy / ingest / scheduler in admin Settings
uv sync
uv run uvicorn app.main:app --reload
```

- Health: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs
- **Outbound proxy**: Admin **Settings → Ingest & network** (empty = direct). Used for iTunes/Google Play **and** LiteLLM calls. Test with **Test connectivity** before saving.

### Frontend (admin UI)

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

- Admin UI: http://localhost:3000

### Minimal end-to-end loop

1. Search and add a monitored app by name (admin UI **Monitor → Add**, or API):

```powershell
# Search
Invoke-RestMethod "http://127.0.0.1:8000/api/apps/search?q=Notion&country=us"

# Create with platform IDs (iOS + Android in one monitor)
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/apps -ContentType 'application/json' -Body '{"name":"Demo","app_store_id":"389801252","google_play_package":"notion.id","country_codes":["us"]}'
```

Configure runtime options in **Settings** (LLM API key, weekly recipient email, Notion integration, proxy, ingest defaults, scheduler). Values persist to `backend/.env` under the managed section.

2. Ingest reviews: `POST /api/apps/{id}/ingest` (does not block on LLM; run classify separately)
3. Classify & enrich: `POST /api/apps/{id}/classify` or **Re-run classification** in the UI (rule classify immediately; LLM praise/complaint analysis runs in background)
4. Generate digest: `POST /api/digests/generate?app_id={id}` (requires LLM API key in Settings)
5. View digest: `GET /api/digests?app_id={id}`

---

## 5. API Overview (design doc §10)

| Module | Method | Path |
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
| Digests | PATCH | `/api/digests/{id}` (status/title/summary; review workflow) |
| Digests | POST | `/api/digests/generate` / `/api/digests/{id}/send` |
| Settings | GET / PATCH | `/api/settings` (LLM / email / Notion / ingest / proxy / scheduler → `.env`) |
| Settings | POST | `/api/settings/proxy-test` (test proxy without saving) |

**`.env` layout:** keep only infrastructure keys in `.env.example` (`DATABASE_URL`, `CORS_ORIGINS`, etc.). All business/runtime config is edited in **Settings** and written back to `.env` on save.

CORS for the frontend is controlled by `CORS_ORIGINS` (`.env`), defaulting to `http://localhost:3000`.

---

## 6. Core Data Flow

```text
Ingest → normalize & dedupe → classify (ReviewInsight) → week-over-week diff → LLM digest → review → email
```

- Ingestion: `services/ingestion/*` via `ReviewIngestor` (new source ~1 day to add)
- Dedupe key: `platform + external_review_id` (sha256 fallback when no stable id)
- Digest: fixed JSON `sections` + evidence review ids per insight
- Delivery: only `status=approved` reports are sent

---

## 7. Development Plan

Roadmap for this framework. Items may shift; completed work stays in git history.

### Phase 1 — App Store MVP framework *(mostly done, ongoing polish)*

| Item | Status | Notes |
|---|---|---|
| App Store RSS ingestion | Done | Default `us`; multi-country configurable |
| Review normalize & dedupe | Done | `platform + external_review_id` |
| LLM classification + rule fallback | Done | LiteLLM batch + cost controls |
| Week-over-week change detection | Done | Feeds digest generator |
| LLM weekly digest (JSON sections) | Done | Evidence review ids per insight |
| Email delivery (SMTP / Resend / console) | Done | Only `approved` → send |
| Digest review workflow (draft → sent) | Done | Admin UI + PATCH status rules |
| Scheduler (daily ingest / weekly digest) | Done | Configurable via settings API |
| Admin UI (monitor / reports / settings) | Done | Next.js + icon-based review actions |
| Alembic migrations | Planned | Replace `create_all` for production |

### Phase 2 — Coverage & data reliability

| Item | Status | Notes |
|---|---|---|
| Google Play ingestor | Done | `google-play-scraper`; dual-platform ingest |
| App Store Connect API (own apps) | Planned | Higher stability for customer apps |
| Google Play Developer API (own apps) | Planned | Official auth path |
| Apify / third-party review API adapter | Planned | Stub exists in `ingestion/apify_adapter.py` |
| Competitor review ingest loop | Planned | Wire competitor apps into daily job |
| Notion export for manual review | Planned | Settings UI + `notion_exporter.py`; export API exists |
| Multi-country ingest strategy | Planned | Smarter defaults & quotas |

### Phase 3 — Productization & operations

| Item | Status | Notes |
|---|---|---|
| User onboarding & auth | Planned | Multi-tenant / team accounts |
| Stripe billing & plans | Planned | Per design doc pricing tiers |
| Release-window alerts | Planned | Higher ingest frequency post-release |
| PDF / white-label report export | Planned | Agency use case |
| Slack / Feishu / webhook notifications | Planned | Beyond email |
| Observability (metrics, job dashboard) | Planned | Failed ingest / digest alerts |
| Docker Compose & deploy docs | Planned | One-command self-host |

### Phase 4 — Platform extension *(architecture reserved)*

| Item | Status | Notes |
|---|---|---|
| YouTube / TikTok / Bilibili comment digest | Planned | Reuse `source_type=creator` model |
| Agency multi-client workspace | Planned | Many apps, many recipients |
| Trust score / brand safety signals | Planned | From audiencepulse-style ideas |

**Customization** (private deploy, extra data sources, branded reports, integrations): [paininsight40@outlook.com](mailto:paininsight40@outlook.com)

---

## 8. TODO (near-term)

- [x] LiteLLM review classification (batch + rule fallback + cost control)
- [x] Email delivery (SMTP / Resend / console)
- [x] Frontend (Next.js admin UI: monitor / reviews / digest review & send)
- [x] Google Play ingestor
- [x] App name search onboarding (iTunes + Google Play)
- [x] Global digest recipient email in settings
- [x] Review highlights (praise / complaints with analysis)
- [x] Notion integration settings (API key / database ID; export wiring in progress)
- [ ] Notion export (full workflow)
- [ ] Alembic migrations (replace `create_all`)

### Implemented details

**Classification (§6.4 / §9.4)**  
Two-phase flow: (1) **rule classify** on ingest or via `POST /api/apps/{id}/classify` — sentiment, priority, placeholder summaries for long praise/complaints; (2) **LLM enrich** in a background thread — batch analysis of “what’s good / pain points” for reviews with enough text (`CLASSIFIER_MIN_BODY_CHARS`, default 20). Requires `ENABLE_LLM_CLASSIFICATION` and API key in **Settings**; uses the same outbound proxy as ingest. Review **Highlights** tab shows enriched summaries after refresh.

**Email (§7.3)**  
`EMAIL_PROVIDER`: `smtp` (STARTTLS/SSL), `resend`, or `console` (log-only for local dev). Only `approved` digests are sent; success → `sent`, failure → `failed`. HTML template reads like an email, not a BI dashboard.

---

## 9. Contact

| Purpose | Contact |
|---|---|
| Custom features, private deployment, integrations | [paininsight40@outlook.com](mailto:paininsight40@outlook.com) |
| Bugs & feature requests | GitHub Issues (when published) |

We welcome feedback on this framework direction. Commercial or tailored builds can be discussed via email.
