// Bundles an interactive /mockup board (<name>.src.html + the .ts it imports, which may pull in
// the project's REAL modules and CSS) into ONE self-contained HTML file with JS and CSS inlined,
// ready for verify-board.cjs and a /preview push.
//
//   node bundle-board.mjs <src.html> <out.html> [--project <dir>]
//
// vite is resolved from the web project being mocked (--project, else env BOARD_PROJECT, else the
// current directory), never from ~/.claude: the board must build with the same vite and the same
// node_modules as the real app. Run from the project root or pass --project.
import { createRequire } from "node:module";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve, relative, join } from "node:path";
import { pathToFileURL } from "node:url";

function usage(msg) {
  if (msg) console.error(`bundle-board: ${msg}`);
  console.error("usage: node bundle-board.mjs <src.html> <out.html> [--project <dir>]");
  process.exit(2);
}

const args = process.argv.slice(2);
let projectArg = process.env.BOARD_PROJECT || "";
const positional = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--project") projectArg = args[++i] || usage("--project needs a directory");
  else positional.push(args[i]);
}
if (positional.length !== 2) usage();
const src = resolve(positional[0]);
const outFile = resolve(positional[1]);
const project = resolve(projectArg || process.cwd());

// Resolve vite relative to the project and import its ESM entry directly (the CJS entry prints a
// deprecation warning on vite 5+).
async function loadVite() {
  let req;
  try {
    req = createRequire(join(project, "package.json"));
    const pkgPath = req.resolve("vite/package.json");
    const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));
    const root = pkg.exports && pkg.exports["."];
    const esm = root && (typeof root === "string" ? root : typeof root.import === "string" ? root.import : root.import && root.import.default);
    const rel = esm || pkg.module || pkg.main;
    return await import(pathToFileURL(resolve(dirname(pkgPath), rel)).href);
  } catch (e) {
    if (req) {
      try { return await import(pathToFileURL(req.resolve("vite")).href); } catch {}
    }
    console.error(
      `bundle-board: cannot resolve "vite" from ${project} (${e.code || e.message}).\n` +
      "Run from the web project root, or pass --project <dir> / set BOARD_PROJECT to a directory\n" +
      "whose node_modules has vite. Nothing is installed for you."
    );
    process.exit(3);
  }
}

const { build } = await loadVite();
const root = dirname(src);

const result = await build({
  configFile: false,
  root,
  base: "./",
  logLevel: "warn",
  build: {
    write: false,
    assetsInlineLimit: 100_000_000,
    cssCodeSplit: false,
    modulePreload: false,
    rollupOptions: {
      input: src,
      output: { inlineDynamicImports: true },
    },
  },
});
const outputs = (Array.isArray(result) ? result : [result]).flatMap((r) => r.output);

const htmlName = relative(root, src).replace(/\\/g, "/");
const htmlAsset = outputs.find((o) => o.type === "asset" && o.fileName === htmlName);
if (!htmlAsset) {
  console.error(`bundle-board: vite produced no ${htmlName}; got ${outputs.map((o) => o.fileName).join(", ")}`);
  process.exit(1);
}
const byName = new Map(outputs.map((o) => [o.fileName, o]));
const text = (o) => (o.type === "chunk" ? o.code : Buffer.from(o.source).toString("utf8"));
const lookup = (ref) => byName.get(ref.replace(/^\.\//, "").replace(/^\//, ""));

// A literal </script, <!--, </body>, <head or <html inside inline JS breaks the document or the
// preview panel's text splice; \x3C is the same character inside a JS string, regex or template.
const escapeInline = (js) =>
  js.replace(/<(\/script|\/body>|!--|(?:head|html)(?=[\s>/]))/gi, "\\x3C$1");

let html = Buffer.from(htmlAsset.source).toString("utf8");
html = html.replace(/<script\b[^>]*\bsrc="([^"]+)"[^>]*><\/script>/g, (tag, ref) => {
  const chunk = lookup(ref);
  if (!chunk) return tag;
  const type = /\btype="module"/.test(tag) ? ' type="module"' : "";
  return `<script${type}>${escapeInline(text(chunk))}</script>`;
});
html = html.replace(/<link\b[^>]*\brel="stylesheet"[^>]*\bhref="([^"]+)"[^>]*>/g, (tag, ref) => {
  const css = lookup(ref);
  return css ? `<style>${escapeInline(text(css))}</style>` : tag;
});

// Anything still external would 404 inside the panel's opaque-origin sandbox.
const leftovers = [...html.matchAll(/<(?:script|link)\b[^>]*\b(?:src|href)="(\.\/[^"]+)"/g)].map((m) => m[1]);
if (leftovers.length) {
  console.error(`bundle-board: board still references local files after inlining: ${leftovers.join(", ")}`);
  process.exit(1);
}

// Hand-written classic inline scripts in the .src.html are not run through vite, so lint them too.
const blocks = [
  ...[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => ["script", m[1]]),
  ...[...html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => ["style", m[1]]),
  ...[...html.matchAll(/<!--([\s\S]*?)-->/g)].map((m) => ["comment", m[1]]),
];
const bad = [];
for (const [kind, body] of blocks) {
  const hit = /<\/body>|<head[\s>/]|<html[\s>/]/i.exec(body);
  if (hit) bad.push(`${kind} contains literal "${hit[0]}"`);
}
if (bad.length) {
  console.error(
    `bundle-board: ${bad.join("; ")}.\nThe preview panel splices a diagnostics script into the raw text at </body>, ` +
    "so these literals corrupt the pushed page. Build the string at runtime, e.g. '<' + '/body>'."
  );
  process.exit(1);
}

mkdirSync(dirname(outFile), { recursive: true });
writeFileSync(outFile, html);
console.log(`${outFile} ${Math.round(html.length / 1024)}KB`);
