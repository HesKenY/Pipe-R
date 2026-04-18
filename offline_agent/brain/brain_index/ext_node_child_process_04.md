# Node.js child_process (4/7)
source: https://github.com/nodejs/node/blob/main/doc/api/child_process.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
-Windows
   systems.
3. `'ipc'`: Create an IPC channel for passing messages/file descriptors
   between parent and child. A [`ChildProcess`][] may have at most one IPC
   stdio file descriptor. Setting this option enables the
   [`subprocess.send()`][] method. If the child process is a Node.js instance,
   the presence of an IPC channel will enable [`process.send()`][] and
   [`process.disconnect()`][] methods, as well as [`'disconnect'`][] and
   [`'message'`][] events within the child process.

Accessing the IPC channel fd in any way other than [`process.send()`][]
   or using the IPC channel with a child process that is not a Node.js instance
   is not supported.
4. `'ignore'`: Instructs Node.js to ignore the fd in the child. While Node.js
   will always open fds 0, 1, and 2 for the processes it spawns, setting the fd
   to `'ignore'` will cause Node.js to open `/dev/null` and attach it to the
   child's fd.
5. `'inherit'`: Pass through the corresponding stdio stream to/from the
   parent process. In the first three positions, this is equivalent to
   `process.stdin`, `process.stdout`, and `process.stderr`, respectively. In
   any other position, equivalent to `'ignore'`.
6. {Stream} object: Share a readable or writable stream that refers to a tty,
   file, socket, or a pipe with the child process. The stream's underlying
   file descriptor is duplicated in the child process to the fd that
   corresponds to the index in the `stdio` array. The stream must have an
   underlying descriptor (file streams do not start until the `'open'` event has
   occurred).
   **NOTE:** While it is technically possible to pass `stdin` as a writable or
   `stdout`/`stderr` as readable, it is not recommended.
   Readable and writable streams are designed with distinct behaviors, and using
   them incorrectly (e.g., passing a readable stream where a writable stream is
   expected) can lead to unexpected results or errors. This practice is discouraged
   as it may result in undefined behavior or dropped callbacks if the stream
   encounters errors. Always ensure that `stdin` is used as readable and
   `stdout`/`stderr` as writable to maintain the intended flow of data between
   the parent and child processes.
7. Positive integer: The integer value is interpreted as a file descriptor
   that is open in the parent process. It is shared with the child
   process, similar to how {Stream} objects can be shared. Passing sockets
   is not supported on Windows.
8. `null`, `undefined`: Use default value. For stdio fds 0, 1, and 2 (in other
   words, stdin, stdout, and stderr) a pipe is created. For fd 3 and up, the
   default is `'ignore'`.

```cjs
const { spawn } = require('node:child_process');
const process = require('node:process');

// Child will use parent's stdios.
spawn('prg', [], { stdio: 'inherit' });

// Spawn child sharing only stderr.
spawn('prg', [], { stdio: ['pipe', 'pipe', process.stderr] });

// Open an extra fd=4, to interact with programs presenting a
// startd-style interface.
spawn('prg', [], { stdio: ['pipe', null, null, null, 'pipe'] });
```

```mjs
import { spawn } from 'node:child_process';
import process from 'node:process';

// Child will use parent's stdios.
spawn('prg', [], { stdio: 'inherit' });

// Spawn child sharing only stderr.
spawn('prg', [], { stdio: ['pipe', 'pipe', process.stderr] });

// Open an extra fd=4, to interact with programs presenting a
// startd-style interface.
spawn('prg', [], { stdio: ['pipe', null, null, null, 'pipe'] });
```

_It is worth noting that when an IPC channel is established between the
parent and child processes, and the child process is a Node.js instance,
the child process is launched with the IPC channel unreferenced (using
`unref()`) until the child process registers an event handler for the
[`'disconnect'`][] event or the [`'message'`][] event. This allows the
child process to exit normally without the process being held open by the
open IPC channel._
See also: [`child_process.exec()`][] and [`child_process.fork()`][].

## Synchronous process creation

The [`child_process.spawnSync()`][], [`child_process.execSync()`][], and
[`child_process.execFileSync()`][] methods are synchronous and will block the
Node.js event loop, pausing execution of any additional code until the spawned
process exits.

Blocking calls like these are mostly useful for simplifying general-purpose
scripting tasks and for simplifying the loading/processing of application
configuration at startup.

### `child_process.execFileSync(file[, args][, options])`

