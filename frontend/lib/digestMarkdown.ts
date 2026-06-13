// 把周报渲染为 Markdown，供导出 / 复制（设计文档第 11.2 可导出 Markdown）。

import type { DigestReport, DigestSections, SectionItem } from "./types";
import { formatDay } from "./format";

const SECTION_TITLES: Record<keyof DigestSections, string> = {
  top_changes: "本周最重要的变化",
  new_complaints: "新增 / 增多的投诉",
  new_praise: "新增 / 增多的好评",
  rating_movement: "评分变化",
  release_impact: "发版影响",
  competitor_moves: "竞品动向",
  recommended_actions: "建议优先处理的事项",
  confidence_notes: "置信度提示",
};

// 固定顺序的 section 键，供页面与导出统一遍历（强类型）。
const SECTION_KEYS = Object.keys(SECTION_TITLES) as (keyof DigestSections)[];

export function itemToText(item: SectionItem | string): string {
  if (typeof item === "string") return item;
  const main =
    item.title ||
    item.change ||
    item.action ||
    item.note ||
    item.summary ||
    "";
  const analysis =
    item.strength || item.pain_point || item.detail || item.why || "";
  return analysis ? `${main} — ${analysis}` : main;
}

export function itemEvidence(item: SectionItem | string): number[] {
  if (typeof item === "string") return [];
  return item.evidence_review_ids || [];
}

export function digestToMarkdown(report: DigestReport): string {
  const lines: string[] = [];
  lines.push(`# ${report.title || `周报 #${report.id}`}`);
  lines.push("");
  lines.push(
    `> 周期：${formatDay(report.period_start)} ~ ${formatDay(report.period_end)} · 状态：${report.status}`
  );
  lines.push("");
  if (report.summary) {
    lines.push(report.summary);
    lines.push("");
  }

  for (const key of SECTION_KEYS) {
    const items = (report.sections?.[key] || []) as (SectionItem | string)[];
    if (!items.length) continue;
    lines.push(`## ${SECTION_TITLES[key]}`);
    lines.push("");
    for (const item of items) {
      const text = itemToText(item);
      const ev = itemEvidence(item);
      const evStr = ev.length ? `（证据 review: ${ev.join(", ")}）` : "";
      lines.push(`- ${text}${evStr}`);
    }
    lines.push("");
  }

  if (report.llm_model) {
    lines.push("---");
    lines.push(
      `_由 ${report.llm_model} 生成，tokens：${report.tokens_used}_`
    );
  }

  return lines.join("\n");
}

export { SECTION_TITLES, SECTION_KEYS };
