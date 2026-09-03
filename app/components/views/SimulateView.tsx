"use client";

import type { Analysis } from "../../lib/types";
import WhatIfSimulator from "../WhatIfSimulator";

// Simulate workspace — an interactive decision room.
export default function SimulateView({ analysis }: { analysis: Analysis }) {
  return (
    <div className="view">
      <div className="view-head">
        <div className="view-head-main">
          <h1 className="view-title">Simulate</h1>
          <p className="view-sub">See the consequence of a decision before you make it.</p>
        </div>
      </div>

      <WhatIfSimulator analysis={analysis} />
    </div>
  );
}