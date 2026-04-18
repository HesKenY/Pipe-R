# Node.js child_process (7/7)
source: https://github.com/nodejs/node/blob/main/doc/api/child_process.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
its input, the child process will not continue
until this stream has been closed via `end()`.

If the child process was spawned with `stdio[0]` set to anything other than `'pipe'`,
then this will be `null`.

`subprocess.stdin` is an alias for `subprocess.stdio[0]`. Both properties will
refer to the same value.

The `subprocess.stdin` property can be `null` or `undefined`
if the child process could not be successfully spawned.

### `subprocess.stdio`

<!-- YAML
added: v0.7.10
-->

* Type: {Array}

A sparse array of pipes to the child process, corresponding with positions in
the [`stdio`][] option passed to [`child_process.spawn()`][] that have been set
to the value `'pipe'`. `subprocess.stdio[0]`, `subprocess.stdio[1]`, and
`subprocess.stdio[2]` are also available as `subprocess.stdin`,
`subprocess.stdout`, and `subprocess.stderr`, respectively.

In the following example, only the child's fd `1` (stdout) is configured as a
pipe, so only the parent's `subprocess.stdio[1]` is a stream, all other values
in the array are `null`.

```cjs
const assert = require('node:assert');
const fs = require('node:fs');
const child_process = require('node:child_process');

const subprocess = child_process.spawn('ls', {
  stdio: [
    0, // Use parent's stdin for child.
    'pipe', // Pipe child's stdout to parent.
    fs.openSync('err.out', 'w'), // Direct child's stderr to a file.
  ],
});

assert.strictEqual(subprocess.stdio[0], null);
assert.strictEqual(subprocess.stdio[0], subprocess.stdin);

assert(subprocess.stdout);
assert.strictEqual(subprocess.stdio[1], subprocess.stdout);

assert.strictEqual(subprocess.stdio[2], null);
assert.strictEqual(subprocess.stdio[2], subprocess.stderr);
```

```mjs
import assert from 'node:assert';
import fs from 'node:fs';
import child_process from 'node:child_process';

const subprocess = child_process.spawn('ls', {
  stdio: [
    0, // Use parent's stdin for child.
    'pipe', // Pipe child's stdout to parent.
    fs.openSync('err.out', 'w'), // Direct child's stderr to a file.
  ],
});

assert.strictEqual(subprocess.stdio[0], null);
assert.strictEqual(subprocess.stdio[0], subprocess.stdin);

assert(subprocess.stdout);
assert.strictEqual(subprocess.stdio[1], subprocess.stdout);

assert.strictEqual(subprocess.stdio[2], null);
assert.strictEqual(subprocess.stdio[2], subprocess.stderr);
```

The `subprocess.stdio` property can be `undefined` if the child process could
not be successfully spawned.

### `subprocess.stdout`

<!-- YAML
added: v0.1.90
-->

* Type: {stream.Readable|null|undefined}

A `Readable Stream` that represents the child process's `stdout`.

If the child process was spawned with `stdio[1]` set to anything other than `'pipe'`,
then this will be `null`.

`subprocess.stdout` is an alias for `subprocess.stdio[1]`. Both properties will
refer to the same value.

```cjs
const { spawn } = require('node:child_process');

const subprocess = spawn('ls');

subprocess.stdout.on('data', (data) => {
  console.log(`Received chunk ${data}`);
});
```

```mjs
import { spawn } from 'node:child_process';

const subprocess = spawn('ls');

subprocess.stdout.on('data', (data) => {
  console.log(`Received chunk ${data}`);
});
```

The `subprocess.stdout` property can be `null` or `undefined`
if the child process could not be successfully spawned.

### `subprocess.unref()`

<!-- YAML
added: v0.7.10
-->

By default, the parent process will wait for the detached child process to exit.
To prevent the parent process from waiting for a given `subprocess` to exit, use the
`subprocess.unref()` method. Doing so will cause the parent's event loop to not
include the child process in its reference count, allowing the parent to exit
independently of the child, unless there is an established IPC channel between
the child and the parent processes.

```cjs
const { spawn } = require('node:child_process');
const process = require('node:process');

const subprocess = spawn(process.argv[0], ['child_program.js'], {
  detached: true,
  stdio: 'ignore',
});

subprocess.unref();
```

```mjs
import { spawn } from 'node:child_process';
import process from 'node:process';

const subprocess = spawn(process.argv[0], ['child_program.js'], {
  detached: true,
  stdio: 'ignore',
});

subprocess.unref();
```

