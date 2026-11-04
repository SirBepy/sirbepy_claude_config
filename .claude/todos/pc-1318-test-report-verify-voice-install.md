<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: new skill from pc-1315, whose scope did not cover this. -->
# /test-report: pin the voice install to what was audited

**Type:** task
**Origin:** ai
**Summary:** The voice setup should check model file hashes and install exactly the package set that passed the audit.

## Goal

Re-running `setup.ps1` on any machine gives exactly what passed the 2026-11-04 safety check.

## Context

Found by /code-check. `skills/test-report/scripts/setup.ps1:23` checks the two downloaded model files (353MB from a GitHub release) by byte length only. `setup.ps1:19` pins six top-level packages but no transitive ones, so the resolved tree can drift from what was audited. Global `CLAUDE.md`'s Packages section requires the advisory check to run against the actual resolved tree. `pip-audit` on the installed venv reported "No known vulnerabilities found" on 2026-11-04.

## Approach

1. Hash the installed `kokoro-v1.0.onnx` and `voices-v1.0.bin` in `%LOCALAPPDATA%\claude-test-report\models` and compare with `Get-FileHash` in `setup.ps1`.
2. Generate a hashed requirements file from that venv, kept next to `setup.ps1`, and install with `--require-hashes`.

## Acceptance

- `setup.ps1` in an empty `TEST_REPORT_HOME`-style location fails on a tampered model file and installs cleanly otherwise.
- Speech still generates.
