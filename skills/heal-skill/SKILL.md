---
name: heal-skill
description: Triggers on /heal-skill only. Diagnoses why a named skill keeps producing wrong output, classifies the root cause against this repo's own failure patterns, and proposes one approved patch.
argument-hint: "<skill-name> [what went wrong]"
disable-model-invocation: true
---

# /heal-skill

> A skill that reads fine but keeps going wrong. Find the cause, patch it once, record it.

## The trigger is manual, deliberately

This skill does not fire on its own. There is no confusion detector, and the honest reason is on
record: `refs/delegation-doctrine.md` documents a watchdog rule that depended on being remembered
mid-run, fired zero times across eight dispatches, and was deleted rather than reworded. A rule
that must be recalled at exactly the moment things are going wrong does not survive being recalled.
So this is invoked on purpose, by the dev or by a session that has just watched a skill misfire.

Two mechanical triggers were considered and rejected: a hook counting repeated invocations of the
same skill (a long correct run looks identical to a loop), and a `UserPromptSubmit` matcher on the
dev's correction phrases (it would run on every prompt in every project to catch a case that
arrives a few times a month). If either is ever wanted, it is a separate decision with its own
measurement, not a silent addition here.

## What this is not

- Not `bepy-skill-creator`, which checks a skill against conventions. That is a linter and it
  cannot see behavior.
- Not the eval harness (`tools/skill_eval.py`), which measures a skill against fixtures. That
  catches a skill failing a case somebody wrote down. This catches a skill failing reality.
- Not a place for general advice. A run that ends in "consider clarifying the workflow" has failed.

## Workflow

1. **Resolve the target.** `/heal-skill <name> [what went wrong]`. With no name, ask via
   `AskUserQuestion`, offering the skills that misfired in this session as options. Never guess.

2. **Read the heal log first.** `skills/<name>/heal-log.md`, if it exists. A prior entry naming the
   same symptom is the important signal in this whole flow: **the previous patch did not work, so
   the previous diagnosis was wrong.** Say that out loud, and do not propose the same class of fix
   again. If the log names a different symptom, note it and continue.

3. **Get the evidence, and refuse to proceed without it.** Three things:
   - what the skill actually produced, quoted,
   - what it should have produced,
   - the line or section of `SKILL.md` (or its sidecars) that was violated, ignored, or followed
     into the wrong result, cited as `path:line`.

   No quoted output means no diagnosis. A patch built on a recollection of a misfire is how a skill
   accumulates edits that fix nothing. Say what is missing and stop.

4. **Classify.** Read `references/confusion-patterns.md` and name the pattern, with the evidence
   from step 3 mapped onto it. If nothing fits, say so plainly and propose a ninth pattern rather
   than forcing the closest one. A patch aimed at the wrong cause is worse than no patch, because
   it makes the next session think the problem was handled.

5. **Propose exactly one patch, as a literal edit.** Show the current text and the replacement,
   verbatim. Follow the pattern's own preferred fix order: for P1 that means a hook, a script, or
   moving the rule to its point of use, never rewording it harder. State in one line what would
   have gone differently on the quoted evidence had the patch been in place.

6. **Get approval before writing anything.** `AskUserQuestion`: apply it, propose a different fix,
   or log the diagnosis without patching. Never apply on your own judgment, however obvious the
   edit looks. A skill patched without approval is a skill whose behavior changed under the dev
   without being asked.

7. **On apply:** make the edit, then append one dated bullet to `skills/<name>/heal-log.md`,
   creating it with an `# <name> heal log` heading if absent. One line each for symptom, pattern
   number, patch, and whether it was verified. Re-read the file immediately before writing, since
   several sessions share this repo.

8. **Say whether the patch is measured.** If `skills/<name>/evals/evals.json` exists, give the
   command and let the dev decide whether to spend it:

   ```
   python tools/skill_eval.py --skill <name> --label heal-<date> --parent <prior label> --repeat 3
   ```

   Below three repeats the run-to-run noise is as large as most patches, so a single run is not
   evidence. If the skill has no fixtures, say the patch is unverified rather than implying the
   diagnosis settled it, and offer to write a fixture that reproduces the symptom, which is the
   only way a future session finds out whether this heal held.

## Anti-patterns

- Diagnosing more than one cause per run. Two patches at once means neither is attributable.
- Rewording an ignored rule. See P1. This has already failed on record.
- Adding a rule to fix a rule nobody followed. The new one gets skipped by the same mechanism.
- Claiming a heal worked because the next run looked fine. One run is noise; say it is unverified.
