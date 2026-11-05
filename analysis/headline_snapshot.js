// Records the standard headline numbers from a Road to 2028 page so updates can be compared with the baseline.
// Usage: node headline_snapshot.js PATH_TO_PAGE.html OUTPUT.json   (needs Node and Playwright; Claude can run it for you)
const {chromium}=require('playwright');
const [,, page, out]=process.argv;
const PATTERNS=['pool','poolW','open','inc','none'];
const PAIRS=[['Generic Democrat','Generic Republican'],['Buttigieg','Vance'],['Ocasio-Cortez','Vance'],['Ossoff','Rubio']];
(async()=>{
  const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1200,height:900}});
  await p.goto('file://'+require('path').resolve(page));
  await p.waitForFunction(()=>document.querySelectorAll('#audit tr').length>5,{timeout:90000});
  const result={page,generated:new Date().toISOString(),patterns:{}};
  for(const reg of PATTERNS){
    await p.selectOption('#reg',reg); await p.waitForTimeout(2500);
    await p.waitForFunction(()=>document.querySelectorAll('#audit tr').length>5);
    const e=JSON.parse(await p.$eval('#exportBox',el=>el.value));
    if(!result.model){result.model=e.model;result.seed=e.seed;result.simulations=e.simulations}
    const rows={}; for(const [d,r] of PAIRS){const c=e.matrix.flat().find(x=>x.d===d&&x.r===r);
      rows[d+' v '+r]={win:+(100*c.win).toFixed(1),median_margin:+c.median_margin.toFixed(1),margin90:c.margin90.map(v=>+v.toFixed(1))}}
    result.patterns[reg]=rows;
  }
  require('fs').writeFileSync(out,JSON.stringify(result,null,1)); console.log(JSON.stringify(result.patterns.pool,null,1)); await b.close();
})();
