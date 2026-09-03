"use client";

import type { Analysis } from "../lib/types";
import { formatNumber } from "../lib/api";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import ChartTooltip from "./ChartTooltip";
import { ArrowUpIcon, ArrowDownIcon, ArrowRightIcon } from "./icons";

const fmtDay = (iso: string) => {
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

const fmtAxis = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${Math.round(n)}`);

const ACTUAL_FILL = "#9aa2b3";
const FORECAST_FILL = "#315bff";

// Next-7-days as a decision tool: expected demand vs what's on the shelf.
export default function ForecastPanel({ analysis }: { analysis: Analysis }) {
  const fc = analysis.forecast;
  const inv = analysis.inventory;
  const ds = analysis.dataset;

  const past = analysis.trends.daily
    .filter((d) => d.demand != null)
    .slice(-14)
    .map((d) => ({ key: fmtDay(d.date), kind: "actual" as const, value: d.demand ?? 0 }));
  const future = (fc.values ?? []).map((v) => ({ key: fmtDay(v.date), kind: "forecast" as const, value: v.value }));
  const chart = [...past, ...future];
  const splitLabel = ds.date_max ? fmtDay(ds.date_max) : null;

  const coverageDays = inv.available
    ? (inv.total_stock ?? 0) / (((fc.total ?? 0) || 1) / 7)
    : null;

  const risk = coverageDays !== null && coverageDays < 7;
  const thin = coverageDays !== null && !risk && coverageDays < 14;

  let verdict: { cls: "teal" | "amber" | "coral" | "gray"; text: string } | null = null;
  if (!fc.available) verdict = null;
  else if (!inv.available) verdict = { cls: "gray", text: "Add an inventory file to see coverage." };
  else if (risk) verdict = { cls: "coral", text: "Stock may run short within the forecast window." };
  else if (thin) verdict = { cls: "amber", text: "Inventory is thin — review top-selling lines." };
  else verdict = { cls: "teal", text: "Stock covers projected demand across products." };

  const TrendGlyph =
    fc.trend_direction === "up" ? ArrowUpIcon : fc.trend_direction === "down" ? ArrowDownIcon : fc.trend_direction === "flat" ? ArrowRightIcon : null;
  const trendTone =
    fc.trend_direction === "up" ? "teal" : fc.trend_direction === "down" ? "coral" : "neutral";

  return (
    <div className="well fp">
      {!fc.available ? (
        <div className="alert alert-warn" style={{ margin: 18 }}>
          <strong>Forecast unavailable.</strong>{" "}
          <span>{fc.reason ?? "Not enough history to estimate the next 7 days."}</span>
        </div>
      ) : (
        <>
          <div className="fp-grid">
            <div className="fp-readout">
              <div className="row" style={{ gap: 10 }}>
                <span className="eyebrow">Next 7 days</span>
                {TrendGlyph && (
                  <span className="trend-tag" data-tone={trendTone}>
                    <TrendGlyph size={12} />
                    trending {fc.trend_direction}
                  </span>
                )}
              </div>

              <div className="fp-total num">
                {formatNumber(fc.total)}
                <span className="fp-unit">units</span>
              </div>
              <div className="fp-caption">expected demand · 7-day forecast</div>
              <div className="fp-range mono num">
                range {Math.round(fc.low ?? 0)}–{Math.round(fc.high ?? 0)} units
                <span className="fp-range-note"> · an estimate, not a guarantee</span>
              </div>

              <dl className="fp-points">
                <div className="fp-point">
                  <dt>Method</dt>
                  <dd className="mono">
                    {fc.method ? (fc.method.includes(" + ") ? fc.method.split(" + ").slice(0, 3).join(" + ") : fc.method) : "—"}
                  </dd>
                </div>
                <div className="fp-point">
                  <dt>History used</dt>
                  <dd className="mono">{fc.historical_days ?? "—"} days</dd>
                </div>
              </dl>
            </div>

            <div className="fp-chart">
              <div className="fp-canvas well-sunken">
                <ResponsiveContainer width="100%" height={208}>
                  <BarChart data={chart} margin={{ top: 6, right: 2, left: -16, bottom: 0 }} barCategoryGap="30%">
                    <CartesianGrid stroke="#e0dbcf" vertical={false} strokeDasharray="2 5" />
                    <XAxis dataKey="key" tick={{ fontSize: 10.5, fill: "#98a0ab" }} tickLine={false} axisLine={false} minTickGap={26} />
                    <YAxis tick={{ fontSize: 10.5, fill: "#98a0ab" }} tickLine={false} axisLine={false} width={44} tickFormatter={fmtAxis} />
                    <Tooltip content={<ChartTooltip unit="units" />} cursor={{ fill: "rgba(23,26,31,0.04)" }} />
                    {splitLabel && (
                      <ReferenceLine
                        x={splitLabel}
                        stroke="#8d928f"
                        strokeDasharray="3 3"
                        strokeWidth={1}
                        label={{ value: "now", position: "insideTopLeft", fill: "#8d928f", fontSize: 10, fontFamily: "var(--font-mono)", dy: 4 }}
                      />
                    )}
                    <Bar dataKey="value" name="Units" radius={[2, 2, 0, 0]}>
                      {chart.map((p, i) => (
                        <Cell key={i} fill={p.kind === "actual" ? ACTUAL_FILL : FORECAST_FILL} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="fp-legend">
                <span className="lg-item">
                  <i className="sw" style={{ background: ACTUAL_FILL }} /> actual · daily units
                </span>
                <span className="lg-item">
                  <i className="sw" style={{ background: FORECAST_FILL }} /> forecast · next 7 days
                </span>
              </div>
            </div>
          </div>

          <div className="fp-status">
            <div className="fp-stat">
              <span className="fp-stat-label">Current stock</span>
              <span className="fp-stat-value num">
                {inv.available ? `${formatNumber(inv.total_stock)} units` : "—"}
              </span>
              <span className="fp-stat-sub">{inv.available ? "on hand" : "no inventory file"}</span>
            </div>
            <div className="fp-stat">
              <span className="fp-stat-label">Coverage</span>
              <span className="fp-stat-value num" data-tone={risk ? "coral" : thin ? "amber" : "ok"}>
                {coverageDays != null ? `~${coverageDays.toFixed(1)} days` : "—"}
              </span>
              <span className="fp-stat-sub">at projected demand pace</span>
            </div>
            <div className="fp-verdict" data-tone={verdict?.cls ?? "gray"}>
              <span className={`dot dot-${verdict?.cls ?? "gray"}`} />
              <span className="fp-verdict-text">{verdict?.text}</span>
            </div>
          </div>
        </>
      )}

      <style jsx>{`
        .fp {
          overflow: hidden;
        }
        .fp-grid {
          display: grid;
          grid-template-columns: minmax(260px, 0.9fr) minmax(0, 1.35fr);
          gap: 24px;
        }
        .fp-readout {
          padding: 26px 0 18px 28px;
          display: flex;
          flex-direction: column;
        }
        .trend-tag {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          font-size: 11.5px;
          font-weight: 650;
          border-radius: var(--radius-sm);
          padding: 2px 8px;
          border: 1px solid var(--border);
          background: var(--surface-2);
          color: var(--ink-3);
          text-transform: capitalize;
        }
        .trend-tag[data-tone="teal"] {
          color: var(--teal-ink);
          border-color: var(--teal-border);
          background: var(--teal-soft);
        }
        .trend-tag[data-tone="coral"] {
          color: var(--coral-ink);
          border-color: var(--coral-border);
          background: var(--coral-soft);
        }
        .fp-total {
          margin-top: 14px;
          font-size: 54px;
          font-weight: 620;
          letter-spacing: -0.04em;
          line-height: 1;
          color: var(--ink);
        }
        .fp-unit {
          font-size: 16px;
          font-weight: 550;
          color: var(--ink-3);
          margin-left: 10px;
          letter-spacing: 0;
        }
        .fp-caption {
          margin-top: 8px;
          font-size: 13px;
          color: var(--ink-3);
        }
        .fp-range {
          margin-top: 14px;
          font-size: 12.5px;
          color: var(--blue-ink);
        }
        .fp-range-note {
          color: var(--ink-4);
        }
        .fp-points {
          margin: auto 0 0;
          padding-top: 20px;
          display: grid;
          gap: 8px;
        }
        .fp-point {
          display: grid;
          grid-template-columns: 88px 1fr;
          gap: 10px;
          font-size: 12px;
          align-items: baseline;
        }
        .fp-point dt {
          font-family: var(--font-mono);
          font-size: 11px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--ink-4);
        }
        .fp-point dd {
          margin: 0;
          color: var(--ink-2);
          font-size: 12px;
          line-height: 1.4;
        }
        .fp-chart {
          padding: 24px 24px 4px 0;
        }
        .fp-canvas {
          padding: 14px 10px 4px 4px;
        }
        .fp-legend {
          display: flex;
          gap: 18px;
          margin-top: 8px;
          padding-left: 6px;
        }
        .lg-item {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          font-size: 11.5px;
          color: var(--ink-3);
        }
        .sw {
          width: 10px;
          height: 10px;
          border-radius: 3px;
        }
        .fp-status {
          display: grid;
          grid-template-columns: 1fr 1fr 1.4fr;
          border-top: 1px solid var(--border);
          margin-top: 8px;
        }
        .fp-stat {
          display: flex;
          flex-direction: column;
          gap: 3px;
          padding: 18px 28px;
          border-right: 1px solid var(--border);
        }
        .fp-stat-label {
          font-family: var(--font-mono);
          font-size: 10.5px;
          font-weight: 500;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--ink-4);
        }
        .fp-stat-value {
          font-size: 20px;
          font-weight: 630;
          letter-spacing: -0.02em;
        }
        .fp-stat-value[data-tone="ok"] {
          color: var(--ink);
        }
        .fp-stat-value[data-tone="amber"] {
          color: var(--amber-ink);
        }
        .fp-stat-value[data-tone="coral"] {
          color: var(--coral-ink);
        }
        .fp-stat-sub {
          font-size: 12px;
          color: var(--ink-3);
        }
        .fp-verdict {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 18px 28px;
        }
        .fp-verdict-text {
          font-size: 14px;
          font-weight: 620;
          letter-spacing: -0.01em;
        }
        .fp-verdict[data-tone="teal"] .fp-verdict-text { color: var(--teal-ink); }
        .fp-verdict[data-tone="amber"] .fp-verdict-text { color: var(--amber-ink); }
        .fp-verdict[data-tone="coral"] .fp-verdict-text { color: var(--coral-ink); }
        .fp-verdict[data-tone="gray"] .fp-verdict-text { color: var(--ink-2); }

        @media (max-width: 980px) {
          .fp-grid {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          .fp-readout {
            padding: 22px 24px 8px;
          }
          .fp-chart {
            padding: 8px 24px 0;
          }
          .fp-status {
            grid-template-columns: 1fr 1fr;
          }
          .fp-verdict {
            grid-column: span 2;
            border-top: 1px solid var(--border);
          }
        }
        @media (max-width: 560px) {
          .fp-total {
            font-size: 44px;
          }
          .fp-status {
            grid-template-columns: 1fr;
          }
          .fp-verdict {
            grid-column: span 1;
          }
          .fp-stat {
            border-right: 0;
            border-bottom: 1px solid var(--border);
          }
        }
      `}</style>
    </div>
  );
}