<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# recall ingests what a Conductor sub decided, since subs never run /close

**Type:** skill-improvement
**Origin:** ai
**Summary:** Hidden sub chats in Claude Conductor skip `/close`, so what they decided never reaches `/recall` until something feeds their digest files in.

## Why

Subchats v1 (`claude_usage_in_taskbar`, todo pc-1597, spec section 10): "`/close` does not apply to subs, so they skip its digest and memory step. The finish fields feed the same digest, in the `## Decided` and `## Rejected` shape `permanent-memory.md` describes, so what a sub learned is not lost to `/recall`."

## Context

On every sub finish, the Conductor daemon writes the exact body `recall.py digest-save` takes on stdin to `<data_dir>/subchats/<sub_id>.digest.md`, where `<data_dir>` is `%APPDATA%\claude-conductor` for the default instance. It skips the file when the sub decided and ruled out nothing, the same bar `/close` uses. Code: `src-tauri/src/daemon/subchats/decisions.rs` in that repo, `on_finished`. UNVERIFIED by the filer against a live run: the exact data dir path, check `settings/paths.rs::resolve_data_dir` there.

`recall.py digest-save` redacts secrets, takes scope and repo from the recall index, and writes `~/.claude/memory-archive/digests/<sessionId>.md`. The daemon deliberately does not write there itself, because that is inside `~/.claude` and would skip redaction. A reader reported that `digest-save` accepts a session missing from the index and writes "(session not indexed)" in the header. A plain `digest-save` refuses to overwrite, and a continued sub finishes again, so re-ingesting needs `--replace`.

## Approach

Pick one:
1. `recall.py` ingests `<data_dir>/subchats/*.digest.md` when it refreshes its index, saving each with `digest-save --replace` under the sub's session id.
2. Claude Conductor calls `python ~/.claude/skills/recall/recall.py digest-save <sub_id>` itself on finish. This couples the app to a local skill path, so (1) is the likely pick.

## Done when

A sub that finishes with a decision shows up in `/recall` for that decision's words, and finishing it a second time updates the digest instead of failing.


## Notes

- Took approach 1: recall.py ingest_subchat_digests() runs on every index-backed command (not digest-save), reads %APPDATA%\claude-conductor\subchats\<uuid>.digest.md read-only (verified path: 19 real files, all ingest into a scratch archive), saves with replace when the source is newer than the digest. test_recall.py::test_subchat_digests failed before the change (no ingest_subchat_digests).