const { chromium } = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('http://127.0.0.1:4173/');
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: '../product_desktop_landing_full_v2.png', fullPage: true });
  await page.getByRole('button', { name: /Open the investigation/i }).click();
  await page.getByRole('button', { name: /Analyse this area/i }).click();
  await page.waitForSelector('.result-body');
  await page.screenshot({ path: '../product_desktop_result_v2.png', fullPage: true });
  if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw Error('desktop horizontal overflow');
  if (errors.length) throw Error(errors.join('; '));
  console.log('desktop landing, investigation and responsive width passed');
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
