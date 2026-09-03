import type { Analysis } from "../lib/types";
import { formatNumber } from "../lib/api";
import { ArrowUpIcon, ArrowDownIcon } from "./icons";

const fmtDay = (iso: string) => {
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
};

// Attention feed — the strongest anomalies (ranked by deviation from the
// rolling baseline) that changed the demand pattern.
const LIMIT = 5;

export default function AnomalyPanel({ analysis }: { analysis: Analysis }) {
  const { anomalies } = analysis;
  const shown = anomalies.slice(0, LIMIT);
  const truncated = anomalies.length > LIMIT;

  return (
    <div className="anom" aria-label="What needs your attention">
      <div className="anom-head">
        <div>
          <h3 className="anom-title">What needs attention</h3>
        </div>
        <span className="tag tag-neutral">
          {anomalies.length ? `${anomalies.length} flagged` : "none detected"}
        </span>
      </div>
      <p className="anom-method">
        Robust rolling baseline (median + MAD, z ≥ 3) — {anomalies.length ? "real shifts, shown with evidence." : "no unusual patterns found."}
      </p>

      {anomalies.length === 0 ? (
        <div className="alert alert-success" style={{ margin: "0 26px 22px" }}>
          No unusual demand patterns detected within the threshold. The series is behaving along its baseline.
        </div>
      ) : (
        <>
          <ul className="anom-list">
            {shown.map((a) => {
              const Icon = a.direction === "up" ? ArrowUpIcon : ArrowDownIcon;
              const up = a.direction === "up";
              return (
                <li key={`${a.date}-${a.product}`} className="anom-row" data-dir={a.direction}>
                  <div className="anom-main">
                    <span className={`anom-mark ${up ? "mark-up" : "mark-down"}`}>
                      <Icon size={13} />
                    </span>
                    <div className="anom-body">
                      <div className="anom-top">
                        <span className="anom-product">{a.product === "All products" ? "Total sales" : a.product}</span>
                        <span className="anom-date mono num">{fmtDay(a.date)}</span>
                      </div>
                      <div className="anom-what num">
                        {formatNumber(a.observed)} units <span className="anom-vs">vs baseline {formatNumber(a.expected)}</span>
                        {a.direction === "up" && (a.multiplier ?? 0) >= 1.5 && (
                          <span className="anom-mult">{a.multiplier.toFixed(1)}×</span>
                        )}
                      </div>
                      <div className="anom-why">{a.why}</div>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
          {truncated && (
            <div className="anom-more mono">
              viewing top {shown.length} of {anomalies.length} · ranked by deviation from baseline
            </div>
          )}
        </>
      )}

      <style jsx>{`
        .anom {
          display: flex;
          flex-direction: column;
        }
        .anom-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 20px 26px 0;
        }
        .anom-title {
          font-size: 15px;
          font-weight: 660;
          letter-spacing: -0.015em;
        }
        .anom-method {
          padding: 6px 26px 16px;
          font-family: var(--font-mono);
          font-size: 11.5px;
          color: var(--ink-4);
          letter-spacing: 0.02em;
          line-height: 1.5;
        }
        .anom-list {
          list-style: none;
          margin: 0;
          padding: 0;
        }
        .anom-more {
          padding: 12px 26px;
          border-top: 1px solid var(--border);
          font-size: 10.5px;
          letter-spacing: 0.04em;
          color: var(--ink-4);
        }
        .anom-row {
          border-top: 1px solid var(--border);
        }
        .anom-main {
          display: grid;
          grid-template-columns: 26px minmax(0, 1fr);
          gap: 10px;
          padding: 12px 26px;
        }
        .anom-mark {
          margin-top: 1px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 20px;
          height: 20px;
          border-radius: var(--radius-sm);
          border: 1px solid var(--border);
          background: var(--surface-2);
        }
        .mark-up {
          color: var(--teal-ink);
          border-color: var(--teal-border);
          background: var(--teal-soft);
        }
        .mark-down {
          color: var(--coral-ink);
          border-color: var(--coral-border);
          background: var(--coral-soft);
        }
        .anom-top {
          display: flex;
          justify-content: space-between;
          gap: 10px;
          align-items: baseline;
        }
        .anom-product {
          font-size: 13.5px;
          font-weight: 620;
          color: var(--ink);
          letter-spacing: -0.01em;
        }
        .anom-date {
          font-size: 11.5px;
          color: var(--ink-4);
        }
        .anom-what {
          margin-top: 3px;
          font-size: 13px;
          font-weight: 600;
          color: var(--ink-2);
        }
        .anom-vs {
          font-weight: 450;
          color: var(--ink-3);
        }
        .anom-mult {
          margin-left: 8px;
          font-size: 11.5px;
          font-weight: 600;
          color: var(--coral-ink);
          background: var(--coral-soft);
          border: 1px solid var(--coral-border);
          padding: 1px 6px;
          border-radius: var(--radius-sm);
        }
        .anom-why {
          margin-top: 4px;
          font-size: 12.5px;
          color: var(--ink-3);
          line-height: 1.45;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        @media (max-width: 640px) {
          .anom-main,
          .anom-head,
          .anom-method,
          .anom-more {
            padding-left: 18px;
            padding-right: 18px;
          }
        }
      `}</style>
    </div>
  );
}