/* Trend Detective — map UI (Member 5)
 *
 * Rules this file follows:
 *  - Numbers are copied from the API result. Nothing is computed in the browser
 *    except colours and pixel positions.
 *  - Every variable has its own palette; NDVI never inherits temperature colours.
 *  - Missing / ineligible cells are drawn as "no data", never as zero.
 *  - The selection state is exported on window.TDState and announced with
 *    'td:statechange' so Member 6 can integrate without reaching into the DOM.
 */
'use strict';

const API = '';                       // same origin
const OFFLINE = window.TD_OFFLINE || null;   // snapshot built by tools/export_offline.py
const MONTHS = (() => {
  const out = [];
  for (let y = 2001; y <= 2024; y++) for (let m = 1; m <= 12; m++)
    out.push(`${y}-${String(m).padStart(2, '0')}`);
  return out;
})();

const I18N = {
  ar: {
    'app.title': 'كاشف الاتجاهات',
    'app.subtitle': 'ماذا يخفي المتوسط؟ — NASA Space Apps',
    'ctl.region': 'النطاق', 'ctl.variable': 'المتغير', 'ctl.period': 'الفترة',
    'ctl.from': 'من', 'ctl.to': 'إلى',
    'ctl.periodHint': 'القاعدة المجمّدة: 60 شهرًا على الأقل و80% قيم صالحة.',
    'ctl.aoi': 'منطقة مخصصة (اختياري)',
    'ctl.draw': 'ارسم مستطيلاً على الخريطة', 'ctl.clear': 'مسح',
    'ctl.aoiHint': 'أو اكتب الحدود بالأرقام — نفس الطلب ونفس المفتاح.',
    'ctl.run': 'حلّل',
    'legend.fdr': 'خلية دالة (FDR)', 'legend.nodata': 'لا بيانات / غير مؤهلة',
    'legend.attrib': 'المصادر: NASA MERRA-2 · GLDAS · GPM IMERG · MODIS — الشبكة الأصلية بدون استيفاء.',
    'res.title': 'بطاقة الدليل',
    'res.empty': 'اختر نطاقًا ومتغيرًا ثم اضغط «حلّل».',
    'res.slope': 'الميل / سنة', 'res.ci': 'مجال 95%', 'res.p': 'قيمة p',
    'res.cover': 'تغطية', 'res.limits': 'القيود', 'res.spin': 'Spin It — حساسية الفترة',
    'res.spinHint': 'نسبة توافق الإشارة وصفية، وليست احتمالًا معايرًا.',
    'res.cites': 'المصادر',
    'foot.note': 'أرقام هذه الواجهة تُنسخ من نتيجة التحليل المتحققة، ولا تُحسب في المتصفح.',
    loading: 'جاري التحليل…', queued: 'في الانتظار…', running: 'يعمل…',
    errPrefix: 'خطأ', noSlope: 'لا يوجد ميل معروض لهذه الفترة.',
    insufficientTitle: 'بيانات غير كافية',
    insufficientBody: 'الفترة المختارة لا تحقق قاعدة التغطية المجمّدة (60 شهرًا و80% قيم صالحة).',
    cells: 'خلية', tested: 'خلية مؤهلة',
    significantOf: 'دالة إحصائيًا',
    receipt: 'الإيصال', method: 'طريقة',
    'chart.title': 'السلسلة الشهرية',
    'chart.hint': 'الخط الرقيق هو السلسلة الشهرية، والخط السميك هو خط الاتجاه المحسوب على الخادم.',
    'rc.title': 'Reality Check',
    'rc.prompt': 'توقّعك للاتجاه في هذه النافذة؟',
    'rc.up': 'ارتفاع', 'rc.down': 'انخفاض', 'rc.flat': 'لا تغيّر واضح',
    'cmp.title': 'مقارنة النوافذ',
    'cmp.run': 'قارن نفس المتغير في الثلاث نوافذ',
    'exp.title': 'تصدير',
    'exp.result': 'النتيجة JSON', 'exp.receipt': 'الإيصال JSON',
    'exp.csv': 'السلسلة CSV',
  },
  en: {
    'app.title': 'Trend Detective',
    'app.subtitle': 'What the average hides — NASA Space Apps',
    'ctl.region': 'Study window', 'ctl.variable': 'Variable', 'ctl.period': 'Period',
    'ctl.from': 'From', 'ctl.to': 'To',
    'ctl.periodHint': 'Frozen rule: at least 60 months and 80% valid values.',
    'ctl.aoi': 'Custom area (optional)',
    'ctl.draw': 'Draw a rectangle on the map', 'ctl.clear': 'Clear',
    'ctl.aoiHint': 'Or type the bounds — same request, same cache key.',
    'ctl.run': 'Analyse',
    'legend.fdr': 'Significant cell (FDR)', 'legend.nodata': 'No data / not eligible',
    'legend.attrib': 'Sources: NASA MERRA-2 · GLDAS · GPM IMERG · MODIS — native grid, no interpolation.',
    'res.title': 'Evidence card',
    'res.empty': 'Pick a window and a variable, then press Analyse.',
    'res.slope': 'Slope / year', 'res.ci': '95% interval', 'res.p': 'p-value',
    'res.cover': 'Coverage', 'res.limits': 'Limitations', 'res.spin': 'Spin It — period sensitivity',
    'res.spinHint': 'The sign-agreement fraction is descriptive, not calibrated confidence.',
    'res.cites': 'Sources',
    'foot.note': 'Numbers are copied from the verified analysis result; nothing is computed in the browser.',
    loading: 'Analysing…', queued: 'Queued…', running: 'Running…',
    errPrefix: 'Error', noSlope: 'No slope is reported for this period.',
    insufficientTitle: 'Insufficient data',
    insufficientBody: 'The selected period does not meet the frozen coverage rule (60 months, 80% valid).',
    cells: 'cells', tested: 'eligible cells',
    significantOf: 'significant',
    receipt: 'Receipt', method: 'method',
    'chart.title': 'Monthly series',
    'chart.hint': 'Thin line: monthly series. Thick line: trend computed on the server.',
    'rc.title': 'Reality check',
    'rc.prompt': 'What do you expect the trend to be here?',
    'rc.up': 'Increasing', 'rc.down': 'Decreasing', 'rc.flat': 'No clear change',
    'cmp.title': 'Window comparison',
    'cmp.run': 'Compare the same variable across the three windows',
    'exp.title': 'Export',
    'exp.result': 'Result JSON', 'exp.receipt': 'Receipt JSON',
    'exp.csv': 'Series CSV',
  },
};