<!-- YAML
added: v0.11.12
changes:
  - version:
      - v16.4.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/38862
    description: The `cwd` option can be a WHATWG `URL` object using
                 `file:` protocol.
  - version: v10.10.0
    pr-url: https://github.com/nodejs/node/pull/22409
    description: The `input` option can now be any `TypedArray` or a
                 `DataView`.
  - version: v8.8.0
    pr-url: https://github.com/nodejs/node/pull/15380
    description: The `windowsHide` option is supported now.
  - version: v8.0.0
    pr-url: https://github.com/nodejs/node/pull/10653
    description: The `input` option can now be a `Uint8Array`.
  - version:
    - v6.2.1
    - v4.5.0
    pr-url: https://github.com/nodejs/node/pull/6939
    description: The `encoding` option can now explicitly be set to `buffer`.
-->

* `file` {string} The name or path of the executable file to run.
* `args` {string\[]} List of string arguments.
* `options` {Object}
  * `cwd` {string|URL} Current working directory of the child process.
  * `input` {string|Buffer|TypedArray|DataView} The value which will be passed
    as stdin to the spawned process. If `stdio[0]` is set to `'pipe'`, Supplying
    this value will override `stdio[0]`.
  * `stdio` {string|Array} Child's stdio configuration.
    See [`child_process.spawn()`][]'s [`stdio`][]. `stderr` by default will
    be output to the parent process' stderr unless `stdio` is specified.
    **Default:** `'pipe'`.
  * `env` {Object} Environment key-value pairs. **Default:** `process.env`.
  * `uid` {number} Sets the user identity of the process (see setuid(2)).
  * `gid` {number} Sets the group identity of the process (see setgid(2)).
  * `timeout` {number} In milliseconds the maximum amount of time the process
    is allowed to run. **Default:** `undefined`.
  * `killSignal` {string|integer} The signal value to be used when the spawned
    process will be killed. **Default:** `'SIGTERM'`.
  * `maxBuffer` {number} Largest amount of data in bytes allowed on stdout or
    stderr. If exceeded, the child process is terminated. See caveat at
    [`maxBuffer` and Unicode][]. **Default:** `1024 * 1024`.
  * `encoding` {string} The encoding used for all stdio inputs and outputs.
    **Default:** `'buffer'`.
  * `windowsHide` {boolean} Hide the subprocess console window that would
    normally be created on Windows systems. **Default:** `false`.
  * `shell` {boolean|string} If `true`, runs `command` inside of a shell. Uses
    `'/bin/sh'` on Unix, and `process.env.ComSpec` on Windows. A different
    shell can be specified as a string. See [Shell requirements][] and
    [Default Windows shell][]. **Default:** `false` (no shell).
* Returns: {Buffer|string} The stdout from the command.

The `child_process.execFileSync()` method is generally identical to
[`child_process.execFile()`][] with the exception that the method will not
return until the child process has fully closed. When a timeout has been
encountered and `killSignal` is sent, the method won't return until the process
has completely exited.

If the child process intercepts and handles the `SIGTERM` signal and
does not exit, the parent process will still wait until the child process has
exited.

If the process times out or has a non-zero exit code, this method will throw an
[`Error`][] that will include the full result of the underlying
[`child_process.spawnSync()`][].

**If the `shell` option is enabled, do not pass unsanitized user input to this
function. Any input containing shell metacharacters may be used to trigger
arbitrary command execution.**

```cjs
const { execFileSync } = require('node:child_process');

try {
  const stdout = execFileSync('my-script.sh', ['my-arg'], {
    // Capture stdout and stderr from child process. Overrides the
    // default behavior of streaming child stderr to the parent stderr
    stdio: 'pipe',

// Use utf8 encoding for stdio pipes
    encoding: 'utf8',
  });

console.log(stdout);
} catch (err) {
  if (err.code) {
    // Spawning child process failed
    console.error(err.code);
  } else {
    // Child was spawned but exited with non-zero exit code
    // Error contains any stdout and stderr from the child
    const { stdout, stderr } = err;

console.error({ stdout, stderr });
  }
}
```

```mjs
import { execFileSync } from 'node:child_process';

try {
  const stdout = execFileSync('my-script.sh', ['my-arg'], {
    // Capture stdout and stderr from child process. Overrides the
    // default behavior of streaming child stderr to the parent stderr
    stdio: 'pipe',

// Use utf8 encoding for stdio pipes
    encoding: 'utf8',
  });

console.log(stdout);
} catch (err) {
  if (err.code) {
    // Spawning child process failed
    console.error(err.code);
  } else {
    // Child was spawned but exited with non-zero exit code
    // Error contains any stdout and stderr from the child
    const { stdout, stderr } = err;

console.error({ stdout, stderr });
  }
}
```

