HP Remote v2 — Pipe-R Client
============================

What's new in v2
----------------
- CLAUDE tab (unchanged) — prompt Claude Code on the dev box
- SHELL tab (new) — full PowerShell terminal controller for the dev box
- Live wallpaper color sync — the laptop client pulls dominant colors
  from the dev box's current desktop wallpaper every 30s and re-themes
  itself to match the main deck automatically
- Dependency check script (check-deps.ps1) that verifies reachability
  and offers to install Node.js + Claude Code CLI locally if missing

Files in this zip
-----------------
  index.html       - the whole client in one file, no build, no deps
  check-deps.ps1   - optional pre-flight script (right-click > Run with PowerShell)
  README.txt       - this file

First run
---------
1. Make sure the Pipe-R server is running on the dev box:
     - Double-click DECK.bat, or
     - `node server.js` from C:\Users\Ken\Desktop\Claude
   Server listens on 0.0.0.0:7777 so anything on the same WiFi can reach.

2. Extract this zip anywhere on the laptop.

3. (Optional) Right-click `check-deps.ps1` and "Run with PowerShell".
   It verifies the dev box is reachable and offers to install Node.js
   + Claude Code CLI locally (you don't need them locally to use the
   client — the browser talks directly to the dev box).

4. Double-click `index.html`. The client opens in whichever browser
   is default.

5. The server URL defaults to http://192.168.0.58:7777. If the dev
   box has a different LAN IP, type it into the "Server" field at the
   top and hit Save. The status pill turns green when it connects.

Using the client
----------------
- **CLAUDE tab**: type a prompt in the bottom textarea. Ctrl+Enter to
  send. Runs on the dev box as `claude -p "<your prompt>"`. Response
  streams back into the turn log. History persists in localStorage.

- **SHELL tab**: type any PowerShell command. Enter to run. ↑/↓ cycles
  the last 50 commands. Commands execute on the dev box's PowerShell
  under the Pipe-R server's user context. 30s timeout, 4MB buffer cap.
  Bare `claude <text>` auto-wraps to `claude -p "<text>"` on the server.

- **Wallpaper color sync**: every 30s the client pulls colors from the
  dev box and re-themes itself. Change the wallpaper on the dev box
  and the laptop client follows.

Safety notes
------------
- The Pipe-R server is bound to 0.0.0.0:7777 and assumes LAN trust.
- Anyone on your WiFi who finds that URL could hit the same endpoints.
- No auth on /api/shell/run — it's behind the PIN-gated remote UI,
  but the direct API is wide open on the LAN. Treat accordingly.
- If the laptop wants shell access to itself (not the dev box), that's
  a separate build — this client is remote-only to the dev box.
