# Driving a Flutter web canvas with Playwright

Flutter web renders to `<canvas>`. There is no normal DOM to query until you
force the accessibility tree on. Everything below is a rule, not a suggestion
- each one was a silent, no-error failure mode before it was known.

## Activate the semantics tree first

Click the hidden `flt-semantics-placeholder` once per fresh page load, before
querying anything:

```js
page.evaluate(() => {
  const el = document.querySelector('flt-semantics-placeholder');
  if (el) el.click();
});
```

It sits off-viewport, so a normal Playwright click on it times out - dispatch
it via `evaluate`. After this fires, `flt-semantics` nodes populate the DOM
with `aria-label`/`role`/text. Without it, only a handful of nodes exist and
the rest stay hidden behind the canvas. Wait ~300-500ms after clicking before
the first query; a fresh route can take a beat to populate.

## Clicking semantics nodes

Never click by raw x/y coordinates. Locate the `flt-semantics` node and click
it directly.

**Atomic evaluate-dispatched click - use for anything just created or
changed by the previous action** (confirm bars, toasts, a button whose
label/count/enabled-state depends on prior state): find the node AND call
`.click()` on it inside one synchronous `page.evaluate()`. Flutter recreates
semantics nodes on label/state change; a two-step "get coordinates, then
click" - even via MCP's `browser_click` - has a round-trip gap where the old
node handle goes stale between the two calls. The click lands on a dead
reference and silently no-ops: no error, nothing happens, looks like the step
"did nothing" rather than "failed." This is the single most expensive-to-
diagnose landmine in this whole technique - don't skip the atomic form
because a step looks simple.

A two-step "query snapshot, then click by coordinate" is fine ONLY for a
widget you have not just interacted with in the last render pass.

**`flutter-view` intercepts pointer events on many button nodes** - a normal
`.click()` (mouse-event based) frequently gets swallowed by `<flutter-view>`
sitting above the semantics node in the z-stack, and times out with
"intercepts pointer events." Always dispatch the click via `.evaluate(el =>
el.click())` on the `flt-semantics` element itself, never a real mouse click.

**Disabled-state race:** a CTA's semantics node (e.g. "Next"/"Continue") can
exist in the DOM with `aria-disabled="true"` before its enabling state change
(a toggle flip, a selection) has round-tripped through `setState` to the next
Flutter frame. Clicking a matched-but-disabled node lands the click and it is
silently dropped by Flutter. Poll past disabled-only matches until an enabled
match appears (short timeout, then fall back to clicking the disabled node
anyway so the resulting failure surfaces downstream instead of a generic
"not found").

## Typing into fields

**Per-character typing, not `fill()` or a single `type()` across fields.**
Flutter web uses one global hidden `<input>` that "floats" to whichever text
field currently has focus. Consequences:

- `fill()` sets the DOM value directly and never reaches Flutter's own state
  - the app never sees the keystrokes.
- Typing into one field, then another, without an explicit click between
  them concatenates both values into whichever field has focus last. Both
  fields can visually appear to hold a value but only one actually does.
- Fix: click the target field's semantics node (or the enabled
  `input`/`textarea[data-semantics-role="text-field"]:not([disabled])`
  selector), `Control+A` to clear existing content, then
  `page.keyboard.type(text, { delay })` per field, in order.
- Tune `delay` (ms/keystroke) up from the ~20ms default for fields whose
  `onChanged` rewrites the controller's own text mid-typing (e.g. phone
  number dash auto-formatting) - too fast a delay races that rewrite and
  leaves the DOM holding raw, un-synced keystrokes instead of Flutter's
  reformatted value.

## Snapshot staleness

After typing or clicking, the semantic tree can lag the visual UI by a
second or two. If a button looks enabled in a screenshot but the snapshot
still marks it `[disabled]`, take a fresh snapshot after a short wait rather
than trusting the stale one - or trust the screenshot and attempt the click.
Always re-snapshot before looking up a node's DOM id/coordinates; don't reuse
one taken more than a step ago.

## Never reload mid-flow

Drive every transition through in-app navigation. Flutter streams update
live without a reload, and a full page reload can drop session/auth state
that lives only in memory or in a JS SDK that hasn't finished restoring by
the time the reload lands (worst case: an emulator-backed auth session gets
wiped). If a route seems stuck on first paint, that is a boot-timing issue
to retry/wait on, not a reason to reload.

## Release build, not DWDS

`flutter run` web (debug) serves through DWDS, which needs its own CDP
debugger attachment. Playwright's own CDP session conflicts with it and the
page hangs forever at "DDC is about to load ... scripts" - no error, no
timeout. Drive a `flutter build web` release bundle served statically
instead; debug/DWDS sessions are not drivable by raw Playwright. (Playwright
MCP against a human's own already-running debug session is a different,
supported shape - see plan-file mode - because the human owns that session
and Claude never touches DWDS's CDP attachment.)

## Headless guidance

Headless chromium works fine for driving Flutter web in general - it is not
a universal `headless: false` requirement. The one confirmed exception is
signing in through a **Firebase auth-emulator popup relay** (the "Continue
with Google" -> emulator popup -> `#add-account-button`/`#email-input`/
`#sign-in` flow): that relay hangs forever under headless chromium. Launch
headless only for flows that route through that specific popup relay; every
other flow, including ones that read/write local API + Postgres state
directly, can run headless.
