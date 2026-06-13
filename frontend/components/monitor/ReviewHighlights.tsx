// 评论重点：好评 / 差评分栏展示（设计文档第 10.3）。
"use client";

import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { formatDay, PLATFORM_LABEL } from "@/lib/format";
import { uniqueHighlightItems } from "@/lib/uniqueById";
import type { Platform, PlatformFilter } from "@/lib/types";
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

function HighlightColumn({
  title,
  tone,
  emptyTitle,
  items,
}: {
  title: string;
  tone: "green" | "red";
  emptyTitle: string;
  items: {
    review: {
      id: number;
      rating: number | null;
      title: string | null;
      body: string;
      platform: Platform;
      source_created_at: string;
    };
    insight: {
      summary: string | null;
      feature_area: string | null;
    };
  }[];
}) {
  const border =
    tone === "green" ? "border-emerald-100 bg-emerald-50/30" : "border-red-100 bg-red-50/30";
  const label = tone === "green" ? "好在哪里" : "痛点 / 不足";

  return (
    <Card>
      <div className={`border-b px-4 py-3 ${border}`}>
        <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      </div>
      {items.length === 0 ? (
        <div className="p-4">
          <EmptyState title={emptyTitle} description="采集并分类后会出现分析结果。" />
        </div>
      ) : (
        <ul className="divide-y divide-border">
          {items.map(({ review, insight }) => (
            <li key={review.id} className="px-4 py-4">
              <div className="flex items-center gap-2">
                <Stars rating={review.rating} />
                {review.title && (
                  <span className="truncate font-medium">{review.title}</span>
                )}
                <Badge tone="slate">{PLATFORM_LABEL[review.platform]}</Badge>
              </div>
              <p className="mt-2 line-clamp-3 text-sm text-slate-600">
                {review.body}
              </p>
              {insight.summary && (
                <div
                  className={`mt-3 rounded-md border px-3 py-2 text-sm ${
                    tone === "green"
                      ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                      : "border-red-200 bg-red-50 text-red-900"
                  }`}
                >
                  <span className="font-medium">{label}：</span>
                  {insight.summary}
                </div>
              )}
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted">
                <span>#{review.id}</span>
                {insight.feature_area && (
                  <Badge tone="purple">{insight.feature_area}</Badge>
                )}
                <span>{formatDay(review.source_created_at)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function ReviewHighlights({
  appId,
  platformFilter,
  refreshToken = 0,
}: {
  appId: number;
  platformFilter: PlatformFilter;
  refreshToken?: number;
}) {
  const platform = platformParam(platformFilter);
  const { data, loading, error } = useApi(
    () => api.reviewHighlights(appId, 10, platform),
    [appId, platformFilter, refreshToken]
  );

  if (loading) return <Spinner_Page />;
  if (error) return <Alert tone="error">{error}</Alert>;

  const praise = uniqueHighlightItems(data?.praise || []);
  const complaints = uniqueHighlightItems(data?.complaints || []);

  if (!praise.length && !complaints.length) {
    return (
      <EmptyState
        title="暂无评论重点"
        description="请先采集评论并完成分类，系统会自动提炼好评优点与差评痛点。"
      />
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <HighlightColumn
        title={`用户说好 (${praise.length})`}
        tone="green"
        emptyTitle="暂无好评重点"
        items={praise}
      />
      <HighlightColumn
        title={`用户吐槽 (${complaints.length})`}
        tone="red"
        emptyTitle="暂无差评重点"
        items={complaints}
      />
    </div>
  );
}
