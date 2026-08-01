# Tauri dev entries

- **Before `cargo build`/`cargo test` in a repo whose supervised entry runs `cargo tauri dev`:** stop the entry first (`POST /procs/<id>/stop`), run the build/test, then `POST /procs/<id>/start`. The running dev app holds a lock on `target/debug/<app>.exe`; building or testing against it while it's up fails with "failed to remove <app>.exe: Access is denied (os error 5)".
- **After any `cargo tauri dev` entry crash, before restarting:** the supervisor only kills the `tauri` CLI process, not its `beforeDevCommand` grandchild (vite/node). Check for and kill an orphan vite first, then verify the dev port (1420 by default for Tauri) is free, or the restart will crash again with "Port 1420 is already in use":
  ```powershell
  Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -match 'vite' }
  ```
  Kill any matches with `Stop-Process -Id <PID> -Force`, then confirm the port is free before `POST /procs/<id>/start` or `/restart`.
