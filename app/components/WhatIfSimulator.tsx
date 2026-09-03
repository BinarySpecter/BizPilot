"use client";

import { useEffect, useState } from "react";
import type { Analysis, SimulationResult } from "../lib/types";
import { simulateScenario, formatNumber } from "../lib/api";
import { ArrowRightIcon } from "./icons";

export default function WhatIfSimulator({ analysis }: { analysis: Analysis }) {
  const [scenarioType, setScenarioType] = useState<"demand" | "inventory">("demand");
  const [pct, setPct] = useState(20);
  const [product, setProduct] = useState("");
  const [result, setResult] = useState<SimulationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const hasInventory = analysis.inventory.available === true;
  const disabled = scenarioType === "inventory" && !hasInventory;

  const run = async () => {
    if (disabled) return;
    setBusy(true);
    setError(null);
    try {
      const r = await simulateScenario(analysis, {
        type: scenarioType,
        adjustment_pct: pct,
        product: product || undefined,
      });
      setResult(r);
    } catch (e: any) {
      setError(e?.message ?? "Simulation failed.");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (disabled) return;
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioType, pct, product, disabled]);

  const o = result?.outputs;
  const scopeLabel = product || "All products";
  const isDemand = scenarioType === "demand";
  const pctLabel = `${pct > 0 ? "+" : ""}${pct}%`;
  const fill = `${((pct + 50) / 150) * 100}%`;

  const baselineValue = isDemand ? result?.inputs.baseline_forecast_units : result?.inputs.current_stock_units;
  const adjustedValue = isDemand ? o?.adjusted_forecast_units : o?.adjusted_stock_units;
  const changeValue = isDemand ? o?.forecast_change_units : o?.stock_change_units;
  const scenarioLabel = `${isDemand ? "Demand" : "Inventory"} ${pctLabel} · ${scopeLabel}`;

  return (
    <div className="well sim">
      <div className="sim-body">
        <div className="row-between sim-frame">
          <p className="sim-question">
            What happens if <strong className="num">{isDemand ? "demand" : "inventory"} {pctLabel}</strong> for <strong>{scopeLabel}</strong>?
          </p>
          <span className="sim-meta mono">scenario · not a prediction</span>
        </div>

        <div className="sim-controls">
          <label className="field sim-scope">
            <span className="field-label">Scope</span>
            <select className="select" value={product} onChange={(e) => setProduct(e.target.value)}>
              <option value="">All products</option>
              {(analysis.dataset.product_names ?? []).map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>

          <div className="seg" role="tablist" aria-label="Scenario type">
            <button
              type="button"
              role="tab"
              aria-selected={scenarioType === "demand"}
              className={`seg-btn${scenarioType === "demand" ? " seg-on" : ""}`}
              onClick={() => setScenarioType("demand")}
            >
              Demand changes
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={scenarioType === "inventory"}
              className={`seg-btn${scenarioType === "inventory" ? " seg-on" : ""}`}
              onClick={() => setScenarioType("inventory")}
              disabled={!hasInventory}
              title={hasInventory ? undefined : "No inventory data uploaded"}
            >
              Inventory changes
            </button>
          </div>

          <label className="field grow">
            <span className="row-between field-label">
              <span>{isDemand ? "Demand adjustment" : "Inventory adjustment"}</span>
              <span className="sim-pct num">{pctLabel}</span>
            </span>
            <input
              type="range"
              className="range"
              min={-50}
              max={100}
              step={5}
              value={pct}
              style={{ ["--range-fill" as string]: fill }}
              onChange={(e) => setPct(Number(e.target.value))}
              aria-label="Adjustment percentage"
            />
          </label>

          <button type="button" className="btn btn-ghost sim-recompute" onClick={run} disabled={busy || disabled}>
            Recompute
          </button>
        </div>

        {disabled && (
          <div className="alert alert-warn">
            Add an inventory CSV to run inventory scenarios. Demand scenarios still work.
          </div>
        )}
        {error && <div className="alert alert-error">{error}</div>}

        {result && !error && (
          <div className="sim-out">
            <div className="sim-compare">
              <div className="sc-cell">
                <span className="sc-label">Baseline</span>
                <span className="sc-value num">
                  {formatNumber(baselineValue)} <span className="sc-unit">units</span>
                </span>
                <span className="sc-sub">{isDemand ? "7-day forecast" : "total stock"}</span>
              </div>

              <div className="sc-arrow">
                <ArrowRightIcon size={16} />
              </div>

              <div className="sc-cell sc-res">
                <span className="sc-label">Scenario</span>
                <span className="sc-value num sc-adj">
                  {formatNumber(adjustedValue)} <span className="sc-unit">units</span>
                </span>
                <span className="sc-sub sc-sub-tight">{scenarioLabel}</span>
              </div>

              <div className="sc-arrow">
                <span className="sc-diff num">
                  {changeValue != null && changeValue > 0 ? "+" : ""}
                  {formatNumber(changeValue)}
                </span>
              </div>

              <div className="sc-cell">
                <span className="sc-label">Net change</span>
                <span className="sc-value num" data-sign={changeValue !== null && changeValue !== undefined && changeValue > 0 ? "pos" : "neg"}>
                  {changeValue != null && changeValue > 0 ? "+" : ""}
                  {formatNumber(changeValue)} <span className="sc-unit">units</span>
                </span>
                <span className="sc-sub">vs baseline</span>
              </div>
            </div>

            {(o?.baseline_coverage_days != null || o?.coverage_days != null) && hasInventory && (
              <div className="sim-conseq">
                <span className="sim-conseq-label">Consequence</span>
                <div className="sim-cover">
                <div className="cov-row">
                  <span className="cov-label mono">Coverage · baseline</span>
                  <span className="cov-value num">
                    {o?.baseline_coverage_days != null ? `~${o.baseline_coverage_days.toFixed(1)} days` : "—"}
                  </span>
                </div>
                <div className="cov-row cov-main">
                  <span className="cov-label mono">Coverage · scenario</span>
                  <span className={`cov-value num ${o && o.coverage_days != null && o.coverage_days < 7 ? "risk" : "ok"}`}>
                    {o?.coverage_days != null ? `~${o.coverage_days.toFixed(1)} days` : "—"}
                  </span>
                </div>
                <div className="cov-row">
                  <span className="cov-label mono">Stock gap under scenario</span>
                  <span className="cov-value num">{formatNumber(o?.stock_gap_units)} units</span>
                </div>
                </div>
              </div>
            )}

            {o?.stock_risk ? (
              <div className="alert alert-warn sim-alert">
                {o.alert ?? "Stock would drop below the projected demand window under this scenario."}
              </div>
            ) : o && hasInventory && o.baseline_coverage_days != null ? (
              <div className="alert alert-success sim-alert">
                Stock remains above projected demand for {scopeLabel} under this scenario.
              </div>
            ) : null}
          </div>
        )}
      </div>

      <style jsx>{`
        .sim {
          overflow: hidden;
        }
        .sim-body {
          padding: 22px 26px 26px;
        }
        .sim-frame {
          margin-bottom: 18px;
          align-items: baseline;
        }
        .sim-question {
          font-size: 15px;
          font-weight: 580;
          letter-spacing: -0.012em;
          color: var(--ink);
        }
        .sim-question strong {
          font-weight: 670;
          color: var(--blue-ink);
          font-variant-numeric: tabular-nums;
        }
        .sim-meta {
          font-size: 11px;
          color: var(--ink-4);
          letter-spacing: 0.03em;
          white-space: nowrap;
        }
        .sim-controls {
          display: grid;
          grid-template-columns: auto minmax(0, 1fr) auto;
          grid-template-areas:
            "scope scope scope"
            "seg range recompute";
          gap: 14px 16px;
          align-items: end;
        }
        .sim-scope {
          grid-area: scope;
          justify-self: start;
          width: min(240px, 100%);
        }
        .sim-scope .select {
          width: 100%;
        }
        .seg {
          grid-area: seg;
        }
        .grow {
          grid-area: range;
        }
        .sim-recompute {
          grid-area: recompute;
        }
        .sim-pct {
          font-size: 13px;
          font-weight: 650;
          color: var(--blue-ink);
        }
        .sim-out {
          margin-top: 22px;
          border-top: 1px solid var(--border);
          padding-top: 20px;
        }
        .sim-compare {
          display: grid;
          grid-template-columns: 1fr auto 1fr auto 1fr;
          gap: 10px;
          align-items: center;
        }
        .sc-cell {
          display: flex;
          flex-direction: column;
          gap: 4px;
          padding: 14px 16px;
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
        }
        .sc-label {
          font-family: var(--font-mono);
          font-size: 10.5px;
          font-weight: 500;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--ink-4);
        }
        .sc-value {
          font-size: 21px;
          font-weight: 640;
          letter-spacing: -0.02em;
          color: var(--ink);
          margin-top: 2px;
        }
        .sc-unit {
          font-size: 12px;
          font-weight: 500;
          color: var(--ink-4);
        }
        .sc-sub {
          font-size: 11.5px;
          color: var(--ink-3);
        }
        .sc-sub-tight {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .sc-res {
          border-color: var(--blue-border);
          background: var(--blue-soft);
        }
        .sc-res .sc-value {
          color: var(--blue-ink);
        }
        .sc-arrow {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 2px;
          color: var(--ink-4);
        }
        .sc-diff {
          font-size: 13px;
          font-weight: 650;
        }
        .sc-value[data-sign="pos"] {
          color: var(--teal-ink);
        }
        .sc-value[data-sign="neg"] {
          color: var(--coral-ink);
        }
        .sim-conseq {
          margin-top: 18px;
        }
        .sim-conseq-label {
          font-family: var(--font-mono);
          font-size: 10.5px;
          font-weight: 500;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: var(--ink-4);
          margin-bottom: 8px;
          display: block;
        }
        .sim-cover {
          display: grid;
          grid-template-columns: 1fr 1fr 1fr;
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          background: var(--surface);
        }
        .cov-row {
          display: flex;
          flex-direction: column;
          gap: 3px;
          padding: 13px 16px;
        }
        .cov-row + .cov-row {
          border-left: 1px solid var(--border);
        }
        .cov-label {
          font-size: 10.5px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--ink-4);
        }
        .cov-value {
          font-size: 15px;
          font-weight: 640;
          color: var(--ink-2);
        }
        .cov-value.ok {
          color: var(--teal-ink);
        }
        .cov-value.risk {
          color: var(--coral-ink);
        }
        .sim-alert {
          margin-top: 14px;
        }

        @media (max-width: 560px) {
          .sim-controls {
            grid-template-areas:
              "scope scope"
              "seg range"
              "recompute recompute";
            grid-template-columns: auto minmax(0, 1fr);
          }
          .sim-recompute {
            justify-self: start;
          }
          .sim-compare {
            grid-template-columns: 1fr;
          }
          .sc-arrow {
            display: none;
          }
          .sim-cover {
            grid-template-columns: 1fr;
          }
          .cov-row + .cov-row {
            border-left: 0;
            border-top: 1px solid var(--border);
          }
          .sim-head,
          .sim-body {
            padding-left: 18px;
            padding-right: 18px;
          }
        }
      `}</style>
    </div>
  );
}