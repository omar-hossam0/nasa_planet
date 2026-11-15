const { chromium } = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const context = await browser.newContext({viewport:{width:390,height:844},deviceScaleFactor:1,recordVideo:{dir:'../journey-video',size:{width:390,height:844}}});
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:4173/');
  await page.locator('.section-actor').first().waitFor({state:'attached',timeout:15000});
  await page.addStyleTag({content:'html { scroll-behavior:auto !important }'});
  for (const scene of ['plant','umbrella','wave']) {
    const top=await page.locator(`[data-scene="${scene}"]`).evaluate(el=>el.getBoundingClientRect().top+scrollY);
    for(let step=0;step<=40;step++){
      await page.evaluate(y=>scrollTo({top:y,behavior:'instant'}),top-700+step*11);
      await page.waitForTimeout(35);
    }
    await page.waitForTimeout(700);
  }
  const video=page.video();
  await context.close();
  const output=path.resolve('../journey-mobile-demo.webm');
  fs.copyFileSync(await video.path(),output);
  await browser.close();
  console.log(output);
})().catch(e=>{console.error(e);process.exit(1)});
