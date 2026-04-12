## HP Remote — dependency check / auto-install
##
## Run this on the laptop (where hp-remote is unzipped) to verify the
## setup before opening index.html. Checks:
##   1. Pipe-R dev box is reachable on the LAN
##   2. (optional) Node.js is installed locally for backup/offline use
##   3. (optional) Claude Code CLI is installed locally
##
## If Node or Claude are missing and Ken confirms, install via winget/npm.
## Double-click works via PowerShell → Right-click → Run with PowerShell.

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

function Write-Step($msg) { Write-Host "[*] $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[+] $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "[X] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "================================================" -ForegroundColor Magenta
Write-Host "   HP Remote  -  Pipe-R Client Dependency Check" -ForegroundColor Magenta
Write-Host "================================================" -ForegroundColor Magenta
Write-Host ""

# ---- Read current server URL from localStorage hint --------------
$defaultServer = 'http://192.168.0.58:7777'
$serverUrl = Read-Host "Pipe-R server URL [$defaultServer]"
if (-not $serverUrl) { $serverUrl = $defaultServer }
$serverUrl = $serverUrl.TrimEnd('/')

# ---- Step 1: reach the dev box ----------------------------------
Write-Step "Checking reachability of $serverUrl ..."
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
    Write-Host "      - Dev box is off, or DECK.bat / server.js is not running" -ForegroundColor DarkGray
    Write-Host "      - Laptop is on a different WiFi / network" -ForegroundColor DarkGray
    Write-Host "      - Dev box LAN IP has changed (edit the Server field in index.html)" -ForegroundColor DarkGray
    Write-Host "      - Windows firewall on dev box is blocking inbound 7777" -ForegroundColor DarkGray
}

# ---- Step 2: Node.js local --------------------------------------
Write-Step "Checking for local Node.js install..."
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    $nv = (& node --version 2>$null)
    Write-OK "Node.js found: $nv  ($($node.Source))"
} else {
    Write-Warn "Node.js is not installed on the laptop."
    Write-Host "    You don't strictly need it on the laptop to use the HP Remote client" -ForegroundColor DarkGray
    Write-Host "    (the browser talks to the dev box), but it's handy for offline tooling." -ForegroundColor DarkGray
    $install = Read-Host "Install Node.js LTS via winget now? [y/N]"
    if ($install -match '^[yY]') {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            Write-Step "Running: winget install OpenJS.NodeJS.LTS"
            winget install --id OpenJS.NodeJS.LTS -e --silent --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) {
                Write-OK "Node.js install finished. Open a new terminal for PATH to pick up."
            } else {
                Write-Err "winget exited $LASTEXITCODE"
            }
        } else {
            Write-Err "winget not available. Install Node.js manually from https://nodejs.org/"
        }
    }
}

# ---- Step 3: Claude Code local ----------------------------------
Write-Step "Checking for local Claude Code CLI install..."
$claude = Get-Command claude -ErrorAction SilentlyContinue
if ($claude) {
    try {
        $cv = (& claude --version 2>$null)
        Write-OK "Claude Code found: $cv  ($($claude.Source))"
    } catch {
        Write-OK "Claude Code CLI present at $($claude.Source)"
    }
} else {
    Write-Warn "Claude Code CLI is not installed on the laptop."
    Write-Host "    The HP Remote client runs Claude on the DEV BOX, not here." -ForegroundColor DarkGray
    Write-Host "    Local install is only needed if you want to run Claude offline on the laptop." -ForegroundColor DarkGray
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($npm) {
        $install = Read-Host "Install Claude Code CLI via npm now? [y/N]"
        if ($install -match '^[yY]') {
            Write-Step "Running: npm install -g @anthropic-ai/claude-code"
            & npm install -g @anthropic-ai/claude-code
            if ($LASTEXITCODE -eq 0) {
                Write-OK "Claude Code installed. Open a new terminal for PATH."
            } else {
                Write-Err "npm exited $LASTEXITCODE"
            }
        }
    } else {
        Write-Warn "npm not found. Install Node.js first (step 2), then re-run this script."
    }
}

Write-Host ""
Write-Host "------------------------------------------------" -ForegroundColor Magenta
Write-Host "   Check complete. Double-click index.html to launch the client." -ForegroundColor Magenta
Write-Host "------------------------------------------------" -ForegroundColor Magenta
Write-Host ""
Read-Host "Press Enter to close"
