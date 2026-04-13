HP Remote v3 — Pipe-R Client
=============================

WHAT'S NEW IN V3
----------------
- Five tabs in the laptop client:
    CLAUDE     fast one-shot prompt box (runs `claude -p` on dev box)
    SHELL      full PowerShell terminal (runs on dev box)
    DECK       the entire main Pipe-R deck embedded live via iframe
    METRICS    the deck's Metrics tab (CPU/RAM/GPU/ollama gauges)
    STEAM      the deck's Steam library tab
- "↗ FULL DECK" link that pops the whole deck in a new browser tab
- Tailscale detection in check-deps.ps1, with guided install
- README rewritten for work-from-anywhere use

FILES
-----
  index.html       single-file client, no build
  check-deps.ps1   pre-flight script (right-click > Run with PowerShell)
  README.txt       this file


============================
PART 1 — HOME LAN (EASIEST)
============================

If the laptop is on the same WiFi as Ken's dev box:

1. On the dev box, run DECK.bat or `node server.js` inside
   C:\Users\Ken\Desktop\Claude

2. On the laptop, extract this zip anywhere and double-click
   index.html. The default server URL is http://192.168.0.58:7777.

3. The status pill at the top should flip to "connected · Ken AI".
   If it says "unreachable", check:
     - dev box is on + server.js is running
     - Windows firewall on dev box allows inbound TCP 7777
     - laptop is on the same WiFi (not hotspot, not VPN)


==================================
PART 2 — FROM WORK / ANOTHER WIFI
==================================

The 192.168.0.58 IP only exists on the home network. To reach the
dev box from work, coffee shop, phone hotspot etc, you need ONE of:

-------------------
OPTION A: TAILSCALE (recommended)
-------------------

Tailscale is a free-for-personal zero-config VPN that gives every
device on your account a stable 100.x.y.z IP. It works through NAT
and corporate firewalls. Setup takes 5 minutes.

DEV BOX SETUP (one time):
  1. Install Tailscale: https://tailscale.com/download
     or in PowerShell:  winget install Tailscale.Tailscale
  2. Open the Tailscale tray app, click "Log in", use your Google /
     GitHub / Microsoft account. Accept the device.
  3. In an admin cmd:   tailscale ip -4
     Write down the 100.x.y.z address it prints. That's the dev
     box's permanent Tailscale IP.
  4. Make sure server.js is running on the dev box (DECK.bat).
     Windows firewall will ask once — allow Pipe-R on Private.

LAPTOP SETUP (one time):
  1. Run check-deps.ps1 — it will detect Tailscale, offer to install
     it, and walk through sign-in.
  2. Sign in to Tailscale with the SAME account as the dev box.
  3. Open index.html in a browser.
  4. In the Server field at the top, replace the default with:
        http://<dev-box-100.x.y.z>:7777
     Hit Save. The pill should turn green.

THAT'S IT. Now you can hit the dev box from anywhere the laptop has
internet — work, cafe, hotel, phone hotspot. No port forward, no
exposing anything to the public internet. Tailscale's free tier
covers up to 100 devices.

-------------------
OPTION B: CLOUDFLARE TUNNEL
-------------------

If you already have a Cloudflare account + domain:
  1. Install cloudflared on the dev box
  2. `cloudflared tunnel create pipe-r`
  3. `cloudflared tunnel route dns pipe-r pipe-r.yourdomain.com`
  4. Route localhost:7777 through the tunnel
  5. Use https://pipe-r.yourdomain.com in the laptop Server field

More complex than Tailscale. Only pick this if you want a pretty URL.

-------------------
OPTION C: NGROK (quick, temporary)
-------------------

  1. `winget install Ngrok.Ngrok` on the dev box
  2. `ngrok http 7777`
  3. Copy the https://xxx.ngrok-free.app URL into the laptop Server
     field

The free tier gives you a random URL that changes every restart.
Fine for a one-off, annoying for daily use.


USING THE CLIENT
----------------
Once the status pill is green:

- **CLAUDE tab**: type a prompt, Ctrl+Enter to send. Runs as
  `claude -p "<your prompt>"` on the dev box. History persists
  in localStorage.

- **SHELL tab**: PowerShell console. Enter to run, ↑/↓ cycles
  the last 50 commands. Bare `claude <text>` auto-wraps to
  `claude -p "<text>"`.

- **DECK tab**: embeds the live Pipe-R ops deck in an iframe.
  Every tab (trainer bench, squad, task queue, metrics, steam,
  chat, settings, etc.) is available. First click loads the
  iframe — subsequent switches are instant.

- **METRICS / STEAM tabs**: same deck page, different anchor.
  Iframe lazy-loads on first click.

- **↗ FULL DECK link**: opens the whole deck in a new browser
  tab for the full-screen experience.


SAFETY NOTES
------------
- Pipe-R's server binds to 0.0.0.0:7777 with no auth on
  /api/shell/run. The LAN assumption is: your WiFi is trusted.
- Tailscale restores that assumption when you're away — only
  devices in your tailnet can reach the dev box IP.
- Don't port-forward 7777 to the public internet unprotected.
- If you need a phone-friendly UI with PIN auth, use
  http://<serverUrl>/remote.html instead — that UI has a 4-digit
  PIN gate (currently 0615).
