# Degraded documentation pass

Used two ways: as the prompt handed to a fresh `general-purpose` subagent when
the harness has a subagent tool but no agent type registered under the name
`impeccable-documenter`, or followed in-thread on a harness with no subagent
tool at all.

## Inputs

The project root, the artifact path, the direction contract, `PRODUCT.md`,
the [document.md](../document.md) reference path, and the boundary to write
at (the project root for `DESIGN.md`, `.impeccable/design.json` for the
sidecar).

## What to do

There is no separate contract here: follow [document.md](../document.md)'s
own steps directly against the inputs above. That file already is the full
recipe (frontmatter token schema, the eight-section body, the Step 4b
sidecar) - a documenter agent does not get a different process, only a
different runner.

The one rule worth repeating because it is the one a direction contract
tempts a model to skip: tokens come from the **built** code and rendered
screenshots, not from the direction contract's intention. A contract says
what the build was supposed to be; `DESIGN.md` records what it actually is.
Where they disagree, the built world wins and the disagreement is worth a
one-line note back to the caller.

## Degraded disclosure

One line in the caller's final report:
`⚠️ DEGRADED: documentation ran via <general-purpose agent|in-thread pass> (no impeccable-documenter agent type on this harness)`.
