<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped ~/.claude/.claude/todos/ (backlog + done/) for "screenshot-helper", "evaluate",
     "--plan". Nothing covers it. -->
# screenshot-helper discards every evaluate result

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/screenshot/screenshot-helper.cjs` print what an `evaluate` step returns, so `/mockup`
step 5's mandatory computed-style and geometry checks can be read directly instead of through a
workaround.

## Context

`screenshot-helper.cjs:272` is:

```js
case 'evaluate':
  await page.evaluate(step.js);
  break;
```

The return value is dropped on the floor. Nothing else in the plan runner surfaces it, and page
`console` is not forwarded either.

`/mockup`'s SKILL.md step 5 REQUIRES reading `getComputedStyle` and `getBoundingClientRect` values
back ("Computed style, not a glance", "Geometric/numeric claims, measured"). With the return value
discarded there is no supported way to do that.

Measured cost, claude_usage_in_taskbar session 2026-08-24: the workaround is to have the evaluate
step build a `<pre>`, inject it over the page, screenshot it, and OCR the numbers off the image by
reading the PNG back. That was done SIX times in one session. It works, but it turns a numeric
assertion into an image the model has to read, which is both slower and less reliable than a
string - and it silently biases toward not doing the check at all.

## Approach

In the `evaluate` case, capture the result and print it when it is not `undefined`:

```js
case 'evaluate': {
  const out = await page.evaluate(step.js);
  if (out !== undefined) console.log('evaluate:', typeof out === 'string' ? out : JSON.stringify(out));
  break;
}
```

Optionally accept `{"type":"evaluate","js":"...","label":"..."}` and prefix the label, so a plan
with several evaluates is readable.

Then update `skills/mockup/SKILL.md` step 5 to say the values are printed, and drop any implied
render-to-page workaround.

## Acceptance

- A plan with `{"type":"evaluate","js":"(function(){return {a:1};})()"}` prints `evaluate: {"a":1}`.
- An evaluate returning nothing prints nothing (no `evaluate: undefined` noise).
- A `/mockup` run can assert a computed style without screenshotting a `<pre>`.
