import React, { useEffect, useRef, useState } from "react";
import {ReferenceActors} from './ReferenceActors';
import { GeoBackdrop, mapExtent } from "./GeoBackdrop";
import { createRoot } from "react-dom/client";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Database,
  Download,
  ExternalLink,
  Globe2,
  Leaf,
  Layers3,
  MapPinned,
  Menu,
  Microscope,
  Satellite,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import {
  analyse,
  compare,
  getCatalog,
  getExplanation,
  getReceipt,
  isOffline,
  type Analysis,
  type BBox,
  type Catalog,
  type CatalogEntry,
  type Lang,
  type RegionId,
  type Series,
  type Spatial,
  type VariableId,
} from "./api";
import "./style.css";
import "./product-theme.css";
import "./reference-layout.css";

const REGIONS: { id: RegionId; en: string; ar: string; caption: string }[] = [
  {
    id: "nile_corridor",
    en: "Nile Corridor",
    ar: "وادي النيل",
    caption: "Egypt",
  },
  {
    id: "morocco_comparison",
    en: "Morocco",
    ar: "المغرب",
    caption: "North Africa",
  },
  { id: "sahel_comparison", en: "Sahel", ar: "الساحل", caption: "West Africa" },
];
const VARIABLES: {
  id: VariableId;
  en: string;
  ar: string;
  icon: typeof Leaf;
  color: string;
}[] = [
  {
    id: "air_temperature",
    en: "Air temperature",
    ar: "درجة حرارة الهواء",
    icon: Globe2,
    color: "#efae74",
  },
  {
    id: "precipitation",
    en: "Precipitation",
    ar: "الهطول",
    icon: Layers3,
    color: "#6fb9ee",
  },
  {
    id: "soil_moisture",
    en: "Soil moisture",
    ar: "رطوبة التربة",
    icon: Database,
    color: "#c6ad8b",
  },
  {
    id: "vegetation_greenness",
    en: "Vegetation greenness",
    ar: "اخضرار النبات",
    icon: Leaf,
    color: "#a9e677",
  },
];
const fmt = (n: number | null | undefined, digits = 3) =>
  n == null || !Number.isFinite(n)
    ? "—"
    : Number(n).toLocaleString("en-US", {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      });
const regionLabel = (id: string, lang: Lang) =>
  REGIONS.find((r) => r.id === id)?.[lang] || id;
const variableLabel = (id: string, lang: Lang) =>
  VARIABLES.find((v) => v.id === id)?.[lang] || id;

function SceneHeader({
  lang,
  setLang,
  setPage,
}: {
  lang: Lang;
  setLang: (l: Lang) => void;
  setPage: (p: string) => void;
}) {
  const [menu, setMenu] = useState(false);
  return (
    <header className="scene-header">
      <button
        className="wordmark"
        onClick={() => {
          setPage("home");
          scrollTo({ top: 0, behavior: "smooth" });
        }}
        aria-label="AstraVerd home"
      >
        <span className="logo-mark">✦</span> ASTRAVERD
      </button>
      <nav className={menu ? "open" : ""} aria-label="Main navigation">
        <button
          onClick={() => {
            setPage("home");
            setMenu(false);
            document
              .getElementById("story")
              ?.scrollIntoView({ behavior: "smooth" });
          }}
        >
          {lang === "en" ? "Explore" : "استكشف"}
        </button>
        <button
          onClick={() => {
            setPage("home");
            setMenu(false);
            setTimeout(
              () =>
                document
                  .getElementById("method")
                  ?.scrollIntoView({ behavior: "smooth" }),
              20,
            );
          }}
        >
          {lang === "en" ? "How it works" : "كيف تعمل"}
        </button>
        <button
          onClick={() => {
            setPage("home");
            setMenu(false);
            setTimeout(
              () =>
                document
                  .getElementById("sources")
                  ?.scrollIntoView({ behavior: "smooth" }),
              20,
            );
          }}
        >
          {lang === "en" ? "Data sources" : "مصادر البيانات"}
        </button>
      </nav>
      <div className="head-actions">
        <button
          className="lang-button"
          onClick={() => setLang(lang === "en" ? "ar" : "en")}
        >
          {lang === "en" ? "عربي" : "EN"}
        </button>
        <button
          className="launch"
          onClick={() => {
            setPage("explore");
            setMenu(false);
            scrollTo({ top: 0 });
          }}
        >
          {lang === "en" ? "Launch explorer" : "افتح المستكشف"}{" "}
          <ArrowUpRight size={16} />
        </button>
        <button
          className="mobile-menu"
          onClick={() => setMenu(!menu)}
          aria-label="Open menu"
        >
          {menu ? <X /> : <Menu />}
        </button>
      </div>
    </header>
  );
}

