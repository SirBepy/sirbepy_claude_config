#!/usr/bin/env node
// Name availability checker: domains (RDAP / port-43 whois + DNS cross-check), npm, GitHub.
// Node 20+, zero dependencies. See README-check.md for usage and the reliability of each signal.
//
// Statuses are exactly FREE, TAKEN, UNKNOWN. A lookup that fails (429, 5xx, timeout, odd answer)
// is retried with backoff and then reported as UNKNOWN, never as FREE.

import { readFileSync, writeFileSync, renameSync, existsSync } from 'node:fs';
import { dirname, basename, extname, join, resolve } from 'node:path';
import net from 'node:net';
import dns from 'node:dns';

const FREE = 'FREE';
const TAKEN = 'TAKEN';
const UNKNOWN = 'UNKNOWN';

const CORE_TLDS = ['com', 'hr', 'io', 'dev', 'app', 'eu'];
// .com and .hr dominate the score: a Croatian product needs .hr, and .com is the default
// destination for anyone typing the name.
const WEIGHTS = { com: 3, hr: 3, io: 1, dev: 1, app: 1, eu: 1 };
const UA = 'naming-availability-check/1.0 (personal name research, low volume)';
const MAX_CONCURRENCY = 5;
const MAX_TRIES = 4;

// Used when IANA's bootstrap file cannot be fetched, and for TLDs it does not list (.io is not in it
// although Identity Digital serves RDAP for it; verified 200/404 against google.io / a random string).
const FALLBACK_RDAP = {
  com: 'https://rdap.verisign.com/com/v1/',
  dev: 'https://pubapi.registry.google/rdap/',
  app: 'https://pubapi.registry.google/rdap/',
  io: 'https://rdap.identitydigital.services/rdap/',
  ai: 'https://rdap.identitydigital.services/rdap/',
};

// Per-host minimum gap (ms) where the default is too fast. Google's registry RDAP (.dev/.app) answers 429 after
// ~10 requests in ~8 s (measured from this machine), so one request per 1.1 s stays under it.
const HOST_GAP = { 'pubapi.registry.google': 1100 };

// TLDs without a reachable public RDAP server are asked over port-43 whois instead.
// .hr: whois.dns.hr (registered answer starts "Domain Name:", free answer is "%ERROR: No entries found").
// .eu: whois.eu (EURid's RDAP host does not resolve from here; free answer is "Status: AVAILABLE").
// .co: whois.registry.co ("DOMAIN NOT FOUND" when free).
// `gap` is the default minimum ms between queries to that server. whois.dns.hr answers
// "%ERROR: Too many requests" after about 9-10 queries inside ~75 s (measured from this machine) and
// refused connections entirely for ~10+ min after a burst with retries, hence the 10 s gap.
const WHOIS = {
  hr: { host: 'whois.dns.hr', gap: 10000, free: /No entries found/i, taken: /^Domain Name:\s*\S+/im, limited: /Too many requests/i },
  eu: {
    host: 'whois.eu',
    gap: 2000,
    free: /^Status:\s*AVAILABLE/im,
    taken: /^(Registrar:|Name servers:|Status:\s*(?!AVAILABLE)\S+)/im,
    limited: /rate|limit|too many|exceed|quota/i,
  },
  co: { host: 'whois.registry.co', gap: 1500, free: /DOMAIN NOT FOUND/i, taken: /^Domain Name:\s*\S+/im, limited: /rate|limit|too many|exceed|quota/i },
};

// ---------------------------------------------------------------- CLI

function die(msg) {
  console.error(`ERROR: ${msg}`);
  process.exit(1);
}

