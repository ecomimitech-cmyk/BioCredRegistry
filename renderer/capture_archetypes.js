/**
 * BioCred Renderer — capture screenshots of the 3 archetype payloads.
 * Used as a one-shot visual artefact for review (Block 1 deliverable).
 */
const path = require("path");
const fs = require("fs");
const http = require("http");
const puppeteer = require("puppeteer");

const PORT = 8792;
const ROOT = path.resolve(__dirname);
const OUT = path.join(ROOT, "screenshots");

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const reqPath = req.url.split("?")[0];
      const filePath = path.join(ROOT, reqPath);
      if (!filePath.startsWith(ROOT)) { res.writeHead(403); return res.end(); }
      fs.readFile(filePath, (err, data) => {
        if (err) { res.writeHead(404); return res.end(); }
        const ext = path.extname(filePath);
        const types = { ".html": "text/html", ".js": "application/javascript", ".css": "text/css" };
        res.writeHead(200, { "Content-Type": types[ext] || "text/plain" });
        res.end(data);
      });
    });
    server.listen(PORT, () => resolve(server));
  });
}

async function main() {
  if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });
  const server = await startServer();
  const launchOpts = { headless: "new" };
  const sysChrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
  if (fs.existsSync(sysChrome)) launchOpts.executablePath = sysChrome;
  const browser = await puppeteer.launch(launchOpts);
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 800, height: 720, deviceScaleFactor: 2 });
    await page.goto(`http://localhost:${PORT}/test_renderer.html`, { waitUntil: "networkidle0" });

    const archetypes = [
      { fn: "loadField",      file: "archetype_field.png" },
      { fn: "loadRegulatory", file: "archetype_regulatory.png" },
      { fn: "loadAcademic",   file: "archetype_academic.png" },
    ];

    for (const a of archetypes) {
      await page.evaluate((fn) => window[fn](), a.fn);
      await new Promise((r) => setTimeout(r, 300));
      await page.screenshot({ path: path.join(OUT, a.file), fullPage: false });
      console.log("wrote", a.file);
    }
  } finally {
    await browser.close();
    server.close();
  }
}

main();
