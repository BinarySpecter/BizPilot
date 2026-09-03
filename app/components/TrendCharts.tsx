"use client";

import type { Analysis } from "../lib/types";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceDot,
} from "recharts";
import ChartTooltip from "./ChartTooltip";
import { ArrowUpIcon, ArrowDownIcon } from "./icons";

const fmtDay = (iso: string) => {
  const d = new Date(iso.slice(0, 10) + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
};

const fmtAxis = (n: number, dollar = false) => {
  const sign = n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : `${Math.round(n)}`;
  return dollar ? `$${sign}` : sign;
};

// Last-14 vs prior-14 growth, computed live from the daily series (real data).
function rollingDelta(
  daily: { date: string; demand: number | null; revenue: number | null }[],
  field: "demand" | "revenue",
): number | null {
  const vals = daily.filter((d) => d[field] != null).map((d) => d[field]) as number[];
  if (vals.length < 28) return null;
  const last14 = vals.slice(-14).reduce((a, b) => a + b, 0);
  const prev14 = vals.slice(-28, -14).reduce((a, b) => a + b, 0);
  if (!prev14) return null;
  return ((last14 - prev14) / prev14) * 100;
}

const AXIS = { fontSize: 11, fill: "#98a0ab", fontWeight: 500 } as const;
const GRID = "#e6e1d6";

function DeltaTag({ value, suffix }: { value: number; suffix: string }) {
  const up = value >= 0;
  const Icon = up ? ArrowUpIcon : ArrowDownIcon;
  const tone = Math.abs(value) < 0.05 ? "flat" : up ? "teal" : "coral";
  return (
    <span className={`delta delta-${tone}`}>
      <Icon size={11} />
      {up ? "+" : ""}
      {value.toFixed(1)}%
      <span className="delta-suffix">{suffix}</span>
      <style jsx>{`
        .delta {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          font-weight: 650;
          font-variant-numeric: tabular-nums;
        }
        .delta-teal { color: var(--teal-ink); }
        .delta-coral { color: var(--coral-ink); }
        .delta-flat { color: var(--ink-3); }
        .delta-suffix {
          font-weight: 500;
          color: var(--ink-4);
          margin-left: 2px;
        }
      `}</style>
    </span>
  );
}

function Panel({
  title,
  sub,
  delta,
  foot,
  children,
}: {
  title: string;
  sub: string;
  delta?: number | null;
  foot: string;
  children: React.ReactNode;
}) {
  return (
    <div className="well chart-card">
      <div className="chart-head">
        <div>
          <div className="chart-title">{title}</div>
          <div className="chart-sub">{sub}</div>
        </div>
        {delta != null && delta !== 0 ? (
          <DeltaTag value={delta} suffix="vs prior 14d" />
        ) : delta === 0 ? (
          <DeltaTag value={0} suffix="vs prior 14d" />
        ) : null}
      </div>
      <div className="chart-canvas well-sunken">{children}</div>
      <div className="chart-foot mono num">{foot}</div>
      <style jsx>{`
        .chart-card {
          padding: 20px 22px 14px;
        }
        .chart-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 14px;
        }
        .chart-title {
          font-size: 15px;
          font-weight: 650;
          letter-spacing: -0.015em;
        }
        .chart-sub {
          margin-top: 2px;
          font-size: 12px;
          color: var(--ink-3);
        }
        .chart-canvas {
          padding: 12px 10px 4px 6px;
        }
        .chart-foot {
          margin-top: 10px;
          font-size: 11px;
          letter-spacing: 0.04em;
          color: var(--ink-4);
        }
      `}</style>
    </div>
  );
}

export function RevenueTrend({ analysis }: { analysis: Analysis }) {
  const days = analysis.trends.daily.slice(-30).filter((d) => d.revenue != null);
  const data = days.map((d) => ({ date: fmtDay(d.date), value: d.revenue ?? 0 }));
  const delta = rollingDelta(analysis.trends.daily, "revenue");

  return (
    <Panel
      title="Revenue trend"
      sub="daily revenue · last 30 days"
      delta={delta}
      foot="1 dot = 1 trading day · revenue USD"
    >
      <ResponsiveContainer width="100%" height={228}>
        <AreaChart data={data} margin={{ top: 6, right: 4, left: -14, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} strokeDasharray="2 5" />
          <XAxis dataKey="date" tick={AXIS} tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={40} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} width={52} tickFormatter={(n: number) => fmtAxis(n, true)} />
          <Tooltip content={<ChartTooltip unit="$" />} cursor={{ stroke: "#c9c5b8", strokeDasharray: "3 3", strokeWidth: 1 }} />
          <Area type="monotone" dataKey="value" name="Revenue" stroke="#315bff" strokeWidth={2} fill="#315bff" fillOpacity={0.05} activeDot={{ r: 3.5 }} />
        </AreaChart>
      </ResponsiveContainer>
    </Panel>
  );
}

export function DemandTrend({ analysis }: { analysis: Analysis }) {
  const days = analysis.trends.daily.slice(-30).filter((d) => d.demand != null);
  const data = days.map((d) => ({ date: fmtDay(d.date), value: d.demand ?? 0 }));
  const delta = rollingDelta(analysis.trends.daily, "demand");

  // Mark genuine total-scale anomalies on the series — real evidence, not decoration.
  const totalAnomalies = analysis.anomalies.filter((a) => a.scale === "total");
  const marks = totalAnomalies.flatMap((a) => {
    const pt = data.find((d) => d.date === fmtDay(a.date));
    return pt ? [{ x: fmtDay(a.date), y: pt.value }] : [];
  });

  return (
    <Panel
      title="Demand trend"
      sub="units sold per day · last 30 days"
      delta={delta}
      foot={`${analysis.trends.daily.filter((d) => d.demand != null).length} days of history${
        marks.length ? ` · ${marks.length} anomaly marked` : ""
      }`}
    >
      <ResponsiveContainer width="100%" height={228}>
        <AreaChart data={data} margin={{ top: 6, right: 4, left: -14, bottom: 0 }}>
          <CartesianGrid stroke={GRID} vertical={false} strokeDasharray="2 5" />
          <XAxis dataKey="date" tick={AXIS} tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={40} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} width={52} tickFormatter={(n: number) => fmtAxis(n)} />
          <Tooltip content={<ChartTooltip unit="units" />} cursor={{ stroke: "#c9c5b8", strokeDasharray: "3 3", strokeWidth: 1 }} />
          <Area type="monotone" dataKey="value" name="Units" stroke="#168c83" strokeWidth={2} fill="#168c83" fillOpacity={0.05} activeDot={{ r: 3.5 }} />
          {marks.map((m) => (
            <ReferenceDot key={m.x} x={m.x} y={m.y} r={4} fill="#e8753b" stroke="#fff" strokeWidth={1.5} />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </Panel>
  );
}