export type RegionId =
  "nile_corridor" | "morocco_comparison" | "sahel_comparison";
export type VariableId =
  | "air_temperature"
  | "soil_moisture"
  | "precipitation"
  | "vegetation_greenness";
export type Lang = "en" | "ar";
export type BBox = { w: number; s: number; e: number; n: number };
export type CatalogEntry = {
  variable_id: VariableId;
  region_id: RegionId;
  product_id: string;
  version: string | null;
  units: string;
  label: string;
  bbox: number[];
  native_grid: Record<string, string> | null;
  app_available: boolean;
  source_kind: string;
  limitations: string[];
};
export type Catalog = {
  data_revision: string;
  method_revision: string;
  entries: CatalogEntry[];
};
export type Trend = {
  slope_per_year: number | null;
  slope_units: string;
  p_value: number | null;
  ci_low: number | null;
  ci_high: number | null;
  significant_at?: string;
};
export type WindowResult = {
  start: string;
  end: string;
  slope: number | null;
  p_value: number | null;
  ci_low: number | null;
  ci_high: number | null;
};
export type VariableResult = {
  variable_id: VariableId;
  state: string;
  label: string;
  product_id: string;
  version: string;
  units: string;
  counts: { months: number; cells: number; valid_fraction: number };
  trend: Trend | null;
  period_sensitivity?: {
    windows?: WindowResult[];
    sign_agreement?: {
      fraction_same_sign_as_full: number;
      n_windows: number;
      note: string;
    };
  };
  warnings: string[];
};
export type Result = {
  job_id: string;
  receipt_id: string | null;
  data_revision: string;
  method_revision: string;
  request: { region_id: RegionId; start_month: string; end_month: string };
  variables: VariableResult[];
  warnings: string[];
};
export type Series = {
  variable_id: VariableId;
  units: string;
  months: string[];
  values: (number | null)[];
  trend_line: (number | null)[];
  valid_fraction: number;
};
export type Spatial = {
  variable_id: VariableId;
  region_id: RegionId;
  grid: { lat: number[]; lon: number[] };
  slope: (number | null)[][];
  significant_fdr: number[][];
  fdr: { q: number; m_tested: number };
  bbox: number[];
  limitations: string[];
};
export type Explanation = {
  explanation: { answer: string; limitations: string[] };
  citations: { title: string; source_url: string; page?: number }[];
  path: string;
};
export type Analysis = {
  result: Result;
  series: Series | null;
  spatial: Spatial | null;
  explanation: Explanation | null;
  offline: boolean;
};
type Offline = {
  catalog: Catalog;
  explanations: Record<string, Explanation>;
  analyses: Record<
    string,
    {
      result: { payload: Result };
      series: { series: Series[] };
      spatial: Spatial;
      explanation: Explanation;
    }
  >;
};
declare global {
  interface Window {
    TD_OFFLINE?: Offline;
  }
}

