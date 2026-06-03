/**
 * BioCred Renderer — Visual Centroid Test (headless Chrome via puppeteer)
 *
 * Validates that the black centroid dot is drawn at the geometric mean
 * of the evidence points for each demo payload. Runs against
 * test_renderer.html served by a local HTTP server.
 *
 * Usage:
 *   node renderer/test_centroid_visual.js
 *
 * Exits 0 on success, 1 on any assertion failure.
 */
const path = require("path");
const puppeteer = require("puppeteer");
const http = require("http");
const fs = require("fs");

const PORT = 8791;
const ROOT = path.resolve(__dirname);

function startServer() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const reqPath = req.url.split("?")[0];
      const filePath = path.join(ROOT, reqPath);
      if (!filePath.startsWith(ROOT)) {
        res.writeHead(403);
        return res.end();
      }
      fs.readFile(filePath, (err, data) => {
        if (err) {
          res.writeHead(404);
          return res.end();
        }
        const ext = path.extname(filePath);
        const types = {
          ".html": "text/html",
          ".js":   "application/javascript",
          ".css":  "text/css",
        };
        res.writeHead(200, { "Content-Type": types[ext] || "text/plain" });
        res.end(data);
      });
    });
    server.listen(PORT, () => resolve(server));
  });
}

async function main() {
  const server = await startServer();
  let failed = 0;
  let passed = 0;
  const launchOpts = { headless: "new" };
  const sysChrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
  if (fs.existsSync(sysChrome)) launchOpts.executablePath = sysChrome;
  const browser = await puppeteer.launch(launchOpts);

  function assert(name, cond, detail) {
    if (cond) { passed++; console.log("  PASS:", name); }
    else      { failed++; console.log("  FAIL:", name, detail || ""); }
  }

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 800, height: 700, deviceScaleFactor: 1 });
    await page.goto(`http://localhost:${PORT}/test_renderer.html`, {
      waitUntil: "networkidle0",
    });

    const fixtures = ["loadField", "loadRegulatory", "loadAcademic"];
    for (const fnName of fixtures) {
      console.log(`\n[${fnName}]`);
      await page.evaluate((fn) => window[fn](), fnName);
      await new Promise((r) => setTimeout(r, 250));

      const result = await page.evaluate(() => {
        const Geo = window.BioCredGeo;
        const container = document.getElementById("biocred-profile");
        const canvas = container.querySelector("canvas");
        if (!canvas) return { ok: false, reason: "no canvas" };

        const dpr = window.devicePixelRatio || 1;
        const w = canvas.width / dpr;
        const h = canvas.height / dpr;
        const cx = w / 2;
        const cy = h * 0.49;
        const radius = Math.min(w, h) * 0.30;
        const verts = Geo.pentagonVertices(cx, cy, radius, -90);

        const lastPayload =
          /Field/i.test(document.querySelector("h1").textContent)
            ? window.fieldPayload
            : /Regulatory/i.test(document.querySelector("h1").textContent)
              ? window.regulatoryPayload
              : window.academicPayload;

        const points = lastPayload.evidence_units.map((u) =>
          Geo.barycentricXY(u.domain_weights, verts)
        );
        const expected = Geo.centroid(points);

        const ctx = canvas.getContext("2d");
        const sample = (x, y) => {
          const px = ctx.getImageData(x * dpr, y * dpr, 1, 1).data;
          return { r: px[0], g: px[1], b: px[2], a: px[3] };
        };

        let bestDist = Infinity;
        let bestXY = null;
        for (let dy = -10; dy <= 10; dy++) {
          for (let dx = -10; dx <= 10; dx++) {
            const x = Math.round(expected.x + dx);
            const y = Math.round(expected.y + dy);
            const c = sample(x, y);
            if (c.r < 30 && c.g < 30 && c.b < 30 && c.a > 200) {
              const d = Math.hypot(dx, dy);
              if (d < bestDist) { bestDist = d; bestXY = { x, y }; }
            }
          }
        }
        return {
          ok: true,
          expected,
          bestXY,
          bestDist,
        };
      });

      assert(`${fnName}: canvas rendered`, result.ok, result.reason);
      assert(
        `${fnName}: black centroid dot found near expected (x=${result.expected.x.toFixed(1)}, y=${result.expected.y.toFixed(1)})`,
        result.bestDist <= 6,
        `nearest black pixel was at distance ${result.bestDist}`,
      );
    }

    console.log("\n[loadEmpty]");
    await page.evaluate(() => window.loadEmpty());
    await new Promise((r) => setTimeout(r, 200));
    const emptyMsg = await page.evaluate(() =>
      document.getElementById("biocred-profile").textContent.trim()
    );
    assert(
      "loadEmpty: shows 'No evidence' fallback (no centroid expected)",
      emptyMsg.toLowerCase().includes("no evidence"),
      `got: '${emptyMsg}'`,
    );
  } catch (e) {
    console.error("FATAL:", e);
    failed++;
  } finally {
    await browser.close();
    server.close();
  }

  console.log("\n============================================================");
  console.log(`RESULTS: ${passed} passed, ${failed} failed, ${passed + failed} total`);
  console.log("============================================================");
  process.exit(failed > 0 ? 1 : 0);
}

main();
