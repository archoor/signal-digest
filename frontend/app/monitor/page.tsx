// App 监控列表（设计文档第 11.1 /monitor）。
"use client";

import Link from "next/link";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { fromNow, PLATFORM_LABEL } from "@/lib/format";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  PageHeader,
  Spinner_Page,
  StatusBadge,
} from "@/components/ui";

export default function MonitorListPage() {
  const { data, loading, error } = useApi(() => api.listApps(), []);
  const apps = data || [];

  return (
    <div>
      <PageHeader
        title="App 监控"
        description="管理监控中的 App、采集状态与竞品配置。"
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
      ) : apps.length === 0 ? (
        <EmptyState
          title="还没有监控 App"
          description="添加你的 App Store / Google Play 链接，系统会定期采集评论并生成每周报告。"
          action={
            <Link href="/monitor/new">
              <Button>+ 添加监控 App</Button>
            </Link>
          }
        />
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-slate-50 text-left text-xs uppercase tracking-wide text-muted">
                <th className="px-5 py-3 font-medium">App</th>
                <th className="px-5 py-3 font-medium">平台</th>
                <th className="px-5 py-3 font-medium">国家</th>
                <th className="px-5 py-3 font-medium">状态</th>
                <th className="px-5 py-3 font-medium">上次采集</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {apps.map((app) => (
                <tr key={app.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3.5">
                    <Link
                      href={`/monitor/${app.id}`}
                      className="font-medium text-slate-900 hover:text-brand"
                    >
                      {app.name}
                    </Link>
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex flex-wrap gap-1">
                      {app.app_store_id && (
                        <Badge tone="blue">{PLATFORM_LABEL.app_store}</Badge>
                      )}
                      {app.google_play_package && (
                        <Badge tone="green">
                          {PLATFORM_LABEL.google_play}
                        </Badge>
                      )}
                      {!app.app_store_id && !app.google_play_package && (
                        <span className="text-xs text-muted">未解析</span>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-muted">
                    {app.country_codes.join(", ").toUpperCase() || "—"}
                  </td>
                  <td className="px-5 py-3.5">
                    <StatusBadge status={app.status} />
                  </td>
                  <td className="px-5 py-3.5 text-muted">
                    {fromNow(app.last_ingested_at)}
                  </td>
                  <td className="px-5 py-3.5 text-right">
                    <Link
                      href={`/monitor/${app.id}`}
                      className="text-sm text-brand hover:underline"
                    >
                      详情 →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
