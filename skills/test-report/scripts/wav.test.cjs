// Run with: node wav.test.cjs
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { readWav } = require('./wav.cjs');
const { lengthMs } = require('./tts-client.cjs');

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wav-test-'));

const chunk = (id, body) => {
  const h = Buffer.alloc(8);
  h.write(id, 0, 'ascii');
  h.writeUInt32LE(body.length, 4);
  // Chunks are word-aligned: an odd body is followed by a pad byte that its size field does not count.
  return Buffer.concat([h, body, Buffer.alloc(body.length % 2)]);
};

const fmt = (rate) => {
  const b = Buffer.alloc(16);
  b.writeUInt16LE(1, 0); b.writeUInt16LE(1, 2); b.writeUInt32LE(rate, 4);
  b.writeUInt32LE(rate * 2, 8); b.writeUInt16LE(2, 12); b.writeUInt16LE(16, 14);
  return chunk('fmt ', b);
};

const wav = (...chunks) => {
  const body = Buffer.concat([Buffer.from('WAVE', 'ascii'), ...chunks]);
  const h = Buffer.alloc(8);
  h.write('RIFF', 0, 'ascii');
  h.writeUInt32LE(body.length, 4);
  return Buffer.concat([h, body]);
};

const write = (name, buf) => {
  const file = path.join(dir, name);
  fs.writeFileSync(file, buf);
  return file;
};

try {
  const pcm = Buffer.alloc(48000);
  for (let i = 0; i < pcm.length; i++) pcm[i] = i % 251;

  // A plain file: fmt then data.
  const plain = write('plain.wav', wav(fmt(24000), chunk('data', pcm)));
  const read = readWav(plain);
  assert.strictEqual(read.rate, 24000);
  assert.ok(read.pcm.equals(pcm));
  assert.strictEqual(lengthMs(plain), 1000, '48000 bytes of 16-bit mono at 24kHz is one second');

  // An odd-sized chunk before data, with its pad byte, must not shift the body.
  const odd = write('odd.wav', wav(fmt(16000), chunk('LIST', Buffer.from('abcde')), chunk('data', pcm)));
  const readOdd = readWav(odd);
  assert.strictEqual(readOdd.rate, 16000);
  assert.ok(readOdd.pcm.equals(pcm));
  assert.strictEqual(lengthMs(odd), 1500, 'the rate comes from the fmt chunk, not a constant');

  // A file with no data chunk, and one with data before fmt, are refused.
  assert.throws(() => readWav(write('nodata.wav', wav(fmt(24000)))), /no data chunk/);
  assert.throws(() => readWav(write('order.wav', wav(chunk('data', pcm), fmt(24000)))), /before fmt/);

  console.log('wav tests passed');
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
