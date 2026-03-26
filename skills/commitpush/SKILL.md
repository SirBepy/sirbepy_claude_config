---
name: commitpush
description: Commit then immediately push. Triggers on /commitpush, /commitpush v, /commitpush bump, /commitpush onlybump, and /commitpush onlyv.
---

# /commitpush

> Run the full commit flow then push.

Follow the `/commit` skill exactly for all variants, then run `git push` at the end.

Do not push if the commit failed or there was nothing to commit.
