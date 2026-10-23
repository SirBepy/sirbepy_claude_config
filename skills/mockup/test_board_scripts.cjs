// End-to-end test for bundle-board.mjs and verify-board.cjs using a tiny generated sample board.
//   BOARD_PROJECT=<web project with vite in node_modules> node test_board_scripts.cjs
// Optional: BOARD_PANEL_DOC=<preview-panel-document.ts> exercises the panel splice offline;
// BOARD_TEST_SCRATCH=<dir> picks where the throwaway run folder is created (default os.tmpdir()).
// Skips (exit 0, says so) when no project with vite is given: the scripts never install packages.
// Uses --route local: the panel route needs the live Conductor app, which this test never POSTs to.
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const here = __dirname;
const project = process.env.BOARD_PROJECT;
if (!project || !fs.existsSync(path.join(project, "node_modules", "vite"))) {
  console.log("SKIP: set BOARD_PROJECT to a web project that has vite installed");
  process.exit(0);
}

const run = path.join(process.env.BOARD_TEST_SCRATCH || os.tmpdir(), `board-test-${process.pid}`);
fs.mkdirSync(run, { recursive: true });
const made = [];
const write = (name, text) => { const p = path.join(run, name); fs.writeFileSync(p, text); made.push(p); return p; };

let failed = 0;
const check = (name, ok, detail) => {
  console.log(`${ok ? "ok  " : "FAIL"} ${name}${ok ? "" : ": " + detail}`);
  if (!ok) failed++;
};
const node = (script, args) =>
  spawnSync(process.execPath, [path.join(here, script), ...args], { encoding: "utf8", env: { ...process.env, BOARD_PROJECT: project }, timeout: 110000 });

try {
  write("helper.ts", "export const label = (n: number): string => `count:${n}`;\n");
  write("style.css", ".board-root .counter { color: rgb(1, 2, 3); }\n");
  write("good.ts", `import "./style.css";
import { label } from "./helper";
let n = 0;
const out = document.getElementById("out")!;
document.getElementById("inc")!.addEventListener("click", () => { n++; out.textContent = label(n); });
`);
  write("good.src.html", `<!doctype html><html><head><meta charset="utf-8"></head>
<body><div class="board-root"><button id="inc" class="counter">inc</button><span id="out">count:0</span></div>
<script type="module" src="./good.ts"></script></body></html>
`);
  write("bad-click.ts", `document.getElementById("inc")!.addEventListener("click", () => { throw new Error("boom"); });\n`);
  write("bad-click.src.html", `<!doctype html><html><head></head><body><button id="inc">inc</button>
<script type="module" src="./bad-click.ts"></script></body></html>
`);
  write("bad-literal.src.html", `<!doctype html><html><head></head><body><p id="p">x</p>
<script>var tpl = "</body>"; document.getElementById("p").textContent = tpl.length;</script></body></html>
`);
  const plan = write("plan.json", JSON.stringify({
    settleMs: 1800,
    steps: [
      { type: "click", selector: "#inc" },
      { type: "click", selector: "#inc" },
      { type: "expectText", selector: "#out", equals: "count:2" },
      { type: "shot", name: "after-clicks.png" },
    ],
  }));
  const shots = path.join(run, "shots");

  const out = path.join(run, "good.html");
  const b = node("bundle-board.mjs", [path.join(run, "good.src.html"), out]);
  check("bundle-board builds the sample board", b.status === 0 && fs.existsSync(out), b.stderr || b.stdout);
  const html = fs.existsSync(out) ? fs.readFileSync(out, "utf8") : "";
  check("bundle is self-contained (inline script and style, no local refs)", /<script type="module">/.test(html) && /<style>/.test(html) && !/(src|href)="\.\//.test(html), html.slice(0, 400));
  check("bundled CSS rule is present", /\.board-root \.counter\{/.test(html), "css missing (vite minifies, so match the selector)");

  const extra = process.env.BOARD_PANEL_DOC ? ["--panel-doc", process.env.BOARD_PANEL_DOC] : [];
  const v = node("verify-board.cjs", [out, shots, plan, "--route", "local", ...extra]);
  check("verify-board passes real clicks in the sandbox", v.status === 0, v.stdout + v.stderr);
  check("verify-board wrote a plan screenshot", fs.existsSync(path.join(shots, "after-clicks.png")), "no png");

  const bc = path.join(run, "bad-click.html");
  node("bundle-board.mjs", [path.join(run, "bad-click.src.html"), bc]);
  const badPlan = write("bad-plan.json", JSON.stringify([{ type: "click", selector: "#inc" }, { type: "wait", ms: 200 }]));
  const vb = node("verify-board.cjs", [bc, shots, badPlan, "--route", "local"]);
  check("verify-board fails on a pageerror from a click", vb.status === 1 && /boom/.test(vb.stdout), vb.stdout + vb.stderr);

  const bl = node("bundle-board.mjs", [path.join(run, "bad-literal.src.html"), path.join(run, "bad-literal.html")]);
  check("bundle-board rejects </body> in an inline script", bl.status === 1 && /<\/body>/.test(bl.stderr), bl.stderr || bl.stdout);

  const rawBad = write("raw-bad.html", fs.readFileSync(path.join(run, "bad-literal.src.html"), "utf8"));
  const vl = node("verify-board.cjs", [rawBad, shots, "--route", "local"]);
  check("verify-board fails a board holding </body> in an inline script", vl.status === 1 && /<\/body>/.test(vl.stdout), vl.stdout + vl.stderr);

  // CSS strings holding </body> and </style must survive bundling with their meaning intact and
  // must not close the style element. The probe reads the computed `content` back in a real browser.
  write("css-literal.css", `.q::before { content: "</body>"; } .q::after { content: "</style>"; }\n`);
  write("css-literal.ts", `import "./css-literal.css";
const q = document.getElementById("q")!;
document.getElementById("o")!.textContent =
  getComputedStyle(q, "::before").content + getComputedStyle(q, "::after").content;
`);
  write("css-literal.src.html", `<!doctype html><html><head><meta charset="utf-8"></head>
<body><div id="q" class="q"></div><span id="o">unset</span>
<script type="module" src="./css-literal.ts"></script></body></html>
`);
  const cssOut = path.join(run, "css-literal.html");
  const cb = node("bundle-board.mjs", [path.join(run, "css-literal.src.html"), cssOut]);
  check("bundle-board bundles a board whose CSS strings hold </body> and </style>", cb.status === 0 && fs.existsSync(cssOut), cb.stderr || cb.stdout);
  const cssHtml = fs.existsSync(cssOut) ? fs.readFileSync(cssOut, "utf8") : "";
  check("a literal </style in CSS cannot close the style element", (cssHtml.match(/<\/style/gi) || []).length === 1, cssHtml.slice(0, 600));
  const cssPlan = write("css-plan.json", JSON.stringify({
    settleMs: 1800,
    steps: [{ type: "expectText", selector: "#o", equals: '"</body>""</style>"' }],
  }));
  const cv = node("verify-board.cjs", [cssOut, shots, cssPlan, "--route", "local"]);
  check("CSS content strings render unchanged in the sandbox", cv.status === 0, cv.stdout + cv.stderr);
} finally {
  fs.rmSync(run, { recursive: true, force: true });
}
process.exit(failed ? 1 : 0);
