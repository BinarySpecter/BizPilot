"use client";

import type { Analysis } from "../../lib/types";
import RecommendationPanel from "../RecommendationPanel";

// Actions workspace — a prioritized decision queue, each action traced back
// to the signal that produced it.
export default function ActionsView({ analysis }: { analysis: Analysis }) {
  const recs = analysis.recommendations;
  return (
    <div className="view">
      <div className="view-head">
        <div className="view-head-main">
          <h1 className="view-title">Actions</h1>
          <p className="view-sub">Prioritized decisions with the evidence behind them.</p>
        </div>
        <span className="tag tag-neutral">{recs.length} actions</span>
      </div>

      <RecommendationPanel analysis={analysis} />
    </div>
  );
}