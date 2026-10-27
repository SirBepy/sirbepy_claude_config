# check-availability.mjs: usage, signals, limits

Dependency-free name checker (Node 20+, built-in `fetch`, `node:net`, `node:dns`). No `npm install`, no API keys.

```
node ~/.claude/skills/name-brainstorm/check-availability.mjs names.txt --skip hr --extra ai --out results/round1 --resume results/cache.json
```

Input: one name per line, `#` lines and blank lines ignored, lowercased. A line that is not a valid DNS label (`[a-z0-9-]`, 1-63 chars, no spaces, dots, diacritics or double hyphens) aborts the run with line numbers. A corrupt `--resume` file aborts and is never overwritten.

Flags: `--out <prefix>` (default `<input>.results`), `--resume <file>` (JSON cache), `--extra co,ai`, `--skip hr,eu` (drop slow core TLDs; the score then counts only what was checked), `--no-github`, `--no-dns`, `--concurrency 1-5`, `--delay <ms>`, `--whois-delay <ms>`, `--verbose`.

Output: Markdown table on stdout plus `<prefix>.csv` and `<prefix>.json`. Statuses are exactly `FREE`, `TAKEN`, `UNKNOWN`. Score = weights of FREE among com/hr/io/dev/app/eu (`.com` 3, `.hr` 3, others 1); scores from runs with different `--skip` are not comparable.

Resume: only FREE/TAKEN are cached, keyed `kind:name`; a rerun skips them and retries every UNKNOWN. The cache is flushed every 10 results and on Ctrl+C. Reuse one cache across rounds. Read it with `view-cache.mjs`.

## What each signal means

| Check | Method | Trust |
|---|---|---|
| .com | RDAP, Verisign | reliable; 404 = not registered |
| .dev, .app | RDAP, Google Registry | reliable; the script spaces requests 1.1 s apart (429 beyond ~1.3/s) |
| .io, .ai | RDAP, Identity Digital (built-in fallback URL) | reliable |
| .hr | port-43 whois `whois.dns.hr` (no RDAP exists) | reliable answers, but rationed: about 10 s per name without NS records |
| .eu, .co | port-43 whois | reliable answers; quarantined names read as TAKEN |
| DNS cross-check | `NS` then `SOA` | NS present overrides "free" to TAKEN (taken or parked); no NS never proves FREE |
| npm | `registry.npmjs.org/<name>` | reliable for the exact name only |
| GitHub | `HEAD github.com/<name>` | weak: users, orgs and reserved paths look alike |

"FREE" means **not registered today**, not buyable at the standard price: premium and registry-blocked names can read free, and TAKEN includes parked and for-sale names. 429, 5xx, timeouts and odd answers are retried 4 times, then UNKNOWN with a reason in `notes`; never FREE.

## Practical rules

- Run bare names with `--skip hr` (about 4 checks a second), then run the finalists with `.hr` (about 10 s per name). Over about 200 names with `.hr`, split the run and use `--resume`.
- Real words and first names are registered on nearly every bare domain. Test `hey`, `my`, `ask`, `get` prefixes for the finalists.
- If the dev doubts a result, verify directly: `Resolve-DnsName <d> -Type NS`, port-43 whois, the registry's RDAP. A registered name with no website is still registered.
- Do not run two instances at once: the `.hr` whois server refuses connections after bursts.

## Trademark and company registers (not scripted)

- **Croatian court register (Sudski registar):** the open-data API needs a registered client id (an unauthenticated call returns 401); use the public page `https://sudreg.pravosudje.hr/registar/f?p=150:1`, search by company name.
- **DZIV** (Croatian trademark office, `https://www.dziv.hr/`): no documented API; search by hand.
- **EUIPO TMview** `https://www.tmdn.org/tmview/` (national offices, EUIPO, WIPO) and **WIPO Global Brand Database** `https://branddb.wipo.int/`: by hand or a browser agent; EUIPO's eSearch plus is disallowed in its robots.txt, do not automate it. Search exact and similar, Nice classes 9, 35, 42 for software.

## Limits

A point-in-time registry answer: no homoglyph or typo variants, no social handles beyond GitHub, no app stores, no trademark conflicts. A filtered system DNS resolver can fail a lookup; that is noted but never turns FREE into TAKEN.
