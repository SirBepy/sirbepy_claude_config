---
name: work-recap-deck
description: Triggers on /work-recap-deck only. Turns merged GitHub PRs into a self-contained HTML deck with an embedded, syntax-highlighted diff explorer.
argument-hint: "[author] [since-date]"
---

# /work-recap-deck

> Turn a set of GitHub PRs into a presentation deck with an embedded PR/diff explorer.

Builds a single self-contained `.html` file: a slide deck that groups PRs into narrative
"arcs" (What/Why/Impact), where each arc slide reveals in two beats then shows an embedded
viewer with the real, syntax-highlighted diffs. Bundled assets live next to this file:
`build-deck.mjs` (generator), `template.html` (styled shell), `deck.config.example.json` (schema example).

Needs `gh` authenticated and `node`. The generator runs `gh pr view/diff`, so run it from inside
the target repo OR set `"repo": "owner/name"` in the config.

## Step 1 - Gather the PRs

Ask the dev whose work and what window (default: the merged PRs authored by the current `gh` user).
List candidates with `gh pr list --author <login> --state merged --limit 60 --json number,title,mergedAt`.
Confirm the set before writing narrative.

## Step 2 - Group into arcs and draft the narrative

Cluster the PRs into a handful of themed streams (the "arcs"), ordered as a story. For each arc draft:
- a plain-language `story` headline (what the stream accomplished),
- `what` (bullets, the concrete work - lead with this; it is what the viewer wants first),
- `why` (one sentence of context/problem),
- `impact` (bullets, the result).
Keep copy clear and specific, not over-summarized. The wording is the dev's to approve - present
drafts and revise on feedback; do not treat your first pass as final.

## Step 3 - Write the config

Write `deck.config.json` matching this schema (see `deck.config.example.json` for a full sample):

| Key | Meaning |
|---|---|
| `repo` | Optional `owner/name`; omit if running inside the repo |
| `title` | `{line1, line2, name, role, dates}` for the opening slide |
| `stats` | Opening `[{n, l}]` counters (e.g. PRs merged, days) |
| `overviewTitle` / `overviewLede` | Headline + lede for the overview slide |
| `arcs[]` | `{title, icon, desc, story, why, what[], impact[], prs}` |
| `arcs[].icon` | A Phosphor icon name (e.g. `shield-check`, `database`, `browsers`) |
| `arcs[].prs` | `[[number, "short title"], ...]` in display order |
| `closing` | `{title, stats:[{n,l}], takeaways:[]}`; takeaways may use `<b>` |

## Step 4 - Generate

Run the bundled generator (absolute path to this skill folder):

```
node "<skill-dir>/build-deck.mjs" deck.config.json work-recap-deck.html
```

It fetches each PR, bakes the diffs in, and writes one self-contained HTML file (typically a few MB).
For a personal recap, write output under a gitignored path (e.g. `.for_bepy/presentations/`).

## Step 5 - Preview and verify

Open the file in a browser, or headless-screenshot to verify it rendered (a blank page usually means
diff content broke the inline data - the generator already escapes `<`, so rebuild if you edited the
template). Deep-links: `#s4` a slide's intro, `#s4full` its revealed state, `#pr-72` a specific PR.

Controls in the deck: **left / right** step through reveal beats and slides, **up / down** switch PRs
within an arc, **F** fullscreen.

## Step 6 - Iterate

Reword arcs per the dev's feedback and re-run Step 4. Only the config changes between runs; the
template and generator stay put.
