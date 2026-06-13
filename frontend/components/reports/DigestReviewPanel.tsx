// 周报审核面板：流程步骤、编辑摘要、图标化审核操作（设计文档第 8.3）。
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import {
  availableActions,
  actionTargetStatus,
  REVIEW_STEPS,
  stepIndex,
  type ReviewAction,
} from "@/lib/digestReview";
import { formatDay, fromNow } from "@/lib/format";
import type { DigestReport, MonitoredApp } from "@/lib/types";
import {
  DigestStatusBadge,
  DigestStatusIcon,
  ReviewActionButton,
} from "@/components/reports/digestIcons";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  Field,
  Input,
  Textarea,
} from "@/components/ui";

interface Props {
  report: DigestReport;
  app: MonitoredApp | null;
  onUpdated: () => void;
}

function actionVariant(
  action: ReviewAction
): "primary" | "secondary" | "ghost" | "danger" {
  if (action === "send" || action === "retry_send" || action === "approve")
    return "primary";
  if (action === "reject") return "danger";
  return "secondary";
}

export function DigestReviewPanel({ report, app, onUpdated }: Props) {
  const [title, setTitle] = useState(report.title);
  const [summary, setSummary] = useState(report.summary);
  const [recipient, setRecipient] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<{
    tone: "success" | "error" | "info";
    text: string;
  } | null>(null);

  useEffect(() => {
    setTitle(report.title);
    setSummary(report.summary);
  }, [report.id, report.title, report.summary]);

  useEffect(() => {
    api
      .getSettings()
      .then((s) => setRecipient(s.digest_recipient_email))
      .catch(() => setRecipient(null));
  }, []);

  const actions = availableActions(report.status);
  const currentStep = stepIndex(report.status);
  const dirty = title !== report.title || summary !== report.summary;

  async function saveContent() {
    setBusy("save");
    setMessage(null);
    try {
      await api.updateDigest(report.id, {
        title: title.trim(),
        summary: summary.trim(),
      });
      onUpdated();
      setMessage({ tone: "success", text: "标题与摘要已保存。" });
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "保存失败",
      });
    } finally {
      setBusy(null);
    }
  }

  async function runAction(action: ReviewAction) {
    setBusy(action);
    setMessage(null);
    try {
      if (dirty) {
        await api.updateDigest(report.id, {
          title: title.trim(),
          summary: summary.trim(),
        });
      }

      const target = actionTargetStatus(action);
      if (target) {
        await api.updateDigest(report.id, { status: target });
      }

      if (action === "send" || action === "retry_send") {
        if (!recipient) {
          throw new ApiError(400, "未配置周报接收邮箱，请前往设置页配置");
        }
        const ok = await api.sendDigest(report.id);
        if (!ok.sent) {
          throw new ApiError(400, "发送未成功，请检查邮件配置");
        }
        setMessage({ tone: "success", text: `已发送至 ${recipient}` });
      } else {
        const labels: Partial<Record<ReviewAction, string>> = {
          submit_review: "已提交审核",
          approve: "审核已通过",
          reject: "已退回草稿",
          reopen: "已重新打开，可再次发送",
        };
        setMessage({
          tone: "success",
          text: labels[action] || "操作完成",
        });
      }
      onUpdated();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "操作失败",
      });
    } finally {
      setBusy(null);
    }
  }

  async function approveAndSend() {
    setBusy("approve_and_send");
    setMessage(null);
    try {
      if (!recipient) {
        throw new ApiError(400, "未配置周报接收邮箱，请前往设置页配置");
      }
      if (dirty) {
        await api.updateDigest(report.id, {
          title: title.trim(),
          summary: summary.trim(),
        });
      }
      if (report.status === "draft") {
        await api.updateDigest(report.id, { status: "needs_review" });
      }
      if (
        report.status === "draft" ||
        report.status === "needs_review" ||
        report.status === "failed"
      ) {
        await api.updateDigest(report.id, { status: "approved" });
      }
      const ok = await api.sendDigest(report.id);
      if (!ok.sent) throw new ApiError(400, "发送未成功");
      setMessage({ tone: "success", text: `已审核并发送至 ${recipient}` });
      onUpdated();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "操作失败",
      });
    } finally {
      setBusy(null);
    }
  }

  async function exportToNotion(force = false) {
    setBusy("notion");
    setMessage(null);
    try {
      if (dirty) {
        await api.updateDigest(report.id, {
          title: title.trim(),
          summary: summary.trim(),
        });
      }
      const updated = await api.exportDigestToNotion(report.id, force);
      setMessage({
        tone: "success",
        text: updated.notion_page_url
          ? "已推送到 Notion"
          : "未配置 Notion，已跳过",
      });
      onUpdated();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Notion 导出失败",
      });
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card className="mb-6">
      <CardBody className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">审核与发送</h2>
            <p className="mt-1 text-xs text-muted">
              悬停图标查看说明
            </p>
          </div>
          <DigestStatusBadge status={report.status} />
        </div>

        {/* 流程步骤条（图标） */}
        <div className="flex items-center gap-1">
          {REVIEW_STEPS.map((step, idx) => {
            const done = idx < currentStep;
            const active = idx === currentStep;
            const failed = report.status === "failed" && idx === 2;
            return (
              <div key={step.status} className="flex flex-1 items-center">
                <div className="flex flex-col items-center gap-1">
                  <div
                    title={step.label}
                    className={`flex h-8 w-8 items-center justify-center rounded-full ${
                      failed
                        ? "bg-red-100 text-red-700"
                        : done
                          ? "bg-emerald-100 text-emerald-700"
                          : active
                            ? "bg-indigo-100 text-brand"
                            : "bg-slate-100 text-slate-400"
                    }`}
                  >
                    {done ? (
                      <DigestStatusIcon status="approved" className="h-4 w-4" />
                    ) : (
                      <DigestStatusIcon status={step.status} className="h-4 w-4" />
                    )}
                  </div>
                </div>
                {idx < REVIEW_STEPS.length - 1 && (
                  <div
                    className={`mx-1 h-0.5 flex-1 ${
                      done ? "bg-emerald-200" : "bg-slate-200"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>

        {report.status === "failed" && (
          <Alert tone="error">
            上次发送失败。修正邮件配置后可重试发送，或退回草稿重新编辑。
          </Alert>
        )}

        <div className="rounded-lg border border-border bg-slate-50 px-4 py-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-muted">收件人</span>
            {recipient ? (
              <span className="font-medium">{recipient}</span>
            ) : (
              <span className="text-amber-700">
                未配置邮箱
                {" · "}
                <Link href="/settings" className="text-brand hover:underline">
                  去设置页
                </Link>
              </span>
            )}
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-muted">
            <span>
              周期：{formatDay(report.period_start)} ~{" "}
              {formatDay(report.period_end)}
            </span>
            {report.sent_at && <span>发送于 {fromNow(report.sent_at)}</span>}
            {report.llm_model && <Badge tone="purple">{report.llm_model}</Badge>}
            {report.notion_page_url && (
              <a
                href={report.notion_page_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand hover:underline"
              >
                在 Notion 中打开
              </a>
            )}
          </div>
        </div>

        {(report.status === "draft" ||
          report.status === "needs_review" ||
          report.status === "approved") && (
          <div className="space-y-3">
            <Field label="周报标题">
              <Input value={title} onChange={(e) => setTitle(e.target.value)} />
            </Field>
            <Field label="一句话摘要">
              <Textarea
                rows={3}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
              />
            </Field>
            {dirty && (
              <ReviewActionButton
                action="save"
                variant="secondary"
                loading={busy === "save"}
                disabled={!!busy}
                onClick={() => void saveContent()}
                className="!h-9 !w-9"
              />
            )}
          </div>
        )}

        {message && (
          <Alert tone={message.tone === "info" ? "info" : message.tone}>
            {message.text}
          </Alert>
        )}

        <div className="flex flex-wrap items-center gap-1.5 border-t border-border pt-4">
          {actions.map((action) => (
            <ReviewActionButton
              key={action}
              action={action}
              variant={actionVariant(action)}
              loading={busy === action}
              disabled={
                !!busy ||
                ((action === "send" || action === "retry_send") && !recipient)
              }
              onClick={() => runAction(action)}
            />
          ))}

          {(report.status === "needs_review" ||
            report.status === "draft" ||
            report.status === "failed") && (
            <ReviewActionButton
              action="approve_and_send"
              variant="primary"
              loading={busy === "approve_and_send"}
              disabled={!!busy || !recipient}
              onClick={approveAndSend}
            />
          )}

          {report.status === "sent" && (
            <span className="ml-1 text-xs text-muted">
              已发送 · 再次投递请先重新打开
            </span>
          )}

          <Button
            variant="secondary"
            loading={busy === "notion"}
            disabled={!!busy}
            onClick={() => exportToNotion(!!report.notion_page_url)}
            title={
              report.notion_page_url
                ? "重新创建 Notion 页面"
                : "推送到 Notion Weekly Reports 数据库"
            }
          >
            {report.notion_page_url ? "重新导出 Notion" : "导出到 Notion"}
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
