// Verifies a bundled interactive /mockup board the way the preview panel will run it: inside an
// <iframe sandbox="allow-scripts"> (opaque origin), driven by REAL mouse/keyboard events from a
// plan, with pageerror/console errors captured. A plain Playwright tab hides bugs the sandbox
// exposes (a focus refresh swallowing the first click, a clipboard call denied, a script cut short).
//
//   node verify-board.cjs <board.html> <shotdir> [plan.json]
//        [--route panel|local] [--panel-doc <preview-panel-document.ts>] [--project <dir>]
//
// Routes:
//   panel (default)  Builds the document with the app's own buildPreviewDocumentHtml (transpiled
//                    from --panel-doc), POSTs it to the running Conductor app at
//                    http://127.0.0.1:${PREVIEW_PORT||27182}/hooks/preview-render and loads
//                    GET /hooks/preview-render/<id> in the sandboxed iframe. This is the panel's
//                    real route; a board that works only in a hand-made iframe fails here.
//   local            Same document, but loaded through iframe srcdoc with no server. Use it when
//                    the app is not running, and say so: it is weaker than panel.
//
// --panel-doc defaults to <project>/src/views/sessions/preview-panel-document.ts when that file
// exists. --project (or env BOARD_PROJECT, else cwd) is where vite/esbuild is resolved from to
// transpile that TS. Without a panel-doc the raw board is sent as-is and the diagnostics splice is
// not simulated (stated in the output).
//
// plan.json: an array of steps, or {"viewport":{"width":..,"height":..},"settleMs":2500,"steps":[..]}.
//   {"type":"click","selector":"..."}        real mouse click at the element centre
//   {"type":"hover","selector":"..."}        real mouse move
//   {"type":"type","selector":"...","text":"..."}   click, then real keystrokes
//   {"type":"press","key":"ArrowRight"}
//   {"type":"wait","ms":300}   {"type":"waitFor","selector":"..."}
//   {"type":"expectText","selector":"...","equals"|"contains":"..."}
//   {"type":"expectCount","selector":"...","count":3}
//   {"type":"expectAttr","selector":"...","attr":"data-theme","equals"|"contains":"..."}
//   {"type":"expectVisible","selector":"...","visible":false}
//   {"type":"shot","name":"after-click.png"}
// Selectors are scoped to the board inside the iframe. Exit 0 = all green, 1 = a check failed,
// 2 = usage, 3 = tooling missing.
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");
const { pathToFileURL } = require("node:url");

function usage(msg) {
  if (msg) console.error(`verify-board: ${msg}`);
  console.error("usage: node verify-board.cjs <board.html> <shotdir> [plan.json] [--route panel|local] [--panel-doc <ts>] [--project <dir>]");
  process.exit(2);
}

const argv = process.argv.slice(2);
const pos = [];
let route = "panel";
let panelDoc = process.env.BOARD_PANEL_DOC || "";
let projectArg = process.env.BOARD_PROJECT || "";
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === "--route") route = argv[++i];
  else if (argv[i] === "--panel-doc") panelDoc = argv[++i];
  else if (argv[i] === "--project") projectArg = argv[++i];
  else pos.push(argv[i]);
}
if (pos.length < 2 || pos.length > 3) usage();
if (route !== "panel" && route !== "local") usage(`--route must be panel or local, got ${route}`);
const boardPath = path.resolve(pos[0]);
const shotDir = path.resolve(pos[1]);
const project = path.resolve(projectArg || process.cwd());
if (!fs.existsSync(boardPath)) usage(`board not found: ${boardPath}`);
if (!panelDoc) {
  const guess = path.join(project, "src/views/sessions/preview-panel-document.ts");
  if (fs.existsSync(guess)) panelDoc = guess;
}

let plan = { steps: [] };
if (pos[2]) {
  const raw = JSON.parse(fs.readFileSync(path.resolve(pos[2]), "utf8"));
  plan = Array.isArray(raw) ? { steps: raw } : raw;
}
const viewport = plan.viewport || { width: 1100, height: 800 };
// Longer than the panel diagnostics timer (1500 ms) so its "never executed" banner can surface.
const settleMs = plan.settleMs ?? 2000;

