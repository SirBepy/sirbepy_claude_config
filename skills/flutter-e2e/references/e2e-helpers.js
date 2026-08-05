// Reusable Playwright helpers for driving a Flutter WEB RELEASE build against
// Firebase emulators. Copy this file into the target project's e2e script
// folder (e.g. .for_bepy/e2e/helpers.js) and fill in the CONFIG block below.
// Source: harvested from the pomalo overnight E2E run (2026-07-17), see
// C:/Users/tecno/.claude/skills/flutter-e2e/SKILL.md for the full recipe.

const fs = require('fs');
const path = require('path');

// ---- CONFIG: fill these in per project ----
const APP_URL = 'http://127.0.0.1:PORT';               // static-served release bundle URL (see SKILL.md Step 3)
const FIREBASE_PROJECT_ID = 'YOUR-PROJECT-ID';          // matches firebase.json / firebase_options.dart
const FIRESTORE_BASE = `http://127.0.0.1:8080/v1/projects/${FIREBASE_PROJECT_ID}/databases/(default)/documents`;
const AUTH_EMULATOR_ACCOUNTS = `http://127.0.0.1:9099/emulator/v1/projects/${FIREBASE_PROJECT_ID}/accounts`;
const SHOT_DIR = 'PATH/TO/PROJECT/.for_bepy/screenshots/<claude-ancestor-pid>-<ancestor-start-ticks>';
const E2E_DIR = 'PATH/TO/PROJECT/.for_bepy/e2e';
// --------------------------------------------

async function shot(page, name) {
  await page.screenshot({ path: path.join(SHOT_DIR, name) });
  console.log(`  screenshot -> ${name}`);
}

// Dumps every flt-semantics node (aria label, role, tappable/editable flags,
// and center point) to a JSON file. Use this as your "snapshot" between
// steps instead of relying on cached Playwright locators - Flutter recreates
// semantics nodes on label/state change, so a locator queried once and
// re-clicked later can point at a dead node (see clickNodeAtomic below).
async function dumpSemantics(page, tag) {
  const nodes = await page.evaluate(() => {
    function ownText(el) {
      let s = '';
      for (const child of el.childNodes) {
        if (child.nodeType === 3) s += child.textContent;
        else if (child.nodeType === 1 && child.tagName !== 'FLT-SEMANTICS') s += child.textContent;
      }
      return s.trim();
    }
    const els = Array.from(document.querySelectorAll('flt-semantics'));
    return els.map((n) => {
      const r = n.getBoundingClientRect();
      return {
        aria: n.getAttribute('aria-label') || ownText(n) || null,
        role: n.getAttribute('role'),
        tappable: n.hasAttribute('flt-tappable'),
        editable: n.hasAttribute('flt-editable-text') || n.getAttribute('contenteditable') === 'true',
        value: n.getAttribute('aria-valuetext') || n.getAttribute('aria-valuenow'),
        checked: n.getAttribute('aria-checked'),
        x: Math.round(r.x + r.width / 2),
        y: Math.round(r.y + r.height / 2),
        w: Math.round(r.width),
        h: Math.round(r.height),
      };
    }).filter((n) => n.w > 0 && n.h > 0);
  });
  fs.writeFileSync(path.join(E2E_DIR, `semantics-${tag}.json`), JSON.stringify(nodes, null, 2));
  return nodes;
}

async function waitForFlutterBoot(page, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const ok = await page.evaluate(() => !!document.querySelector('flt-semantics-placeholder, flt-glass-pane'));
    if (ok) return true;
    await page.waitForTimeout(500);
  }
  return false;
}

// Flutter web renders to canvas; the semantics DOM tree only exists after
// this placeholder is clicked once per page load.
async function enableSemantics(page) {
  await page.evaluate(() => {
    const el = document.querySelector('flt-semantics-placeholder');
    if (el) el.click();
  });
  await page.waitForTimeout(500);
}

async function waitForSemanticsNodes(page, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const n = await page.evaluate(() => document.querySelectorAll('flt-semantics').length);
    if (n > 0) return true;
    await page.waitForTimeout(500);
  }
  return false;
}

async function refreshSemantics(page, tag) {
  await enableSemantics(page);
  await waitForSemanticsNodes(page, 8000);
  await page.waitForTimeout(600);
  return dumpSemantics(page, tag);
}

function findNode(nodes, patterns) {
  for (const p of patterns) {
    const hit = nodes.find((n) => n.aria && p.test(n.aria));
    if (hit) return hit;
  }
  return null;
}

// Two-step click (find node from a dumpSemantics() snapshot, then click by
// coordinate). Fine for nodes whose label/state has NOT just changed. Do NOT
// use this for anything you interacted with in the last render pass - use
// clickNodeAtomic instead (see below).
async function clickNode(page, node) {
  const clicked = await page.evaluate(({ x, y }) => {
    const stack = document.elementsFromPoint(x, y);
    const target = stack.find((el) => el.tagName === 'FLT-SEMANTICS');
    if (target) {
      target.click();
      return true;
    }
    return false;
  }, { x: node.x, y: node.y });
  if (!clicked) {
    await page.mouse.click(node.x, node.y);
  }
}

