#!/usr/bin/env node
// /context-left - report remaining context window for the CURRENT claude session.
// PRIMARY: the daemon's authoritative /context endpoint (single source of truth,
// shared with the claude_usage_in_taskbar app chip - fix the math in ONE place).
// FALLBACK: self-compute from this session's own transcript when the daemon is
// unreachable (covers non-daemon instances and pre-endpoint daemon binaries).
// No network beyond localhost, read-only.

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const SESSION_ID = process.env.CLAUDE_CODE_SESSION_ID || null;
const DAEMON_URL = "http://127.0.0.1:27182/context";
const PROJECTS = join(homedir(), ".claude", "projects");

function human(n) {
  n = Number(n) || 0;
  if (n >= 1000000) return (n / 1000000).toFixed(n % 1000000 === 0 ? 0 : 1).replace(/\.0$/, "") + "M";
  if (n >= 1000) return Math.round(n / 1000) + "K";
  return String(n);
}

function printStatus(s) {
  const pctLeft = s.pctLeft;
  const filled = Math.max(0, Math.min(10, Math.round((pctLeft / 100) * 10)));
  const bar = "#".repeat(filled) + "-".repeat(10 - filled);
  const approx = s.confidence && s.confidence !== "proven" ? "~" : "";
  const modelShort = (s.model || "unknown").replace(/^claude-/, "");
  console.log(`context left: ${approx}${human(s.remaining)} / ${human(s.window)} (${approx}${pctLeft}%)  [${bar}]  ${modelShort}`);
  if (s.note) console.log(`   note: ${s.note}`);
  if (s.warning) console.log(`   warning: ${s.warning}`);
}

// ---- PRIMARY: daemon endpoint (single source of truth) ----
async function fromDaemon() {
  if (!SESSION_ID || typeof fetch !== "function") return null;
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1200);
    const res = await fetch(`${DAEMON_URL}?session_id=${encodeURIComponent(SESSION_ID)}`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (!res.ok) return null;
    const s = await res.json();
    if (s == null || typeof s.window !== "number") return null;
    const window = Number(s.window);
    const remaining = Number(s.remaining);
    return {
      remaining,
      window,
      pctLeft: typeof s.pct_left === "number" ? s.pct_left : Math.round((remaining / window) * 100),
      model: s.model,
      confidence: s.confidence,
      note: s.confidence && s.confidence !== "proven"
        ? "window is a heuristic (no definitive 200K-vs-1M signal); ~ marks an estimate"
        : "",
    };
  } catch {
    return null;
  }
}

// ---- FALLBACK: self-compute from this session's transcript ----
function safeReaddir(p) { try { return readdirSync(p); } catch { return []; } }

function findTranscript(sessionId) {
  if (!existsSync(PROJECTS)) return null;
  if (sessionId) {
    for (const dir of safeReaddir(PROJECTS)) {
      const p = join(PROJECTS, dir, `${sessionId}.jsonl`);
      if (existsSync(p)) return { path: p, exact: true };
    }
  }
  let newest = null, newestM = 0;
  for (const dir of safeReaddir(PROJECTS)) {
    const d = join(PROJECTS, dir);
    for (const f of safeReaddir(d)) {
      if (!f.endsWith(".jsonl")) continue;
      const p = join(d, f);
      let m; try { m = statSync(p).mtimeMs; } catch { continue; }
      if (m > newestM) { newestM = m; newest = p; }
    }
  }
  return newest ? { path: newest, exact: false } : null;
}

// Scan ALL usage lines: current occupancy = last line, max occupancy = sticky-correction input.
function scanUsage(path) {
  const lines = readFileSync(path, "utf8").split("\n");
  let current = null, maxOcc = 0, model = null;
  for (const raw of lines) {
    const ln = raw.trim();
    if (!ln || !ln.includes('"usage"')) continue;
    let o; try { o = JSON.parse(ln); } catch { continue; }
    const msg = o && o.message;
    const u = msg && msg.usage;
    if (!u || typeof u.input_tokens !== "number") continue;
    const occ = (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0);
    current = occ;
    if (occ > maxOcc) maxOcc = occ;
    if (msg.model || o.model) model = msg.model || o.model;
  }
  return current == null ? null : { current, maxOcc, model };
}

function windowFor(model, maxOcc) {
  let win, confidence = "heuristic";
  if (model && /claude-3[^0-9]*opus/i.test(model)) win = 200000;
  else if (model && /opus/i.test(model)) win = 1000000;
  else win = 200000;
  // sticky correction: any turn exceeding 200K proves the real window is >= 1M.
  if (maxOcc > 200000) { win = Math.max(win, 1000000); confidence = "proven"; }
  return { win, confidence };
}

function selfCompute() {
  const t = findTranscript(SESSION_ID);
  if (!t) { console.log("context-left: could not locate this session's transcript under ~/.claude/projects"); return false; }
  const scan = scanUsage(t.path);
  if (!scan) { console.log("context-left: no usage data yet (no completed turn in this session)"); return false; }
  const { win, confidence } = windowFor(scan.model, scan.maxOcc);
  // remaining is driven by `current` (this turn's occupancy), not `maxOcc`: after a
  // context compaction the live window genuinely shrinks, so the latest line is right.
  const remaining = Math.max(0, win - scan.current);
  // Be precise about WHY we fell back to the newest transcript - the two causes are different.
  let warning = "";
  if (!t.exact) {
    warning = SESSION_ID
      ? `CLAUDE_CODE_SESSION_ID=${SESSION_ID} set but no matching transcript found; used newest instead - may be a different session`
      : "CLAUDE_CODE_SESSION_ID unset; used newest transcript - may be a different session";
  }
  printStatus({
    remaining, window: win, pctLeft: Math.round((remaining / win) * 100), model: scan.model, confidence,
    note: confidence !== "proven" ? "window is a heuristic; ~ marks an estimate (computed locally, daemon unreachable)" : "computed locally (daemon unreachable)",
    warning,
  });
  return true;
}

// ---- main: daemon first, self-compute fallback ----
const d = await fromDaemon();
if (d) printStatus(d);
else selfCompute();
