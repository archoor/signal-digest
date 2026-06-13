// 评论浏览：最近 / 高优先级 / 评论重点（设计文档第 10.3）。
"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { formatDay, PLATFORM_LABEL } from "@/lib/format";
import { uniqueById, uniqueHighlightItems } from "@/lib/uniqueById";
import type { AppReview, Platform, PlatformFilter } from "@/lib/types";
import { ReviewHighlights } from "@/components/monitor/ReviewHighlights";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  Spinner_Page,
  Stars,
} from "@/components/ui";

function platformParam(filter: PlatformFilter): Platform | undefined {
  return filter === "all" ? undefined : filter;
}

function ReviewItem({ review }: { review: AppReview }) {
  return (
    <li className="px-5 py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Stars rating={review.rating} />
            {review.title && (
              <span className="truncate font-medium">{review.title}</span>
            )}
            <Badge tone="slate">{PLATFORM_LABEL[review.platform]}</Badge>
          </div>
          <p className="mt-1.5 whitespace-pre-wrap text-sm text-slate-600">
            {review.body}
          </p>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
        <span>#{review.id}</span>
        {review.country && (
          <Badge tone="slate">{review.country.toUpperCase()}</Badge>
        )}
        {review.app_version && <span>v{review.app_version}</span>}
        <span>{formatDay(review.source_created_at)}</span>
      </div>
    </li>
  );
}

export function ReviewsTab({
  appId,
  platformFilter,
  refreshToken = 0,
}: {
  appId: number;
  platformFilter: PlatformFilter;
  refreshToken?: number;
}) {
  const [tab, setTab] = useState<"recent" | "urgent" | "highlights">("recent");
  const platform = platformParam(platformFilter);

  const recent = useApi(
    () => api.listReviews(appId, 100, platform),
    [appId, platformFilter]
  );
  const urgent = useApi(
    () => api.urgentReviews(appId, 100, platform),
    [appId, platformFilter]
  );

  const current = tab === "recent" ? recent : tab === "urgent" ? urgent : null;
  const reviews = uniqueById(current?.data || []);

  const tabClass = (active: boolean, urgent?: boolean) =>
    `rounded-lg px-3 py-1.5 text-sm font-medium ${
      active
        ? urgent
          ? "bg-red-50 text-red-600"
          : "bg-indigo-50 text-brand"
        : "text-slate-600 hover:bg-slate-100"
    }`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setTab("recent")}
          className={tabClass(tab === "recent")}
        >
          最近评论 {recent.data ? `(${recent.data.length})` : ""}
        </button>
        <button
          onClick={() => setTab("urgent")}
          className={tabClass(tab === "urgent", true)}
        >
          高优先级 (P0/P1) {urgent.data ? `(${urgent.data.length})` : ""}
        </button>
        <button
          onClick={() => setTab("highlights")}
          className={tabClass(tab === "highlights")}
        >
          评论重点
        </button>
      </div>

      {tab === "highlights" ? (
        <ReviewHighlights
          appId={appId}
          platformFilter={platformFilter}
          refreshToken={refreshToken}
        />
      ) : (
        <>
          {current?.error && <Alert tone="error">{current.error}</Alert>}

          {current?.loading ? (
            <Spinner_Page />
          ) : reviews.length === 0 ? (
            <EmptyState
              title={tab === "recent" ? "暂无评论" : "暂无高优先级评论"}
              description={
                tab === "recent"
                  ? "点击上方「立即采集」抓取最新评论。"
                  : "采集并分类后，P0/P1 评论会显示在这里。"
              }
            />
          ) : (
            <Card>
              <ul className="divide-y divide-border">
                {reviews.map((r) => (
                  <ReviewItem key={r.id} review={r} />
                ))}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
