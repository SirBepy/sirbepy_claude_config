// Shared CLI/launch boilerplate for hs_preflight.cjs and hs_weekshot.cjs.
// Playwright resolution itself lives in skills/_shared/playwright-resolve.cjs (todo 295), shared
// with screenshot-helper.cjs so the fallback chain is defined once, not copied per skill.
const fs = require('fs');
const { getChromium, assertNoAutomationLoginBlock } = require('../../_shared/playwright-resolve.cjs');

function getArg(args, flag, def = null) {
  const i = args.indexOf(flag);
  return i !== -1 ? args[i + 1] : def;
}

// firstTargetUrl is the URL the caller is about to page.goto() first; checking it here means a
// known-blocked login host (todo 816) fails before this visible, profile-persisted browser even
// launches, instead of after the dev is already staring at a rejected sign-in window. Optional -
// none of today's HubStaff callers ever target accounts.google.com, but the check is free and
// this is the one choke point all three scripts launch through.
async function launchProfileContext(profile, firstTargetUrl = null) {
  if (firstTargetUrl) assertNoAutomationLoginBlock(firstTargetUrl);
  fs.mkdirSync(profile, { recursive: true });
  return getChromium().launchPersistentContext(profile, { headless: false });
}

module.exports = { getChromium, getArg, launchProfileContext };