let offlineMode = location.protocol === "file:";
export const isOffline = () => offlineMode;
const local = () => window.TD_OFFLINE;
let loadingOffline: Promise<Offline> | null = null;
function loadOffline(): Promise<Offline> {
  if (local()) return Promise.resolve(local()!);
  if (loadingOffline) return loadingOffline;
  loadingOffline = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `${import.meta.env.BASE_URL}offline_data.js`;
    script.onload = () =>
      local()
        ? resolve(local()!)
        : reject(new Error("Offline data bundle is invalid."));
    script.onerror = () => reject(new Error("Offline data bundle is missing."));
    document.head.appendChild(script);
  });
  return loadingOffline;
}
async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const body = await response.json();
  if (!response.ok)
    throw new Error(
      body?.error?.detail || `${response.status} ${response.statusText}`,
    );
  return body as T;
}
export async function getCatalog(): Promise<Catalog> {
  if (offlineMode) {
    return (await loadOffline()).catalog;
  }
  try {
    return await json<Catalog>("/v1/catalog");
  } catch (error) {
    try {
      const snapshot = await loadOffline();
      offlineMode = true;
      return snapshot.catalog;
    } catch {
      throw error;
    }
  }
}
const polygon = (box: BBox) => ({
  type: "Polygon",
  coordinates: [
    [
      [box.w, box.s],
      [box.e, box.s],
      [box.e, box.n],
      [box.w, box.n],
      [box.w, box.s],
    ],
  ],
});
export async function analyse(
  region: RegionId,
  variable: VariableId,
  start: string,
  end: string,
  lang: Lang,
  aoi: BBox | null,
  onProgress: (status: string) => void,
): Promise<Analysis> {
  if (offlineMode) {
    if (aoi || start !== "2001-01" || end !== "2024-12")
      throw new Error(
        "The offline snapshot covers the full 2001–2024 period and predefined regions only. Start the server for custom analyses.",
      );
    const item =
      local()?.analyses[`${region}|${variable}|${start}|${end}|none`];
    if (!item)
      throw new Error("This analysis is not included in the offline snapshot.");
    return {
      result: item.result.payload,
      series:
        item.series.series.find((s) => s.variable_id === variable) || null,
      spatial: item.spatial,
      explanation:
        local()?.explanations[`${item.result.payload.job_id}:${lang}`] ||
        item.explanation,
      offline: true,
    };
  }
  const body = {
    region_id: region,
    variable_ids: [variable],
    start_month: start,
    end_month: end,
    aoi: aoi ? polygon(aoi) : null,
  };
  const submitted = await json<{
    job_id: string;
    state: string;
    error?: { detail: string };
  }>("/v1/analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let job = submitted;
  for (
    let attempt = 0;
    attempt < 120 && !["succeeded", "failed"].includes(job.state);
    attempt++
  ) {
    onProgress(job.state);
    await new Promise((resolve) => setTimeout(resolve, 500));
    job = await json<typeof submitted>(`/v1/analyses/${submitted.job_id}`);
  }
  if (job.state !== "succeeded")
    throw new Error(job.error?.detail || "Analysis did not finish.");
  onProgress("loading result");
  const [resultResponse, seriesResponse, spatial, explanation] =
    await Promise.all([
      json<{ payload: Result }>(`/v1/analyses/${job.job_id}/result`),
      json<{ series: Series[] }>(`/v1/analyses/${job.job_id}/series`),
      json<Spatial>(`/v1/spatial/${variable}/${region}`).catch(() => null),
      json<Explanation>(
        `/v1/analyses/${job.job_id}/explanation?language=${lang}`,
      ).catch(() => null),
    ]);
  return {
    result: resultResponse.payload,
    series:
      seriesResponse.series.find((s) => s.variable_id === variable) || null,
    spatial,
    explanation,
    offline: false,
  };
}
export async function getExplanation(
  jobId: string,
  lang: Lang,
): Promise<Explanation | null> {
  if (offlineMode) return local()?.explanations[`${jobId}:${lang}`] || null;
  return json<Explanation>(
    `/v1/analyses/${jobId}/explanation?language=${lang}`,
  );
}
export async function getReceipt(id: string) {
  return json<{ payload: object }>(`/v1/receipts/${encodeURIComponent(id)}`);
}
export async function compare(
  variable: VariableId,
  start: string,
  end: string,
) {
  if (offlineMode) {
    if (start !== "2001-01" || end !== "2024-12")
      throw new Error("Comparison for this time window requires the server.");
    return (
      ["nile_corridor", "morocco_comparison", "sahel_comparison"] as RegionId[]
    ).map((region) => {
      const v =
        local()?.analyses[`${region}|${variable}|${start}|${end}|none`]?.result
          .payload.variables[0];
      return {
        region_id: region,
        state: v?.state || "unavailable",
        slope_per_year: v?.trend?.slope_per_year ?? null,
        p_value: v?.trend?.p_value ?? null,
        valid_fraction: v?.counts.valid_fraction ?? null,
      };
    });
  }
  const response = await json<{
    regions: {
      region_id: RegionId;
      state: string;
      slope_per_year: number | null;
      p_value: number | null;
      valid_fraction: number | null;
    }[];
  }>("/v1/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      variable_id: variable,
      start_month: start,
      end_month: end,
    }),
  });
  return response.regions;
}
