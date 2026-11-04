// Borrower app take: the links for the billers set up in the Admin Portal take.
const L = require('./lib.cjs');

const FIELD = 'input[data-semantics-role="text-field"]:not([disabled]), textarea[data-semantics-role="text-field"]:not([disabled])';

async function typeField(page, index, text) {
  await page.waitForSelector(FIELD, { timeout: 15000 });
  await page.waitForTimeout(500);
  const handles = await page.$$(FIELD);
  if (!handles[index]) throw new Error(`no field ${index}, found ${handles.length}`);
  const box = await handles[index].boundingBox();
  await L.moveClick(page, box.x + Math.min(box.width / 2, 160), box.y + box.height / 2);
  await page.waitForTimeout(350);
  await page.keyboard.type(text, { delay: 70 });
  await page.waitForTimeout(500);
}

async function button(page, name, timeout = 15000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    const hit = await L.find(page, name, { exact: true, role: 'button', timeout: 1000 });
    if (hit && !hit.disabled) {
      await L.moveClick(page, hit.x + hit.w / 2, hit.y + hit.h / 2);
      await page.waitForTimeout(900);
      return;
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`button ${JSON.stringify(name)} never enabled`);
}

async function mustSee(page, text, timeout = 15000) {
  if (!(await L.find(page, text, { timeout }))) throw new Error(`never saw ${JSON.stringify(text)}`);
}

async function mustNotSee(page, text) {
  if (await L.find(page, text, { timeout: 800 })) throw new Error(`should not show ${JSON.stringify(text)}`);
}

(async () => {
  const s = await L.open({ record: 'app' });
  const { page } = s;
  const step = L.stepper(page);
  let booted = false;
  const slugBodies = {};
  page.on('response', async (r) => {
    const m = r.url().match(/biller-groups\/slug\/([^/?]+)/);
    if (m && r.request().method() === 'GET') slugBodies[m[1]] = await r.json().catch(() => null);
  });

  // The boot of each link is cut from the video; a borrower's first load is not what this shows.
  async function load(path) {
    await page.evaluate(() => { sessionStorage.clear(); localStorage.clear(); }).catch(() => {});
    await L.goto(page, `${L.URLS.app}${path}`);
    await page.waitForTimeout(600);
    await L.find(page, 'Pay my bill', { exact: true, role: 'button', timeout: 30000 });
    await page.waitForTimeout(1800);
  }
  async function visit(path) {
    if (booted) { await L.skip(page, () => load(path)); return; }
    await load(path);
    L.begin(page);
    booted = true;
  }

  try {
    await step('Group link: landing page', async () => {
      await visit('/biller/cedar-valley');
      await L.say(page, 'The group link: /biller/cedar-valley', { min: 2600, speak: "The group's link." });
      const body = slugBodies['cedar-valley'];
      if (!body || body.displayName !== 'Cedar Valley Utilities') throw new Error(`slug answered ${JSON.stringify(body).slice(0, 200)}`);
      await button(page, 'Pay my bill');
    });

    await step('Group link: the search lists only billers that are on', async () => {
      await mustSee(page, 'Find your bill');
      await L.say(page, 'A group with several billers asks for the account number', 1400);
      await typeField(page, 0, '4521873690');
      await page.waitForTimeout(500);
      const box = await page.locator('input').last().boundingBox();
      await L.say(page, 'Then the Billing company search. Tap it without typing.', 1200);
      await L.moveClick(page, box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(1000);
      for (const n of ['Cedar Valley Electric', 'Cedar Valley Gas', 'Cedar Valley Water']) await mustSee(page, n, 5000);
      await mustNotSee(page, 'Cedar Valley Telecom');
      await mustNotSee(page, 'Cedar Valley Internet');
      await L.say(page, 'Only the 3 turned on in the Admin Portal. Telecom and Internet are off, so not listed.', 3800);
    });

    await step('Group link: typing narrows, picking reaches Does this look right?', async () => {
      await page.keyboard.type('wa', { delay: 160 });
      await page.waitForTimeout(800);
      await mustNotSee(page, 'Cedar Valley Gas');
      await L.say(page, 'Typing narrows the list', 1400);
      await L.click(page, 'Cedar Valley Water', { exact: true, after: 900 });
      await button(page, 'Find my bill');
      await mustSee(page, 'Does this look right?', 20000);
      await mustSee(page, 'Cedar Valley Water', 5000);
      await L.say(page, 'The number fits, so the borrower confirms that biller', 3000);
    });

    await step('Group link: a number that does not fit', async () => {
      await visit('/biller/cedar-valley');
      await button(page, 'Pay my bill');
      await mustSee(page, 'Find your bill');
      await typeField(page, 0, '12345');
      await page.waitForTimeout(500);
      const box = await page.locator('input').last().boundingBox();
      await L.moveClick(page, box.x + box.width / 2, box.y + box.height / 2);
      await page.waitForTimeout(900);
      await L.click(page, 'Cedar Valley Gas', { exact: true, after: 800 });
      await L.say(page, 'Same flow with a number that does not fit Gas', 1500);
      await button(page, 'Find my bill');
      await mustSee(page, 'Just a few more details', 20000);
      await L.say(page, 'The borrower is asked for more details', 2800);
    });

    await step("Electric's own link: its own name and logo, no search", async () => {
      await visit('/biller/cedar-electric');
      const body = slugBodies['cedar-electric'];
      if (!body || !body.isBillerSlug) throw new Error(`slug answered ${JSON.stringify(body).slice(0, 300)}`);
      await L.say(page, "Electric's own link: the name and logo set in the Admin Portal", 3800);
      await button(page, 'Pay my bill');
      await mustSee(page, 'Add your account');
      await mustNotSee(page, 'Find your bill');
      await L.say(page, 'Straight to Add your account. No search.', 2000);
      await typeField(page, 0, '4521873690');
      await button(page, 'Add your account');
      await mustSee(page, 'Cedar Electric Co-op', 20000);
      await L.say(page, 'Connected, under its own name', 3000);
    });

    await step("Water's own link: no name of its own, so the group's show", async () => {
      await visit('/biller/cedar-water');
      await L.say(page, "Water's link: no name or logo of its own, so the group's show", 3600);
      await button(page, 'Pay my bill');
      await mustSee(page, 'Add your account');
      await mustNotSee(page, 'Find your bill');
      await L.say(page, 'Still goes straight to Water', 1800);
    });

    await step("Telecom's link: off, so it goes to the group", async () => {
      // This boot stays in the video: the address changing is the point.
      await load('/biller/cedar-telecom');
      const path = new URL(page.url()).pathname;
      if (path !== '/biller/cedar-valley') throw new Error(`stayed on ${path}`);
      await page.evaluate(() => {
        const b = document.createElement('div');
        b.style.cssText = 'position:fixed;left:50%;top:12px;transform:translateX(-50%);padding:6px 14px;border-radius:6px;background:#fff;color:#111;border:1px solid #999;font:14px monospace;z-index:2147483647';
        b.textContent = location.href;
        document.body.append(b);
      });
      await L.say(page, 'Opened /biller/cedar-telecom. It is off, so the address changed to the group link.', { min: 4200, speak: "This opened Telecom's link. It is off, so the address changed to the group's link." });
    });
  } catch (e) {
    console.log('ABORTED', e.message);
  }
  await L.close(s, { slugBodies: Object.keys(slugBodies) });
})().catch((e) => { console.error('FAILED', e.message); process.exit(1); });
