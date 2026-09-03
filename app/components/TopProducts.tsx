import type { Analysis } from "../lib/types";
import { formatCurrency, formatNumber, formatPct } from "../lib/api";
import { ArrowUpIcon, ArrowDownIcon } from "./icons";

export default function TopProducts({ analysis }: { analysis: Analysis }) {
  const rows = analysis.products;
  if (!rows.length) return null;

  return (
    <div className="well tp">
      <div className="tp-head">
        <div>
          <h3 className="tp-title">Products</h3>
          <p className="tp-sub">The product-level evidence behind the forecast — momentum, stock, and projected coverage.</p>
        </div>
        <span className="tag tag-neutral">{rows.length} tracked</span>
      </div>

      <div className="tp-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th>Product</th>
              <th className="right">Units · 7d</th>
              <th className="right">14d change</th>
              <th className="right">Revenue</th>
              <th className="right">Stock</th>
              <th className="right">Coverage</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => {
              const up = (p.demand_change_pct ?? 0) >= 0;
              return (
                <tr key={p.name}>
                  <td>
                    <span className="pname">{p.name}</span>
                    {p.units_share_pct != null && (
                      <span className="pshare">· {formatPct(p.units_share_pct)} of units</span>
                    )}
                  </td>
                  <td className="right num">{formatNumber(p.units_7d)}</td>
                  <td className="right">
                    {p.demand_change_pct != null ? (
                      <span className={`chg ${up ? "chg-up" : "chg-down"}`}>
                        {up ? <ArrowUpIcon size={12} /> : <ArrowDownIcon size={12} />}
                        <span className="num">{formatPct(p.demand_change_pct)}</span>
                      </span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td className="right num">{formatCurrency(p.revenue)}</td>
                  <td className="right num">{p.stock != null ? formatNumber(p.stock) : <span className="muted">—</span>}</td>
                  <td className="right num">
                    {p.coverage_days != null ? (
                      <span className={`cov ${p.coverage_days < 7 ? "cov-low" : "cov-ok"}`}>~{p.coverage_days.toFixed(1)}d</span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td className="risk">
                    {p.coverage_days != null && p.coverage_days < 7 ? (
                      <span className="risk-txt risk-bad">Stock-out risk</span>
                    ) : p.demand_change_pct != null && p.demand_change_pct <= -25 ? (
                      <span className="risk-txt risk-warn">Declining</span>
                    ) : (
                      <span className="risk-txt risk-ok">OK</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <style jsx>{`
        .tp {
          overflow: hidden;
        }
        .tp-head {
          display: flex;
          align-items: flex-end;
          justify-content: space-between;
          gap: 16px;
          padding: 20px 22px 16px;
          border-bottom: 1px solid var(--border);
        }
        .tp-title {
          font-size: 15px;
          font-weight: 660;
          letter-spacing: -0.015em;
        }
        .tp-sub {
          margin-top: 3px;
          font-size: 13px;
          color: var(--ink-3);
        }
        .tp-wrap {
          overflow-x: auto;
        }
        .tbl {
          width: 100%;
          border-collapse: collapse;
          font-size: 13.5px;
        }
        .tbl th {
          text-align: left;
          font-family: var(--font-mono);
          font-size: 10.5px;
          font-weight: 500;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--ink-4);
          padding: 10px 14px;
          border-bottom: 1px solid var(--border);
          white-space: nowrap;
        }
        .tbl td {
          padding: 12px 14px;
          border-bottom: 1px solid var(--border);
          vertical-align: middle;
        }
        .tbl tbody tr {
          transition: background 0.15s ease;
        }
        .tbl tbody tr:hover {
          background: var(--surface-2);
        }
        .tbl tr:last-child td {
          border-bottom: 0;
        }
        .tbl th.right,
        .tbl td.right {
          text-align: right;
        }
        .pname {
          font-weight: 640;
          color: var(--ink);
          letter-spacing: -0.01em;
        }
        .pshare {
          color: var(--ink-3);
          font-size: 12.5px;
          margin-left: 2px;
        }
        .chg {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 13px;
          font-weight: 600;
        }
        .chg-up { color: var(--teal-ink); }
        .chg-down { color: var(--coral-ink); }
        .cov {
          font-weight: 650;
          font-size: 13.5px;
        }
        .cov-ok { color: var(--teal-ink); }
        .cov-low { color: var(--coral-ink); }
        .risk-txt {
          font-size: 12px;
          font-weight: 650;
          letter-spacing: 0.01em;
        }
        .risk-ok { color: var(--teal-ink); }
        .risk-warn { color: var(--amber-ink); }
        .risk-bad { color: var(--coral-ink); }
        @media (max-width: 640px) {
          .tp-head {
            padding-left: 18px;
            padding-right: 18px;
          }
        }
      `}</style>
    </div>
  );
}