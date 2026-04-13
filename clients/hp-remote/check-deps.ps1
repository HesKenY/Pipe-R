## HP Remote v3 — dependency + reachability check
##
## Run this on the laptop you want to connect from. It:
##   1. Probes the configured Pipe-R server URL
##   2. Detects Tailscale install + status (recommended for work-from-anywhere)
##   3. Optionally installs Node.js + Claude Code locally for backup use
##
## Right-click > Run with PowerShell.

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

function Write-Step($msg) { Write-Host "[*] $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[+] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[X] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "================================================" -ForegroundColor Magenta
Write-Host "   HP Remote v3  -  Pipe-R Client Dependency Check" -ForegroundColor Magenta
Write-Host "================================================" -ForegroundColor Magenta
Write-Host ""

$defaultServer = 'http://192.168.0.58:7777'
Write-Host "Default server URL is $defaultServer (home LAN)." -ForegroundColor DarkGray
Write-Host "For work/remote use you'll want a Tailscale URL like http://100.x.y.z:7777" -ForegroundColor DarkGray
$serverUrl = Read-Host "Pipe-R server URL [$defaultServer]"
if (-not $serverUrl) { $serverUrl = $defaultServer }
$serverUrl = $serverUrl.TrimEnd('/')

# ---- Step 1: reach the server ----------------------------------
Write-Step "Probing $serverUrl ..."
try {
    $resp = Invoke-WebRequest -Uri "$serverUrl/api/dashboard" -TimeoutSec 5 -UseBasicParsing
    if ($resp.StatusCode -eq 200) {
        $json = $resp.Content | ConvertFrom-Json
        $trainer = if ($json.trainer.displayName) { $json.trainer.displayName } else { 'pipe-r' }
        Write-OK "Server reachable. Trainer: $trainer"
    } else {
        Write-Warn "Server responded with HTTP $($resp.StatusCode)."
    }
} catch {
    Write-Err "Could not reach $serverUrl"
    Write-Host "    Possible causes:" -ForegroundColor DarkGray
    Write-Host "      - You are NOT on the home LAN (the 192.168.0.58 IP only exists there)" -ForegroundColor DarkGray
    Write-Host "      - Dev box is off, or DECK.bat / server.js is not running" -ForegroundColor DarkGray
    Write-Host "      - Windows firewall on dev box is blocking inbound TCP 7777" -ForegroundColor DarkGray
    Write-Host "    => For work/remote access, set up Tailscale (step 2 below)." -ForegroundColor Yellow
}

# ---- Step 2: Tailscale ------------------------------------------
Write-Host ""
Write-Step "Checking for Tailscale (recommended for work-from-anywhere)..."
$tailscalePath = @(
    "$env:ProgramFiles\Tailscale\tailscale.exe",
    "${env:ProgramFiles(x86)}\Tailscale\tailscale.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($tailscalePath) {
    Write-OK "Tailscale installed at $tailscalePath"
    try {
        $tsStatus = & $tailscalePath status 2>&1 | Select-Object -First 6
        if ($tsStatus) {
            Write-Host ""
            Write-Host "    Tailscale status:" -ForegroundColor DarkGray
            $tsStatus | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkGray }
        }
        $myIp = & $tailscalePath ip -4 2>&1 | Select-Object -First 1
        if ($myIp -match '^100\.') {
            Write-OK "This laptop's Tailscale IP: $myIp"
            Write-Host ""
            Write-Host "    On the dev box, run the same command to get its 100.x.y.z IP," -ForegroundColor Yellow
            Write-Host "    then in index.html use  http://<devbox-tailscale-ip>:7777" -ForegroundColor Yellow
        }
    } catch {
        Write-Warn "Tailscale CLI didn't answer — are you logged in? Run: tailscale up"
    }
} else {
    Write-Warn "Tailscale is NOT installed."
    Write-Host ""
    Write-Host "    Tailscale gives the dev box and this laptop stable 100.x.y.z IPs that" -ForegroundColor DarkGray
    Write-Host "    reach each other from any network (home, work, coffee shop). Free for" -ForegroundColor DarkGray
    Write-Host "    personal use, zero config after sign-in, works through NAT / CGNAT." -ForegroundColor DarkGray
    Write-Host ""
    $install = Read-Host "Install Tailscale via winget now? [y/N]"
    if ($install -match '^[yY]') {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            Write-Step "Running: winget install Tailscale.Tailscale"
            winget install --id Tailscale.Tailscale -e --silent --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) {
                Write-OK "Tailscale install finished."
                Write-Host "    Next steps:" -ForegroundColor Yellow
                Write-Host "      1. Open the Tailscale tray app and sign in (same account on dev box and laptop)" -ForegroundColor Yellow
                Write-Host "      2. On the dev box, also install Tailscale and sign in with the same account" -ForegroundColor Yellow
                Write-Host "      3. Run 'tailscale ip -4' on the dev box to get its 100.x.y.z address" -ForegroundColor Yellow
                Write-Host "      4. Use that address in index.html's Server field on the laptop" -ForegroundColor Yellow
            } else {
                Write-Err "winget exited $LASTEXITCODE"
            }
        } else {
            Write-Err "winget not available. Install Tailscale manually from https://tailscale.com/download"
        }
    }
}

# ---- Step 3: Node.js local --------------------------------------
Write-Host ""
Write-Step "Checking for local Node.js install (optional, for offline tooling)..."
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    $nv = (& node --version 2>$null)
    Write-OK "Node.js found: $nv  ($($node.Source))"
} else {
    Write-Warn "Node.js is not installed on the laptop."
    Write-Host "    Not required — the HP Remote client is just a browser talking to the dev box." -ForegroundColor DarkGray
    $install = Read-Host "Install Node.js LTS via winget now? [y/N]"
    if ($install -match '^[yY]') {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            winget install --id OpenJS.NodeJS.LTS -e --silent --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) { Write-OK "Node.js installed." }
        }
    }
}

# ---- Step 4: Claude Code local ----------------------------------
Write-Host ""
Write-Step "Checking for local Claude Code CLI install (optional)..."
$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($claude) {
    Write-OK "Claude Code found at $($claude.Source)"
} else {
    Write-Warn "Claude Code CLI is not installed on the laptop (not required)."
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($npm) {
        $install = Read-Host "Install Claude Code CLI via npm now? [y/N]"
        if ($install -match '^[yY]') {
            & npm install -g "@anthropic-ai/claude-code"
            if ($LASTEXITCODE -eq 0) { Write-OK "Claude Code installed." }
        }
    }
}

Write-Host ""
Write-Host "------------------------------------------------" -ForegroundColor Magenta
Write-Host "   Check complete. Launch the client:" -ForegroundColor Magenta
Write-Host "     1. Double-click index.html" -ForegroundColor White
Write-Host "     2. If status pill says 'unreachable', edit the Server field" -ForegroundColor White
Write-Host "        to your Tailscale URL and hit Save" -ForegroundColor White
Write-Host "------------------------------------------------" -ForegroundColor Magenta
Write-Host ""
Read-Host "Press Enter to close"