function Landing({ lang, onLaunch }: { lang: Lang; onLaunch: () => void }) {
  const [previewYear,setPreviewYear]=useState(2001);
  const dragStart = useRef<number | null>(null);
  const touchStart = useRef<{ x: number; y: number } | null>(null);
  const [dragProgress, setDragProgress] = useState(0);
  const finishDrag = (clientX: number) => {
    if (dragStart.current !== null && clientX - dragStart.current > 85) onLaunch();
    dragStart.current = null;
    setDragProgress(0);
  };
  return (
    <main className="landing">
      <ReferenceActors/>

      <section className="hero" aria-labelledby="hero-title"
        onTouchStart={(event) => { touchStart.current = { x: event.touches[0].clientX, y: event.touches[0].clientY }; }}
        onTouchEnd={(event) => {
          if (!touchStart.current) return;
          const dx = event.changedTouches[0].clientX - touchStart.current.x;
          const dy = event.changedTouches[0].clientY - touchStart.current.y;
          if (dx > 95 && Math.abs(dy) < 65) onLaunch();
          touchStart.current = null;
        }}>
        <div
          className="hero-art"
          role="img"
          aria-label="Illustrated astrobotanist looking at Earth from a research observatory"
        />
        <div className="hero-veil" />
        <div className="hero-copy">
          <h1 id="hero-title">
            {lang === "en" ? "READ THE EARTH." : "اقرأ الأرض."}
          </h1>
          <p className="hero-sub">
            {lang === "en" ? "Question the trend." : "اسأل عن الاتجاه."}
          </p>
          <p className="hero-lead">
            {lang === "en"
              ? "Explore Earth data. Test what the chart really says."
              : "استكشف بيانات الأرض. واختبر ما تقوله الرسوم فعلًا."}
          </p>
          <button className="hero-mobile-cta" onClick={onLaunch}>
            {lang === "en" ? "Launch explorer" : "افتح المستكشف"}{" "}
            <ArrowRight size={17} />
          </button>
        </div>
        <div className="hero-bottom">
          <div>
            <span className="lime-square" />
            {lang === "en" ? "Choose a variable" : "اختر متغيرًا"}
          </div>
          <div>
            <span className="lime-square" />
            {lang === "en" ? "Change the time window" : "غيّر الفترة الزمنية"}
          </div>
          <div>
            <span className="lime-square" />
            {lang === "en" ? "Inspect the evidence" : "افحص الدليل"}
          </div>
        </div>
        <button
          className="investigate-rail"
          onClick={onLaunch}
          onPointerDown={(event) => {
            dragStart.current = event.clientX;
            event.currentTarget.setPointerCapture(event.pointerId);
          }}
          onPointerMove={(event) => {
            if (dragStart.current !== null)
              setDragProgress(Math.min(1, Math.max(0, (event.clientX - dragStart.current) / 110)));
          }}
          onPointerUp={(event) => finishDrag(event.clientX)}
          onPointerCancel={() => { dragStart.current = null; setDragProgress(0); }}
          style={{ "--drag-progress": dragProgress } as React.CSSProperties}
          aria-label={lang === "en" ? "Open the investigation. Drag right or tap." : "افتح التحقيق. اسحب لليمين أو اضغط."}
        >
          <span className="rail-icon"><ArrowRight size={19} /></span>
          <span className="rail-copy">
            <strong>{lang === "en" ? "INVESTIGATE" : "ابدأ التحقيق"}</strong>
            <small>{lang === "en" ? "SWIPE RIGHT ANYWHERE" : "اسحب يمين الشاشة"}</small>
          </span>
        </button>
        <a className="scroll-hint" href="#story">
          {lang === "en" ? "Scroll down to learn how it works" : "انزل لتعرف كيف تعمل الأداة"}{" "}
          <ChevronDown size={25} />
        </a>
        <span className="art-note">
          {lang === "en"
            ? "Illustrated scene, not measured data"
            : "مشهد مرسوم وليس بيانات مقاسة"}
        </span>
      </section>
      <section className="science-band" aria-labelledby="science-band-title">
        <div>
          <span className="eyebrow">{lang === "en" ? "THE MISSION" : "المهمة"}</span>
          <h2 id="science-band-title">{lang === "en" ? "From Earth data to a claim you can defend." : "من بيانات الأرض إلى استنتاج يمكن الدفاع عنه."}</h2>
          <p>{lang === "en" ? "Choose a place and a NASA variable. AstraVerd tests the trend, shows how the answer changes with time and location, and keeps the evidence attached." : "اختر مكانًا ومتغيرًا من NASA. تختبر AstraVerd الاتجاه، وتكشف أثر اختيار الزمن والمكان، وتربط النتيجة بدليلها."}</p>
        </div>
        <div className="science-flow">
          <div><Satellite size={22}/><strong>{lang === "en" ? "Observe" : "ارصد"}</strong><span>MERRA-2 · GPM · GLDAS · MODIS</span></div>
          <div><Layers3 size={22}/><strong>{lang === "en" ? "Test" : "اختبر"}</strong><span>{lang === "en" ? "Monthly series · slope · significance" : "قيم شهرية · ميل · دلالة"}</span></div>
          <div><ShieldCheck size={22}/><strong>{lang === "en" ? "Verify" : "تحقق"}</strong><span>{lang === "en" ? "Methods · limits · evidence receipt" : "الطريقة · القيود · إيصال الدليل"}</span></div>
        </div>
      </section>
      <section id="story" className="story-section average">
        <div className="story-text">
          <div className="eyebrow">
            01 / {lang === "en" ? "PLACE" : "المكان"}
          </div>
          <h2>
            {lang === "en"
              ? "Choose a place and NASA variable"
              : "أين يحدث التغير؟"}
          </h2>
          <p>
            {lang === "en"
              ? "Our explorer starts with a real place, not a headline. Select an area and compare its NASA observations with nearby regions; one average can hide opposite local trends."
              : "يبدأ المستكشف بمكان حقيقي، لا بعنوان جاهز. اختر منطقة وقارن رصد NASA فيها بالمناطق المجاورة؛ قد يخفي المتوسط اتجاهات محلية متعاكسة."}
          </p>
          <ul className="chapter-benefits"><li><MapPinned/><div><strong>Choose a place</strong><span>Select a study region or draw an area.</span></div></li><li><Layers3/><div><strong>Choose a NASA variable</strong><span>Explore temperature, rainfall, soil moisture and vegetation.</span></div></li><li><Sparkles/><div><strong>Load the time series</strong><span>Follow monthly observations through time.</span></div></li></ul>
          <button onClick={onLaunch} className="text-link">
            {lang === "en" ? "Compare regions" : "قارن المناطق"}{" "}
            <ArrowUpRight size={18} />
          </button>
        </div>
        <div className="story-visual region-visual">
          <div className="observatory-title"><Satellite size={20}/> Earth observatory <span>01 / Choose data</span></div>
          <div className="observatory-map"><GeoBackdrop/><span className="place-pin"><MapPinned size={25}/> Nile Corridor</span><small>NASA Blue Marble · Natural Earth boundaries</small></div>
          <div className="observatory-controls"><label>Place</label><button className="preview-field" onClick={onLaunch}><MapPinned size={16}/> Nile Corridor, Egypt <ChevronDown size={14}/></button><label>NASA variable</label><button className="preview-field" onClick={onLaunch}><Globe2 size={16}/> Air temperature <ChevronDown size={14}/></button><p>MERRA-2 · Monthly observations<br/>2001–2024 · Reanalysis</p><button onClick={onLaunch}>Load time series <ArrowRight size={17}/></button></div>
          <div className="visual-foot">
            <span>{lang === "en" ? "ARRIVE / SELECT A PLACE" : "الوصول / اختيار المكان"}</span>
            <span>{lang === "en" ? "PLANT ONE QUESTION" : "ازرع سؤالًا"}</span>
          </div>
          <span className="concept-note">
            {lang === "en" ? "CONCEPTUAL ILLUSTRATION" : "رسم توضيحي"}
          </span>
        </div>
      </section>
      <section id="method" className="story-section window">
        <div className="story-visual window-visual">
          <div className="monitor-head">
            <span className="status-dot" />{" "}
            {lang === "en" ? "PERIOD SENSITIVITY" : "حساسية الفترة"}{" "}
            <span>2001 — 2024</span>
          </div>
          <svg
            viewBox="0 0 700 300"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path
              className="gridline"
              d="M0 75H700 M0 150H700 M0 225H700 M100 0V300 M200 0V300 M300 0V300 M400 0V300 M500 0V300 M600 0V300"
            />
            <path
              className="chart-path"
              d="M15 245L30 168L45 228L60 205L75 242L90 140L105 214L120 187L135 207L150 160L165 222L180 120L195 183L210 155L225 198L240 135L255 174L270 98L285 164L300 141L315 183L330 112L345 152L360 82L375 148L390 128L405 165L420 102L435 133L450 65L465 127L480 110L495 149L510 92L525 118L540 49L555 110L570 96L585 135L600 72L615 99L630 35L645 94L660 73L682 100"
            />
            <path d="M15 218L682 83" stroke="#ecaa65" strokeWidth="3"/>
            <rect
              x={(previewYear-2001)/23*550}
              y="10"
              width={680-(previewYear-2001)/23*550}
              height="280"
              className="window-focus"
            />
            <path d="M195 18V290 M515 18V290" className="window-guide" />
          </svg>
          <label className="preview-range">Time window <span>{previewYear} — 2024</span><input aria-label="Illustrative time window start" type="range" min="2001" max="2018" value={previewYear} onChange={e=>setPreviewYear(Number(e.target.value))}/></label>
          <div className="window-labels">
            <span>{lang === "en" ? "FULL PERIOD" : "الفترة الكاملة"}</span>
            <span>{lang === "en" ? "SELECTED WINDOW" : "الفترة المختارة"}</span>
          </div>
          <span className="concept-note">
            {lang === "en" ? "CONCEPTUAL ILLUSTRATION" : "رسم توضيحي"}
          </span>
        </div>
        <div className="story-text">
          <div className="eyebrow">02 / {lang === "en" ? "TIME" : "الزمن"}</div>
          <h2>{lang === "en" ? "Challenge a trend by changing the time window" : "اختبر الاتجاه بتغيير الفترة الزمنية"}</h2>
          <p>
            {lang === "en"
              ? "Rain changes by the hour; an Earth-system trend needs years. Change the start and end dates to see whether your conclusion survives a different window."
              : "المطر يتغير كل ساعة؛ اتجاه نظام الأرض يحتاج سنوات. غيّر بداية الفترة ونهايتها لتعرف هل يصمد الاستنتاج أم يعتمد على نافذة مختارة."}
          </p>
          <ul className="chapter-benefits"><li><Clock3/><div><strong>Adjust the time window</strong><span>Compare alternative start and end dates.</span></div></li><li><Layers3/><div><strong>See how the trend changes</strong><span>Inspect the slope and uncertainty together.</span></div></li><li><ShieldCheck/><div><strong>Assess robustness</strong><span>Check whether the conclusion survives your choices.</span></div></li></ul>
          <button onClick={onLaunch} className="text-link">
            {lang === "en" ? "Test a time window" : "اختبر فترة زمنية"}{" "}
            <ArrowUpRight size={18} />
          </button>
        </div>
      </section>
      <div className="evidence-finale">
      <section id="sources" className="story-section evidence">
        <div className="story-text">
          <div className="eyebrow">
            03 / {lang === "en" ? "PROOF" : "الدليل"}
          </div>
          <h2>{lang === "en" ? "Inspect the evidence" : "أظهر الدليل"}</h2>
          <p>
            {lang === "en"
              ? "The answer is more than a number. Inspect the source, trend method, confidence interval, valid coverage and limitations; then carry them with the claim."
              : "الإجابة أكثر من رقم. افحص المصدر وطريقة الاتجاه ومجال الثقة والتغطية الصالحة والقيود، ثم احتفظ بها مع الاستنتاج."}
          </p>
          <ul className="chapter-benefits"><li><BookOpen/><div><strong>See the complete receipt</strong><span>Keep sources and methods with the result.</span></div></li><li><ShieldCheck/><div><strong>Understand the uncertainty</strong><span>Read the interval, significance and coverage.</span></div></li><li><Layers3/><div><strong>Know the boundaries</strong><span>Check resolution and limitations before drawing conclusions.</span></div></li></ul>
          <button onClick={onLaunch} className="text-link">
            {lang === "en" ? "Open the evidence lab" : "افتح معمل الدليل"}{" "}
            <ArrowUpRight size={18} />
          </button>
        </div>
        <div className="story-visual receipt-visual">
          <div className="receipt-head">
            <ShieldCheck size={24} />
            <span>{lang === "en" ? "EVIDENCE RECEIPT" : "إيصال الدليل"}</span>
          </div>
          {[
            [Database, "SOURCE"],
            [Microscope, "METHOD"],
            [Layers3, "UNCERTAINTY"],
            [CircleHelp, "LIMITATIONS"],
          ].map(([Icon, label]) => {
            const I = Icon as typeof Database;
            return (
              <div className="receipt-row" key={label as string}>
                <I size={20} />
                <span>{label as string}</span>
                <span className="receipt-detail">{label === 'SOURCE' ? 'NASA product & version' : label === 'METHOD' ? 'Trend method & time window' : label === 'UNCERTAINTY' ? '95% interval & valid coverage' : 'Resolution, gaps & assumptions'}</span>
              </div>
            );
          })}
        </div>
      </section>
      <div className="closing">
        <span className="eyebrow">
          {lang === "en" ? "YOUR INVESTIGATION STARTS HERE" : "تحقيقك يبدأ هنا"}
        </span>
        <h2>
          {lang === "en"
            ? "Explore Earth’s changing patterns with NASA data"
            : "ماذا تُظهر الصورة الكاملة؟"}
        </h2>
        <button className="launch big" onClick={onLaunch}>
          {lang === "en" ? "Launch explorer" : "افتح المستكشف"}{" "}
          <ArrowUpRight size={20} />
        </button>
      </div>
      </div>
      <footer>
        <span>ASTRAVERD</span>
        <span>
          {lang === "en"
            ? "Independent Space Apps project. NASA products are credited with every analysis."
            : "مشروع مستقل في Space Apps. مصادر NASA موثقة مع كل تحليل."}
        </span>
      </footer>
    </main>
  );
}