function parseArgs(argv) {
  const opts = {
    input: null,
    out: null,
    resume: null,
    extra: [],
    skip: [],
    github: true,
    dns: true,
    verbose: false,
    concurrency: MAX_CONCURRENCY,
    httpGap: 350,
    whoisGap: null, // null = per-server default from WHOIS
  };
  const need = (i, flag) => {
    if (i + 1 >= argv.length || argv[i + 1].startsWith('--')) die(`${flag} needs a value`);
    return argv[i + 1];
  };
  const num = (v, flag) => {
    const n = Number(v);
    if (!Number.isFinite(n) || n < 0) die(`${flag} must be a non-negative number, got "${v}"`);
    return n;
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--help' || a === '-h') {
      console.log('Usage: node check-availability.mjs <names.txt> [--out prefix] [--resume cache.json] [--extra co,ai]');
      console.log('       [--skip hr,eu] [--no-github] [--no-dns] [--concurrency 1-5] [--delay ms] [--whois-delay ms]');
      process.exit(0);
    } else if (a === '--out') opts.out = need(i++, a);
    else if (a === '--resume') opts.resume = need(i++, a);
    else if (a === '--extra') opts.extra = need(i++, a).split(',').map((s) => s.trim().toLowerCase()).filter(Boolean);
    else if (a === '--skip') opts.skip = need(i++, a).split(',').map((s) => s.trim().toLowerCase()).filter(Boolean);
    else if (a === '--no-github') opts.github = false;
    else if (a === '--no-dns') opts.dns = false;
    else if (a === '--verbose') opts.verbose = true;
    else if (a === '--concurrency') opts.concurrency = num(need(i++, a), a);
    else if (a === '--delay') opts.httpGap = num(need(i++, a), a);
    else if (a === '--whois-delay') opts.whoisGap = num(need(i++, a), a);
    else if (a.startsWith('--')) die(`unknown flag ${a}`);
    else if (opts.input === null) opts.input = a;
    else die(`unexpected extra argument "${a}"`);
  }
  if (!opts.input) die('missing input file. Usage: node check-availability.mjs <names.txt> [options]');
  if (opts.concurrency < 1 || opts.concurrency > MAX_CONCURRENCY || !Number.isInteger(opts.concurrency)) {
    die(`--concurrency must be an integer 1..${MAX_CONCURRENCY}`);
  }
  for (const t of opts.extra) {
    if (!['co', 'ai'].includes(t)) die(`--extra supports only co and ai, got "${t}"`);
  }
  for (const t of opts.skip) {
    if (!CORE_TLDS.includes(t)) die(`--skip supports only ${CORE_TLDS.join(', ')}, got "${t}"`);
  }
  return opts;
}

function readNames(path) {
  if (!existsSync(path)) die(`input file not found: ${path}`);
  const raw = readFileSync(path, 'utf8');
  if (raw.charCodeAt(0) === 0xfeff) die('input file starts with a UTF-8 BOM; save it without BOM');
  const names = [];
  const seen = new Set();
  const bad = [];
  raw.split(/\r?\n/).forEach((line, idx) => {
    const t = line.trim();
    if (t === '' || t.startsWith('#')) return;
    const n = t.toLowerCase();
    // A DNS label: ASCII letters, digits, inner hyphens, max 63 chars. Anything else (spaces,
    // diacritics, dots, underscores) would silently probe a different name than intended.
    if (!/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(n)) {
      bad.push(`line ${idx + 1}: "${t}"`);
      return;
    }
    if (n.includes('--')) {
      bad.push(`line ${idx + 1}: "${t}" (double hyphen is reserved for punycode in domains)`);
      return;
    }
    if (seen.has(n)) {
      console.error(`warning: duplicate name "${n}" on line ${idx + 1} ignored`);
      return;
    }
    seen.add(n);
    names.push(n);
  });
  if (bad.length) die(`malformed input, expected one ASCII name per line ([a-z0-9-], 1-63 chars):\n  ${bad.join('\n  ')}`);
  if (names.length === 0) die('input file contains no names');
  return names;
}

// ---------------------------------------------------------------- utilities

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const jitter = (ms) => ms * (0.85 + Math.random() * 0.4);

