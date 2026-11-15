const {chromium}=require('C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 for(const width of [1440,390]){
  const page=await browser.newPage({viewport:{width,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:4173/');await page.locator('.section-actor').first().waitFor({state:'attached'});await page.evaluate(()=>document.fonts.ready);
  for(const scene of ['plant','umbrella','wave']){
   const actor=page.locator(`[data-scene="${scene}"]`);
   const top=await actor.evaluate(el=>el.getBoundingClientRect().top+scrollY);
   await page.evaluate(y=>scrollTo({top:y-700,behavior:'instant'}),top);await page.waitForTimeout(400);
   const early=Number(await actor.getAttribute('data-progress'));
   await page.evaluate(y=>scrollTo({top:y-290,behavior:'instant'}),top);await page.waitForTimeout(600);
   const late=Number(await actor.getAttribute('data-progress'));
   const after=await actor.evaluate(el=>el.getBoundingClientRect().top+scrollY);
   if(late<=early||Math.abs(after-top)>2)throw Error(`Scene progress/anchor failed: ${scene} ${early} ${late}`);
   if(await actor.evaluate(el=>el.getBoundingClientRect().height)>170)throw Error('Actor too large');
   await page.screenshot({path:`../section_actor_${width}_${scene}.png`});
   await page.evaluate(y=>scrollTo({top:y-700,behavior:'instant'}),top);await page.waitForTimeout(500);
   if(Number(await actor.getAttribute('data-progress'))>=late)throw Error('Reverse scroll failed');
  }
  await page.locator('[data-scene="wave"]').scrollIntoViewIfNeeded();
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow');
  await page.emulateMedia({reducedMotion:'reduce'});await page.waitForTimeout(150);
  if(await page.locator('[data-scene="wave"]').getAttribute('data-progress')!=='1.000')throw Error('Reduced motion not settled');
  if(errors.length)throw Error(errors.join(';'));console.log(width,'fixed docks, scroll actions, size, reduced motion passed');await page.close();
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