// ATOMIC find-and-click, by aria text pattern, in a SINGLE page.evaluate().
//
// Why this exists (hours-costing landmine): any widget whose label or state
// just changed gets a RECREATED semantics node. A cached element handle, or
// even a two-step "query nodes, then click by coordinate" across two
// separate page.evaluate() calls, has a round-trip gap where the old node
// goes stale and the click silently no-ops - no error, nothing happens, and
// it looks like the step "did nothing" rather than "failed". Doing the DOM
// query AND the .click() inside the same synchronous JS execution closes
// that gap. ALWAYS use this (not clickNode) for anything that was just
// created/updated by the previous action (confirm bars, toasts, a button
// whose count/label depends on prior selections).
async function clickNodeAtomic(page, ariaTextPattern) {
  const result = await page.evaluate((patternSource) => {
    const pattern = new RegExp(patternSource, 'i');
    const els = Array.from(document.querySelectorAll('flt-semantics'));
    const target = els.find((el) => {
      let t = '';
      for (const c of el.childNodes) {
        if (c.nodeType === 3) t += c.textContent;
        else if (c.nodeType === 1 && c.tagName !== 'FLT-SEMANTICS') t += c.textContent;
      }
      return pattern.test(t.trim()) || pattern.test(el.getAttribute('aria-label') || '');
    });
    if (!target) return { found: false };
    const r = target.getBoundingClientRect();
    target.click();
    return { found: true, rect: { x: r.x, y: r.y, w: r.width, h: r.height } };
  }, ariaTextPattern.source);
  return result;
}

async function fetchJson(url, opts) {
  opts = opts || {};
  opts.headers = Object.assign({ Authorization: 'Bearer owner' }, opts.headers || {});
  const res = await fetch(url, opts);
  const text = await res.text();
  try {
    return { status: res.status, json: JSON.parse(text) };
  } catch (e) {
    return { status: res.status, json: null, raw: text };
  }
}

async function waitForBodyText(page, pattern, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const txt = await page.evaluate(() => document.body.innerText);
    if (pattern.test(txt)) return true;
    await page.waitForTimeout(800);
  }
  return false;
}

// Drives the Firebase Auth emulator's "Continue with Google" popup relay.
// Requires the browser context to be launched headless:false - the popup
// relay hangs forever under headless chromium.
async function signIn(page, context, email, displayName, postSignInBodyPattern) {
  let nodes = await refreshSemantics(page, 'signin');
  const googleBtn = findNode(nodes, [/continue with google/i, /google/i]);
  if (!googleBtn) return false;
  let signedIn = false;
  for (let attempt = 1; attempt <= 3 && !signedIn; attempt++) {
    try {
      const [popup] = await Promise.all([
        context.waitForEvent('page', { timeout: 15000 }),
        clickNode(page, googleBtn),
      ]);
      await popup.waitForLoadState('load', { timeout: 15000 });
      await popup.waitForTimeout(1200);
      await popup.locator('#add-account-button').click({ timeout: 8000 });
      await popup.waitForTimeout(1000);
      await popup.locator('#email-input').fill(email, { timeout: 8000 });
      const nameInput = popup.locator('#display-name-input');
      if (await nameInput.count()) await nameInput.fill(displayName);
      await popup.locator('#sign-in').click({ timeout: 8000 });
      await popup.waitForEvent('close', { timeout: 35000 }).catch(() => {});
      signedIn = true;
    } catch (e) {
      console.log(`  signin attempt ${attempt} failed: ${e.message}`);
    }
  }
  if (signedIn && postSignInBodyPattern) {
    await waitForBodyText(page, postSignInBodyPattern, 25000);
    await page.waitForTimeout(1000);
  }
  return signedIn;
}

// Reads the signed-in Firebase uid out of IndexedDB (firebaseLocalStorageDb)
// rather than requiring the app to expose it anywhere - works against any
// Flutter/firebase_auth app without app-code changes.
async function getUidFromIndexedDb(page) {
  try {
    return await page.evaluate(() => new Promise((resolve) => {
      const req = indexedDB.open('firebaseLocalStorageDb');
      req.onerror = () => resolve(null);
      req.onsuccess = () => {
        try {
          const db = req.result;
          const tx = db.transaction('firebaseLocalStorage', 'readonly');
          const store = tx.objectStore('firebaseLocalStorage');
          const getAllReq = store.getAll();
          getAllReq.onsuccess = () => {
            const rows = getAllReq.result || [];
            const hit = rows.find((r) => r && r.value && r.value.uid);
            resolve(hit ? hit.value.uid : null);
          };
          getAllReq.onerror = () => resolve(null);
        } catch (e) { resolve(null); }
      };
    }));
  } catch (e) {
    return null;
  }
}

module.exports = {
  APP_URL, FIRESTORE_BASE, AUTH_EMULATOR_ACCOUNTS, SHOT_DIR, E2E_DIR,
  shot, dumpSemantics, waitForFlutterBoot, enableSemantics, waitForSemanticsNodes, refreshSemantics,
  findNode, clickNode, clickNodeAtomic, fetchJson, waitForBodyText, signIn, getUidFromIndexedDb,
};
