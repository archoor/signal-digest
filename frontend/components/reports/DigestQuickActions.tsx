// 周报列表行内快捷审核操作（图标按钮）。
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { actionTargetStatus, availableActions, type ReviewAction } from "@/lib/digestReview";
import type { DigestReport } from "@/lib/types";
import { ReviewActionButton } from "@/components/reports/digestIcons";

function actionVariant(
  action: ReviewAction
): "primary" | "secondary" | "ghost" | "danger" {
  if (action === "send" || action === "retry_send" || action === "approve")
    return "primary";
  if (action === "reject") return "danger";
  return "secondary";
}

export function DigestQuickActions({
  digest,
  recipientEmail,
  onDone,
}: {
  digest: DigestReport;
  recipientEmail: string | null;
  onDone: () => void;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);

  const actions = availableActions(digest.status).filter(
    (a) => a !== "reopen"
  );

  async function run(action: ReviewAction, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    setBusy(action);
    try {
      const target = actionTargetStatus(action);
      if (target) {
        if (digest.status === "draft" && target === "approved") {
          await api.updateDigest(digest.id, { status: "needs_review" });
        }
        await api.updateDigest(digest.id, { status: target });
      }
      if (action === "send" || action === "retry_send") {
        if (!recipientEmail) throw new ApiError(400, "未配置周报接收邮箱");
        await api.sendDigest(digest.id);
      }
      onDone();
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "操作失败");
    } finally {
      setBusy(null);
    }
  }

  if (actions.length === 0) {
    return (
      <div className="flex justify-end" onClick={(e) => e.stopPropagation()}>
        <ReviewActionButton
          action="detail"
          variant="ghost"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            router.push(`/reports/${digest.id}`);
          }}
        />
      </div>
    );
  }

  return (
    <div
      className="flex flex-wrap justify-end gap-1"
      onClick={(e) => e.stopPropagation()}
    >
      {actions.map((action) => (
        <ReviewActionButton
          key={action}
          action={action}
          variant={actionVariant(action)}
          loading={busy === action}
          disabled={
            !!busy ||
            ((action === "send" || action === "retry_send") && !recipientEmail)
          }
          onClick={(e) => run(action, e)}
        />
      ))}
      <ReviewActionButton
        action="detail"
        variant="ghost"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          router.push(`/reports/${digest.id}`);
        }}
      />
    </div>
  );
}