const PALETTES = {
  air_temperature: { cold: [64, 122, 190], mid: [240, 240, 240], warm: [196, 74, 58] },
  soil_moisture:   { cold: [138, 108, 74], mid: [240, 240, 240], warm: [42, 122, 128] },
  precipitation:   { cold: [214, 178, 84], mid: [240, 240, 240], warm: [52, 96, 168] },
  vegetation_greenness: { cold: [146, 112, 70], mid: [240, 240, 240], warm: [58, 130, 82] },
};

const state = {
  lang: 'ar',
  catalog: null,
  regionId: null,
  variableId: null,
  start: '2001-01',
  end: '2024-12',
  aoi: null,            // {w,s,e,n} or null
  drawing: false,
  dragStart: null,
  spatial: null,
  series: null,
  result: null,
  explanation: null,
  jobId: null,
  busy: false,
};

const el = (id) => document.getElementById(id);
const t = (key) => (I18N[state.lang][key] ?? key);

/* ------------------------------------------------------------------ i18n */
function applyLang() {
  const html = document.documentElement;
  html.lang = state.lang;
  html.dir = state.lang === 'ar' ? 'rtl' : 'ltr';
  el('langAr').classList.toggle('active', state.lang === 'ar');
  el('langEn').classList.toggle('active', state.lang === 'en');
  el('langAr').setAttribute('aria-pressed', state.lang === 'ar');
  el('langEn').setAttribute('aria-pressed', state.lang === 'en');
  document.querySelectorAll('[data-i18n]').forEach((n) => {
    const k = n.getAttribute('data-i18n');
    if (I18N[state.lang][k]) n.textContent = I18N[state.lang][k];
  });
  renderVariables();
  renderRegionLabel();
  if (state.result) renderCard();
}

/* -------------------------------------------------------------- catalog */
function offlineKey(body) {
  const aoi = body.aoi ? body.aoi.coordinates[0].map(
    (p) => p.map((v) => v.toFixed(2)).join(',')).join(';') : 'none';
  return [body.region_id, (body.variable_ids || []).join('+'),
          body.start_month, body.end_month, aoi].join('|');
}

async function loadCatalog() {
  if (OFFLINE && OFFLINE.catalog) {
    state.catalog = OFFLINE.catalog;
    finishCatalog();
    setOfflineBadge();
    return;
  }
  const res = await fetch(`${API}/v1/catalog`);
  if (!res.ok) throw new Error(`catalog ${res.status}`);
  state.catalog = await res.json();
  finishCatalog();
}

function finishCatalog() {
  el('revBadge').textContent = state.catalog.method_revision;

  const regions = [...new Map(state.catalog.entries.map((e) => [e.region_id, e])).values()];
  state.regionId = regions[0].region_id;
  state.variableId = state.catalog.entries.find(
    (e) => e.region_id === state.regionId).variable_id;

  const box = el('regionList');
  box.innerHTML = '';
  regions.forEach((r) => {
    const b = document.createElement('button');
    b.className = 'chip';
    b.type = 'button';
    b.role = 'radio';
    b.dataset.region = r.region_id;
    b.textContent = regionName(r.region_id);
    b.setAttribute('aria-checked', String(r.region_id === state.regionId));
    b.onclick = () => selectRegion(r.region_id);
    box.appendChild(b);
  });
  renderVariables();
  renderRegionLabel();
  syncAoiInputs();
}

function setOfflineBadge() {
  const b = el('revBadge');
  b.textContent = `${state.catalog.method_revision} · offline`;
  b.title = 'offline snapshot: no network, no model';
}

function regionName(id) {
  const ar = { nile_corridor: 'وادي النيل', morocco_comparison: 'المغرب', sahel_comparison: 'الساحل' };
  const en = { nile_corridor: 'Nile corridor', morocco_comparison: 'Morocco', sahel_comparison: 'Sahel' };
  return (state.lang === 'ar' ? ar : en)[id] || id;
}

function variableName(v) {
  const ar = {
    air_temperature: 'حرارة الهواء', soil_moisture: 'رطوبة التربة',
    precipitation: 'المطر', vegetation_greenness: 'الغطاء النباتي',
  };
  const en = {
    air_temperature: 'Air temperature', soil_moisture: 'Soil moisture',
    precipitation: 'Precipitation', vegetation_greenness: 'Vegetation greenness',
  };
  return (state.lang === 'ar' ? ar : en)[v] || v;
}

function renderVariables() {
  if (!state.catalog) return;
  const box = el('variableList');
  box.innerHTML = '';
  const vars = state.catalog.entries.filter((e) => e.region_id === state.regionId);
  vars.forEach((v) => {
    const b = document.createElement('button');
    b.className = 'var';
    b.type = 'button';
    b.role = 'radio';
    b.setAttribute('aria-checked', String(v.variable_id === state.variableId));
    b.innerHTML = `<span>${variableName(v.variable_id)}</span>
      <small>${v.units} · ${v.product_id}</small>`;
    b.onclick = () => { state.variableId = v.variable_id; renderVariables(); renderHint(); };
    box.appendChild(b);
  });
  renderHint();
}

