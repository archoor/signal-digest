# SignalDigest

> **English** | [简体中文](README.zh-CN.md)

> One-liner: an open-source **App review signal weekly digest** system. Add your App Store / Google Play links plus 1–3 competitor apps; the system ingests reviews on a schedule, detects complaints, praise, rating shifts, release impact, and competitor moves, then delivers a **What changed?** weekly report with prioritized next actions.

First product line: **SignalDigest for App Reviews**. The primary deliverable is a high-quality weekly email—not a complex dashboard.

Full design doc: [`doc/signaldigest-open-source-design-20260612.md`](doc/signaldigest-open-source-design-20260612.md).

---

## 1. Current Status

**Phase 1 (App Store MVP)** scaffold is in place:

- Backend runs locally: create tables, ingest App Store RSS reviews, classify, generate digest drafts via API.
- Stubs remain for Google Play ingestion, App Store Connect, Apify, Notion export (roadmap items).
- Frontend (Next.js) is a Phase 3 placeholder.

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
└── frontend/                 # Next.js placeholder (Phase 3)
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
| Ingestion | App Store public RSS (MVP); Google Play / Apify later |
| Package manager | uv |
| Frontend | Next.js (Phase 3) |

---

## 4. Quick Start (Backend)

Requires [uv](https://docs.astral.sh/uv/). Commands below use PowerShell.

```powershell
cd backend
copy .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

After startup:

- Health: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs

### Minimal end-to-end loop

1. Add a monitored app (auto-parses `app_store_id`):

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/apps -ContentType 'application/json' -Body '{"name":"Demo","app_store_url":"https://apps.apple.com/us/app/id389801252","country_codes":["us"]}'
```

2. Ingest reviews: `POST /api/apps/{id}/ingest` (auto-classifies new reviews)
3. Generate digest: `POST /api/digests/generate?app_id={id}` (requires `LLM_API_KEY`)
4. View digest: `GET /api/digests?app_id={id}`

---

## 5. API Overview (design doc §10)

| Module | Method | Path |
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

## 6. Core Data Flow

```text
Ingest → normalize & dedupe → classify (ReviewInsight) → week-over-week diff → LLM digest → review → email
```

- Ingestion: `services/ingestion/*` via `ReviewIngestor` (new source ~1 day to add)
- Dedupe key: `platform + external_review_id` (sha256 fallback when no stable id)
- Digest: fixed JSON `sections` + evidence review ids per insight
- Delivery: only `status=approved` reports are sent

---

## 7. Roadmap

- **Phase 0**: Manual paid validation (free reports → pilots)
- **Phase 1 (in progress)**: App Store MVP loop
- **Phase 2**: Google Play (best-effort / third-party / official API)
- **Phase 3**: Productization (frontend onboarding, Stripe, multi-app, release alerts, PDF)
- **Phase 4**: Reuse architecture for video-platform comment analysis

---

## 8. TODO

- [x] LiteLLM review classification (batch + rule fallback + cost control)
- [x] Email delivery (SMTP / Resend / console)
- [ ] Google Play ingestor
- [ ] Notion export
- [ ] Alembic migrations (replace `create_all`)
- [ ] Frontend (Next.js)

### Implemented details

**Classification (§6.4 / §9.4)**  
When `ENABLE_LLM_CLASSIFICATION=true` and `LLM_API_KEY` is set, reviews are classified in batches via LiteLLM (`sentiment`, `intent`, `feature_area`, `priority`, `summary`). On failure or missing key, rule-based fallback from star ratings keeps the pipeline running. Classification runs after ingest (manual or scheduled) or via `POST /api/apps/{id}/classify`.

**Email (§7.3)**  
`EMAIL_PROVIDER`: `smtp` (STARTTLS/SSL), `resend`, or `console` (log-only for local dev). Only `approved` digests are sent; success → `sent`, failure → `failed`. HTML template reads like an email, not a BI dashboard.
