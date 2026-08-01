# disk-doctor — platform-file edit confirmation gate

Shared by `windows.md` and `macos.md`. Required before either platform file is edited with a
new SCAN LOG / KNOWN-SAFE / NEVER-TOUCH entry.

Output this exact format and wait for explicit YES before writing anything:

```
## PLATFORM-FILE-EDIT -- reply YES to apply
+ [SECTION-NAME] exact line to be added
```

- `SECTION-NAME` must be one of: `SCAN LOG`, `KNOWN-SAFE`, `NEVER-TOUCH`
- Claude resolves the section name to the matching header in the platform file being edited and appends the line there
- The `## PLATFORM-FILE-EDIT` sentinel line is required and must be reproduced verbatim
- Only lines beginning with `+` are written to the platform file
- No prose above or below the block
- A single gate block may contain multiple `+` lines targeting different sections
