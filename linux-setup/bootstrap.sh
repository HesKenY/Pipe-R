#!/usr/bin/env bash
# linux-setup/bootstrap.sh — one-click Pop!_OS 24.04 NVIDIA setup for Ken
#
# Run once after first boot of Pop!_OS. Idempotent — safe to re-run.
# Paste into a terminal:
#
#   bash <(curl -sL https://raw.githubusercontent.com/HesKenY/CHERP-Backup/main/linux-setup/bootstrap.sh)
#
# Or clone the repo first, then:
#
#   bash linux-setup/bootstrap.sh
#
# Installs: Node.js LTS, Python, Ollama, gh, Chrome, VS Code, Tailscale,
# Claude Code CLI, Codex CLI, Steam + Proton-GE + Lutris + MangoHud +
# GameMode, firewall rules, repo clone, Ollama base model pulls.

set -euo pipefail

# ---- pretty output ---------------------------------------------------------
BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step()  { echo -e "\n${BLUE}==>${NC} ${1}"; }
ok()    { echo -e "${GREEN}OK${NC} ${1}"; }
warn()  { echo -e "${YELLOW}!!${NC} ${1}"; }
fail()  { echo -e "${RED}XX${NC} ${1}"; exit 1; }

# ---- sanity ---------------------------------------------------------------
step "Sanity checks"
if ! grep -qi 'pop!_os\|pop_os' /etc/os-release 2>/dev/null; then
  warn "Not Pop!_OS — script assumes Pop. Continue anyway? [y/N]"
  read -r ans; [[ "$ans" =~ ^[Yy]$ ]] || exit 1
fi
if [ "$(id -u)" -eq 0 ]; then fail "Don't run as root. Use your user account; sudo will prompt."; fi

step "Cache sudo password (keeps alive for the whole run)"
sudo -v
while true; do sudo -n true; sleep 60; kill -0 "$$" 2>/dev/null || exit; done 2>/dev/null &
SUDO_REFRESH=$!
trap 'kill $SUDO_REFRESH 2>/dev/null || true' EXIT

# ---- baseline --------------------------------------------------------------
step "System update"
sudo apt-get update
sudo apt-get upgrade -y

step "Dev essentials"
sudo apt-get install -y \
  git curl wget jq unzip zip tree htop vim build-essential \
  ca-certificates gnupg lsb-release software-properties-common \
  apt-transport-https ufw net-tools
ok "Dev essentials installed"

# ---- Node.js LTS (NodeSource) ---------------------------------------------
step "Node.js 22 LTS"
if ! command -v node >/dev/null || ! node --version | grep -q '^v22'; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
ok "Node $(node --version), npm $(npm --version)"

# ---- Python 3 + pip + venv -------------------------------------------------
step "Python 3 + pip + venv"
sudo apt-get install -y python3 python3-pip python3-venv python-is-python3
ok "Python $(python3 --version)"

# ---- Ollama ---------------------------------------------------------------
step "Ollama"
if ! command -v ollama >/dev/null; then
  curl -fsSL https://ollama.com/install.sh | sh
else
  ok "Ollama already installed"
fi
ok "Ollama $(ollama --version 2>&1 | head -1)"

# ---- GitHub CLI -----------------------------------------------------------
step "GitHub CLI (gh)"
if ! command -v gh >/dev/null; then
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | \
    sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
  sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
  sudo apt-get update
  sudo apt-get install -y gh
fi
ok "gh $(gh --version | head -1)"

# ---- Google Chrome --------------------------------------------------------
step "Google Chrome"
if ! command -v google-chrome >/dev/null; then
  wget -qO - https://dl.google.com/linux/linux_signing_key.pub | \
    sudo gpg --dearmor -o /usr/share/keyrings/google-chrome-keyring.gpg
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | \
    sudo tee /etc/apt/sources.list.d/google-chrome.list > /dev/null
  sudo apt-get update
  sudo apt-get install -y google-chrome-stable
fi
ok "Chrome installed"

