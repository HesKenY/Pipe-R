# Node.js child_process (5/7)
source: https://github.com/nodejs/node/blob/main/doc/api/child_process.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
80
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

* `command` {string} The command to run.
* `args` {string\[]} List of string arguments.
* `options` {Object}
  * `cwd` {string|URL} Current working directory of the child process.
  * `input` {string|Buffer|TypedArray|DataView} The value which will be passed
    as stdin to the spawned process. If `stdio[0]` is set to `'pipe'`, Supplying
    this value will override `stdio[0]`.
  * `argv0` {string} Explicitly set the value of `argv[0]` sent to the child
    process. This will be set to `command` if not specified.
  * `stdio` {string|Array} Child's stdio configuration.
    See [`child_process.spawn()`][]'s [`stdio`][]. **Default:** `'pipe'`.
  * `env` {Object} Environment key-value pairs. **Default:** `process.env`.
  * `uid` {number} Sets the user identity of the process (see setuid(2)).
  * `gid` {number} Sets the group identity of the process (see setgid(2)).
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
  * `shell` {boolean|string} If `true`, runs `command` inside of a shell. Uses
    `'/bin/sh'` on Unix, and `process.env.ComSpec` on Windows. A different
    shell can be specified as a string. See [Shell requirements][] and
    [Default Windows shell][]. **Default:** `false` (no shell).
  * `windowsVerbatimArguments` {boolean} No quoting or escaping of arguments is
    done on Windows. Ignored on Unix. This is set to `true` automatically
    when `shell` is specified and is CMD. **Default:** `false`.
  * `windowsHide` {boolean} Hide the subprocess console window that would
    normally be created on Windows systems. **Default:** `false`.
* Returns: {Object}
  * `pid` {number} Pid of the child process.
  * `output` {Array} Array of results from stdio output.
  * `stdout` {Buffer|string} The contents of `output[1]`.
  * `stderr` {Buffer|string} The contents of `output[2]`.
  * `status` {number|null} The exit code of the subprocess, or `null` if the
    subprocess terminated due to a signal.
  * `signal` {string|null} The signal used to kill the subprocess, or `null` if
    the subprocess did not terminate due to a signal.
  * `error` {Error} The error object if the child process failed or timed out.

The `child_process.spawnSync()` method is generally identical to
[`child_process.spawn()`][] with the exception that the function will not return
until the child process has fully closed. When a timeout has been encountered
and `killSignal` is sent, the method won't return until the process has
completely exited. If the process intercepts and handles the `SIGTERM` signal
and doesn't exit, the parent process will wait until the child process has
exited.

**If the `shell` option is enabled, do not pass unsanitized user input to this
function. Any input containing shell metacharacters may be used to trigger
arbitrary command execution.**

## Class: `ChildProcess`

<!-- YAML
added: v2.2.0
-->

* Extends: {EventEmitter}

Instances of the `ChildProcess` represent spawned child processes.

Instances of `ChildProcess` are not intended to be created directly. Rather,
use the [`child_process.spawn()`][], [`child_process.exec()`][],
[`child_process.execFile()`][], or [`child_process.fork()`][] methods to create
instances of `ChildProcess`.

### Event: `'close'`

<!-- YAML
added: v0.7.7
-->

* `code` {number} The exit code if the child process exited on its own, or
  `null` if the child process terminated due to a signal.
* `signal` {string} The signal by which the child process was terminated, or
  `null` if the child process did not terminated due to a signal.

The `'close'` event is emitted after a process has ended _and_ the stdio
streams of a child process have been closed. This is distinct from the
[`'exit'`][] event, since multiple processes might share the same stdio
streams. The `'close'` event will always emit after [`'exit'`][] was
already emitted, or [`'error'`][] if the child process failed to spawn.

If the process exited, `code` is the final exit code of the process, otherwise
`null`. If the process terminated due to receipt of a signal, `signal` is the
string name of the signal, otherwise `null`. One of the two will always be
non-`null`.

