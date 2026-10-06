<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 226 (done) is the hub-port HTTP route; this is the adb reverse limitation bullet, a different surface -->
# Update supervised-run's proxy-hub doc: adb reverse is now automatic

**Type:** task
**Origin:** ai

## Goal

`skills/supervised-run/proxy-hub.md`'s Limitations section still says the supervisor does NOT set
up the `adb reverse` tunnel for Flutter mobile. server_supervisor `00f2fc5` (2026-10-06, its todo
0025) made it automatic, so the doc now tells agents to do by hand what the app already does.

## Approach

Replace the bullet that starts "Doesn't help Flutter mobile out of the box" with (drafted by the
server_supervisor builder, check it against the shipped code before pasting):

> - Flutter mobile (Android emulator, USB device) works automatically: when the supervisor starts a
>   Flutter proc in a project with hub presets, it runs `adb reverse tcp:<hub_port> tcp:<hub_port>`
>   for whichever device Flutter itself selected (parsed from the `--machine` daemon's `app.start`
>   event), and tears it down on stop or on the process's own exit. A missing `adb`, or no device,
>   never blocks the launch: it logs and runs without a tunnel. WiFi-connected devices are NOT
>   covered: `adb reverse` only works over USB or to an emulator, and the hub stays loopback-only,
>   so a WiFi device still cannot reach it.

Only true once Joe's installed supervisor is a release that includes `00f2fc5`; check the version
before editing, or word it as "from the release after v0.1.39".

## Acceptance

- The Limitations bullet describes the automatic tunnel and the WiFi exclusion.

## Notes

Filed 2026-10-06 from a server_supervisor `/auto-do-todos` run, per the rule that global `~/.claude`
work goes in this repo's own backlog rather than being done from a project session.
