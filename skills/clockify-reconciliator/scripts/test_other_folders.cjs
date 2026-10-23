#!/usr/bin/env node
// Self-contained test for other_folders.cjs: builds synthetic project folders under a temp dir,
// so it never reads the real ~/.claude-personal/projects. Run: node test_other_folders.cjs
'use strict';
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { scan, groupWindows, sanitizeCwd } = require('./other_folders.cjs');

function msg(ts, type = 'user') {
  return JSON.stringify({ type, timestamp: ts, message: { content: 'x' } });
}
function writeSession(root, folder, name, lines) {
  const dir = path.join(root, folder);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, name), lines.join('\n') + '\n');
}

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'other-folders-test-'));
try {
  // 2026-10-20 is CEST (UTC+2): 15:05Z is 17:05 local.
  writeSession(root, 'personal-a', 's1.jsonl', [
    msg('2026-10-20T15:05:00.000Z'),
    msg('2026-10-20T15:20:00.000Z', 'assistant'),
    // 25 min after 15:20Z: still the same window.
    msg('2026-10-20T15:45:00.000Z'),
    // 26 min after 15:45Z: starts a new window.
    msg('2026-10-20T16:11:00.000Z'),
    // Bookkeeping record, ignored.
    JSON.stringify({ type: 'queue-operation', timestamp: '2026-10-20T10:00:00.000Z' }),
    // Outside the requested range.
    msg('2026-10-21T15:00:00.000Z'),
  ]);
  // Configured repo folder plus a worktree folder of it: both excluded.
  const repo = 'C:/Users/x/Projects/zng-app';
  writeSession(root, sanitizeCwd(repo), 's.jsonl', [msg('2026-10-20T15:05:00.000Z')]);
  writeSession(root, sanitizeCwd(repo) + '--claude-worktrees-foo', 's.jsonl', [msg('2026-10-20T15:05:00.000Z')]);
  // A second configured repo whose folder carries a lowercase drive letter: still excluded. (A
  // different repo from the one above, since Windows folder names are case-insensitive.)
  const repo2 = 'C:/Users/x/Projects/zng-api';
  writeSession(root, sanitizeCwd(repo2).replace(/^C/, 'c'), 's.jsonl', [msg('2026-10-20T15:05:00.000Z')]);
  // A local date that differs from the UTC date: 22:30Z on the 19th is 00:30 local on the 20th.
  writeSession(root, 'personal-b', 's.jsonl', [msg('2026-10-19T22:30:00.000Z')]);

  const r = scan({ projectsDir: root, repos: [repo, repo2], from: '2026-10-20', to: '2026-10-20' });

  assert.deepStrictEqual(Object.keys(r.days), ['2026-10-20']);
  assert.deepStrictEqual(Object.keys(r.days['2026-10-20']).sort(), ['personal-a', 'personal-b']);
  assert.deepStrictEqual(r.days['2026-10-20']['personal-a'], [
    { start: '17:05', end: '17:45', count: 3 },
    { start: '18:11', end: '18:11', count: 1 },
  ]);
  assert.deepStrictEqual(r.days['2026-10-20']['personal-b'], [{ start: '00:30', end: '00:30', count: 1 }]);
  assert.strictEqual(r.skipped.length, 3);

  // The gap threshold itself: exactly 25 min joins, 25 min + 1 s splits.
  const t0 = Date.parse('2026-10-20T10:00:00Z');
  assert.strictEqual(groupWindows([t0, t0 + 25 * 60000], 25).length, 1);
  assert.strictEqual(groupWindows([t0, t0 + 25 * 60000 + 1000], 25).length, 2);

  console.log('test_other_folders: all assertions passed');
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}