function renderHint() {
  const e = currentEntry();
  el('varHint').textContent = e
    ? `${e.product_id} ${e.version || ''} — ${e.units} · ${e.source_kind || ''}`
    : '';
}

function renderRegionLabel() {
  const e = currentEntry();
  if (!e) return;
  const [w, s, ea, n] = e.bbox;
  el('mapTitle').textContent = `${regionName(state.regionId)} · ${variableName(state.variableId)}`;
  el('gridInfo').textContent = `${e.native_grid?.lat || '?'} × ${e.native_grid?.lon || '?'}`;
  el('gridInfo').dir = 'ltr';
  el('fdrInfo').textContent = `W${w} S${s} E${ea} N${n}`;
  el('fdrInfo').dir = 'ltr';
}

function currentEntry() {
  if (!state.catalog) return null;
  return state.catalog.entries.find(
    (e) => e.region_id === state.regionId && e.variable_id === state.variableId);
}

function selectRegion(id) {
  state.regionId = id;
  const first = state.catalog.entries.find((e) => e.region_id === id);
  state.variableId = first.variable_id;
  document.querySelectorAll('#regionList .chip').forEach((c) => {
    c.setAttribute('aria-checked', String(c.dataset.region === id));
  });
  renderVariables();
  renderRegionLabel();
  syncAoiInputs();
  state.spatial = null;
  drawMap();
}

/* ----------------------------------------------------------------- period */
function fillMonths() {
  [el('startMonth'), el('endMonth')].forEach((sel, idx) => {
    sel.innerHTML = '';
    MONTHS.forEach((m) => {
      const o = document.createElement('option');
      o.value = m; o.textContent = m;
      sel.appendChild(o);
    });
    sel.value = idx === 0 ? state.start : state.end;
  });
}

/* -------------------------------------------------------------------- AOI */
function syncAoiInputs() {
  const e = currentEntry();
  const [w, s, ea, n] = e ? e.bbox : [-10, -10, 10, 10];
  if (!state.aoi) {
    el('aoiW').value = ''; el('aoiS').value = '';
    el('aoiE').value = ''; el('aoiN').value = '';
    el('aoiW').placeholder = w; el('aoiS').placeholder = s;
    el('aoiE').placeholder = ea; el('aoiN').placeholder = n;
  }
}

function readAoiInputs() {
  const w = parseFloat(el('aoiW').value);
  const s = parseFloat(el('aoiS').value);
  const e = parseFloat(el('aoiE').value);
  const n = parseFloat(el('aoiN').value);
  if ([w, s, e, n].every(Number.isFinite)) {
    state.aoi = { w: Math.min(w, e), s: Math.min(s, n), e: Math.max(w, e), n: Math.max(s, n) };
    drawMap();
    emitState();
  }
}

function clearAoi() {
  state.aoi = null;
  ['aoiW', 'aoiS', 'aoiE', 'aoiN'].forEach((id) => { el(id).value = ''; });
  drawMap();
  emitState();
}

function aoiToPolygon(a) {
  return {
    type: 'Polygon',
    coordinates: [[[a.w, a.s], [a.e, a.s], [a.e, a.n], [a.w, a.n], [a.w, a.s]]],
  };
}

/* ------------------------------------------------------------------- map */
const canvas = () => el('map');

function project(spatial, bbox) {
  const [w, s, e, n] = bbox;
  // measure the panel, not the wrapper: the wrapper is sized from the canvas,
  // so measuring it would create a shrinking feedback loop
  const panel = canvas().closest('.panel');
  const budgetW = Math.max(320, (panel ? panel.clientWidth : 900) - 34);
  const budgetH = Math.min(560, Math.round(window.innerHeight * 0.58));
  const pad = 38;
  const midLat = (s + n) / 2;
  const k = Math.cos((midLat * Math.PI) / 180);
  const spanX = Math.max((e - w) * k, 1e-6);
  const spanY = Math.max(n - s, 1e-6);
  // A tall narrow window would leave most of the panel empty. Allow a bounded
  // horizontal stretch (max 1.6:1); the graticule still shows true coordinates
  // and cells stay on the native grid.
  const maxStretch = 1.35;
  const ratio = spanY / spanX;
  const stretch = ratio > maxStretch ? Math.min(2.6, ratio / maxStretch) : 1;
  const effSpanX = spanX * stretch;
  const scale = Math.min((budgetW - 2 * pad) / effSpanX,
                         (budgetH - 2 * pad) / spanY);
  const mapW = effSpanX * scale;
  const mapH = spanY * scale;
  const W = Math.round(mapW + 2 * pad);
  const H = Math.round(mapH + 2 * pad);
  const offX = pad;
  const offY = pad;
  return {
    W, H,
    toPx: (lon, lat) => [offX + (lon - w) * k * stretch * scale,
                         offY + (n - lat) * scale],
    scale, k, stretch, pad,
  };
}

function colorFor(variableId, value, vmax) {
  const p = PALETTES[variableId] || PALETTES.air_temperature;
  const x = Math.max(-1, Math.min(1, value / (vmax || 1)));
  const mid = p.mid, end = x >= 0 ? p.warm : p.cold;
  const f = Math.abs(x);
  const rgb = mid.map((m, i) => Math.round(m + (end[i] - m) * f));
  return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
}

