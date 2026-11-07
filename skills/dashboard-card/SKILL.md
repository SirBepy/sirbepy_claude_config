---
name: dashboard-card
description: Use when asked to show a metric on a project's dashboard. Tests then upserts a Conductor card.
argument-hint: "<what to show, e.g. days since the last audit> [--action /skill]"
---

# /dashboard-card

> "Show X on the dashboard" from any repo: a card that renders real data on the first save.

Joe (2026-10-30), after hand-building the `~/.claude` "days since the last audit" card: "honestly,
we should make a skill for that". The tool is `mcp__cc_conductor__dashboard_card`, a Conductor-only
MCP tool. Outside Conductor it does not exist: say so and stop.

## Before the first call

The tool is DEFERRED: only its name is known until its schema loads. Load it once, then use the
real params:

```
ToolSearch  query: select:mcp__cc_conductor__dashboard_card
```

Calling a deferred Conductor tool from guessed params wasted several failed calls in the 2026-10-27
`claude_usage_in_taskbar` chat about a broken Clockify dashboard card (the blind-call pattern is
written up in todo 1252; the other tools there were `send_message` and `write_draft`, this one was
not shown failing).

## Steps

1. **Pin the reading.** What number or list, from where, how fresh, and what should one click do
   (an `action` button that starts a chat running a skill or a short prompt on the card's data).
2. **`list` first.** Cards are per project (`scope` defaults to this project). An existing card for
   the same thing is edited by `upsert` with its `id`; omitting `id` creates a second one.
3. **Pick the source.**
   - `command`: a local script or CLI that prints JSON. The default for anything derived from
     files, git, a ledger, `gh`, or several calls stitched together. Use an absolute script path
     (the working `~/.claude` card does) so the card does not depend on which checkout runs it.
   - `http`: one API call whose JSON already has the shape you display. Secrets as
     `{{secret:NAME}}` in url/headers/body.
4. **Write the script when a command needs one.** It prints exactly one JSON object on stdout and
   nothing else (logs go to stderr), exits non-zero on failure, and may carry a `_card` block
   (recipe below). Reference: `skills/global-claude-folder-audit/days_since.py` (reads a committed
   ledger, so a chat that died half-way does not count as a run).
5. **Check the output offline,** before touching the tool:
   ```powershell
   python <script> | python "C:\Users\tecno\.claude\skills\dashboard-card\check_card_output.py" --paths days_since,last_run
   ```
   `--paths` lists every path the display will read. This matters because the tool answers a wrong
   path or non-JSON stdout with a `-` value and **no error** (probed 2026-11-07), so a broken card
   looks like a working one with an empty reading.
6. **`test` the card** (`action: test`, same `card` object). Read `result`: `error` must be null and
   every `stats` value real, none `-`. Fix and `test` again until it is.
7. **`upsert`.** An enabled card runs once on save and returns its `result`; check it again, it
   is the first thing the dashboard shows. Then say what the card shows and where.
8. **`pin`** only when Joe asks for quick-action chips: a list of slash commands (max 20, never
   `/close`); `[]` clears them.

## The card object

```json
{
  "title": "Global .claude audit",
  "source": {"kind": "command", "program": "python", "args": ["C:/path/to/script.py"]},
  "display": {"kind": "stats", "items": [{"label": "Days since", "path": "days_since", "format": "number"}]},
  "action": {"label": "Run audit", "command": "/global-claude-folder-audit"},
  "refresh_secs": 3600
}
```

- Templates usable in url, headers, body, args, env, cwd: `{{secret:NAME}}` (from `~/.claude/.env`),
  `{{cwd}}`, `{{repo}}`, `{{today}}` (verified: becomes `2026-11-07` in args), `{{week_start}}`,
  `{{now_iso}}`, `{{last_run:/cmd}}` (epoch ms of the latest chat run of that slash command; 0 if never).
- **Secrets go through `env`, never `args`:** `"env": {"API_TOKEN": "{{secret:CLOCKIFY_API_KEY}}"}`
  (args show up in process listings). Never write a secret value into a card. UNVERIFIED: no
  secret call was made in the probes; the rule is from the tool's own schema.
- `format`: `number | text | count | duration_s | duration_ms | duration_iso | relative_time`.
  **`count` counts a list's items and shows `-` for a plain number** (probed: `items:[1,2,3]` gives
  3, `n: 3` gives `-`), so use `number` for a number. `sum(items)` works as a path.
- Path syntax: dotted, `[n]`, `[]` (map over a list), `sum(...)`.

## `_card`: headline, progress, segments

A command's JSON may carry a top-level `_card`; then `display` can be `{"kind":"stats","items":[]}`.
All of this renders from the probe on 2026-11-07:

```json
{"_card": {
  "headline": "8 days since last audit", "headline_tone": "good",
  "progress": {"value": 3, "max": 10, "label": "3 of 10"},
  "segments": {"items": [{"label": "done", "value": 6}, {"label": "open", "value": 2}],
               "max": 10, "note": "2 left", "note_tone": "warn"}
}}
```

- Tones are `warn` or `good` only. Headline tone is the nudge: amber when something wants
  attention (past a threshold you pick and comment in the script), green otherwise.
- Charts: `segments` is one bar split into labelled slices sized value/max (add `marker` for a
  pace tick); `progress` is a single filled bar. Values must add up to no more than `max`.
  `check_card_output.py` checks the shape.

## One example per display kind

**stats** (the days-since card): `display` as in the card object above; script prints
`{"last_run": "2026-10-30", "days_since": 8, "runs": 1, "_card": {"headline": "8 days since last audit", "headline_tone": "good"}}`.
Use `number` for `runs`, not `count`.

**list** (rows of label, value, optional link): script prints
`{"items": [{"name": "a", "n": 3, "url": "https://example.com/a"}]}` and the display is
`{"kind": "list", "items_path": "items", "label_path": "name", "value_path": "n", "link_path": "url", "limit": 5}`.
A script that gets a bare list from a CLI (`gh run list --json ...`) wraps it in an object first,
because the paths are read from an object.

**html** (static markup only): `{"kind": "html", "template": "<div style=\"color: var(--color-text)\">...</div>"}`.
It renders in a sandboxed frame with no network, and **inline `<script>` does not run in the
installed app**, so nothing may depend on `window.CARD_DATA` or script-drawn charts. Theme colours
are CSS variables (`--color-text`, `--color-accent`). `test` returns the fetched `data`, not the
rendered page, so an html card is only confirmed by looking at the dashboard; UNVERIFIED: how
fetched values are placed into a template. Prefer `stats` or `list` plus `_card` whenever the card
shows numbers.

## Failures the tool reports

| `result.error` | Cause |
|---|---|
| `python exited with code 3: <stderr>` | the script failed; fix it, stderr is shown |
| `could not start <program>: program not found` | wrong `program` or not on PATH |
| none, but every value `-` | stdout was not one JSON object, or a `path` does not exist: run `check_card_output.py` |

## Rules

- Never `upsert` before a clean `test`. Never leave a probe card behind: `test` creates nothing,
  `upsert` does, and `delete` takes an `id` from `list`.
- A card shows one answer. Two metrics that need different refresh rates or actions are two cards.
- `refresh_secs`: slow for file-derived numbers (3600), faster only for something that moves
  inside an hour; an http source pays a request per refresh.

## Test

`python skills/dashboard-card/test_check_card_output.py` (stdlib only).
