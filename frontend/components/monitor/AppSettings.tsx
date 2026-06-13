// App 配置编辑（设计文档第 10.1 PATCH /apps/{id}）。
"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { AppSearchResult, MonitoredApp, MonitorStatus } from "@/lib/types";
import { PLATFORM_LABEL } from "@/lib/format";
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
  Field,
  Input,
  Select,
} from "@/components/ui";

function toDateInput(value: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString().slice(0, 10);
}

function applySearchToPlatforms(
  current: { appStoreUrl: string; googlePlayUrl: string },
  result: AppSearchResult
) {
  return {
    appStoreUrl: result.app_store_url || current.appStoreUrl,
    googlePlayUrl: result.google_play_url || current.googlePlayUrl,
  };
}

export function AppSettings({
  app,
  onUpdated,
}: {
  app: MonitoredApp;
  onUpdated: (app: MonitoredApp) => void;
}) {
  const [name, setName] = useState(app.name);
  const [appStoreUrl, setAppStoreUrl] = useState(app.app_store_url || "");
  const [googlePlayUrl, setGooglePlayUrl] = useState(app.google_play_url || "");
  const [countries, setCountries] = useState(app.country_codes.join(", "));
  const [status, setStatus] = useState<MonitorStatus>(app.status);
  const [releaseDate, setReleaseDate] = useState(
    toDateInput(app.last_release_date)
  );
  const [searchQuery, setSearchQuery] = useState("");
  const [searchPick, setSearchPick] = useState<AppSearchResult | null>(null);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);

  useEffect(() => {
    setName(app.name);
    setAppStoreUrl(app.app_store_url || "");
    setGooglePlayUrl(app.google_play_url || "");
    setCountries(app.country_codes.join(", "));
    setStatus(app.status);
    setReleaseDate(toDateInput(app.last_release_date));
    setSearchQuery("");
    setSearchPick(null);
  }, [app.id, app.name, app.app_store_url, app.google_play_url, app.country_codes, app.status, app.last_release_date]);

  const countryCode = countries.split(",")[0]?.trim().toLowerCase() || "us";

  function handleSearchSelect(result: AppSearchResult) {
    setSearchPick(result);
    setSearchQuery(result.name);
    const next = applySearchToPlatforms(
      { appStoreUrl, googlePlayUrl },
      result
    );
    setAppStoreUrl(next.appStoreUrl);
    setGooglePlayUrl(next.googlePlayUrl);
    if (result.name && !name.trim()) {
      setName(result.name);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setOk(false);

    if (!appStoreUrl.trim() && !googlePlayUrl.trim()) {
      setError("至少保留 App Store 或 Google Play 其中一个平台链接");
      return;
    }

    setSaving(true);
    try {
      const updated = await api.updateApp(app.id, {
        name: name.trim(),
        app_store_url: appStoreUrl.trim() || null,
        google_play_url: googlePlayUrl.trim() || null,
        country_codes: countries
          .split(",")
          .map((c) => c.trim().toLowerCase())
          .filter(Boolean),
        status,
        last_release_date: releaseDate
          ? new Date(releaseDate + "T00:00:00").toISOString()
          : null,
      });
      onUpdated(updated);
      setOk(true);
      setSearchPick(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="max-w-2xl">
      <CardBody>
        <form onSubmit={handleSave} className="space-y-4">
          {error && <Alert tone="error">{error}</Alert>}
          {ok && <Alert tone="success">已保存。</Alert>}

          <Field label="App 名称">
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>

          <div className="rounded-lg border border-border bg-slate-50/80 p-4 space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                平台链接
              </h3>
              <p className="mt-1 text-xs text-muted">
                可修改已有链接，或补充缺失的平台。留空并保存会清除对应平台。
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                {app.app_store_id && (
                  <Badge tone="blue">{PLATFORM_LABEL.app_store} 已配置</Badge>
                )}
                {app.google_play_package && (
                  <Badge tone="green">{PLATFORM_LABEL.google_play} 已配置</Badge>
                )}
                {!app.app_store_id && !app.google_play_package && (
                  <span className="text-xs text-amber-700">尚未配置任何平台</span>
                )}
              </div>
            </div>

            <Field
              label="App Store 链接"
              hint="例如 https://apps.apple.com/us/app/id123456789"
            >
              <Input
                value={appStoreUrl}
                onChange={(e) => setAppStoreUrl(e.target.value)}
                placeholder="https://apps.apple.com/..."
              />
            </Field>

            <Field
              label="Google Play 链接"
              hint="例如 https://play.google.com/store/apps/details?id=com.example"
            >
              <Input
                value={googlePlayUrl}
                onChange={(e) => setGooglePlayUrl(e.target.value)}
                placeholder="https://play.google.com/store/apps/details?id=..."
              />
            </Field>

            <div className="border-t border-border pt-4">
              <p className="mb-2 text-xs font-medium text-slate-700">
                或按名称搜索补充
              </p>
              {searchPick ? (
                <SelectedAppCard
                  selection={searchPick}
                  onClear={() => {
                    setSearchPick(null);
                    setSearchQuery("");
                  }}
                />
              ) : (
                <AppSearchPicker
                  value={searchQuery}
                  onChange={setSearchQuery}
                  onSelect={handleSearchSelect}
                  country={countryCode}
                  placeholder="搜索 App 名称，自动填入双平台链接…"
                />
              )}
            </div>
          </div>

          <Field label="采集国家" hint="逗号分隔的国家代码，例如 us,gb,jp。">
            <Input
              value={countries}
              onChange={(e) => setCountries(e.target.value)}
            />
          </Field>

          <Field label="监控状态">
            <Select
              value={status}
              onChange={(e) => setStatus(e.target.value as MonitorStatus)}
            >
              <option value="active">监控中</option>
              <option value="paused">已暂停</option>
              <option value="error">异常</option>
            </Select>
          </Field>

          <Field
            label="最近发版日期"
            hint="发版后 7 天为发版窗口，会提高采集频率与低分告警敏感度。"
          >
            <Input
              type="date"
              value={releaseDate}
              onChange={(e) => setReleaseDate(e.target.value)}
            />
          </Field>

          <Button type="submit" loading={saving}>
            保存配置
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}
