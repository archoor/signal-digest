// App 详情：采集 / 分类 / 生成周报 / 评论 / 竞品 / 设置（设计文档第 11.1 /monitor/{id}）。
"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { formatDate, fromNow, PLATFORM_LABEL } from "@/lib/format";
import { formatIngestMessage } from "@/lib/ingestFormat";
import type { MonitoredApp, Platform, PlatformFilter } from "@/lib/types";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  PageHeader,
  Spinner_Page,
  StatusBadge,
} from "@/components/ui";
import { Competitors } from "@/components/monitor/Competitors";
import { ReviewsTab } from "@/components/monitor/ReviewsTab";
import { AppSettings } from "@/components/monitor/AppSettings";

type Tab = "reviews" | "competitors" | "settings";

function StatBox({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <Card>
      <CardBody className="py-4">
        <div className="text-xs text-muted">{label}</div>
        <div className="mt-1 text-2xl font-semibold">{value}</div>
      </CardBody>
    </Card>
  );
}

export default function AppDetailPage() {
  const params = useParams<{ id: string }>();
  const appId = Number(params.id);
  const router = useRouter();

  const [platformFilter, setPlatformFilter] = useState<PlatformFilter>("all");
  const platformParam =
    platformFilter === "all" ? undefined : (platformFilter as Platform);

  const appQuery = useApi(() => api.getApp(appId), [appId]);
  const statsQuery = useApi(
    () => api.reviewStats(appId, platformParam),
    [appId, platformFilter]
  );

  const [tab, setTab] = useState<Tab>("reviews");
  const [reviewsRefresh, setReviewsRefresh] = useState(0);
  const [action, setAction] = useState<string | null>(null);
  const [message, setMessage] = useState<{
    tone: "success" | "error" | "info";
    text: string;
  } | null>(null);

  const app = appQuery.data;

  async function runIngest() {
    setAction("ingest");
    setMessage(null);
    try {
      const r = await api.ingestApp(appId);
      const msg = formatIngestMessage(r);
      setMessage({ tone: msg.tone, text: msg.text });
      appQuery.refetch();
      statsQuery.refetch();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "采集失败",
      });
    } finally {
      setAction(null);
    }
  }

  async function runClassify() {
    setAction("classify");
    setMessage(null);
    try {
      const r = await api.classifyApp(appId);
      const text = r.enrich_queued
        ? r.message ||
          `规则分类 ${r.classified} 条；已后台排队 ${r.candidates} 条 LLM 分析，请稍后刷新查看。`
        : `规则分类 ${r.classified} 条；LLM 深度分析 ${r.enriched} 条（${r.batches} 个批次）。${r.skipped_short ? ` ${r.skipped_short} 条过短评论未分析。` : ""}`;
      setMessage({ tone: "success", text });
      setReviewsRefresh((k) => k + 1);
      if (r.enrich_queued) {
        window.setTimeout(() => setReviewsRefresh((k) => k + 1), 45_000);
        window.setTimeout(() => setReviewsRefresh((k) => k + 1), 120_000);
      }
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "分类失败",
      });
    } finally {
      setAction(null);
    }
  }

  async function runGenerate() {
    setAction("generate");
    setMessage(null);
    try {
      const digest = await api.generateDigest(appId);
      router.push(`/reports/${digest.id}`);
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "生成周报失败",
      });
      setAction(null);
    }
  }

  if (appQuery.loading) return <Spinner_Page />;
  if (appQuery.error || !app)
    return (
      <div>
        <Alert tone="error">{appQuery.error || "App 不存在"}</Alert>
        <div className="mt-4">
          <Link href="/monitor" className="text-sm text-brand hover:underline">
            ← 返回列表
          </Link>
        </div>
      </div>
    );

  const stats = statsQuery.data;

  return (
    <div>
      <div className="mb-2">
        <Link href="/monitor" className="text-sm text-muted hover:text-brand">
          ← App 监控
        </Link>
      </div>

      <PageHeader
        title={app.name}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              onClick={runIngest}
              loading={action === "ingest"}
              disabled={!!action}
            >
              立即采集
            </Button>
            <Button
              variant="secondary"
              onClick={runClassify}
              loading={action === "classify"}
              disabled={!!action}
            >
              补跑分类
            </Button>
            <Button
              onClick={runGenerate}
              loading={action === "generate"}
              disabled={!!action}
            >
              生成周报
            </Button>
          </div>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <StatusBadge status={app.status} />
        {app.app_store_id && (
          <Badge tone="blue">
            {PLATFORM_LABEL.app_store} · {app.app_store_id}
          </Badge>
        )}
        {app.google_play_package && (
          <Badge tone="green">
            {PLATFORM_LABEL.google_play} · {app.google_play_package}
          </Badge>
        )}
        {app.country_codes.length > 0 && (
          <span className="text-sm text-muted">
            国家：{app.country_codes.join(", ").toUpperCase()}
          </span>
        )}
      </div>

      {(app.app_store_id || app.google_play_package) && (
        <div className="mb-5 inline-flex rounded-lg border border-border p-0.5">
          {(
            [
              ["all", "全部"],
              ...(app.app_store_id
                ? [["app_store", PLATFORM_LABEL.app_store] as const]
                : []),
              ...(app.google_play_package
                ? [["google_play", PLATFORM_LABEL.google_play] as const]
                : []),
            ] as [PlatformFilter, string][]
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setPlatformFilter(key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                platformFilter === key
                  ? "bg-indigo-50 text-brand"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {message && (
        <div className="mb-5">
          <Alert tone={message.tone === "info" ? "info" : message.tone}>
            <span className="whitespace-pre-line">{message.text}</span>
          </Alert>
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatBox label="评论总数" value={stats?.total ?? "—"} />
        <StatBox
          label="平均评分"
          value={stats?.avg_rating != null ? stats.avg_rating.toFixed(2) : "—"}
        />
        <StatBox label="上次采集" value={fromNow(app.last_ingested_at)} />
        <StatBox
          label="最近发版"
          value={app.last_release_date ? formatDate(app.last_release_date) : "—"}
        />
      </div>

      <div className="mb-5 flex gap-1 border-b border-border">
        {(
          [
            ["reviews", "评论"],
            ["competitors", "竞品"],
            ["settings", "设置"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              tab === key
                ? "border-brand text-brand"
                : "border-transparent text-slate-600 hover:text-slate-900"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "reviews" && (
        <ReviewsTab
          appId={appId}
          platformFilter={platformFilter}
          refreshToken={reviewsRefresh}
        />
      )}
      {tab === "competitors" && (
        <Competitors appId={appId} app={app} />
      )}
      {tab === "settings" && (
        <AppSettings
          app={app}
          onUpdated={(u: MonitoredApp) => {
            appQuery.refetch();
            setMessage({ tone: "success", text: `已更新 ${u.name} 的配置。` });
          }}
        />
      )}
    </div>
  );
}
