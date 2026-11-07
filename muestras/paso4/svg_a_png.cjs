// Convierte cada .svg de las subcarpetas a PNG a 150 ppp con Chromium (Playwright).
// Uso: node muestras/paso4/svg_a_png.cjs muestras/paso4
const { chromium } = require('playwright');
const { readdirSync, readFileSync, statSync } = require('node:fs');
const { join } = require('node:path');

const root = process.argv[2];
const PX_PER_PT = 150 / 72;      // 150 ppp
const CSS_PX_PER_PT = 96 / 72;   // 1pt = 1.333 px CSS
(async () => {
const browser = await chromium.launch();
for (const sub of readdirSync(root)) {
  const dir = join(root, sub);
  if (!statSync(dir).isDirectory()) continue;
  for (const f of readdirSync(dir).filter((n) => n.endsWith('.svg'))) {
    const svg = readFileSync(join(dir, f), 'utf8');
    const [, w, h] = svg.match(/width="([\d.]+)pt" height="([\d.]+)pt"/);
    const page = await browser.newPage({
      viewport: { width: Math.ceil(w * CSS_PX_PER_PT), height: Math.ceil(h * CSS_PX_PER_PT) },
      deviceScaleFactor: PX_PER_PT / CSS_PX_PER_PT,
    });
    await page.setContent(`<html><body style="margin:0;background:#fff">${svg}</body></html>`);
    await page.screenshot({ path: join(dir, f.replace(/\.svg$/, '.svg.png')) });
    await page.close();
  }
}
await browser.close();
})();
