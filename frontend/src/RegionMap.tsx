import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './region-map.css';
import type { BBox, CatalogEntry, Lang, RegionId, Spatial } from './api';

type Props = {
  entries: CatalogEntry[]; region: RegionId; lang: Lang; aoi: BBox | null;
  spatial: Spatial | null; onRegion: (id: RegionId) => void; onAoi: (box: BBox | null) => void;
};
const bounds = (b: number[]) => L.latLngBounds([b[1], b[0]], [b[3], b[2]]);

export function RegionMap(props: Props) {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const latest = useRef(props);
  latest.current = props;
  const mode = useRef(false);
  const corner = useRef<L.LatLng | null>(null);
  const preview = useRef<L.Rectangle | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [firstCorner, setFirstCorner] = useState(false);
  const [error, setError] = useState('');
  const [tilesFailed, setTilesFailed] = useState(false);
  const [overview, setOverview] = useState(true);
  const en = props.lang === 'en';

  function cancelDrawing() {
    mode.current = false; corner.current = null;
    preview.current?.remove(); preview.current = null;
    setDrawing(false); setFirstCorner(false); setError('');
  }

  useEffect(() => {
    if (!host.current) return;
    const instance = L.map(host.current, { center: [25, 12], zoom: 3, minZoom: 2, maxZoom: 18,
      worldCopyJump: false, preferCanvas: true });
    map.current = instance;
    L.tileLayer(import.meta.env.VITE_MAP_TILE_URL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: import.meta.env.VITE_MAP_ATTRIBUTION || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19, noWrap: true,
    }).on('tileerror', () => setTilesFailed(true)).addTo(instance);
    L.control.scale({ imperial: false }).addTo(instance);
    const observer = new ResizeObserver(() => instance.invalidateSize());
    observer.observe(host.current);
    instance.on('click', (event: L.LeafletMouseEvent) => {
      if (!mode.current) return;
      const { entries, region, lang, onAoi } = latest.current;
      const entry = entries.find(e => e.region_id === region);
      if (!entry || !bounds(entry.bbox).contains(event.latlng)) {
        setError(lang === 'en' ? 'Choose points inside the highlighted study region.' : 'اختار النقط داخل حدود منطقة الدراسة المحددة.');
        return;
      }
      setError('');
      if (!corner.current) {
        corner.current = event.latlng; setFirstCorner(true);
        return;
      }
      const box = L.latLngBounds(corner.current, event.latlng);
      if (box.getEast() - box.getWest() < .25 || box.getNorth() - box.getSouth() < .25) {
        setError(lang === 'en' ? 'Choose an area at least 0.25° wide and high.' : 'اختار مساحة عرضها وارتفاعها على الأقل 0.25 درجة.');
        return;
      }
      onAoi({ w: box.getWest(), s: box.getSouth(), e: box.getEast(), n: box.getNorth() });
      cancelDrawing();
    });
    instance.on('mousemove', (event: L.LeafletMouseEvent) => {
      if (!mode.current || !corner.current) return;
      const entry = latest.current.entries.find(e => e.region_id === latest.current.region);
      if (!entry) return;
      const [w,s,e,n] = entry.bbox;
      const endpoint = L.latLng(Math.max(s,Math.min(n,event.latlng.lat)), Math.max(w,Math.min(e,event.latlng.lng)));
      const box = L.latLngBounds(corner.current, endpoint);
      if (!preview.current) preview.current = L.rectangle(box, { color: '#f6b43f', dashArray: '6 5', interactive: false }).addTo(instance);
      else preview.current.setBounds(box);
    });
    return () => { observer.disconnect(); instance.remove(); map.current = null; preview.current = null; };
  }, []);

  useEffect(() => {
    const instance = map.current;
    if (!instance) return;
    const regions = [...new Map(props.entries.map(e => [e.region_id, e])).values()];
    const group = L.layerGroup().addTo(instance);
    regions.forEach(entry => {
      const selected = entry.region_id === props.region;
      L.rectangle(bounds(entry.bbox), { color: selected ? '#047857' : '#334d82', weight: selected ? 3 : 2,
        fillOpacity: selected ? .08 : .04, bubblingMouseEvents: true })
        .bindTooltip((props.lang === 'ar' ? entry.region_label_ar : entry.region_label) || entry.region_id.replaceAll('_', ' '), { sticky: true })
        .on('click', () => { if (!mode.current && entry.region_id !== latest.current.region) latest.current.onRegion(entry.region_id); })
        .addTo(group);
    });
    return () => { group.remove(); };
  }, [props.entries, props.region]);

  const selectedBounds = props.entries.find(e => e.region_id === props.region)?.bbox.join(',');
  const allBounds = [...new Map(props.entries.map(e => [e.region_id,e.bbox.join(',')])).values()].sort().join(';');
  useEffect(() => {
    cancelDrawing();
  }, [props.region, selectedBounds]);

  useEffect(() => {
    const instance = map.current;
    if (!instance || !selectedBounds) return;
    const area = bounds(selectedBounds.split(',').map(Number));
    if (overview) allBounds.split(';').filter(Boolean).forEach(b => area.extend(bounds(b.split(',').map(Number))));
    const fit = () => {
      instance.setMinZoom(2);
      instance.fitBounds(area, { padding: [30,30], maxZoom: 8, animate: false });
    };
    fit();
    instance.on('resize', fit);
    return () => { instance.off('resize', fit); };
  }, [selectedBounds, allBounds, overview]);

  useEffect(() => {
    if (!map.current || !props.aoi) return;
    const b = props.aoi;
    const rectangle = L.rectangle(bounds([b.w, b.s, b.e, b.n]), { color: '#d77700', fillOpacity: .15, interactive: false }).addTo(map.current);
    return () => { rectangle.remove(); };
  }, [props.aoi]);

  useEffect(() => {
    const spatial = props.spatial;
    if (!map.current || !spatial) return;
    const group = L.layerGroup().addTo(map.current);
    const lat = spatial.grid.lat, lon = spatial.grid.lon;
    const finite = spatial.slope.flat().filter((v): v is number => v != null && Number.isFinite(v));
    const max = finite.reduce((m,v) => Math.max(m, Math.abs(v)), 1e-12);
    // Canvas renderer keeps native-grid cells in map coordinates during pan and zoom.
    lat.forEach((y, row) => lon.forEach((x, col) => {
      const value = spatial.slope[row]?.[col];
      if (value == null || !Number.isFinite(value)) return;
      const south = row ? (lat[row-1]+y)/2 : spatial.bbox[1];
      const north = row+1<lat.length ? (lat[row+1]+y)/2 : spatial.bbox[3];
      const west = col ? (lon[col-1]+x)/2 : spatial.bbox[0];
      const east = col+1<lon.length ? (lon[col+1]+x)/2 : spatial.bbox[2];
      L.rectangle(bounds([west,south,east,north]), { stroke: false, fillColor: value === 0 ? '#899ca2' : value>0 ? '#23985a' : '#ca7839',
        fillOpacity: .2+.5*Math.min(1,Math.abs(value)/max), interactive: false }).addTo(group);
    }));
    return () => { group.remove(); };
  }, [props.spatial]);

  return <section className={`region-map ${drawing ? 'is-selecting' : ''}`} aria-label={en ? 'Interactive study region map' : 'خريطة مناطق الدراسة التفاعلية'}>
    <div className="region-map-toolbar">
      <button type="button" disabled={!selectedBounds} onClick={() => { cancelDrawing(); setOverview(value => !value); }}>{overview ? (en ? 'Selected region' : 'المنطقة المحددة') : (en ? 'All regions' : 'كل المناطق')}</button>
      <button type="button" aria-pressed={drawing} disabled={!selectedBounds} onClick={() => { if (drawing) cancelDrawing(); else { setOverview(false); mode.current=true; setDrawing(true); setError(''); } }}>{drawing ? (en ? 'Cancel' : 'إلغاء') : (en ? 'Select area' : 'حدد مساحة')}</button>
      <button type="button" disabled={!props.aoi} onClick={() => { cancelDrawing(); props.onAoi(null); }}>{en ? 'Use full region' : 'استخدم المنطقة كلها'}</button>
    </div>
    <div ref={host} className="region-map-canvas" />
    <div className="region-map-help" role="status" aria-live="polite">
      {error || (drawing ? (en ? (firstCorner ? 'Click the opposite corner.' : 'Click the first corner inside the study region.') : (firstCorner ? 'اضغط على الركن المقابل.' : 'اضغط على أول ركن داخل منطقة الدراسة.')) : (en ? 'Click a region to select it. Pan and zoom to explore.' : 'اضغط على منطقة لاختيارها. حرّك الخريطة وكبّرها للاستكشاف.'))}
      {props.aoi && <small>{[props.aoi.w,props.aoi.s,props.aoi.e,props.aoi.n].map(v => v.toFixed(3)).join(' / ')}</small>}
      {tilesFailed && <small>{en ? 'Background tiles could not load. Check your connection; region selection remains available.' : 'تعذّر تحميل خلفية الخريطة. راجع الاتصال؛ اختيار المناطق ما زال متاح.'}</small>}
    </div>
  </section>;
}
