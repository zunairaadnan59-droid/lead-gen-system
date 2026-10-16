const { chromium } = require('/opt/node-tools/node_modules/playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 2 });
  await p.goto('file://' + __dirname + '/post.html');
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(300);
  const fams = await p.evaluate(() => [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight));
  console.log([...new Set(fams)].join(', '));
  await p.screenshot({ path: __dirname + '/store-season-post.png' });
  await b.close();
})();