function drawMap() {
  const c = canvas();
  const e = currentEntry();
  if (!e) return;
  const proj = project(state.spatial, e.bbox);
  const dpr = window.devicePixelRatio || 1;
  // the canvas takes the shape of the window instead of a fixed 3:2 box
  c.style.width = `${proj.W}px`;
  c.style.height = `${proj.H}px`;
  c.width = Math.round(proj.W * dpr);
  c.height = Math.round(proj.H * dpr);
  const ctx = c.getContext('2d');
  // canvas text must stay LTR: in an RTL page Chromium applies Arabic digit
  // shaping, which turned "24.0°" into a single Arabic-Indic glyph
  ctx.direction = 'ltr';
  ctx.textAlign = 'start';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, proj.W, proj.H);
  const bbox = e.bbox;
  const [w, s, ea, n] = bbox;

  // plain background (works with no basemap at all)
  ctx.fillStyle = '#0b0f14';
  ctx.fillRect(0, 0, proj.W, proj.H);

  // graticule
  ctx.strokeStyle = '#1c2531';
  ctx.lineWidth = 1;
  ctx.font = '10px system-ui';
  ctx.fillStyle = '#6c7c8f';
  const stepX = niceStep(ea - w), stepY = niceStep(n - s);
  for (let lon = Math.ceil(w / stepX) * stepX; lon <= ea; lon += stepX) {
    const [x] = proj.toPx(lon, s);
    ctx.beginPath(); ctx.moveTo(x, proj.pad / 2); ctx.lineTo(x, proj.H - proj.pad / 2); ctx.stroke();
    ctx.fillText(`${lon.toFixed(1)}°`, x + 2, proj.H - 6);
  }
  for (let lat = Math.ceil(s / stepY) * stepY; lat <= n; lat += stepY) {
    const [, y] = proj.toPx(w, lat);
    ctx.beginPath(); ctx.moveTo(proj.pad / 2, y); ctx.lineTo(proj.W - proj.pad / 2, y); ctx.stroke();
    ctx.fillText(`${lat.toFixed(1)}°`, 6, y - 3);
  }

  if (state.spatial) {
    const { grid, slope, significant_fdr } = state.spatial;
    const latStep = grid.lat.length > 1 ? Math.abs(grid.lat[1] - grid.lat[0]) : 0.5;
    const lonStep = grid.lon.length > 1 ? Math.abs(grid.lon[1] - grid.lon[0]) : 0.5;
    // robust colour range: the 95th percentile of |slope| so a few extreme
    // cells cannot wash out the rest of the map
    const mags = [];
    slope.forEach((row) => row.forEach((v) => {
      if (v !== null) mags.push(Math.abs(v));
    }));
    mags.sort((a, b) => a - b);
    const p95 = mags.length ? mags[Math.min(mags.length - 1,
      Math.floor(mags.length * 0.95))] : 0;
    let vmax = p95 || (mags.length ? mags[mags.length - 1] : 0) || 1;
    state._vmax = vmax;
    state._clipped = mags.length ? mags[mags.length - 1] : 0;

    for (let j = 0; j < grid.lat.length; j++) {
      for (let i = 0; i < grid.lon.length; i++) {
        const v = slope[j][i];
        const [x0, y0] = proj.toPx(grid.lon[i] - lonStep / 2, grid.lat[j] + latStep / 2);
        const [x1, y1] = proj.toPx(grid.lon[i] + lonStep / 2, grid.lat[j] - latStep / 2);
        const wpx = Math.max(1, x1 - x0);
        const hpx = Math.max(1, y1 - y0);
        if (v === null) {
          ctx.fillStyle = '#1a212b';
          ctx.fillRect(x0, y0, wpx, hpx);
          continue;
        }
        ctx.fillStyle = colorFor(state.variableId, v, vmax);
        ctx.fillRect(x0, y0, wpx, hpx);
        if (significant_fdr[j][i]) {
          const dense = grid.lat.length * grid.lon.length > 8000;
          ctx.strokeStyle = dense ? 'rgba(255,255,255,.32)'
                                  : 'rgba(255,255,255,.85)';
          ctx.lineWidth = dense ? 0.8 : Math.max(1, wpx * 0.06);
          ctx.strokeRect(x0 + 0.5, y0 + 0.5, wpx - 1, hpx - 1);
        }
      }
    }
    updateLegend(vmax);
  } else {
    updateLegend(null);
  }

  // AOI rectangle
  if (state.aoi) {
    const [x0, y0] = proj.toPx(state.aoi.w, state.aoi.n);
    const [x1, y1] = proj.toPx(state.aoi.e, state.aoi.s);
    ctx.strokeStyle = '#4da3ff';
    ctx.setLineDash([6, 4]);
    ctx.lineWidth = 2;
    ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
    ctx.setLineDash([]);
    ctx.fillStyle = 'rgba(77,163,255,.10)';
    ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
  }

  // attribution on the canvas itself
  ctx.fillStyle = 'rgba(140,158,178,.9)';
  ctx.font = '10px system-ui';
  ctx.fillText('NASA MERRA-2 / GLDAS / GPM IMERG / MODIS · native grid',
               10, 14);
}

function niceStep(span) {
  const raw = span / 5;
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  const n = raw / pow;
  return (n >= 5 ? 10 : n >= 2 ? 5 : 2) * pow;
}

function updateLegend(vmax) {
  const e = currentEntry();
  const p = PALETTES[state.variableId] || PALETTES.air_temperature;
  el('legGradient').style.background =
    `linear-gradient(90deg, rgb(${p.cold.join(',')}), rgb(${p.mid.join(',')}), rgb(${p.warm.join(',')}))`;
  if (vmax === null) {
    el('legMin').textContent = '—';
    el('legMax').textContent = '—';
  } else {
    el('legMin').textContent = `−${vmax.toPrecision(2)}`;
    el('legMax').textContent = `+${vmax.toPrecision(2)}`;
    const clipped = state._clipped && state._clipped > vmax * 1.05;
    el('legUnits').title = clipped
      ? `scale clipped at the 95th percentile; max |slope| = ${state._clipped.toPrecision(3)}`
      : '';
  }
  el('legUnits').textContent = e ? `${e.units} / year` : '';
}

