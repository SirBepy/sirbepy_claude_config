// Shared playwright resolution + CLI/launch boilerplate for hs_preflight.cjs and hs_weekshot.cjs.
// See todo 288: a hardcoded npx-cache hash path vanishes on any cache eviction or playwright
// version bump. This resolves normally first, falls back to scanning the npx cache for the
// newest match, and only then fails, with the exact fix command in the message.
const fs = require('fs');
const path = require('path');
const os = require('os');

function findInNpxCache() {
  const npxCacheRoot = path.join(os.homedir(), 'AppData', 'Local', 'npm-cache', '_npx');
  if (!fs.existsSync(npxCacheRoot)) return null;
  const hits = fs.readdirSync(npxCacheRoot, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => path.join(npxCacheRoot, d.name, 'node_modules', 'playwright'))
    .filter(p => fs.existsSync(path.join(p, 'package.json')))
    .map(p => ({ p, mtime: fs.statSync(p).mtimeMs }))
    .sort((a, b) => b.mtime - a.mtime);
  return hits.length ? hits[0].p : null;
}

// Lazy on purpose: a usage-error exit (bad/missing args) should work even with playwright absent.
function getChromium() {
  try {
    return require('playwright').chromium;
  } catch {}
  const fallback = findInNpxCache();
  if (fallback) {
    try {
      return require(fallback).chromium;
    } catch {}
  }
  throw new Error(
    'playwright not found via normal require resolution or the npx cache ' +
    '(%LOCALAPPDATA%/npm-cache/_npx). Fix: run "npx --yes playwright install chromium" once to ' +
    'materialize a cache copy, or "npm install playwright" in scripts/ for a pinned local install.'
  );
}

function getArg(args, flag, def = null) {
  const i = args.indexOf(flag);
  return i !== -1 ? args[i + 1] : def;
}

async function launchProfileContext(profile) {
  fs.mkdirSync(profile, { recursive: true });
  return getChromium().launchPersistentContext(profile, { headless: false });
}

module.exports = { getChromium, getArg, launchProfileContext };
