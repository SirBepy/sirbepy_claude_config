<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: new scripts from 2026-11-04, no existing todo covers d-cargo-sweep.ps1 tier D -->
# d-cargo-sweep.ps1 tier D keeps the newest hash per crate even when that hash has no built binary

**Type:** task
**Origin:** ai
**Summary:** Make the tier D keep rule retain the newest variant that actually has an exe or pdb, so a metadata-only hash cannot cause the only runnable test binary to be deleted.

## Goal

Tier D must never remove the only variant of a crate that carries `.exe` or `.pdb` files, whatever newer metadata-only hashes exist for it.

## Context

Found by the `/close` code-check of commits b4cb674 and f9b3753 (fresh subagent, 2026-11-04). Cost if it happens is a rebuild only (`.rlib`/`.rmeta` are never touched), not data loss.

- `skills/disk-doctor/d-cargo-sweep.ps1:158-178` groups deps files by crate and 16-hex hash and ranks units by the newest non-`.o` file; the loop at `:172` starts at index 1, so only index 0 is kept.
- A `cargo check` or metadata-only hash writes just `<crate>-<hash>.d` (`:167` counts `.d` as non-`.o`), so it can become index 0 while the only hash with `.exe`/`.pdb` sits at index 1, older than `-ObjDays`, and has its pdb/exe/d/o deleted at `:175`.
- A unit with only `.o` files has `Newest = MinValue` and ranks last, so it is deleted too.
- Whether this occurs on the real deps dir is UNVERIFIED; check by listing a crate with a recent `.d`-only hash.

## Approach

Make a unit eligible as the kept index 0 only if it has an `.exe` or `.pdb`; or keep both the newest unit overall and the newest unit that has an `.exe`. Rejected for now: skipping tier D entirely (the 119 GB reclaim on 2026-11-04 came from it).

## Acceptance

- A crate whose newest hash is `.d`-only keeps its newest `.exe`/`.pdb` hash in a preview run (`d-cargo-sweep.ps1 -Tiers D`, no `-Apply`).
- A normal crate still has all older variants listed for deletion.

## Notes

- fixed: tier D selection moved to d-cargo-sweep-lib.ps1 Get-TierDDeletions; keeps the newest hash overall plus the newest hash carrying an .exe/.pdb. Test skills/disk-doctor/test_d_cargo_sweep.ps1 (fake deps dir; red with the old keep rule). Whether the real D: deps dir has a metadata-only newest hash was not checked (listing is minutes on the HDD, verify only). Also did the 1312 optional StartsWith OrdinalIgnoreCase.