function SeriesChart({ series, lang }: { series: Series | null; lang: Lang }) {
  if (!series)
    return (
      <div className="chart-empty">
        {lang === "en"
          ? "Run an analysis to see the monthly series."
          : "شغّل التحليل لعرض السلسلة الشهرية."}
      </div>
    );
  const values = series.values.filter(
    (v): v is number => v != null && Number.isFinite(v),
  );
  if (!values.length)
    return (
      <div className="chart-empty">
        {lang === "en"
          ? "No valid values for this selection."
          : "لا توجد قيم صالحة لهذا الاختيار."}
      </div>
    );
  const min = Math.min(...values),
    max = Math.max(...values),
    span = max - min || 1;
  const xy = (v: number, i: number) =>
    `${48 + (i / Math.max(1, series.values.length - 1)) * 830},${245 - ((v - min) / span) * 190}`;
  const monthly = series.values
    .map((v, i) => (v == null ? "" : xy(v, i)))
    .filter(Boolean)
    .join(" ");
  const trend = series.trend_line
    .map((v, i) => (v == null ? "" : xy(v, i)))
    .filter(Boolean)
    .join(" ");
  return (
    <svg
      className="series-chart"
      viewBox="0 0 920 290"
      role="img"
      aria-label="Monthly values and server-computed trend line"
    >
      <path d="M48 55H878 M48 150H878 M48 245H878" className="axis-grid" />
      <polyline points={monthly} className="monthly-line" />
      <polyline points={trend} className="trend-line" />
      <text x="48" y="277">
        {series.months[0]?.slice(0, 4)}
      </text>
      <text x="838" y="277">
        {series.months.at(-1)?.slice(0, 4)}
      </text>
      <text x="8" y="65">
        {fmt(max, 2)}
      </text>
      <text x="8" y="246">
        {fmt(min, 2)}
      </text>
    </svg>
  );
}

