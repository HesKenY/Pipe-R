# Node.js child_process (2/7)
source: https://github.com/nodejs/node/blob/main/doc/api/child_process.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
eprecated.
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

* `file` {string} The name or path of the executable file to run.
* `args` {string\[]} List of string arguments.
* `options` {Object}
  * `cwd` {string|URL} Current working directory of the child process.
  * `env` {Object} Environment key-value pairs. **Default:** `process.env`.
  * `encoding` {string} **Default:** `'utf8'`
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
  * `windowsVerbatimArguments` {boolean} No quoting or escaping of arguments is
    done on Windows. Ignored on Unix. **Default:** `false`.
  * `shell` {boolean|string} If `true`, runs `command` inside of a shell. Uses
    `'/bin/sh'` on Unix, and `process.env.ComSpec` on Windows. A different
    shell can be specified as a string. See [Shell requirements][] and
    [Default Windows shell][]. **Default:** `false` (no shell).
  * `signal` {AbortSignal} allows aborting the child process using an
    AbortSignal.
* `callback` {Function} Called with the output when process terminates.
  * `error` {Error}
  * `stdout` {string|Buffer}
  * `stderr` {string|Buffer}
* Returns: {ChildProcess}

The `child_process.execFile()` function is similar to [`child_process.exec()`][]
except that it does not spawn a shell by default. Rather, the specified
executable `file` is spawned directly as a new process making it slightly more
efficient than [`child_process.exec()`][].

The same options as [`child_process.exec()`][] are supported. Since a shell is
not spawned, behaviors such as I/O redirection and file globbing are not
supported.

```cjs
const { execFile } = require('node:child_process');
const child = execFile('node', ['--version'], (error, stdout, stderr) => {
  if (error) {
    throw error;
  }
  console.log(stdout);
});
```

```mjs
import { execFile } from 'node:child_process';
const child = execFile('node', ['--version'], (error, stdout, stderr) => {
  if (error) {
    throw error;
  }
  console.log(stdout);
});
```

The `stdout` and `stderr` arguments passed to the callback will contain the
stdout and stderr output of the child process. By default, Node.js will decode
the output as UTF-8 and pass strings to the callback. The `encoding` option
can be used to specify the character encoding used to decode the stdout and
stderr output. If `encoding` is `'buffer'`, or an unrecognized character
encoding, `Buffer` objects will be passed to the callback instead.

If this method is invoked as its [`util.promisify()`][]ed version, it returns
a `Promise` for an `Object` with `stdout` and `stderr` properties. The returned
`ChildProcess` instance is attached to the `Promise` as a `child` property. In
case of an error (including any error resulting in an exit code other than 0), a
rejected promise is returned, with the same `error` object given in the
callback, but with two additional properties `stdout` and `stderr`.

```cjs
const util = require('node:util');
const execFile = util.promisify(require('node:child_process').execFile);
async function getVersion() {
  const { stdout } = await execFile('node', ['--version']);
  console.log(stdout);
}
getVersion();
```

```mjs
import { promisify } from 'node:util';
import child_process from 'node:child_process';
const execFile = promisify(child_process.execFile);
async function getVersion() {
  const { stdout } = await execFile('node', ['--version']);
  console.log(stdout);
}
getVersion();
```

**If the `shell` option is enabled, do not pass unsanitized user input to this
function. Any input containing shell metacharacters may be used to trigger
arbitrary command execution.**

If the `signal` option is enabled, calling `.abort()` on the corresponding
`AbortController` is similar to calling `.kill()` on the child process except
the error passed to the callback will be an `AbortError`:

```cjs
const { execFile } = require('node:child_process');
const controller = new AbortController();
const { signal } = controller;
const child = execFile('node', ['--version'], { signal }, (error) => {
  console.error(error); // an AbortError
});
controller.abort();
```

```mjs
import { execFile } from 'node:child_process';
const controller = new AbortController();
const { signal } = controller;
const child = execFile('node', ['--version'], { signal }, (error) => {
  console.error(error); // an AbortError
});
controller.abort();
```

### `child_process.fork(modulePath[, args][, options])`

<!-- YAML
added: v0.5.0
changes:
  - version:
      - v17.4.0
      - v16.14.0
    pr-url: https://github.com/nodejs/node/pull/41225
    description: The `modulePath` parameter can be a WHATWG `URL` object using
                 `file:` protocol.
  - version:
      - v16.4.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/38862
    description: The `cwd` option can be a WHATWG `URL` object using
                 `file:` protocol.
  - version:
      - v15.13.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/37256
    description: timeout was added.
  - version:
      - v15.11.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/37325
    description: killSignal for AbortSignal was added.
  - version:
      - v15.6.0
      - v14.17.0
    pr-url: https://github.com/nodejs/node/pull/36603
    description: AbortSignal support was added.
  - version:
      - v13.2.0
      - v12.16.0
    pr-url: https://github.com/nodejs/node/pull/30162
    description: The `serialization` option is supported now.
  - version: v8.0.0
    pr-url: https://github.com/nodejs/node/pull/10866
    description: The `stdio` option can now be a string.
  - version: v6.4.0
    pr-url: https://github.com/nodejs/node/pull/7811
    description: The `stdio` option is supported now.
-->