/* -------------------------------------------------------------- analysis */
async function runAnalysis() {
  if (state.busy) return;
  state.busy = true;
  el('runBtn').disabled = true;
  showOverlay('loading', t('loading'));
  el('statusLine').textContent = '';

  const body = {
    region_id: state.regionId,
    variable_ids: [state.variableId],
    start_month: state.start,
    end_month: state.end,
  };
  if (state.aoi) body.aoi = aoiToPolygon(state.aoi);

  try {
    const res = await fetch(`${API}/v1/analyses`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const payload = await res.json();
    if (!res.ok) throw new ApiError(payload.error);
    state.jobId = payload.job_id;
    el('statusLine').textContent = `${t('queued')} ${payload.job_id}`;
    const job = await poll(payload.job_id);
    if (job.state === 'failed') throw new ApiError(job.error || { code: 'FAILED', detail: '' });
    await Promise.all([loadResult(job), loadSpatial(), loadExplanation()]);
    await loadSeries();
    hideOverlay();   // the insufficient-data case is a banner, not a blocker
    el('statusLine').textContent = '';
  } catch (err) {
    // offline fallback: a precomputed snapshot for exactly this request
    const snap = OFFLINE && OFFLINE.analyses
      ? OFFLINE.analyses[offlineKey(body)] : null;
    if (snap) {
      state.jobId = snap.job.job_id;
      state.result = snap.result;
      state.explanation = snap.explanation;
      state.series = (snap.series && snap.series.series)
        ? snap.series.series[0] : null;
      if (snap.spatial) state.spatial = snap.spatial;
      renderCard();
      drawMap();
      drawChart();
      hideOverlay();
      showBanner(state.lang === 'ar'
        ? 'وضع أوفلاين — نتيجة محسوبة مسبقًا من نفس الطريقة، بدون شبكة وبدون موديل.'
        : 'Offline snapshot — precomputed with the same method, no network, no model.', false);
      el('statusLine').textContent = '';
    } else {
      const code = err.code || 'ERROR';
      showOverlay('error', `${t('errPrefix')}: ${code}\n${err.message || ''}`);
    }
  } finally {
    state.busy = false;
    el('runBtn').disabled = false;
  }
}

class ApiError extends Error {
  constructor(e) {
    super(e?.detail || 'request failed');
    this.code = e?.code || 'ERROR';
  }
}

async function poll(jobId) {
  for (let i = 0; i < 900; i++) {
    const r = await fetch(`${API}/v1/analyses/${jobId}`);
    const j = await r.json();
    if (j.state === 'succeeded' || j.state === 'failed') return j;
    showOverlay('loading', `${t(j.state)} ${Math.round((j.progress || 0) * 100)}%`);
    await new Promise((res) => setTimeout(res, 400));
  }
  throw new ApiError({ code: 'TIMEOUT', detail: 'job did not finish' });
}

async function loadResult(job) {
  const r = await fetch(`${API}/v1/analyses/${job.job_id}/result`);
  const body = await r.json();
  if (!r.ok) throw new ApiError(body.error);
  state.result = body;
  renderCard();
  emitState();
  if (body.payload.state === 'insufficient_data') {
    showBanner(`${t('insufficientTitle')} — ${t('insufficientBody')}`, false);
  } else {
    hideBanner();
  }
}

async function loadSpatial() {
  const key = `${state.variableId}:${state.regionId}`;
  let r = null;
  try { r = await fetch(`${API}/v1/spatial/${state.variableId}/${state.regionId}`); }
  catch (e) { r = null; }
  if (!r || !r.ok) {
    if (OFFLINE && OFFLINE.spatial && OFFLINE.spatial[key]) {
      state.spatial = OFFLINE.spatial[key];
      drawMap();
      return;
    }
    state.spatial = null; drawMap(); return;
  }
  state.spatial = await r.json();
  el('fdrInfo').textContent =
    `FDR q=${state.spatial.fdr.q} · ${state.spatial.fdr.m_tested} ${t('tested')}`;
  drawMap();
}

async function loadExplanation() {
  if (!state.jobId) return;
  let r = null;
  try {
    r = await fetch(`${API}/v1/analyses/${state.jobId}/explanation?language=${state.lang}`);
  } catch (e) { r = null; }
  if (!r || !r.ok) {
    const key = `${state.jobId}:${state.lang}`;
    if (OFFLINE && OFFLINE.explanations && OFFLINE.explanations[key]) {
      state.explanation = OFFLINE.explanations[key];
      renderCard();
      return;
    }
    state.explanation = null; return;
  }
  state.explanation = await r.json();
  renderCard();
}

/* -------------------------------------------------------------- card */
function renderCard() {
  if (!state.result) return;
  el('cardEmpty').classList.add('hidden');
  el('card').classList.remove('hidden');
  const v = state.result.payload.variables[0];
  const tr = v.trend;
  const expl = state.explanation?.explanation;

  el('cardHeadline').textContent = expl?.answer || v.warnings.join(' ');

  if (tr.slope_per_year === null) {
    el('stSlope').textContent = '—';
    el('stCi').textContent = '—';
    el('stP').textContent = '—';
    el('stVerdict').textContent = t('noSlope');
  } else {
    el('stSlope').textContent = `${fmt(tr.slope_per_year)} ${v.units}/yr`;
    el('stCi').textContent = tr.ci_low === null ? '—'
      : `${fmt(tr.ci_low)} … ${fmt(tr.ci_high)}`;
    el('stP').textContent = tr.p_value === null ? '—' : tr.p_value.toPrecision(3);
    const sig = tr.p_value !== null && tr.p_value < 0.05;
    el('stVerdict').textContent = sig
      ? (state.lang === 'ar'
        ? 'النتيجة تحت حد 0.05 المجمّد — دليل ضد فرضية عدم الاتجاه، وليست احتمال أن الاتجاه حقيقي.'
        : 'Below the frozen 0.05 threshold — evidence against the no-trend null, not the probability that a trend is real.')
      : (state.lang === 'ar'
        ? 'فوق حد 0.05 المجمّد — النتيجة غير حاسمة، والميل معروض كما هو.'
        : 'Above the frozen 0.05 threshold — inconclusive; the effect size is still shown.');
  }
  el('stCover').textContent = `${(v.counts.valid_fraction * 100).toFixed(1)}% · ${v.counts.cells} ${t('cells')}`;

  const limits = expl?.limitations || [];
  el('limitList').innerHTML = limits.map((l) => `<li>${escapeHtml(l)}</li>`).join('');

  const spin = v.period_sensitivity;
  const rows = [];
  if (spin) {
    const full = spin.full_period;
    rows.push(spinRow(`${full.start}→${full.end}`, full.slope, true));
    spin.windows.forEach((wdw) => {
      if (wdw.slope === null || wdw.slope === undefined) return;
      rows.push(spinRow(`${wdw.start}→${wdw.end}`, wdw.slope, false));
    });
  }
  el('spinList').innerHTML = rows.join('') +
    (spin ? `<p class="hint">${state.lang === 'ar' ? 'توافق الإشارة' : 'sign agreement'}: ${
      spin.sign_agreement.positive}+ / ${spin.sign_agreement.negative}− · ${
      (spin.sign_agreement.fraction_same_sign_as_full * 100).toFixed(0)}%</p>` : '');

  const cites = state.explanation?.citations || [];
  el('citeList').innerHTML = cites.length
    ? cites.map((c) => `<li><a href="${escapeAttr(c.source_url || '#')}" target="_blank" rel="noopener">${
      escapeHtml(c.title || c.chunk_id)}</a>${c.page ? ` — p${c.page}` : ''}
      <span class="muted small">(${escapeHtml(c.authority || '')})</span></li>`).join('')
    : '<li class="muted">—</li>';

  el('receiptLine').textContent = state.result.receipt_id
    ? `${t('receipt')}: ${state.result.receipt_id} · ${t('method')} ${state.result.method_revision}`
    : '';
}

function spinRow(label, slope, isFull) {
  const max = Math.max(0.0001, Math.abs(slope) * 4);
  const pct = Math.min(50, (Math.abs(slope) / max) * 50);
  const cls = slope < 0 ? 'spin-bar neg' : 'spin-bar';
  const style = slope < 0
    ? `right:50%;width:${pct}%` : `left:50%;width:${pct}%`;
  return `<div class="spin-row"><span>${label}</span>
    <div class="spin-track"><div class="${cls}" style="${style}"></div></div>
    <span>${fmt(slope)}</span></div>`;
}

function fmt(v) {
  if (v === null || v === undefined) return '—';
  return (v >= 0 ? '+' : '') + v.toPrecision(3);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

/* ------------------------------------------------------- series chart */
async function loadSeries() {
  if (!state.jobId) return;
  try {
    const r = await fetch(`${API}/v1/analyses/${state.jobId}/series`);
    if (!r.ok) { state.series = null; return; }
    const body = await r.json();
    state.series = (body.series || [])[0] || null;
    drawChart();
  } catch (err) {
    const snap = OFFLINE && OFFLINE.series ? OFFLINE.series[state.jobId] : null;
    state.series = snap ? (snap.series || [])[0] || null : null;
    drawChart();
  }
}

function drawChart() {
  const c = el('chart');
  const dpr = window.devicePixelRatio || 1;
  const cssW = c.clientWidth || 820;
  const cssH = 170;
  c.width = Math.round(cssW * dpr);
  c.height = Math.round(cssH * dpr);
  c.style.height = `${cssH}px`;
  const ctx = c.getContext('2d');
  ctx.direction = 'ltr';
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);

  const s = state.series;
  el('chartMeta').textContent = s
    ? `${s.units} · ${s.months.length} months` : '';
  if (!s || !s.values || !s.values.length) return;

  const padL = 52, padR = 12, padT = 12, padB = 22;
  const vals = s.values.filter((v) => v !== null);
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if (s.trend_line) {
    const line = s.trend_line.filter((v) => v !== null);
    lo = Math.min(lo, ...line); hi = Math.max(hi, ...line);
  }
  const span = (hi - lo) || 1;
  lo -= span * 0.06; hi += span * 0.06;
  const X = (i) => padL + (i / (s.values.length - 1)) * (cssW - padL - padR);
  const Y = (v) => padT + (1 - (v - lo) / (hi - lo)) * (cssH - padT - padB);

  // grid + labels
  ctx.strokeStyle = '#1c2531';
  ctx.fillStyle = '#6c7c8f';
  ctx.font = '10px system-ui';
  for (let g = 0; g <= 2; g++) {
    const v = lo + (hi - lo) * (g / 2);
    const y = Y(v);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(cssW - padR, y); ctx.stroke();
    ctx.fillText(v.toPrecision(4), 6, y + 3);
  }
  const years = s.months.map((m) => m.slice(0, 4));
  years.forEach((y, i) => {
    if (i % 48 === 0) {
      ctx.fillText(y, X(i) - 10, cssH - 6);
    }
  });

  // monthly series
  ctx.strokeStyle = 'rgba(147,162,181,.55)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  let started = false;
  s.values.forEach((v, i) => {
    if (v === null) { started = false; return; }
    if (!started) { ctx.moveTo(X(i), Y(v)); started = true; }
    else ctx.lineTo(X(i), Y(v));
  });
  ctx.stroke();

  // server-computed trend line
  if (s.trend_line) {
    ctx.strokeStyle = '#4da3ff';
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    s.trend_line.forEach((v, i) => {
      if (v === null) return;
      if (i === 0) ctx.moveTo(X(i), Y(v)); else ctx.lineTo(X(i), Y(v));
    });
    ctx.stroke();
  }
}

/* ------------------------------------------------------- reality check */
function realityCheck(expectation) {
  document.querySelectorAll('[data-expect]').forEach((b) => {
    b.setAttribute('aria-pressed', String(b.dataset.expect === expectation));
  });
  const v = state.result?.payload?.variables?.[0];
  const box = el('rcVerdict');
  box.classList.remove('hidden');
  if (!v || v.state !== 'succeeded') {
    box.textContent = t('insufficientBody');
    return;
  }
  const slope = v.trend.slope_per_year;
  const p = v.trend.p_value;
  const sig = p !== null && p < 0.05;
  const dir = slope > 0 ? 'up' : slope < 0 ? 'down' : 'flat';
  const ar = state.lang === 'ar';
  let text;
  if (!sig) {
    text = expectation === 'flat'
      ? (ar ? 'التوقع «لا تغيّر واضح» متوافق مع النتيجة: مفيش اتجاه دال عند 0.05. لكن عدم الدلالة مش إثبات لغياب التغير.'
            : 'Your expectation matches the result: no trend detected at 0.05. Absence of evidence is not proof of absence.')
      : (ar ? 'البيانات غير حاسمة: مفيش اتجاه دال عند 0.05، فما ينفعش نقول إن توقعك مدعوم أو مخالف.'
            : 'The data are inconclusive: no trend detected at 0.05, so your expectation is neither supported nor contradicted.');
  } else if (dir === expectation) {
    text = ar ? 'البيانات تدعم توقعك في الإشارة والدلالة، لكن الميل وصف للتغير مش سبب له.'
              : 'The data support your expectation in sign and significance, but a slope describes change, not cause.';
  } else if (expectation === 'flat') {
    text = ar ? 'البيانات تخالف توقع «لا تغيّر»: فيه اتجاه دال في هذه النافذة.'
              : 'The data contradict the "no change" expectation: a trend is detected here.';
  } else {
    text = ar ? 'البيانات تخالف توقعك في الإشارة: الاتجاه الدال عكس ما توقعت.'
              : 'The data contradict your expectation in sign: the detected trend runs the other way.';
  }
  box.textContent = text;
}

/* ---------------------------------------------------- window comparison */
async function runCompare() {
  const btn = el('cmpBtn');
  btn.disabled = true;
  el('cmpTable').innerHTML = `<p class="hint">${t('loading')}</p>`;
  try {
    const r = await fetch(`${API}/v1/compare`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ variable_id: state.variableId,
                             start_month: state.start, end_month: state.end }),
    });
    const body = await r.json();
    if (!r.ok) throw new ApiError(body.error);
    renderCompare(body);
  } catch (err) {
    el('cmpTable').innerHTML = `<p class="hint">${t('errPrefix')}: ${escapeHtml(err.code || '')}</p>`;
  } finally {
    btn.disabled = false;
  }
}

