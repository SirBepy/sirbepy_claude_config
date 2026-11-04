// Speech clips for the recorder, cached by text so a retake costs no generation time.
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const HOME = process.env.TEST_REPORT_HOME || path.join(process.env.LOCALAPPDATA || '', 'claude-test-report');
const PYTHON = path.join(HOME, 'venv', 'Scripts', 'python.exe');
const MODELS = path.join(HOME, 'models');
const CACHE = path.join(HOME, 'speech');
const VOICE = 'af_heart';

let child = null;
let ready = null;
let waiting = null;
let buffer = '';

function onLine(line) {
  let message;
  // onnxruntime and the phonemizer can print to stdout too; only our JSON lines count.
  try { message = JSON.parse(line); } catch { return; }
  if (message.ready) { ready.resolve(); return; }
  if (waiting) {
    const w = waiting;
    waiting = null;
    if (message.ok) w.resolve(); else w.reject(new Error(`speech failed: ${message.error}`));
  }
}

function start() {
  if (child) return ready.promise;
  if (!fs.existsSync(PYTHON)) throw new Error(`no voice installed: run ${path.join(__dirname, 'setup.ps1')}`);
  fs.mkdirSync(CACHE, { recursive: true });
  ready = {};
  ready.promise = new Promise((resolve, reject) => { ready.resolve = resolve; ready.reject = reject; });
  child = spawn(PYTHON, ['-I', path.join(__dirname, 'tts.py'), MODELS], { stdio: ['pipe', 'pipe', 'inherit'] });
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', (d) => {
    buffer += d;
    let at;
    while ((at = buffer.indexOf('\n')) >= 0) {
      onLine(buffer.slice(0, at).trim());
      buffer = buffer.slice(at + 1);
    }
  });
  child.on('exit', (code) => {
    const error = new Error(`voice process exited with ${code}`);
    ready.reject(error);
    if (waiting) waiting.reject(error);
    child = null;
  });
  // The voice process must never outlive the recording.
  process.on('exit', () => { if (child) child.kill(); });
  return ready.promise;
}

function lengthMs(file) {
  const b = fs.readFileSync(file);
  let at = 12;
  while (at < b.length) {
    const id = b.toString('ascii', at, at + 4);
    const size = b.readUInt32LE(at + 4);
    if (id === 'fmt ') var rate = b.readUInt32LE(at + 12);
    if (id === 'data') return Math.round(size / 2 / rate * 1000);
    at += 8 + size + (size % 2);
  }
  throw new Error(`no data chunk in ${file}`);
}

// Requests run one at a time: the protocol answers in order and a single voice is all the CPU should run.
let queue = Promise.resolve();

function speak(text) {
  const wav = path.join(CACHE, `${VOICE}-${crypto.createHash('sha1').update(text).digest('hex')}.wav`);
  const job = queue.then(async () => {
    if (!fs.existsSync(wav)) {
      await start();
      await new Promise((resolve, reject) => {
        waiting = { resolve, reject };
        child.stdin.write(`${JSON.stringify({ text, out: wav })}\n`);
      });
    }
    return { wav, ms: lengthMs(wav) };
  });
  queue = job.catch(() => {});
  return job;
}

function stop() {
  if (child) child.kill();
  child = null;
}

module.exports = { speak, stop, HOME };
