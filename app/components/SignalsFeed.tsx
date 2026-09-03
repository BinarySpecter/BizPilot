import type { Analysis } from "../lib/types";
import { formatNumber } from "../lib/api";
import { ArrowUpIcon, ArrowDownIcon, ArrowRightIcon } from "./icons";

// Signals rendered as a quiet decision feed: directional marker + evidence.
function marker(direction: "up" | "down" | "flat") {
  if (direction === "up") return { Icon: ArrowUpIcon, cls: "dir-up", label: "rising" };
  if (direction === "down") return { Icon: ArrowDownIcon, cls: "dir-down", label: "falling" };
  return { Icon: ArrowRightIcon, cls: "dir-flat", label: "steady" };
}

export default function SignalsFeed({ analysis }: { analysis: Analysis }) {
  const signals = analysis.signals;
  if (!signals.length) return null;

  const computedAt = analysis.meta.generated_at
    ? new Date(analysis.meta.generated_at).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : null;

  return (
    <div className="sig-feed" aria-label="Business signals">
      <div className="feed-head">
        <h3 className="feed-title">Signals</h3>
        <span className="feed-note">what the data changed</span>
      </div>

      <ul className="feed-list">
        {signals.map((s) => {
          const m = marker(s.direction);
          const meta =
            s.value_units != null
              ? `${formatNumber(s.value_units)} units`
              : s.change_pct != null && s.change_pct !== 0
                ? `${s.change_pct > 0 ? "+" : ""}${s.change_pct.toFixed(1)}%`
                : null;
          return (
            <li key={s.key} className="feed-row" data-dir={s.direction}>
              <span className="feed-mark" aria-label={m.label}>
                <m.Icon size={13} />
              </span>
              <div className="feed-body">
                <div className="feed-label">{s.label}</div>
                <div className="feed-phrase">{s.phrase}</div>
              </div>
              {meta && <span className="feed-meta num">{meta}</span>}
            </li>
          );
        })}
      </ul>

      {computedAt && (
        <div className="feed-foot mono">
          computed {computedAt} · from the analytics on this page
        </div>
      )}

      <style jsx>{`
        .sig-feed {
          display: flex;
          flex-direction: column;
        }
        .feed-head {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 12px;
          padding: 20px 26px;
          border-bottom: 1px solid var(--border);
        }
        .feed-title {
          font-size: 15px;
          font-weight: 660;
          letter-spacing: -0.015em;
        }
        .feed-note {
          font-family: var(--font-mono);
          font-size: 11px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--ink-4);
        }
        .feed-list {
          list-style: none;
          margin: 0;
          padding: 0;
          flex: 1;
        }
        .feed-row {
          display: grid;
          grid-template-columns: 26px minmax(0, 1fr) auto;
          gap: 11px;
          align-items: start;
          padding: 16px 26px;
          border-bottom: 1px solid var(--border);
        }
        .feed-row:last-child {
          border-bottom: 0;
        }
        .feed-mark {
          margin-top: 2px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 20px;
          height: 20px;
          border-radius: var(--radius-sm);
          border: 1px solid var(--border);
          background: var(--surface-2);
        }
        .feed-row[data-dir="up"] .feed-mark {
          color: var(--teal-ink);
          border-color: var(--teal-border);
          background: var(--teal-soft);
        }
        .feed-row[data-dir="down"] .feed-mark {
          color: var(--coral-ink);
          border-color: var(--coral-border);
          background: var(--coral-soft);
        }
        .feed-row[data-dir="flat"] .feed-mark {
          color: var(--ink-4);
        }
        .feed-label {
          font-size: 13.5px;
          font-weight: 620;
          color: var(--ink);
          letter-spacing: -0.01em;
        }
        .feed-phrase {
          margin-top: 2px;
          font-size: 13px;
          color: var(--ink-3);
          line-height: 1.45;
        }
        .feed-meta {
          font-size: 12px;
          font-weight: 600;
          color: var(--ink-2);
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          padding: 3px 8px;
          white-space: nowrap;
          margin-top: 1px;
        }
        .feed-foot {
          padding: 14px 26px;
          border-top: 1px solid var(--border);
          font-size: 11px;
          letter-spacing: 0.03em;
          color: var(--ink-4);
        }
        @media (max-width: 640px) {
          .feed-row,
          .feed-head,
          .feed-foot {
            padding-left: 18px;
            padding-right: 18px;
          }
        }
      `}</style>
    </div>
  );
}