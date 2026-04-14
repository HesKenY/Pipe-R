from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

import tkinter as tk


ROOT = Path(__file__).resolve().parents[2]
SERVER_URL = "http://127.0.0.1:7777"
SERVER_JS = ROOT / "server.js"

TRAINING_FILE = ROOT / "agent_mode" / "config" / "halo_training.json"
MEMORY_DIR = ROOT / "agent_mode" / "memories" / "ken-ai-latest"
HALO_LOG = MEMORY_DIR / "halo-log.jsonl"
HALO_EVENTS = MEMORY_DIR / "halo-events.jsonl"
HALO_KEYLOG = MEMORY_DIR / "halo-keylog.jsonl"
HALO_VISION = MEMORY_DIR / "halo-vision-cache.json"
HALO_JUMPSTART = MEMORY_DIR / "halo-jumpstart.json"

DEFAULT_START_PAYLOADS = [
    ("POST", "/api/halo/training-mode/on", {
        "goal": "one-hit-kill headshot target practice while Ken steers and Ken AI learns dev reflexes",
        "targetPractice": True,
        "oneHitKill": True,
        "graduated": False,
    }),
    ("POST", "/api/halo/keylog/start", {}),
    ("POST", "/api/halo/analyzer/start", {"intervalMs": 1500}),
    ("POST", "/api/halo/vision/start", {"intervalMs": 20000, "model": "llama3.2-vision"}),
    ("POST", "/api/halo/aim/start", {
        "intervalMs": 120,
        "palette": "all",
        "minConfidence": 0.04,
        "engage": True,
        "burstSize": 1,
        "shotDelay": 85,
        "maxShots": 1,
    }),
    ("POST", "/api/halo/start", {
        "tickMs": 3000,
        "model": "ken-ai:latest",
        "mode": "drive",
        "lifelike": True,
    }),
    ("POST", "/api/halo/trainer/start", {"intervalMs": 90000, "model": "ken-ai:latest"}),
]

DEFAULT_STOP_PATHS = [
    "/api/halo/stop",
    "/api/halo/aim/stop",
    "/api/halo/vision/stop",
    "/api/halo/trainer/stop",
    "/api/halo/analyzer/stop",
    "/api/halo/keylog/stop",
    "/api/halo/training-mode/off",
]


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def read_recent_jsonl(path: Path, limit: int = 8) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = deque(path.read_text(encoding="utf-8", errors="ignore").splitlines(), maxlen=max(limit * 4, 20))
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows[-limit:]


def iso_to_age_seconds(value: str | None) -> int | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
    except Exception:
        return None


def short_text(value: Any, limit: int = 80) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def format_key_event(row: dict[str, Any]) -> str:
    kind = row.get("kind")
    if kind == "key":
        return str(row.get("key") or "?")
    if kind == "mouse":
        button = str(row.get("button") or "mouse")
        return button.replace("Button.", "").replace("Button", "mouse")
    return str(kind or "?")


def server_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 7777), timeout=0.6):
            return True
    except OSError:
        return False


