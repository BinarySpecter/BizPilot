// BizPilot AI — frontend types.
// These mirror the analytics engine's JSON schema (see analytics/schemas.py).

export type Priority = "high" | "medium" | "low";

export interface Kpis {
  total_revenue: number | null;
  revenue_rows: number;
  avg_record_revenue: number | null;
  total_units: number | null;
  recent_7d_revenue: number | null;
  recent_7d_units: number | null;
  recent_30d_revenue: number | null;
  recent_30d_units: number | null;
  days_covered: number;
  date_range: { min: string; max: string };
}

export interface DataQuality {
  rows_in_source: number;
  rows_kept: number;
  bad_dates: number;
  bad_quantity: number;
  bad_revenue: number;
  duplicate_rows: number;
  dropped_rows: number;
  dropped_pct: number;
  date_min: string | null;
  date_max: string | null;
  n_products: number;
  missing_revenue: boolean;
  inventory_warning: string | null;
}

export interface InventoryProduct {
  name: string;
  stock: number;
}

export interface Inventory {
  available: boolean;
  total_stock?: number;
  as_of?: string;
  products: InventoryProduct[];
}

export interface ProductRow {
  name: string;
  rows: number;
  revenue: number | null;
  units: number | null;
  units_last_14d: number | null;
  units_prior_14d: number | null;
  demand_change_pct: number | null;
  units_7d: number | null;
  revenue_7d: number | null;
  forecast_7d: number | null;
  coverage_days: number | null;
  stock: number | null;
  revenue_share_pct: number | null;
  units_share_pct: number | null;
}

export interface DailyPoint {
  date: string;
  demand: number | null;
  revenue: number | null;
}

export interface WeeklyPoint {
  week: string;
  demand: number | null;
  revenue: number | null;
}

export interface ForecastPoint {
  date: string;
  value: number;
}

export interface Forecast {
  available: boolean;
  reason?: string;
  horizon: number;
  method: string | null;
  seasonality_used?: boolean;
  values: ForecastPoint[];
  total: number | null;
  low: number | null;
  high: number | null;
  baseline_daily?: number | null;
  recent_avg_daily?: number | null;
  trend_direction?: "up" | "down" | "flat" | null;
  historical_days?: number;
  by_product?: Record<string, { available: boolean; total: number | null; method?: string }>;
}

export interface Anomaly {
  date: string;
  product: string;
  observed: number;
  expected: number;
  direction: "up" | "down";
  z_score: number;
  multiplier: number;
  scale: "product" | "total";
  what: string;
  why: string;
}

export interface Recommendation {
  title: string;
  evidence: string;
  reason: string;
  priority: Priority;
  category: "inventory" | "product" | "anomaly" | "data" | "signal";
}

export interface Signal {
  key: string;
  label: string;
  phrase: string;
  direction: "up" | "down" | "flat";
  change_pct?: number | null;
  period?: string;
  value_units?: number;
}

export interface Analysis {
  dataset: {
    name: string;
    rows: number;
    date_min: string | null;
    date_max: string | null;
    n_products: number;
    has_inventory: boolean;
    product_names: string[];
  };
  data_quality: DataQuality;
  kpis: Kpis;
  inventory: Inventory;
  trends: {
    daily: DailyPoint[];
    weekly: WeeklyPoint[];
  };
  forecast: Forecast;
  anomalies: Anomaly[];
  products: ProductRow[];
  signals: Signal[];
  recommendations: Recommendation[];
  meta: {
    engine_version: string;
    generated_at: string;
  };
}

export interface SimulationResult {
  label: string;
  type: "demand" | "inventory";
  adjustment_pct: number;
  product?: string | null;
  inputs: {
    baseline_forecast_units: number;
    current_stock_units: number;
  };
  outputs?: {
    adjusted_forecast_units?: number;
    adjusted_stock_units?: number;
    forecast_change_units?: number;
    stock_change_units?: number;
    coverage_days?: number | null;
    baseline_coverage_days?: number | null;
    stock_risk?: boolean;
    stock_gap_units?: number;
    alert?: string;
  };
  error?: string;
}

export interface ChatResponse {
  ok: boolean;
  available: boolean;
  answer?: string;
  message?: string;
  error?: string;
  mode?: "llm" | "deterministic";
  related_view?: string;
}

export interface ApiErrorBody {
  ok: false;
  error: string;
  code?: string;
}

export type LoadSource = "sample" | "upload";