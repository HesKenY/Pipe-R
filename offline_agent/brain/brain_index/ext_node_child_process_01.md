# Node.js child_process (1/7)
source: https://github.com/nodejs/node/blob/main/doc/api/child_process.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
# Child process

<!--introduced_in=v0.10.0-->

> Stability: 2 - Stable

<!-- source_link=lib/child_process.js -->

The `node:child_process` module provides the ability to spawn subprocesses in
a manner that is similar, but not identical, to popen(3). This capability
is primarily provided by the [`child_process.spawn()`][] function:

```cjs
const { spawn } = require('node:child_process');
const ls = spawn('ls', ['-lh', '/usr']);

ls.stdout.on('data', (data) => {
  console.log(`stdout: ${data}`);
});

ls.stderr.on('data', (data) => {
  console.error(`stderr: ${data}`);
});

ls.on('close', (code) => {
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

ls.stderr.on('data', (data) => {
  console.error(`stderr: ${data}`);
});

const [code] = await once(ls, 'close');
console.log(`child process exited with code ${code}`);
```

By default, pipes for `stdin`, `stdout`, and `stderr` are established between
the parent Node.js process and the spawned subprocess. These pipes have
limited (and platform-specific) capacity. If the subprocess writes to
stdout in excess of that limit without the output being captured, the
subprocess blocks, waiting for the pipe buffer to accept more data. This is
identical to the behavior of pipes in the shell. Use the `{ stdio: 'ignore' }`
option if the output will not be consumed.

The command lookup is performed using the `options.env.PATH` environment
variable if `env` is in the `options` object. Otherwise, `process.env.PATH` is
used. If `options.env` is set without `PATH`, lookup on Unix is performed
on a default search path search of `/usr/bin:/bin` (see your operating system's
manual for execvpe/execvp), on Windows the current processes environment
variable `PATH` is used.

On Windows, environment variables are case-insensitive. Node.js
lexicographically sorts the `env` keys and uses the first one that
case-insensitively matches. Only first (in lexicographic order) entry will be
passed to the subprocess. This might lead to issues on Windows when passing
objects to the `env` option that have multiple variants of the same key, such as
`PATH` and `Path`.

The [`child_process.spawn()`][] method spawns the child process asynchronously,
without blocking the Node.js event loop. The [`child_process.spawnSync()`][]
function provides equivalent functionality in a synchronous manner that blocks
the event loop until the spawned process either exits or is terminated.

For convenience, the `node:child_process` module provides a handful of
synchronous and asynchronous alternatives to [`child_process.spawn()`][] and
[`child_process.spawnSync()`][]. Each of these alternatives are implemented on
top of [`child_process.spawn()`][] or [`child_process.spawnSync()`][].

* [`child_process.exec()`][]: spawns a shell and runs a command within that
  shell, passing the `stdout` and `stderr` to a callback function when
  complete.
* [`child_process.execFile()`][]: similar to [`child_process.exec()`][] except
  that it spawns the command directly without first spawning a shell by
  default.
* [`child_process.fork()`][]: spawns a new Node.js process and invokes a
  specified module with an IPC communication channel established that allows
  sending messages between parent and child.
* [`child_process.execSync()`][]: a synchronous version of
  [`child_process.exec()`][] that will block the Node.js event loop.
* [`child_process.execFileSync()`][]: a synchronous version of
  [`child_process.execFile()`][] that will block the Node.js event loop.

For certain use cases, such as automating shell scripts, the
[synchronous counterparts][] may be more convenient. In many cases, however,
the synchronous methods can have significant impact on performance due to
stalling the event loop while spawned processes complete.

## Asynchronous process creation

The [`child_process.spawn()`][], [`child_process.fork()`][], [`child_process.exec()`][],
and [`child_process.execFile()`][] methods all follow the idiomatic asynchronous
programming pattern typical of other Node.js APIs.

Each of the methods returns a [`ChildProcess`][] instance. These objects
implement the Node.js [`EventEmitter`][] API, allowing the parent process to
register listener functions that are called when certain events occur during
the life cycle of the child process.

The [`child_process.exec()`][] and [`child_process.execFile()`][] methods
additionally allow for an optional `callback` function to be specified that is
invoked when the child process terminates.

### Spawning `.bat` and `.cmd` files on Windows

