import type { Analysis, LoadSource } from "../lib/types";
import { formatNumber } from "../lib/api";
import { ArrowRightIcon } from "./icons";

const fmtShort = (iso: string | null | undefined) => {
  if (!iso) return "—";
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

function daySpan(a: string | null | undefined, b: string | null | undefined): number | null {
  if (!a || !b) return null;
  const dA = new Date(a.slice(0, 10) + "T00:00:00").getTime();
  const dB = new Date(b.slice(0, 10) + "T00:00:00").getTime();
  if (Number.isNaN(dA) || Number.isNaN(dB)) return null;
  return Math.round((dB - dA) / 86_400_000) + 1;
}

// Names the active workspace: dataset · date range · data quality.
// Sits directly on the page canvas — no floating box.
export default function DashboardHeader({ analysis, source }: { analysis: Analysis; source: LoadSource }) {
  const ds = analysis.dataset;
  const q = analysis.data_quality;
  const span = daySpan(ds.date_min, ds.date_max);
  const keptPct = q.rows_in_source ? Math.round((q.rows_kept / q.rows_in_source) * 100) : 100;
  const dropped = q.dropped_rows > 0;

  const rangeLine = [
    ds.date_min && ds.date_max ? `${fmtShort(ds.date_min)} – ${fmtShort(ds.date_max)}` : null,
    span ? `${span} days` : null,
    `${formatNumber(q.rows_kept)} rows`,
    `${formatNumber(ds.n_products)} products`,
  ]
    .filter(Boolean)
    .join(" · ");

  const topAction = analysis.recommendations[0] ?? null;

  return (
    <div className="mast">
      <div className="mast-row">
        <div className="mast-id">
          <div className="row" style={{ gap: 10 }}>
            <span className="dot dot-teal" />
            <span className="mast-name num">{ds.name}</span>
            {source === "sample" && (
              <span className="tag tag-amber" style={{ marginLeft: 2 }}>
                Demo data
              </span>
            )}
            {dropped && <span className="tag tag-coral">{q.dropped_rows} rows cleaned</span>}
            {q.inventory_warning && (
              <span className="tag tag-amber" title={q.inventory_warning}>
                Inventory skipped
              </span>
            )}
          </div>
          <div className="mast-line mono">
            <span>{rangeLine}</span>
          </div>
        </div>

        <div className="mast-quality">
          <span className="eyebrow">Data quality</span>
          <span className="mast-quality-value num" data-good={!dropped}>
            {keptPct}%
          </span>
          <span className="mast-quality-sub">
            {dropped ? `${q.dropped_pct.toFixed(0)}% dropped` : "clean — nothing dropped"}
          </span>
        </div>
      </div>

      {topAction && (
        <a className="read-link" href="#/actions" aria-label={`Recommended action: ${topAction.title}`}>
          <span className="read-label">Recommended</span>
          <span className="read-text">{topAction.title}</span>
          <ArrowRightIcon size={13} />
        </a>
      )}

      <style jsx>{`
        .mast {
          padding: 34px 0 26px;
        }
        .mast-row {
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          gap: 24px;
          flex-wrap: wrap;
        }
        .mast-name {
          font-size: 22px;
          font-weight: 650;
          letter-spacing: -0.02em;
          color: var(--ink);
        }
        .mast-line {
          margin-top: 9px;
          font-size: 12px;
          color: var(--ink-3);
          letter-spacing: 0.02em;
        }
        .mast-line span + span {
          margin-left: 18px;
        }
        .mast-quality {
          display: flex;
          align-items: baseline;
          gap: 10px;
          padding-bottom: 4px;
        }
        .mast-quality .eyebrow {
          letter-spacing: 0.14em;
        }
        .mast-quality-value {
          font-size: 22px;
          font-weight: 600;
          letter-spacing: -0.02em;
        }
        .mast-quality-value[data-good="true"] {
          color: var(--teal-ink);
        }
        .mast-quality-value:not([data-good="true"]) {
          color: var(--coral-ink);
        }
        .mast-quality-sub {
          font-size: 12px;
          color: var(--ink-4);
        }
        .read-link {
          margin-top: 16px;
        }
        @media (max-width: 640px) {
          .mast {
            padding-top: 24px;
          }
          .read-link {
            max-width: 100%;
          }
        }
      `}</style>
    </div>
  );
}