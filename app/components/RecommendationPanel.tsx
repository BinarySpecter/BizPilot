import type { Analysis, Priority, Recommendation } from "../lib/types";

const prioMeta: Record<Priority, { cls: string; label: string }> = {
  high: { cls: "prio-coral", label: "High" },
  medium: { cls: "prio-amber", label: "Medium" },
  low: { cls: "prio-neutral", label: "Low" },
};

// Every action visibly traces back to the computed signal that produced it.
const traceFor: Record<Recommendation["category"], string> = {
  inventory: "stock coverage & forecast signal",
  product: "demand change by product",
  anomaly: "anomaly detection · z ≥ 3",
  data: "data quality report",
  signal: "computed signals",
};

// Action Center — a prioritized queue. Order comes from the engine
// (highest priority first); each row shows the action, why, evidence and the
// signal it traces back to.
export default function RecommendationPanel({ analysis }: { analysis: Analysis }) {
  const recs = analysis.recommendations;
  const highCount = recs.filter((r) => r.priority === "high").length;

  return (
    <div className="well rec">
      <div className="rec-head">
        <span className="trace">
          <b>queue</b> prioritized · this week
        </span>
        <div className="rec-head-right">
          {highCount > 0 && <span className="tag tag-coral">{highCount} high</span>}
          <span className="tag tag-neutral">{recs.length} actions</span>
        </div>
      </div>

      {recs.length === 0 ? (
        <div className="alert alert-success" style={{ margin: "0 24px 22px" }}>
          No urgent actions right now. The data is broadly balanced.
        </div>
      ) : (
        <ol className="rec-list">
          {recs.map((r, i) => {
            const m = prioMeta[r.priority];
            return (
              <li key={`${i}-${r.title}`} className="rec-row" data-prio={r.priority}>
                <span className="rec-rank num" aria-hidden>
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div className="rec-main">
                  <div className="rec-top">
                    <span className="rec-title">{r.title}</span>
                    <span className={`rec-prio ${m.cls}`}>{m.label}</span>
                  </div>
                  <p className="rec-reason">{r.reason}</p>
                  <span className="trace">
                    <b>traces to</b> {traceFor[r.category]}
                  </span>
                </div>
                <div className="rec-evidence">
                  <span className="rec-ev-label">Evidence</span>
                  <span className="rec-ev-text mono num">{r.evidence}</span>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      <style jsx>{`
        .rec {
          overflow: hidden;
        }
        .rec-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 16px 26px;
          border-bottom: 1px solid var(--border);
        }
        .rec-head-right {
          display: flex;
          gap: 8px;
        }
        .rec-list {
          list-style: none;
          margin: 0;
          padding: 0;
        }
        .rec-row {
          display: grid;
          grid-template-columns: 46px minmax(0, 1fr) minmax(200px, 260px);
          gap: 20px;
          align-items: start;
          padding: 20px 26px;
          border-bottom: 1px solid var(--border);
        }
        .rec-row:last-child {
          border-bottom: 0;
        }
        .rec-row:hover {
          background: var(--surface-2);
        }
        .rec-rank {
          font-size: 22px;
          font-weight: 620;
          letter-spacing: -0.02em;
          line-height: 1;
          padding-top: 3px;
        }
        .rec-row[data-prio="high"] .rec-rank { color: var(--coral); }
        .rec-row[data-prio="medium"] .rec-rank { color: var(--amber); }
        .rec-row[data-prio="low"] .rec-rank { color: var(--ink-4); }
        .rec-top {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
        }
        .rec-title {
          font-size: 15px;
          font-weight: 640;
          letter-spacing: -0.014em;
          color: var(--ink);
        }
        .rec-prio {
          flex: none;
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          border-radius: var(--radius-sm);
          padding: 3px 8px;
          margin-top: 1px;
        }
        .prio-coral { color: var(--coral-ink); background: var(--coral-soft); }
        .prio-amber { color: var(--amber-ink); background: var(--amber-soft); }
        .prio-neutral { color: var(--ink-3); background: var(--surface-3); }
        .rec-reason {
          margin-top: 7px;
          font-size: 13.5px;
          line-height: 1.5;
          color: var(--ink-2);
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        .trace {
          margin-top: 8px;
        }
        .rec-evidence {
          display: flex;
          flex-direction: column;
          gap: 5px;
        }
        .rec-ev-label {
          font-family: var(--font-mono);
          font-size: 10.5px;
          font-weight: 500;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--ink-4);
        }
        .rec-ev-text {
          font-size: 12px;
          line-height: 1.55;
          color: var(--ink-2);
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          padding: 8px 11px;
        }
        @media (max-width: 900px) {
          .rec-row {
            grid-template-columns: 38px minmax(0, 1fr);
            gap: 14px;
          }
          .rec-evidence {
            grid-column: 2;
          }
        }
        @media (max-width: 640px) {
          .rec-row,
          .rec-head {
            padding-left: 18px;
            padding-right: 18px;
          }
        }
      `}</style>
    </div>
  );
}