The importance of the distinction between [`child_process.exec()`][] and
[`child_process.execFile()`][] can vary based on platform. On Unix-type
operating systems (Unix, Linux, macOS) [`child_process.execFile()`][] can be
more efficient because it does not spawn a shell by default. On Windows,
however, `.bat` and `.cmd` files are not executable on their own without a
terminal, and therefore cannot be launched using [`child_process.execFile()`][].
When running on Windows, `.bat` and `.cmd` files can be invoked by:

* using [`child_process.spawn()`][] with the `shell` option set (not recommended, see [DEP0190][]), or
* using [`child_process.exec()`][], or
* spawning `cmd.exe` and passing the `.bat` or `.cmd` file as an argument
  (which is what [`child_process.exec()`][] does internally).

In any case, if the script filename contains spaces, it needs to be quoted.

```cjs
const { exec, spawn } = require('node:child_process');

exec('my.bat', (err, stdout, stderr) => { /* ... */ });

// Or, spawning cmd.exe directly:
const bat = spawn('cmd.exe', ['/c', 'my.bat']);

// If the script filename contains spaces, it needs to be quoted
exec('"my script.cmd" a b', (err, stdout, stderr) => { /* ... */ });
```

```mjs
import { exec, spawn } from 'node:child_process';

exec('my.bat', (err, stdout, stderr) => { /* ... */ });

// Or, spawning cmd.exe directly:
const bat = spawn('cmd.exe', ['/c', 'my.bat']);

// If the script filename contains spaces, it needs to be quoted
exec('"my script.cmd" a b', (err, stdout, stderr) => { /* ... */ });
```

### `child_process.exec(command[, options][, callback])`

<!-- YAML
added: v0.1.90
changes:
  - version:
      - v16.4.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/38862
    description: The `cwd` option can be a WHATWG `URL` object using
                 `file:` protocol.
  - version: v15.4.0
    pr-url: https://github.com/nodejs/node/pull/36308
    description: AbortSignal support was added.
  - version: v8.8.0
    pr-url: https://github.com/nodejs/node/pull/15380
    description: The `windowsHide` option is supported now.
-->

* `command` {string} The command to run, with space-separated arguments.
* `options` {Object}
  * `cwd` {string|URL} Current working directory of the child process.
    **Default:** `process.cwd()`.
  * `env` {Object} Environment key-value pairs. **Default:** `process.env`.
  * `encoding` {string} **Default:** `'utf8'`
  * `shell` {string} Shell to execute the command with. See
    [Shell requirements][] and [Default Windows shell][]. **Default:**
    `'/bin/sh'` on Unix, `process.env.ComSpec` on Windows.
  * `signal` {AbortSignal} allows aborting the child process using an
    AbortSignal.
  * `timeout` {number} **Default:** `0`
  * `maxBuffer` {number} Largest amount of data in bytes allowed on stdout or
    stderr. If exceeded, the child process is terminated and any output is
    truncated. See caveat at [`maxBuffer` and Unicode][].
    **Default:** `1024 * 1024`.
  * `killSignal` {string|integer} **Default:** `'SIGTERM'`
  * `uid` {number} Sets the user identity of the process (see setuid(2)).
  * `gid` {number} Sets the group identity of the process (see setgid(2)).
  * `windowsHide` {boolean} Hide the subprocess console window that would
    normally be created on Windows systems. **Default:** `false`.
* `callback` {Function} called with the output when process terminates.
  * `error` {Error}
  * `stdout` {string|Buffer}
  * `stderr` {string|Buffer}
* Returns: {ChildProcess}

