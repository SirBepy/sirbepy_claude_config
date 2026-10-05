<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=HARD, worth=5, reconfirm-count=2, content-hash=e3250126 -->
# Finish remote Wake-on-LAN: FRITZ!Box WireGuard tunnel + verify wake from outside the LAN

**Type:** task
**Origin:** dev

## Goal

Joe wants to turn his desktop PC (DESKTOP-6GJ2QR0) back on from anywhere, from his phone, whether
the PC is asleep or fully shut down. Local wake already works; what's left is reaching the router
from outside the home network, plus wake-from-full-shutdown.

## Context

This is a machine/network setup task, not a change to this repo. It was filed here because the
session ran in `~/.claude` and there's no other repo it belongs to. All state below is from the
session on 2026-09-05, so re-verify it before acting on any of it.

**Hardware / network facts (receipts from that session's command output):**
- PC NIC: Realtek Gaming 2.5GbE, MAC `58-11-22-BE-9E-03`, IP `192.168.178.39` (DHCP, not pinned:
  router reports `ipv4.dhcp.alwaysSameIp = false`).
- Motherboard: ASUS PRIME Z790-P D4, BIOS 1645 (2024-03-15).
- Router: FRITZ!Box 5530 Fiber, FRITZ!OS 8.20, at `192.168.178.1`, login user `fritz4160`. The
  password is NOT recorded here, so ask Joe for it. Full `BoxAdmin` rights confirmed.
- Router's device entry for the PC: `uid=landevice7617`, `wakeOnLan.show = true`.
- WAN: router's TR-064 `GetExternalIPAddress` and api.ipify.org both returned `78.1.219.62`, so
  there is **no CGNAT** and inbound VPN is viable. No IPv6 reachability. The IP is presumably dynamic,
  so a DynDNS hostname is needed (`ddnsActivated: false` on the WireGuard page).
- Router DECT is `off`, so its two-factor confirmations go to a **physical button on the box**.
- Phone: Redmi Note 8 Pro, Android 11, adb serial `z9tkammfp7ob7llj` (authorized over USB on
  2026-09-05). Home WiFi SSID `TID-5GHz`, phone LAN IP was `192.168.178.41`.

**Done and verified on 2026-09-05:**
- NIC driver: `*WakeOnMagicPacket`, `*WakeOnPattern` and `S5WakeOnLan` all Enabled. `powercfg
  /devicequery wake_armed` lists the Realtek NIC.
- Fast Startup off: `HiberbootEnabled=0`, re-checked 2026-10-02.
- **Local wake from sleep works.** Joe slept the PC and pressed "Start computer" in the FRITZ!Box UI
  on his phone over home WiFi, and the PC woke.
- WireGuard Android app installed via adb from the official `download.wireguard.com` APK
  (`com.wireguard.android` 1.0.20260315). Before install, `apksigner` showed the signer was
  `O=WireGuard LLC, CN=WireGuard Android Infrastructure`.

**Settled decisions (don't re-litigate):**
- Remote access goes through **WireGuard only**. MyFRITZ! HTTPS access to the router UI was
  rejected because it would put the router login on the public internet behind a weak password. Using
  MyFRITZ! *only for its DynDNS hostname* is fine; the "internet access to the FRITZ!Box via HTTPS"
  toggle must stay off.
- Tailscale was ruled out as the wake sender because Joe's other tailnet nodes (MacBook, phone) were
  offline and none is always-on inside the LAN.
- Sleep is acceptable as the everyday state. The BIOS change is only needed for wake-from-shutdown.

**Where it stalled:** creating the WireGuard connection needs FRITZ!Box two-factor confirmation.
The `shareWireguard` page returned `wg_device_config: "UIM_FAIL_TWOFACTOR_AUTH_NEEDED"`, and Claude
deliberately did not try to bypass it. Joe hadn't done the button press when the session ended.

**Misunderstandings and bugs hit (so they don't recur):**
- `C:\tmp\fritz.ps1` login first failed after a successful login. The box starts returning
  `<User last="1">fritz4160</User>`, which PowerShell surfaces as an XmlElement whose ToString is the
  type name. Fixed by normalising to `.InnerText`. That cost one lockout increment (BlockTime 2s).
- The first wake POST included `apply=`. That runs the form-save path and failed with `valerror`
  / `tooshort` on `dev_name`. Fixed by dropping `apply` and sending `dev_name`.
- Even the fixed scripted wake POST (`btn_wake`) returned HTTP 200 with no magic packet seen by
  `wol-sniff.ps1` while the PC was ONLINE. UNVERIFIED: the box may skip sending WoL to a device it
  already sees online, or the parameter may still be wrong. The UI button is known to work, so the
  scripted wake is optional.
- `rundll32 powrprof.dll,SetSuspendState` hibernates instead of sleeping when hibernation is enabled.
  `C:\tmp\sleep-test.ps1` uses a P/Invoke instead.
- The FRITZ!OS 8.20 UI is a single-page app: `/net/edit_device.lua` 404s. Read state via
  `data.lua` pages (`netDev`, `edit_device`, `shareWireguard`, `shareVpn`); `fritz.ps1 -Page <name>`
  dumps one. Unknown page names fall back to `pid: overview`.

**Scratch toolkit in `C:\tmp\` (not in any repo):** `fritz.ps1` (PBKDF2 v2 login, verified against
RFC test vectors; `-Page`, `-DumpDevicePage`, `-Wake`; refuses to run while BlockTime > 0 and never
retries a failed password), `wol-sniff.ps1` (UDP 7/9 listener, self-tested), `wol-send.ps1`,
`sleep-test.ps1`, `wireguard.apk` (17 MB) and several `fritz-*.json` dumps.

## Approach

1. **Joe, at the router (physical):** in the FRITZ!Box UI go to Internet, then Permit Access, then
   VPN (WireGuard), then Add Connection, then "Connect a single device". Press the button on the box
   when prompted. A QR code appears: in the phone's WireGuard app, tap +, then "Scan from QR code".
   On the same flow, enable MyFRITZ! / DynDNS so the tunnel endpoint is a hostname, not
   `78.1.219.62`.
2. **Claude verifies the remote path without needing the PC asleep:** with the phone on USB, run
   `adb shell svc wifi disable` to force mobile data. Joe toggles the tunnel on, or Claude does it via
   the app's intent. UNVERIFIED: WireGuard Android accepts `com.wireguard.android.action.SET_TUNNEL_UP`
   only when "Allow remote control apps" is enabled in its settings. Then run
   `adb shell ping -c 3 192.168.178.1` and `adb shell ping -c 3 192.168.178.39`. Replies over mobile
   data prove the tunnel works. Re-enable WiFi afterwards with `adb shell svc wifi enable`.
3. **End-to-end test (Joe):** sleep the PC, then on the phone with WiFi off and the tunnel on, open
   `http://192.168.178.1`, go to Home Network, then Network, then DESKTOP-6GJ2QR0, and press Start
   computer. On resume, Claude checks `powercfg /lastwake` and `C:\tmp\wol-test-log.txt` if
   `sleep-test.ps1` was used.
4. **Wake from full shutdown (Joe, physical, optional):** in BIOS press Del, then F7 (Advanced),
   then go to Advanced, then APM Configuration. Set `Power On By PCI-E` to **Enabled** and
   `ErP Ready` to **Disabled**, then F10. Then shut down for real and repeat step 3.
5. **Offered but unanswered:** pinning the PC's DHCP lease (`alwaysSameIp`). It doesn't affect
   WoL, which targets the MAC, but helps with any later RDP or port forwards. Ask before changing it.
6. Clean up `C:\tmp\` once done. The APK and JSON dumps are disposable, and the scripts can go to
   Joe's vault or a tools folder if he wants to keep them.

## Acceptance

- With the phone on mobile data (WiFi off) and the WireGuard tunnel up, the phone reaches
  `192.168.178.1`.
- From that state, pressing Start computer wakes the sleeping PC.
- If Joe does the BIOS step, the same works from a full shutdown.
- Must not regress: local wake over home WiFi (verified 2026-09-05), and Fast Startup staying off
  (`HiberbootEnabled=0`).
- The router's "internet access via HTTPS" toggle stays off.

## Verify

- [ ] `(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power').HiberbootEnabled` must be 0
- [ ] `Get-NetAdapter -Name Ethernet | Select MacAddress, Status`
- [ ] `C:\Users\tecno\AppData\Local\Android\Sdk\platform-tools\adb.exe devices -l`: the phone must show `device`, not `unauthorized`
- [ ] `adb shell pm list packages | findstr wireguard`
- [ ] `powershell -File C:\tmp\fritz.ps1 -Password <ask Joe> -Page shareWireguard -Out C:\tmp\fritz-wg.json`, then check whether `userConnections`/`boxConnections` are still empty
- [ ] Compare the router WAN IP (TR-064 `GetExternalIPAddress` on `:49000/igdupnp/control/WANIPConn1`) with `https://api.ipify.org` to confirm there's still no CGNAT

## Open questions

Written by /auto-do-todos on 2026-10-06 (loop-todos cycle 2). The next run opens with these.

- [ ] [TOOLING] Joe: press the FRITZ!Box two-factor button at the router so the WireGuard tunnel can be created.

## Notes

- Joe ended the session with `/create-todo to finish this` then `/close` on 2026-10-02, almost a
  month after the work was done. Joe may already have finished the WireGuard step by hand, so check
  `userConnections` before redoing anything.
- On 2026-10-02 adb listed no device, so the phone wasn't plugged in at that point.
- Never write the router password into a file. It's in the 2026-09-05 session transcript only.
