// 与后端 SQLModel / 枚举对应的 TypeScript 类型（设计文档第 6 章）。

export type MonitorStatus = "active" | "paused" | "error";
export type Platform =
  | "app_store"
  | "google_play"
  | "youtube"
  | "tiktok"
  | "bilibili";
export type SourceKind = "own" | "competitor";
export type Sentiment = "positive" | "neutral" | "negative" | "urgent";
export type Intent =
  | "bug"
  | "feature_request"
  | "pricing"
  | "usability"
  | "praise"
  | "competitor_comparison"
  | "other";
export type Priority = "P0" | "P1" | "P2" | "P3" | "none";
export type DigestStatus =
  | "draft"
  | "needs_review"
  | "approved"
  | "sent"
  | "failed";

export interface MonitoredApp {
  id: number;
  name: string;
  owner_email: string | null;
  app_store_id: string | null;
  google_play_package: string | null;
  app_store_url: string | null;
  google_play_url: string | null;
  country_codes: string[];
  status: MonitorStatus;
  last_ingested_at: string | null;
  last_release_date: string | null;
}

export interface MonitoredAppCreate {
  name: string;
  app_store_id?: string | null;
  google_play_package?: string | null;
  app_store_url?: string | null;
  google_play_url?: string | null;
  country_codes?: string[];
}

export interface MonitoredAppUpdate {
  name?: string | null;
  app_store_id?: string | null;
  google_play_package?: string | null;
  app_store_url?: string | null;
  google_play_url?: string | null;
  country_codes?: string[] | null;
  status?: MonitorStatus | null;
  last_release_date?: string | null;
}

export interface AppSearchResult {
  name: string;
  developer: string | null;
  icon_url: string | null;
  app_store_id: string | null;
  app_store_url: string | null;
  google_play_package: string | null;
  google_play_url: string | null;
  platforms: string[];
}

export interface Competitor {
  id: number;
  monitored_app_id: number;
  name: string;
  app_store_id: string | null;
  google_play_package: string | null;
  app_store_url: string | null;
  google_play_url: string | null;
}

export interface CompetitorCreate {
  name: string;
  app_store_id?: string | null;
  google_play_package?: string | null;
  app_store_url?: string | null;
  google_play_url?: string | null;
}

export interface AppReview {
  id: number;
  monitored_app_id: number | null;
  competitor_app_id: number | null;
  source_kind: SourceKind;
  platform: Platform;
  external_review_id: string;
  rating: number | null;
  title: string | null;
  body: string;
  author_hash: string | null;
  country: string | null;
  language: string | null;
  app_version: string | null;
  source_created_at: string;
  fetched_at: string;
  raw_payload: Record<string, unknown> | null;
}

export interface ReviewStats {
  app_id: number;
  total: number;
  avg_rating: number | null;
  by_platform?: Record<
    string,
    { total: number; avg_rating: number | null }
  >;
}

export interface ReviewInsightBrief {
  summary: string | null;
  feature_area: string | null;
  sentiment: Sentiment;
  priority: Priority;
}

export interface ReviewHighlightEntry {
  review: AppReview;
  insight: ReviewInsightBrief;
}

export interface ReviewHighlights {
  praise: ReviewHighlightEntry[];
  complaints: ReviewHighlightEntry[];
}

export type PlatformFilter = Platform | "all";

// 周报 section 中的单个条目：可能是字符串，也可能是带证据的对象。
export interface SectionItem {
  title?: string;
  detail?: string;
  change?: string;
  action?: string;
  note?: string;
  summary?: string;
  why?: string;
  strength?: string;
  pain_point?: string;
  evidence_review_ids?: number[];
  [key: string]: unknown;
}

export interface DigestSections {
  top_changes: (SectionItem | string)[];
  new_complaints: (SectionItem | string)[];
  new_praise: (SectionItem | string)[];
  rating_movement: (SectionItem | string)[];
  release_impact: (SectionItem | string)[];
  competitor_moves: (SectionItem | string)[];
  recommended_actions: (SectionItem | string)[];
  confidence_notes: (SectionItem | string)[];
}

export interface DigestReport {
  id: number;
  monitored_app_id: number;
  period_start: string;
  period_end: string;
  status: DigestStatus;
  title: string;
  summary: string;
  sections: DigestSections;
  evidence_review_ids: number[];
  llm_model: string | null;
  tokens_used: number;
  notion_page_url: string | null;
  sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DigestUpdate {
  status?: DigestStatus;
  title?: string;
  summary?: string;
}

export interface ClassifyResult {
  classified: number;
  enriched: number;
  batches: number;
  candidates: number;
  skipped_short: number;
  enrich_queued?: boolean;
  message: string;
}

export interface IngestResult {
  fetched: number;
  inserted: number;
  classified: number;
  platforms?: IngestPlatformResult[];
  warnings?: string[];
}

export interface IngestPlatformResult {
  platform: string;
  fetched: number;
  inserted: number;
  status: string;
  message?: string | null;
}

/** 后端可管理运行配置（GET /api/settings） */
export interface RuntimeSettings {
  env_file: string;
  llm_model: string;
  llm_classifier_model: string;
  llm_api_base: string | null;
  llm_timeout: number;
  llm_api_key_set: boolean;
  enable_llm_classification: boolean;
  classifier_batch_size: number;
  classifier_body_max_chars: number;
  email_provider: string;
  email_from: string;
  smtp_host: string | null;
  smtp_port: number;
  smtp_user: string | null;
  smtp_password_set: boolean;
  smtp_use_tls: boolean;
  resend_api_key_set: boolean;
  digest_recipient_email: string | null;
  default_country_codes: string;
  ingest_http_timeout: number;
  ingest_google_play_timeout: number;
  ingest_http_proxy: string | null;
  enable_scheduler: boolean;
  daily_ingest_hour: number;
  weekly_digest_weekday: number;
  weekly_digest_hour: number;
  notion_api_key_set: boolean;
  notion_reports_database_id: string | null;
  notion_title_property: string;
  notion_status_property: string | null;
  notion_period_property: string | null;
  notion_report_id_property: string | null;
  notion_auto_export: boolean;
}

export type RuntimeSettingsUpdate = Partial<{
  llm_model: string;
  llm_classifier_model: string;
  llm_api_key: string;
  llm_api_base: string | null;
  llm_timeout: number;
  enable_llm_classification: boolean;
  classifier_batch_size: number;
  classifier_body_max_chars: number;
  email_provider: string;
  email_from: string;
  smtp_host: string | null;
  smtp_port: number;
  smtp_user: string | null;
  smtp_password: string;
  smtp_use_tls: boolean;
  resend_api_key: string;
  digest_recipient_email: string | null;
  default_country_codes: string;
  ingest_http_timeout: number;
  ingest_google_play_timeout: number;
  ingest_http_proxy: string | null;
  enable_scheduler: boolean;
  daily_ingest_hour: number;
  weekly_digest_weekday: number;
  weekly_digest_hour: number;
  notion_api_key: string;
  notion_reports_database_id: string | null;
  notion_title_property: string;
  notion_status_property: string | null;
  notion_period_property: string | null;
  notion_report_id_property: string | null;
  notion_auto_export: boolean;
}>;

export interface ProxyCheckResult {
  name: string;
  ok: boolean;
  latency_ms?: number | null;
  status_code?: number | null;
  error?: string | null;
}

export interface ProxyTestResult {
  ok: boolean;
  mode: "proxy" | "direct";
  proxy: string | null;
  message: string;
  checks: ProxyCheckResult[];
}
