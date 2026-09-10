<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=8, reconfirm-count=1, content-hash=e1b83633 -->
<!-- duplicate-checked: grep for "preview" and "node -e" across ~/.claude/.claude/todos/ found no open item on this -->
# /preview's documented `node -e` one-liners are a parse error in PowerShell 5.1

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/preview/SKILL.md`'s copy-paste commands actually run on Joe's machine, where the default
shell is Windows PowerShell 5.1.

## Context

Found 2026-09-04 while pushing a mockup and an image gallery to the preview panel from the
claude_usage_in_taskbar project.

`SKILL.md` documents two `node -e "..."` one-liners:

- Step 2's "Primary: Node body-builder + curl.exe POST" - the JSON body builder.
- The Image branch's step 1 - the base64 gallery builder.

Both embed escaped double quotes inside a double-quoted argument. **PowerShell 5.1 fails these at
parse time**, before node is invoked:

```
At line:2 char:488
+ ... e style=\"margin:0 0 28px\"><img src=\"data:image/png;base64,'+b64+'\ ...
+                                                                 ~
Missing argument in parameter list.
    + CategoryInfo          : ParserError
```

The simple body-builder (step 2) happens to survive because its payload has no inner quotes; the
image-gallery one cannot, since it is building HTML attributes. Escaping does not rescue it - moving
to a single-quoted outer string just relocates the failure onto the inner `'` characters. The
working fix is to `Write` the builder to a `.mjs` file, run `node path\to\builder.mjs`, and delete
it, which is what this session did.

Note this is documented from the PowerShell side in the claude_usage_in_taskbar project memory
(`feedback_powershell_for_windows_flags`), but the skill itself still hands out the broken form, so
the next session re-derives the same failure.

## Approach

1. In `skills/preview/SKILL.md` step 2, keep the `node -e` form as the quick path but add a one-line
   caveat: any payload containing `"` needs the `.mjs` file variant on PowerShell.
2. Replace the Image branch's step 1 one-liner outright with the `.mjs` form - that one can never be
   quote-free, so leaving a broken command as the documented default is the actual defect.
3. Show the `.mjs` variant concretely: write to `.for_bepy/preview-build.mjs` (or `C:\tmp`), run it,
   delete it. Keep the existing 1.5MB raw budget and dropped-file reporting logic unchanged.
4. Check whether any sibling skill copies the same `node -e` shape and fix those too, rather than
   leaving the pattern to spread.

## Acceptance

- Both documented commands run as written in a PowerShell 5.1 tool call with a quote-containing
  payload and return the endpoint's `{"id": ...}`.
- `python ci/run_all.py` still passes (skill frontmatter + token budget checks).

## Notes

- DONE 2026-09-10 via /loop-todos cycle 2, and proven by running both forms rather than reasoning about quoting. skills/preview/SKILL.md:48 no longer uses a node -e one-liner carrying embedded double quotes; it writes a .mjs file to C:\tmp via the Write tool, runs node against it, then removes it, with the budget and drop-reporting logic carried over verbatim. Live evidence from this session PowerShell: the OLD form produced SyntaxError Unexpected token colon, matching the error this todo reported, and the NEW form printed out with included 1 dropped empty, with the generated HTML confirmed to carry a properly double-quoted img src data URI. The quote-free form further down at :62-66 was left alone because it genuinely works, verified by running it, and now carries a one-line note explaining WHY it survives (no embedded double quote) plus a pointer to the file variant for any payload that needs one. The whole skills tree was grepped for the same shape: the only other PowerShell-run instance, in supervised-run, is the quote-free shape and was executed to confirm it works; the react.yml one runs on a Linux CI runner and is out of scope. python ci/run_all.py exits 0.