function renderCompare(body) {
  const ar = state.lang === 'ar';
  const head = `<tr><th>${ar ? 'النافذة' : 'Window'}</th>
    <th>${ar ? 'الميل/سنة' : 'Slope/yr'}</th><th>p</th>
    <th>${ar ? 'التغطية' : 'Coverage'}</th></tr>`;
  const rows = body.regions.map((r) => {
    if (r.state !== 'succeeded') {
      return `<tr><td>${regionName(r.region_id)}</td>
        <td colspan="3" class="notsig">${r.state}</td></tr>`;
    }
    const sig = r.p_value !== null && r.p_value < 0.05;
    return `<tr><td>${regionName(r.region_id)}</td>
      <td class="num ${sig ? 'sig' : 'notsig'}">${fmt(r.slope_per_year)}</td>
      <td class="num">${r.p_value === null ? '—' : r.p_value.toPrecision(3)}</td>
      <td class="num">${(r.valid_fraction * 100).toFixed(1)}%</td></tr>`;
  }).join('');
  const note = ar
    ? 'نفس المتغير والفترة والطريقة وقاعدة التغطية؛ الشبكات الأصلية مختلفة، فالمقارنة في الميل لا في القيم المطلقة.'
    : body.note;
  el('cmpTable').innerHTML = `<table><thead>${head}</thead><tbody>${rows}</tbody></table>
    <p class="hint">${escapeHtml(note)}</p>`;
}

