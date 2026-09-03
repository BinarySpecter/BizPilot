"use client";

import type { Analysis } from "../../lib/types";
import AskBusiness from "../AskBusiness";

// Ask workspace — the conversational analyst over this loaded dataset.
export default function AskView({ analysis }: { analysis: Analysis }) {
  return (
    <div className="view">
      <div className="view-head">
        <div className="view-head-main">
          <h1 className="view-title">Ask Business</h1>
          <p className="view-sub">An analyst explaining your numbers — every figure grounded in this dashboard.</p>
        </div>
      </div>

      <AskBusiness analysis={analysis} />
    </div>
  );
}