// Starts requests to one host at least `gap` ms apart and keeps at most `maxInflight` open.
// A 429 widens the gap for the rest of the run (adaptive politeness).
class Gate {
  constructor(gap, maxInflight) {
    this.gap = gap;
    this.baseGap = gap;
    this.streak = 0;
    this.maxInflight = maxInflight;
    this.inflight = 0;
    this.waiters = [];
    this.nextStart = 0;
  }
  async acquire() {
    while (this.inflight >= this.maxInflight) await new Promise((r) => this.waiters.push(r));
    this.inflight++;
    const now = Date.now();
    const start = Math.max(now, this.nextStart);
    this.nextStart = start + jitter(this.gap);
    if (start > now) await sleep(start - now);
  }
  release() {
    this.inflight--;
    const w = this.waiters.shift();
    if (w) w();
  }
  backoff() {
    this.streak = 0;
    this.gap = Math.min(Math.max(this.gap * 2, 500), 20000);
    this.pause(5000);
  }
  // After a calm stretch, relax a widened gap back toward the base so one 429 does not slow the whole run.
  ok() {
    if (++this.streak >= 15 && this.gap > this.baseGap) {
      this.gap = Math.max(this.baseGap, this.gap / 2);
      this.streak = 0;
    }
  }
  // Server said slow down: nobody starts a request to this host for `ms`.
  pause(ms) {
    this.nextStart = Math.max(this.nextStart, Date.now() + ms);
  }
}

// Counting semaphore: the hard cap on requests in flight across all hosts.
class Semaphore {
  constructor(n) {
    this.free = n;
    this.waiters = [];
  }
  async take() {
    while (this.free <= 0) await new Promise((r) => this.waiters.push(r));
    this.free--;
  }
  give() {
    this.free++;
    const w = this.waiters.shift();
    if (w) w();
  }
}

const gates = new Map();
let httpGap = 350;
let global = new Semaphore(MAX_CONCURRENCY);
function gateFor(host, gap, maxInflight) {
  if (!gates.has(host)) gates.set(host, new Gate(gap, maxInflight));
  return gates.get(host);
}

// Order matters: wait for the host's turn first, only then take a global slot, so a request that
// is merely queued behind a slow host (whois.dns.hr) does not occupy one of the 5 in-flight slots.
async function gated(host, gap, maxInflight, fn) {
  const g = gateFor(host, gap, maxInflight);
  await g.acquire();
  await global.take();
  try {
    return await fn(g);
  } finally {
    global.give();
    g.release();
  }
}

// fn() returns {done: result} or {retry: note, waitMs?}. After MAX_TRIES the last note is returned
// as an UNKNOWN result, so a flaky server can never look like an available name.
async function withRetry(fn) {
  let note = '';
  for (let attempt = 1; attempt <= MAX_TRIES; attempt++) {
    const r = await fn();
    if (r.done) return r.done;
    note = r.retry;
    if (attempt < MAX_TRIES) await sleep(jitter(r.waitMs ?? 2000 * 2 ** (attempt - 1)));
  }
  return { status: UNKNOWN, note: `${note} (gave up after ${MAX_TRIES} tries)` };
}

async function httpStatus(host, url, { method = 'GET', headers = {}, redirect = 'follow' } = {}) {
  return gated(host, HOST_GAP[host] ?? httpGap, HOST_GAP[host] ? 1 : 2, async (gate) => {
    try {
      const res = await fetch(url, {
        method,
        redirect,
        headers: { 'user-agent': UA, ...headers },
        signal: AbortSignal.timeout(15000),
      });
      if (method !== 'HEAD') await res.arrayBuffer().catch(() => {});
      if (res.status === 429) gate.backoff();
      else gate.ok();
      return { status: res.status, retryAfter: Number(res.headers.get('retry-after')) };
    } catch (e) {
      return { status: 0, error: e.cause?.code || e.name || String(e) };
    }
  });
}

function retryWait(r) {
  return Number.isFinite(r.retryAfter) && r.retryAfter > 0 ? Math.min(r.retryAfter * 1000, 30000) : undefined;
}

// ---------------------------------------------------------------- domains

