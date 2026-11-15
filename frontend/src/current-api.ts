import type { Analysis, BBox, Catalog, Lang, RegionId, VariableId, Explanation, Spatial } from './api';

export type CatalogResponse = {
  registry_snapshot: string; data_mode: string; disclaimer: string;
  variables: { variable_id: VariableId; display_name: string; unit: string;
    app_available: boolean; demo_available: boolean;
    source: { product_id: string; version: string; lineage_note: string } }[];
};
type Regions = { regions: { region_id: RegionId; display_name: string; display_name_ar?: string; bbox: number[]; supported_variable_ids: string[] }[] };
type Job = { job_id: string; status: string; result_id: string | null; error?: string };
type StoredResult = {
  result_id: string; job_id: string; receipt_id: string; data_mode: string; disclaimer: string;
  analysis: { region_id: RegionId; start_month: string; end_month: string };
  method: { method_version: string };
  datasets: { variable_id: string; product_id: string; version: string; revision: string }[];
  warnings: { message: string }[];
  science?: Record<string, { annual_years: number[]; regional_annual: (number|null)[];
    positive_cells: number; negative_cells: number; zero_cells: number; unavailable_eligible_cells: number;
    metadata: { selected_cell_count: number; eligible_fixed_support_cells: number; fixed_support_area_fraction_of_selected_native_cells: number }; }>;
  variables: { variable_id: VariableId; display_name: string; unit: string;
    series: { month: string; value: number | null }[];
    trend: { slope_per_year: number | null; slope_unit: string | null; n_months: number; notes: string[] } }[];
};
type StoredExplanation = { sections: { title: string; body: string }[]; limitations: string[]; mode: string; references: string[] };
type StoredSpatial = { variable_id: VariableId; bounds: number[]; disclaimer: string;
  cells: { centroid: number[]; trend_value: number | null }[] };
type CompactSpatial = { variable_id: VariableId; bounds: number[]; disclaimer: string; lat: number[]; lon: number[]; slope: (number|null)[][] };

export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const body = await response.json();
  if (!response.ok) throw new Error(body?.error?.message || body?.error?.detail || `${response.status} ${response.statusText}`);
  return body as T;
}
const post = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export async function catalogFromCurrent(raw: CatalogResponse): Promise<Catalog> {
  const { regions } = await request<Regions>('/v1/catalog/regions');
  if (!Array.isArray(raw.variables) || !Array.isArray(regions)) throw new Error('Invalid catalog response.');
  return {
    data_revision: raw.registry_snapshot, method_revision: raw.data_mode === 'mock' ? 'Synthetic demo' : 'See analysis method',
    entries: regions.flatMap(region => raw.variables.filter(v => region.supported_variable_ids.includes(v.variable_id)).map(v => ({
      variable_id: v.variable_id, region_id: region.region_id, region_label: region.display_name, region_label_ar: region.display_name_ar, product_id: v.source.product_id,
      version: v.source.version, units: v.unit, label: v.display_name, bbox: region.bbox,
      native_grid: null, app_available: raw.data_mode === 'mock' ? v.demo_available : v.app_available,
      source_kind: raw.data_mode === 'mock' ? 'synthetic_demo' : 'registered',
      limitations: [raw.disclaimer, v.source.lineage_note],
    }))),
  };
}

export async function explanationForResult(resultId: string, language: Lang): Promise<Explanation> {
  const raw = await request<StoredExplanation>('/v1/explanations', post({ result_id: resultId, language }));
  return { explanation: { answer: raw.sections.map(s => `${s.title}\n${s.body}`).join('\n\n'), limitations: raw.limitations },
    citations: raw.references.map(url => ({ title: 'Source documentation', source_url: url })), path: raw.mode };
}

export async function currentExplanation(jobId: string, language: Lang): Promise<Explanation | null> {
  const job = await request<Job>(`/v1/analyses/${encodeURIComponent(jobId)}`);
  return job.result_id ? explanationForResult(job.result_id, language) : null;
}

