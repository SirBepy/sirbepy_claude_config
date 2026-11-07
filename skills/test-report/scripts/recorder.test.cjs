// Run with: node recorder.test.cjs
// Drives recorder.open/finish against a fake Playwright and calls the network route directly, so no
// browser, video or voice is involved.
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const R = require('./recorder.cjs');

const workDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recorder-test-'));
let handler = null;
const closed = [];

const chromium = {
  launch: async () => ({
    newContext: async () => ({
      route: async (match, fn) => { assert.strictEqual(match, '**/*', 'every request must pass the guard'); handler = fn; },
      addInitScript: async () => {},
      newPage: async () => ({ on: () => {}, video: () => ({ path: async () => 'unused.webm' }) }),
      close: async () => { closed.push('context'); },
    }),
    close: async () => { closed.push('browser'); },
  }),
};

// What the page's request does to the route: which of abort/continue/fulfill the guard chose.
const request = (url) => {
  const result = { url, action: null };
  handler({
    request: () => ({ url: () => url }),
    abort: (reason) => { result.action = 'abort'; result.reason = reason; },
    continue: () => { result.action = 'continue'; },
    fulfill: () => { result.action = 'fulfill'; },
  });
  return result;
};

(async () => {
  try {
    R.setup({ chromium, workDir, narrate: false, refuseUrls: /dev\.example|firestore\.googleapis\.com/ });
    const session = await R.open({ take: 'guard' });

    assert.strictEqual(request('http://localhost:8080/app.js').action, 'continue', 'local host passes');
    assert.strictEqual(request('http://127.0.0.1:3000/x').action, 'continue', 'loopback passes');
    for (const url of ['https://www.gstatic.com/flutter-canvaskit/abc/canvaskit.wasm', 'https://fonts.gstatic.com/s/roboto.woff2', 'https://fonts.googleapis.com/css', 'https://cdn.jsdelivr.net/npm/x.js']) {
      assert.strictEqual(request(url).action, 'continue', `${url} is an allowed CDN host`);
    }

    // The allow list is exact: a host that merely contains an allowed name is not allowed.
    for (const url of ['https://gstatic.com.evil.test/x', 'https://notfonts.gstatic.com.test/x', 'https://evil-jsdelivr.test/x', 'https://analytics.example.org/c']) {
      assert.strictEqual(request(url).action, 'fulfill', `${url} is stubbed, not fetched`);
    }

    // A refuseUrls match is aborted before it is sent, even on a host that is otherwise allowed.
    const refused = request('https://dev.example.com/api/groups');
    assert.strictEqual(refused.action, 'abort');
    assert.strictEqual(request('https://firestore.googleapis.com/v1/projects').action, 'abort', 'refuseUrls wins over allowHosts');

    assert.deepStrictEqual(session.refused, ['https://dev.example.com/api/groups', 'https://firestore.googleapis.com/v1/projects']);
    assert.strictEqual(session.outside.length, 4, 'stubbed hosts are listed in outside');

    // The take fails visibly, after the browser has been closed.
    await assert.rejects(() => R.finish(session), /take failed.*dev\.example\.com\/api\/groups/);
    assert.deepStrictEqual(closed, ['context', 'browser']);
    console.log('recorder tests passed');
  } finally {
    fs.rmSync(workDir, { recursive: true, force: true });
  }
})().catch((e) => { console.error(e); process.exit(1); });
