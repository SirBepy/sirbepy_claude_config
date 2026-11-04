// Project layer over the test-report skill: local URLs, sign-in, ids. Local only.
const R = require('C:/Users/tecno/.claude/skills/test-report/scripts/recorder.cjs');
const F = require('C:/Users/tecno/.claude/skills/test-report/scripts/flutter.cjs');
const { chromium } = require('C:/Users/tecno/Desktop/Projects/zng-admin/e2e/node_modules/playwright');

const API = 'http://localhost:3009/api/core/';
const KEY = '123';
const OUT = process.env.REPORT_WORK;
if (!OUT) throw new Error('set REPORT_WORK to the report work folder');
const URLS = { ap: 'http://localhost:8190', app: 'http://localhost:8191', bp: 'http://localhost:8192' };
const GROUP = 'ced0ce00-0000-4000-8000-000000000001';
const biller = (n) => `ced0ce00-0000-4000-8000-2000000000${String(n).padStart(2, '0')}`;
const [vw, vh] = (process.env.VP || '1280x800').split('x').map(Number);

R.setup({ chromium, workDir: OUT, viewport: { width: vw, height: vh }, refuseUrls: /dev\.zirtue|ng\.zirtue|api\.zirtue/ });

async function apiLogin(email, { register = false } = {}) {
  const headers = { 'Content-Type': 'application/json', 'X-API-Key': KEY };
  const post = async (url, body) => {
    const r = await fetch(`${API}${url}`, { method: 'POST', headers, body: JSON.stringify(body) });
    return { status: r.status, json: await r.json().catch(() => ({})) };
  };
  let a = await post('auth/login', { email });
  let verify = 'auth/verify';
  if (!a.json.userId || register) {
    a = await post('auth/register', { email });
    verify = 'auth/register/verify';
  }
  if (!a.json.userId) throw new Error(`login ${email}: ${a.status} ${JSON.stringify(a.json).slice(0, 200)}`);
  const v = await post(verify, { userId: a.json.userId, code: '000000' });
  if (!v.json.accessToken) throw new Error(`verify ${email}: ${v.status} ${JSON.stringify(v.json).slice(0, 200)}`);
  return v.json;
}

const signIn = (a) => {
  for (const k of ['accessToken', 'accessTokenExpiresAt', 'refreshToken', 'refreshTokenExpiresAt', 'userId']) localStorage.setItem(k, a.auth[k]);
  if (a.seedGroup) {
    localStorage.setItem('billerPortal.selectedBillerGroupId', a.seedGroup);
    localStorage.setItem('billerPortal.selectedPortalType', 'billerGroup');
  }
};

async function open({ auth, record, seedGroup }) {
  const s = await R.open({ take: record, initScripts: auth ? [[signIn, { auth, seedGroup }]] : [] });
  s.apiErrors = [];
  s.page.on('response', (r) => {
    if (r.url().startsWith(API) && r.status() >= 400 && r.request().method() !== 'OPTIONS') s.apiErrors.push(`${r.status()} ${r.request().method()} ${r.url().replace(API, '')}`);
  });
  return s;
}

const close = (s, extra = {}) => {
  console.log('api errors', JSON.stringify(s.apiErrors));
  return R.finish(s, { apiErrors: s.apiErrors, ...extra });
};

module.exports = { ...F, begin: R.begin, skip: R.skip, caption: R.caption, say: R.say, stepper: R.stepper, apiLogin, open, close, URLS, GROUP, biller, OUT, API, KEY };
