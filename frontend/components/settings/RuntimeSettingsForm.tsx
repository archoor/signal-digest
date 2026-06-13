// 运行配置表单：LLM / 邮件 / 调度（对接 PATCH /api/settings）。
"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { RuntimeSettings, RuntimeSettingsUpdate, ProxyTestResult } from "@/lib/types";
import {
  Alert,
  Button,
  Card,
  CardBody,
  Field,
  Input,
  Select,
  Spinner_Page,
} from "@/components/ui";

const WEEKDAYS = [
  { value: 0, label: "周一" },
  { value: 1, label: "周二" },
  { value: 2, label: "周三" },
  { value: 3, label: "周四" },
  { value: 4, label: "周五" },
  { value: 5, label: "周六" },
  { value: 6, label: "周日" },
];

type FormState = {
  llm_model: string;
  llm_classifier_model: string;
  llm_api_base: string;
  llm_timeout: string;
  llm_api_key: string;
  enable_llm_classification: boolean;
  classifier_batch_size: string;
  classifier_body_max_chars: string;
  email_provider: string;
  email_from: string;
  smtp_host: string;
  smtp_port: string;
  smtp_user: string;
  smtp_password: string;
  smtp_use_tls: boolean;
  resend_api_key: string;
  digest_recipient_email: string;
  default_country_codes: string;
  ingest_http_timeout: string;
  ingest_google_play_timeout: string;
  ingest_http_proxy: string;
  enable_scheduler: boolean;
  daily_ingest_hour: string;
  weekly_digest_weekday: string;
  weekly_digest_hour: string;
  notion_api_key: string;
  notion_reports_database_id: string;
  notion_title_property: string;
  notion_status_property: string;
  notion_period_property: string;
  notion_report_id_property: string;
  notion_auto_export: boolean;
};

function fromSettings(s: RuntimeSettings): FormState {
  return {
    llm_model: s.llm_model,
    llm_classifier_model: s.llm_classifier_model,
    llm_api_base: s.llm_api_base || "",
    llm_timeout: String(s.llm_timeout),
    llm_api_key: "",
    enable_llm_classification: s.enable_llm_classification,
    classifier_batch_size: String(s.classifier_batch_size),
    classifier_body_max_chars: String(s.classifier_body_max_chars),
    email_provider: s.email_provider,
    email_from: s.email_from,
    smtp_host: s.smtp_host || "",
    smtp_port: String(s.smtp_port),
    smtp_user: s.smtp_user || "",
    smtp_password: "",
    smtp_use_tls: s.smtp_use_tls,
    resend_api_key: "",
    digest_recipient_email: s.digest_recipient_email || "",
    default_country_codes: s.default_country_codes,
    ingest_http_timeout: String(s.ingest_http_timeout),
    ingest_google_play_timeout: String(s.ingest_google_play_timeout),
    ingest_http_proxy: s.ingest_http_proxy || "",
    enable_scheduler: s.enable_scheduler,
    daily_ingest_hour: String(s.daily_ingest_hour),
    weekly_digest_weekday: String(s.weekly_digest_weekday),
    weekly_digest_hour: String(s.weekly_digest_hour),
    notion_api_key: "",
    notion_reports_database_id: s.notion_reports_database_id || "",
    notion_title_property: s.notion_title_property,
    notion_status_property: s.notion_status_property || "",
    notion_period_property: s.notion_period_property || "",
    notion_report_id_property: s.notion_report_id_property || "",
    notion_auto_export: s.notion_auto_export,
  };
}

