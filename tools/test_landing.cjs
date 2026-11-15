const { chromium } = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const { pathToFileURL } = require('url');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
  for (const [name, width, height] of [['desktop', 1440, 900], ['mobile', 390, 844]]) {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    const errors = [];
    page.on('pageerror', err => errors.push(err.message));
    await page.goto(pathToFileURL(path.resolve('web/landing.html')).href);
    await page.waitForTimeout(600);
    await page.screenshot({ path: `../landing_${name}.png`, fullPage: true });
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw Error(`${name}: horizontal overflow`);
    if (!(await page.locator('canvas').count())) throw Error('companion missing');
    await page.getByRole('button', { name: 'التبديل إلى العربية' }).click();
    if (await page.locator('html').getAttribute('dir') !== 'rtl') throw Error('Arabic RTL failed');
    if (!(await page.locator('.primary-cta').first().getAttribute('href')).includes('lang=ar')) throw Error('Arabic explorer link failed');
    await page.getByRole('button', { name: 'Switch to English' }).click();
    if (!(await page.locator('.primary-cta').first().getAttribute('href')).includes('lang=en')) throw Error('English explorer link failed');
    await page.locator('#mission').scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    if (errors.length) throw Error(`${name}: ${errors.join('; ')}`);
    console.log(name, 'passed', 'scrollY', await page.evaluate(() => scrollY));
    await page.close();
  }
  await browser.close();
})().catch(err => { console.error(err); process.exit(1); });
