"""
Pokemon Crystal AI agent v1 — state-aware loop over mGBA bridge.

Run order:
  1. mGBA → load Pokemon Crystal ROM
  2. Tools → Scripting → Load script → agent_mode/pokecrystal/bridge.lua
  3. python agent_mode/pokecrystal/agent.py [--verbose]

Flags:
  --verbose   also dump every tick to poke-tick.jsonl
  --host HOST / --port N   bridge address (defaults 127.0.0.1:8888)
"""

import argparse
import json
import random
import signal
import socket
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RAM_MAP_PATH = HERE / "ram_map.json"
MEM_DIR = REPO / "agent_mode" / "memories" / "ken-ai-latest"
EVENT_LOG = MEM_DIR / "poke-events.jsonl"
TICK_LOG = MEM_DIR / "poke-tick.jsonl"

TICK_SEC = 0.30
DIR_HOLD_FRAMES = 10   # enough for a full tile step on GBC
TAP_HOLD_FRAMES = 6
STUCK_WINDOW = 12      # ticks to scan for stuck detection
STUCK_UNIQUE = 2       # <= this many unique positions = stuck


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class Bridge:
    """Line-oriented TCP client for bridge.lua. Auto-reconnects on drop."""

    def __init__(self, host="127.0.0.1", port=8888):
        self.host = host
        self.port = port
        self.sock = None
        self.buf = b""
        self._connect()

    def _connect(self):
        for attempt in range(10):
            try:
                self.sock = socket.create_connection((self.host, self.port), timeout=5)
                self.sock.settimeout(3.0)
                self.buf = b""
                return
            except (ConnectionRefusedError, OSError) as e:
                print(f"  bridge connect failed ({e}); retry {attempt + 1}/10")
                time.sleep(1.0)
        raise RuntimeError(f"could not connect to bridge at {self.host}:{self.port}")

    def _line(self, cmd):
        for attempt in range(3):
            try:
                if self.sock is None:
                    self._connect()
                self.sock.sendall((cmd + "\n").encode())
                while b"\n" not in self.buf:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        raise ConnectionError("bridge closed")
                    self.buf += chunk
                line, _, rest = self.buf.partition(b"\n")
                self.buf = rest
                return line.decode().strip()
            except (ConnectionError, socket.timeout, OSError) as e:
                print(f"  bridge io err ({e}); reconnecting")
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None
                time.sleep(0.5)
        raise RuntimeError("bridge io failed after 3 retries")

    def ping(self):
        try:
            return self._line("ping") == "pong"
        except Exception:
            return False

    def read_byte(self, addr):
        return int(self._line(f"r8 {addr:x}"), 16)

    def read_range(self, addr, n):
        return bytes.fromhex(self._line(f"r {addr:x} {n}"))

    def press(self, button, frames):
        return self._line(f"press {button} {frames}")

    def clear(self):
        try:
            return self._line("clear")
        except Exception:
            return None


def load_ram_map():
    data = json.loads(RAM_MAP_PATH.read_text())
    return {k: v for k, v in data.items() if not k.startswith("_")}


def read_state(b, ram_map):
    s = {}
    for name, spec in ram_map.items():
        addr = int(spec["addr"], 16)
        size = int(spec.get("size", 1))
        if size == 1:
            s[name] = b.read_byte(addr)
        elif size == 2:
            raw = b.read_range(addr, 2)
            s[name] = raw[0] | (raw[1] << 8)
        else:
            s[name] = b.read_range(addr, size).hex()
    return s


POST_DIALOG_COOLDOWN = 4   # ticks of forced movement after text ends


