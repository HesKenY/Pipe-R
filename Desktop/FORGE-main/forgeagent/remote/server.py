"""Remote monitoring server — serves mobile companion dashboard.

Runs a lightweight HTTP server alongside the TUI.
Auto-discoverable on local network. Mobile connects via IP:port.
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
import socket
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

log = logging.getLogger("forgeagent.remote")

# Shared state — updated by the TUI, read by the HTTP server
_state = {
    "status": "idle",
    "model": "forgeagent",
    "ollama": False,
    "todo_pct": 0,
    "todo_completed": 0,
    "todo_total": 0,
    "todo_current": "",
    "todo_status": "idle",  # idle, running, paused, complete
    "agents": [],
    "datasets": 0,
    "buddy_name": "Sparky",
    "buddy_level": 1,
    "buddy_mood": "happy",
    "log": [],  # last N chat messages
    "last_update": "",
    "uptime_start": datetime.now().isoformat(),
    "project": "",
    "pending_tasks": [],
    "completed_tasks": [],
}

# Command queue — mobile sends commands, TUI picks them up
_command_queue: list[dict] = []
_command_lock = threading.Lock()


def update_state(**kwargs):
    """Update shared state from the TUI thread."""
    _state.update(kwargs)
    _state["last_update"] = datetime.now().isoformat()


def push_log(message: str):
    """Add a log message visible on mobile."""
    _state["log"].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "msg": message,
    })
    # Keep last 100
    if len(_state["log"]) > 100:
        _state["log"] = _state["log"][-100:]


def get_commands() -> list[dict]:
    """Get and clear pending commands from mobile."""
    with _command_lock:
        cmds = list(_command_queue)
        _command_queue.clear()
    return cmds


def _queue_command(cmd: dict):
    with _command_lock:
        _command_queue.append(cmd)


def get_local_ip() -> str:
    """Get the machine's local network IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ── HTML Dashboard ───────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>ForgeAgent Remote</title>
<style>
:root {
  --bg: #0a0e14; --surface: #111822; --cyan: #00e5ff;
  --purple: #7c4dff; --green: #00e676; --red: #ff1744;
  --amber: #ffd740; --dim: #5c6b7a; --text: #e0e0e0;
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: 'SF Mono','Fira Code','Consolas',monospace;
  background: var(--bg); color: var(--text);
  min-height: 100vh; padding: 12px;
  -webkit-font-smoothing: antialiased;
}
.header {
  text-align: center; padding: 16px 0 8px;
  border-bottom: 1px solid #1a2332;
}
.header h1 { color: var(--cyan); font-size: 18px; letter-spacing: 4px; }
.header .sub { color: var(--dim); font-size: 11px; margin-top: 4px; }
.conn {
  text-align: center; padding: 6px; font-size: 11px;
  color: var(--green); transition: color 0.3s;
}
.conn.off { color: var(--red); }

/* Cards */
.card {
  background: var(--surface); border-radius: 8px;
  padding: 14px; margin: 10px 0;
  border: 1px solid #1a2332;
}
.card-title {
  color: var(--cyan); font-size: 11px; letter-spacing: 2px;
  margin-bottom: 8px; text-transform: uppercase;
}
.stat-row {
  display: flex; justify-content: space-between;
  padding: 4px 0; font-size: 13px;
}
.stat-label { color: var(--dim); }
.stat-value { color: var(--text); font-weight: bold; }
.stat-value.online { color: var(--green); }
.stat-value.offline { color: var(--red); }

