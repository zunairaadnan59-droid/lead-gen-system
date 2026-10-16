const { chromium } = require('/opt/node-tools/node_modules/playwright');
const { spawn } = require('child_process');
const path = require('path');
const mode = process.argv[2] || 'preview';
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.join(__dirname, 'scene.html'));
  await page.evaluate(() => document.fonts.ready);
  if (mode === 'preview') {
    const times = process.argv.slice(3).map(Number);
    for (const t of times) {
      await page.evaluate(t => render(t), t);
      await page.screenshot({ path: path.join(__dirname, 'preview', `t${t}.jpg`), type: 'jpeg', quality: 70 });
    }
  } else {
    const fps = 30, dur = 36.5, out = path.join(__dirname, 'night-watch.mp4');
    const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out], { stdio: ['pipe', 'ignore', 'inherit'] });
    for (let i = 0; i < Math.round(fps * dur); i++) {
      await page.evaluate(t => render(t), i / fps);
      const buf = await page.screenshot({ type: 'png' });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    console.log('wrote', out);
  }
  await browser.close();
})();