function spatialFromCurrent(raw: StoredSpatial | CompactSpatial, region: RegionId): Spatial {
  if ('slope' in raw) return { variable_id: raw.variable_id, region_id: region, grid: { lat: raw.lat, lon: raw.lon }, slope: raw.slope,
    significant_fdr: [], fdr: { q: 0, m_tested: 0 }, bbox: raw.bounds, limitations: [raw.disclaimer, 'Descriptive only.'] };
  const lon = [...new Set(raw.cells.map(c => c.centroid[0]))].sort((a,b) => a-b);
  const lat = [...new Set(raw.cells.map(c => c.centroid[1]))].sort((a,b) => a-b);
  const byCoordinate = new Map(raw.cells.map(c => [`${c.centroid[0]},${c.centroid[1]}`, c.trend_value]));
  const slope = lat.map(y => lon.map(x => byCoordinate.get(`${x},${y}`) ?? null));
  return { variable_id: raw.variable_id, region_id: region, grid: { lat, lon }, slope,
    significant_fdr: [], fdr: { q: 0, m_tested: 0 }, bbox: raw.bounds,
    limitations: [raw.disclaimer, 'Descriptive slopes only; significance is not computed.'] };
}

export async function analyseCurrent(region: RegionId, variable: VariableId, start: string, end: string,
  lang: Lang, aoi: BBox | null, progress: (status: string) => void): Promise<Analysis> {
  let job = await request<Job>('/v1/analyses', post({ region_id: region, variable_ids: [variable],
    start_month: start, end_month: end, aoi: aoi ? { type: 'bbox', coordinates: [aoi.w, aoi.s, aoi.e, aoi.n] } : null }));
  for (let attempt=0; attempt<240 && !['completed','failed'].includes(job.status); attempt++) {
    progress(job.status);
    await new Promise(resolve => setTimeout(resolve, 1000));
    job = await request<Job>(`/v1/analyses/${encodeURIComponent(job.job_id)}`);
  }
  if (job.status !== 'completed' || !job.result_id) throw new Error(job.error || 'Analysis did not finish. Check worker status and try again.');
  progress('loading result');
  const raw = await request<StoredResult>(`/v1/results/${encodeURIComponent(job.result_id)}`);
  const selected = raw.variables.find(v => v.variable_id === variable);
  if (!selected) throw new Error('Result does not contain the requested variable.');
  const [spatial, explanation] = await Promise.all([
    request<StoredSpatial | CompactSpatial>(`/v1/results/${encodeURIComponent(job.result_id)}/spatial?compact=true`).then(s => spatialFromCurrent(s, region)).catch(() => null),
    explanationForResult(job.result_id, lang).catch(() => null),
  ]);
  return {
    offline: false, spatial, explanation,
    result: { result_id: raw.result_id, data_mode: raw.data_mode, job_id: raw.job_id, receipt_id: raw.receipt_id, data_revision: raw.datasets.map(d => d.revision).join(','),
      method_revision: raw.method.method_version, request: raw.analysis, warnings: [raw.disclaimer, ...raw.warnings.map(w => w.message)],
      variables: raw.variables.map(v => {
        const dataset = raw.datasets.find(d => d.variable_id === v.variable_id);
        const meta = raw.science?.[v.variable_id]?.metadata;
        const artifact = raw.science?.[v.variable_id];
        return { variable_id: v.variable_id, state: v.trend.slope_per_year == null ? 'insufficient_data' : 'succeeded', label: v.display_name,
          annual: artifact ? { years: artifact.annual_years, values: artifact.regional_annual } : undefined,
          cell_counts: artifact ? { positive: artifact.positive_cells, negative: artifact.negative_cells, zero: artifact.zero_cells, unavailable: artifact.unavailable_eligible_cells } : undefined,
          support: meta ? { selected_cells: meta.selected_cell_count, eligible_cells: meta.eligible_fixed_support_cells, eligible_area_fraction: meta.fixed_support_area_fraction_of_selected_native_cells } : undefined,
          product_id: dataset?.product_id || '', version: dataset?.version || '', units: v.unit,
          counts: { months: v.trend.n_months, cells: spatial ? spatial.grid.lat.length * spatial.grid.lon.length : 0, valid_fraction: v.series.length ? v.series.filter(p => p.value != null).length/v.series.length : 0 },
          trend: { slope_per_year: v.trend.slope_per_year, slope_units: v.trend.slope_unit || '', p_value: null, ci_low: null, ci_high: null },
          warnings: [raw.disclaimer, ...v.trend.notes] };
      }) },
    series: { variable_id: variable, units: selected.unit, months: selected.series.map(p => p.month),
      values: selected.series.map(p => p.value), trend_line: selected.series.map(() => null),
      valid_fraction: selected.series.length ? selected.series.filter(p => p.value != null).length/selected.series.length : 0 },
  };
}