/* Progress */
.progress-wrap { margin: 8px 0; }
.progress-bar {
  height: 20px; background: #1a2332; border-radius: 10px;
  overflow: hidden; position: relative;
}
.progress-fill {
  height: 100%; border-radius: 10px; transition: width 0.5s ease;
  background: linear-gradient(90deg, var(--purple), var(--cyan));
}
.progress-text {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: bold; color: white;
}
.current-task {
  color: var(--amber); font-size: 12px; margin-top: 6px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* Log */
.log-area {
  max-height: 250px; overflow-y: auto; font-size: 11px;
  padding: 4px 0;
}
.log-line { padding: 2px 0; border-bottom: 1px solid #0d1117; }
.log-time { color: var(--dim); margin-right: 8px; }

/* Tasks */
.task-list { font-size: 12px; }
.task { padding: 4px 0; display: flex; gap: 6px; }
.task-check { color: var(--dim); }
.task-check.done { color: var(--green); }

/* Buttons */
.btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.btn {
  flex: 1; min-width: 80px; padding: 12px 8px;
  border: 1px solid var(--cyan); border-radius: 6px;
  background: transparent; color: var(--cyan);
  font-family: inherit; font-size: 12px; font-weight: bold;
  letter-spacing: 1px; cursor: pointer;
  transition: background 0.2s;
}
.btn:active { background: rgba(0,229,255,0.15); }
.btn.danger { border-color: var(--red); color: var(--red); }
.btn.danger:active { background: rgba(255,23,68,0.15); }
.btn.green { border-color: var(--green); color: var(--green); }
.btn.green:active { background: rgba(0,230,118,0.15); }
.btn.purple { border-color: var(--purple); color: var(--purple); }
.btn.purple:active { background: rgba(124,77,255,0.15); }

/* Agents */
.agent-chip {
  display: inline-block; padding: 4px 10px; margin: 2px;
  border-radius: 12px; font-size: 11px;
  background: #1a2332; border: 1px solid var(--dim);
}
.agent-chip.running { border-color: var(--green); color: var(--green); }
</style>
</head>
<body>

<div class="header">
  <h1>F O R G E</h1>
  <div class="sub">REMOTE MONITOR</div>
</div>
<div class="conn" id="conn">CONNECTING...</div>

<!-- Status -->
<div class="card">
  <div class="card-title">STATUS</div>
  <div class="stat-row"><span class="stat-label">Ollama</span><span class="stat-value" id="s-ollama">—</span></div>
  <div class="stat-row"><span class="stat-label">Model</span><span class="stat-value" id="s-model">—</span></div>
  <div class="stat-row"><span class="stat-label">Status</span><span class="stat-value" id="s-status">—</span></div>
  <div class="stat-row"><span class="stat-label">Datasets</span><span class="stat-value" id="s-datasets">—</span></div>
  <div class="stat-row"><span class="stat-label">Buddy</span><span class="stat-value" id="s-buddy">—</span></div>
</div>

<!-- Progress -->
<div class="card">
  <div class="card-title">TODO PROGRESS</div>
  <div class="progress-wrap">
    <div class="progress-bar">
      <div class="progress-fill" id="p-fill" style="width:0%"></div>
      <div class="progress-text" id="p-text">0%</div>
    </div>
  </div>
  <div class="stat-row"><span class="stat-label">Tasks</span><span class="stat-value" id="p-tasks">0/0</span></div>
  <div class="current-task" id="p-current"></div>
</div>

<!-- Controls -->
<div class="card">
  <div class="card-title">CONTROLS</div>
  <div class="btn-row">
    <button class="btn green" onclick="send('pause')">PAUSE</button>
    <button class="btn" onclick="send('resume')">RESUME</button>
    <button class="btn purple" onclick="send('add_task')">ADD TASK</button>
  </div>
  <div class="btn-row" style="margin-top:6px">
    <button class="btn" onclick="send('save')">SAVE</button>
    <button class="btn" onclick="send('compact')">COMPACT</button>
    <button class="btn danger" onclick="send('stop')">STOP</button>
  </div>
</div>

<!-- Agents -->
<div class="card">
  <div class="card-title">AGENTS</div>
  <div id="agents-list"><span style="color:var(--dim)">None deployed</span></div>
</div>

<!-- Tasks -->
<div class="card">
  <div class="card-title">PENDING TASKS</div>
  <div class="task-list" id="task-list"></div>
</div>

<!-- Log -->
<div class="card">
  <div class="card-title">LIVE LOG</div>
  <div class="log-area" id="log-area"></div>
</div>

<script>
const POLL_MS = 2000;
let fails = 0;

async function poll() {
  try {
    const r = await fetch('/api/state');
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    fails = 0;
    document.getElementById('conn').textContent = 'CONNECTED';
    document.getElementById('conn').className = 'conn';
    update(d);
  } catch(e) {
    fails++;
    const el = document.getElementById('conn');
    el.textContent = fails > 3 ? 'OFFLINE — waiting for PC...' : 'RECONNECTING...';
    el.className = 'conn off';
  }
  setTimeout(poll, fails > 3 ? 5000 : POLL_MS);
}

function update(d) {
  // Status
  const olEl = document.getElementById('s-ollama');
  olEl.textContent = d.ollama ? 'ONLINE' : 'OFFLINE';
  olEl.className = 'stat-value ' + (d.ollama ? 'online' : 'offline');
  document.getElementById('s-model').textContent = d.model || '—';
  document.getElementById('s-status').textContent = d.todo_status.toUpperCase();
  document.getElementById('s-datasets').textContent = d.datasets;
  document.getElementById('s-buddy').textContent = d.buddy_name + ' Lv.' + d.buddy_level + ' (' + d.buddy_mood + ')';

  // Progress
  const pct = d.todo_pct || 0;
  document.getElementById('p-fill').style.width = pct + '%';
  document.getElementById('p-text').textContent = pct + '%';
  document.getElementById('p-tasks').textContent = d.todo_completed + '/' + d.todo_total;
  document.getElementById('p-current').textContent = d.todo_current || '';

  // Agents
  const agEl = document.getElementById('agents-list');
  if (d.agents && d.agents.length) {
    agEl.innerHTML = d.agents.map(a =>
      '<span class="agent-chip ' + (a.status === 'running' ? 'running' : '') + '">' +
      a.name + '</span>'
    ).join('');
  } else {
    agEl.innerHTML = '<span style="color:var(--dim)">None deployed</span>';
  }

  // Tasks
  const tl = document.getElementById('task-list');
  let taskHtml = '';
  (d.completed_tasks || []).forEach(t => {
    taskHtml += '<div class="task"><span class="task-check done">✓</span>' + esc(t) + '</div>';
  });
  (d.pending_tasks || []).forEach(t => {
    taskHtml += '<div class="task"><span class="task-check">○</span>' + esc(t) + '</div>';
  });
  tl.innerHTML = taskHtml || '<span style="color:var(--dim)">No tasks</span>';

  // Log
  const la = document.getElementById('log-area');
  const atBottom = la.scrollTop + la.clientHeight >= la.scrollHeight - 20;
  la.innerHTML = (d.log || []).map(l =>
    '<div class="log-line"><span class="log-time">' + l.time + '</span>' + esc(l.msg) + '</div>'
  ).join('');
  if (atBottom) la.scrollTop = la.scrollHeight;
}

function esc(s) { const d=document.createElement('div');d.textContent=s;return d.innerHTML; }

async function send(cmd) {
  if (cmd === 'add_task') {
    const task = prompt('Enter task for agents:');
    if (!task) return;
    cmd = 'add_task:' + task;
  }
  try {
    await fetch('/api/command', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({command: cmd})
    });
  } catch(e) {}
}

poll();
</script>
</body>
</html>"""


class RemoteHandler(BaseHTTPRequestHandler):
    """Handle API requests and serve dashboard."""

    def log_message(self, fmt, *args):
        # Suppress default HTTP logging
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif self.path == "/api/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(_state).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/command":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                data = json.loads(body)
                cmd = data.get("command", "")
                if cmd:
                    _queue_command({"command": cmd, "time": datetime.now().isoformat()})
            except Exception:
                pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def start_remote_server(port: int = 7777) -> tuple[HTTPServer, str]:
    """Start the remote monitoring server in a background thread.
    Returns (server, url).
    """
    ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", port), RemoteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://{ip}:{port}"
    log.info(f"Remote server started at {url}")
    return server, url