const failures = [];
const fail = (msg) => { failures.push(msg); console.log(`FAIL  ${msg}`); };
const pass = (msg) => console.log(`ok    ${msg}`);

// The preview panel splices a diagnostics script into the raw text at </body>; these literals in
// an inline script or comment corrupt the pushed page. Checked statically so the failure does not
// depend on which splice implementation the installed app has.
function lintLiterals(html) {
  const blocks = [
    ...[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => ["script", m[1]]),
    ...[...html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => ["style", m[1]]),
    ...[...html.matchAll(/<!--([\s\S]*?)-->/g)].map((m) => ["comment", m[1]]),
  ];
  const bad = [];
  for (const [kind, body] of blocks) {
    const hit = /<\/body>|<head[\s>/]|<html[\s>/]/i.exec(body);
    if (hit) bad.push(`inline ${kind} contains literal "${hit[0]}"`);
  }
  return bad;
}

async function loadPanelBuilder() {
  const ts = fs.readFileSync(panelDoc, "utf8");
  const req = createRequire(path.join(project, "package.json"));
  let code;
  try {
    code = req("esbuild").transformSync(ts, { loader: "ts", format: "esm" }).code;
  } catch {
    try {
      const vp = req.resolve("vite/package.json");
      const pkg = JSON.parse(fs.readFileSync(vp, "utf8"));
      const root = pkg.exports && pkg.exports["."];
      const esm = root && (typeof root === "string" ? root : typeof root.import === "string" ? root.import : root.import && root.import.default);
      const vite = await import(pathToFileURL(path.resolve(path.dirname(vp), esm || pkg.module || pkg.main)).href);
      code = (await vite.transformWithEsbuild(ts, "doc.ts", { loader: "ts", format: "esm" })).code;
    } catch (e) {
      console.error(`verify-board: cannot transpile ${panelDoc}: no esbuild or vite resolvable from ${project} (${e.code || e.message}). Pass --project <dir> or BOARD_PROJECT.`);
      process.exit(3);
    }
  }
  const mod = await import("data:text/javascript;base64," + Buffer.from(code).toString("base64"));
  if (typeof mod.buildPreviewDocumentHtml !== "function") {
    console.error(`verify-board: ${panelDoc} does not export buildPreviewDocumentHtml`);
    process.exit(3);
  }
  return mod.buildPreviewDocumentHtml;
}

