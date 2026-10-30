// Headless render of cad/render/render.html -> cad/out/render_<view>.png
//   npm install three@0.160.0      (anywhere; pass its node_modules via THREE_DIR)
//   THREE_DIR=/path/to/node_modules/three node cad/render/render.mjs
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const here = path.dirname(fileURLToPath(import.meta.url));
const sceneDir = path.resolve(here, "../out/scene");
const outDir = path.resolve(here, "../out");
const threeDir = process.env.THREE_DIR || path.resolve(here, "node_modules/three");

const types = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".stl": "model/stl" };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(new URL(req.url, "http://x").pathname);
  let f;
  if (u.startsWith("/three/")) f = path.join(threeDir, u.slice(7));
  else if (u.startsWith("/scene/")) f = path.join(sceneDir, u.slice(7));
  else f = path.join(here, u === "/" ? "render.html" : u);
  fs.readFile(f, (err, data) => {
    if (err) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { "Content-Type": types[path.extname(f)] || "application/octet-stream" });
    res.end(data);
  });
}).listen(0);
const port = server.address().port;

const views = [
  ["hero", 1600, 1700], ["cutaway", 1600, 1700], ["top", 1400, 1100], ["exploded", 2200, 1800],
];
const browser = await chromium.launch({ args: ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
for (const [view, w, h] of views) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  page.on("console", (m) => { if (m.type() === "error") console.error(view, m.text()); });
  page.on("pageerror", (e) => console.error(view, e.message));
  await page.goto(`http://localhost:${port}/render.html?view=${view}&w=${w}&h=${h}`);
  await page.waitForFunction("window.__done === true", null, { timeout: 300000 });
  await page.screenshot({ path: path.join(outDir, `render_${view}.png`) });
  console.log("wrote", `render_${view}.png`);
  await page.close();
}
await browser.close();
server.close();
