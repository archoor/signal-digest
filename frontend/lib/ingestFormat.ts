// 采集结果文案格式化。
import type { IngestResult } from "./types";
import { PLATFORM_LABEL } from "./format";

export function formatIngestMessage(result: IngestResult): {
  tone: "success" | "error" | "info";
  text: string;
} {
  const { fetched, inserted, classified, warnings = [] } = result;

  let tone: "success" | "error" | "info" = "success";
  if (fetched === 0 && warnings.length > 0) {
    tone = "error";
  } else if (fetched > 0 && inserted === 0) {
    tone = "info";
  }

  const lines = [
    `采集完成：抓取 ${fetched} 条，新增 ${inserted} 条，分类 ${classified} 条。`,
  ];

  if (result.platforms?.length) {
    for (const p of result.platforms) {
      if (p.status === "skipped") continue;
      const label =
        PLATFORM_LABEL[p.platform as keyof typeof PLATFORM_LABEL] || p.platform;
      if (p.status === "error") {
        lines.push(`· ${label}：失败${p.message ? ` — ${p.message}` : ""}`);
      } else {
        lines.push(`· ${label}：抓取 ${p.fetched}，新增 ${p.inserted}`);
      }
    }
  }

  for (const w of warnings) {
    if (!lines.some((l) => l.includes(w))) {
      lines.push(`⚠ ${w}`);
    }
  }

  return { tone, text: lines.join("\n") };
}
