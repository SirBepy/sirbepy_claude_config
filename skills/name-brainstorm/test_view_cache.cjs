// Test for view-cache.mjs: status letters (F/T/?) and the .co column that --extra co results need.
//   node test_view_cache.cjs
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

// VIEW_CACHE_PATH lets a red-proof run point the same assertions at an older copy of the script.
const script = process.env.VIEW_CACHE_PATH || path.join(__dirname, "view-cache.mjs");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "view-cache-test-"));
const cachePath = path.join(dir, "cache.json");

let failed = 0;
const check = (name, ok, detail) => {
  console.log(`${ok ? "ok  " : "FAIL"} ${name}${ok ? "" : ": " + detail}`);
  if (!ok) failed++;
};
const run = (...args) => spawnSync(process.execPath, [script, cachePath, ...args], { encoding: "utf8" });

try {
  fs.writeFileSync(
    cachePath,
    JSON.stringify({
      "com:alpha": { status: "FREE", note: "" },
      "io:alpha": { status: "TAKEN", note: "" },
      "co:alpha": { status: "FREE", note: "" },
      "ai:alpha": { status: "FREE", note: "" },
      "com:beta": { status: "TAKEN", note: "" },
      "ai:beta": { status: "FREE", note: "" },
      "co:beta": { status: "TAKEN", note: "" },
    }),
  );

  const list = run("list", "alpha,beta");
  check("list exits 0", list.status === 0, list.stderr);
  const lines = list.stdout.split("\n");
  const alpha = lines.find((l) => l.startsWith("alpha")) || "";
  const beta = lines.find((l) => l.startsWith("beta")) || "";
  check("FREE shows F", /\bcom=F\b/.test(alpha), alpha);
  check("TAKEN shows T", /\bio=T\b/.test(alpha), alpha);
  check("never-looked-up shows ?", /\bhr=\?/.test(alpha) && /\bnpm=\?/.test(alpha), alpha);
  check(".co FREE is shown", /\bco=F\b/.test(alpha), alpha);
  check(".co TAKEN is shown", /\bco=T\b/.test(beta), beta);

  const comfree = run("comfree");
  check("comfree counts names with .com free", /^1 of 2 with \.com free/.test(comfree.stdout), comfree.stdout);
  check("comfree lists alpha only", /^alpha\b/m.test(comfree.stdout) && !/^beta\b/m.test(comfree.stdout), comfree.stdout);

  const aifree = run("aifree");
  check("aifree lists .ai free with .com taken", /^1 with \.ai free but \.com taken/.test(aifree.stdout) && /^beta$/m.test(aifree.stdout), aifree.stdout);

  const bad = run("nonsense");
  check("unknown mode exits 1", bad.status === 1, `status ${bad.status}`);
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}

if (failed) {
  console.log(`${failed} check(s) failed`);
  process.exit(1);
}
console.log("all checks passed");
