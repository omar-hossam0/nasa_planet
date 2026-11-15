import { RagChat } from './RagChat';
import { AnalysisInsights, InferenceNotice } from './AnalysisInsights';
import { RegionMap } from './RegionMap';
import React, { useEffect, useRef, useState } from "react";
import {ReferenceActors} from './ReferenceActors';
import { GeoBackdrop } from "./GeoBackdrop";
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
  computeSensitivity,
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
  type VariableId,
} from "./api";
import "./style.css";
import "./product-theme.css";
import "./reference-layout.css";

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
  const pathFor = (points: (number | null)[]) => points.map((value, index) => {
    if (value == null || !Number.isFinite(value)) return '';
    const previous = points[index - 1];
    return `${index === 0 || previous == null || !Number.isFinite(previous) ? 'M' : 'L'}${xy(value, index)}`;
  }).join(' ');
  return (
    <svg
      className="series-chart"
      viewBox="0 0 920 290"
      role="img"
      aria-label="Monthly values and server-computed trend line"
    >
      <path d="M48 55H878 M48 150H878 M48 245H878" className="axis-grid" />
      <path d={pathFor(series.values)} className="monthly-line" />
      <path d={pathFor(series.trend_line)} className="trend-line" />
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

function Explorer({ lang, onHome }: { lang: Lang; onHome: () => void }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [region, setRegion] = useState<RegionId>("");
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
  const [spinLoading, setSpinLoading] = useState(false);
  const [spinYears, setSpinYears] = useState(10);
  const requestVersion = useRef(0);
  useEffect(() => {
    requestVersion.current += 1;
    setAnalysis(null);
    setComparison(null);
    setStatus('');
    setError('');
    setRunning(false);
    setSpinLoading(false);
    return () => { requestVersion.current += 1; };
  }, [region, variable, start, end, aoi]);
  useEffect(() => {
    let active = true;
    getCatalog()
      .then((c) => {
        if (active) {
          setCatalog(c);
          setRegion(current => c.entries.some(e => e.region_id === current) ? current : c.entries[0]?.region_id || '');
        }
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
  const entry: CatalogEntry | undefined = catalog?.entries?.find(
    (e) => e.region_id === region && e.variable_id === variable,
  );
  const regions = [...new Map((catalog?.entries || []).map(e => [e.region_id, {
    id: e.region_id, en: e.region_label || e.region_id.replaceAll('_', ' '),
    ar: e.region_label_ar || e.region_label || e.region_id.replaceAll('_', ' '), caption: '',
  }])).values()];
  const regionLabel = (id: string, language: Lang) => regions.find(r => r.id === id)?.[language] || id;
  const result = analysis?.result.variables.find(
    (v) => v.variable_id === variable,
  );
  const months = Array.from(
    { length: 24 * 12 },
    (_, i) =>
      `${2001 + Math.floor(i / 12)}-${String((i % 12) + 1).padStart(2, "0")}`,
  );
  async function run() {
    const version = ++requestVersion.current;
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
        value => { if (version === requestVersion.current) setStatus(value); },
      );
      if (version !== requestVersion.current) return;
      setAnalysis(next);
      setTab("evidence");
      setStatus("");
    } catch (e) {
      if (version !== requestVersion.current) return;
      setError(e instanceof Error ? e.message : String(e));
      setStatus("");
    } finally {
      if (version === requestVersion.current) setRunning(false);
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
    const version = requestVersion.current;
    setError("");
    try {
      const response = await compare(variable, start, end);
      if (version === requestVersion.current) setComparison(response);
    } catch (e) {
      if (version === requestVersion.current) setError(e instanceof Error ? e.message : String(e));
    }
  }
  const windows = result?.period_sensitivity?.windows || [];
  async function loadSensitivity() {
    if (!analysis?.result.result_id) return;
    const version = requestVersion.current;
    setSpinLoading(true); setError('');
    try {
      const values = await computeSensitivity(analysis.result.result_id, spinYears);
      if (version !== requestVersion.current) return;
      setSelectedWindow(null);
      setAnalysis(current => current ? { ...current, result: { ...current.result, variables: current.result.variables.map(v =>
        v.variable_id === variable ? { ...v, period_sensitivity: { windows: values } } : v) } } : current);
    } catch (failure) {
      if (version === requestVersion.current) setError(failure instanceof Error ? failure.message : String(failure));
    } finally { if (version === requestVersion.current) setSpinLoading(false); }
  }
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
          <span>{isOffline() ? "OFFLINE SNAPSHOT" : entry?.source_kind === 'synthetic_demo' ? 'SYNTHETIC DEMO' : 'NASA EARTH DATA'}</span>
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
        {entry?.source_kind === 'synthetic_demo' && <div className="data-mode-notice" role="status">
          {lang === 'en' ? 'Synthetic demonstration data. Not a NASA scientific result.' : 'بيانات تجريبية مصطنعة. ليست نتائج علمية من ناسا.'}
        </div>}
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
                {regions.map((r) => (
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
                  const available = catalog?.entries?.find(
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
                  onClick={() => { setAoi(null); setAnalysis(null); }}
                  aria-label="Clear custom area"
                >
                  <X size={15} />
                </button>
              </div>
            ) : null}
            <button
              className="run-button"
              onClick={run}
              disabled={running || !entry?.app_available || start >= end}
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
                ? (entry?.source_kind === 'synthetic_demo' ? 'Synthetic demo values; real science is not connected.' : 'Check method status and provenance for server values.')
                : (entry?.source_kind === 'synthetic_demo' ? 'قيم تجريبية؛ التحليل العلمي الحقيقي غير متصل.' : 'راجع حالة الطريقة ومصدر القيم من الخادم.')}
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
                    {analysis.spatial.fdr.m_tested > 0
                      ? `FDR q=${analysis.spatial.fdr.q} · ${analysis.spatial.fdr.m_tested} cells`
                      : 'Significance not computed'}
                  </span>
                ) : null}
              </div>
            </div>
            <div className="map-panel">
              <RegionMap
                entries={catalog?.entries.filter(e => e.variable_id === variable) || []}
                region={region}
                lang={lang}
                aoi={aoi}
                spatial={analysis?.spatial || null}
                onRegion={id => { setRegion(id); setAoi(null); setAnalysis(null); setComparison(null); }}
                onAoi={box => { setAoi(box); setAnalysis(null); setComparison(null); }}
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
                {lang === "en" ? "Study region boundary" : "حدود منطقة الدراسة"}
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
                    {lang === "en" ? "Valid monthly values" : "القيم الشهرية الصالحة"}{" "}
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
                {analysis?.series?.trend_line.some(value => value != null) && <span>
                  <i className="key-trend" />
                  {lang === "en" ? "Server trend line" : "خط اتجاه الخادم"}
                </span>}
              </div>
            </div>
            {analysis && <AnalysisInsights analysis={analysis} lang={lang} variableId={variable}/>}
            <RagChat lang={lang} region={region} />
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
                    {result?.trend?.ci_low == null || result?.trend?.ci_high == null
                      ? (lang === 'en' ? 'Not computed' : 'غير محسوب')
                      : `${fmt(result.trend.ci_low, 4)} to ${fmt(result.trend.ci_high, 4)}`}
                  </strong>
                </div>
                <div className="metric-row">
                  <span>p-value</span>
                  <strong>{result?.trend?.p_value == null ? (lang === 'en' ? 'Not computed' : 'غير محسوب') : fmt(result.trend.p_value, 4)}</strong>
                </div>
                {result?.trend?.p_value==null && <InferenceNotice lang={lang}/>}
                <div className="metric-row">
                  <span>
                    {lang === "en" ? "Valid monthly values" : "القيم الشهرية الصالحة"}
                  </span>
                  <strong>
                    {fmt((result?.counts.valid_fraction || 0) * 100, 1)}%
                  </strong>
                </div>
                {result?.support && <div className="metric-row"><span>{lang === 'en' ? 'QA retained cells / area' : 'الخلايا والمساحة المقبولة بالجودة'}</span>
                  <strong>{result.support.eligible_cells}/{result.support.selected_cells} · {fmt(result.support.eligible_area_fraction*100,1)}%</strong></div>}
                <div className="metric-row">
                  <span>{lang === "en" ? "Product" : "المنتج"}</span>
                  <strong>
                    {result?.product_id} v{result?.version}
                  </strong>
                </div>
                <div className="spatial-note">{lang === 'en'
                  ? (entry?.source_kind === 'synthetic_demo' ? 'Synthetic demo: these numbers are not NASA measurements. Result explanations use templates; ask documentation questions below the chart.' : 'Result explanations and documentation questions are separate. No significance is inferred from a descriptive slope.')
                  : (entry?.source_kind === 'synthetic_demo' ? 'عرض تجريبي: الأرقام ليست قياسات ناسا. شرح النتيجة من قوالب؛ اسأل عن الوثائق أسفل الرسم.' : 'شرح النتائج وأسئلة الوثائق مساران منفصلان. الميل الوصفي لا يثبت دلالة إحصائية.')}</div>
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
                {analysis.result.result_id && !analysis.offline && <div>
                  <label htmlFor="spin-years">{lang === 'en' ? 'Window length (years)' : 'طول الفترة بالسنوات'}</label>
                  <input id="spin-years" type="number" min={3} max={30} value={spinYears} disabled={spinLoading} onChange={e => setSpinYears(Number(e.target.value))} />
                  <button className="compare-button" disabled={spinLoading || !Number.isInteger(spinYears) || spinYears<3 || spinYears>30} onClick={loadSensitivity}>
                    {spinLoading ? (lang === 'en' ? 'Computing…' : 'جاري الحساب…') : (lang === 'en' ? 'Compute sensitivity windows' : 'احسب حساسية الفترات')}
                  </button></div>}
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