def start_server() -> bool:
    if server_running():
        return True
    creationflags = 0
    creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(
        ["node", "server.js"],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    deadline = time.time() + 18
    while time.time() < deadline:
        if server_running():
            return True
        time.sleep(0.4)
    return False


def restart_server_process() -> bool:
    powershell = (
        "$listener = Get-NetTCPConnection -LocalPort 7777 -State Listen -ErrorAction SilentlyContinue | "
        "Select-Object -First 1; "
        "if ($listener) { Stop-Process -Id $listener.OwningProcess -Force }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", powershell],
        cwd=str(ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    deadline = time.time() + 8
    while time.time() < deadline and server_running():
        time.sleep(0.25)
    return start_server()


def api_call(method: str, path: str, payload: Any | None = None, timeout: int = 45) -> Any:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(SERVER_URL + path, data=body, headers=headers, method=method)
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")
        if not raw:
            return {"ok": True}
        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw}


def stop_stack(ignore_errors: bool = False) -> dict[str, Any]:
    results: dict[str, Any] = {}
    if not server_running():
        return {"server": "offline"}
    for path in DEFAULT_STOP_PATHS:
        try:
            results[path] = api_call("POST", path, {})
        except Exception as exc:
            if not ignore_errors:
                raise
            results[path] = {"error": str(exc)}
    return results


def start_stack(restart: bool = True) -> dict[str, Any]:
    if restart:
        if server_running():
            stop_stack(ignore_errors=True)
            time.sleep(0.75)
        if not restart_server_process():
            raise RuntimeError("server did not restart on :7777")
    elif not start_server():
        raise RuntimeError("server did not start on :7777")
    results: dict[str, Any] = {}
    for method, path, payload in DEFAULT_START_PAYLOADS:
        results[path] = api_call(method, path, payload)
        time.sleep(0.15)
    return results


def load_snapshot() -> dict[str, Any]:
    training = load_json(TRAINING_FILE, {})
    tick = (read_recent_jsonl(HALO_LOG, 1) or [None])[-1]
    event = (read_recent_jsonl(HALO_EVENTS, 1) or [None])[-1]
    vision = load_json(HALO_VISION, {})
    jumpstart = load_json(HALO_JUMPSTART, {})
    key_rows = [
        row for row in read_recent_jsonl(HALO_KEYLOG, 40)
        if row.get("kind") != "system" and row.get("dir") != "up"
    ]
    key_rows = key_rows[-8:]
    tick_age = iso_to_age_seconds((tick or {}).get("at"))
    vision_age = iso_to_age_seconds((vision or {}).get("at"))
    return {
        "server": server_running(),
        "training": training,
        "tick": tick,
        "event": event,
        "vision": vision,
        "jumpstart": jumpstart,
        "keys": key_rows,
        "tick_age": tick_age,
        "vision_age": vision_age,
        "live": tick_age is not None and tick_age < 150,
    }


class OverlayWindow:
    def __init__(self, master: tk.Tk) -> None:
        self.window = tk.Toplevel(master)
        self.window.title("Ken AI Halo Overlay")
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0.88)
        self.window.configure(bg="#07141f")

        sw = self.window.winfo_screenwidth()
        self.window.geometry(f"430x260+{max(20, sw - 460)}+30")

        self.header = tk.Label(
            self.window,
            text="KEN AI HALO",
            font=("Consolas", 13, "bold"),
            fg="#9ef8d8",
            bg="#07141f",
            anchor="w",
            padx=12,
            pady=10,
        )
        self.header.pack(fill="x")

        self.body = tk.Label(
            self.window,
            text="waiting for halo data...",
            justify="left",
            anchor="nw",
            font=("Consolas", 10),
            fg="#d9f6ff",
            bg="#07141f",
            padx=12,
            pady=8,
        )
        self.body.pack(fill="both", expand=True)

        self.drag_offset: tuple[int, int] | None = None
        for widget in (self.window, self.header, self.body):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag)

    def _start_drag(self, event: tk.Event) -> None:
        self.drag_offset = (event.x_root - self.window.winfo_x(), event.y_root - self.window.winfo_y())

    def _drag(self, event: tk.Event) -> None:
        if not self.drag_offset:
            return
        dx, dy = self.drag_offset
        self.window.geometry(f"+{event.x_root - dx}+{event.y_root - dy}")

    def set_visible(self, visible: bool) -> None:
        if visible:
            self.window.deiconify()
        else:
            self.window.withdraw()

    def render(self, snapshot: dict[str, Any]) -> None:
        tick = snapshot.get("tick") or {}
        training = snapshot.get("training") or {}
        vision = snapshot.get("vision") or {}
        event = snapshot.get("event") or {}
        tick_age = snapshot.get("tick_age")
        keys = " ".join(format_key_event(row) for row in snapshot.get("keys") or []) or "(waiting)"
        live = snapshot.get("live")
        jumpstart = snapshot.get("jumpstart") or {}
        style_notes = ", ".join((jumpstart.get("styleNotes") or [])[:2]) or "building from keylogs"
        header_color = "#8ef0b7" if live else "#ffc97d"
        state_before = tick.get("stateBefore") or {}

        lines = [
            f"engine: {'LIVE' if live else 'STALE'}   server: {'UP' if snapshot.get('server') else 'DOWN'}",
            f"mode: {tick.get('mode') or 'n/a'}   last tick: {tick_age if tick_age is not None else '?'}s ago",
            f"action: {tick.get('action') or 'n/a'}   raw: {short_text(tick.get('rawResponse') or 'n/a', 34)}",
            f"training: {'ON' if training.get('safety_net') else 'OFF'} | target practice: {'ON' if training.get('target_practice') else 'OFF'}",
            f"one-hit-kill: {'ON' if training.get('one_hit_kill') else 'OFF'}",
            f"hud: {state_before.get('activity') or 'n/a'} | shield={short_text(state_before.get('shield') or '-', 14)} | ammo={short_text(state_before.get('ammo') or '-', 10)}",
            f"center: {short_text(state_before.get('center') or '-', 52)}",
            f"vision: {short_text(vision.get('situation') or 'pending', 28)} ({snapshot.get('vision_age') if snapshot.get('vision_age') is not None else '?'}s)",
            f"sees: {short_text(vision.get('enemies') or 'unknown', 48)}",
            f"suggests: {short_text(vision.get('suggestion') or 'waiting on vision cache', 48)}",
            f"jumpstart: {short_text(style_notes, 54)}",
            f"recent keys: {short_text(keys, 58)}",
            f"last event: {short_text(event.get('kind') or 'none', 28)}",
        ]
        self.header.configure(fg=header_color)
        self.body.configure(text="\n".join(lines))


class ControlApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Ken AI Halo Control")
        self.geometry("500x460+30+30")
        self.configure(bg="#0c1824")

        self.overlay_visible = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="ready")
        self.summary_var = tk.StringVar(value="halo idle")
        self.vision_var = tk.StringVar(value="vision pending")
        self.keys_var = tk.StringVar(value="keys waiting")
        self.training_var = tk.StringVar(value="training mode pending")

        self.overlay = OverlayWindow(self)
        self._build_ui()
        self.refresh_snapshot()
        self.after(1500, self._poll)

    def _build_ui(self) -> None:
        title = tk.Label(
            self,
            text="KEN AI HALO CONTROL",
            font=("Consolas", 16, "bold"),
            fg="#9ef8d8",
            bg="#0c1824",
            pady=14,
        )
        title.pack()

        button_row = tk.Frame(self, bg="#0c1824")
        button_row.pack(fill="x", padx=18, pady=8)

        self._make_button(button_row, "Start Ken AI", self.start_clicked, "#1f8259").pack(side="left", padx=4)
        self._make_button(button_row, "Stop Ken AI", self.stop_clicked, "#7c2435").pack(side="left", padx=4)
        self._make_button(button_row, "Refresh", self.refresh_snapshot, "#315d8a").pack(side="left", padx=4)
        self._make_button(button_row, "Restart Server", self.restart_server_clicked, "#6252a2").pack(side="left", padx=4)

        overlay_row = tk.Frame(self, bg="#0c1824")
        overlay_row.pack(fill="x", padx=18, pady=(0, 8))

        self._make_button(overlay_row, "Show Overlay", lambda: self.set_overlay(True), "#3a4660").pack(side="left", padx=4)
        self._make_button(overlay_row, "Hide Overlay", lambda: self.set_overlay(False), "#3a4660").pack(side="left", padx=4)

        cards = tk.Frame(self, bg="#0c1824")
        cards.pack(fill="both", expand=True, padx=18, pady=8)

        self._make_card(cards, "Status", self.status_var).pack(fill="x", pady=5)
        self._make_card(cards, "Last Tick", self.summary_var).pack(fill="x", pady=5)
        self._make_card(cards, "Vision", self.vision_var).pack(fill="x", pady=5)
        self._make_card(cards, "Recent Keys", self.keys_var).pack(fill="x", pady=5)
        self._make_card(cards, "Training", self.training_var).pack(fill="x", pady=5)

    def _make_button(self, master: tk.Misc, label: str, command: Any, color: str) -> tk.Button:
        return tk.Button(
            master,
            text=label,
            command=command,
            font=("Consolas", 10, "bold"),
            fg="#f3fbff",
            bg=color,
            activebackground=color,
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=8,
        )

    def _make_card(self, master: tk.Misc, title: str, variable: tk.StringVar) -> tk.Frame:
        frame = tk.Frame(master, bg="#132435", highlightbackground="#244159", highlightthickness=1)
        header = tk.Label(frame, text=title, font=("Consolas", 11, "bold"), fg="#9ef8d8", bg="#132435", anchor="w")
        header.pack(fill="x", padx=12, pady=(10, 4))
        # tk.Label config accepts only a single int for pady, not a
        # tuple — tuples are geometry-manager (pack/grid) options.
        # Push the top/bottom spacing into .pack() instead.
        body = tk.Label(
            frame,
            textvariable=variable,
            justify="left",
            anchor="w",
            wraplength=450,
            font=("Consolas", 10),
            fg="#d9f6ff",
            bg="#132435",
            padx=12,
        )
        body.pack(fill="x", pady=(0, 10))
        return frame

    def set_overlay(self, visible: bool) -> None:
        self.overlay_visible.set(visible)
        self.overlay.set_visible(visible)

    def _run_async(self, label: str, func: Any) -> None:
        self.status_var.set(label)

        def worker() -> None:
            try:
                result = func()
                message = short_text(json.dumps(result), 140)
            except Exception as exc:
                message = f"error: {exc}"
            self.after(0, lambda: self.status_var.set(message))
            self.after(0, self.refresh_snapshot)

        threading.Thread(target=worker, daemon=True).start()

    def start_clicked(self) -> None:
        self._run_async("starting ken ai halo...", lambda: start_stack(restart=True))

    def stop_clicked(self) -> None:
        self._run_async("stopping ken ai halo...", lambda: stop_stack(ignore_errors=True))

    def restart_server_clicked(self) -> None:
        def restart_server_only() -> dict[str, Any]:
            stop_stack(ignore_errors=True)
            restart_server_process()
            return {"server": "up" if server_running() else "down"}

        self._run_async("restarting local deck server...", restart_server_only)

    def refresh_snapshot(self) -> None:
        snap = load_snapshot()
        tick = snap.get("tick") or {}
        training = snap.get("training") or {}
        vision = snap.get("vision") or {}
        jumpstart = snap.get("jumpstart") or {}
        event = snap.get("event") or {}
        age = snap.get("tick_age")
        mode = tick.get("mode") or "n/a"
        action = tick.get("action") or "n/a"
        state_before = tick.get("stateBefore") or {}
        keys = ", ".join(format_key_event(row) for row in snap.get("keys") or []) or "(waiting)"

        self.summary_var.set(
            f"{'LIVE' if snap.get('live') else 'STALE'} | mode={mode} | action={action} | "
            f"tick age={age if age is not None else '?'}s | hud={state_before.get('activity') or 'n/a'}"
        )
        self.vision_var.set(
            f"{short_text(vision.get('situation') or 'pending', 48)} | sees: "
            f"{short_text(vision.get('enemies') or 'unknown', 52)} | "
            f"suggests: {short_text(vision.get('suggestion') or 'waiting on vision cache', 64)}"
        )
        self.keys_var.set(keys)
        self.training_var.set(
            f"safety net={'ON' if training.get('safety_net') else 'OFF'} | "
            f"target practice={'ON' if training.get('target_practice') else 'OFF'} | "
            f"one-hit-kill={'ON' if training.get('one_hit_kill') else 'OFF'} | "
            f"jumpstart={short_text(', '.join((jumpstart.get('styleNotes') or [])[:2]) or 'building', 72)} | "
            f"goal={short_text(training.get('goal') or 'n/a', 72)} | "
            f"last event={short_text(event.get('kind') or 'none', 24)}"
        )
        if self.overlay_visible.get():
            self.overlay.render(snap)

    def _poll(self) -> None:
        self.refresh_snapshot()
        self.after(1500, self._poll)


def cli_main(args: list[str]) -> int:
    if "--start-stack" in args:
        print(json.dumps(start_stack(restart=True), indent=2))
        return 0
    if "--stop-stack" in args:
        print(json.dumps(stop_stack(ignore_errors=True), indent=2))
        return 0
    app = ControlApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main(sys.argv[1:]))
