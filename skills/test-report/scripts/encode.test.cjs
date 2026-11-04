// Run with: node encode.test.cjs
const assert = require('assert');
const { timeline } = require('./encode.cjs');

const take = (over) => ({ take: 't', videoMs: 21000, end: 20000, raw: 'x.webm', cuts: [], captions: [], steps: [], ...over });
const line = (t, ms, text = 'a line') => ({ t, ms, text, wav: 'x.wav' });

// The video starts before the script's clock: 21s of video against 20s of script means a 1s lead.
{
  const tl = timeline([take({ captions: [line(2000, 500)], steps: [{ name: 's', ok: true, t: 2000 }] })]);
  assert.strictEqual(tl.captions[0].at, 3000);
  assert.strictEqual(tl.steps[0].at, 3000);
  assert.strictEqual(tl.total, 21000);
}

// begin() removes everything from the very first frame, lead included, and later times shift down.
{
  const tl = timeline([take({ cuts: [{ from: 0, to: 5000, fromStart: true }], captions: [line(6000, 500)] })]);
  assert.strictEqual(tl.captions[0].at, 1000);
  assert.strictEqual(tl.total, 15000);
}

// A cut in the middle shifts only what comes after it.
{
  const tl = timeline([take({ cuts: [{ from: 3000, to: 5000 }], captions: [line(1000, 500), line(6000, 500)] })]);
  assert.strictEqual(tl.captions[0].at, 2000);
  assert.strictEqual(tl.captions[1].at, 5000);
}

// The second take of a clip starts where the first one ended.
{
  const tl = timeline([take({ captions: [line(1000, 500)] }), take({ captions: [line(1000, 500)] })]);
  assert.strictEqual(tl.captions[1].at, 21000 + 2000);
}

// Lines that overlap are refused, whichever take they came from, and touching lines are allowed.
assert.throws(() => timeline([take({ captions: [line(1000, 2000, 'first'), line(2000, 500, 'second')] })]), /overlap/);
assert.doesNotThrow(() => timeline([take({ captions: [line(1000, 1000), line(2000, 500)] })]));

// A cut must never remove video under a line that is being spoken.
assert.throws(() => timeline([take({ cuts: [{ from: 1500, to: 1800 }], captions: [line(500, 1500, 'spoken')] })]), /cut removes video/);

console.log('encode tests passed');