function toUpdate(form: FormState): RuntimeSettingsUpdate {
  const body: RuntimeSettingsUpdate = {
    llm_model: form.llm_model.trim(),
    llm_classifier_model: form.llm_classifier_model.trim(),
    llm_api_base: form.llm_api_base.trim() || null,
    llm_timeout: Number(form.llm_timeout),
    enable_llm_classification: form.enable_llm_classification,
    classifier_batch_size: Number(form.classifier_batch_size),
    classifier_body_max_chars: Number(form.classifier_body_max_chars),
    email_provider: form.email_provider,
    email_from: form.email_from.trim(),
    smtp_host: form.smtp_host.trim() || null,
    smtp_port: Number(form.smtp_port),
    smtp_user: form.smtp_user.trim() || null,
    smtp_use_tls: form.smtp_use_tls,
    digest_recipient_email: form.digest_recipient_email.trim() || null,
    default_country_codes: form.default_country_codes.trim(),
    ingest_http_timeout: Number(form.ingest_http_timeout),
    ingest_google_play_timeout: Number(form.ingest_google_play_timeout),
    ingest_http_proxy: form.ingest_http_proxy.trim() || null,
    enable_scheduler: form.enable_scheduler,
    daily_ingest_hour: Number(form.daily_ingest_hour),
    weekly_digest_weekday: Number(form.weekly_digest_weekday),
    weekly_digest_hour: Number(form.weekly_digest_hour),
    notion_reports_database_id: form.notion_reports_database_id.trim() || null,
    notion_title_property: form.notion_title_property.trim() || "Name",
    notion_status_property: form.notion_status_property.trim() || null,
    notion_period_property: form.notion_period_property.trim() || null,
    notion_report_id_property: form.notion_report_id_property.trim() || null,
    notion_auto_export: form.notion_auto_export,
  };
  if (form.llm_api_key.trim()) body.llm_api_key = form.llm_api_key.trim();
  if (form.smtp_password.trim()) body.smtp_password = form.smtp_password.trim();
  if (form.resend_api_key.trim())
    body.resend_api_key = form.resend_api_key.trim();
  if (form.notion_api_key.trim())
    body.notion_api_key = form.notion_api_key.trim();
  return body;
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardBody className="space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          {description && (
            <p className="mt-1 text-xs text-muted">{description}</p>
          )}
        </div>
        {children}
      </CardBody>
    </Card>
  );
}

