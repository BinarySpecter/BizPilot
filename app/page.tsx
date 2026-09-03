"use client";

import { useCallback, useState } from "react";
import type { Analysis, LoadSource } from "./lib/types";
import { analyzeFiles, analyzeSample, ApiError } from "./lib/api";
import { useView, type ViewId } from "./lib/useView";
import UploadPanel from "./components/UploadPanel";
import Sidebar from "./components/Sidebar";
import OverviewView from "./components/views/OverviewView";
import SignalsView from "./components/views/SignalsView";
import InsightsView from "./components/views/InsightsView";
import ActionsView from "./components/views/ActionsView";
import SimulateView from "./components/views/SimulateView";
import AskView from "./components/views/AskView";
import { PilotMark, RefreshIcon } from "./components/icons";

type Stage =
  | { status: "idle" }
  | { status: "loading"; label: string }
  | { status: "error"; message: string }
  | { status: "ready"; analysis: Analysis; source: LoadSource };

export default function Page() {
  const [stage, setStage] = useState<Stage>({ status: "idle" });
  const { view } = useView();

  const runAnalyze = useCallback(async (operation: () => Promise<{ analysis: Analysis; source: LoadSource }>, label: string) => {
    setStage({ status: "loading", label });
    try {
      const { analysis, source } = await operation();
      setStage({ status: "ready", analysis, source });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Unexpected error while analyzing the data.";
      setStage({ status: "error", message: msg });
    }
  }, []);

  const handleFiles = useCallback(
    (sales: File, inventory: File | null) =>
      runAnalyze(() => analyzeFiles(sales, inventory), "Analyzing your business data…"),
    [runAnalyze],
  );

  const handleSample = useCallback(
    () => runAnalyze(() => analyzeSample(), "Loading demo dataset…"),
    [runAnalyze],
  );

  const exitToUpload = useCallback(() => {
    setStage({ status: "idle" });
    if (typeof window !== "undefined") window.location.hash = "#/overview";
  }, []);

  // Load demo data into a specific app view — the landing CTAs end at the
  // Overview (default), while "See the evidence" lands straight in Actions.
  const loadDemoView = useCallback(
    (view: ViewId) => {
      if (typeof window !== "undefined") window.location.hash = `#/${view}`;
      handleSample();
    },
    [handleSample],
  );

  const ready = stage.status === "ready" ? stage : null;

  return (
    <>
      <header className="topbar">
        <div className="container topbar-inner">
          <div className="brand">
            <span className="brand-sq">
              <PilotMark size={17} />
            </span>
            <span className="brand-name">
              BizPilot<span className="brand-ai">AI</span>
            </span>
            <span className="brand-tag">decision intelligence</span>
          </div>
          {ready && (
            <button type="button" className="btn btn-ghost" onClick={exitToUpload}>
              <RefreshIcon size={15} />
              New data
            </button>
          )}
        </div>
      </header>

      {ready ? (
        <div className="app-body">
          <Sidebar analysis={ready.analysis} source={ready.source} active={view} />

          <main className="app-main">
            {view === "overview" && <OverviewView analysis={ready.analysis} source={ready.source} />}
            {view === "signals" && <SignalsView analysis={ready.analysis} />}
            {view === "insights" && <InsightsView analysis={ready.analysis} />}
            {view === "actions" && <ActionsView analysis={ready.analysis} />}
            {view === "simulate" && <SimulateView analysis={ready.analysis} />}
            {view === "ask" && <AskView analysis={ready.analysis} />}

            <footer className="app-footer">
              <hr className="hairline" />
              <div className="small muted" style={{ marginTop: 14 }}>
                BizPilot AI — every number on this screen is computed from your uploaded data.
                {ready.source === "sample" ? " Current view uses clearly labeled demo data." : ""}
                {" "}
                Forecasts and what-if results are estimates, not guarantees.
              </div>
            </footer>
          </main>
        </div>
      ) : stage.status === "idle" ? (
        <main style={{ paddingBottom: 60 }}>
          <UploadPanel
            onFiles={handleFiles}
            onTryDemo={() => loadDemoView("overview")}
            onSeeEvidence={() => loadDemoView("actions")}
          />
        </main>
      ) : (
        <main className="container" style={{ paddingBottom: 76 }}>
          {stage.status === "loading" && (
            <div className="boot">
              <div className="boot-card">
                <div className="boot-eyebrow eyebrow">Analyzing</div>
                <div className="boot-label">{stage.label}</div>
                <div className="boot-sub small muted mono">
                  clean → kpis → trends → forecast → anomalies → recommendations
                </div>
                <div className="pulse-line" />
                <div className="skeleton-stack">
                  <div className="skeleton" />
                  <div className="skeleton" />
                  <div className="skeleton" />
                </div>
              </div>
            </div>
          )}

          {stage.status === "error" && (
            <div className="boot">
              <div className="boot-card">
                <div className="alert alert-error" style={{ maxWidth: 560, margin: "0 auto" }}>
                  <div>
                    <strong>We could not analyze that file.</strong>
                    <div style={{ marginTop: 4 }}>{stage.message}</div>
                    <div className="mt-3" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                      <button type="button" className="btn btn-secondary" onClick={() => setStage({ status: "idle" })}>
                        Back to upload
                      </button>
                      <button type="button" className="btn btn-primary" onClick={handleSample}>
                        Try sample data
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      )}
    </>
  );
}