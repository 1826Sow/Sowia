import { chromium } from "playwright";
import fs from "node:fs/promises";

const renderUrl = process.env.RENDER_URL || "https://sowia.onrender.com/";
const cloudUrl = process.env.STREAMLIT_URL || "https://fm5aczcvvj5jgkhpxwqtcr.streamlit.app/";
await fs.mkdir("artifacts", { recursive: true });

const browser = await chromium.launch({ headless: true });
const diagnostics = { render: {}, streamlitCloud: {} };

async function inspect(url, name, expectedText = null, timeout = 240000) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = { console: [], page: [], failedRequests: [], badResponses: [] };
  page.on("console", msg => { if (msg.type() === "error") errors.console.push(msg.text()); });
  page.on("pageerror", err => errors.page.push(String(err)));
  page.on("requestfailed", req => errors.failedRequests.push({ url: req.url(), error: req.failure()?.errorText || "unknown" }));
  page.on("response", res => { if (res.status() >= 400) errors.badResponses.push({ status: res.status(), url: res.url() }); });
  let navigationError = null;
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout });
    if (expectedText) {
      await page.getByText(expectedText, { exact: false }).first().waitFor({ state: "visible", timeout });
    } else {
      await page.waitForTimeout(12000);
    }
  } catch (err) {
    navigationError = String(err);
  }
  const bodyText = await page.locator("body").innerText().catch(() => "");
  const result = {
    url,
    title: await page.title().catch(() => ""),
    navigationError,
    expectedTextVisible: expectedText ? bodyText.includes(expectedText) : null,
    bodyPreview: bodyText.slice(0, 2500),
    errors
  };
  await page.screenshot({ path: `artifacts/${name}.png`, fullPage: true }).catch(() => {});
  await fs.writeFile(`artifacts/${name}.json`, JSON.stringify(result, null, 2));
  await page.close();
  return result;
}

try {
  diagnostics.render = await inspect(renderUrl, "render", "Connexion à SOW IA", 240000);
  diagnostics.streamlitCloud = await inspect(cloudUrl, "streamlit-cloud", null, 60000);
  console.log("SOWIA_BROWSER_DIAGNOSTICS=" + JSON.stringify(diagnostics, null, 2));
  if (!diagnostics.render.expectedTextVisible) {
    console.error("ÉCHEC: l'écran de connexion SOW IA n'a pas été rendu sur Render.");
    process.exitCode = 1;
  } else {
    console.log("SUCCÈS: l'écran de connexion SOW IA est visible sur Render.");
  }
} finally {
  await browser.close();
}
