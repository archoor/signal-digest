// 统一的后端 API 客户端（设计文档第 10 章）。
// 所有请求走 NEXT_PUBLIC_API_BASE + /api，集中处理错误与 JSON 解析。

import type {
  AppReview,
  AppSearchResult,
  Competitor,
  CompetitorCreate,
  DigestReport,
  DigestStatus,
  DigestUpdate,
  ClassifyResult,
  IngestResult,
  MonitoredApp,
  MonitoredAppCreate,
  MonitoredAppUpdate,
  Platform,
  ReviewHighlights,
  ReviewStats,
  RuntimeSettings,
  RuntimeSettingsUpdate,
  ProxyTestResult,
} from "./types";

const SERVER_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
  process.env.BACKEND_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

/** 浏览器用同源（Next rewrite）；SSR 直连后端。 */
export const API_BASE =
  typeof window !== "undefined" ? "" : SERVER_API_BASE;

/** 设置页展示用：实际后端地址。 */
export const API_BASE_DISPLAY = SERVER_API_BASE;

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
      cache: "no-store",
    });
  } catch (err) {
    const hint =
      typeof window !== "undefined"
        ? "请确认 FastAPI 已启动；若仍失败，检查浏览器/系统代理是否拦截 localhost"
        : "请确认 FastAPI 已启动";
    throw new ApiError(
      0,
      `无法连接后端 ${SERVER_API_BASE}，${hint}`
    );
  }

  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const data = await res.json();
      if (data?.detail) {
        detail =
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail);
      }
    } catch {
      // 忽略 JSON 解析失败，使用默认状态文案。
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// 后端健康检查（/health 不在 /api 前缀下）。
export async function pingBackend(): Promise<{ status: string; app: string }> {
  try {
    const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
    if (!res.ok) throw new ApiError(res.status, `${res.status}`);
    return (await res.json()) as { status: string; app: string };
  } catch {
    throw new ApiError(
      0,
      `无法连接后端 ${SERVER_API_BASE}，请确认 FastAPI 已启动`
    );
  }
}

function reviewQuery(appId: number, opts?: { platform?: Platform; limit?: number }) {
  const params = new URLSearchParams({ app_id: String(appId) });
  if (opts?.platform) params.set("platform", opts.platform);
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  return params.toString();
}

// ---- Apps（第 10.1）----
export const api = {
  searchApps: (q: string, country = "us", limit = 10) =>
    request<AppSearchResult[]>(
      `/apps/search?q=${encodeURIComponent(q)}&country=${country}&limit=${limit}`
    ),
  listApps: () => request<MonitoredApp[]>("/apps"),
  getApp: (id: number) => request<MonitoredApp>(`/apps/${id}`),
  createApp: (body: MonitoredAppCreate) =>
    request<MonitoredApp>("/apps", { method: "POST", body: JSON.stringify(body) }),
  updateApp: (id: number, body: MonitoredAppUpdate) =>
    request<MonitoredApp>(`/apps/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  ingestApp: (id: number) =>
    request<IngestResult>(`/apps/${id}/ingest`, { method: "POST" }),
  classifyApp: (id: number) =>
    request<ClassifyResult>(`/apps/${id}/classify`, { method: "POST" }),

  // ---- Competitors（第 10.2）----
  listCompetitors: (appId: number) =>
    request<Competitor[]>(`/apps/${appId}/competitors`),
  addCompetitor: (appId: number, body: CompetitorCreate) =>
    request<Competitor>(`/apps/${appId}/competitors`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  deleteCompetitor: (competitorId: number) =>
    request<void>(`/competitors/${competitorId}`, { method: "DELETE" }),

  // ---- Reviews（第 10.3）----
  listReviews: (appId: number, limit = 50, platform?: Platform) =>
    request<AppReview[]>(`/reviews?${reviewQuery(appId, { platform, limit })}`),
  reviewStats: (appId: number, platform?: Platform) => {
    const q = reviewQuery(appId, { platform }).replace(/&limit=\d+/, "");
    return request<ReviewStats>(`/reviews/stats?${q}`);
  },
  urgentReviews: (appId: number, limit = 50, platform?: Platform) =>
    request<AppReview[]>(`/reviews/urgent?${reviewQuery(appId, { platform, limit })}`),
  reviewHighlights: (appId: number, limit = 10, platform?: Platform) =>
    request<ReviewHighlights>(
      `/reviews/highlights?${reviewQuery(appId, { platform, limit })}`
    ),

  // ---- Digests（第 10.4）----
  listDigests: (opts?: { appId?: number; status?: DigestStatus }) => {
    const params = new URLSearchParams();
    if (opts?.appId != null) params.set("app_id", String(opts.appId));
    if (opts?.status) params.set("status", opts.status);
    const q = params.toString();
    return request<DigestReport[]>(`/digests${q ? `?${q}` : ""}`);
  },
  getDigest: (id: number) => request<DigestReport>(`/digests/${id}`),
  updateDigest: (id: number, body: DigestUpdate) =>
    request<DigestReport>(`/digests/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  generateDigest: (appId: number) =>
    request<DigestReport>(`/digests/generate?app_id=${appId}`, {
      method: "POST",
    }),
  sendDigest: (id: number) =>
    request<{ sent: boolean }>(`/digests/${id}/send`, { method: "POST" }),
  exportDigestToNotion: (id: number, force = false) =>
    request<DigestReport>(
      `/digests/${id}/export-notion${force ? "?force=true" : ""}`,
      { method: "POST" }
    ),

  // ---- Settings ----
  getSettings: () => request<RuntimeSettings>("/settings"),
  updateSettings: (body: RuntimeSettingsUpdate) =>
    request<RuntimeSettings>("/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  testProxyConnectivity: (ingest_http_proxy: string | null) =>
    request<ProxyTestResult>("/settings/proxy-test", {
      method: "POST",
      body: JSON.stringify({ ingest_http_proxy }),
    }),
};