# ---- VS Code --------------------------------------------------------------
step "VS Code"
if ! command -v code >/dev/null; then
  wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | \
    sudo tee /usr/share/keyrings/packages.microsoft.gpg > /dev/null
  echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" | \
    sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null
  sudo apt-get update
  sudo apt-get install -y code
fi
ok "VS Code installed"

# ---- Tailscale ------------------------------------------------------------
step "Tailscale"
if ! command -v tailscale >/dev/null; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
ok "Tailscale installed (run 'sudo tailscale up' later to join tailnet)"

# ---- Claude Code CLI -------------------------------------------------------
step "Claude Code CLI"
sudo npm install -g @anthropic-ai/claude-code || warn "Claude Code CLI install failed (check npm config)"
ok "Claude Code installed (run 'claude' to authenticate)"

# ---- Codex CLI ------------------------------------------------------------
step "OpenAI Codex CLI"
sudo npm install -g @openai/codex || warn "Codex CLI install failed — might need different package name"
ok "Codex CLI attempted"

# ---- Gaming stack ---------------------------------------------------------
step "Enable 32-bit architecture (required for Steam)"
sudo dpkg --add-architecture i386
sudo apt-get update

step "Steam"
sudo apt-get install -y steam-installer || sudo apt-get install -y steam
ok "Steam installed"

step "Lutris + MangoHud + GameMode"
sudo apt-get install -y lutris mangohud gamemode
ok "Lutris / MangoHud / GameMode installed"

step "Flatpak + ProtonUp-Qt (for Proton-GE management)"
sudo apt-get install -y flatpak
sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
sudo flatpak install -y flathub net.davidotek.pupgui2 || warn "ProtonUp-Qt flatpak skipped"
ok "ProtonUp-Qt installed (launch it to pick + install Proton-GE)"

# ---- firewall -------------------------------------------------------------
step "UFW firewall — allow Pipe-R on 7777 (Tailscale only)"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow in on tailscale0 to any port 7777 proto tcp comment "Pipe-R server over Tailscale"
sudo ufw --force enable
ok "UFW enabled (Pipe-R 7777 reachable only via Tailscale)"

# ---- repo clone -----------------------------------------------------------
step "Clone CHERP-Backup repo to ~/Codex"
if [ ! -d "$HOME/Codex" ]; then
  gh auth status >/dev/null 2>&1 || {
    warn "gh not authenticated. Run 'gh auth login' then re-run this script."
    warn "Skipping repo clone."
  }
  if gh auth status >/dev/null 2>&1; then
    gh repo clone HesKenY/CHERP-Backup "$HOME/Codex"
    ok "Repo cloned to ~/Codex"
  fi
else
  ok "~/Codex already exists — skipping clone"
fi

# ---- Ollama base models ---------------------------------------------------
step "Pull Ollama base models (this takes a while — 10-30 min depending on bandwidth)"
if [ -f "$HOME/Codex/linux-setup/ollama-models.txt" ]; then
  while IFS= read -r model; do
    [[ -z "$model" || "$model" =~ ^# ]] && continue
    echo "  pulling $model..."
    ollama pull "$model" || warn "Failed to pull $model"
  done < "$HOME/Codex/linux-setup/ollama-models.txt"
  ok "Ollama base models pulled"
else
  warn "Skipping Ollama models — model list not found at ~/Codex/linux-setup/ollama-models.txt"
fi

# ---- done -----------------------------------------------------------------
step "Bootstrap complete"
cat <<EOF

${GREEN}All core tools installed.${NC}

Next steps (manual, one-time):
  1. gh auth login                   # if not done yet; then re-run this script for repo clone
  2. sudo tailscale up               # join your tailnet (heskeny@)
  3. claude                           # authenticate Claude Code
  4. Launch ProtonUp-Qt → install latest Proton-GE
  5. Launch Steam → sign in → install games from library
  6. Rebuild custom Ollama models from Modelfiles in ~/Codex/agent_mode/ken/, ~/Codex/agent_mode/m3w/
     (e.g.  ollama create ken-ai -f ~/Codex/agent_mode/ken/Modelfile)

Pipe-R server:
  cd ~/Codex && node server.js

EOF