function SpatialMap({
  spatial,
  lang,
  onAoi,
}: {
  spatial: Spatial | null;
  lang: Lang;
  onAoi: (b: BBox) => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const start = useRef<{ x: number; y: number } | null>(null);
  const [selection, setSelection] = useState<{
    x: number;
    y: number;
    w: number;
    h: number;
  } | null>(null);
  useEffect(() => {
    const c = canvas.current;
    if (!c || !spatial) return;
    const rows = spatial.slope.length,
      cols = spatial.slope[0]?.length || 0;
    if (!rows || !cols) return;
    const cell = 8;
    c.width = cols * cell;
    c.height = rows * cell;
    const ctx = c.getContext("2d");
    if (!ctx) return;
    const vals = spatial.slope
      .flat()
      .filter((v): v is number => v != null && Number.isFinite(v));
    const bound = Math.max(0.000001, Math.max(...vals.map(Math.abs)));
    for (let y = 0; y < rows; y++)
      for (let x = 0; x < cols; x++) {
        const v = spatial.slope[y][x];
        if (v == null || !Number.isFinite(v)) {
          ctx.fillStyle = "#223047";
        } else {
          const t = Math.min(1, Math.abs(v) / bound);
          ctx.fillStyle =
            v >= 0
              ? `rgb(${Math.round(36 + 125 * t)},${Math.round(112 + 86 * t)},${Math.round(82 + 10 * t)})`
              : `rgb(${Math.round(64 + 134 * t)},${Math.round(91 + 80 * t)},${Math.round(110 + 8 * t)})`;
        }
        ctx.fillRect(x * cell, y * cell, cell, cell);
        if (spatial.significant_fdr?.[y]?.[x]) {
          ctx.strokeStyle = "#eff8e5";
          ctx.lineWidth = 1;
          ctx.strokeRect(x * cell + 0.5, y * cell + 0.5, cell - 1, cell - 1);
        }
      }
  }, [spatial]);
  if (!spatial)
    return (
      <div className="map-placeholder">
        <div className="radar-ring">
          <Globe2 size={62} />
        </div>
        <p>
          {lang === "en"
            ? "Choose a variable and run an analysis to reveal its native-grid map."
            : "اختر متغيرًا وشغّل التحليل لعرض خريطة الشبكة الأصلية."}
        </p>
      </div>
    );
  const point = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)),
      y: Math.max(0, Math.min(1, (e.clientY - r.top) / r.height)),
    };
  };
  const finish = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!start.current) return;
    const p = point(e),
      s = start.current;
    start.current = null;
    setSelection(null);
    const [w, south, east, north] = spatial.bbox;
    const x0 = Math.min(s.x, p.x),
      x1 = Math.max(s.x, p.x),
      y0 = Math.min(s.y, p.y),
      y1 = Math.max(s.y, p.y);
    if (x1 - x0 > 0.03 && y1 - y0 > 0.03)
      onAoi({
        w: w + x0 * (east - w),
        e: w + x1 * (east - w),
        n: north - y0 * (north - south),
        s: north - y1 * (north - south),
      });
  };
  const extent=mapExtent(spatial.bbox);
  const [west,south,east,north]=extent;
  return (
    <div className="spatial-wrap geographic-map">
      <GeoBackdrop bbox={extent}/>
      <div className="map-coordinate map-coordinate-top">{spatial.bbox[3].toFixed(2)}° N</div>
      <div className="map-coordinate map-coordinate-bottom">{spatial.bbox[1].toFixed(2)}° N</div>
      <div
        className="spatial-plot"
        style={{
          aspectRatio: `${spatial.grid.lon.length} / ${spatial.grid.lat.length}`,
          left:`${(spatial.bbox[0]-west)/(east-west)*100}%`,
          top:`${(north-spatial.bbox[3])/(north-south)*100}%`,
          width:`${(spatial.bbox[2]-spatial.bbox[0])/(east-west)*100}%`,
          height:`${(spatial.bbox[3]-spatial.bbox[1])/(north-south)*100}%`,
        }}
      >
        <canvas
          ref={canvas}
          className="spatial-canvas"
          aria-label="Native-grid slope map. Drag to select an analysis rectangle."
          onPointerDown={(e) => {
            start.current = point(e);
            e.currentTarget.setPointerCapture(e.pointerId);
          }}
          onPointerMove={(e) => {
            if (!start.current) return;
            const p = point(e),
              s = start.current;
            setSelection({
              x: Math.min(s.x, p.x) * 100,
              y: Math.min(s.y, p.y) * 100,
              w: Math.abs(s.x - p.x) * 100,
              h: Math.abs(s.y - p.y) * 100,
            });
          }}
          onPointerUp={finish}
          onPointerCancel={() => {
            start.current = null;
            setSelection(null);
          }}
        />
        {selection ? (
          <div
            className="map-selection"
            style={{
              left: `${selection.x}%`,
              top: `${selection.y}%`,
              width: `${selection.w}%`,
              height: `${selection.h}%`,
            }}
          />
        ) : null}
      </div>
      <div className="map-grid-note">
        <span>{lang === "en" ? "NATIVE GRID" : "الشبكة الأصلية"}</span>
        <strong>{spatial.grid.lon.length} × {spatial.grid.lat.length}</strong>
        <small>{lang === "en" ? "Cells shown at source resolution" : "الخلايا بدقة المصدر"}</small>
      </div>
      <div className="map-corner">
        <span className="map-attribution">NASA Blue Marble · Natural Earth boundaries</span>
        {lang === "en" ? "DRAG TO SELECT AREA" : "اسحب لاختيار منطقة"}
      </div>
    </div>
  );
}

