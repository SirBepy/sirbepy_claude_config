#!/usr/bin/env node
// Self-contained test for the HubStaff retry logic. Stubs the page, so it never launches a browser,
// logs in, or touches HubStaff. Run: node test_hs_retry.cjs
'use strict';
const assert = require('assert');
const { gotoWithRetry, NAV_TIMEOUT_MS } = require('./hs_common.cjs');
const { addEntryWithRetry, makeAttempt } = require('./hs_addtime.cjs');

const noSleep = async () => {};
const entry = { date: '2026-11-02', from: '9:00 am', to: '10:00 am', note: 'n' };

// A locator whose every method returns another locator; hooks decide waitFor/click behaviour.
function fakePage({ gotoFails = 0, dialogFails = 0, saveFails = false, closeFails = false } = {}) {
  const log = { goto: 0, dialogWaits: 0, saveClicks: 0, gotoOpts: [] };
  const loc = (name) => new Proxy(function () {}, {
    get(_t, prop) {
      if (prop === 'then') return undefined; // not thenable, so `await locator` resolves to itself
      if (prop === 'waitFor') return async () => {
        if (name === 'dialog' && ++log.dialogWaits <= dialogFails) throw new Error('locator not visible within 10000ms');
      };
      if (prop === 'count') return async () => 0;
      if (prop === 'click') return async () => {
        if (name === 'save') { log.saveClicks++; if (saveFails) throw new Error('save click failed'); }
      };
      return (arg) => {
        if (prop === 'locator' && String(arg).includes('.app-dialog.opened')) return loc('dialog');
        if (prop === 'locator' && String(arg).includes('save-button')) return loc('save');
        return loc(name);
      };
    },
  });
  const page = {
    goto: async (_url, opts) => { log.gotoOpts.push(opts); if (++log.goto <= gotoFails) throw new Error('page.goto: Timeout 30000ms exceeded'); },
    waitForTimeout: async () => {},
    // The dialog failing to close after Save is the real maybeSaved case: the click went through.
    waitForFunction: async () => { if (closeFails) throw new Error('page.waitForFunction: Timeout 10000ms exceeded'); },
    keyboard: { press: async () => {}, type: async () => {} },
    getByText: () => loc('text'),
    locator: (s) => (String(s).includes('.app-dialog.opened') ? loc('dialog') : loc('x')),
  };
  return { page, log };
}

(async () => {
  const cfg = { org: '1', user: '2', projectLabel: 'P', reasonLabel: 'R' };

  // gotoWithRetry: one retry by default, longer timeout, and the final failure propagates.
  {
    const { page, log } = fakePage({ gotoFails: 1 });
    await gotoWithRetry(page, 'u', { sleep: noSleep });
    assert.strictEqual(log.goto, 2);
    assert.strictEqual(log.gotoOpts[0].timeout, NAV_TIMEOUT_MS);
    assert.ok(NAV_TIMEOUT_MS > 30000);
    const bad = fakePage({ gotoFails: 5 });
    await assert.rejects(gotoWithRetry(bad.page, 'u', { sleep: noSleep }), /Timeout/);
    assert.strictEqual(bad.log.goto, 2);
  }

  // A transient goto timeout no longer leaves the entry ok:false.
  {
    const { page, log } = fakePage({ gotoFails: 1 });
    const r = await addEntryWithRetry(entry, makeAttempt(page, cfg), { sleep: noSleep });
    assert.strictEqual(r.ok, true);
    assert.strictEqual(r.error, undefined);
    assert.strictEqual(r.maybeSaved, undefined);
    assert.strictEqual(log.goto, 2);
    assert.strictEqual(log.saveClicks, 1);
  }

  // A dialog that never opens twice, then opens: succeeds on the third try, Save clicked once.
  {
    const { page, log } = fakePage({ dialogFails: 2 });
    const r = await addEntryWithRetry(entry, makeAttempt(page, cfg), { sleep: noSleep });
    assert.strictEqual(r.ok, true);
    assert.strictEqual(log.dialogWaits, 3);
    assert.strictEqual(log.saveClicks, 1);
  }

  // Retries are bounded: a dialog that never opens fails after 1 + 2 tries, never having saved.
  {
    const { page, log } = fakePage({ dialogFails: 99 });
    const r = await addEntryWithRetry(entry, makeAttempt(page, cfg), { sleep: noSleep });
    assert.strictEqual(r.ok, false);
    assert.match(r.error, /not visible/);
    assert.strictEqual(r.maybeSaved, undefined);
    assert.strictEqual(log.dialogWaits, 3);
    assert.strictEqual(log.saveClicks, 0);
  }

  // A failure after Save was clicked is never retried and is flagged maybeSaved.
  {
    const { page, log } = fakePage({ saveFails: true });
    const r = await addEntryWithRetry(entry, makeAttempt(page, cfg), { sleep: noSleep });
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.maybeSaved, true);
    assert.strictEqual(log.saveClicks, 1);
    assert.strictEqual(log.goto, 1);
  }

  // Save clicked, dialog never closes: the entry may exist, so no retry and maybeSaved is set.
  {
    const { page, log } = fakePage({ closeFails: true });
    const r = await addEntryWithRetry(entry, makeAttempt(page, cfg), { sleep: noSleep });
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.maybeSaved, true);
    assert.match(r.error, /waitForFunction/);
    assert.strictEqual(log.saveClicks, 1);
    assert.strictEqual(log.goto, 1);
  }

  // recover() runs after every failed try, so a half-open dialog is closed before the next one.
  {
    let recovered = 0;
    let calls = 0;
    const r = await addEntryWithRetry(entry, async () => { if (++calls < 3) throw new Error('x'); }, { sleep: noSleep, recover: async () => { recovered++; } });
    assert.strictEqual(r.ok, true);
    assert.strictEqual(recovered, 2);
  }

  console.log('test_hs_retry: all assertions passed');
})().catch((e) => { console.error(e); process.exit(1); });