/* -------------------------------------------------------------- export */
function download(name, text, mime) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

async function exportReceipt() {
  if (!state.result?.receipt_id) return;
  const r = await fetch(`${API}/v1/receipts/${state.result.receipt_id}`);
  if (!r.ok) return;
  download(`receipt_${state.result.receipt_id}.json`,
    JSON.stringify(await r.json(), null, 2), 'application/json');
}

function exportResult() {
  if (!state.result) return;
  download(`result_${state.result.result_id}.json`,
    JSON.stringify(state.result, null, 2), 'application/json');
}

function exportCsv() {
  const s = state.series;
  if (!s) return;
  const rows = ['month,value,trend_line'];
  s.months.forEach((m, i) => {
    rows.push(`${m},${s.values[i] === null ? '' : s.values[i]},${
      s.trend_line && s.trend_line[i] !== undefined ? s.trend_line[i] : ''}`);
  });
  download(`series_${state.variableId}_${state.regionId}.csv`,
    rows.join('\n'), 'text/csv');
}

/* --------------------------------------------------------------- overlay */
function showOverlay(kind, text) {
  const o = el('overlay');
  o.className = `overlay ${kind}`;
  o.innerHTML = kind === 'loading'
    ? `<div><div class="spin"></div><div>${escapeHtml(text)}</div></div>`
    : `<div>${escapeHtml(text).replace(/\n/g, '<br>')}</div>`;
}
function hideOverlay() { el('overlay').className = 'overlay hidden'; }

