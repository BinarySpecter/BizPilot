import type { Analysis } from "../lib/types";
import { formatCurrency, formatNumber } from "../lib/api";

// Primary metric + restrained readout cells, separated by vertical hairlines.
// Typography does the hierarchy work — no five identical cards.
export default function KpiBand({ analysis }: { analysis: Analysis }) {
  const { kpis } = analysis;
  const fc = analysis.forecast;
  const inv = analysis.inventory;

  const coverageDays = inv.available
    ? (inv.total_stock ?? 0) / (((fc.total ?? 0) || 1) / 7)
    : null;

  const fcValue = fc.available && fc.total != null ? fc.total.toLocaleString() : null;
  const fcRange = fc.available && fc.low != null ? `${Math.round(fc.low)}–${Math.round(fc.high)}` : null;

  return (
    <div className="kpi-band">
      <div className="kpi-hero">
        <span className="eyebrow">Total revenue</span>
        <div className="kpi-hero-value num">{formatCurrency(kpis.total_revenue)}</div>
        <div className="kpi-hero-sub">
          <span>
            last 7d <strong className="num">{formatCurrency(kpis.recent_7d_revenue)}</strong>
          </span>
          <span className="sep" aria-hidden />
          <span>
            last 30d <strong className="num">{formatCurrency(kpis.recent_30d_revenue)}</strong>
          </span>
        </div>
      </div>

      <div className="kpi-cell">
        <span className="kpi-label">Units sold</span>
        <span className="kpi-value num">{formatNumber(kpis.total_units)}</span>
        <span className="kpi-sub">last 7d {formatNumber(kpis.recent_7d_units)} units</span>
      </div>

      <div className="kpi-cell">
        <span className="kpi-label">Avg value / record</span>
        <span className="kpi-value num">{formatCurrency(kpis.avg_record_revenue)}</span>
        <span className="kpi-sub">{formatNumber(kpis.revenue_rows)} records</span>
      </div>

      <div className="kpi-cell">
        <span className="kpi-label">Forecast · 7 days</span>
        <span className="kpi-value num">
          {fcValue != null ? (
            <>
              {fcValue} <span className="kpi-unit">units</span>
            </>
          ) : (
            "—"
          )}
        </span>
        <span className="kpi-sub">{fcRange != null ? `range ${fcRange} units` : (fc.reason ?? "")}</span>
      </div>

      <div className="kpi-cell">
        <span className="kpi-label">Inventory coverage</span>
        <span className="kpi-value num" data-cov={coverageDays !== null && coverageDays < 7 ? "low" : "ok"}>
          {inv.available ? (
            coverageDays != null ? (
              <>
                ~{coverageDays.toFixed(1)} <span className="kpi-unit">days</span>
              </>
            ) : (
              "—"
            )
          ) : (
            "—"
          )}
        </span>
        <span className="kpi-sub">
          {inv.available ? `${formatNumber(inv.total_stock)} units on hand` : "no inventory data"}
        </span>
      </div>

      <style jsx>{`
        .kpi-band {
          display: grid;
          grid-template-columns: 2.05fr repeat(4, minmax(0, 1fr));
          gap: 0;
        }
        .kpi-hero {
          min-width: 0;
          padding: 22px 28px 22px 0;
          border-right: 1px solid var(--border);
        }
        .kpi-hero-value {
          margin-top: 8px;
          font-size: 46px;
          font-weight: 620;
          letter-spacing: -0.035em;
          line-height: 1;
          color: var(--ink);
        }
        .kpi-hero-sub {
          margin-top: 10px;
          font-size: 12.5px;
          color: var(--ink-3);
          display: flex;
          gap: 12px;
        }
        .kpi-hero-sub strong {
          color: var(--ink-2);
          font-weight: 650;
        }
        .kpi-hero-sub .sep {
          width: 1px;
          height: 12px;
          background: var(--border-strong);
          align-self: center;
        }
        .kpi-cell {
          min-width: 0;
          padding: 22px 20px;
          border-right: 1px solid var(--border);
          display: flex;
          flex-direction: column;
          justify-content: center;
          gap: 7px;
        }
        .kpi-cell:last-child {
          border-right: 0;
        }
        .kpi-label {
          font-family: var(--font-mono);
          font-size: 11px;
          font-weight: 500;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--ink-3);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .kpi-value {
          font-size: 22px;
          font-weight: 630;
          letter-spacing: -0.02em;
          line-height: 1.05;
          color: var(--ink);
        }
        .kpi-value[data-cov="low"] {
          color: var(--coral-ink);
        }
        .kpi-value[data-cov="ok"] {
          color: var(--ink);
        }
        .kpi-unit {
          font-size: 12px;
          font-weight: 500;
          color: var(--ink-4);
        }
        .kpi-sub {
          font-size: 12px;
          color: var(--ink-3);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        @media (max-width: 1180px) {
          .kpi-band {
            grid-template-columns: 1fr 1fr;
            row-gap: 0;
          }
          .kpi-hero {
            grid-column: span 2;
            border-right: 0;
            border-bottom: 0;
            padding-bottom: 20px;
          }
          .kpi-cell {
            border-top: 1px solid var(--border);
          }
          .kpi-cell:nth-child(2n) {
            border-right: 1px solid var(--border);
          }
          .kpi-cell:nth-child(2n + 1) {
            border-right: 0;
          }
        }
        @media (max-width: 640px) {
          .kpi-hero-value {
            font-size: 38px;
          }
          .kpi-hero {
            padding: 18px 0;
          }
          .kpi-cell {
            padding: 16px 0;
          }
        }
      `}</style>
    </div>
  );
}