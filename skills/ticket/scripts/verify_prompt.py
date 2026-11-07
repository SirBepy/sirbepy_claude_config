#!/usr/bin/env python3
"""Print the finished outbound-verify prompt for one draft: the same text for all 3 dispatches.

`refs/outbound-verify.md` has the verifier template; this fills its placeholders from a small
spec file and inlines the draft between the `<<<OUTBOUND-DRAFT` lines the hook matches on. A
re-round is: edit the draft file, rerun this, paste the output into 3 Agent calls. Nothing
about the pasted prompt changes how `hooks/outbound-verify-guard.py` matches it.

The template is read from the ref at run time (its fenced block that opens with
`READ-ONLY DISPATCH`), never copied here, so the two cannot drift. If a placeholder is no
longer in the ref, the script stops instead of printing a prompt with a hole in it.

Usage:
    python verify_prompt.py <spec.md> [--out FILE] [--ref refs/outbound-verify.md]

Spec file: `## Section` headings, one value each. Relative paths resolve against the spec's
own folder.

    ## Target        a Shortcut ticket | a Linear issue | a GitHub PR
    ## Repo          absolute path of the repo the text talks about
    ## Branch        tracked branch, without the origin/ prefix
    ## Pointers      files, ticket ids, PR numbers, endpoints the text talks about
    ## Provenance    who asked for this posting and what it descends from
    ## Sources       (tickets) requirement-to-source list; optional
    ## Fields        planned non-text fields (team, epic, owner, state, links); optional
    ## Draft path    file holding the exact text to be posted
"""

import argparse
import re
import sys
from pathlib import Path

DEFAULT_REF = Path(__file__).resolve().parents[3] / "refs" / "outbound-verify.md"
TEMPLATE_OPENER = "READ-ONLY DISPATCH"
DRAFT_CLOSER = "OUTBOUND-DRAFT>>>"

REQUIRED = ("target", "repo", "branch", "pointers", "provenance", "draft path")
OPTIONAL = ("sources", "fields")

# Placeholder text exactly as it stands in the ref's template.
PLACEHOLDERS = {
    "target": "<a Shortcut ticket / a Linear issue / a GitHub PR>",
    "repo": "<absolute path>",
    "branch": "<branch>",
    "pointers": "<files, ticket ids, PR numbers, endpoints the text talks about>",
    "provenance": "<who asked for this posting, and what it descends from - a todo id, a ticket, a PR>",
    "draft": "<the exact text, verbatim>",
}


class SpecError(Exception):
    pass


def extract_template(ref_text: str) -> str:
    """The first fenced block of the ref whose first line is READ-ONLY DISPATCH."""
    for m in re.finditer(r"^```[^\n]*\n(.*?)^```[ \t]*$", ref_text, re.DOTALL | re.MULTILINE):
        block = m.group(1)
        if block.lstrip().startswith(TEMPLATE_OPENER):
            return block.rstrip("\n")
    raise SpecError(f"no fenced block starting with {TEMPLATE_OPENER!r} in the ref")


def parse_spec(text: str) -> dict:
    sections: dict = {}
    current = None
    for line in text.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def fill(template: str, spec: dict, draft: str) -> str:
    pointers = spec["pointers"]
    for key, title in (("sources", "Requirement-to-source list"), ("fields", "Planned non-text fields")):
        if spec.get(key):
            pointers += f"\n\n{title}:\n{spec[key]}"
    values = {
        "target": spec["target"],
        "repo": spec["repo"],
        "branch": spec["branch"],
        "pointers": pointers,
        "provenance": spec["provenance"],
        "draft": draft,
    }
    # The ref wraps its prose, so a placeholder may span a line break: match on whitespace runs.
    patterns = {k: re.compile(r"\s+".join(re.escape(w) for w in p.split())) for k, p in PLACEHOLDERS.items()}
    for key, pattern in patterns.items():
        if not pattern.search(template):
            raise SpecError(f"the ref's template no longer contains {PLACEHOLDERS[key]!r}; update PLACEHOLDERS")
    # One pass, so a value that happens to contain another placeholder is never filled twice.
    combined = re.compile("|".join(f"(?P<{k}>{p.pattern})" for k, p in patterns.items()))
    return combined.sub(lambda m: values[m.lastgroup], template)


def build_prompt(spec_path: Path, ref_path: Path) -> str:
    spec = parse_spec(spec_path.read_text(encoding="utf-8-sig"))
    missing = [k for k in REQUIRED if not spec.get(k)]
    if missing:
        raise SpecError(f"spec {spec_path} lacks section(s): {', '.join('## ' + m for m in missing)}")
    unknown = sorted(set(spec) - set(REQUIRED) - set(OPTIONAL))
    if unknown:
        raise SpecError(f"spec {spec_path} has unknown section(s): {', '.join('## ' + u for u in unknown)}")

    draft_path = Path(spec["draft path"].strip("`\"' "))
    if not draft_path.is_absolute():
        draft_path = spec_path.parent / draft_path
    try:
        draft = draft_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip("\n")
    except OSError as e:
        raise SpecError(f"cannot read the draft {draft_path}: {e}")
    if not draft.strip():
        raise SpecError(f"the draft {draft_path} is empty")
    if DRAFT_CLOSER in draft or "<<<OUTBOUND-DRAFT" in draft:
        raise SpecError("the draft contains an OUTBOUND-DRAFT marker line, which would end the block early")

    template = extract_template(ref_path.read_text(encoding="utf-8-sig").replace("\r\n", "\n"))
    return fill(template, spec, draft) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="verify_prompt.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, default=None, help="write the prompt here instead of stdout")
    parser.add_argument("--ref", type=Path, default=DEFAULT_REF, help="outbound-verify ref holding the template")
    args = parser.parse_args(argv)
    try:
        prompt = build_prompt(args.spec, args.ref)
    except SpecError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    data = prompt.encode("utf-8")
    if args.out:
        args.out.write_bytes(data)
    else:
        sys.stdout.buffer.write(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
