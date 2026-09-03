"use client";

import type { Analysis } from "../../lib/types";
import { RevenueTrend, DemandTrend } from "../TrendCharts";
import ForecastPanel from "../ForecastPanel";
import TopProducts from "../TopProducts";

// Insights workspace — the evidence read in one dashboard grid.
export default function InsightsView({ analysis }: { analysis: Analysis }) {
  return (
    <div className="view">
      <div className="view-head">
        <div className="view-head-main">
          <h1 className="view-title">Insights</h1>
          <p className="view-sub">
            What the last 30 days say, and what the next 7 look like — with the product evidence behind it.
          </p>
        </div>
      </div>

      <div className="cols">
        <div className="span-6">
          <RevenueTrend analysis={analysis} />
        </div>
        <div className="span-6">
          <DemandTrend analysis={analysis} />
        </div>
      </div>

      <div className="view-block">
        <ForecastPanel analysis={analysis} />
      </div>

      <div className="view-block">
        <TopProducts analysis={analysis} />
      </div>
    </div>
  );
}