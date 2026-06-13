// 周报审核流程工具（设计文档第 8.3：draft → needs_review → approved → sent）。

import type { DigestStatus } from "./types";

export const DIGEST_STATUS_LABEL: Record<DigestStatus, string> = {
  draft: "草稿",
  needs_review: "待审核",
  approved: "已审核",
  sent: "已发送",
  failed: "发送失败",
};

/** 审核流程步骤（不含 failed） */
export const REVIEW_STEPS: { status: DigestStatus; label: string }[] = [
  { status: "draft", label: "草稿" },
  { status: "needs_review", label: "待审核" },
  { status: "approved", label: "已审核" },
  { status: "sent", label: "已发送" },
];

/** 后端允许的状态流转 */
export const ALLOWED_TRANSITIONS: Record<DigestStatus, DigestStatus[]> = {
  draft: ["draft", "needs_review"],
  needs_review: ["needs_review", "draft", "approved"],
  approved: ["approved", "needs_review"],
  sent: ["sent", "approved"],
  failed: ["failed", "approved"],
};

export function canTransition(from: DigestStatus, to: DigestStatus): boolean {
  return ALLOWED_TRANSITIONS[from]?.includes(to) ?? false;
}

export function stepIndex(status: DigestStatus): number {
  if (status === "failed") return 2; // 显示在「已审核」步骤，提示异常
  const idx = REVIEW_STEPS.findIndex((s) => s.status === status);
  return idx >= 0 ? idx : 0;
}

export type ReviewAction =
  | "submit_review"
  | "approve"
  | "reject"
  | "reopen"
  | "send"
  | "retry_send";

export function availableActions(status: DigestStatus): ReviewAction[] {
  switch (status) {
    case "draft":
      return ["submit_review"];
    case "needs_review":
      return ["approve", "reject"];
    case "approved":
      return ["send", "reject"];
    case "sent":
      return ["reopen"];
    case "failed":
      return ["retry_send", "reject"];
    default:
      return [];
  }
}

export function actionTargetStatus(action: ReviewAction): DigestStatus | null {
  switch (action) {
    case "submit_review":
      return "needs_review";
    case "approve":
    case "retry_send":
      return "approved";
    case "reject":
      return "draft";
    case "reopen":
      return "approved";
    default:
      return null;
  }
}

export const ACTION_LABEL: Record<ReviewAction, string> = {
  submit_review: "提交审核",
  approve: "审核通过",
  reject: "退回草稿",
  reopen: "重新打开（可再发送）",
  send: "发送邮件",
  retry_send: "重试发送",
};
