"use client";

import type { Analysis, LoadSource } from "../../lib/types";
import { formatNumber } from "../../lib/api";
import DashboardHeader from "../DashboardHeader";
import KpiBand from "../KpiBand";
import { RevenueTrend, DemandTrend } from "../TrendCharts";
import { ArrowRightIcon } from "../icons";

// Overview = command center. State, KPIs, forecast & coverage, the strongest
// signal, and the top action — plus a trend preview. Answers "what is
// happening and what should I care about" in one compact screen.
export default function OverviewView({ analysis, source }: { analysis: Analysis; source: LoadSource }) {
  const fc = analysis.forecast;
  const inv = analysis.inventory;
  const topAnom = analysis.anomalies[0] ?? null;
  const topRec = analysis.recommendations[0] ?? null;

  const coverageDays = inv.available ? (inv.total_stock ?? 0) / (((fc.total ?? 0) || 1) / 7) : null;
  const verdict =
    !fc.available
      ? null
      : !inv.available
        ? { tone: "gray" as const, text: "Add an inventory file to see coverage." }
        : coverageDays !== null && coverageDays < 7
          ? { tone: "coral" as const, text: "Stock may run short within the forecast window." }
          : coverageDays !== null && coverageDays < 14
            ? { tone: "amber" as const, text: "Inventory is thin — review top-selling lines." }
            : { tone: "teal" as const, text: "Stock covers projected demand." };

  return (
    <div className="view">
      <div className="dash-head">
        <DashboardHeader analysis={analysis} source={source} />
        <KpiBand analysis={analysis} />
      </div>

      <div className="cols ov-row">
        <div className="span-4">
          <div className="well mini">
            <div className="mini-head">
              <span className="mini-label">Forecast · next 7 days</span>
              <a className="mini-open" href="#/insights">
                open <ArrowRightIcon size={11} />
              </a>
            </div>
            {fc.available ? (
              <>
                <div className="mini-value num">
                  {formatNumber(fc.total)} <span className="mini-unit">units</span>
                </div>
                <div className="mini-sub mono num">
                  range {Math.round(fc.low ?? 0)}–{Math.round(fc.high ?? 0)} units · expected demand
                </div>
                {verdict && (
                  <div className="mini-verdict" data-tone={verdict.tone}>
                    <span className={`dot dot-${verdict.tone}`} />
                    <span>{verdict.text}</span>
                  </div>
                )}
              </>
            ) : (
              <div className="alert alert-warn">{fc.reason ?? "Forecast unavailable."}</div>
            )}
          </div>
        </div>

        <div className="span-4">
          <div className="well mini">
            <div className="mini-head">
              <span className="mini-label">Needs attention</span>
              <a className="mini-open" href="#/signals">
                open <ArrowRightIcon size={11} />
              </a>
            </div>
            {topAnom ? (
              <>
                <div className="mini-title">{topAnom.product === "All products" ? "Total sales" : topAnom.product}</div>
                <div className="mini-sub num">
                  {formatNumber(topAnom.observed)} units vs baseline {formatNumber(topAnom.expected)}
                </div>
                <div className="mini-verdict" data-tone={topAnom.direction === "up" ? "teal" : "coral"}>
                  <span className={`dot dot-${topAnom.direction === "up" ? "teal" : "coral"}`} />
                  <span>
                    {topAnom.direction === "up" ? "demand spike" : "demand dip"} · {topAnom.multiplier.toFixed(1)}× baseline
                  </span>
                </div>
              </>
            ) : (
              <div className="alert alert-success">No unusual demand patterns detected.</div>
            )}
          </div>
        </div>

        <div className="span-4">
          <div className="well mini">
            <div className="mini-head">
              <span className="mini-label">Recommended action</span>
              <a className="mini-open" href="#/actions">
                open <ArrowRightIcon size={11} />
              </a>
            </div>
            {topRec ? (
              <>
                <div className="mini-title">{topRec.title}</div>
                <div className="mini-ev mono num">{topRec.evidence}</div>
                <div className="mini-verdict" data-tone={topRec.priority === "high" ? "coral" : topRec.priority === "medium" ? "amber" : "gray"}>
                  <span className={`dot dot-${topRec.priority === "high" ? "coral" : topRec.priority === "medium" ? "amber" : "gray"}`} />
                  <span>{topRec.priority} priority</span>
                </div>
              </>
            ) : (
              <div className="alert alert-success">No urgent actions right now.</div>
            )}
          </div>
        </div>
      </div>

      <div className="cols ov-row">
        <div className="span-6">
          <RevenueTrend analysis={analysis} />
        </div>
        <div className="span-6">
          <DemandTrend analysis={analysis} />
        </div>
      </div>

      <style jsx>{`
        .ov-row {
          margin-top: 18px;
        }
        .mini {
          height: 100%;
          padding: 16px 18px 14px;
          display: flex;
          flex-direction: column;
          gap: 9px;
        }
        .mini-head {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          gap: 10px;
        }
        .mini-label {
          font-family: var(--font-mono);
          font-size: 10.5px;
          font-weight: 500;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: var(--ink-4);
        }
        .mini-open {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 11.5px;
          font-weight: 650;
          color: var(--blue-ink);
          text-decoration: none;
          white-space: nowrap;
        }
        .mini-open:hover {
          text-decoration: underline;
          text-underline-offset: 2px;
        }
        .mini-value {
          font-size: 30px;
          font-weight: 640;
          letter-spacing: -0.03em;
          color: var(--ink);
          line-height: 1.05;
        }
        .mini-unit {
          font-size: 12px;
          font-weight: 500;
          color: var(--ink-4);
          margin-left: 4px;
          letter-spacing: 0;
        }
        .mini-title {
          font-size: 14.5px;
          font-weight: 640;
          letter-spacing: -0.012em;
          color: var(--ink);
          line-height: 1.35;
        }
        .mini-sub {
          font-size: 12.5px;
          color: var(--ink-3);
          line-height: 1.45;
        }
        .mini-ev {
          font-size: 11.5px;
          line-height: 1.5;
          color: var(--ink-2);
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          padding: 6px 9px;
        }
        .mini-verdict {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12.5px;
          font-weight: 620;
          margin-top: auto;
          padding-top: 4px;
          letter-spacing: -0.01em;
        }
        .mini-verdict[data-tone="teal"] { color: var(--teal-ink); }
        .mini-verdict[data-tone="coral"] { color: var(--coral-ink); }
        .mini-verdict[data-tone="amber"] { color: var(--amber-ink); }
        .mini-verdict[data-tone="gray"] { color: var(--ink-2); }
      `}</style>
    </div>
  );
}