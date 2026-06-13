// 周报列表：状态筛选 + 快捷审核操作（设计文档第 8.3 / 11.1）。
"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { formatDay, fromNow } from "@/lib/format";
import type { DigestStatus } from "@/lib/types";
import { DigestQuickActions } from "@/components/reports/DigestQuickActions";
import {
  DigestStatusBadge,
  STATUS_FILTER_LABEL,
  StatusFilterIcon,
} from "@/components/reports/digestIcons";
import {
  Alert,
  Card,
  EmptyState,
  PageHeader,
  Select,
  Spinner_Page,
} from "@/components/ui";

type StatusFilter = "all" | DigestStatus | "pending";

const STATUS_TABS: { key: StatusFilter }[] = [
  { key: "all" },
  { key: "pending" },
  { key: "needs_review" },
  { key: "approved" },
  { key: "sent" },
  { key: "failed" },
];

export default function ReportsListPage() {
  const apps = useApi(() => api.listApps(), []);
  const allDigests = useApi(() => api.listDigests(), []);
  const [appFilter, setAppFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const digests = useApi(
    () =>
      api.listDigests({
        appId: appFilter === "all" ? undefined : Number(appFilter),
        status:
          statusFilter === "all" || statusFilter === "pending"
            ? undefined
            : statusFilter,
      }),
    [appFilter, statusFilter]
  );

  const settings = useApi(() => api.getSettings(), []);

  const appNameMap = useMemo(() => {
    const m = new Map<number, string>();
    (apps.data || []).forEach((a) => m.set(a.id, a.name));
    return m;
  }, [apps.data]);

  const recipientEmail = settings.data?.digest_recipient_email ?? null;

  const list = (digests.data || []).filter((d) => {
    if (statusFilter === "pending") {
      return d.status === "draft" || d.status === "needs_review";
    }
    return true;
  });

  const pendingCount = (allDigests.data || []).filter(
    (d) => d.status === "draft" || d.status === "needs_review"
  ).length;

  return (
    <div>
      <PageHeader
        title="周报"
        description="每周「What changed?」报告。审核通过后即可发送至设置页配置的接收邮箱。"
        actions={
          <Select
            value={appFilter}
            onChange={(e) => setAppFilter(e.target.value)}
            className="w-44"
          >
            <option value="all">全部 App</option>
            {(apps.data || []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </Select>
        }
      />

      <div className="mb-4 flex flex-wrap gap-1.5">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.key}
            title={STATUS_FILTER_LABEL[tab.key]}
            aria-label={STATUS_FILTER_LABEL[tab.key]}
            onClick={() => setStatusFilter(tab.key)}
            className={`relative inline-flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
              statusFilter === tab.key
                ? "bg-indigo-50 text-brand ring-1 ring-indigo-200"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <StatusFilterIcon filter={tab.key} className="h-4 w-4" />
            {tab.key === "pending" && pendingCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber-500 px-1 text-[10px] font-medium text-white">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {digests.error && (
        <div className="mb-6">
          <Alert tone="error">{digests.error}</Alert>
        </div>
      )}

      {digests.loading ? (
        <Spinner_Page />
      ) : list.length === 0 ? (
        <EmptyState
          title={
            statusFilter === "pending"
              ? "没有待处理的周报"
              : "还没有周报"
          }
          description={
            statusFilter === "all"
              ? "进入某个 App 详情页，点击「生成周报」即可创建第一份报告。"
              : `当前筛选「${STATUS_FILTER_LABEL[statusFilter as keyof typeof STATUS_FILTER_LABEL]}」下无数据。`
          }
          action={
            statusFilter === "all" ? (
              <Link href="/monitor" className="text-sm text-brand hover:underline">
                前往 App 监控 →
              </Link>
            ) : undefined
          }
        />
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full table-fixed text-sm">
            <thead>
              <tr className="border-b border-border bg-slate-50 text-left text-xs uppercase tracking-wide text-muted">
                <th className="w-[28%] px-5 py-3 font-medium">标题</th>
                <th className="px-5 py-3 font-medium">App</th>
                <th className="px-5 py-3 font-medium">周期</th>
                <th className="px-5 py-3 font-medium">状态</th>
                <th className="px-5 py-3 font-medium">创建</th>
                <th className="px-5 py-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {list.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50">
                  <td className="w-[28%] max-w-0 px-5 py-3.5">
                    <Link
                      href={`/reports/${d.id}`}
                      className="block truncate font-medium text-slate-900 hover:text-brand"
                      title={d.title || `周报 #${d.id}`}
                    >
                      {d.title || `周报 #${d.id}`}
                    </Link>
                    {d.summary && (
                      <p
                        className="mt-0.5 truncate text-xs text-muted"
                        title={d.summary}
                      >
                        {d.summary}
                      </p>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-muted">
                    {appNameMap.get(d.monitored_app_id) ||
                      `App #${d.monitored_app_id}`}
                  </td>
                  <td className="px-5 py-3.5 text-muted">
                    {formatDay(d.period_start)} ~ {formatDay(d.period_end)}
                  </td>
                  <td className="px-5 py-3.5">
                    <DigestStatusBadge status={d.status} size="sm" />
                  </td>
                  <td className="px-5 py-3.5 text-muted">
                    {fromNow(d.created_at)}
                  </td>
                  <td className="px-5 py-3.5">
                    <DigestQuickActions
                      digest={d}
                      recipientEmail={recipientEmail}
                      onDone={() => digests.refetch()}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <p className="mt-4 flex flex-wrap items-center gap-3 text-xs text-muted">
        <span>悬停图标查看状态说明</span>
        {STATUS_TABS.map((tab) => (
          <span key={tab.key} className="inline-flex items-center gap-1">
            <StatusFilterIcon filter={tab.key} className="h-3.5 w-3.5" />
            {STATUS_FILTER_LABEL[tab.key]}
          </span>
        ))}
      </p>
    </div>
  );
}