let bootstrap = null;
async function loadBootstrap() {
  if (bootstrap) return bootstrap;
  bootstrap = {};
  try {
    const res = await fetch('https://data.iana.org/rdap/dns.json', {
      headers: { 'user-agent': UA },
      signal: AbortSignal.timeout(15000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const j = await res.json();
    for (const [tlds, urls] of j.services) {
      const url = urls.find((u) => u.startsWith('https://')) || urls[0];
      for (const t of tlds) bootstrap[t.toLowerCase()] = url;
    }
  } catch (e) {
    console.error(`warning: IANA RDAP bootstrap unavailable (${e.message}); using built-in server list`);
  }
  return bootstrap;
}

async function rdapBase(tld) {
  const b = await loadBootstrap();
  const base = b[tld] || FALLBACK_RDAP[tld];
  return base ? base.replace(/\/?$/, '/') : null;
}

async function rdapLookup(domain, tld) {
  const base = await rdapBase(tld);
  if (!base) return { status: UNKNOWN, note: `no RDAP server known for .${tld}` };
  const url = `${base}domain/${domain}`;
  const host = new URL(url).host;
  return withRetry(async () => {
    const r = await httpStatus(host, url, { headers: { accept: 'application/rdap+json, application/json' } });
    if (r.status === 404) return { done: { status: FREE, note: '' } };
    if (r.status === 200) return { done: { status: TAKEN, note: '' } };
    if (r.status === 0) return { retry: `RDAP network error ${r.error}` };
    if (r.status === 429 || r.status >= 500) return { retry: `RDAP HTTP ${r.status}`, waitMs: retryWait(r) };
    return { done: { status: UNKNOWN, note: `RDAP unexpected HTTP ${r.status}` } };
  });
}

function whoisRaw(host, query) {
  return new Promise((resolveP, reject) => {
    const s = net.connect({ host, port: 43 });
    let buf = '';
    s.setEncoding('utf8');
    s.setTimeout(15000, () => s.destroy(new Error('timeout')));
    s.on('connect', () => s.write(`${query}\r\n`));
    s.on('data', (d) => {
      buf += d;
      if (buf.length > 200000) s.destroy();
    });
    s.on('error', reject);
    s.on('close', () => resolveP(buf));
  });
}

async function whoisLookup(domain, tld) {
  const cfg = WHOIS[tld];
  const gap = whoisGapOverride ?? cfg.gap;
  return withRetry(async () => {
    let text;
    let gate;
    try {
      text = await gated(cfg.host, gap, 1, async (g) => {
        gate = g;
        return whoisRaw(cfg.host, domain);
      });
    } catch (e) {
      // Connect timeouts are what a temporary IP block looks like: wait long instead of hammering.
      gate?.pause(30000);
      return { retry: `whois ${cfg.host} error ${e.code || e.message}`, waitMs: 30000 };
    }
    // Taken is tested first: a registered answer must never be read as free because of a stray phrase.
    if (cfg.taken.test(text)) return { done: { status: TAKEN, note: '' } };
    if (cfg.free.test(text)) return { done: { status: FREE, note: '' } };
    const limited = cfg.limited.test(text);
    // Their window is ~75 s; every queued query to the same server also waits it out.
    gateFor(cfg.host, gap, 1).pause(limited ? 75000 : 5000);
    return { retry: `whois ${cfg.host} ${limited ? 'rate-limited' : 'unrecognised answer'}`, waitMs: limited ? 75000 : 5000 };
  });
}

let whoisGapOverride = null;
const resolver = new dns.promises.Resolver({ timeout: 4000, tries: 2 });

// 'present' = a zone/delegation exists, 'absent' = authoritative nothing, 'error' = no usable answer.
async function dnsSignal(domain) {
  const absent = new Set(['ENOTFOUND', 'ENODATA', 'NXDOMAIN']);
  let sawError = false;
  for (const fn of [() => resolver.resolveNs(domain), () => resolver.resolveSoa(domain)]) {
    try {
      await global.take();
      const r = await fn().finally(() => global.give());
      if (r && (!Array.isArray(r) || r.length)) return 'present';
    } catch (e) {
      if (!absent.has(e.code)) sawError = true;
    }
  }
  return sawError ? 'error' : 'absent';
}

async function checkDomain(name, tld, useDns) {
  const domain = `${name}.${tld}`;
  let sig = null;
  if (WHOIS[tld] && useDns) {
    // Whois servers ration queries (.hr allows ~9 per 75 s), so spend none on names whose NS
    // records already prove they are registered.
    sig = await dnsSignal(domain);
    if (sig === 'present') return { status: TAKEN, note: 'NS/SOA exist (whois skipped)' };
  }
  const reg = WHOIS[tld] ? await whoisLookup(domain, tld) : await rdapLookup(domain, tld);
  const src = WHOIS[tld] ? 'whois' : 'RDAP';
  if (reg.status === TAKEN) return reg;
  if (!useDns) return reg;
  sig ??= await dnsSignal(domain);
  if (reg.status === FREE) {
    if (sig === 'present') {
      return { status: TAKEN, note: `no ${src} record but NS/SOA exist (taken or parked)` };
    }
    if (sig === 'error') return { status: FREE, note: 'DNS cross-check failed' };
    return reg;
  }
  // registry lookup failed: DNS can only prove "taken", never "free"
  if (sig === 'present') return { status: TAKEN, note: `${reg.note}; NS/SOA exist` };
  return reg;
}

// ---------------------------------------------------------------- npm / GitHub

async function checkNpm(name) {
  const url = `https://registry.npmjs.org/${name}`;
  return withRetry(async () => {
    const r = await httpStatus('registry.npmjs.org', url, {
      headers: { accept: 'application/vnd.npm.install-v1+json' },
    });
    if (r.status === 404) return { done: { status: FREE, note: '' } };
    if (r.status === 200) return { done: { status: TAKEN, note: '' } };
    if (r.status === 0) return { retry: `npm network error ${r.error}` };
    if (r.status === 429 || r.status >= 500) return { retry: `npm HTTP ${r.status}`, waitMs: retryWait(r) };
    return { done: { status: UNKNOWN, note: `npm unexpected HTTP ${r.status}` } };
  });
}

async function checkGithub(name) {
  // HEAD without redirect-following: a 301 means the account exists under another capitalisation.
  const url = `https://github.com/${name}`;
  return withRetry(async () => {
    const r = await httpStatus('github.com', url, { method: 'HEAD', redirect: 'manual' });
    if (r.status === 404) return { done: { status: FREE, note: '' } };
    if (r.status === 200 || (r.status >= 301 && r.status <= 308)) return { done: { status: TAKEN, note: '' } };
    if (r.status === 0) return { retry: `github network error ${r.error}` };
    if (r.status === 429 || r.status >= 500) return { retry: `github HTTP ${r.status}`, waitMs: retryWait(r) };
    return { done: { status: UNKNOWN, note: `github unexpected HTTP ${r.status}` } };
  });
}

// ---------------------------------------------------------------- cache

function loadCache(path) {
  if (!path || !existsSync(path)) return {};
  let data;
  try {
    data = JSON.parse(readFileSync(path, 'utf8'));
  } catch (e) {
    // Not overwritten: a corrupt cache is the user's data, not ours to replace silently.
    die(`resume cache ${path} is not valid JSON (${e.message}); fix or delete it`);
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) die(`resume cache ${path} must be a JSON object`);
  return data;
}

function saveCache(path, cache) {
  if (!path) return;
  const tmp = `${path}.tmp`;
  writeFileSync(tmp, JSON.stringify(cache, null, 1));
  renameSync(tmp, path);
}

// ---------------------------------------------------------------- output

const csvCell = (v) => {
  const s = String(v ?? '');
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};
const mdCell = (v) => String(v ?? '').replace(/\|/g, '\\|');

function render(rows, cols) {
  const head = [...cols, 'score', 'notes'];
  const md = [
    `| name | ${head.slice(1).join(' | ')} |`,
    `|${head.map(() => '---').join('|')}|`,
    ...rows.map((r) => `| ${[r.name, ...cols.slice(1).map((c) => r[c]), r.score, r.notes].map(mdCell).join(' | ')} |`),
  ].join('\n');
  const csv = [
    head.join(','),
    ...rows.map((r) => [r.name, ...cols.slice(1).map((c) => r[c]), r.score, r.notes].map(csvCell).join(',')),
  ].join('\n');
  return { md, csv: `${csv}\n` };
}

// ---------------------------------------------------------------- main

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  httpGap = opts.httpGap;
  whoisGapOverride = opts.whoisGap;
  global = new Semaphore(opts.concurrency);
  const inputPath = resolve(opts.input);
  const names = readNames(inputPath);
  const outPrefix = resolve(
    opts.out || join(dirname(inputPath), `${basename(inputPath, extname(inputPath))}.results`),
  );
  const resumePath = opts.resume ? resolve(opts.resume) : null;
  const cache = loadCache(resumePath);

  // --skip drops a core TLD from the run (the .hr and .eu whois lanes are the slow ones); the score then counts only the TLDs checked.
  const tlds = [...CORE_TLDS.filter((t) => !opts.skip.includes(t)), ...opts.extra];
  const kinds = [...tlds, 'npm', ...(opts.github ? ['github'] : [])];
  const results = new Map(); // `${kind}:${name}` -> {status, note}
  const queue = [];
  for (const name of names) {
    for (const kind of kinds) {
      const key = `${kind}:${name}`;
      if (cache[key]) results.set(key, cache[key]);
      else queue.push({ name, kind, key });
    }
  }
  const total = queue.length;
  console.error(`${names.length} names, ${kinds.length} checks each, ${results.size} from cache, ${total} to run`);

  let done = 0;
  let sinceSave = 0;
  const started = Date.now();
  const flush = () => saveCache(resumePath, cache);
  process.on('SIGINT', () => {
    flush();
    console.error('\ninterrupted, cache saved');
    process.exit(130);
  });

  async function runTask(t) {
    let r;
    const t0 = Date.now();
    try {
      if (t.kind === 'npm') r = await checkNpm(t.name);
      else if (t.kind === 'github') r = await checkGithub(t.name);
      else r = await checkDomain(t.name, t.kind, opts.dns);
    } catch (e) {
      r = { status: UNKNOWN, note: `unexpected error ${e.message}` };
    }
    results.set(t.key, r);
    if (opts.verbose) console.error(`    ${t.key} ${r.status} ${Date.now() - t0}ms ${r.note}`);
    // Only conclusive answers are cached, so a resumed run retries every UNKNOWN.
    if (r.status !== UNKNOWN) {
      cache[t.key] = r;
      if (++sinceSave >= 10) {
        flush();
        sinceSave = 0;
      }
    }
    done++;
    if (done % 10 === 0 || done === total) {
      const s = Math.round((Date.now() - started) / 1000);
      console.error(`  ${done}/${total} checks (${s}s)`);
    }
  }

  // Rationed whois servers get their own lane so their long waits never stall the fast checks.
  // Lanes are only a scheduling aid: the global semaphore still caps requests in flight at --concurrency.
  const lanes = new Map();
  for (const t of queue) {
    const lane = WHOIS[t.kind] ? t.kind : 'fast';
    if (!lanes.has(lane)) lanes.set(lane, []);
    lanes.get(lane).push(t);
  }
  const workers = [];
  for (const [lane, items] of lanes) {
    let cursor = 0;
    const worker = async () => {
      while (cursor < items.length) await runTask(items[cursor++]);
    };
    const n = lane === 'fast' ? Math.min(opts.concurrency, items.length) : 1;
    for (let i = 0; i < n; i++) workers.push(worker());
  }
  await Promise.all(workers);
  flush();

  const rows = names.map((name) => {
    const row = { name };
    const notes = [];
    for (const kind of kinds) {
      const r = results.get(`${kind}:${name}`);
      row[kind] = r.status;
      if (r.note) notes.push(`${kind}: ${r.note}`);
    }
    row.score = CORE_TLDS.reduce((s, t) => s + (row[t] === FREE ? WEIGHTS[t] : 0), 0);
    row.notes = notes.join('; ');
    return row;
  });
  rows.sort((a, b) => b.score - a.score || a.name.localeCompare(b.name));

  const cols = ['name', ...kinds];
  const { md, csv } = render(rows, cols);
  console.log(md);
  writeFileSync(`${outPrefix}.csv`, csv);
  writeFileSync(
    `${outPrefix}.json`,
    JSON.stringify(
      {
        generatedAt: new Date().toISOString(),
        input: inputPath,
        scoring: `sum of weights of FREE among ${CORE_TLDS.join('/')} (weights ${JSON.stringify(WEIGHTS)}, max ${Object.values(WEIGHTS).reduce((a, b) => a + b, 0)})`,
        rows,
      },
      null,
      2,
    ),
  );

  const unknown = rows.reduce((n, r) => n + kinds.filter((k) => r[k] === UNKNOWN).length, 0);
  console.error(`\nwrote ${outPrefix}.csv and ${outPrefix}.json in ${Math.round((Date.now() - started) / 1000)}s`);
  if (unknown) console.error(`${unknown} UNKNOWN cell(s): rerun with --resume to retry only those`);
}

main().catch((e) => die(e.stack || String(e)));
