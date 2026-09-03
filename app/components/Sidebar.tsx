"use client";

import type { Analysis, LoadSource } from "../lib/types";
import type { ViewId } from "../lib/useView";

const NAV: { id: ViewId; index: string; label: string }[] = [
  { id: "overview", index: "01", label: "Overview" },
  { id: "signals", index: "02", label: "Signals" },
  { id: "insights", index: "03", label: "Insights" },
  { id: "actions", index: "04", label: "Actions" },
  { id: "simulate", index: "05", label: "Simulate" },
  { id: "ask", index: "06", label: "Ask Business" },
];

const fmtShort = (iso: string | null | undefined) => {
  if (!iso) return "—";
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

// Persistent application navigation. Active view is marked; live counts come
// straight from the loaded analysis (no fabricated numbers).
export default function Sidebar({
  analysis,
  source,
  active,
}: {
  analysis: Analysis;
  source: LoadSource;
  active: ViewId;
}) {
  const flagged = analysis.anomalies.length;
  const actions = analysis.recommendations.length;

  const counts: Partial<Record<ViewId, number>> = {
    signals: flagged,
    actions,
  };

  return (
    <aside className="sidebar" aria-label="Workspace navigation">
      <div className="sidebar-head">Workspace</div>
      <nav className="side-nav">
        {NAV.map((n) => {
          const count = counts[n.id];
          return (
            <a
              key={n.id}
              href={`#/${n.id}`}
              className={`side-item${active === n.id ? " is-active" : ""}`}
              aria-current={active === n.id ? "page" : undefined}
            >
              <span className="side-index num">{n.index}</span>
              <span className="side-label">{n.label}</span>
              {count != null && count > 0 && <span className="side-count num">{count}</span>}
            </a>
          );
        })}
      </nav>
      <div className="sidebar-foot">
        <span className="dot dot-teal" />
        <div>
          <span className="side-foot-name num">{analysis.dataset.name}</span>
          <span className="side-foot-meta mono">
            {source === "sample" ? "demo data · " : ""}
            {analysis.dataset.date_min && analysis.dataset.date_max
              ? `${fmtShort(analysis.dataset.date_min)} – ${fmtShort(analysis.dataset.date_max)}`
              : ""}
          </span>
        </div>
      </div>
    </aside>
  );
}