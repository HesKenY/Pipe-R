# linux-setup — Pop!_OS 24.04 NVIDIA bootstrap

One-click installer that sets up a fresh Pop!_OS 24.04 NVIDIA install with
Ken's full dev + gaming stack.

## After you boot Pop!_OS for the first time

Open a Terminal (GNOME Terminal, preinstalled) and paste:

```bash
bash <(curl -sL https://raw.githubusercontent.com/HesKenY/CHERP-Backup/main/linux-setup/bootstrap.sh)
```

That's it. Enter your password when prompted, grab coffee, ~20 min runtime.

## What it installs

**Dev:**
- Node.js 22 LTS + npm
- Python 3 + pip + venv
- Ollama
- GitHub CLI (gh)
- Claude Code CLI (@anthropic-ai/claude-code)
- OpenAI Codex CLI (@openai/codex)
- VS Code
- Google Chrome
- Tailscale

**Gaming:**
- Steam (with 32-bit arch enabled)
- Lutris (for non-Steam games — Rockstar launcher, EGS, GOG)
- MangoHud (FPS overlay)
- GameMode (CPU governor during play)
- Flatpak + ProtonUp-Qt (GUI for installing/updating Proton-GE)

**System:**
- UFW firewall — Pipe-R port 7777 reachable only over Tailscale
- Clones `HesKenY/CHERP-Backup` to `~/Codex`
- Pulls Ollama base models listed in `ollama-models.txt`

## After bootstrap completes

One-time manual steps (the script prints a summary at the end):

1. `gh auth login` — if not already authenticated (skip repo clone otherwise)
2. `sudo tailscale up` — join the `heskeny@` tailnet
3. `claude` — authenticate Claude Code CLI
4. Launch **ProtonUp-Qt** (from app grid) → install latest Proton-GE
5. Launch **Steam** → sign in → install GTA V + other games
6. Rebuild custom Ollama personalities:
   ```bash
   cd ~/Codex
   ollama create ken-ai -f agent_mode/ken/Modelfile
   ollama create m3w-learning -f agent_mode/m3w/Modelfile
   ```

## Run Pipe-R

```bash
cd ~/Codex
node server.js                 # HTTP API + agent loop on :7777
# or
node hub.js                    # terminal TUI
```

Access the deck from any device on the tailnet:
`http://<this-box-tailscale-ip>:7777/pipe-r.html?deck=1`

## Idempotent

Safe to re-run. Each section checks if the tool is already installed and
skips if so.

## If a section fails

Re-run — it'll pick up where it left off. For Ollama model pulls, edit
`ollama-models.txt` to add/remove models.

## Files

- `bootstrap.sh` — main installer
- `ollama-models.txt` — base models to pull (custom models rebuild from Modelfiles)
- `README.md` — this file
