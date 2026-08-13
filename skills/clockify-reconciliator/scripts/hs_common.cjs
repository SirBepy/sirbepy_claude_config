// Shared CLI/launch boilerplate for hs_preflight.cjs and hs_weekshot.cjs.
// Playwright resolution itself lives in skills/_shared/playwright-resolve.cjs (todo 295), shared
// with screenshot-helper.cjs so the fallback chain is defined once, not copied per skill.
const fs = require('fs');
const { getChromium } = require('../../_shared/playwright-resolve.cjs');

function getArg(args, flag, def = null) {
  const i = args.indexOf(flag);
  return i !== -1 ? args[i + 1] : def;
}

async function launchProfileContext(profile) {
  fs.mkdirSync(profile, { recursive: true });
  return getChromium().launchPersistentContext(profile, { headless: false });
}

module.exports = { getChromium, getArg, launchProfileContext };
