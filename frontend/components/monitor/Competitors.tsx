// 竞品管理：列表 + 搜索添加 + 删除（设计文档第 10.2，每个 App 最多 3 个）。
"use client";

import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { PLATFORM_LABEL } from "@/lib/format";
import type { AppSearchResult, MonitoredApp } from "@/lib/types";
import {
  AppSearchPicker,
  SelectedAppCard,
} from "@/components/monitor/AppSearchPicker";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  Spinner_Page,
} from "@/components/ui";

export function Competitors({
  appId,
  app,
}: {
  appId: number;
  app?: MonitoredApp | null;
}) {
  const { data, loading, error, refetch } = useApi(
    () => api.listCompetitors(appId),
    [appId]
  );
  const competitors = data || [];

  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<AppSearchResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const country = app?.country_codes?.[0] || "us";

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!selected) {
      setFormError("请搜索并选择一个竞品");
      return;
    }
    setBusy(true);
    try {
      await api.addCompetitor(appId, {
        name: selected.name,
        app_store_id: selected.app_store_id,
        google_play_package: selected.google_play_package,
        app_store_url: selected.app_store_url,
        google_play_url: selected.google_play_url,
      });
      setQuery("");
      setSelected(null);
      refetch();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "添加失败");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("确认删除该竞品？")) return;
    try {
      await api.deleteCompetitor(id);
      refetch();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "删除失败");
    }
  }

  if (loading) return <Spinner_Page />;

  return (
    <div className="space-y-5">
      {error && <Alert tone="error">{error}</Alert>}

      <Card>
        <CardBody>
          <ul className="divide-y divide-border">
            {competitors.length === 0 && (
              <li className="py-6 text-center text-sm text-muted">
                暂无竞品
              </li>
            )}
            {competitors.map((c) => (
              <li
                key={c.id}
                className="flex items-center justify-between gap-4 py-4"
              >
                <div>
                  <div className="font-medium">{c.name}</div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {c.app_store_id && (
                      <Badge tone="blue">
                        {PLATFORM_LABEL.app_store} · {c.app_store_id}
                      </Badge>
                    )}
                    {c.google_play_package && (
                      <Badge tone="green">
                        {PLATFORM_LABEL.google_play} · {c.google_play_package}
                      </Badge>
                    )}
                  </div>
                </div>
                <Button variant="ghost" onClick={() => handleDelete(c.id)}>
                  删除
                </Button>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>

      {competitors.length < 3 && (
        <Card>
          <CardBody>
            <h3 className="mb-3 text-sm font-semibold">添加竞品</h3>
            <form onSubmit={handleAdd} className="space-y-3">
              {formError && <Alert tone="error">{formError}</Alert>}
              {selected ? (
                <SelectedAppCard
                  selection={selected}
                  onClear={() => {
                    setSelected(null);
                    setQuery("");
                  }}
                />
              ) : (
                <AppSearchPicker
                  value={query}
                  onChange={setQuery}
                  onSelect={(r) => {
                    setSelected(r);
                    setQuery(r.name);
                  }}
                  country={country}
                  placeholder="搜索竞品 App 名称…"
                />
              )}
              <Button type="submit" loading={busy} disabled={!selected}>
                添加竞品
              </Button>
            </form>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
