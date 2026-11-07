// The one WAV reader for the recorder and the encoder. tts.py writes mono 16-bit PCM; chunks are
// walked by id so extra chunks (LIST, fact) before `data` do not shift the body.
const fs = require('fs');

// Returns { rate, pcm }: the sample rate from the `fmt ` chunk and the raw PCM bytes of `data`.
function readWav(file) {
  const b = fs.readFileSync(file);
  let rate = null;
  let at = 12;
  while (at + 8 <= b.length) {
    const id = b.toString('ascii', at, at + 4);
    const size = b.readUInt32LE(at + 4);
    if (id === 'fmt ') rate = b.readUInt32LE(at + 12);
    if (id === 'data') {
      // The sample rate is only known from `fmt `, which must come first; a reader that guessed would
      // silently mis-time every line.
      if (rate === null) throw new Error(`data chunk before fmt chunk in ${file}`);
      return { rate, pcm: b.subarray(at + 8, at + 8 + size) };
    }
    // Chunks are word-aligned: an odd size is followed by one pad byte.
    at += 8 + size + (size % 2);
  }
  throw new Error(`no data chunk in ${file}`);
}

module.exports = { readWav };