function Explorer({ lang, onHome }: { lang: Lang; onHome: () => void }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [region, setRegion] = useState<RegionId>("nile_corridor");
  const [variable, setVariable] = useState<VariableId>("air_temperature");
  const [start, setStart] = useState("2001-01");
  const [end, setEnd] = useState("2024-12");
  const [aoi, setAoi] = useState<BBox | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"evidence" | "spin" | "sources">("evidence");
  const [selectedWindow, setSelectedWindow] = useState<number | null>(null);
  const [comparison, setComparison] = useState<Awaited<
    ReturnType<typeof compare>
  > | null>(null);
  const [running, setRunning] = useState(false);
  useEffect(() => {
    let active = true;
    getCatalog()
      .then((c) => {
        if (active) setCatalog(c);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    const jobId = analysis?.result.job_id;
    if (!jobId) return;
    let active = true;
    getExplanation(jobId, lang)
      .then((explanation) => {
        if (active)
          setAnalysis((current) =>
            current?.result.job_id === jobId
              ? { ...current, explanation }
              : current,
          );
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [lang, analysis?.result.job_id]);
  const entry: CatalogEntry | undefined = catalog?.entries.find(
    (e) => e.region_id === region && e.variable_id === variable,
  );
  const result = analysis?.result.variables.find(
    (v) => v.variable_id === variable,
  );
  const months = Array.from(
    { length: 24 * 12 },
    (_, i) =>
      `${2001 + Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, "0")}`,
  );
  async function run() {
    setRunning(true);
    setStatus(lang === "en" ? "Submitting analysis…" : "جاري إرسال التحليل…");
    setError("");
    setAnalysis(null);
    setComparison(null);
    setSelectedWindow(null);
    try {
      const next = await analyse(
        region,
        variable,
        start,
        end,
        lang,
        aoi,
        setStatus,
      );
      setAnalysis(next);
      setTab("evidence");
      setStatus("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus("");
    } finally {
      setRunning(false);
    }
  }
  async function downloadReceipt() {
    if (!analysis?.result.receipt_id || analysis.offline) return;
    try {
      const data = await getReceipt(analysis.result.receipt_id);
      const blob = new Blob([JSON.stringify(data.payload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `trend-detective-receipt-${analysis.result.receipt_id}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }
  async function runCompare() {
    setError("");
    try {
      setComparison(await compare(variable, start, end));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }
  const windows = result?.period_sensitivity?.windows || [];
  return (
    <main className="workspace">
      <aside className="workspace-sidebar">
        <div className="sidebar-brand">
          <span className="logo-mark">✦</span>
          <div>
            ASTRA
            <br />
            VERD
          </div>
        </div>
        <div className="sidebar-nav">
          <button className="selected">
            <MapPinned size={18} />
            {lang === "en" ? "Explorer" : "المستكشف"}
          </button>
          <button onClick={onHome}>
            <BookOpen size={18} />
            {lang === "en" ? "The story" : "القصة"}
          </button>
        </div>
        <div className="sidebar-bottom">
          <Satellite size={16} />
          <span>{isOffline() ? "OFFLINE SNAPSHOT" : "NASA EARTH DATA"}</span>
          <small>{catalog?.method_revision || "—"}</small>
        </div>
      </aside>
      <div className="workspace-main">
        <div className="workspace-top">
          <div>
            <div className="breadcrumb">
              ASTRAVERD <span>/</span>{" "}
              {lang === "en" ? "EXPLORER" : "المستكشف"}
            </div>
            <h1>
              {lang === "en" ? "Earth data explorer" : "مستكشف بيانات الأرض"}
            </h1>
            <p>
              {lang === "en"
                ? "Build a claim. Change the frame. Inspect the evidence."
                : "كوّن استنتاجًا. غيّر الإطار. وافحص الدليل."}
            </p>
          </div>
          <div className="top-tools">
            <span className={"availability " + (isOffline() ? "offline" : "")}>
              {isOffline()
                ? lang === "en"
                  ? "Precomputed offline"
                  : "محسوب مسبقًا دون اتصال"
                : lang === "en"
                  ? "Live analysis"
                  : "تحليل مباشر"}
            </span>
            <button onClick={onHome} title="Back to landing">
              <ArrowUpRight size={17} /> {lang === "en" ? "Story" : "القصة"}
            </button>
          </div>
        </div>
        <div className="mission-strip" aria-label={lang === "en" ? "Investigation workflow" : "خطوات التحقيق"}>
          <div className="mission-symbol"><Leaf size={24} /></div>
          <div className="mission-intro">
            <span>{lang === "en" ? "INVESTIGATION / 001" : "التحقيق / 001"}</span>
            <strong>{lang === "en" ? "One planet. Many possible stories." : "كوكب واحد. روايات متعددة."}</strong>
          </div>
          <div className="mission-steps">
            {(["configure", "observe", "signal", "verify"] as const).map((target, i) => (
              <a href="#explore" key={target} onClick={(event) => {
                event.preventDefault();
                document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
              }}>
                <b>0{i + 1}</b> {lang === "en" ? ["FRAME", "OBSERVE", "QUESTION", "VERIFY"][i] : ["الإطار", "الرصد", "التساؤل", "التحقق"][i]}
              </a>
            ))}
          </div>
        </div>
        <div className="workspace-grid">
          <aside id="configure" className="control-rail">
            <div className="rail-heading">
              <span>
                01 / {lang === "en" ? "BUILD YOUR ANALYSIS" : "جهّز تحليلك"}
              </span>
              <p>
                {lang === "en"
                  ? "Make the choices behind the result visible."
                  : "اجعل اختيارات التحليل واضحة."}
              </p>
            </div>
            <div className="control-group">
              <label>{lang === "en" ? "Study area" : "منطقة الدراسة"}</label>
              <div className="region-options">
                {REGIONS.map((r) => (
                  <button
                    key={r.id}
                    className={region === r.id ? "active" : ""}
                    onClick={() => {
                      setRegion(r.id);
                      setAoi(null);
                      setAnalysis(null);
                    }}
                  >
                    <MapPinned size={16} />
                    <span>
                      {r[lang]}
                      <small>{r.caption}</small>
                    </span>
                    {region === r.id ? <Check size={15} /> : null}
                  </button>
                ))}
              </div>
            </div>
            <div className="control-group">
              <label>{lang === "en" ? "Earth variable" : "متغير الأرض"}</label>
              <div className="variable-options">
                {VARIABLES.map((v) => {
                  const Icon = v.icon;
                  const available = catalog?.entries.find(
                    (e) => e.region_id === region && e.variable_id === v.id,
                  )?.app_available;
                  return (
                    <button
                      key={v.id}
                      disabled={catalog != null && !available}
                      className={variable === v.id ? "active" : ""}
                      onClick={() => {
                        setVariable(v.id);
                        setAnalysis(null);
                      }}
                    >
                      <Icon size={17} color={v.color} />
                      <span>{v[lang]}</span>
                    </button>
                  );
                })}
              </div>
              {entry ? (
                <p className="source-caption">
                  {entry.product_id} v{entry.version} ·{" "}
                  {entry.source_kind.replaceAll("_", " ")}
                </p>
              ) : null}
            </div>
            <div className="control-group">
              <label>{lang === "en" ? "Time window" : "الفترة الزمنية"}</label>
              <div className="date-row">
                <div>
                  <small>{lang === "en" ? "FROM" : "من"}</small>
                  <select
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                  >
                    {months
                      .filter((_, i) => i % 12 === 0)
                      .map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                  </select>
                </div>
                <ArrowRight size={16} />
                <div>
                  <small>{lang === "en" ? "TO" : "إلى"}</small>
                  <select value={end} onChange={(e) => setEnd(e.target.value)}>
                    {months
                      .filter((_, i) => i % 12 === 11)
                      .map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                  </select>
                </div>
              </div>
              <p className="control-hint">
                {lang === "en"
                  ? "At least 60 months and 80% valid values."
                  : "الحد الأدنى 60 شهرًا و80% قيم صالحة."}
              </p>
            </div>
            {aoi ? (
              <div className="aoi-chip">
                <MapPinned size={16} />
                <span>
                  {lang === "en" ? "Custom area selected" : "منطقة مخصصة محددة"}
                </span>
                <button
                  onClick={() => setAoi(null)}
                  aria-label="Clear custom area"
                >
                  <X size={15} />
                </button>
              </div>
            ) : null}
            <button
              className="run-button"
              onClick={run}
              disabled={running || !catalog || start >= end}
            >
              {running
                ? lang === "en"
                  ? "Analysing…"
                  : "جاري التحليل…"
                : lang === "en"
                  ? "Analyse this area"
                  : "حلّل هذه المنطقة"}{" "}
              <ArrowRight size={18} />
            </button>
            <p className="control-hint">
              {lang === "en"
                ? "Numbers are produced by the verified server method."
                : "الأرقام ناتجة عن طريقة التحليل المعتمدة على الخادم."}
            </p>
          </aside>
          <div id="observe" className="analysis-center">
            <div className="panel-title">
              <div>
                <span className="eyebrow">
                  02 / {lang === "en" ? "SPATIAL SIGNAL" : "الإشارة المكانية"}
                </span>
                <h2>{regionLabel(region, lang)}</h2>
                <p>
                  {variableLabel(variable, lang)} <span>·</span>{" "}
                  {lang === "en"
                    ? "Reference layer: full period 2001–2024"
                    : "طبقة مرجعية: الفترة الكاملة 2001–2024"}
                </p>
              </div>
              <div className="panel-badges">
                <span>
                  {entry?.native_grid
                    ? Object.values(entry.native_grid).join(" × ")
                    : "NATIVE GRID"}
                </span>
                {analysis?.spatial ? (
                  <span>
                    FDR q={analysis.spatial.fdr.q} ·{" "}
                    {analysis.spatial.fdr.m_tested} cells
                  </span>
                ) : null}
              </div>
            </div>
            <div className="map-panel">
              <SpatialMap
                spatial={analysis?.spatial || null}
                lang={lang}
                onAoi={setAoi}
              />
            </div>
            <div className="map-legend">
              <span>
                <i className="legend-cool" />
                {lang === "en" ? "Negative slope" : "ميل سالب"}
              </span>
              <span>
                <i className="legend-warm" />
                {lang === "en" ? "Positive slope" : "ميل موجب"}
              </span>
              <span>
                <i className="legend-mark" />
                {lang === "en" ? "FDR significant cell" : "خلية دالة بعد FDR"}
              </span>
              <span>
                <i className="legend-none" />
                {lang === "en" ? "No data" : "لا توجد بيانات"}
              </span>
            </div>
            <div id="signal" className="series-panel">
              <div className="series-heading">
                <div>
                  <span className="eyebrow">
                    03 / {lang === "en" ? "TIME SERIES" : "السلسلة الزمنية"}
                  </span>
                  <h2>
                    {lang === "en" ? "Monthly signal" : "الإشارة الشهرية"}
                  </h2>
                </div>
                {analysis?.series ? (
                  <span>
                    {lang === "en" ? "Valid coverage" : "التغطية الصالحة"}{" "}
                    {fmt(analysis.series.valid_fraction * 100, 1)}%
                  </span>
                ) : null}
              </div>
              <SeriesChart series={analysis?.series || null} lang={lang} />
              <div className="chart-key">
                <span>
                  <i className="key-month" />
                  {lang === "en" ? "Monthly observations" : "القيم الشهرية"}
                </span>
                <span>
                  <i className="key-trend" />
                  {lang === "en" ? "Server trend line" : "خط اتجاه الخادم"}
                </span>
              </div>
            </div>
          </div>
          <aside id="verify" className="evidence-rail">
            <div className="evidence-heading">
              <span className="eyebrow">
                04 / {lang === "en" ? "THE EVIDENCE" : "الدليل"}
              </span>
              <h2>{lang === "en" ? "Evidence lab" : "معمل الدليل"}</h2>
              <p>
                {lang === "en"
                  ? "Every conclusion carries its method and limits."
                  : "كل استنتاج مرتبط بطريقته وقيوده."}
              </p>
            </div>
            <div className="evidence-tabs" role="tablist">
              {(["evidence", "spin", "sources"] as const).map((t) => (
                <button
                  role="tab"
                  aria-selected={tab === t}
                  className={tab === t ? "active" : ""}
                  key={t}
                  onClick={() => setTab(t)}
                >
                  {t === "evidence"
                    ? lang === "en"
                      ? "Result"
                      : "النتيجة"
                    : t === "spin"
                      ? "Spin It"
                      : lang === "en"
                        ? "Sources"
                        : "المصادر"}
                </button>
              ))}
            </div>
            {!analysis ? (
              <div className="empty-evidence">
                <Search size={28} />
                <h3>
                  {lang === "en" ? "No analysis yet" : "لا يوجد تحليل بعد"}
                </h3>
                <p>
                  {lang === "en"
                    ? "Select a place, variable and period, then run the analysis."
                    : "اختر المكان والمتغير والفترة، ثم شغّل التحليل."}
                </p>
              </div>
            ) : tab === "evidence" ? (
              <div className="result-body">
                <div className="result-state">
                  <span
                    className={
                      result?.state === "succeeded" ? "state-ok" : "state-warn"
                    }
                  >
                    {result?.state === "succeeded"
                      ? lang === "en"
                        ? "ANALYSIS COMPLETE"
                        : "اكتمل التحليل"
                      : lang === "en"
                        ? "INSUFFICIENT DATA"
                        : "بيانات غير كافية"}
                  </span>
                </div>
                <h3>{result?.label || variableLabel(variable, lang)}</h3>
                <p className="result-sub">
                  {regionLabel(region, lang)} · {start} — {end}
                </p>
                <div className="big-number">
                  <span>{fmt(result?.trend?.slope_per_year, 4)}</span>
                  <small>{result?.trend?.slope_units || ""}</small>
                </div>
                <div className="metric-row">
                  <span>
                    {lang === "en" ? "95% slope interval" : "مجال ميل 95%"}
                  </span>
                  <strong>
                    {fmt(result?.trend?.ci_low, 4)} to{" "}
                    {fmt(result?.trend?.ci_high, 4)}
                  </strong>
                </div>
                <div className="metric-row">
                  <span>p-value</span>
                  <strong>{fmt(result?.trend?.p_value, 4)}</strong>
                </div>
                <div className="metric-row">
                  <span>
                    {lang === "en" ? "Valid coverage" : "التغطية الصالحة"}
                  </span>
                  <strong>
                    {fmt((result?.counts.valid_fraction || 0) * 100, 1)}%
                  </strong>
                </div>
                <div className="metric-row">
                  <span>{lang === "en" ? "Product" : "المنتج"}</span>
                  <strong>
                    {result?.product_id} v{result?.version}
                  </strong>
                </div>
                <div className="spatial-note">{lang === 'en' ? 'Map context: the spatial layer shows the full 2001–2024 reference period. A different analysis window can produce a different trend.' : 'الخريطة تعرض الفترة المرجعية الكاملة 2001–2024. قد تختلف نتيجة الاتجاه عند تغيير فترة التحليل.'}</div>
                {analysis.explanation ? (
                  <div className="explanation">
                    <Sparkles size={17} />
                    <p>{analysis.explanation.explanation.answer}</p>
                  </div>
                ) : null}
                <button
                  className="receipt-button"
                  onClick={downloadReceipt}
                  disabled={!analysis.result.receipt_id || analysis.offline}
                >
                  <Download size={16} />
                  {analysis.offline
                    ? lang === "en"
                      ? "Receipt needs live server"
                      : "الإيصال يحتاج الخادم"
                    : lang === "en"
                      ? "Download receipt"
                      : "حمّل الإيصال"}
                </button>
              </div>
            ) : tab === "spin" ? (
              <div className="spin-body">
                <h3>
                  {lang === "en"
                    ? "How much does the window matter?"
                    : "ما أثر اختيار الفترة؟"}
                </h3>
                <p>
                  {lang === "en"
                    ? "These windows were computed by the server. Select one to inspect its reported slope."
                    : "هذه الفترات محسوبة على الخادم. اختر واحدة لفحص الميل الناتج."}
                </p>
                {windows.length ? (
                  <>
                    <div className="window-list">
                      {windows.map((w, i) => (
                        <button
                          className={selectedWindow === i ? "active" : ""}
                          key={`${w.start}-${w.end}`}
                          onClick={() => setSelectedWindow(i)}
                        >
                          <span>
                            {w.start.slice(0, 4)}–{w.end.slice(0, 4)}
                          </span>
                          <strong>{fmt(w.slope, 4)}</strong>
                        </button>
                      ))}
                    </div>
                    {selectedWindow != null ? (
                      <div className="selected-window">
                        <span>
                          {lang === "en"
                            ? "SELECTED WINDOW"
                            : "الفترة المختارة"}
                        </span>
                        <strong>
                          {fmt(windows[selectedWindow].slope, 4)}{" "}
                          {result?.trend?.slope_units}
                        </strong>
                        <small>
                          p = {fmt(windows[selectedWindow].p_value, 4)}
                        </small>
                      </div>
                    ) : null}
                    <p className="control-hint">
                      {lang === "en"
                        ? "Sign agreement is descriptive, not calibrated confidence."
                        : "توافق الإشارة وصفي، وليس ثقة معايرة."}
                    </p>
                  </>
                ) : (
                  <div className="empty-evidence">
                    {lang === "en"
                      ? "No sensitivity windows returned for this result."
                      : "لم تُرجع فترات حساسية لهذه النتيجة."}
                  </div>
                )}
                <button className="compare-button" onClick={runCompare}>
                  {lang === "en" ? "Compare all regions" : "قارن كل المناطق"}{" "}
                  <ArrowRight size={16} />
                </button>
                {comparison ? (
                  <div className="comparison">
                    {comparison.map((row) => (
                      <div key={row.region_id}>
                        <span>{regionLabel(row.region_id, lang)}</span>
                        <strong>{fmt(row.slope_per_year, 4)}</strong>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="sources-body">
                <h3>
                  {lang === "en"
                    ? "Provenance & limitations"
                    : "المصدر والقيود"}
                </h3>
                <p>
                  {lang === "en"
                    ? "Dataset and method versions are tied to the result."
                    : "إصدارات البيانات والطريقة مرتبطة بالنتيجة."}
                </p>
                <div className="source-meta">
                  <span>DATA REVISION</span>
                  <code>{analysis.result.data_revision.slice(0, 14)}…</code>
                  <span>METHOD</span>
                  <code>{analysis.result.method_revision}</code>
                </div>
                <h4>{lang === "en" ? "Limitations" : "القيود"}</h4>
                <ul>
                  {[
                    ...(entry?.limitations || []),
                    ...(result?.warnings || []),
                  ].map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
                {analysis.explanation?.citations?.length ? (
                  <>
                    <h4>{lang === "en" ? "References" : "المراجع"}</h4>
                    {analysis.explanation.citations.map((c, i) => (
                      <a
                        className="citation"
                        href={c.source_url}
                        target="_blank"
                        rel="noreferrer"
                        key={i}
                      >
                        {c.title}
                        <ExternalLink size={13} />
                      </a>
                    ))}
                  </>
                ) : null}
              </div>
            )}
            {status ? (
              <div className="status-line" role="status">
                <Clock3 size={16} />
                {status}
              </div>
            ) : null}
            {error ? (
              <div className="error-line" role="alert">
                {error}
                <button onClick={() => setError("")} aria-label="Dismiss error">
                  <X size={14} />
                </button>
              </div>
            ) : null}
          </aside>
        </div>
      </div>
    </main>
  );
}

function App() {
  const [lang, setLang] = useState<Lang>(
    new URLSearchParams(location.search).get("lang") === "ar" ? "ar" : "en",
  );
  const [page, setPage] = useState(
    location.hash === "#explore" ? "explore" : "home",
  );
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  }, [lang]);
  useEffect(() => {
    location.hash = page === "explore" ? "explore" : "";
  }, [page]);
  return (
    <>
      <SceneHeader lang={lang} setLang={setLang} setPage={setPage} />
      {page === "home" ? (
        <Landing
          lang={lang}
          onLaunch={() => {
            setPage("explore");
            scrollTo({ top: 0 });
          }}
        />
      ) : (
        <Explorer
          lang={lang}
          onHome={() => {
            setPage("home");
            scrollTo({ top: 0 });
          }}
        />
      )}
    </>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

