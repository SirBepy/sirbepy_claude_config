#!/usr/bin/env node
// Self-contained test for other_folders.cjs: builds synthetic project folders under a temp dir,
// so it never reads the real ~/.claude-personal/projects. Run: node test_other_folders.cjs
'use strict';
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { scan, groupWindows, sanitizeCwd, isConfiguredFolder, gitWorktreeFolders, render } = require('./other_folders.cjs');

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

  // A sibling repo whose name merely starts with a configured repo's name is NOT that repo.
  const siblingFolder = sanitizeCwd(repo) + '-x';
  writeSession(root, siblingFolder, 's.jsonl', [msg('2026-10-20T15:05:00.000Z')]);

  // worktreeFolders is injected so the test never shells out to git for the fake repo paths.
  const r = scan({ projectsDir: root, repos: [repo, repo2], from: '2026-10-20', to: '2026-10-20', worktreeFolders: [] });

  assert.deepStrictEqual(Object.keys(r.days), ['2026-10-20']);
  assert.deepStrictEqual(Object.keys(r.days['2026-10-20']).sort(), ['personal-a', 'personal-b', siblingFolder].sort());
  assert.deepStrictEqual(r.days['2026-10-20']['personal-a'], [
    { start: '17:05', end: '17:45', count: 3 },
    { start: '18:11', end: '18:11', count: 1 },
  ]);
  assert.deepStrictEqual(r.days['2026-10-20']['personal-b'], [{ start: '00:30', end: '00:30', count: 1 }]);
  assert.strictEqual(r.skipped.length, 3);

  // isConfiguredFolder: EnterWorktree's folder form and the repo itself match, a lookalike sibling
  // does not, and a sibling checkout registered with git does.
  const wtName = sanitizeCwd(repo) + '--claude-worktrees-foo';
  assert.strictEqual(isConfiguredFolder(wtName, [repo], []), true);
  assert.strictEqual(isConfiguredFolder(siblingFolder, [repo], []), false);
  assert.strictEqual(isConfiguredFolder(siblingFolder, [repo], [], [siblingFolder]), true);
  assert.strictEqual(isConfiguredFolder(siblingFolder, [repo], [siblingFolder]), true);

  // gitWorktreeFolders tolerates a path that is not a git repo.
  assert.deepStrictEqual(gitWorktreeFolders([path.join(root, 'no-such-repo')]), []);

  // render(): a folder ending in a configured repo's name but not its path gets the NOTE hint.
  const noted = 'C--Users-x-elsewhere-zng-app';
  const out = render({ days: { '2026-10-20': { [noted]: [{ start: '10:00', end: '10:30', count: 2 }] } }, skipped: ['a'] }, [repo]);
  assert.ok(out.includes(`LOCAL 2026-10-20  ${noted}  10:00-10:30 (2 msgs)`), out);
  assert.ok(out.includes(`NOTE ${noted} ends with configured repo name "zng-app"`), out);
  assert.ok(out.includes(`--exclude-folder ${noted}`), out);
  assert.ok(out.endsWith('Skipped as configured project folders: a'), out);
  // A folder with no repo-name suffix gets no NOTE.
  const plain = render({ days: { '2026-10-20': { 'personal-a': [{ start: '10:00', end: '10:00', count: 1 }] } }, skipped: [] }, [repo]);
  assert.ok(!plain.includes('NOTE'), plain);

  // The gap threshold itself: exactly 25 min joins, 25 min + 1 s splits.
  const t0 = Date.parse('2026-10-20T10:00:00Z');
  assert.strictEqual(groupWindows([t0, t0 + 25 * 60000], 25).length, 1);
  assert.strictEqual(groupWindows([t0, t0 + 25 * 60000 + 1000], 25).length, 2);

  // --only-configured mode: configured folders' windows, minus idle-on-card waits.
  const askUse = (ts, name = 'mcp__cc_conductor__ask_user_question') => JSON.stringify({
    type: 'assistant', timestamp: ts, message: { content: [{ type: 'tool_use', id: 't1', name, input: {} }] },
  });
  const toolResult = (ts) => JSON.stringify({ type: 'user', timestamp: ts, message: { content: [{ type: 'tool_result', tool_use_id: 't1', content: 'x' }] } });
  const answer = (ts) => JSON.stringify({ type: 'user', timestamp: ts, message: { content: '<auq-answer id="a">ok</auq-answer>' } });
  const opts = { projectsDir: root, from: '2026-10-20', to: '2026-10-20', worktreeFolders: [], onlyConfigured: true };

  const repoA = 'C:/Users/x/Projects/cfg-a';
  writeSession(root, sanitizeCwd(repoA), 'idle.jsonl', [
    msg('2026-10-20T10:00:00.000Z'),
    msg('2026-10-20T10:05:00.000Z', 'assistant'),
    askUse('2026-10-20T10:10:00.000Z'),
    // Bookkeeping inside the wait (tool_result, a trailing assistant line) is not activity.
    toolResult('2026-10-20T10:10:01.000Z'),
    msg('2026-10-20T10:10:05.000Z', 'assistant'),
    answer('2026-10-20T10:20:00.000Z'),
    msg('2026-10-20T10:21:00.000Z', 'assistant'),
    // A 1 minute wait is under the 2 minute floor: no idle interval, window stays whole.
    askUse('2026-10-20T10:22:00.000Z', 'AskUserQuestion'),
    answer('2026-10-20T10:23:00.000Z'),
    msg('2026-10-20T10:25:00.000Z', 'assistant'),
    // A card never answered (the dev typed instead) produces no interval.
    askUse('2026-10-20T10:30:00.000Z'),
    msg('2026-10-20T10:40:00.000Z'),
    msg('2026-10-20T10:41:00.000Z', 'assistant'),
  ]);
  const rA = scan({ ...opts, repos: [repoA] });
  assert.deepStrictEqual(rA.days['2026-10-20'][sanitizeCwd(repoA)], [
    { start: '12:00', end: '12:10', count: 3 },
    { start: '12:20', end: '12:41', count: 8 },
  ]);
  assert.deepStrictEqual(rA.idle['2026-10-20'][sanitizeCwd(repoA)], [{ start: '12:10', end: '12:20' }]);
  assert.ok(render(rA, [repoA]).includes('IDLE-ON-CARD 12:10-12:20'), render(rA, [repoA]));

  // Only configured folders appear; the other folders do not.
  assert.deepStrictEqual(Object.keys(rA.days['2026-10-20']), [sanitizeCwd(repoA)]);

  // A subagent transcript is agent runtime: its messages inside the wait keep the window whole,
  // and other_folders mode (the default) still never lists a configured folder.
  const repoB = 'C:/Users/x/Projects/cfg-b';
  writeSession(root, sanitizeCwd(repoB), 'main.jsonl', [
    msg('2026-10-20T10:00:00.000Z'),
    askUse('2026-10-20T10:10:00.000Z'),
    answer('2026-10-20T10:20:00.000Z'),
    msg('2026-10-20T10:21:00.000Z', 'assistant'),
  ]);
  writeSession(root, path.join(sanitizeCwd(repoB), 'main', 'subagents'), 'agent-a.jsonl', [
    msg('2026-10-20T10:12:00.000Z', 'assistant'),
    msg('2026-10-20T10:18:00.000Z', 'assistant'),
  ]);
  const rB = scan({ ...opts, repos: [repoB] });
  // Subagent messages at 10:12 and 10:18 sit inside the wait: window is one piece, 6 messages.
  assert.deepStrictEqual(rB.days['2026-10-20'][sanitizeCwd(repoB)], [{ start: '12:00', end: '12:21', count: 6 }]);
  assert.deepStrictEqual(rB.idle['2026-10-20'][sanitizeCwd(repoB)], [{ start: '12:10', end: '12:20' }]);

  // The mtime floor skips a stale file even in this mode.
  const repoC = 'C:/Users/x/Projects/cfg-c';
  writeSession(root, sanitizeCwd(repoC), 'old.jsonl', [msg('2026-10-20T10:00:00.000Z')]);
  const old = new Date('2020-01-01T00:00:00Z');
  fs.utimesSync(path.join(root, sanitizeCwd(repoC), 'old.jsonl'), old, old);
  assert.deepStrictEqual(scan({ ...opts, repos: [repoC] }).days, {});

  console.log('test_other_folders: all assertions passed');
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}