```cjs
const { spawn } = require('node:child_process');
const ls = spawn('ls', ['-lh', '/usr']);

ls.stdout.on('data', (data) => {
  console.log(`stdout: ${data}`);
});

ls.on('close', (code) => {
  console.log(`child process close all stdio with code ${code}`);
});

ls.on('exit', (code) => {
  console.log(`child process exited with code ${code}`);
});
```

```mjs
import { spawn } from 'node:child_process';
import { once } from 'node:events';
const ls = spawn('ls', ['-lh', '/usr']);

ls.stdout.on('data', (data) => {
  console.log(`stdout: ${data}`);
});

ls.on('close', (code) => {
  console.log(`child process close all stdio with code ${code}`);
});

ls.on('exit', (code) => {
  console.log(`child process exited with code ${code}`);
});

const [code] = await once(ls, 'close');
console.log(`child process close all stdio with code ${code}`);
```

### Event: `'disconnect'`

<!-- YAML
added: v0.7.2
-->

The `'disconnect'` event is emitted after calling the
[`subprocess.disconnect()`][] method in parent process or
[`process.disconnect()`][] in child process. After disconnecting it is no longer
possible to send or receive messages, and the [`subprocess.connected`][]
property is `false`.

### Event: `'error'`

* `err` {Error} The error.

The `'error'` event is emitted whenever:

* The process could not be spawned.
* The process could not be killed.
* Sending a message to the child process failed.
* The child process was aborted via the `signal` option.

The `'exit'` event may or may not fire after an error has occurred. When
listening to both the `'exit'` and `'error'` events, guard
against accidentally invoking handler functions multiple times.

See also [`subprocess.kill()`][] and [`subprocess.send()`][].

### Event: `'exit'`

<!-- YAML
added: v0.1.90
-->

* `code` {number} The exit code if the child process exited on its own, or
  `null` if the child process terminated due to a signal.
* `signal` {string} The signal by which the child process was terminated, or
  `null` if the child process did not terminated due to a signal.

The `'exit'` event is emitted after the child process ends. If the process
exited, `code` is the final exit code of the process, otherwise `null`. If the
process terminated due to receipt of a signal, `signal` is the string name of
the signal, otherwise `null`. One of the two will always be non-`null`.

When the `'exit'` event is triggered, child process stdio streams might still be
open.

Node.js establishes signal handlers for `SIGINT` and `SIGTERM` and Node.js
processes will not terminate immediately due to receipt of those signals.
Rather, Node.js will perform a sequence of cleanup actions and then will
re-raise the handled signal.

See waitpid(2).

When `code` is `null` due to signal termination, you can use
[`util.convertProcessSignalToExitCode()`][] to convert the signal to a POSIX
exit code.

### Event: `'message'`

<!-- YAML
added: v0.5.9
-->

* `message` {Object} A parsed JSON object or primitive value.
* `sendHandle` {Handle|undefined} `undefined` or a [`net.Socket`][],
  [`net.Server`][], or [`dgram.Socket`][] object.

The `'message'` event is triggered when a child process uses
[`process.send()`][] to send messages.

The message goes through serialization and parsing. The resulting
message might not be the same as what is originally sent.

If the `serialization` option was set to `'advanced'` used when spawning the
child process, the `message` argument can contain data that JSON is not able
to represent.
See [Advanced serialization][] for more details.

### Event: `'spawn'`

<!-- YAML
added:
  - v15.1.0
  - v14.17.0
-->

The `'spawn'` event is emitted once the child process has spawned successfully.
If the child process does not spawn successfully, the `'spawn'` event is not
emitted and the `'error'` event is emitted instead.

If emitted, the `'spawn'` event comes before all other events and before any
data is received via `stdout` or `stderr`.

The `'spawn'` event will fire regardless of whether an error occurs **within**
the spawned process. For example, if `bash some-command` spawns successfully,
the `'spawn'` event will fire, though `bash` may fail to spawn `some-command`.
This caveat also applies when using `{ shell: true }`.

### `subprocess.channel`