(async () => {
  let chromium;
  try {
    chromium = require("../_shared/playwright-resolve.cjs").getChromium();
  } catch (e) {
    console.error(`verify-board: playwright unavailable: ${e.message}`);
    process.exit(3);
  }

  const raw = fs.readFileSync(boardPath, "utf8");
  const lint = lintLiterals(raw);
  for (const l of lint) fail(`${l} (breaks the panel's </body> splice)`);

  let doc = raw;
  if (panelDoc) doc = (await loadPanelBuilder())(raw);
  else console.log("note  no --panel-doc: raw board sent, the panel's diagnostics splice is NOT simulated");

  let frameAttrs;
  if (route === "panel") {
    const base = `http://127.0.0.1:${process.env.PREVIEW_PORT || 27182}/hooks/preview-render`;
    let id;
    try {
      const res = await fetch(base, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ html: doc }) });
      ({ id } = await res.json());
      if (!id) throw new Error(`no id in response (HTTP ${res.status})`);
    } catch (e) {
      console.error(`verify-board: Conductor preview endpoint unreachable at ${base} (${e.message}). Start the app, or rerun with --route local and report that the panel route was not exercised.`);
      process.exit(3);
    }
    frameAttrs = `src="${base}/${id}"`;
    console.log(`route panel: ${base}/${id}`);
  } else {
    frameAttrs = `srcdoc="${doc.replace(/&/g, "&amp;").replace(/"/g, "&quot;")}"`;
    console.log("route local: srcdoc in a sandboxed iframe (panel route NOT exercised)");
  }

  fs.mkdirSync(shotDir, { recursive: true });
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport });
    const errors = [];
    page.on("pageerror", (e) => errors.push(`pageerror: ${e}`));
    page.on("console", (m) => { if (m.type() === "error") errors.push(`console.error: ${m.text()}`); });
    await page.setContent(
      `<body style="margin:0"><iframe sandbox="allow-scripts" style="border:0;width:${viewport.width}px;height:${viewport.height}px" ${frameAttrs}></iframe></body>`
    );
    const f = page.frameLocator("iframe");
    const centre = async (loc) => {
      await loc.first().scrollIntoViewIfNeeded();
      const b = await loc.first().boundingBox();
      if (!b) throw new Error("element has no box");
      return [b.x + b.width / 2, b.y + b.height / 2];
    };

    try {
      await f.locator("body *").first().waitFor({ timeout: 10000 });
      pass("board rendered inside the sandboxed iframe");
    } catch {
      fail("board body is empty inside the sandboxed iframe (scripts dead or document cut short)");
    }
    await page.waitForTimeout(settleMs);
    const banners = await f.locator("text=preview diagnostic").count();
    if (banners) fail(`panel diagnostics banner shown (${banners}): ${await f.locator("text=preview diagnostic").first().innerText()}`);
    else pass("no panel diagnostics banner");
    await page.screenshot({ path: path.join(shotDir, "board-initial.png") });

    let n = 0;
    for (const step of plan.steps) {
      n++;
      const label = `step ${n} ${step.type}${step.selector ? " " + step.selector : ""}`;
      try {
        const loc = step.selector ? f.locator(step.selector) : null;
        switch (step.type) {
          case "click": { const [x, y] = await centre(loc); await page.mouse.click(x, y); break; }
          case "hover": { const [x, y] = await centre(loc); await page.mouse.move(x, y); break; }
          case "type": { const [x, y] = await centre(loc); await page.mouse.click(x, y); await page.keyboard.type(step.text); break; }
          case "press": await page.keyboard.press(step.key); break;
          case "wait": await page.waitForTimeout(step.ms ?? 300); break;
          case "waitFor": await loc.first().waitFor({ timeout: step.timeout ?? 5000 }); break;
          case "expectText": {
            const t = (await loc.first().innerText({ timeout: 3000 })).trim();
            if ("equals" in step ? t !== step.equals : !t.includes(step.contains)) throw new Error(`text was "${t}"`);
            break;
          }
          case "expectCount": {
            const c = await loc.count();
            if (c !== step.count) throw new Error(`count was ${c}, expected ${step.count}`);
            break;
          }
          case "expectAttr": {
            const v = (await loc.first().getAttribute(step.attr, { timeout: 3000 })) ?? "";
            if ("equals" in step ? v !== step.equals : !v.includes(step.contains)) throw new Error(`${step.attr} was "${v}"`);
            break;
          }
          case "expectVisible": {
            const v = await loc.first().isVisible();
            if (v !== (step.visible !== false)) throw new Error(`visible was ${v}`);
            break;
          }
          case "shot": await page.screenshot({ path: path.join(shotDir, step.name || `step-${n}.png`) }); break;
          default: throw new Error(`unknown step type "${step.type}"`);
        }
        pass(label);
      } catch (e) {
        fail(`${label}: ${String(e.message).split("\n")[0]}`);
      }
    }

    await page.screenshot({ path: path.join(shotDir, "board-final.png") });
    for (const e of errors) fail(e);
    if (!errors.length) pass("no pageerror or console.error");
  } finally {
    await browser.close();
  }

  console.log(failures.length ? `\nFAILED: ${failures.length} problem(s)` : "\nPASSED");
  process.exit(failures.length ? 1 : 0);
})().catch((e) => { console.error(`verify-board: ${e.stack || e}`); process.exit(3); });
