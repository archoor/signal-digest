// 添加监控 App + 竞品（设计文档第 7.1 Onboarding / 11.1 /monitor/new）。
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { AppSearchResult } from "@/lib/types";
import {
  AppSearchPicker,
  SelectedAppCard,
} from "@/components/monitor/AppSearchPicker";
import {
  Alert,
  Button,
  Card,
  CardBody,
  Field,
  Input,
  PageHeader,
} from "@/components/ui";

interface CompetitorRow {
  query: string;
  selected: AppSearchResult | null;
}

export default function NewMonitorPage() {
  const router = useRouter();

  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<AppSearchResult | null>(null);
  const [countries, setCountries] = useState("us");
  const [competitors, setCompetitors] = useState<CompetitorRow[]>([]);
  const [advanced, setAdvanced] = useState(false);
  const [appStoreUrl, setAppStoreUrl] = useState("");
  const [googlePlayUrl, setGooglePlayUrl] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const countryCode = countries.split(",")[0]?.trim().toLowerCase() || "us";

  function updateCompetitor(idx: number, patch: Partial<CompetitorRow>) {
    setCompetitors((rows) =>
      rows.map((r, i) => (i === idx ? { ...r, ...patch } : r))
    );
  }

  function addCompetitorRow() {
    if (competitors.length >= 3) return;
    setCompetitors((rows) => [...rows, { query: "", selected: null }]);
  }

  function removeCompetitorRow(idx: number) {
    setCompetitors((rows) => rows.filter((_, i) => i !== idx));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const name = selected?.name || query.trim();
    if (!name) {
      setError("请搜索并选择一个 App");
      return;
    }

    const hasPlatform =
      selected?.app_store_id ||
      selected?.google_play_package ||
      appStoreUrl.trim() ||
      googlePlayUrl.trim();
    if (!hasPlatform) {
      setError("请从搜索结果中选择一个 App，或在高级模式中填写链接");
      return;
    }

    setSubmitting(true);
    try {
      const app = await api.createApp({
        name,
        app_store_id: selected?.app_store_id || null,
        google_play_package: selected?.google_play_package || null,
        app_store_url: advanced ? appStoreUrl.trim() || null : selected?.app_store_url || null,
        google_play_url: advanced ? googlePlayUrl.trim() || null : selected?.google_play_url || null,
        country_codes: countries
          .split(",")
          .map((c) => c.trim().toLowerCase())
          .filter(Boolean),
      });

      for (const c of competitors) {
        if (!c.selected) continue;
        await api.addCompetitor(app.id, {
          name: c.selected.name,
          app_store_id: c.selected.app_store_id,
          google_play_package: c.selected.google_play_package,
          app_store_url: c.selected.app_store_url,
          google_play_url: c.selected.google_play_url,
        });
      }

      router.push(`/monitor/${app.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "创建失败，请重试");
      setSubmitting(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="添加监控 App"
        description="输入 App 名称搜索，点选结果即可同时绑定 iOS / Android（若商店均有上架）。"
      />

      <form onSubmit={handleSubmit} className="max-w-2xl space-y-6">
        {error && <Alert tone="error">{error}</Alert>}

        <Card>
          <CardBody className="space-y-4">
            <h2 className="text-sm font-semibold text-slate-900">你的 App</h2>

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
                label="App 名称 *"
                value={query}
                onChange={setQuery}
                onSelect={(r) => {
                  setSelected(r);
                  setQuery(r.name);
                }}
                country={countryCode}
              />
            )}

            <Field
              label="采集国家"
              hint="逗号分隔的国家代码，例如 us,gb,jp。App Store RSS 按国家分散，默认 us。"
            >
              <Input
                value={countries}
                onChange={(e) => setCountries(e.target.value)}
                placeholder="us"
              />
            </Field>

            <button
              type="button"
              className="text-sm text-brand hover:underline"
              onClick={() => setAdvanced((a) => !a)}
            >
              {advanced ? "收起高级模式" : "高级模式：手动粘贴链接"}
            </button>

            {advanced && (
              <div className="space-y-3 rounded-lg border border-border p-3">
                <Field label="App Store 链接">
                  <Input
                    value={appStoreUrl}
                    onChange={(e) => setAppStoreUrl(e.target.value)}
                    placeholder="https://apps.apple.com/..."
                  />
                </Field>
                <Field label="Google Play 链接">
                  <Input
                    value={googlePlayUrl}
                    onChange={(e) => setGooglePlayUrl(e.target.value)}
                    placeholder="https://play.google.com/store/apps/details?id=..."
                  />
                </Field>
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardBody className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900">
                竞品 App（可选，最多 3 个）
              </h2>
              <Button
                type="button"
                variant="secondary"
                onClick={addCompetitorRow}
                disabled={competitors.length >= 3}
              >
                + 添加竞品
              </Button>
            </div>

            {competitors.length === 0 && (
              <p className="text-sm text-muted">
                暂未添加竞品。也可以稍后在 App 详情页添加。
              </p>
            )}

            {competitors.map((c, idx) => (
              <div
                key={idx}
                className="space-y-2 rounded-lg border border-border p-3"
              >
                {c.selected ? (
                  <SelectedAppCard
                    selection={c.selected}
                    onClear={() => updateCompetitor(idx, { selected: null, query: "" })}
                  />
                ) : (
                  <AppSearchPicker
                    value={c.query}
                    onChange={(q) => updateCompetitor(idx, { query: q })}
                    onSelect={(r) =>
                      updateCompetitor(idx, { selected: r, query: r.name })
                    }
                    country={countryCode}
                    placeholder="搜索竞品名称…"
                  />
                )}
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => removeCompetitorRow(idx)}
                >
                  删除
                </Button>
              </div>
            ))}
          </CardBody>
        </Card>

        <div className="flex gap-3">
          <Button type="submit" loading={submitting}>
            创建并开始监控
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => router.push("/monitor")}
          >
            取消
          </Button>
        </div>
      </form>
    </div>
  );
}