function showBanner(text, isError) {
  const b = el('banner');
  b.textContent = text;
  b.className = `banner${isError ? ' error' : ''}`;
}
function hideBanner() { el('banner').className = 'banner hidden'; }

/* ------------------------------------------------------------------ state */
function emitState() {
  const snapshot = {
    lang: state.lang, regionId: state.regionId, variableId: state.variableId,
    period: { start: state.start, end: state.end },
    aoi: state.aoi, jobId: state.jobId,
    resultState: state.result?.payload?.state || null,
  };
  window.TDState = snapshot;
  window.dispatchEvent(new CustomEvent('td:statechange', { detail: snapshot }));
  if (state.result) {
    window.dispatchEvent(new CustomEvent('td:result', { detail: state.result.payload }));
  }
}

/* ------------------------------------------------------------------- init */
function initEvents() {
  el('langAr').onclick = () => { state.lang = 'ar'; applyLang(); if (state.jobId) loadExplanation(); };
  el('langEn').onclick = () => { state.lang = 'en'; applyLang(); if (state.jobId) loadExplanation(); };
  el('runBtn').onclick = runAnalysis;
  el('clearAoi').onclick = clearAoi;
  ['aoiW', 'aoiS', 'aoiE', 'aoiN'].forEach((id) => { el(id).onchange = readAoiInputs; });
  el('startMonth').onchange = (e) => { state.start = e.target.value; emitState(); };
  el('endMonth').onchange = (e) => { state.end = e.target.value; emitState(); };

  document.querySelectorAll('[data-expect]').forEach((b) => {
    b.onclick = () => realityCheck(b.dataset.expect);
  });
  el('cmpBtn').onclick = runCompare;
  el('expResult').onclick = exportResult;
  el('expReceipt').onclick = exportReceipt;
  el('expCsv').onclick = exportCsv;

  el('drawBtn').onclick = () => {
    state.drawing = !state.drawing;
    el('drawBtn').setAttribute('aria-pressed', String(state.drawing));
    canvas().style.cursor = state.drawing ? 'crosshair' : 'default';
  };

  const c = canvas();
  const toGeo = (evt) => {
    const e = currentEntry();
    if (!e) return null;
    const rect = c.getBoundingClientRect();
    const x = (evt.clientX - rect.left) * (c.clientWidth / rect.width);
    const y = (evt.clientY - rect.top) * (c.clientHeight / rect.height);
    const proj = project(state.spatial, e.bbox);
    const [w, s, ea, n] = e.bbox;
    const lon = w + (x - (proj.W - (ea - w) * proj.k * proj.stretch * proj.scale) / 2) /
      (proj.k * proj.stretch * proj.scale);
    const lat = n - (y - (proj.H - (n - s) * proj.scale) / 2) / proj.scale;
    return {
      lon: Math.min(ea, Math.max(w, lon)),
      lat: Math.min(n, Math.max(s, lat)),
    };
  };

  c.addEventListener('pointerdown', (evt) => {
    if (!state.drawing) return;
    state.dragStart = toGeo(evt);
    c.setPointerCapture(evt.pointerId);
  });
  c.addEventListener('pointermove', (evt) => {
    if (!state.drawing || !state.dragStart) return;
    const now = toGeo(evt);
    state.aoi = {
      w: Math.min(state.dragStart.lon, now.lon), e: Math.max(state.dragStart.lon, now.lon),
      s: Math.min(state.dragStart.lat, now.lat), n: Math.max(state.dragStart.lat, now.lat),
    };
    drawMap();
  });
  c.addEventListener('pointerup', (evt) => {
    if (!state.drawing || !state.dragStart) return;
    state.dragStart = null;
    state.drawing = false;
    el('drawBtn').setAttribute('aria-pressed', 'false');
    c.style.cursor = 'default';
    if (state.aoi) {
      el('aoiW').value = state.aoi.w.toFixed(2);
      el('aoiS').value = state.aoi.s.toFixed(2);
      el('aoiE').value = state.aoi.e.toFixed(2);
      el('aoiN').value = state.aoi.n.toFixed(2);
    }
    emitState();
  });

  window.addEventListener('resize', drawMap);
}

async function boot() {
  fillMonths();
  initEvents();
  applyLang();
  try {
    await loadCatalog();
    await loadSpatial();
  } catch (err) {
    showOverlay('error', `${t('errPrefix')}: ${err.message}`);
  }
  emitState();
  // ?autorun=1 runs one analysis immediately: useful for screenshots and for
  // the demo checklist, and it exercises exactly the normal code path.
  const params = new URLSearchParams(window.location.search);
  if (params.get('lang') === 'en' || params.get('lang') === 'ar') {
    state.lang = params.get('lang');
    applyLang();
  }
  if (params.get('autorun') === '1') {
    if (params.get('region')) state.regionId = params.get('region');
    if (params.get('variable')) state.variableId = params.get('variable');
    if (params.get('start')) state.start = params.get('start');
    if (params.get('end')) state.end = params.get('end');
    const aoi = params.get('aoi');           // "w,s,e,n"
    if (aoi) {
      const [w, s, e, n] = aoi.split(',').map(Number);
      if ([w, s, e, n].every(Number.isFinite)) state.aoi = { w, s, e, n };
    }
    el('startMonth').value = state.start;
    el('endMonth').value = state.end;
    renderVariables();
    renderRegionLabel();
    drawMap();
    await runAnalysis();
    if (params.get('compare') === '1') await runCompare();
    const expect = params.get('expect');
    if (expect && ['up', 'down', 'flat'].includes(expect)) realityCheck(expect);
  }
}

boot();