### `child_process.execSync(command[, options])`

<!-- YAML
added: v0.11.12
changes:
  - version:
      - v16.4.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/38862
    description: The `cwd` option can be a WHATWG `URL` object using
                 `file:` protocol.
  - version: v10.10.0
    pr-url: https://github.com/nodejs/node/pull/22409
    description: The `input` option can now be any `TypedArray` or a
                 `DataView`.
  - version: v8.8.0
    pr-url: https://github.com/nodejs/node/pull/15380
    description: The `windowsHide` option is supported now.
  - version: v8.0.0
    pr-url: https://github.com/nodejs/node/pull/10653
    description: The `input` option can now be a `Uint8Array`.
-->

* `command` {string} The command to run.
* `options` {Object}
  * `cwd` {string|URL} Current working directory of the child process.
  * `input` {string|Buffer|TypedArray|DataView} The value which will be passed
    as stdin to the spawned process. If `stdio[0]` is set to `'pipe'`, Supplying
    this value will override `stdio[0]`.
  * `stdio` {string|Array} Child's stdio configuration.
    See [`child_process.spawn()`][]'s [`stdio`][]. `stderr` by default will
    be output to the parent process' stderr unless `stdio` is specified.
    **Default:** `'pipe'`.
  * `env` {Object} Environment key-value pairs. **Default:** `process.env`.
  * `shell` {string} Shell to execute the command with. See
    [Shell requirements][] and [Default Windows shell][]. **Default:**
    `'/bin/sh'` on Unix, `process.env.ComSpec` on Windows.
  * `uid` {number} Sets the user identity of the process. (See setuid(2)).
  * `gid` {number} Sets the group identity of the process. (See setgid(2)).
  * `timeout` {number} In milliseconds the maximum amount of time the process
    is allowed to run. **Default:** `undefined`.
  * `killSignal` {string|integer} The signal value to be used when the spawned
    process will be killed. **Default:** `'SIGTERM'`.
  * `maxBuffer` {number} Largest amount of data in bytes allowed on stdout or
    stderr. If exceeded, the child process is terminated and any output is
    truncated. See caveat at [`maxBuffer` and Unicode][].
    **Default:** `1024 * 1024`.
  * `encoding` {string} The encoding used for all stdio inputs and outputs.
    **Default:** `'buffer'`.
  * `windowsHide` {boolean} Hide the subprocess console window that would
    normally be created on Windows systems. **Default:** `false`.
* Returns: {Buffer|string} The stdout from the command.

The `child_process.execSync()` method is generally identical to
[`child_process.exec()`][] with the exception that the method will not return
until the child process has fully closed. When a timeout has been encountered
and `killSignal` is sent, the method won't return until the process has
completely exited. If the child process intercepts and handles the `SIGTERM`
signal and doesn't exit, the parent process will wait until the child process
has exited.

If the process times out or has a non-zero exit code, this method will throw.
The [`Error`][] object will contain the entire result from
[`child_process.spawnSync()`][].

**Never pass unsanitized user input to this function. Any input containing shell
metacharacters may be used to trigger arbitrary command execution.**

### `child_process.spawnSync(command[, args][, options])`

<!-- YAML
added: v0.11.12
changes:
  - version:
      - v16.4.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/38862
    description: The `cwd` option can be a WHATWG `URL` object using
                 `file:` protocol.
  - version: v10.10.0
    pr-url: https://github.com/nodejs/node/pull/22409
    description: The `input` option can now be any `TypedArray` or a
                 `DataView`.
  - version: v8.8.0
    pr-url: https://github.com/nodejs/node/pull/15380
    description: The `windowsHide` option is supported now.
  - version: v8.0.0
    pr-url: https://github.com/nodejs/node/pull/10653
    description: The `input` option can now be a `Uint8Array`.
  - version:
    - v6.2.1
    - v4.5.0
    pr-url: https://github.com/nodejs/node/pull/6939
    description: The `encoding` option can now explicitly be set to `buffer`.
  - version: v5.7.0
    pr-url: https://github.com/nodejs/node/pull/4598
    description: The `shell` option is supported now.
-->
