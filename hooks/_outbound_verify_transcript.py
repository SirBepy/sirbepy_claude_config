"""Transcript-verdict tally for outbound-verify-guard.py (todo 1088 split).

Reads the session transcript (`transcript_path` in the hook payload) for Agent/Task
dispatches that carry an `<<<OUTBOUND-DRAFT ... OUTBOUND-DRAFT>>>` block, matches each
dispatch to its `OUTBOUND-VERDICT: PASS|FAIL` report wherever the harness delivers it (the
tool_result inline, an async `<agent-message>` hand-back, or a sync hand-back enqueued
before the tool_result that names its agentId), and tallies PASS/FAIL per distinct
(whitespace-normalized) draft text. `uncovered()` then answers, for a list of outbound
values, which ones no cleared draft (>= REQUIRED_PASSES PASS, zero FAIL) contains.

Split out of outbound-verify-guard.py, which keeps outbound-call detection and main();
this module owns none of the detection regexes or PROSE_KEYS, only the transcript side.
"""

import json
import re

REQUIRED_PASSES = 3
MIN_PROSE_CHARS = 25

DRAFT_RE = re.compile(r"^[ \t]*<<<OUTBOUND-DRAFT[^\n]*\n(.*?)\n[ \t]*OUTBOUND-DRAFT>>>", re.DOTALL | re.MULTILINE)
VERDICT_RE = re.compile(r"^[ \t]*OUTBOUND-VERDICT:[ \t]*(PASS|FAIL)[ \t]*$", re.MULTILINE)
AGENT_MESSAGE_RE = re.compile(r'<agent-message from="([^"]+)">(.*?)(?:</agent-message>|\Z)', re.DOTALL)
TASK_NOTIFICATION_RE = re.compile(r"<tool-use-id>([^<]+)</tool-use-id>.*?<result>(.*?)</result>", re.DOTALL)


def normalize(text: str) -> str:
    return " ".join(text.split())


def entry_strings(entry: dict) -> list:
    """Every string in a transcript entry that can carry a harness-delivered hand-back."""
    out = []
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        out.append(content)
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                out.append(block.get("text") or "")
    if isinstance(entry.get("content"), str):
        out.append(entry["content"])
    attachment = entry.get("attachment")
    if isinstance(attachment, dict) and isinstance(attachment.get("prompt"), str):
        out.append(attachment["prompt"])
    return out


def tool_result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text") or "" for b in content if isinstance(b, dict))
    return ""


def load_verdicts(transcript_path: str) -> dict:
    """Map each normalized draft to its {"PASS": n, "FAIL": n} tally from the transcript."""
    drafts_by_dispatch: dict = {}
    dispatch_by_agent: dict = {}
    # (line index, text): the latest report wins, since a resumed verifier reports again.
    reports: dict = {}
    # A sync agent's hand-back is enqueued BEFORE the tool_result that names its agentId,
    # so agent messages are resolved to dispatches only after the whole file is read.
    agent_reports: list = []

    with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
        for seq, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict) or entry.get("isSidechain"):
                continue

            content = (entry.get("message") or {}).get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if (
                        entry.get("type") == "assistant"
                        and block.get("type") == "tool_use"
                        and block.get("name") in ("Agent", "Task")
                    ):
                        tool_input = block.get("input") or {}
                        if tool_input.get("subagent_type") == "fork":
                            continue
                        drafts = {normalize(d) for d in DRAFT_RE.findall(tool_input.get("prompt") or "")}
                        drafts.discard("")
                        if drafts:
                            drafts_by_dispatch[block.get("id")] = drafts
                    elif block.get("type") == "tool_result" and block.get("tool_use_id") in drafts_by_dispatch:
                        dispatch_id = block["tool_use_id"]
                        result = entry.get("toolUseResult")
                        if isinstance(result, dict) and result.get("agentId"):
                            dispatch_by_agent[result["agentId"]] = dispatch_id
                        text = tool_result_text(block)
                        if VERDICT_RE.search(text):
                            reports[dispatch_id] = (seq, text)

            if entry.get("type") == "assistant":
                continue
            for text in entry_strings(entry):
                if "<agent-message" in text:
                    for agent_id, body in AGENT_MESSAGE_RE.findall(text):
                        if VERDICT_RE.search(body):
                            agent_reports.append((seq, agent_id, body))
                if "<task-notification>" in text:
                    for dispatch_id, body in TASK_NOTIFICATION_RE.findall(text):
                        if dispatch_id in drafts_by_dispatch and VERDICT_RE.search(body):
                            reports[dispatch_id] = (seq, body)

    for seq, agent_id, body in agent_reports:
        dispatch_id = dispatch_by_agent.get(agent_id)
        if dispatch_id and (dispatch_id not in reports or seq >= reports[dispatch_id][0]):
            reports[dispatch_id] = (seq, body)

    tally: dict = {}
    for dispatch_id, drafts in drafts_by_dispatch.items():
        verdict = None
        if dispatch_id in reports:
            verdict = VERDICT_RE.findall(reports[dispatch_id][1])[-1]
        for draft in drafts:
            counts = tally.setdefault(draft, {"PASS": 0, "FAIL": 0, "PENDING": 0})
            counts[verdict or "PENDING"] += 1
    return tally


def uncovered(values: list, tally: dict) -> list:
    """Return (snippet, reason) for each checked value no cleared draft contains."""
    cleared = [d for d, c in tally.items() if c["PASS"] >= REQUIRED_PASSES and c["FAIL"] == 0]
    misses = []
    for value in values:
        norm = normalize(value)
        if len(norm) < MIN_PROSE_CHARS or any(norm in d for d in cleared):
            continue
        holders = [c for d, c in tally.items() if norm in d]
        if not holders:
            reason = "no verifier dispatch carries this text"
        else:
            best = max(holders, key=lambda c: (c["FAIL"] == 0, c["PASS"]))
            reason = f"best draft holding it has {best['PASS']} PASS, {best['FAIL']} FAIL, {best['PENDING']} without a verdict"
        snippet = norm if len(norm) <= 70 else norm[:67] + "..."
        misses.append((snippet, reason))
    return misses
