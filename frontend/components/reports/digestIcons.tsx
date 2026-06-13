// 周报审核状态与操作的 SVG 图标（无第三方依赖）。
"use client";

import type { DigestStatus } from "@/lib/types";
import {
  ACTION_LABEL,
  DIGEST_STATUS_LABEL,
  type ReviewAction,
} from "@/lib/digestReview";

type IconProps = { className?: string };

function Svg({
  className,
  children,
}: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      className={className ?? "h-4 w-4"}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {children}
    </svg>
  );
}

/** 周报状态图标 */
export function DigestStatusIcon({
  status,
  className,
}: IconProps & { status: DigestStatus }) {
  switch (status) {
    case "draft":
      return (
        <Svg className={className}>
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
          <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
        </Svg>
      );
    case "needs_review":
      return (
        <Svg className={className}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v4l2.5 2.5" />
        </Svg>
      );
    case "approved":
      return (
        <Svg className={className}>
          <path d="M9 12l2 2 4-4" />
          <circle cx="12" cy="12" r="9" />
        </Svg>
      );
    case "sent":
      return (
        <Svg className={className}>
          <path d="M22 2L11 13" />
          <path d="M22 2l-7 20-4-9-9-4 20-7z" />
        </Svg>
      );
    case "failed":
      return (
        <Svg className={className}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v5M12 16h.01" />
        </Svg>
      );
    default:
      return null;
  }
}

const STATUS_TONE: Record<
  DigestStatus,
  { bg: string; text: string }
> = {
  draft: { bg: "bg-slate-100", text: "text-slate-600" },
  needs_review: { bg: "bg-amber-100", text: "text-amber-700" },
  approved: { bg: "bg-blue-100", text: "text-blue-700" },
  sent: { bg: "bg-emerald-100", text: "text-emerald-700" },
  failed: { bg: "bg-red-100", text: "text-red-700" },
};

/** 仅图标的周报状态徽章，hover 显示文字说明 */
export function DigestStatusBadge({
  status,
  size = "md",
}: {
  status: DigestStatus;
  size?: "sm" | "md";
}) {
  const tone = STATUS_TONE[status] ?? STATUS_TONE.draft;
  const dim = size === "sm" ? "h-6 w-6" : "h-7 w-7";
  const icon = size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";
  return (
    <span
      title={DIGEST_STATUS_LABEL[status]}
      className={`inline-flex ${dim} items-center justify-center rounded-full ${tone.bg} ${tone.text}`}
    >
      <DigestStatusIcon status={status} className={icon} />
    </span>
  );
}

/** 审核操作图标 */
export function ReviewActionIcon({
  action,
  className,
}: IconProps & {
  action: ReviewAction | "approve_and_send" | "detail" | "save";
}) {
  switch (action) {
    case "submit_review":
      return (
        <Svg className={className}>
          <path d="M12 19V5M5 12l7-7 7 7" />
        </Svg>
      );
    case "approve":
      return (
        <Svg className={className}>
          <path d="M20 6L9 17l-5-5" />
        </Svg>
      );
    case "reject":
      return (
        <Svg className={className}>
          <path d="M18 6L6 18M6 6l12 12" />
        </Svg>
      );
    case "reopen":
      return (
        <Svg className={className}>
          <path d="M3 12a9 9 0 0115-6.7L21 8" />
          <path d="M21 3v5h-5M21 12a9 9 0 01-15 6.7L3 16" />
          <path d="M3 21v-5h5" />
        </Svg>
      );
    case "send":
      return (
        <Svg className={className}>
          <path d="M22 2L11 13" />
          <path d="M22 2l-7 20-4-9-9-4 20-7z" />
        </Svg>
      );
    case "retry_send":
      return (
        <Svg className={className}>
          <path d="M3 12a9 9 0 0115-6.7L21 8" />
          <path d="M21 3v5h-5" />
          <path d="M22 2L11 13" />
        </Svg>
      );
    case "approve_and_send":
      return (
        <Svg className={className}>
          <path d="M20 6L9 17l-5-5" />
          <path d="M22 2L11 13" />
        </Svg>
      );
    case "detail":
      return (
        <Svg className={className}>
          <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z" />
          <circle cx="12" cy="12" r="3" />
        </Svg>
      );
    case "save":
      return (
        <Svg className={className}>
          <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z" />
          <path d="M17 21v-8H7v8M7 3v5h8" />
        </Svg>
      );
    default:
      return null;
  }
}

const ACTION_LABEL_EXT: Record<
  ReviewAction | "approve_and_send" | "detail" | "save",
  string
> = {
  ...ACTION_LABEL,
  approve_and_send: "审核并发送",
  detail: "查看详情",
  save: "保存标题与摘要",
};

type ActionKind = ReviewAction | "approve_and_send" | "detail" | "save";

/** 图标操作按钮（title 作 tooltip） */
export function ReviewActionButton({
  action,
  onClick,
  disabled,
  loading,
  variant = "secondary",
  className,
}: {
  action: ActionKind;
  onClick?: (e: React.MouseEvent) => void;
  disabled?: boolean;
  loading?: boolean;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  className?: string;
}) {
  const styles = {
    primary:
      "bg-brand text-white hover:bg-[var(--brand-hover)] border-transparent",
    secondary: "bg-white text-slate-700 border-border hover:bg-slate-50",
    ghost: "bg-transparent text-slate-600 border-transparent hover:bg-slate-100",
    danger: "bg-red-50 text-red-600 border-red-200 hover:bg-red-100",
  };

  return (
    <button
      type="button"
      title={ACTION_LABEL_EXT[action]}
      aria-label={ACTION_LABEL_EXT[action]}
      disabled={disabled || loading}
      onClick={onClick}
      className={`inline-flex h-8 w-8 items-center justify-center rounded-lg border transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${styles[variant]} ${className ?? ""}`}
    >
      {loading ? (
        <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
          />
        </svg>
      ) : (
        <ReviewActionIcon action={action} />
      )}
    </button>
  );
}

/** 筛选 Tab 用状态图标 */
export function StatusFilterIcon({
  filter,
  className,
}: IconProps & {
  filter: "all" | "pending" | DigestStatus;
}) {
  switch (filter) {
    case "all":
      return (
        <Svg className={className}>
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </Svg>
      );
    case "pending":
      return (
        <Svg className={className}>
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </Svg>
      );
    default:
      return <DigestStatusIcon status={filter} className={className} />;
  }
}

export const STATUS_FILTER_LABEL: Record<
  "all" | "pending" | DigestStatus,
  string
> = {
  all: "全部",
  pending: "待处理",
  ...DIGEST_STATUS_LABEL,
};