class Policy:
    """Picks a (button, hold_frames) tuple given current state."""

    def __init__(self):
        self.positions = deque(maxlen=STUCK_WINDOW)
        self.last_dir = "right"
        self.was_in_text = False
        self.cooldown = 0

    def choose(self, state):
        in_text = state.get("text_delay", 0) > 0

        # 1. Text is scrolling — mash B. Two reasons:
        #    a) B advances text but won't confirm yes/no prompts (nickname,
        #       use item, evolve, buy/sell).
        #    b) After text ends, B on the NPC's tile WON'T re-trigger the
        #       same conversation. A would loop us back into the dialog.
        if in_text:
            self.was_in_text = True
            return "b", TAP_HOLD_FRAMES

        # 1b. Just exited dialog — STEP AWAY before any A press.
        # Without this, the random-walk overworld branch can roll an A
        # while we're still on the NPC's tile and re-trigger the dialog.
        if self.was_in_text:
            self.was_in_text = False
            self.cooldown = POST_DIALOG_COOLDOWN

        if self.cooldown > 0:
            self.cooldown -= 1
            return self.last_dir, DIR_HOLD_FRAMES

        # 2. In battle — A to confirm move/menu selections.
        if state.get("battle_mode", 0) != 0:
            return "a", TAP_HOLD_FRAMES

        # 3. Overworld — walk with stuck detection
        return self._overworld(state)

    def _overworld(self, state):
        pos = (
            state.get("map_group"),
            state.get("map_number"),
            state.get("x"),
            state.get("y"),
        )
        self.positions.append(pos)

        unique = len(set(self.positions))
        if len(self.positions) >= STUCK_WINDOW and unique <= STUCK_UNIQUE:
            self.positions.clear()
            return random.choice(["a", "b", "start"]), TAP_HOLD_FRAMES

        # 15% chance to interact, 5% to open menu, else walk
        roll = random.random()
        if roll < 0.12:
            return "a", TAP_HOLD_FRAMES
        if roll < 0.14:
            return "b", TAP_HOLD_FRAMES

        # Bias toward continuing current direction (more fluid walking)
        if random.random() < 0.55:
            return self.last_dir, DIR_HOLD_FRAMES
        self.last_dir = random.choice(["up", "down", "left", "right"])
        return self.last_dir, DIR_HOLD_FRAMES


class EventEmitter:
    """Appends only on meaningful state transitions."""

    TRACKED = ("battle_mode", "map_group", "map_number", "party_count")

    def __init__(self, path):
        self.path = path
        self.prev = None

    def diff(self, state, tick, action):
        events = []
        if self.prev is None:
            events.append({"kind": "boot", "state": state})
        else:
            if state.get("battle_mode") != self.prev.get("battle_mode"):
                events.append({
                    "kind": "battle_transition",
                    "from": self.prev.get("battle_mode"),
                    "to": state.get("battle_mode"),
                })
            prev_map = (self.prev.get("map_group"), self.prev.get("map_number"))
            now_map = (state.get("map_group"), state.get("map_number"))
            if prev_map != now_map:
                events.append({
                    "kind": "map_change",
                    "from": prev_map,
                    "to": now_map,
                    "coords": (state.get("x"), state.get("y")),
                })
            if state.get("party_count") != self.prev.get("party_count"):
                events.append({
                    "kind": "party_change",
                    "from": self.prev.get("party_count"),
                    "to": state.get("party_count"),
                })
        self.prev = state
        if not events:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stamp = utc_now()
        with self.path.open("a", encoding="utf-8") as f:
            for e in events:
                e.update({"at": stamp, "tick": tick, "action": action})
                f.write(json.dumps(e) + "\n")
        for e in events:
            print(f"  ! {e['kind']} @ t{tick}: {e}")


def write_tick(path, tick, state, action):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": utc_now(), "tick": tick, "action": action, "state": state}) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8888)
    ap.add_argument("--verbose", action="store_true", help="dump every tick to poke-tick.jsonl")
    args = ap.parse_args()

    print(f"connecting to bridge {args.host}:{args.port}")
    b = Bridge(args.host, args.port)
    if not b.ping():
        raise RuntimeError("bridge ping failed — is bridge.lua loaded in mGBA?")
    print("bridge ok.")

    ram_map = load_ram_map()
    policy = Policy()
    emitter = EventEmitter(EVENT_LOG)
    tick = 0

    def shutdown(signum=None, frame=None):
        print("\nshutdown — releasing keys")
        try:
            b.clear()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    try:
        signal.signal(signal.SIGTERM, shutdown)
    except (AttributeError, ValueError):
        pass  # not on every platform

    print("running. ctrl-c to stop.")
    while True:
        state = read_state(b, ram_map)
        button, frames = policy.choose(state)
        b.press(button, frames)
        emitter.diff(state, tick, button)
        if args.verbose:
            write_tick(TICK_LOG, tick, state, button)
        if tick % 20 == 0:
            print(
                f"t{tick:04d}  mode={state.get('battle_mode')} "
                f"map={state.get('map_group')}.{state.get('map_number')} "
                f"xy=({state.get('x')},{state.get('y')})  party={state.get('party_count')}  -> {button}/{frames}f"
            )
        tick += 1
        time.sleep(TICK_SEC)


if __name__ == "__main__":
    main()
