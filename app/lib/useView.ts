"use client";

import { useCallback, useEffect, useState } from "react";

// App views. Routing is plain hash navigation ("#/overview" … "#/ask") — it
// survives refresh, plays nicely with the back button, and needs no extra
// router. Works entirely inside the existing client page.

export const VIEWS = ["overview", "signals", "insights", "actions", "simulate", "ask"] as const;
export type ViewId = (typeof VIEWS)[number];

function isView(value: string): value is ViewId {
  return (VIEWS as readonly string[]).includes(value);
}

function readHash(): ViewId {
  if (typeof window === "undefined") return "overview";
  const raw = window.location.hash.replace(/^#\/?/, "").trim();
  return isView(raw) ? raw : "overview";
}

export function useView(): { view: ViewId; go: (view: ViewId) => void } {
  const [view, setView] = useState<ViewId>(readHash);

  useEffect(() => {
    const onChange = () => setView(readHash());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  // Each view is a workspace — start it at the top.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [view]);

  const go = useCallback((next: ViewId) => {
    if (readHash() === next) return;
    window.location.hash = `/${next}`;
  }, []);

  return { view, go };
}