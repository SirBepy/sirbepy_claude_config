"""PreToolUse hook: block driving a zng app or its e2e suite against the DEV backend.

Two real incidents on 2026-08-25, the second after the first was already
apologised for in Slack, which is why this is a hook and not a rule.

Morning: the zng-app e2e suite was pointed at dev. Its fixture bootstrap
registers its own users, generating a phone as `415` + 7 random digits, which
routinely lands on an impossible NANP exchange (`415-100-...`, `415-147-...`).
Dev's notification service handed each to real Twilio, producing `21211
Invalid 'To' Phone Number` ERRORs in CloudWatch `/ecs/notification`. Its
negative tests also log expected 403s to `/ecs/core`. A teammate asked for it
to stop and the dev agreed to keep that testing local.

Evening: two builder dispatches were told to run
`flutter run ... --dart-define-from-file=.env.dev` so OTP and card linking
would be "real". Three more Twilio ERRORs in 15 minutes, Amazon Q fired an
`@here`, and the team started hunting an incident hours after being told it
had stopped.

The generated-number technique is safe LOCALLY and only locally: local's
Twilio sender is fake so no SMS can leave the machine, and the phone-lookup
gate is a local postgres row. `.env.dev` has neither property. Local also has
an OTP bypass (`000000`) and a debit-card cheat endpoint that skips Fiserv, so
almost nothing genuinely requires dev.

Scope (deliberately narrow, same reasoning as flutter-workdir-guard): HARD
BLOCK only when a command DRIVES something against dev - a flutter/dart
run/build/drive/test carrying a dev env file or dev host, or the e2e runner
with a dev target. Everything else that merely mentions a dev host (curl
probes, grepping the env file, reading config) only WARNS, because a blanket
block would get this hook switched off and then it protects nothing.

Override: set CLAUDE_DEV_BACKEND_BYPASS=1 when hitting dev is genuinely the
task (verifying an already-deployed fix). If you do, use a real reachable
phone number, never a generated one, and run no negative tests.
"""

import os
import re
import shlex
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, strip_quotes as _lib_strip_quotes
except Exception as e:
    sys.stderr.write(
        f"[dev-backend-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n"
    )
    sys.exit(2)

OVERRIDE_ENV = "CLAUDE_DEV_BACKEND_BYPASS"

APP_RUNNERS = {"flutter", "flutter.bat", "flutter.exe", "dart", "dart.exe", "dart.bat", "fvm", "fvm.exe"}
DRIVING_SUBCOMMANDS = {"run", "build", "drive", "test"}

E2E_RUNNERS = {"node", "node.exe", "npm", "npm.cmd", "pnpm", "pnpm.cmd", "yarn", "yarn.cmd"}

# Anything pointing a build or a suite at the deployed dev environment.
DEV_MARKERS = (
    ".env.dev",
    "api.dev.ng.zirtue.com",
    "dev.pay.zirtue.com",
    "dev.ng.zirtue.com",
)

# `--target` is also a flag on tsc, cargo, docker and vite, so a nonlocal target
# alone cannot block - the segment must also name an e2e entrypoint. Otherwise
# `npm run build --target=production` reads as an e2e run against "production".
E2E_ENTRYPOINT_RE = re.compile(r"run-all|e2e", re.IGNORECASE)

# `--target=dev`, `--target dev`, `E2E_TARGET=dev`, `$env:E2E_TARGET = "dev"`.
E2E_TARGET_RE = re.compile(
    r"""(?:--?target[=\s]+|E2E_TARGET\s*=\s*)['"]?(?P<value>[A-Za-z0-9_-]+)""",
    re.IGNORECASE,
)

CHAIN_SPLIT_RE = re.compile(r"&&|\|\||;|\n|\|")


def allow(message: str = "") -> None:
    if message:
        print(message)
    sys.exit(0)


def basename(tok: str) -> str:
    return re.split(r"[\\/]", tok)[-1].lower()


def flatten_tokens(tokens: list[str]) -> list[str]:
    out: list[str] = []
    for tok in tokens:
        for piece in tok.split(","):
            piece = _lib_strip_quotes(piece.strip())
            if piece:
                out.append(piece)
    return out


def tokenize(segment: str) -> list[str]:
    try:
        return flatten_tokens(shlex.split(segment, posix=False))
    except ValueError:
        return [p for p in re.split(r"\s+", segment) if p]


def dev_marker_in(text: str) -> str | None:
    low = text.lower()
    for marker in DEV_MARKERS:
        if marker in low:
            return marker
    return None


def nonlocal_e2e_target(segment: str) -> str | None:
    """Return the target value when an e2e target is set to anything but local."""
    for match in E2E_TARGET_RE.finditer(segment):
        value = match.group("value").lower()
        if value and value not in {"local", "localhost"}:
            return value
    return None


def block(reason: str) -> None:
    deny(
        f"[dev-backend-guard] Blocked: {reason} On 2026-08-25 this put invalid-phone Twilio ERRORs "
        "into CloudWatch twice in one day, the second time hours after the team was told it had "
        "stopped, and set off an @here incident hunt. Generated test numbers reach real Twilio on "
        "dev but cannot on local, and negative tests log expected 403s that page people. Use local: "
        "it has the '000000' OTP bypass and a debit-card cheat endpoint that skips Fiserv, which "
        "covers essentially every verification task. If hitting dev is genuinely the point, set "
        f"{OVERRIDE_ENV}=1, use a real reachable phone number, and run no negative tests."
    )


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        allow()
    if os.environ.get(OVERRIDE_ENV):
        allow()

    for segment in CHAIN_SPLIT_RE.split(command):
        tokens = tokenize(segment)
        if not tokens:
            continue
        lowered = [t.lower() for t in tokens]
        basenames = {basename(t) for t in tokens}

        target = nonlocal_e2e_target(segment)
        if (
            target is not None
            and E2E_ENTRYPOINT_RE.search(segment)
            and (basenames & E2E_RUNNERS or "run-all" in segment.lower())
        ):
            block(f"this runs the e2e suite against the '{target}' target.")

        seg_marker = dev_marker_in(segment)
        if seg_marker is None:
            continue

        if basenames & APP_RUNNERS and any(t in DRIVING_SUBCOMMANDS for t in lowered):
            block(f"this drives the app against the DEV backend ('{seg_marker}').")

        if basenames & E2E_RUNNERS:
            block(f"this runs a Node script against the DEV backend ('{seg_marker}').")

    marker = dev_marker_in(command)
    if marker:
        allow(
            f"[dev-backend-guard] Warning: this command references the dev environment ('{marker}'). "
            "Not blocked, since it does not drive the app or the suite. Anything that registers a "
            "user, sends an OTP, or links a card on dev shows up in the team's CloudWatch alerts."
        )
    allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[dev-backend-guard] hook error, failing open: {e}\n")
        sys.exit(0)
