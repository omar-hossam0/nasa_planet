const { chromium } = require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
(async () => {
  const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe' });
  for (const [name,width,height] of [['desktop',1440,900],['mobile',390,844]]) {
    const page = await browser.newPage({ viewport:{width,height}, deviceScaleFactor:1, acceptDownloads:true });
    const errors=[]; page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8000/');
    await page.waitForLoadState('networkidle');
    if (!page.url().includes('/product/')) throw Error('root did not open product');
    if (await page.locator('h1').innerText() !== 'READ THE EARTH.') throw Error('hero headline missing');
    await page.screenshot({path:`../product_${name}_landing.png`,fullPage:true});
    if (await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw Error(`${name} landing overflow`);
    await page.getByRole('button',{name:/Launch explorer/i}).first().click();
    await page.waitForSelector('.workspace-grid');
    await page.screenshot({path:`../product_${name}_explorer_empty.png`,fullPage:true});
    if (await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw Error(`${name} explorer overflow`);
    await page.getByRole('button',{name:/Analyse this area/i}).click();
    await page.waitForSelector('.result-body',{timeout:60000});
    const slope=await page.locator('.big-number span').innerText();
    if (slope==='—') throw Error('missing result slope');
    await page.screenshot({path:`../product_${name}_result.png`,fullPage:true});
    if(name==='desktop'){
      await page.getByRole('tab',{name:'Spin It'}).click();
      if(await page.locator('.window-list button').count() < 2) throw Error('Spin It windows missing');
      await page.locator('.window-list button').first().click();
      await page.getByRole('button',{name:/Compare all regions/i}).click();
      await page.waitForSelector('.comparison>div');
      if(await page.locator('.comparison>div').count()!==3) throw Error('region comparison incomplete');
      await page.getByRole('tab',{name:'Sources'}).click();
      if(await page.locator('.source-meta code').count()!==2) throw Error('provenance missing');
      await page.getByRole('tab',{name:'Result'}).click();
      const download=page.waitForEvent('download');
      await page.getByRole('button',{name:/Download receipt/i}).click();
      if(!(await download).suggestedFilename().endsWith('.json')) throw Error('receipt did not download');
      await page.getByRole('button',{name:'عربي'}).click();
      if(await page.locator('html').getAttribute('dir')!=='rtl') throw Error('Arabic direction missing');
      await page.waitForFunction(()=>/[\u0600-\u06ff]/.test(document.querySelector('.explanation p')?.textContent||''));
    }
    if (errors.length) throw Error(`${name} errors: ${errors.join('; ')}`);
    console.log(name,'result slope',slope,'url',page.url());
    await page.close();
  }
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
