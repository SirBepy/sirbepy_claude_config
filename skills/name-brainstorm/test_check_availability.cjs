// Offline test for check-availability.mjs: fetch is stubbed, nothing touches the network.
//   node test_check_availability.cjs
// Covers: concurrent first lookups all see the IANA bootstrap data, an npm 404 is UNKNOWN (an
// unpublished package also 404s), withRetry gives up as UNKNOWN, parseArgs and readNames.
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

// CHECK_AVAILABILITY_PATH lets a red-proof run point the same assertions at an older copy.
const script = process.env.CHECK_AVAILABILITY_PATH || path.join(__dirname, "check-availability.mjs");
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "check-availability-test-"));

let failed = 0;
const check = (name, ok, detail) => {
  console.log(`${ok ? "ok  " : "FAIL"} ${name}${ok ? "" : ": " + detail}`);
  if (!ok) failed++;
};

const realFetch = globalThis.fetch;
const realError = console.error;
let fetchCalls = [];

// Each import gets its own module instance (query string), so the bootstrap memo starts empty.
let n = 0;
const fresh = () => import(`${pathToFileURL(script).href}?t=${++n}`);

const jsonRes = (status, body) => ({
  status,
  ok: status >= 200 && status < 300,
  headers: { get: () => null },
  json: async () => body,
  arrayBuffer: async () => new ArrayBuffer(0),
});
const IANA = { services: [[["com"], ["https://iana-says.test/rdap/"]]] };

async function main() {
  // ---- bootstrap: concurrent first lookups share one fetch and all see its data
  {
    fetchCalls = [];
    globalThis.fetch = async (url) => {
      fetchCalls.push(String(url));
      await new Promise((r) => setTimeout(r, 40)); // slow enough that every caller arrives mid-flight
      return jsonRes(200, IANA);
    };
    const m = await fresh();
    const bases = await Promise.all([1, 2, 3, 4, 5].map(() => m.rdapBase("com")));
    check("5 concurrent first lookups all use IANA data", bases.every((b) => b === "https://iana-says.test/rdap/"), JSON.stringify(bases));
    check("bootstrap fetched exactly once", fetchCalls.length === 1, `${fetchCalls.length} fetches`);
    const bs = await Promise.all([m.loadBootstrap(), m.loadBootstrap()]);
    check("loadBootstrap callers get the parsed map", bs.every((b) => b.com === "https://iana-says.test/rdap/"), JSON.stringify(bs));
  }

  // ---- bootstrap failure: warns once, falls back to the built-in list for every caller
  {
    fetchCalls = [];
    const warnings = [];
    console.error = (...a) => warnings.push(a.join(" "));
    globalThis.fetch = async (url) => {
      fetchCalls.push(String(url));
      throw new Error("offline");
    };
    const m = await fresh();
    const bases = await Promise.all([m.rdapBase("com"), m.rdapBase("com"), m.rdapBase("io")]);
    console.error = realError;
    check("failed bootstrap falls back to the built-in .com server", bases[0] === "https://rdap.verisign.com/com/v1/" && bases[1] === bases[0], JSON.stringify(bases));
    check("failed bootstrap falls back to the built-in .io server", bases[2] === "https://rdap.identitydigital.services/rdap/", JSON.stringify(bases));
    check("failed bootstrap warns once", warnings.filter((w) => /bootstrap unavailable/.test(w)).length === 1, JSON.stringify(warnings));
    check("failed bootstrap is not refetched per caller", fetchCalls.length === 1, `${fetchCalls.length} fetches`);
  }

  // ---- npm: 404 is UNKNOWN (unpublished names 404 too), 200 is TAKEN
  {
    const m = await fresh();
    globalThis.fetch = async () => jsonRes(404, {});
    const r404 = await m.checkNpm("somename");
    check("npm 404 is UNKNOWN, not FREE", r404.status === "UNKNOWN", JSON.stringify(r404));
    check("npm 404 note says free or unpublished", /free or unpublished/.test(r404.note), JSON.stringify(r404));
    globalThis.fetch = async () => jsonRes(200, {});
    const r200 = await m.checkNpm("somename");
    check("npm 200 is TAKEN", r200.status === "TAKEN", JSON.stringify(r200));
  }

  // ---- withRetry
  {
    const m = await fresh();
    let calls = 0;
    const ok = await m.withRetry(async () => (++calls < 3 ? { retry: "flaky", waitMs: 1 } : { done: { status: "FREE", note: "" } }));
    check("withRetry returns the first done result", ok.status === "FREE" && calls === 3, `${JSON.stringify(ok)} after ${calls}`);
    calls = 0;
    const gaveUp = await m.withRetry(async () => (calls++, { retry: "still flaky", waitMs: 1 }));
    check("withRetry gives up as UNKNOWN, never FREE", gaveUp.status === "UNKNOWN" && /gave up after 4 tries/.test(gaveUp.note) && calls === 4, `${JSON.stringify(gaveUp)} after ${calls}`);
  }

  // ---- parseArgs
  {
    const m = await fresh();
    const o = m.parseArgs(["names.txt", "--skip", "hr,eu", "--extra", "CO,ai", "--no-github", "--concurrency", "3", "--out", "res"]);
    check("parseArgs reads input, skip, extra, flags", o.input === "names.txt" && o.skip.join() === "hr,eu" && o.extra.join() === "co,ai" && o.github === false && o.concurrency === 3 && o.out === "res", JSON.stringify(o));
    const d = m.parseArgs(["names.txt"]);
    check("parseArgs defaults", d.github === true && d.dns === true && d.concurrency === 5 && d.whoisGap === null, JSON.stringify(d));
  }

  // ---- readNames
  {
    const m = await fresh();
    const p = path.join(dir, "names.txt");
    fs.writeFileSync(p, "# comment\nAlpha\n\n beta \nalpha\ngamma-3\n");
    const warnings = [];
    console.error = (...a) => warnings.push(a.join(" "));
    const names = m.readNames(p);
    console.error = realError;
    check("readNames lowercases, trims, dedupes, skips comments", names.join() === "alpha,beta,gamma-3", names.join());
    check("readNames warns on the duplicate", warnings.some((w) => /duplicate name "alpha"/.test(w)), JSON.stringify(warnings));
  }
}

main()
  .catch((e) => {
    console.error = realError;
    console.log(`FAIL unexpected error: ${e.stack || e}`);
    failed++;
  })
  .finally(() => {
    globalThis.fetch = realFetch;
    fs.rmSync(dir, { recursive: true, force: true });
    if (failed) {
      console.log(`${failed} check(s) failed`);
      process.exit(1);
    }
    console.log("all checks passed");
  });
