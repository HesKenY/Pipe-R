# Windows rules — hard constraints for KenAI on this box

Ken's development machine is Windows 11 Pro (cp1252 console,
NTFS, PowerShell + cmd.exe + Git Bash all in play). These rules
override generic advice that assumes Linux/mac. KenAI checks
this file before picking any shell command, file path, or
subprocess spawn.

## Paths — hard rules

- **Always use forward slashes** in strings that will be passed
  to Python/Node/JS code. Both `C:/Users/Ken/...` and
  `C:\\Users\\Ken\\...` work in those runtimes; backslash paths
  must be escaped in code and double-escaped in JSON/YAML.
- **In .bat files, use backslashes** — that's the native cmd
  syntax. `cd /d "%~dp0..\scripts"` works; forward slashes
  often don't.
- **Never hardcode `C:\Users\Ken\...`** — Ken's setup may move.
  Use `%USERPROFILE%` in bat, `Path.home()` in Python,
  `process.env.USERPROFILE` in Node. For paths inside the
  Codex clone, use `%~dp0` in bat (resolves to the bat's own
  directory) and `__dirname` / `import.meta.url` in JS.
- **Blocked paths — never touch regardless of mode**:
  - `C:/Windows` and anything under it
  - `C:/System32` / `C:/SysWOW64`
  - `C:/Program Files` / `C:/Program Files (x86)` (except read)
  - `~/.ssh`, `~/.aws`, `~/.gnupg`
  - any file ending in `.env`, `credentials.json`, `token.json`,
    `service-account*.json`
  - `C:/ProgramData/Microsoft/Crypto`
- **Case insensitivity gotcha**: Windows NTFS is case-insensitive
  by default but case-PRESERVING. Don't rely on case for
  uniqueness — `Readme.md` and `README.md` are the same file
  on NTFS but different on the Linux-backed Codex clones Ken's
  other agents use.

## Shell — which one to pick

Ken has three shells available. KenAI runs under whichever
spawned it, but when RECOMMENDING a command for Ken to run:

| task | best shell | why |
|---|---|---|
| Python / Node / git / curl | **Git Bash** | unix idioms work, ctrl+c behaves, jq is there |
| `.bat` / `.cmd` double-click | **cmd.exe** | that's what the shell shortcut uses |
| Services, registry, winget, scheduled tasks | **PowerShell** (as admin) | native Win32 access |
| SendInput, desktop automation | **pyautogui from Git Bash or cmd** | either works; admin NOT required unless the target window is elevated |

### Shell command differences (by shell)

| thing | cmd.exe | PowerShell | Git Bash |
|---|---|---|---|
| list files | `dir` | `ls` / `Get-ChildItem` | `ls` |
| pipe | `|` | `|` | `|` |
| env var | `%USERPROFILE%` | `$env:USERPROFILE` | `$USERPROFILE` (case-sensitive) |
| and | `&&` | `;` or `-and` in conditions | `&&` |
| null device | `nul` | `$null` | `/dev/null` |
| delay | `timeout /t 3 /nobreak` | `Start-Sleep -Seconds 3` | `sleep 3` |
| test file exists | `if exist file` | `Test-Path file` | `[ -f file ]` |
| stdout redirect | `> file` | `> file` | `> file` |

**Portable 2-second pause** (works in all three): `ping -n 3 127.0.0.1 > nul` in cmd, `ping -n 3 127.0.0.1 >$null` in PowerShell, `sleep 2` in bash. Prefer `ping -n` in bat files because `timeout /t` is missing when a bash coreutils shim hijacks the name.

### Process kill (Windows ONLY idioms)

- by name: `taskkill /IM python.exe /F`
- by pid: `taskkill /PID 12345 /F`
- list: `tasklist /FI "IMAGENAME eq python.exe"`
- NEVER use `kill` or `pkill` — those are Git Bash shims that
  call Windows taskkill under the hood but error on weird PIDs.

## Subprocess spawns (Python)

When spawning a subprocess on Windows:

- Default `shell=False` and pass `args` as a list. Only set
  `shell=True` if you genuinely need cmd.exe builtins.
- **Always pass `creationflags=subprocess.CREATE_NO_WINDOW`**
  for background tools that shouldn't pop a console window.
  0x08000000 — same as the Node.js `windowsHide: true` option.
- For detached long-running processes, also OR in
  `CREATE_NEW_PROCESS_GROUP` (0x00000200) so a Ctrl+C to the
  parent doesn't cascade.
- `encoding="utf-8"` on every `subprocess.run()` / `Popen()` —
  Windows defaults to cp1252 which can't decode box-drawing,
  emoji, or accented chars and raises UnicodeDecodeError.