Spawns a shell then executes the `command` within that shell, buffering any
generated output. The `command` string passed to the exec function is processed
directly by the shell and special characters (vary based on
[shell](https://en.wikipedia.org/wiki/List_of_command-line_interpreters))
need to be dealt with accordingly:

```cjs
const { exec } = require('node:child_process');

exec('"/path/to/test file/test.sh" arg1 arg2');
// Double quotes are used so that the space in the path is not interpreted as
// a delimiter of multiple arguments.

exec('echo "The \\$HOME variable is $HOME"');
// The $HOME variable is escaped in the first instance, but not in the second.
```

```mjs
import { exec } from 'node:child_process';

exec('"/path/to/test file/test.sh" arg1 arg2');
// Double quotes are used so that the space in the path is not interpreted as
// a delimiter of multiple arguments.

exec('echo "The \\$HOME variable is $HOME"');
// The $HOME variable is escaped in the first instance, but not in the second.
```

**Never pass unsanitized user input to this function. Any input containing shell
metacharacters may be used to trigger arbitrary command execution.**

If a `callback` function is provided, it is called with the arguments
`(error, stdout, stderr)`. On success, `error` will be `null`. On error,
`error` will be an instance of [`Error`][]. The `error.code` property will be
the exit code of the process. By convention, any exit code other than `0`
indicates an error. `error.signal` will be the signal that terminated the
process.

The `stdout` and `stderr` arguments passed to the callback will contain the
stdout and stderr output of the child process. By default, Node.js will decode
the output as UTF-8 and pass strings to the callback. The `encoding` option
can be used to specify the character encoding used to decode the stdout and
stderr output. If `encoding` is `'buffer'`, or an unrecognized character
encoding, `Buffer` objects will be passed to the callback instead.

```cjs
const { exec } = require('node:child_process');
exec('cat *.js missing_file | wc -l', (error, stdout, stderr) => {
  if (error) {
    console.error(`exec error: ${error}`);
    return;
  }
  console.log(`stdout: ${stdout}`);
  console.error(`stderr: ${stderr}`);
});
```

```mjs
import { exec } from 'node:child_process';
exec('cat *.js missing_file | wc -l', (error, stdout, stderr) => {
  if (error) {
    console.error(`exec error: ${error}`);
    return;
  }
  console.log(`stdout: ${stdout}`);
  console.error(`stderr: ${stderr}`);
});
```

If `timeout` is greater than `0`, the parent process will send the signal
identified by the `killSignal` property (the default is `'SIGTERM'`) if the
child process runs longer than `timeout` milliseconds.

Unlike the exec(3) POSIX system call, `child_process.exec()` does not replace
the existing process and uses a shell to execute the command.

If this method is invoked as its [`util.promisify()`][]ed version, it returns
a `Promise` for an `Object` with `stdout` and `stderr` properties. The returned
`ChildProcess` instance is attached to the `Promise` as a `child` property. In
case of an error (including any error resulting in an exit code other than 0), a
rejected promise is returned, with the same `error` object given in the
callback, but with two additional properties `stdout` and `stderr`.

```cjs
const util = require('node:util');
const exec = util.promisify(require('node:child_process').exec);

async function lsExample() {
  const { stdout, stderr } = await exec('ls');
  console.log('stdout:', stdout);
  console.error('stderr:', stderr);
}
lsExample();
```

```mjs
import { promisify } from 'node:util';
import child_process from 'node:child_process';
const exec = promisify(child_process.exec);

async function lsExample() {
  const { stdout, stderr } = await exec('ls');
  console.log('stdout:', stdout);
  console.error('stderr:', stderr);
}
lsExample();
```

If the `signal` option is enabled, calling `.abort()` on the corresponding
`AbortController` is similar to calling `.kill()` on the child process except
the error passed to the callback will be an `AbortError`:

```cjs
const { exec } = require('node:child_process');
const controller = new AbortController();
const { signal } = controller;
const child = exec('grep ssh', { signal }, (error) => {
  console.error(error); // an AbortError
});
controller.abort();
```

```mjs
import { exec } from 'node:child_process';
const controller = new AbortController();
const { signal } = controller;
const child = exec('grep ssh', { signal }, (error) => {
  console.error(error); // an AbortError
});
controller.abort();
```

### `child_process.execFile(file[, args][, options][, callback])`

<!-- YAML
added: v0.1.91
changes:
  - version:
      - v23.11.0
      - v22.15.0
    pr-url: https://github.com/nodejs/node/pull/57389
    description: Passing `args` when `shell` is set to `true` is deprecated.
  - version:
      - v16.4.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/38862
    description: The `cwd` option can be a WHATWG `URL` object using
                 `file:` protocol.
  - version:
      - v15.4.0
      - v14.17.0
    pr-url: https://github.com/nodejs/node/pull/36308
    description: AbortSignal support was added.
  - version: v8.8.0
    pr-url: https://github.com/nodejs/node/pull/15380
    description: The `windowsHide` option is supported now.
-->
