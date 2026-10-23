---
name: people
description: Use when unsure who Joe means by a name, or he introduces someone new. Vault lookup, else ask; new-person card.
---

# /people

> Know who Joe means, or ask. Never guess a person.

People live in the Obsidian vault, one note per person: `C:\Users\tecno\Documents\ObsidianVault\People\<Name>.md`, frontmatter per `Templates/Person.md`. A client (Zirtue, Revaire) is a vault note at the vault root whose frontmatter lists its `repos:`; its slug is the lowercased note name (`zirtue`). A person's `projects: [zirtue]` says which clients they belong to; `project_aliases: ["zirtue: backend"]` holds names Joe uses for them inside one client only.

## Which client is this session in

The client whose `repos:` list holds this repo's folder name. None matches: no client, every person counts as known everywhere.

## Who did he mean

Only a name Joe himself introduces counts. Names inside pasted material (a Slack thread, a log, a ticket body) are not mentions: never ask about them.

1. Look the name up. In a Claude Conductor chat, call the `person` MCP tool (`mcp__cc_conductor__person`) with `action: find`. Elsewhere, read `People/*.md` and match the name against each note's file name, `name`, `aliases`, and this client's `project_aliases`.
2. Act on the result:
   - **One match in this client, or one person with no `projects`:** that is who he means. Do not ask.
   - **Several matches:** ask which one, with ask_user_question, listing each with their relationship.
   - **One match, but only in another client:** ask "did you mean <name> from <client>?". On yes, add this client to their `projects` (Conductor: `person` with `action: remember` and `join_project`).
   - **No match:** ask, offering the closest-sounding vault names as options plus "someone new". A voice mishear (Stefan vs Stevan) gets asked once, then saved as an alias (`person` with `action: remember` and `alias`, or the note's `aliases`).
3. A role word that names one person here ("backend", "the QA") gets saved as a `project_alias` once Joe confirms it, so it is never asked again in this client.

## Someone new

Offer the profile now or later, in one ask_user_question card. "Later" is a `write_user_todo` item in Conductor (elsewhere, a line in the reply asking Joe to run `/people` when ready), never a chat promise.

The questionnaire, always these six, always this wording:

1. Where do you know them from?
2. What is their role there?
3. Any other names you use for them?
4. What language and tone do you write to them in?
5. Where do you message them (Slack, Shortcut, Google Chat, ...)?
6. What is their gender?

Ask all six in ONE card, with options pre-filled from whatever Claude already knows (drafts, tickets, the conversation), and let Joe correct them. Never infer gender from a name: that option gets no default.

## Saving it

- Conductor: `person` with `action: remember`, `new: true` and the answers. It writes the note from Joe's template and adds this client to `projects`. `remember` may raise a permission card when auto-accept is off; `find` never does.
- Elsewhere: create `People/<Full Name>.md` from `Templates/Person.md` (gender, language, messaged_on, projects filled), body facts as a dated bullet under `## Notes`. Follow `~/.claude/refs/global-knowledge-vault.md`: re-read before every write, edit line-scoped, commit the vault note by pathspec and push.