<!-- YAML
added: v7.1.0
changes:
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/30165
    description: The object no longer accidentally exposes native C++ bindings.
-->

* Type: {Object} A pipe representing the IPC channel to the child process.

The `subprocess.channel` property is a reference to the child's IPC channel. If
no IPC channel exists, this property is `undefined`.

#### `subprocess.channel.ref()`

<!-- YAML
added: v7.1.0
-->

This method makes the IPC channel keep the event loop of the parent process
running if `.unref()` has been called before.

#### `subprocess.channel.unref()`

<!-- YAML
added: v7.1.0
-->

This method makes the IPC channel not keep the event loop of the parent process
running, and lets it finish even while the channel is open.

### `subprocess.connected`

<!-- YAML
added: v0.7.2
-->

* Type: {boolean} Set to `false` after `subprocess.disconnect()` is called.

The `subprocess.connected` property indicates whether it is still possible to
send and receive messages from a child process. When `subprocess.connected` is
`false`, it is no longer possible to send or receive messages.

### `subprocess.disconnect()`

<!-- YAML
added: v0.7.2
-->

Closes the IPC channel between parent and child processes, allowing the child
process to exit gracefully once there are no other connections keeping it alive.
After calling this method the `subprocess.connected` and
`process.connected` properties in both the parent and child processes
(respectively) will be set to `false`, and it will be no longer possible
to pass messages between the processes.

The `'disconnect'` event will be emitted when there are no messages in the
process of being received. This will most often be triggered immediately after
calling `subprocess.disconnect()`.

When the child process is a Node.js instance (e.g. spawned using
[`child_process.fork()`][]), the `process.disconnect()` method can be invoked
within the child process to close the IPC channel as well.

### `subprocess.exitCode`

* Type: {integer}

The `subprocess.exitCode` property indicates the exit code of the child process.
If the child process is still running, the field will be `null`.

When the child process is terminated by a signal, `subprocess.exitCode` will be
`null` and [`subprocess.signalCode`][] will be set. To get the corresponding
POSIX exit code, use
[`util.convertProcessSignalToExitCode(subprocess.signalCode)`][`util.convertProcessSignalToExitCode()`].

### `subprocess.kill([signal])`

<!-- YAML
added: v0.1.90
-->

* `signal` {number|string}
* Returns: {boolean}

The `subprocess.kill()` method sends a signal to the child process. If no
argument is given, the process will be sent the `'SIGTERM'` signal. See
signal(7) for a list of available signals. This function returns `true` if
kill(2) succeeds, and `false` otherwise.

```cjs
const { spawn } = require('node:child_process');
const grep = spawn('grep', ['ssh']);

grep.on('close', (code, signal) => {
  console.log(
    `child process terminated due to receipt of signal ${signal}`);
});

// Send SIGHUP to process.
grep.kill('SIGHUP');
```

```mjs
import { spawn } from 'node:child_process';
const grep = spawn('grep', ['ssh']);

grep.on('close', (code, signal) => {
  console.log(
    `child process terminated due to receipt of signal ${signal}`);
});

// Send SIGHUP to process.
grep.kill('SIGHUP');
```

The [`ChildProcess`][] object may emit an [`'error'`][] event if the signal
cannot be delivered. Sending a signal to a child process that has already exited
is not an error but may have unforeseen consequences. Specifically, if the
process identifier (PID) has been reassigned to another process, the signal will
be delivered to that process instead which can have unexpected results.

While the function is called `kill`, the signal delivered to the child process
may not actually terminate the process.

See kill(2) for reference.

On Windows, where POSIX signals do not exist, the `signal` argument will be
ignored except for `'SIGKILL'`, `'SIGTERM'`, `'SIGINT'` and `'SIGQUIT'`, and the
process will always be killed forcefully and abruptly (similar to `'SIGKILL'`).
See [Signal Events][] for more details.

On Linux, child processes of child processes will not be terminated
when attempting to kill their parent. This is likely to happen when running a
new process in a shell or with the use of the `shell` option of `ChildProcess`:

```cjs
const { spawn } = require('node:child_process');
