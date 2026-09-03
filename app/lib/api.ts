// Client for the BizPilot Python API endpoints.

import type { Analysis, ChatResponse, SimulationResult, LoadSource } from "./types";

export class ApiError extends Error {
  code?: string;
  constructor(message: string, code?: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
  }
}

async function request<T>(path: string, payload?: unknown): Promise<T> {
  const init: RequestInit = payload === undefined ? { method: "GET" } : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  };
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError(
      "Could not reach the analytics service. Is the Python API running locally?",
      "network",
    );
  }
  let data: any = null;
  try {
    data = await res.json();
  } catch {
    throw new ApiError("The analytics service returned an invalid response.", "bad_response");
  }
  if (!res.ok || data?.ok === false) {
    const msg =
      data?.error ||
      (typeof data?.message === "string" ? data.message : undefined) ||
      `Request failed (${res.status}).`;
    throw new ApiError(msg, data?.code || (data?.available === false ? "ai_unavailable" : "error"));
  }
  return data as T;
}

function fileToText(file: File): Promise<string> {
  return file.text();
}

export async function analyzeFiles(
  salesFile: File,
  inventoryFile: File | null,
): Promise<{ analysis: Analysis; source: LoadSource }> {
  const payload: Record<string, string> = {
    sales_csv: await fileToText(salesFile),
    sales_filename: salesFile.name,
  };
  if (inventoryFile) {
    payload.inventory_csv = await fileToText(inventoryFile);
    payload.inventory_filename = inventoryFile.name;
  }
  const data = await request<{ analysis: Analysis; source: LoadSource }>("/api/analyze", payload);
  return { analysis: data.analysis, source: data.source };
}

export async function analyzeSample(): Promise<{ analysis: Analysis; source: LoadSource }> {
  const data = await request<{ analysis: Analysis; source: LoadSource }>("/api/analyze", { sample: true });
  return { analysis: data.analysis, source: data.source };
}

export async function chatWithBusiness(
  analysis: Analysis,
  question: string,
  history: Array<{ role: "user" | "assistant"; content: string }>,
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", { analysis, question, history });
}

export async function simulateScenario(
  analysis: Analysis,
  scenario: { type: "demand" | "inventory"; adjustment_pct: number; product?: string },
): Promise<SimulationResult> {
  const data = await request<{ result: SimulationResult }>("/api/simulate", {
    analysis,
    scenario: { ...scenario, product: scenario.product || null },
  });
  return data.result;
}

export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `$${(value / 1_000).toFixed(1)}K`;
  return `$${value.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "—";
  return value.toLocaleString("en-US", { maximumFractionDigits: digits });
}

export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const v = Math.round(value);
  return `${v > 0 ? "+" : ""}${v}%`;
}