export function RuntimeSettingsForm() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState(false);
  const [meta, setMeta] = useState<RuntimeSettings | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [proxyTesting, setProxyTesting] = useState(false);
  const [proxyTestResult, setProxyTestResult] = useState<ProxyTestResult | null>(
    null
  );

  useEffect(() => {
    api
      .getSettings()
      .then((s) => {
        setMeta(s);
        setForm(fromSettings(s));
      })
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "加载配置失败")
      )
      .finally(() => setLoading(false));
  }, []);

  function patch<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => (f ? { ...f, [key]: value } : f));
    setOk(false);
    if (key === "ingest_http_proxy") {
      setProxyTestResult(null);
    }
  }

  async function handleProxyTest() {
    if (!form) return;
    setProxyTesting(true);
    setProxyTestResult(null);
    try {
      const proxy = form.ingest_http_proxy.trim() || null;
      const result = await api.testProxyConnectivity(proxy);
      setProxyTestResult(result);
    } catch (err) {
      setProxyTestResult({
        ok: false,
        mode: form.ingest_http_proxy.trim() ? "proxy" : "direct",
        proxy: null,
        message: err instanceof ApiError ? err.message : "连通性测试失败",
        checks: [],
      });
    } finally {
      setProxyTesting(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setError(null);
    setOk(false);
    try {
      const updated = await api.updateSettings(toUpdate(form));
      setMeta(updated);
      setForm(fromSettings(updated));
      setOk(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Spinner_Page />;
  if (!form) {
    return error ? <Alert tone="error">{error}</Alert> : null;
  }

  return (
    <form onSubmit={handleSave} className="space-y-6">
      {error && <Alert tone="error">{error}</Alert>}
      {ok && (
        <Alert tone="success">
          配置已保存并生效（写入 {meta?.env_file}，调度任务已热重载）。
        </Alert>
      )}

      <Section
        title="LLM 配置"
        description="周报生成与评论分类使用的 LiteLLM 模型。未配置 API Key 时分类自动降级为规则兜底。"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="周报模型" hint="如 openai/gpt-4o-mini、deepseek/deepseek-chat">
            <Input
              value={form.llm_model}
              onChange={(e) => patch("llm_model", e.target.value)}
            />
          </Field>
          <Field label="分类模型" hint="日常轻量分类，建议选便宜模型">
            <Input
              value={form.llm_classifier_model}
              onChange={(e) => patch("llm_classifier_model", e.target.value)}
            />
          </Field>
          <Field label="API Base（可选）" hint="自定义代理或兼容端点">
            <Input
              value={form.llm_api_base}
              onChange={(e) => patch("llm_api_base", e.target.value)}
              placeholder="https://api.openai.com/v1"
            />
          </Field>
          <Field label="请求超时（秒）">
            <Input
              type="number"
              min={10}
              max={600}
              value={form.llm_timeout}
              onChange={(e) => patch("llm_timeout", e.target.value)}
            />
          </Field>
          <Field
            label="API Key"
            hint={
              meta?.llm_api_key_set
                ? "已配置。留空表示不修改。"
                : "未配置，填写后保存。"
            }
          >
            <Input
              type="password"
              value={form.llm_api_key}
              onChange={(e) => patch("llm_api_key", e.target.value)}
              placeholder={meta?.llm_api_key_set ? "••••••••" : ""}
              autoComplete="off"
            />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.enable_llm_classification}
            onChange={(e) =>
              patch("enable_llm_classification", e.target.checked)
            }
            className="rounded border-border"
          />
          启用 LLM 评论分类
        </label>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="分类批次大小">
            <Input
              type="number"
              min={1}
              max={100}
              value={form.classifier_batch_size}
              onChange={(e) => patch("classifier_batch_size", e.target.value)}
            />
          </Field>
          <Field label="单条评论截断长度">
            <Input
              type="number"
              min={100}
              max={5000}
              value={form.classifier_body_max_chars}
              onChange={(e) =>
                patch("classifier_body_max_chars", e.target.value)
              }
            />
          </Field>
        </div>
      </Section>

      <Section
        title="发件邮箱"
        description="周报发送通道。console 仅打印日志，适合本地开发；生产环境用 smtp 或 resend。"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="邮件 Provider">
            <Select
              value={form.email_provider}
              onChange={(e) => patch("email_provider", e.target.value)}
            >
              <option value="console">console（仅日志）</option>
              <option value="smtp">SMTP</option>
              <option value="resend">Resend</option>
            </Select>
          </Field>
          <Field label="发件人地址" hint="如 SignalDigest <noreply@example.com>">
            <Input
              value={form.email_from}
              onChange={(e) => patch("email_from", e.target.value)}
            />
          </Field>
        </div>

        {form.email_provider === "smtp" && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="SMTP 主机">
              <Input
                value={form.smtp_host}
                onChange={(e) => patch("smtp_host", e.target.value)}
                placeholder="smtp.example.com"
              />
            </Field>
            <Field label="SMTP 端口">
              <Input
                type="number"
                value={form.smtp_port}
                onChange={(e) => patch("smtp_port", e.target.value)}
              />
            </Field>
            <Field label="SMTP 用户名">
              <Input
                value={form.smtp_user}
                onChange={(e) => patch("smtp_user", e.target.value)}
              />
            </Field>
            <Field
              label="SMTP 密码"
              hint={
                meta?.smtp_password_set
                  ? "已配置。留空表示不修改。"
                  : "未配置"
              }
            >
              <Input
                type="password"
                value={form.smtp_password}
                onChange={(e) => patch("smtp_password", e.target.value)}
                autoComplete="off"
              />
            </Field>
            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input
                type="checkbox"
                checked={form.smtp_use_tls}
                onChange={(e) => patch("smtp_use_tls", e.target.checked)}
                className="rounded border-border"
              />
              使用 STARTTLS（587 端口通常为 true；465 SSL 请取消并改端口）
            </label>
          </div>
        )}

        {form.email_provider === "resend" && (
          <Field
            label="Resend API Key"
            hint={
              meta?.resend_api_key_set
                ? "已配置。留空表示不修改。"
                : "未配置"
            }
          >
            <Input
              type="password"
              value={form.resend_api_key}
              onChange={(e) => patch("resend_api_key", e.target.value)}
              autoComplete="off"
            />
          </Field>
        )}
        <Field
          label="周报接收邮箱"
          hint="审核通过后，周报将发送到此邮箱（全局统一配置）"
        >
          <Input
            type="email"
            value={form.digest_recipient_email}
            onChange={(e) => patch("digest_recipient_email", e.target.value)}
            placeholder="you@example.com"
          />
        </Field>
      </Section>

      <Section
        title="Notion 导出"
        description="周报导出到 Notion 数据库（Internal Integration）。配置保存后写入 .env，后续 Notion 功能上线即可直接使用。"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Integration API Key"
            hint={
              meta?.notion_api_key_set
                ? "已配置。留空表示不修改。"
                : "在 notion.so/profile/integrations 创建并复制 Secret"
            }
          >
            <Input
              type="password"
              value={form.notion_api_key}
              onChange={(e) => patch("notion_api_key", e.target.value)}
              placeholder={meta?.notion_api_key_set ? "••••••••" : ""}
              autoComplete="off"
            />
          </Field>
          <Field
            label="Reports 数据库 ID"
            hint="数据库 URL 中 32 位 ID；需将 Integration 连接到该库"
          >
            <Input
              value={form.notion_reports_database_id}
              onChange={(e) =>
                patch("notion_reports_database_id", e.target.value)
              }
              placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            />
          </Field>
          <Field label="标题列名" hint="Notion 数据库 Title 属性名，默认 Name">
            <Input
              value={form.notion_title_property}
              onChange={(e) => patch("notion_title_property", e.target.value)}
            />
          </Field>
          <Field label="Status 列名（可选）" hint="Select 类型，留空则不写入">
            <Input
              value={form.notion_status_property}
              onChange={(e) => patch("notion_status_property", e.target.value)}
            />
          </Field>
          <Field label="Period 列名（可选）" hint="Date 类型，留空则不写入">
            <Input
              value={form.notion_period_property}
              onChange={(e) => patch("notion_period_property", e.target.value)}
            />
          </Field>
          <Field label="Report ID 列名（可选）" hint="Number 类型，留空则不写入">
            <Input
              value={form.notion_report_id_property}
              onChange={(e) =>
                patch("notion_report_id_property", e.target.value)
              }
            />
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.notion_auto_export}
            onChange={(e) => patch("notion_auto_export", e.target.checked)}
            className="rounded border-border"
          />
          生成周报后自动导出到 Notion
        </label>
      </Section>

      <Section
        title="采集与网络"
        description="评论采集默认国家/超时，以及访问 iTunes / Google Play 的外网代理。留空代理则直连。"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="默认国家/地区"
            hint="逗号分隔 ISO 国家码，如 us,gb,jp"
          >
            <Input
              value={form.default_country_codes}
              onChange={(e) => patch("default_country_codes", e.target.value)}
              placeholder="us"
            />
          </Field>
          <Field label="RSS / HTTP 超时（秒）" hint="App Store RSS 等请求">
            <Input
              type="number"
              min={1}
              max={300}
              value={form.ingest_http_timeout}
              onChange={(e) => patch("ingest_http_timeout", e.target.value)}
            />
          </Field>
          <Field label="Google Play 超时（秒）" hint="Play 抓取较慢时可适当加大">
            <Input
              type="number"
              min={1}
              max={600}
              value={form.ingest_google_play_timeout}
              onChange={(e) =>
                patch("ingest_google_play_timeout", e.target.value)
              }
            />
          </Field>
        </div>
        <Field
          label="外网代理地址"
          hint="留空=直连。无认证：socks5://127.0.0.1:12080。带用户名密码：socks5://myuser:mypass@127.0.0.1:12080（密码含 @、: 等特殊字符需 URL 编码，如 p%40ss）"
        >
          <Input
            value={form.ingest_http_proxy}
            onChange={(e) => patch("ingest_http_proxy", e.target.value)}
            placeholder="socks5://myuser:mypass@127.0.0.1:12080"
            autoComplete="off"
          />
        </Field>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="secondary"
            loading={proxyTesting}
            onClick={handleProxyTest}
          >
            测试连通性
          </Button>
          <span className="text-xs text-muted">
            使用当前输入框中的地址测试，无需先保存。
          </span>
        </div>
        {proxyTestResult && (
          <div className="space-y-2">
            <Alert tone={proxyTestResult.ok ? "success" : "error"}>
              {proxyTestResult.message}
            </Alert>
            {proxyTestResult.checks.length > 0 && (
              <ul className="divide-y divide-border rounded-lg border border-border text-sm">
                {proxyTestResult.checks.map((check) => (
                  <li
                    key={check.name}
                    className="flex flex-wrap items-center justify-between gap-2 px-3 py-2"
                  >
                    <span className="font-medium">{check.name}</span>
                    <span className="text-muted">
                      {check.ok ? (
                        <>
                          可达
                          {check.status_code != null && ` · HTTP ${check.status_code}`}
                          {check.latency_ms != null && ` · ${check.latency_ms} ms`}
                        </>
                      ) : (
                        check.error || "不可达"
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Section>

      <Section
        title="调度参数"
        description="APScheduler 定时任务（UTC 时区）。修改后无需重启后端，会自动热重载 cron。"
      >
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.enable_scheduler}
            onChange={(e) => patch("enable_scheduler", e.target.checked)}
            className="rounded border-border"
          />
          启用自动调度（每日采集 + 每周周报）
        </label>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="每日采集时刻（UTC，0-23）">
            <Input
              type="number"
              min={0}
              max={23}
              value={form.daily_ingest_hour}
              onChange={(e) => patch("daily_ingest_hour", e.target.value)}
            />
          </Field>
          <Field label="周报生成日">
            <Select
              value={form.weekly_digest_weekday}
              onChange={(e) =>
                patch("weekly_digest_weekday", e.target.value)
              }
            >
              {WEEKDAYS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="周报生成时刻（UTC，0-23）">
            <Input
              type="number"
              min={0}
              max={23}
              value={form.weekly_digest_hour}
              onChange={(e) => patch("weekly_digest_hour", e.target.value)}
            />
          </Field>
        </div>
      </Section>

      <div className="flex gap-3">
        <Button type="submit" loading={saving}>
          保存配置
        </Button>
      </div>
    </form>
  );
}
