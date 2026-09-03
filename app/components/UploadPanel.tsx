"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Analysis } from "../lib/types";
import { analyzeSample } from "../lib/api";
import { UploadIcon, ArrowRightIcon } from "./icons";

type Props = {
  onFiles: (sales: File, inventory: File | null) => void;
  onTryDemo: () => void;
  onSeeEvidence: () => void;
};

const STEPS = [
  { n: "01", name: "Data", cap: "clean & validate" },
  { n: "02", name: "Signals", cap: "detect what changed" },
  { n: "03", name: "Insights", cap: "understand the meaning" },
  { n: "04", name: "Actions", cap: "know what to do" },
  { n: "05", name: "Simulate", cap: "test the decision" },
  { n: "06", name: "Ask", cap: "question the evidence" },
];

export default function UploadPanel({ onFiles, onTryDemo, onSeeEvidence }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const invInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  // Preview the strongest existing demo decision (computed from the same
  // sample analytics the dashboard uses) while the landing page is open.
  const [preview, setPreview] = useState<Analysis | null>(null);
  const [previewState, setPreviewState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    setPreviewState("loading");
    analyzeSample()
      .then(({ analysis }) => {
        if (cancelled) return;
        setPreview(analysis);
        setPreviewState("ready");
      })
      .catch(() => {
        if (!cancelled) setPreviewState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleFiles = useCallback(
    (list: FileList | null) => {
      if (!list || list.length === 0) return;
      const files = Array.from(list);
      const sales = files.find((f) => /sales|revenue|transactions?/i.test(f.name) && /\.csv$/i.test(f.name));
      const inventory = files.find((f) => /inventor|stock/i.test(f.name) && /\.csv$/i.test(f.name));
      if (sales) {
        onFiles(sales, inventory ?? null);
      } else if (files.some((f) => /\.csv$/i.test(f.name))) {
        const csvs = files.filter((f) => /\.csv$/i.test(f.name));
        onFiles(csvs[0], csvs[1] ?? null);
      } else {
        alert("Please choose a .csv file.");
      }
    },
    [onFiles],
  );

  const rec = preview?.recommendations.find((r) => r.category === "inventory") ?? preview?.recommendations[0] ?? null;
  const recProduct =
    preview && rec ? preview.products.find((p) => rec.title.toLowerCase().includes(p.name.toLowerCase())) ?? null : null;
  const forecastUnits = recProduct?.forecast_7d ?? null;
  const stockUnits = recProduct?.stock ?? null;

  return (
    <div className="landing">
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        style={{ display: "none" }}
        onChange={(e) => handleFiles(e.target.files)}
      />
      <input
        ref={invInputRef}
        type="file"
        accept=".csv,text/csv"
        style={{ display: "none" }}
        aria-hidden
        tabIndex={-1}
      />

      <div className="hero">
        <div className="hero-main">
          <span className="hero-eyebrow">Decision intelligence for small business</span>
          <h1 className="hero-title">
            Know what changed.
            <br />
            Know what matters.
            <br />
            Know what to do next.
          </h1>
          <p className="hero-sub">
            BizPilot turns sales data into evidence-backed business decisions — surfacing important
            signals, explaining what they mean, and showing what action to take next.
          </p>

          <div className="hero-actions">
            <button type="button" className="btn btn-primary btn-demo" onClick={onTryDemo}>
              Try with demo data
              <ArrowRightIcon size={15} />
            </button>
            <button type="button" className="btn btn-secondary btn-upload" onClick={() => inputRef.current?.click()}>
              <UploadIcon size={15} />
              Upload your sales CSV
            </button>
          </div>
          <p className="hero-note mono">demo data is clearly labeled everywhere it appears</p>

          <div
            className={`drop-hint${dragOver ? " dz-over" : ""}`}
            role="button"
            tabIndex={0}
            aria-label="Upload sales CSV"
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFiles(e.dataTransfer.files);
            }}
          >
            <UploadIcon size={14} />
            <span>
              Drop a sales CSV here, or{" "}
              <button
                type="button"
                className="link-like"
                onClick={(e) => {
                  e.stopPropagation();
                  inputRef.current?.click();
                }}
              >
                browse files
              </button>{" "}
              · <code>date</code> <code>product</code> <code>quantity</code> <code>revenue</code>
            </span>
            <button
              type="button"
              className="link-like"
              onClick={(e) => {
                e.stopPropagation();
                invInputRef.current?.click();
              }}
            >
              Add inventory.csv
            </button>
          </div>
        </div>

        <aside className="decision" aria-label="Example decision from demo data">
          <div className="dc-head">
            <span className="dc-eyebrow">A decision BizPilot surfaced</span>
            <span className="tag tag-amber">Demo data</span>
          </div>

          {previewState === "loading" && (
            <div className="dc-loading">
              <div className="dc-skeleton" />
              <div className="dc-skeleton" />
              <div className="dc-skeleton" />
              <span className="mono dc-loading-note">computing from demo data…</span>
            </div>
          )}

          {previewState === "error" && (
            <div className="dc-loading">
              <span className="mono dc-loading-note">demo preview unavailable — analyze demo data to see decisions</span>
            </div>
          )}

          {previewState === "ready" && rec && (
            <>
              <span className="dc-prio">high priority</span>
              <div className="dc-title">{rec.title}</div>

              {(forecastUnits != null || stockUnits != null) && (
                <div className="dc-stats">
                  <div className="dc-stat">
                    <span className="dc-stat-label">Forecast</span>
                    <span className="dc-stat-value num">
                      {forecastUnits != null ? `${forecastUnits.toLocaleString()} units` : "—"}
                    </span>
                  </div>
                  <div className="dc-stat">
                    <span className="dc-stat-label">Inventory</span>
                    <span className="dc-stat-value num">
                      {stockUnits != null ? `${stockUnits.toLocaleString()} units` : "—"}
                    </span>
                  </div>
                </div>
              )}

              <div className="dc-verdict" data-tone="coral">
                <span className="dot dot-coral" />
                <span>{rec.priority === "high" ? "Stock-out risk within the week." : rec.reason}</span>
              </div>

              <button type="button" className="dc-link" onClick={onSeeEvidence}>
                See the evidence
                <ArrowRightIcon size={13} />
              </button>
            </>
          )}
        </aside>
      </div>

      <div className="chain-wrap">
        <div className="chain">
          {STEPS.map((s, i) => (
            <div className="chain-group" key={s.n}>
              {i > 0 && <span className="chain-arrow" aria-hidden>→</span>}
              <div className="chain-item">
                <span className="chain-body">
                  <span className="chain-num num">{s.n}</span>
                  <span className="chain-name">{s.name}</span>
                </span>
                <span className="chain-cap">{s.cap}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="position">
        <div className="pos-col">
          <span className="pos-label">Dashboards</span>
          <p className="pos-q">“What happened?”</p>
        </div>
        <div className="pos-hairline" />
        <div className="pos-col pos-bp">
          <span className="pos-label">BizPilot</span>
          <ul className="pos-qs">
            <li>What changed?</li>
            <li>Why does it matter?</li>
            <li>What should I do?</li>
            <li>What happens if I do it?</li>
          </ul>
        </div>
      </div>

      <style jsx>{`
        .landing {
          max-width: 1264px;
          margin: 0 auto;
          padding: 46px 32px 0;
        }
        .hero {
          display: grid;
          grid-template-columns: minmax(0, 1.16fr) minmax(0, 0.84fr);
          gap: clamp(40px, 5vw, 60px);
          align-items: start;
        }
        .hero-eyebrow {
          font-family: var(--font-mono);
          font-size: 11.5px;
          font-weight: 500;
          letter-spacing: 0.15em;
          text-transform: uppercase;
          color: var(--ink-3);
        }
        .hero-title {
          margin-top: 16px;
          font-size: clamp(30px, 4.8vw, 56px);
          font-weight: 620;
          letter-spacing: -0.035em;
          line-height: 1.06;
          color: var(--ink);
        }
        .hero-sub {
          margin-top: 18px;
          max-width: 560px;
          font-size: 16.5px;
          line-height: 1.62;
          color: var(--ink-3);
        }
        .hero-actions {
          margin-top: 24px;
          display: flex;
          gap: 14px;
          flex-wrap: wrap;
          align-items: center;
        }
        .btn-demo {
          height: 50px;
          padding: 0 24px;
          font-size: 15px;
        }
        .btn-upload {
          height: 50px;
          padding: 0 20px;
        }
        .hero-note {
          margin-top: 12px;
          font-size: 11px;
          letter-spacing: 0.03em;
          color: var(--ink-4);
        }
        .drop-hint {
          margin-top: 22px;
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 14px 18px;
          border: 1px dashed var(--border-strong);
          border-radius: var(--radius-sm);
          background: var(--surface);
          color: var(--ink-3);
          font-size: 13px;
          cursor: pointer;
          transition: border-color 0.15s ease, background 0.15s ease;
          flex-wrap: wrap;
        }
        .drop-hint:hover,
        .drop-hint.dz-over {
          border-color: var(--blue);
          background: var(--blue-soft);
        }
        .drop-hint svg {
          color: var(--blue-ink);
          flex: none;
        }
        .drop-hint code {
          font-family: var(--font-mono);
          font-size: 11px;
          background: var(--surface-2);
          border: 1px solid var(--border);
          border-radius: 4px;
          padding: 0 5px;
        }
        .drop-hint .link-like:last-child {
          margin-left: auto;
        }
        .link-like {
          background: none;
          border: none;
          padding: 0;
          color: var(--blue-ink);
          font: inherit;
          font-size: inherit;
          cursor: pointer;
          text-decoration: underline;
          text-underline-offset: 2px;
        }

        /* ---- example decision card ---- */
        .decision {
          align-self: center;
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          box-shadow: var(--shadow-1);
          padding: 26px 28px 22px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .dc-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }
        .dc-eyebrow {
          font-family: var(--font-mono);
          font-size: 11px;
          font-weight: 500;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          color: var(--ink-4);
        }
        .dc-prio {
          font-family: var(--font-mono);
          font-size: 11.5px;
          font-weight: 600;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--coral-ink);
          background: var(--coral-soft);
          border: 1px solid var(--coral-border);
          border-radius: var(--radius-sm);
          padding: 3px 9px;
          align-self: flex-start;
        }
        .dc-title {
          font-size: 21px;
          font-weight: 640;
          letter-spacing: -0.02em;
          line-height: 1.3;
          color: var(--ink);
        }
        .dc-stats {
          display: grid;
          grid-template-columns: 1fr 1fr;
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          overflow: hidden;
        }
        .dc-stat {
          padding: 14px 16px;
          background: var(--surface-2);
        }
        .dc-stat + .dc-stat {
          border-left: 1px solid var(--border);
        }
        .dc-stat-label {
          display: block;
          font-family: var(--font-mono);
          font-size: 10.5px;
          letter-spacing: 0.1em;
          text-transform: uppercase;
          color: var(--ink-4);
        }
        .dc-stat-value {
          display: block;
          margin-top: 3px;
          font-size: 20px;
          font-weight: 640;
          letter-spacing: -0.02em;
          color: var(--ink);
        }
        .dc-verdict {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13.5px;
          font-weight: 620;
          color: var(--coral-ink);
        }
        .dc-verdict[data-tone="teal"] { color: var(--teal-ink); }
        .dc-link {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          align-self: flex-start;
          margin-top: 2px;
          background: none;
          border: 0;
          padding: 0;
          font: inherit;
          font-size: 13.5px;
          font-weight: 650;
          color: var(--blue-ink);
          cursor: pointer;
        }
        .dc-link svg {
          transition: transform 0.15s ease;
        }
        .dc-link:hover svg {
          transform: translateX(2px);
        }
        .dc-link:hover {
          text-decoration: underline;
          text-underline-offset: 2px;
        }
        .dc-loading {
          display: flex;
          flex-direction: column;
          gap: 10px;
          padding: 6px 0;
        }
        .dc-skeleton {
          height: 18px;
          border-radius: 4px;
          background: var(--surface-3);
          animation: shimmer 1.5s infinite;
        }
        .dc-skeleton:nth-child(2) { height: 38px; }
        @keyframes shimmer {
          0% { opacity: 0.5; }
          50% { opacity: 1; }
          100% { opacity: 0.5; }
        }
        .dc-loading-note {
          font-size: 11px;
          letter-spacing: 0.04em;
          color: var(--ink-4);
        }

        /* ---- decision workflow chain ---- */
        .chain-wrap {
          margin-top: 42px;
          border-top: 1px solid var(--border);
          padding-top: 0;
        }
        .chain {
          display: flex;
          align-items: stretch;
          position: relative;
          overflow-x: auto;
          scrollbar-width: none;
        }
        .chain::-webkit-scrollbar {
          display: none;
        }
        .chain-group {
          display: flex;
          align-items: stretch;
          flex: 0 0 auto;
        }
        .chain-item {
          padding: 22px 24px 20px;
          display: flex;
          flex-direction: column;
          gap: 4px;
          border-bottom: 2px solid transparent;
          min-width: 120px;
        }
        .chain-body {
          display: flex;
          align-items: baseline;
          gap: 9px;
        }
        .chain-num {
          font-family: var(--font-mono);
          font-size: 11.5px;
          font-weight: 600;
          color: var(--blue-ink);
        }
        .chain-name {
          font-size: 15.5px;
          font-weight: 650;
          letter-spacing: -0.01em;
          color: var(--ink);
        }
        .chain-cap {
          font-size: 12.5px;
          color: var(--ink-3);
        }
        .chain-arrow {
          align-self: center;
          color: var(--ink-4);
          font-size: 14px;
          padding: 0 4px;
        }
        @media (min-width: 1184px) {
          .chain-group:hover .chain-item {
            border-bottom-color: var(--blue);
          }
        }

        /* ---- positioning ---- */
        .position {
          margin-top: 44px;
          display: grid;
          grid-template-columns: 1fr 1px 1fr;
          gap: 28px;
          align-items: start;
        }
        .pos-hairline {
          width: 1px;
          align-self: stretch;
          background: var(--border);
        }
        .pos-label {
          font-family: var(--font-mono);
          font-size: 11px;
          font-weight: 500;
          letter-spacing: 0.14em;
          text-transform: uppercase;
          color: var(--ink-4);
        }
        .pos-q {
          margin-top: 12px;
          font-size: 21px;
          font-weight: 540;
          letter-spacing: -0.015em;
          color: var(--ink-3);
        }
        .pos-qs {
          list-style: none;
          margin: 12px 0 0;
          padding: 0;
          display: grid;
          gap: 6px;
        }
        .pos-qs li {
          font-size: 19px;
          font-weight: 620;
          letter-spacing: -0.012em;
          color: var(--ink);
        }
        .pos-qs li::before {
          content: "“";
          color: var(--blue-ink);
          font-weight: 650;
          margin-right: 8px;
        }
        .pos-qs li::after {
          content: "”";
          color: var(--blue-ink);
          font-weight: 650;
        }
        .pos-bp .pos-label {
          color: var(--blue-ink);
        }

        @media (max-width: 1024px) {
          .hero {
            grid-template-columns: 1fr;
            gap: 36px;
          }
          .decision {
            max-width: 680px;
          }
          .chain-item {
            min-width: 132px;
          }
        }
        @media (max-width: 860px) {
          .position {
            grid-template-columns: 1fr;
            gap: 0;
          }
          .pos-hairline {
            width: 100%;
            height: 1px;
            margin: 24px 0;
          }
        }
        @media (max-width: 560px) {
          .landing {
            padding-top: 32px;
          }
          .hero-actions {
            flex-direction: column;
            align-items: stretch;
          }
          .hero-actions .btn {
            width: 100%;
          }
          .drop-hint {
            align-items: flex-start;
          }
          .drop-hint .link-like:last-child {
            margin-left: 0;
          }
        }
      `}</style>
    </div>
  );
}