// Regression coverage for todo 1063: the Stop deep pass re-flagging
// pre-existing findings on every turn even when nothing changed.
//
// Two independent causes, both exercised here:
//   1. runStopHook's own dedupe only remembered the *fresh* subset of a scan,
//      not the complete filtered set, so a finding already known from the
//      per-edit pass got silently forgotten on the very next Stop call and
//      came back as "fresh" again. No file edit required to reproduce.
//   2. findingCacheKey keyed on raw line number, so a finding that is still
//      there verbatim, just shifted a few lines by an unrelated edit
//      elsewhere in the file, got a new key and re-surfaced.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import {
  dedupeAgainstCache,
  rememberFindings,
  runStopHook,
  touchFile,
} from './hook-lib.mjs';

function makeProject() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'impeccable-hooklib-'));
  const filePath = path.join(dir, 'style.css');
  fs.writeFileSync(filePath, '.a { font-size: 10px; }\n.b { box-shadow: 0 0 20px #000; }\n', 'utf-8');
  return { dir, filePath };
}

test('dedupeAgainstCache treats a line-shifted finding as already known', () => {
  const cache = { version: 1, sessions: {} };
  const sessionId = 'session-a';
  const filePath = 'src/style.css';

  const original = { antipattern: 'tiny-text', file: filePath, line: 5, snippet: 'font-size: 10px' };
  rememberFindings(cache, sessionId, filePath, [original]);

  // Same finding, same text, four lines lower: an edit elsewhere in the file
  // pushed everything below it down. The logical finding did not change.
  const shifted = { antipattern: 'tiny-text', file: filePath, line: 9, snippet: 'font-size: 10px' };
  const fresh = dedupeAgainstCache([shifted], cache, sessionId, filePath);

  assert.equal(fresh.length, 0, 'a line-shifted repeat of a known finding must not be fresh');
});

test('dedupeAgainstCache still treats two distinct findings on different lines as distinct', () => {
  const cache = { version: 1, sessions: {} };
  const sessionId = 'session-b';
  const filePath = 'src/style.css';

  const first = { antipattern: 'tiny-text', file: filePath, line: 5, snippet: 'font-size: 10px' };
  rememberFindings(cache, sessionId, filePath, [first]);

  // A different occurrence of the same rule, different surrounding text.
  const second = { antipattern: 'tiny-text', file: filePath, line: 40, snippet: 'font-size: 9px' };
  const fresh = dedupeAgainstCache([second], cache, sessionId, filePath);

  assert.equal(fresh.length, 1, 'a genuinely different occurrence must still surface');
});

test('dedupeAgainstCache keeps two same-value findings from one scan as two (todo 1102)', () => {
  // Reproduces the reviewer's case for todo 1063: a value-keyed detector
  // (overused-font) can emit the same font at two unrelated lines in one
  // file. The value-only key must not collapse them to one.
  const cache = { version: 1, sessions: {} };
  const sessionId = 'session-value-branch';
  const filePath = 'src/page.html';

  const first = { antipattern: 'overused-font', file: filePath, line: 5, snippet: 'Primary font: Comic Sans' };
  const second = { antipattern: 'overused-font', file: filePath, line: 80, snippet: 'Primary font: Comic Sans' };

  const fresh = dedupeAgainstCache([first, second], cache, sessionId, filePath);

  assert.equal(fresh.length, 2, 'two genuinely separate occurrences of the same value must both surface');
});

test('runStopHook stays quiet on a second pass when the file did not change', async () => {
  const { dir, filePath } = makeProject();
  const sessionId = 'session-c';

  // Simulate the per-edit pass: it already surfaced and remembered one
  // "immediate" finding for this file.
  const immediate = { antipattern: 'tiny-text', file: filePath, line: 1, snippet: 'font-size: 10px' };
  const deferred = { antipattern: 'dark-glow', file: filePath, line: 2, snippet: 'box-shadow: 0 0 20px #000' };

  const cache = { version: 1, sessions: {} };
  touchFile(cache, sessionId, filePath);
  rememberFindings(cache, sessionId, filePath, [immediate]);
  fs.mkdirSync(path.join(dir, '.impeccable'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.impeccable', 'hook.cache.json'), JSON.stringify(cache));

  // The full rule set returns both findings on every call; the file never
  // changes between the two Stop events (the session is waiting on CI).
  const detector = { detectText: async () => [immediate, deferred] };
  const stdinJson = JSON.stringify({ cwd: dir, session_id: sessionId });

  const first = await runStopHook({ stdinJson, cwd: dir, detector });
  assert.equal(first.audit.emitted, true, 'first Stop pass must surface the deferred finding');
  assert.equal(first.emission?.groups?.[0]?.findings?.length, 1, 'only the not-yet-known finding is fresh');

  const second = await runStopHook({ stdinJson, cwd: dir, detector });
  assert.equal(
    second.audit.emitted,
    false,
    `second Stop pass on an unchanged file must stay quiet, got: ${JSON.stringify(second.audit)}`,
  );

  fs.rmSync(dir, { recursive: true, force: true });
});
