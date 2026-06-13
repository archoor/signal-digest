// 设置 / 用量：连接状态 → 用量统计 → 运行配置。
"use client";

import { useMemo } from "react";
import { api, API_BASE_DISPLAY, pingBackend } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import {
  Alert,
  Badge,
  Card,
  CardBody,
  PageHeader,
  Spinner,
} from "@/components/ui";
import { RuntimeSettingsForm } from "@/components/settings/RuntimeSettingsForm";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardBody className="py-4">
        <div className="text-xs text-muted">{label}</div>
        <div className="mt-1 text-2xl font-semibold">{value}</div>
      </CardBody>
    </Card>
  );
}

export default function SettingsPage() {
  const health = useApi(() => pingBackend(), []);
  const apps = useApi(() => api.listApps(), []);
  const digests = useApi(() => api.listDigests(), []);

  const usage = useMemo(() => {
    const list = digests.data || [];
    const totalTokens = list.reduce((sum, d) => sum + (d.tokens_used || 0), 0);
    const byModel = new Map<string, number>();
    list.forEach((d) => {
      const key = d.llm_model || "未知";
      byModel.set(key, (byModel.get(key) || 0) + (d.tokens_used || 0));
    });
    const pendingReview = list.filter(
      (d) => d.status === "needs_review" || d.status === "draft"
    ).length;
    return { totalTokens, byModel: Array.from(byModel.entries()), pendingReview };
  }, [digests.data]);

  return (
    <div>
      <PageHeader
        title="设置 / 用量"
        description="查看用量统计，配置 LLM、发件邮箱、外网代理与调度参数。"
      />

      <div className="space-y-8">
        <Card>
          <CardBody>
            <h2 className="mb-3 text-sm font-semibold">后端连接</h2>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted">API 基址</span>
              <code className="rounded bg-slate-100 px-2 py-0.5 text-xs">
                {API_BASE_DISPLAY}
                <span className="ml-1 text-xs text-muted">（浏览器经 Next /api 转发）</span>
              </code>
            </div>
            <div className="mt-3 flex items-center justify-between text-sm">
              <span className="text-muted">状态</span>
              {health.loading ? (
                <Spinner className="h-4 w-4 text-muted" />
              ) : health.error ? (
                <Badge tone="red">未连接</Badge>
              ) : (
                <Badge tone="green">已连接 · {health.data?.app}</Badge>
              )}
            </div>
            {health.error && (
              <div className="mt-3">
                <Alert tone="error">
                  {health.error}。请确认后端已启动：
                  <code className="ml-1">
                    uv run uvicorn app.main:app --reload
                  </code>
                </Alert>
              </div>
            )}
          </CardBody>
        </Card>

        <section>
          <h2 className="mb-3 text-base font-semibold">用量统计</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="监控 App" value={apps.data?.length ?? "—"} />
            <StatCard label="周报总数" value={digests.data?.length ?? "—"} />
            <StatCard
              label="待审核周报"
              value={usage.pendingReview}
            />
            <StatCard
              label="累计 LLM tokens"
              value={usage.totalTokens.toLocaleString()}
            />
          </div>

          {usage.byModel.length > 0 && (
            <Card className="mt-4">
              <CardBody>
                <h3 className="mb-2 text-sm font-medium">按模型分布</h3>
                <ul className="divide-y divide-border text-sm">
                  {usage.byModel.map(([model, tokens]) => (
                    <li
                      key={model}
                      className="flex items-center justify-between py-2"
                    >
                      <span>{model}</span>
                      <span className="text-muted">
                        {tokens.toLocaleString()} tokens
                      </span>
                    </li>
                  ))}
                </ul>
              </CardBody>
            </Card>
          )}
        </section>

        <section>
          <h2 className="mb-4 text-base font-semibold">运行配置</h2>
          <RuntimeSettingsForm />
        </section>
      </div>
    </div>
  );
}
