"use client";

// Shared minimal tooltip for the charts — tabular, restrained, no glow.
export default function ChartTooltip({ active, payload, label, unit }: any) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="tip">
      {label && <div className="tip-label">{label}</div>}
      {payload.map((p: any, i: number) => (
        <div className="tip-row" key={i}>
          <span className="tip-name" style={{ color: p.color || p.fill }}>
            {p.name}
          </span>
          <span className="tip-value num">
            {p.value == null ? "—" : Number(p.value).toLocaleString("en-US", { maximumFractionDigits: 0 })}
            {unit ? ` ${unit}` : ""}
          </span>
        </div>
      ))}
      <style jsx>{`
        .tip {
          background: var(--surface);
          color: var(--ink);
          border: 1px solid var(--border);
          border-radius: 8px;
          padding: 8px 11px;
          box-shadow: var(--shadow-2);
          font-size: 12.5px;
          min-width: 132px;
        }
        .tip-label {
          font-weight: 650;
          margin-bottom: 5px;
          color: var(--ink);
        }
        .tip-row {
          display: flex;
          justify-content: space-between;
          gap: 14px;
          padding: 1px 0;
        }
        .tip-name {
          font-weight: 550;
          opacity: 0.85;
        }
        .tip-value {
          color: var(--ink-2);
          font-weight: 650;
        }
      `}</style>
    </div>
  );
}