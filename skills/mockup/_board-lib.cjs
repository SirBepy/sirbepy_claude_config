// Shared by bundle-board.mjs (via createRequire) and verify-board.cjs: the two scripts must agree on
// which vite entry they load and on which literals the preview panel's </body> splice cannot survive.

// Absolute path of the vite ESM entry, given a require() rooted at the web project. Importing the
// ESM entry directly avoids the deprecation warning the CJS entry prints on vite 5+.
function resolveViteEsm(req) {
  const fs = require("node:fs");
  const path = require("node:path");
  const pkgPath = req.resolve("vite/package.json");
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
  const root = pkg.exports && pkg.exports["."];
  const esm = root && (typeof root === "string" ? root : typeof root.import === "string" ? root.import : root.import && root.import.default);
  return path.resolve(path.dirname(pkgPath), esm || pkg.module || pkg.main);
}

// The preview panel splices a diagnostics script into the raw text at </body>; these literals in an
// inline script, style or comment corrupt the pushed page. Returns [{ kind, literal }] per offending block.
function lintLiterals(html) {
  const blocks = [
    ...[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => ["script", m[1]]),
    ...[...html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => ["style", m[1]]),
    ...[...html.matchAll(/<!--([\s\S]*?)-->/g)].map((m) => ["comment", m[1]]),
  ];
  const bad = [];
  for (const [kind, body] of blocks) {
    const hit = /<\/body>|<head[\s>/]|<html[\s>/]/i.exec(body);
    if (hit) bad.push({ kind, literal: hit[0] });
  }
  return bad;
}

module.exports = { resolveViteEsm, lintLiterals };