- `timeout=<seconds>` always. No unbounded subprocess calls.

```python
# Correct Windows subprocess spawn
import subprocess
res = subprocess.run(
    ["python", "halo_hunt.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    timeout=60,
    creationflags=subprocess.CREATE_NO_WINDOW,  # no cmd pop
)
```

## Unicode + stdout

- Windows `cmd.exe` console is cp1252 by default. Printing
  `═` / `█` / em-dashes via `print()` raises
  `UnicodeEncodeError: 'charmap' codec can't encode`.
- Two fixes, pick one:
  1. **ASCII-only in user-facing `print()`** — `=` instead of
     `═`, `-` instead of `—`. This is what KenAI's START.bat
     banner does.
  2. `sys.stdout.reconfigure(encoding="utf-8")` at module
     start — works on Python 3.7+, but breaks when the
     script is invoked via a tool that captures stdout
     with its own encoding.
- Written to FILES (not stdout), unicode is fine — cp1252
  only applies to the console.

## File locking + open handles

Windows locks open files (Linux doesn't). Consequences:

- You cannot delete, rename, or overwrite a file that another
  process has open — get `WinError 32` / `PermissionError`.
- `git checkout` and `git pull` fail mysteriously when a
  running server has a log file open. Stop the server first.
- `pip install` can fail mid-stream on a .pyd if the module
  is loaded. Close Python first or use a fresh venv.
- `shutil.rmtree()` on a dir containing a running script's
  own location fails silently on the `__pycache__` dir.

When cleaning up, explicitly close handles first. When writing
a file an editor might have open, use `write_text(..., newline="")`
and accept that Git may complain about CRLF later.

## Line endings

- **Windows native = CRLF**. Git auto-converts on checkout
  when `core.autocrlf=true`. The warning
  `"LF will be replaced by CRLF the next time Git touches it"`
  is expected and harmless.
- Do NOT "fix" it by converting files to LF — the warning
  is about the WORKING COPY, not the commit. Commits are
  always normalized.
- Exception: shell scripts (`.sh`) and shebang-lined Python
  files that will run under WSL/Git Bash must keep LF or
  they fail with `/usr/bin/env: 'python3\r': No such file`.
  Ken's repo uses a `.gitattributes` rule for this.

## Permissions + admin elevation

- Regular user is enough for 95% of tasks. Admin is only
  needed for:
  - Memory scanning via `OpenProcess(PROCESS_VM_READ|WRITE)`
    (halo_hunt, halo_vision_hunt)
  - Writing to `C:/Program Files` or registry `HKLM`
  - Installing services, scheduled tasks, firewall rules
- Self-elevation pattern for .bat (UAC prompt):
  ```bat
  net session >nul 2>&1
  if %ERRORLEVEL% neq 0 (
    powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/k cd /d %~dp0 && python my_tool.py'"
    exit
  )
  ```
- **NEVER auto-elevate silently** — always make it a visible
  UAC prompt that Ken accepts or rejects.

## Paths with spaces

Ken has some paths with spaces (`Halo The Master Chief Collection`,
`Google Drive`, `Pipe-R Scripts`). Rules:

- Always quote in shell commands: `"C:/Users/Ken/Desktop/Pipe-R Scripts"`
- In `.bat`, use `"%var%"` (quoted variable expansion) — bare
  `%var%` breaks on spaces.
- In Python, `Path("C:/Users/Ken/Desktop/Pipe-R Scripts")` just
  works — Python doesn't care.

## Tasklist + netstat idioms

```bat
:: Find what's on port 7778
netstat -ano | findstr ":7778 " | findstr "LISTENING"

:: Kill whichever pid
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":7778 " ^| findstr "LISTENING"') do taskkill /PID %%P /F
```

```powershell
# Same in PowerShell
Get-NetTCPConnection -LocalPort 7778 | Where-Object State -eq Listen
Stop-Process -Id (Get-NetTCPConnection -LocalPort 7778 -State Listen).OwningProcess -Force
```

## The kill switch

`config/.kill_switch` file existence halts KenAI instantly.
On Windows, touching the file:

```bat
type nul > config\.kill_switch
```

Removing it:

```bat
del config\.kill_switch
```

Or via the UI — the "arm kill switch" button calls
`POST /api/kill_switch/arm` which does the same thing.

## When the agent is unsure on Windows

If a command might be Linux-flavored, check this file first.
If the command needs admin, stop and ask Ken before doing
anything. If a path looks Linux-like (`/home/`, `/var/`,
`/tmp/`), that's a red flag — this machine is Windows and
those don't exist except via WSL which Ken does not use.