* `modulePath` {string|URL} The module to run in the child.
* `args` {string\[]} List of string arguments.
* `options` {Object}
  * `cwd` {string|URL} Current working directory of the child process.
  * `detached` {boolean} Prepare child process to run independently of its
    parent process. Specific behavior depends on the platform (see
    [`options.detached`][]).
  * `env` {Object} Environment key-value pairs. **Default:** `process.env`.
  * `execPath` {string} Executable used to create the child process.
  * `execArgv` {string\[]} List of string arguments passed to the executable.
    **Default:** `process.execArgv`.
  * `gid` {number} Sets the group identity of the process (see setgid(2)).
  * `serialization` {string} Specify the kind of serialization used for sending
    messages between processes. Possible values are `'json'` and `'advanced'`.
    See [Advanced serialization][] for more details. **Default:** `'json'`.
  * `signal` {AbortSignal} Allows closing the child process using an
    AbortSignal.
  * `killSignal` {string|integer} The signal value to be used when the spawned
    process will be killed by timeout or abort signal. **Default:** `'SIGTERM'`.
  * `silent` {boolean} If `true`, stdin, stdout, and stderr of the child
    process will be piped to the parent process, otherwise they will be inherited
    from the parent process, see the `'pipe'` and `'inherit'` options for
    [`child_process.spawn()`][]'s [`stdio`][] for more details.
    **Default:** `false`.
  * `stdio` {Array|string} See [`child_process.spawn()`][]'s [`stdio`][].
    When this option is provided, it overrides `silent`. If the array variant
    is used, it must contain exactly one item with value `'ipc'` or an error
    will be thrown. For instance `[0, 1, 2, 'ipc']`.
  * `uid` {number} Sets the user identity of the process (see setuid(2)).
  * `windowsVerbatimArguments` {boolean} No quoting or escaping of arguments is
    done on Windows. Ignored on Unix. **Default:** `false`.
  * `timeout` {number} In milliseconds the maximum amount of time the process
    is allowed to run. **Default:** `undefined`.
* Returns: {ChildProcess}

The `child_process.fork()` method is a special case of
[`child_process.spawn()`][] used specifically to spawn new Node.js processes.
Like [`child_process.spawn()`][], a [`ChildProcess`][] object is returned. The
returned [`ChildProcess`][] will have an additional communication channel
built-in that allows messages to be passed back and forth between the parent and
child. See [`subprocess.send()`][] for details.

Keep in mind that spawned Node.js child processes are
independent of the parent with exception of the IPC communication channel
that is established between the two. Each process has its own memory, with
their own V8 instances. Because of the additional resource allocations
required, spawning a large number of child Node.js processes is not
recommended.

By default, `child_process.fork()` will spawn new Node.js instances using the
[`process.execPath`][] of the parent process. The `execPath` property in the
`options` object allows for an alternative execution path to be used.

Node.js processes launched with a custom `execPath` will communicate with the
parent process using the file descriptor (fd) identified using the
environment variable `NODE_CHANNEL_FD` on the child process.

Unlike the fork(2) POSIX system call, `child_process.fork()` does not clone the
current process.

The `shell` option available in [`child_process.spawn()`][] is not supported by
`child_process.fork()` and will be ignored if set.

If the `signal` option is enabled, calling `.abort()` on the corresponding
`AbortController` is similar to calling `.kill()` on the child process except
the error passed to the callback will be an `AbortError`:

```cjs
const { fork } = require('node:child_process');
const process = require('node:process');

if (process.argv[2] === 'child') {
  setTimeout(() => {
    console.log(`Hello from ${process.argv[2]}!`);
  }, 1_000);
} else {
  const controller = new AbortController();
  const { signal } = controller;
  const child = fork(__filename, ['child'], { signal });
  child.on('error', (err) => {
    // This will be called with err being an AbortError if the controller aborts
  });
  controller.abort(); // Stops the child process
}
```

```mjs
import { fork } from 'node:child_process';
import process from 'node:process';

if (process.argv[2] === 'child') {
  setTimeout(() => {
    console.log(`Hello from ${process.argv[2]}!`);
  }, 1_000);
} else {
  const controller = new AbortController();
  const { signal } = controller;
  const child = fork(import.meta.url, ['child'], { signal });
  child.on('error', (err) => {
    // This will be called with err being an AbortError if the controller aborts
  });
  controller.abort(); // Stops the child process
}
```

### `child_process.spawn(command[, args][, options])`

<!-- YAML
added: v0.1.90
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
      - v15.13.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/37256
    description: timeout was added.
  - version:
      - v15.11.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/37325
    description: killSignal for AbortSignal was added.
  - version:
      - v15.5.0
      - v14.17.0
    pr-url: https://github.com/nodejs/node/pull/36432
    description: AbortSignal support was added.
  - version:
      - v13.2.0
      - v12.16.0
    pr-url: https://github.com/nodejs/node/pull/30162
    description: The `serialization` option is supported now.
  - version: v8.8.0
    pr-url: https://github.com/nodejs/node/pull/15380
    description: The `windowsHide` option is supported now.
  - version: v6.4.0
    pr-url: https://github.com/nodejs/node/pull/7696
    description: The `argv0` option is supported now.
  - version: v5.7.0
    pr-url: https://github.com/nodejs/node/pull/4598
    description: The `shell` option is supported now.
-->
