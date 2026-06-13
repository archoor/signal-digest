// 侧边导航：管理后台主入口（设计文档第 11.1 页面）。
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "概览", icon: "M3 12l9-9 9 9M5 10v10h14V10" },
  {
    href: "/monitor",
    label: "App 监控",
    icon: "M4 6h16M4 12h16M4 18h16",
  },
  {
    href: "/reports",
    label: "周报",
    icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h7l5 5v11a2 2 0 01-2 2z",
  },
  {
    href: "/settings",
    label: "设置 / 用量",
    icon: "M10.3 4.3a2 2 0 013.4 0l.6 1a2 2 0 002 1l1.1-.1a2 2 0 011.8 3l-.5 1a2 2 0 000 2.2l.5 1a2 2 0 01-1.8 3l-1.1-.1a2 2 0 00-2 1l-.6 1a2 2 0 01-3.4 0l-.6-1a2 2 0 00-2-1l-1.1.1a2 2 0 01-1.8-3l.5-1a2 2 0 000-2.2l-.5-1a2 2 0 011.8-3l1.1.1a2 2 0 002-1l.6-1zM12 15a3 3 0 100-6 3 3 0 000 6z",
  },
];

export function Sidebar() {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname === href || pathname.startsWith(href + "/");
  }

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-card">
      <div className="flex items-center gap-2 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">
          S
        </div>
        <div>
          <div className="text-sm font-semibold leading-tight">SignalDigest</div>
          <div className="text-[11px] text-muted">App Reviews</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-indigo-50 text-brand"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              <svg
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d={item.icon} />
              </svg>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 text-[11px] leading-relaxed text-muted">
        主交付物是每周邮件周报，
        <br />
        本后台用于配置与审核。
      </div>
    </aside>
  );
}
