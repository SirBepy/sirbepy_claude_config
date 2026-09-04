// Resolves a real playwright chromium launcher: normal require first, then the newest npx-cache
// build whose chromium binary actually exists under ms-playwright, else throws naming the exact
// cli.js install command for the build it picked. See todo 295 (hardcoded hash paths vanish on
// cache eviction) and todo 900 (newest mtime alone can pick a browser-less build).
const fs = require('fs');
const path = require('path');
const os = require('os');

function msPlaywrightRoot() {
  return path.join(os.homedir(), 'AppData', 'Local', 'ms-playwright');
}

// Chromium revision folders actually present on disk, e.g. ["1208", "1228", "1234"].
function presentRevisions() {
  const root = msPlaywrightRoot();
  if (!fs.existsSync(root)) return [];
  return fs.readdirSync(root)
    .map(name => /^chromium(?:_headless_shell)?-(\d+)$/.exec(name))
    .filter(Boolean)
    .map(m => m[1]);
}

function revisionOf(exePath) {
  const m = /chromium(?:_headless_shell)?-(\d+)/.exec(exePath || '');
  return m ? m[1] : 'unknown';
}

function candidatesInNpxCache() {
  const npxCacheRoot = path.join(os.homedir(), 'AppData', 'Local', 'npm-cache', '_npx');
  if (!fs.existsSync(npxCacheRoot)) return [];
  return fs.readdirSync(npxCacheRoot, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => path.join(npxCacheRoot, d.name, 'node_modules', 'playwright'))
    .filter(p => fs.existsSync(path.join(p, 'package.json')))
    .map(p => ({ p, mtime: fs.statSync(p).mtimeMs }))
    .sort((a, b) => b.mtime - a.mtime);
}

// Walks newest-first, skipping any candidate whose resolved chromium executable is missing.
function findInNpxCache() {
  for (const { p } of candidatesInNpxCache()) {
    try {
      const exe = require(p).chromium.executablePath();
      if (exe && fs.existsSync(exe)) return p;
    } catch {}
  }
  return null;
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
  const hits = candidatesInNpxCache();
  if (hits.length) {
    const newest = hits[0].p;
    let exe;
    try { exe = require(newest).chromium.executablePath(); } catch {}
    const present = presentRevisions();
    throw new Error(
      `playwright resolved to ${newest} but its chromium revision (${revisionOf(exe)}) is not ` +
      `installed. Revisions present under ms-playwright: ${present.length ? present.join(', ') : 'none'}. ` +
      `Fix: node "${path.join(newest, 'cli.js')}" install chromium`
    );
  }
  throw new Error(
    'playwright not found via normal require resolution or the npx cache ' +
    '(%LOCALAPPDATA%/npm-cache/_npx). Fix: run "npx --yes playwright install chromium" once to ' +
    'materialize a cache copy, or "npm install playwright" in scripts/ for a pinned local install.'
  );
}

// Google returns "this browser isn't secure" for ANY WebDriver-controlled sign-in, regardless of
// account or profile freshness (confirmed 2026-08-27, todo 816). Callers driving an interactive
// human login should check the target URL here before launching, so the flow fails fast instead
// of burning a browser launch and an OTP round trip.
const AUTOMATION_BLOCKED_LOGIN_HOSTS = new Set(['accounts.google.com']);

function isKnownAutomationLoginBlock(targetUrl) {
  try {
    return AUTOMATION_BLOCKED_LOGIN_HOSTS.has(new URL(targetUrl).hostname);
  } catch {
    return false;
  }
}

function assertNoAutomationLoginBlock(targetUrl) {
  if (!isKnownAutomationLoginBlock(targetUrl)) return;
  throw new Error(
    `${targetUrl} is a Google sign-in page: Google blocks ANY WebDriver-controlled browser from ` +
    'signing in, regardless of account or profile freshness. Skip the automated browser - have the ' +
    'dev log in through their own regular browser, and handle only the mechanical parts (target ' +
    'URL, resulting credentials, config writes).'
  );
}

module.exports = {
  getChromium,
  findInNpxCache,
  isKnownAutomationLoginBlock,
  assertNoAutomationLoginBlock,
};
