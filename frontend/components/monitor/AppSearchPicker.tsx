// App 名称搜索下拉（App Store + Google Play）。
"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { PLATFORM_LABEL } from "@/lib/format";
import type { AppSearchResult } from "@/lib/types";
import { Badge, Field, Input } from "@/components/ui";

export function AppSearchPicker({
  label,
  value,
  onChange,
  onSelect,
  country = "us",
  placeholder = "输入 App 名称搜索…",
}: {
  label?: string;
  value: string;
  onChange: (name: string) => void;
  onSelect: (result: AppSearchResult) => void;
  country?: string;
  placeholder?: string;
}) {
  const [results, setResults] = useState<AppSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (value.trim().length < 2) {
      setResults([]);
      return;
    }
    const t = setTimeout(() => {
      setLoading(true);
      setError(null);
      api
        .searchApps(value.trim(), country, 10)
        .then((r) => {
          setResults(r);
          setOpen(true);
        })
        .catch((e) =>
          setError(e instanceof ApiError ? e.message : "搜索失败")
        )
        .finally(() => setLoading(false));
    }, 300);
    return () => clearTimeout(t);
  }, [value, country]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const field = (
    <div ref={wrapRef} className="relative">
      <Input
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => results.length > 0 && setOpen(true)}
        placeholder={placeholder}
        autoComplete="off"
      />
      {loading && (
        <span className="absolute right-3 top-2.5 text-xs text-muted">
          搜索中…
        </span>
      )}
      {open && results.length > 0 && (
        <ul className="absolute z-20 mt-1 max-h-72 w-full overflow-auto rounded-lg border border-border bg-white py-1 shadow-lg">
          {results.map((r, idx) => (
            <li key={`${r.name}-${idx}`}>
              <button
                type="button"
                className="flex w-full items-start gap-3 px-3 py-2.5 text-left hover:bg-slate-50"
                onClick={() => {
                  onSelect(r);
                  setOpen(false);
                }}
              >
                {r.icon_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={r.icon_url}
                    alt=""
                    className="h-10 w-10 shrink-0 rounded-lg"
                  />
                ) : (
                  <div className="h-10 w-10 shrink-0 rounded-lg bg-slate-100" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-slate-900">{r.name}</div>
                  {r.developer && (
                    <div className="truncate text-xs text-muted">
                      {r.developer}
                    </div>
                  )}
                  <div className="mt-1 flex flex-wrap gap-1">
                    {r.platforms.includes("app_store") && (
                      <Badge tone="blue">{PLATFORM_LABEL.app_store}</Badge>
                    )}
                    {r.platforms.includes("google_play") && (
                      <Badge tone="green">{PLATFORM_LABEL.google_play}</Badge>
                    )}
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  if (label) {
    return (
      <Field label={label}>
        {field}
        {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      </Field>
    );
  }

  return (
    <div>
      {field}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function SelectedAppCard({
  selection,
  onClear,
}: {
  selection: AppSearchResult;
  onClear?: () => void;
}) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-indigo-100 bg-indigo-50/50 p-3">
      {selection.icon_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={selection.icon_url}
          alt=""
          className="h-12 w-12 rounded-xl"
        />
      ) : (
        <div className="h-12 w-12 rounded-xl bg-white" />
      )}
      <div className="min-w-0 flex-1">
        <div className="font-semibold text-slate-900">{selection.name}</div>
        {selection.developer && (
          <div className="text-sm text-muted">{selection.developer}</div>
        )}
        <div className="mt-2 flex flex-wrap gap-1">
          {selection.app_store_id && (
            <Badge tone="blue">
              {PLATFORM_LABEL.app_store} · {selection.app_store_id}
            </Badge>
          )}
          {selection.google_play_package && (
            <Badge tone="green">
              {PLATFORM_LABEL.google_play} · {selection.google_play_package}
            </Badge>
          )}
        </div>
      </div>
      {onClear && (
        <button
          type="button"
          onClick={onClear}
          className="text-sm text-muted hover:text-slate-900"
        >
          更换
        </button>
      )}
    </div>
  );
}
