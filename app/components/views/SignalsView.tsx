"use client";

import type { Analysis } from "../../lib/types";
import SignalsFeed from "../SignalsFeed";
import AnomalyPanel from "../AnomalyPanel";

// Signals workspace — the decision feed and the attention evidence.
export default function SignalsView({ analysis }: { analysis: Analysis }) {
  return (
    <div className="view">
      <div className="view-head">
        <div className="view-head-main">
          <h1 className="view-title">Signals</h1>
          <p className="view-sub">What changed in your numbers, and which shifts deserve a look.</p>
        </div>
        <div className="row" style={{ gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
          <span className="tag tag-neutral">{analysis.signals.length} signals</span>
          <span className="tag tag-neutral">
            {analysis.anomalies.length ? `${analysis.anomalies.length} flagged` : "none flagged"}
          </span>
        </div>
      </div>

      <div className="well df-grid">
        <div className="df-col">
          <SignalsFeed analysis={analysis} />
        </div>
        <div className="df-col">
          <AnomalyPanel analysis={analysis} />
        </div>
      </div>
    </div>
  );
}