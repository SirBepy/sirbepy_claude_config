#!/usr/bin/env node
// Step 6 "other active folders" pass: lists the Claude project folders under
// ~/.claude-personal/projects/ that are NOT one of the configured repos, with each one's activity
// windows per local day. Read-only. The output is negative evidence only: a stretch where only
// these folders were active is not project time, and nothing here ever counts toward a total.
//
// A window is a run of user/assistant message timestamps with no gap longer than --gap-min
// (default 25). Days are local calendar days in --tz (default Europe/Zagreb), so a window never
// spans local midnight. The raw jsonl timestamps are UTC (Z suffix); every time printed is LOCAL.
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const DEFAULT_TZ = 'Europe/Zagreb';
const DEFAULT_GAP_MIN = 25;

// Claude names a project folder after the cwd with every non-alphanumeric char turned into '-'.
function sanitizeCwd(p) {
  return p.replace(/[^A-Za-z0-9]/g, '-');
}

// Sanitized folder names of the configured repos' registered git worktrees. A sibling worktree
// (isolated-build's `../<repo>-<name>`) sanitizes to a name that no prefix rule can tell from an
// unrelated sibling repo like `zng-app-x`, so git is asked instead. A worktree already removed is
// not listed and shows up as an ordinary other folder.
function gitWorktreeFolders(repos) {
  const out = [];
  for (const r of repos) {
    try {
      const txt = execFileSync('git', ['-C', r, 'worktree', 'list', '--porcelain'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
      for (const m of txt.matchAll(/^worktree (.+)$/gm)) out.push(sanitizeCwd(m[1].trim()));
    } catch { /* not a git repo or path gone: the name rules below still apply */ }
  }
  return out;
}

// A worktree of a configured repo gets its own folder. EnterWorktree puts it at
// "<repo>/.claude/worktrees/<name>", which sanitizes to "<sanitized repo>--claude-worktrees-<name>",
// so that exact infix counts as the same project; a bare "<sanitized repo>-" prefix would also
// swallow a sibling repo such as "zng-app-x". Sibling worktrees come in via worktreeFolders.
// Compared case-insensitively because the same checkout shows up under both "C--Users-..." and
// "c--Users-..." depending on how the cwd was spelled.
function isConfiguredFolder(folderName, repos, excludeFolders, worktreeFolders = []) {
  const name = folderName.toLowerCase();
  if (excludeFolders.some((e) => e.toLowerCase() === name)) return true;
  if (worktreeFolders.some((w) => w.toLowerCase() === name)) return true;
  return repos.some((r) => {
    const s = sanitizeCwd(r.replace(/[\\/]+$/, '')).toLowerCase();
    return name === s || name.startsWith(s + '--claude-worktrees-');
  });
}

function makeLocalParts(tz) {
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: tz, hourCycle: 'h23',
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  });
  return (ms) => {
    const p = {};
    for (const part of fmt.formatToParts(new Date(ms))) p[part.type] = part.value;
    return { date: `${p.year}-${p.month}-${p.day}`, min: Number(p.hour) * 60 + Number(p.minute) };
  };
}

function fmtMin(min) {
  return String(Math.floor(min / 60)).padStart(2, '0') + ':' + String(min % 60).padStart(2, '0');
}

// Sorted epoch-ms list -> [{start, end, count}] split wherever the gap exceeds gapMin.
function groupWindows(sortedMs, gapMin) {
  const windows = [];
  for (const t of sortedMs) {
    const last = windows[windows.length - 1];
    if (last && t - last.end <= gapMin * 60000) {
      last.end = t;
      last.count++;
    } else {
      windows.push({ start: t, end: t, count: 1 });
    }
  }
  return windows;
}

function readMessageTimes(file) {
  const times = [];
  for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
    // Cheap prefilter: only user/assistant records carry real conversation activity; queue
    // operations and attachments are bookkeeping.
    if (!line.includes('"type":"user"') && !line.includes('"type":"assistant"')) continue;
    let o;
    try { o = JSON.parse(line); } catch { continue; }
    if ((o.type !== 'user' && o.type !== 'assistant') || !o.timestamp) continue;
    const ms = Date.parse(o.timestamp);
    if (!Number.isNaN(ms)) times.push(ms);
  }
  return times;
}

