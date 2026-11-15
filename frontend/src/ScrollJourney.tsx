import { useEffect, useRef } from "react";

type Pose = "idle" | "plant" | "umbrella" | "wave";
const files: Record<Pose, string> = {
  idle: "astro-idle.png",
  plant: "astro-plant-atlas.png",
  umbrella: "astro-umbrella-atlas.png",
  wave: "astro-wave-atlas.png",
};

export function ScrollJourney() {
  const root = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const node = root.current;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const landing = node?.parentElement;
    if (!node || !landing || !canvas || !ctx) return;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)");
    const sources = Object.fromEntries(
      Object.entries(files).map(([pose, file]) => [pose, `${import.meta.env.BASE_URL}${file}`]),
    ) as Record<Pose, string>;
    const images = {} as Record<Pose, HTMLImageElement>;
    (Object.keys(sources) as Pose[]).forEach((poseName) => {
      const image = new Image();
      image.src = sources[poseName];
      images[poseName] = image;
      image.decode().then(() => { if (!frame && visible) frame = requestAnimationFrame(tick); }).catch(() => {});
    });
    let pose: Pose = "idle";
    let poseStart = performance.now();
    let frame = 0;
    let last = 0;
    let x = 0, y = 0, targetX = 0, targetY = 0;
    let anchors: Array<{ x: number; y: number; trigger: number }> = [];
    let visible = false;

    const resizeCanvas = () => {
      const dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = Math.round(node.offsetWidth * dpr);
      canvas.height = Math.round(node.offsetHeight * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.imageSmoothingEnabled = true;
    };

    const measure = () => {
      const cards = [".region-visual", ".window-visual", ".receipt-visual"]
        .map((selector) => landing.querySelector<HTMLElement>(selector));
      const landingTop = landing.getBoundingClientRect().top + scrollY;
      const actorWidth = node.offsetWidth;
      const actorHeight = node.offsetHeight;
      resizeCanvas();
      anchors = cards.filter((card): card is HTMLElement => !!card).map((card) => {
        // Layout offsets exclude scroll-driven transforms on the scene cards.
        let localLeft = 0, localTop = 0;
        let parent: HTMLElement | null = card;
        while (parent && parent !== landing) {
          localLeft += parent.offsetLeft;
          localTop += parent.offsetTop;
          parent = parent.offsetParent as HTMLElement | null;
        }
        return {
          x: innerWidth <= 760 ? localLeft + 16 : localLeft - actorWidth * .85,
          y: innerWidth <= 760 ? localTop + card.offsetHeight + 10 : localTop + card.offsetHeight - actorHeight + 190,
          trigger: landingTop + localTop - innerHeight * .58,
        };
      });
      sample();
    };
    const changePose = (next: Pose) => {
      if (next === pose) return;
      pose = next;
      poseStart = performance.now();
      node.dataset.pose = next;
    };
    const paint = (now: number) => {
      const chosen = images[pose]?.complete && images[pose].naturalWidth ? images[pose] : images.idle;
      if (!chosen?.naturalWidth) return;
      const elapsed = Math.max(0, now - poseStart);
      let index = 0;
      if (pose === "plant") index = Math.min(3, Math.floor(elapsed / 330));
      if (pose === "umbrella") index = Math.min(3, Math.floor(elapsed / 240));
      if (pose === "wave") index = elapsed < 750 ? Math.min(3, Math.floor(elapsed / 250)) : 2 + Math.floor((elapsed - 750) / 420) % 2;
      if (reduce.matches && pose !== "idle") index = 3;
      const cells = chosen === images.idle ? 1 : 4;
      const width = chosen.naturalWidth / cells;
      ctx.clearRect(0, 0, node.offsetWidth, node.offsetHeight);
      ctx.drawImage(chosen, index * width, 0, width, chosen.naturalHeight, 0, 0, node.offsetWidth, node.offsetHeight);
      node.dataset.frame = String(index);
    };
    const tick = (now: number) => {
      frame = 0;
      if (document.hidden || !visible) return;
      const dt = last ? Math.min(64, now - last) : 16;
      last = now;
      const factor = reduce.matches ? 1 : 1 - Math.exp(-dt / 115);
      x += (targetX - x) * factor;
      y += (targetY - y) * factor;
      node.style.transform = `translate3d(${x.toFixed(1)}px,${y.toFixed(1)}px,0)`;
      paint(now);
      if (!reduce.matches || Math.abs(targetX - x) + Math.abs(targetY - y) > .6) frame = requestAnimationFrame(tick);
    };
    const sample = () => {
      if (anchors.length !== 3) return;
      const now = scrollY;
      visible = now >= anchors[0].trigger - innerHeight * .45 && now <= anchors[2].trigger + innerHeight * .85;
      node.style.opacity = visible ? "1" : "0";
      if (!visible) return;
      let index = now < anchors[1].trigger ? 0 : now < anchors[2].trigger ? 1 : 2;
      const next = anchors[Math.min(index + 1, 2)];
      const current = anchors[index];
      const raw = index === 2 ? 0 : (now - current.trigger) / Math.max(1, next.trigger - current.trigger);
      const fraction = Math.max(0, Math.min(1, (raw - .72) / .28));
      targetX = current.x + (next.x - current.x) * fraction;
      targetY = current.y + (next.y - current.y) * fraction;
      if (!last) { x = targetX; y = targetY; }
      const nextPose: Pose = index === 0
        ? now < anchors[0].trigger + innerHeight * .2 ? "idle" : "plant"
        : index === 1 ? "umbrella" : "wave";
      changePose(nextPose);
      if (!frame) frame = requestAnimationFrame(tick);
    };
    const visibility = () => {
      if (document.hidden) { cancelAnimationFrame(frame); frame = 0; last = 0; }
      else { sample(); }
    };
    measure();
    addEventListener("scroll", sample, { passive: true });
    addEventListener("resize", measure, { passive: true });
    document.addEventListener("visibilitychange", visibility);
    return () => {
      cancelAnimationFrame(frame);
      removeEventListener("scroll", sample);
      removeEventListener("resize", measure);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);
  return (
    <div ref={root} className="scroll-journey" data-pose="idle" aria-hidden="true">
      <div className="journey-shuttle">
        <svg viewBox="0 0 110 100"><path d="M30 76L41 27Q53 8 65 27L79 76Z" fill="#d7dcd9" stroke="#8ea8b0" strokeWidth="3"/><path d="M43 51Q53 24 64 51Z" fill="#235a77" stroke="#90d8e4" strokeWidth="2"/><path d="M30 70L12 91L39 79M79 70l19 21-27-12" fill="#dc8250"/><circle cx="54" cy="68" r="5" fill="#b4f174"/></svg>
      </div>
      <div className="journey-rain" />
      <div className="journey-earth" />
      <canvas ref={canvasRef} className="journey-canvas" />
    </div>
  );
}
