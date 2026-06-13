// 周报详情：审核面板 + 邮件式正文 + 证据评论（设计文档第 11.2）。
"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import {
  digestToMarkdown,
  itemEvidence,
  itemToText,
  SECTION_KEYS,
  SECTION_TITLES,
} from "@/lib/digestMarkdown";
import type { AppReview, DigestReport } from "@/lib/types";
import { DigestReviewPanel } from "@/components/reports/DigestReviewPanel";
import {
  Alert,
  Button,
  Card,
  CardBody,
  PageHeader,
  Spinner_Page,
  Stars,
} from "@/components/ui";

function EvidenceReviews({
  ids,
  reviewMap,
}: {
  ids: number[];
  reviewMap: Map<number, AppReview>;
}) {
  const [open, setOpen] = useState(false);
  if (!ids.length) return null;
  const found = ids.map((id) => reviewMap.get(id)).filter(Boolean) as AppReview[];

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="text-xs font-medium text-brand hover:underline"
      >
        {open ? "收起证据评论" : `查看证据评论 (${ids.length})`}
      </button>
      {open && (
        <div className="mt-2 space-y-2 border-l-2 border-indigo-100 pl-3">
          {found.length === 0 && (
            <p className="text-xs text-muted">
              证据 review id：{ids.join(", ")}（未在最近评论中找到原文）
            </p>
          )}
          {found.map((r) => (
            <div key={r.id} className="rounded-md bg-slate-50 p-2.5 text-sm">
              <div className="flex items-center gap-2">
                <Stars rating={r.rating} />
                {r.title && <span className="font-medium">{r.title}</span>}
                <span className="text-xs text-muted">#{r.id}</span>
              </div>
              <p className="mt-1 whitespace-pre-wrap text-slate-600">{r.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ReportDetailPage() {
  const params = useParams<{ id: string }>();
  const digestId = Number(params.id);

  const reportQuery = useApi(() => api.getDigest(digestId), [digestId]);
  const report = reportQuery.data;

  const appQuery = useApi(
    () =>
      report
        ? api.getApp(report.monitored_app_id)
        : Promise.resolve(null),
    [report?.monitored_app_id]
  );

  const reviewsQuery = useApi(
    () =>
      report
        ? api.listReviews(report.monitored_app_id, 200)
        : Promise.resolve([] as AppReview[]),
    [report?.monitored_app_id]
  );

  const reviewMap = useMemo(() => {
    const m = new Map<number, AppReview>();
    (reviewsQuery.data || []).forEach((r) => m.set(r.id, r));
    return m;
  }, [reviewsQuery.data]);

  const [expandAllEvidence, setExpandAllEvidence] = useState(false);

  function exportMarkdown(r: DigestReport) {
    const md = digestToMarkdown(r);
    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `digest-${r.id}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function refetchAll() {
    reportQuery.refetch();
    appQuery.refetch();
  }

  if (reportQuery.loading) return <Spinner_Page />;
  if (reportQuery.error || !report)
    return (
      <div>
        <Alert tone="error">{reportQuery.error || "周报不存在"}</Alert>
        <div className="mt-4">
          <Link href="/reports" className="text-sm text-brand hover:underline">
            ← 返回周报列表
          </Link>
        </div>
      </div>
    );

  const hasAnySection = SECTION_KEYS.some(
    (k) => (report.sections?.[k]?.length ?? 0) > 0
  );

  const allEvidenceIds = [
    ...new Set(
      SECTION_KEYS.flatMap((key) =>
        (report.sections?.[key] || []).flatMap((item) => itemEvidence(item))
      )
    ),
  ];

  return (
    <div>
      <div className="mb-2">
        <Link href="/reports" className="text-sm text-muted hover:text-brand">
          ← 周报
        </Link>
      </div>

      <PageHeader
        title={report.title || `周报 #${report.id}`}
        actions={
          <Button variant="secondary" onClick={() => exportMarkdown(report)}>
            导出 Markdown
          </Button>
        }
      />

      <DigestReviewPanel
        report={report}
        app={appQuery.data ?? null}
        onUpdated={refetchAll}
      />

      {/* 证据评论汇总 */}
      {allEvidenceIds.length > 0 && (
        <Card className="mb-6 max-w-3xl">
          <CardBody>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">
                全部证据评论（{allEvidenceIds.length} 条）
              </h3>
              <button
                onClick={() => setExpandAllEvidence((o) => !o)}
                className="text-xs text-brand hover:underline"
              >
                {expandAllEvidence ? "收起" : "展开全部"}
              </button>
            </div>
            {expandAllEvidence && (
              <div className="space-y-2">
                {allEvidenceIds.map((id) => {
                  const r = reviewMap.get(id);
                  return r ? (
                    <div
                      key={id}
                      className="rounded-md border border-border p-3 text-sm"
                    >
                      <div className="flex items-center gap-2">
                        <Stars rating={r.rating} />
                        {r.title && (
                          <span className="font-medium">{r.title}</span>
                        )}
                        <span className="text-xs text-muted">#{r.id}</span>
                      </div>
                      <p className="mt-1 whitespace-pre-wrap text-slate-600">
                        {r.body}
                      </p>
                    </div>
                  ) : (
                    <p key={id} className="text-xs text-muted">
                      #{id}（未找到原文）
                    </p>
                  );
                })}
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {/* 像邮件一样呈现正文 */}
      <Card className="max-w-3xl">
        <CardBody className="space-y-6">
          <h3 className="text-sm font-semibold text-slate-900">报告预览</h3>

          {report.summary && (
            <p className="rounded-lg bg-slate-50 px-4 py-3 text-[15px] leading-relaxed text-slate-800">
              {report.summary}
            </p>
          )}

          {!hasAnySection && (
            <p className="text-sm text-muted">
              本周报暂无结构化内容。可在 App 详情页重新「生成周报」。
            </p>
          )}

          {SECTION_KEYS.map((key) => {
            const items = report.sections?.[key] || [];
            if (!items.length) return null;
            return (
              <section key={key}>
                <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
                  {SECTION_TITLES[key]}
                </h3>
                <ul className="space-y-3">
                  {items.map((item, idx) => {
                    const strength =
                      typeof item === "object" && item.strength
                        ? String(item.strength)
                        : null;
                    const painPoint =
                      typeof item === "object" && item.pain_point
                        ? String(item.pain_point)
                        : null;
                    return (
                    <li
                      key={idx}
                      className="rounded-lg border border-border px-4 py-3"
                    >
                      <div className="text-sm text-slate-800">
                        {itemToText(item)}
                      </div>
                      {strength && (
                        <p className="mt-2 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
                          <span className="font-medium">好在哪里：</span>
                          {strength}
                        </p>
                      )}
                      {painPoint && (
                        <p className="mt-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-900">
                          <span className="font-medium">痛点 / 不足：</span>
                          {painPoint}
                        </p>
                      )}
                      <EvidenceReviews
                        ids={itemEvidence(item)}
                        reviewMap={reviewMap}
                      />
                    </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </CardBody>
      </Card>
    </div>
  );
}
