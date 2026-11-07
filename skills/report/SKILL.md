---
name: report
description: Triggers on /report only. Turns findings into one fixed-layout, self-contained HTML report in Conductor's preview.
disable-model-invocation: true
argument-hint: "<topic or what to report on> [--slug <name>]"
---

# /report

> One report layout, every time, so what Joe reads is exactly what he can share.

Joe (2026-10-20): "sometimes youll make me a /report ... and whatever that looks like is what we
should share with others". Conductor's "Publish to claude.ai" button uploads the previewed page
as-is, so this skill pins the page: the same header, summary box, stat tiles, numbered sections
and footer on every report, and nothing in it that fetches or runs.

## When to use

Only on `/report <topic>`. Not for a mockup (`/mockup`), a screenshot gallery or a markdown doc
(`/preview`), or a chat answer: a report is findings Joe wants to keep or send on.

## Steps

1. **Gather first.** Do the investigation the topic needs. Every number and claim in the report
   needs a receipt (a file read, a command's output, a fetched URL) from this session, same rule as
   any outbound text. If a figure cannot be checked, leave it out or say "unverified" in the text.
2. **Write the spec** as JSON to `.for_bepy/reports/<slug>.json` (scratch, gitignored). Fields:

   | Field | Required | Meaning |
   |---|---|---|
   | `title` | yes | Page title |
   | `summary` | yes | String or list of strings: the answer in 1-3 sentences, a reader who stops here still gets it |
   | `sections` | yes | List of `{ "heading": str, "blocks": [...] }`, numbered 1..N in order |
   | `kicker`, `subtitle`, `date`, `author`, `scope` | no | Header strings; kicker defaults to "Report" |
   | `stats` | no | Tiles: `{ "label", "value", "note"?, "tone"? }`; 2-6 read best |
   | `next_steps`, `open_questions` | no | Lists of strings |
   | `sources` | no | Strings or `{ "label", "url"? }` (url must be http/https) |

   A block is exactly one of: `{"p": str}`, `{"bullets": [str]}`, `{"numbered": [str]}`,
   `{"code": str}`, `{"callout": str, "tone"?: tone}`, `{"table": {"columns": [..], "rows": [[..]]}}`.
   Tones are `good`, `warn`, `bad`, `neutral`; the first three also print a word (OK, Watch,
   Problem) so the signal is never colour alone, and `neutral` is plain by design. Strings take `**bold**` and `` `code` `` only; everything else is escaped, so raw
   HTML in a spec shows as text.
3. **Build:**
   ```powershell
   python "C:\Users\tecno\.claude\skills\report\build_report.py" .for_bepy\reports\<slug>.json
   ```
   It prints the HTML path, or exits 1 naming the field at fault ("bad spec: sections[0].blocks[2]
   needs exactly one of ..."); fix the spec and rerun. Source `url`s must start with `http://` or
   `https://`; table cells and stat values must be strings or numbers.
4. **Push through `show_preview`** with `slug: report-<slug>` and the built file's text as `html`,
   passed through unchanged (a retyped page can drift from the file). Reports are small enough to
   pass inline. The page carries `<meta name="preview-template"
   content="bare">` because it owns its layout (860px column, light/dark, phone cards for tables,
   print CSS), so the panel adds no second padding. Re-push the same slug to revise in place.
   Where `show_preview` is unavailable (no Conductor tool), `build_report.py <spec> --post` pushes
   through `skills/preview/push_html.py` instead; with Conductor not running, say so and give the
   file path.
5. **Tell Joe where it is:** `show_preview` lands the report as a card in the chat that he can
   promote to the preview panel; per todo 1209 Conductor's Publish to claude.ai button shares the
   previewed HTML as-is (UNVERIFIED here: the button was not exercised). One line; do not paste the
   report body into chat.

## Rules

- **The layout is fixed.** A report that needs a different shape (a timeline, a chart) gets the
  closest blocks here, or the content goes in `/mockup` instead. Do not hand-write report HTML or
  edit the CSS for one report. A layout change belongs in `build_report.py` and its test; from a
  session in another project, file it as a todo in `C:\Users\tecno\.claude\.claude\todos\` instead
  of editing it there.
- **Self-contained, no fetch.** No script, no web font, no CDN, no image URL, and no icon library
  (Phosphor included): a published copy may be offline or sandboxed, and anything that loads would
  look different for the teammate. Tone words and colour carry the signal instead. Charts are out;
  put the figures in a table or stat tiles.
- **Summary first, decisions last.** Put what Joe must decide under `open_questions`, not buried in
  a section.
- Keep one report per topic; a new topic gets a new slug.

## Test

`python skills/report/test_build_report.py` (stdlib only, no Conductor needed).
