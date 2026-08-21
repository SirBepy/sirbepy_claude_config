# Confusion patterns, derived from this repo's own failures

Eight root causes, each drawn from real skill-improvement todos in `.claude/todos/done/`. Cite the
pattern number in the diagnosis so a second heal of the same skill can tell whether the previous
fix addressed the same cause.

**Why these and not the upstream seven.** `justcarlson/heal-skill` ships a taxonomy of seven
(ambiguous branching, missing examples, implicit file references, missing variables, unclear
workflow, wrong tool, loop-detection failure). Five archived todos were classified against it as a
test: **251, 245, 261, 337, 230. Zero fit cleanly and one fit partially.** That taxonomy diagnoses
a skill written in a rigid `IF / THEN / EXAMPLES / Variables` format, where the defects are
formatting-level. These skills are prose with numbered steps, and their real failures are semantic.
Four of the upstream seven (missing examples, implicit file references, missing variables, wrong
tool) do not appear anywhere in 258 archived skill-improvement todos.

---

## P1. The rule depends on being remembered

**Symptom:** the instruction is present, clear, and correct, and it gets skipped anyway. Often
repeatedly, often by sessions that had read it.

**This is the largest class in this repo.** 02 (enforce no-asking-before-commit mechanically, not
via memory recall), 07 (the never-chain rule was violated constantly and may be unworkable as
written), 21 (enforce it with a hook instead of willpower), 105 (`/commit` step 1 has no
enforcement and gets silently skipped), 253 (harden "report must be the final message" beyond a
written instruction), 270 (third recurrence, same shape as the em-dash enforcement gap).

**Fix, in order of preference:** a hook or script that makes the failure impossible; the rule moved
to the point of use, so it is read while the relevant output is being composed rather than pages
earlier; a mechanical check in `ci/`. Rewording is the fix that has already failed twice on record.

**Do not** answer this pattern with stronger language. `refs/delegation-doctrine.md` records a
watchdog rule that fired zero times across eight dispatches and was deleted rather than reworded.

---

## P2. Two skills, or a skill and a global rule, disagree and nobody owns the resolution

**Symptom:** each document is individually right; following both is impossible or produces a
double action.

**Evidence:** 245 (`/rate-it`'s post-rating menu and `/rate-it-and-commit`'s threshold logic both
claim the terminal question), 106 (`/impeccable`'s direction contract mandates a comment block the
global comment cap forbids), 255 (`/mega-todos`' per-builder commit design is unsafe in a
lint-staged repo).

**Fix:** name the owner explicitly in both places, or in the one that is nested. Precedence stated
once in one file is a coin flip at runtime.

---

## P3. The host or environment makes the instruction unsatisfiable

**Symptom:** the skill is followed exactly and the outcome is still wrong, because the assumption
under the instruction does not hold here.

**Evidence:** 251 (`/rate-it` required a turn with no tool call, but in Conductor the only visible
channel IS a tool call), 100 (a skill assumed a Playwright MCP that is not in the session), 09 (the
commit marker cannot be written in the same call as the commit, so every commit costs two), 254
(`/mega-todos` assumed a Rust/Tauri project).

**Fix:** state the environment the instruction assumes, and give the alternative for hosts where it
does not hold. Never delete the rule; the assumption is usually true somewhere.

---

## P4. A real runtime state that no branch covers

**Symptom:** the skill offers two paths and the situation is a third one, so the session improvises.

**Evidence:** 261 (a run that STARTED interactive and became unattended when the dev walked away is
neither branch), 222 (`/commit push` with nothing to commit but unpushed commits waiting), 259
(`/mega-todos`' verify ladder undefined for a run ending below its own threshold), 08 (a day with
zero Clockify entries).

**Fix:** add the branch. Prefer naming the state in the skill over a rule that says "use judgment",
which is P1 wearing a different hat.

---

## P5. The skill's premise about what the dev wants is wrong

**Symptom:** the skill was followed perfectly and the dev's reaction is "that is not what I wanted".
Nothing in the file is incorrect; the file is aimed at the wrong intent.

**Evidence:** 337 (`/brainstorm` is gate-free by design and built immediately; the dev wanted the
idea stress-tested first), 246 (a skip-picker nobody used), 241 (research flags nobody passed).

**Fix:** split the intents and detect which one is in play, or ask once at the top. This is the one
pattern where the honest patch may be deleting a section the skill was proud of.

---

## P6. Two of the skill's own rules hold different standards

**Symptom:** output that contradicts itself, or a gate that is strict in one phase and loose in the
phase that feeds it.

**Evidence:** 230 (`/iterate-it`'s Phase A promoted on the subagent's score alone while Phase B
required a main-agent audit for the same kind of decision). Found again on 2026-08-22: `/rate-it`'s
new verification pass reported a claim as refuted and then rested a suggested lift on it, because
nothing told the synthesis step to cross-check its own two outputs.

**Fix:** make the later step check the earlier step's output explicitly. An invariant that holds
only because both steps happen to agree is not an invariant.

---

## P7. The instruction is ambiguous exactly where it is used

**Symptom:** the wording is fine read as prose and wrong read as an instruction, and the reader is
composing an action, not reading prose.

**Evidence:** 252 (`build-watch.md`'s launch mechanism read as a raw shell command), 262 (a
copy-paste rule that silently corrupted every Windows path containing a dot-directory).

**Fix:** show the exact literal, before and after. Prose describing a format loses to one example
of the format.

---

## P8. The skill asks for work it supplies no tool for

**Symptom:** every run of the skill hand-rolls the same throwaway script, slightly differently, and
gets it subtly wrong on some runs.

**Evidence:** 10 (archiving a todo needed a hand-written script every time), 11 (orphan-process
forensics rewritten from scratch every time), 266 (a marker-update script hand-rolled per run), 474
(`/commit`'s overlap check should be a script).

**Fix:** ship the script and point the step at it. This is a tooling gap rather than a confusion,
but it surfaces as a confusion because each hand-rolled version behaves differently.

---

## Choosing between them

- Was the instruction followed? **No** and it was clear: P1. **Yes** and the result was still
  wrong: P3, P5 or P6.
- Was there an instruction at all for this situation? **No**: P4.
- Did two documents conflict? P2.
- Did the reader act on a different reading than intended? P7.
- Did the run rebuild something it should have called? P8.

If none fit, say so in the diagnosis and propose a ninth pattern with its evidence. A forced
classification produces a patch aimed at the wrong cause, which is how the same skill gets healed
twice for the same symptom.
