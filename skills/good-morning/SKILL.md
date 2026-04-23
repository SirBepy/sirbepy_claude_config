---
name: good-morning
description: Triggers on /good-morning only. Morning routine dispatcher. Currently runs /clockify-reconciliator zirtue yesterday; more steps will be added over time.
---

# /good-morning

> Morning routine. Currently just reconciles yesterday's Zirtue Clockify entries.

## Steps

### 1. Reconcile yesterday's Clockify

Invoke `/clockify-reconciliator zirtue yesterday`. Follow that skill's flow: fetch entries, propose descriptions + splits, confirm with dev, apply.

## Notes

- More morning tasks will be added here over time (ticket pickup, PR review, etc). Keep this skill as the single entry point.
- When adding new steps, list them here in order and make each step one clear action.
