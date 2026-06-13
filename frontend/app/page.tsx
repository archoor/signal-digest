// 概览首页：整体监控状态与快捷入口。
"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fromNow } from "@/lib/format";
import {
  Alert,
  Button,
  Card,
  CardBody,
  EmptyState,
  PageHeader,
  Spinner_Page,
  StatusBadge,
} from "@/components/ui";
import { DigestStatusBadge } from "@/components/reports/digestIcons";

function StatCard({
  label,
  value,
  tone = "text-slate-900",
}: {
  label: string;
  value: string | number;
  tone?: string;
}) {
  return (
    <Card>
      <CardBody>
        <div className="text-sm text-muted">{label}</div>
        <div className={`mt-1 text-3xl font-semibold ${tone}`}>{value}</div>
      </CardBody>
    </Card>
  );
}

export default function HomePage() {
  const apps = useApi(() => api.listApps(), []);
  const digests = useApi(() => api.listDigests(), []);

  const loading = apps.loading || digests.loading;
  const error = apps.error || digests.error;

  const appList = apps.data || [];
  const digestList = digests.data || [];
  const activeCount = appList.filter((a) => a.status === "active").length;
  const pendingReview = digestList.filter(
    (d) => d.status === "needs_review" || d.status === "draft"
  ).length;

  return (
    <div>
      <PageHeader
        title="概览"
        description="App 评论信号周报系统：配置监控、采集评论、审核并发送每周报告。"
        actions={
          <Link href="/monitor/new">
            <Button>+ 添加监控 App</Button>
          </Link>
        }
      />

      {error && (
        <div className="mb-6">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      {loading ? (
        <Spinner_Page />
      ) : (
        <>
          <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="监控 App" value={appList.length} />
            <StatCard
              label="监控中"
              value={activeCount}
              tone="text-emerald-600"
            />
            <StatCard label="周报总数" value={digestList.length} />
            <StatCard
              label="待审核周报"
              value={pendingReview}
              tone={pendingReview ? "text-amber-600" : "text-slate-900"}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold">监控中的 App</h2>
                <Link
                  href="/monitor"
                  className="text-sm text-brand hover:underline"
                >
                  查看全部 →
                </Link>
              </div>
              {appList.length === 0 ? (
                <EmptyState
                  title="还没有监控 App"
                  description="添加你的 App Store / Google Play 链接，开始监控评论变化。"
                  action={
                    <Link href="/monitor/new">
                      <Button>+ 添加监控 App</Button>
                    </Link>
                  }
                />
              ) : (
                <Card>
                  <ul className="divide-y divide-border">
                    {appList.slice(0, 5).map((app) => (
                      <li key={app.id}>
                        <Link
                          href={`/monitor/${app.id}`}
                          className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50"
                        >
                          <div>
                            <div className="font-medium">{app.name}</div>
                            <div className="text-xs text-muted">
                              上次采集：{fromNow(app.last_ingested_at)}
                            </div>
                          </div>
                          <StatusBadge status={app.status} />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </section>

            <section>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold">最近周报</h2>
                <Link
                  href="/reports"
                  className="text-sm text-brand hover:underline"
                >
                  查看全部 →
                </Link>
              </div>
              {digestList.length === 0 ? (
                <EmptyState
                  title="还没有周报"
                  description="采集到评论后，可在 App 详情或周报页生成第一份周报。"
                />
              ) : (
                <Card>
                  <ul className="divide-y divide-border">
                    {digestList.slice(0, 5).map((d) => (
                      <li key={d.id}>
                        <Link
                          href={`/reports/${d.id}`}
                          className="flex items-center justify-between px-5 py-3.5 hover:bg-slate-50"
                        >
                          <div className="min-w-0 pr-3">
                            <div className="truncate font-medium">
                              {d.title || `周报 #${d.id}`}
                            </div>
                            <div className="text-xs text-muted">
                              {fromNow(d.created_at)}
                            </div>
                          </div>
                          <DigestStatusBadge status={d.status} size="sm" />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