// Returns {days: {date: {folder: [{start:'HH:MM', end:'HH:MM', count}]}}, skipped: [folder]}.
function scan({ projectsDir, repos, excludeFolders = [], from, to, tz = DEFAULT_TZ, gapMin = DEFAULT_GAP_MIN,
  worktreeFolders = gitWorktreeFolders(repos) }) {
  const local = makeLocalParts(tz);
  // A file untouched since before the range start cannot hold in-range messages. One day of slack
  // covers the local-vs-UTC date difference.
  const mtimeFloor = Date.parse(from + 'T00:00:00Z') - 86400000;
  const days = {};
  const skipped = [];
  for (const ent of fs.readdirSync(projectsDir, { withFileTypes: true })) {
    if (!ent.isDirectory()) continue;
    if (isConfiguredFolder(ent.name, repos, excludeFolders, worktreeFolders)) { skipped.push(ent.name); continue; }
    const dir = path.join(projectsDir, ent.name);
    const perDay = {};
    for (const f of fs.readdirSync(dir)) {
      if (!f.endsWith('.jsonl')) continue;
      const file = path.join(dir, f);
      if (fs.statSync(file).mtimeMs < mtimeFloor) continue;
      for (const ms of readMessageTimes(file)) {
        const { date, min } = local(ms);
        if (date < from || date > to) continue;
        (perDay[date] = perDay[date] || []).push({ ms, min });
      }
    }
    for (const [date, msgs] of Object.entries(perDay)) {
      msgs.sort((a, b) => a.ms - b.ms);
      const minOf = new Map(msgs.map((m) => [m.ms, m.min]));
      const wins = groupWindows(msgs.map((m) => m.ms), gapMin).map((w) => ({
        start: fmtMin(minOf.get(w.start)), end: fmtMin(minOf.get(w.end)), count: w.count,
      }));
      ((days[date] = days[date] || {})[ent.name] = wins);
    }
  }
  return { days, skipped };
}

function render(result, repos) {
  const lines = [];
  const dates = Object.keys(result.days).sort();
  if (!dates.length) lines.push('No non-project folder activity in range.');
  for (const date of dates) {
    for (const folder of Object.keys(result.days[date]).sort()) {
      const wins = result.days[date][folder].map((w) => `${w.start}-${w.end} (${w.count} msgs)`).join(', ');
      lines.push(`LOCAL ${date}  ${folder}  ${wins}`);
    }
  }
  // A configured repo can run under a cwd whose sanitized name differs from the config path (a
  // symlinked or relocated checkout). Flag folders sharing a repo's basename so that project does
  // not read as non-project time.
  const bases = repos.map((r) => path.basename(r.replace(/[\\/]+$/, ''))).filter(Boolean);
  const seen = new Set(dates.flatMap((d) => Object.keys(result.days[d])));
  for (const folder of [...seen].sort()) {
    const hit = bases.find((b) => folder.toLowerCase().endsWith('-' + sanitizeCwd(b).toLowerCase()));
    if (hit) lines.push(`NOTE ${folder} ends with configured repo name "${hit}" but not its path: if it is the project, rerun with --exclude-folder ${folder}`);
  }
  lines.push(`Skipped as configured project folders: ${result.skipped.length ? result.skipped.join(', ') : '(none)'}`);
  return lines.join('\n');
}

function getAll(args, flag) {
  const out = [];
  args.forEach((a, i) => { if (a === flag && args[i + 1]) out.push(args[i + 1]); });
  return out;
}

function main() {
  const args = process.argv.slice(2);
  const get = (flag, def = null) => { const i = args.indexOf(flag); return i !== -1 ? args[i + 1] : def; };
  const range = get('--range');
  const m = range && range.match(/^(\d{4}-\d{2}-\d{2})(?:\.\.(\d{4}-\d{2}-\d{2}))?$/);
  if (!m) {
    console.error('Usage: other_folders.cjs --range YYYY-MM-DD[..YYYY-MM-DD] [--repo <cwd>]... [--exclude-folder <name>]... [--projects-dir <dir>] [--tz <zone>] [--gap-min N] [--json]');
    process.exit(2);
  }
  const projectsDir = get('--projects-dir', path.join(os.homedir(), '.claude-personal', 'projects'));
  const repos = getAll(args, '--repo');
  const result = scan({
    projectsDir, repos, excludeFolders: getAll(args, '--exclude-folder'),
    from: m[1], to: m[2] || m[1], tz: get('--tz', DEFAULT_TZ), gapMin: Number(get('--gap-min', DEFAULT_GAP_MIN)),
  });
  console.log(args.includes('--json') ? JSON.stringify(result, null, 2) : render(result, repos));
}

if (require.main === module) main();
module.exports = { sanitizeCwd, isConfiguredFolder, gitWorktreeFolders, groupWindows, scan, render };
