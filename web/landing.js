'use strict';

// The interface copy is real DOM text; only the decorative explorer is drawn.
const languageButton = document.getElementById('language');
let lang = new URLSearchParams(location.search).get('lang') === 'ar' ? 'ar' : 'en';
function setLanguage(next) {
  lang = next;
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
  for (const node of document.querySelectorAll('[data-en][data-ar]')) {
    node.innerHTML = node.dataset[lang];
  }
  languageButton.textContent = lang === 'ar' ? 'EN' : 'عربي';
  languageButton.setAttribute('aria-label', lang === 'ar' ? 'Switch to English' : 'التبديل إلى العربية');
  for (const a of document.querySelectorAll('a[href^="index.html"]')) {
    a.href = lang === 'ar' ? 'index.html?lang=ar' : 'index.html?lang=en';
  }
}
languageButton.addEventListener('click', () => setLanguage(lang === 'en' ? 'ar' : 'en'));
setLanguage(lang);

// Scroll determines journey position; elapsed time determines gait. Stopping
// midway leaves the character in place while the action loop continues.
const canvas = document.getElementById('companion');
const ctx = canvas.getContext('2d', { alpha: true });
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const frames = ['assets/astrobotanist-walk-a.png', 'assets/astrobotanist-walk-b.png'].map((url) => {
  const img = new Image();
  img.decoding = 'async';
  img.src = url;
  return img;
});
let cssWidth = 0;
let cssHeight = 0;
let target = 0;
let position = 0;
let lastTime = 0;
let raf = 0;
let visible = true;

function resize() {
  cssWidth = innerWidth;
  cssHeight = innerHeight;
  const dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.imageSmoothingEnabled = false;
}
function sampleScroll() {
  const hero = document.querySelector('.hero');
  const method = document.getElementById('method');
  const start = hero.offsetTop;
  const end = method.offsetTop + Math.min(method.offsetHeight * .35, 280);
  target = Math.max(0, Math.min(1, (scrollY - start) / Math.max(1, end - start)));
}
function paint(now) {
  raf = 0;
  if (!visible || reducedMotion.matches) return;
  const dt = lastTime ? Math.min(100, now - lastTime) : 16;
  lastTime = now;
  position += (target - position) * (1 - Math.exp(-dt / 160));
  ctx.clearRect(0, 0, cssWidth, cssHeight);

  // Leave the serious data interface unobstructed after the guided intro.
  const opacity = Math.max(0, Math.min(1, (0.84 - position) / .15));
  const frame = frames[Math.floor(now / 340) % 2];
  if (frame.complete && frame.naturalWidth && opacity > 0) {
    const small = cssWidth < 650;
    const height = small ? Math.min(145, cssHeight * .21) : Math.min(190, cssHeight * .25);
    const width = height * frame.naturalWidth / frame.naturalHeight;
    const x0 = cssWidth * .5 - width / 2;
    const x1 = (lang === 'ar' ? cssWidth * .13 : cssWidth * .87) - width / 2;
    const travel = Math.min(1, position / .55);
    const x = x0 + (x1 - x0) * travel;
    const y = cssHeight - height - (small ? 54 : 44) + Math.sin(now / 340) * 2;
    ctx.globalAlpha = opacity;
    ctx.drawImage(frame, x, y, width, height);
    ctx.globalAlpha = 1;
  }
  raf = requestAnimationFrame(paint);
}
function startAnimation() {
  if (!raf && visible && !reducedMotion.matches) raf = requestAnimationFrame(paint);
}
document.addEventListener('visibilitychange', () => {
  visible = !document.hidden;
  lastTime = 0;
  if (visible) startAnimation();
});
reducedMotion.addEventListener('change', () => {
  ctx.clearRect(0, 0, cssWidth, cssHeight);
  lastTime = 0;
  startAnimation();
});
addEventListener('resize', () => { resize(); sampleScroll(); }, { passive: true });
addEventListener('scroll', sampleScroll, { passive: true });
resize();
sampleScroll();
startAnimation();