## `maxBuffer` and Unicode

The `maxBuffer` option specifies the largest number of bytes allowed on `stdout`
or `stderr`. If this value is exceeded, then the child process is terminated.
This impacts output that includes multibyte character encodings such as UTF-8 or
UTF-16. For instance, `console.log('中文测试')` will send 13 UTF-8 encoded bytes
to `stdout` although there are only 4 characters.

## Shell requirements

The shell should understand the `-c` switch. If the shell is `'cmd.exe'`, it
should understand the `/d /s /c` switches and command-line parsing should be
compatible.

## Default Windows shell

Although Microsoft specifies `%COMSPEC%` must contain the path to
`'cmd.exe'` in the root environment, child processes are not always subject to
the same requirement. Thus, in `child_process` functions where a shell can be
spawned, `'cmd.exe'` is used as a fallback if `process.env.ComSpec` is
unavailable.

## Advanced serialization

<!-- YAML
added:
 - v13.2.0
 - v12.16.0
-->

Child processes support a serialization mechanism for IPC that is based on the
[serialization API of the `node:v8` module][v8.serdes], based on the
[HTML structured clone algorithm][]. This is generally more powerful and
supports more built-in JavaScript object types, such as `BigInt`, `Map`
and `Set`, `ArrayBuffer` and `TypedArray`, `Buffer`, `Error`, `RegExp` etc.

However, this format is not a full superset of JSON, and e.g. properties set on
objects of such built-in types will not be passed on through the serialization
step. Additionally, performance may not be equivalent to that of JSON, depending
on the structure of the passed data.
Therefore, this feature requires opting in by setting the
`serialization` option to `'advanced'` when calling [`child_process.spawn()`][]
or [`child_process.fork()`][].

[Advanced serialization]: #advanced-serialization
[DEP0190]: deprecations.md#DEP0190
[Default Windows shell]: #default-windows-shell
[HTML structured clone algorithm]: https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Structured_clone_algorithm
[Shell requirements]: #shell-requirements
[Signal Events]: process.md#signal-events
[`'disconnect'`]: process.md#event-disconnect
[`'error'`]: #event-error
[`'exit'`]: #event-exit
[`'message'`]: process.md#event-message
[`ChildProcess`]: #class-childprocess
[`Error`]: errors.md#class-error
[`EventEmitter`]: events.md#class-eventemitter
[`child_process.exec()`]: #child_processexeccommand-options-callback
[`child_process.execFile()`]: #child_processexecfilefile-args-options-callback
[`child_process.execFileSync()`]: #child_processexecfilesyncfile-args-options
[`child_process.execSync()`]: #child_processexecsynccommand-options
[`child_process.fork()`]: #child_processforkmodulepath-args-options
[`child_process.spawn()`]: #child_processspawncommand-args-options
[`child_process.spawnSync()`]: #child_processspawnsynccommand-args-options
[`dgram.Socket`]: dgram.md#class-dgramsocket
[`maxBuffer` and Unicode]: #maxbuffer-and-unicode
[`net.Server`]: net.md#class-netserver
[`net.Socket`]: net.md#class-netsocket
[`options.detached`]: #optionsdetached
[`process.disconnect()`]: process.md#processdisconnect
[`process.env`]: process.md#processenv
[`process.execPath`]: process.md#processexecpath
[`process.send()`]: process.md#processsendmessage-sendhandle-options-callback
[`stdio`]: #optionsstdio
[`subprocess.connected`]: #subprocessconnected
[`subprocess.disconnect()`]: #subprocessdisconnect
[`subprocess.exitCode`]: #subprocessexitcode
[`subprocess.kill()`]: #subprocesskillsignal
[`subprocess.send()`]: #subprocesssendmessage-sendhandle-options-callback
[`subprocess.signalCode`]: #subprocesssignalcode
[`subprocess.stderr`]: #subprocessstderr
[`subprocess.stdin`]: #subprocessstdin
[`subprocess.stdio`]: #subprocessstdio
[`subprocess.stdout`]: #subprocessstdout
[`util.convertProcessSignalToExitCode()`]: util.md#utilconvertprocesssignaltoexitcodesignalcode
[`util.promisify()`]: util.md#utilpromisifyoriginal
[synchronous counterparts]: #synchronous-process-creation
[v8.serdes]: v8.md#serialization-api
