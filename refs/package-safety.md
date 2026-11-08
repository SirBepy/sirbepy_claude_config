# Package safety reference

`CLAUDE.md` (Packages) holds the short rule. This file holds the detail moved out of it.

## The advisory check runs on the resolved tree

The advisory-DB check must run against the ACTUAL RESOLVED dependency tree, not just a registry lookup of the top-level package name: install for real (or resolve into a scratch lockfile), then run `npm audit --json` / `cargo audit` / equivalent post-resolution. A transitive dependency's CVE (filed against the sub-dependency's own name, e.g. a vulnerable package two levels down) will never surface from a pre-install, name-keyed lookup alone.
