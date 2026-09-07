/**
 * Authentix UI smoke test.
 *
 *   1. start the API + built UI:  python server.py           (port 8000)
 *   2. run:                        node frontend/e2e/smoke.mjs
 *
 * Uploads every file in ./samples, asserts the report renders with no console
 * errors, and writes a full-page screenshot per sample to frontend/e2e/out/.
 * Override the target with  BASE=http://127.0.0.1:8010 node frontend/e2e/smoke.mjs
 */
import { chromium } from "playwright";
import { readdirSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const BASE = process.env.BASE || "http://127.0.0.1:8000";
const SAMPLES = resolve(HERE, "../../samples");
const OUT = join(HERE, "out");
mkdirSync(OUT, { recursive: true });

const files = readdirSync(SAMPLES).filter((f) => /\.(pdf|docx|xlsx|pptx)$/i.test(f));
if (!files.length) {
  console.error("no samples found — run: python tests/make_samples.py");
  process.exit(1);
}

const browser = await chromium.launch();
let failures = 0;

for (const file of files) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1400 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

  try {
    await page.goto(BASE, { waitUntil: "networkidle" });
    await page.setInputFiles('input[type="file"]', join(SAMPLES, file));
    await page.waitForSelector(".rep__hero", { timeout: 15000 });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: join(OUT, `${file}.png`), fullPage: true });

    const info = await page.evaluate(() => ({
      score: document.querySelector(".gauge__num,.gauge__na")?.textContent?.trim(),
      band: document.querySelector(".gauge__band")?.textContent?.trim(),
      sections: [...document.querySelectorAll(".section-title")].every(
        (el) => getComputedStyle(el).opacity === "1"
      ),
    }));

    if (errors.length || !info.sections) {
      failures++;
      console.log(`FAIL  ${file}  ${JSON.stringify(info)}  ${errors.join(" | ")}`);
    } else {
      console.log(`ok    ${file}  ${info.score}  ${info.band}`);
    }
  } catch (e) {
    failures++;
    console.log(`FAIL  ${file}  ${e.message}`);
  }
  await ctx.close();
}

await browser.close();
console.log(failures ? `\n${failures} failure(s)` : `\nall ${files.length} samples ok`);
process.exit(failures ? 1 : 0);
