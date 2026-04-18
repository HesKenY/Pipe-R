# Node.js child_process (6/7)
source: https://github.com/nodejs/node/blob/main/doc/api/child_process.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
rgument will be
ignored except for `'SIGKILL'`, `'SIGTERM'`, `'SIGINT'` and `'SIGQUIT'`, and the
process will always be killed forcefully and abruptly (similar to `'SIGKILL'`).
See [Signal Events][] for more details.

On Linux, child processes of child processes will not be terminated
when attempting to kill their parent. This is likely to happen when running a
new process in a shell or with the use of the `shell` option of `ChildProcess`:

```cjs
const { spawn } = require('node:child_process');

const subprocess = spawn(
  'sh',
  [
    '-c',
    `node -e "setInterval(() => {
      console.log(process.pid, 'is alive')
    }, 500);"`,
  ], {
    stdio: ['inherit', 'inherit', 'inherit'],
  },
);

setTimeout(() => {
  subprocess.kill(); // Does not terminate the Node.js process in the shell.
}, 2000);
```

```mjs
import { spawn } from 'node:child_process';

const subprocess = spawn(
  'sh',
  [
    '-c',
    `node -e "setInterval(() => {
      console.log(process.pid, 'is alive')
    }, 500);"`,
  ], {
    stdio: ['inherit', 'inherit', 'inherit'],
  },
);

setTimeout(() => {
  subprocess.kill(); // Does not terminate the Node.js process in the shell.
}, 2000);
```

### `subprocess[Symbol.dispose]()`

<!-- YAML
added:
 - v20.5.0
 - v18.18.0
changes:
 - version: v24.2.0
   pr-url: https://github.com/nodejs/node/pull/58467
   description: No longer experimental.
-->

Calls [`subprocess.kill()`][] with `'SIGTERM'`.

### `subprocess.killed`

<!-- YAML
added: v0.5.10
-->

* Type: {boolean} Set to `true` after `subprocess.kill()` is used to successfully
  send a signal to the child process.

The `subprocess.killed` property indicates whether the child process
successfully received a signal from `subprocess.kill()`. The `killed` property
does not indicate that the child process has been terminated.

### `subprocess.pid`

<!-- YAML
added: v0.1.90
-->

* Type: {integer|undefined}

Returns the process identifier (PID) of the child process. If the child process
fails to spawn due to errors, then the value is `undefined` and `error` is
emitted.

```cjs
const { spawn } = require('node:child_process');
const grep = spawn('grep', ['ssh']);

console.log(`Spawned child pid: ${grep.pid}`);
grep.stdin.end();
```

```mjs
import { spawn } from 'node:child_process';
const grep = spawn('grep', ['ssh']);

console.log(`Spawned child pid: ${grep.pid}`);
grep.stdin.end();
```

### `subprocess.ref()`

<!-- YAML
added: v0.7.10
-->

Calling `subprocess.ref()` after making a call to `subprocess.unref()` will
restore the removed reference count for the child process, forcing the parent
process to wait for the child process to exit before exiting itself.

```cjs
const { spawn } = require('node:child_process');
const process = require('node:process');

const subprocess = spawn(process.argv[0], ['child_program.js'], {
  detached: true,
  stdio: 'ignore',
});

subprocess.unref();
subprocess.ref();
```

```mjs
import { spawn } from 'node:child_process';
import process from 'node:process';

const subprocess = spawn(process.argv[0], ['child_program.js'], {
  detached: true,
  stdio: 'ignore',
});

subprocess.unref();
subprocess.ref();
```

### `subprocess.send(message[, sendHandle[, options]][, callback])`

<!-- YAML
added: v0.5.9
changes:
  - version: v5.8.0
    pr-url: https://github.com/nodejs/node/pull/5283
    description: The `options` parameter, and the `keepOpen` option
                 in particular, is supported now.
  - version: v5.0.0
    pr-url: https://github.com/nodejs/node/pull/3516
    description: This method returns a boolean for flow control now.
  - version: v4.0.0
    pr-url: https://github.com/nodejs/node/pull/2620
    description: The `callback` parameter is supported now.
-->

* `message` {Object}
* `sendHandle` {Handle|undefined} `undefined`, or a [`net.Socket`][],
  [`net.Server`][], or [`dgram.Socket`][] object.
* `options` {Object} The `options` argument, if present, is an object used to
  parameterize the sending of certain types of handles. `options` supports
  the following properties:
  * `keepOpen` {boolean} A value that can be used when passing instances of
    `net.Socket`. When `true`, the socket is kept open in the sending process.
    **Default:** `false`.
* `callback` {Function}
* Returns: {boolean}

When an IPC channel has been established between the parent and child processes
( i.e. when using [`child_process.fork()`][]), the `subprocess.send()` method
can be used to send messages to the child process. When the child process is a
Node.js instance, these messages can be received via the [`'message'`][] event.

The message goes through serialization and parsing. The resulting
message might not be the same as what is originally sent.

For example, in the parent script:

```cjs
const { fork } = require('node:child_process');
const forkedProcess = fork(`${__dirname}/sub.js`);

forkedProcess.on('message', (message) => {
  console.log('PARENT got message:', message);
});

// Causes the child to print: CHILD got message: { hello: 'world' }
forkedProcess.send({ hello: 'world' });
```

```mjs
import { fork } from 'node:child_process';
const forkedProcess = fork(`${import.meta.dirname}/sub.js`);

forkedProcess.on('message', (message) => {
  console.log('PARENT got message:', message);
});

// Causes the child to print: CHILD got message: { hello: 'world' }
forkedProcess.send({ hello: 'world' });
```

And then the child script, `'sub.js'` might look like this:

```js
process.on('message', (message) => {
  console.log('CHILD got message:', message);
});

// Causes the parent to print: PARENT got message: { foo: 'bar', baz: null }
process.send({ foo: 'bar', baz: NaN });
```

Child Node.js processes will have a [`process.send()`][] method of their own
that allows the child process to send messages back to the parent process.

There is a special case when sending a `{cmd: 'NODE_foo'}` message. Messages
containing a `NODE_` prefix in the `cmd` property are reserved for use within
Node.js core and will not be emitted in the child's [`'message'`][]
event. Rather, such messages are emitted using the
`'internalMessage'` event and are consumed internally by Node.js.
Applications should avoid using such messages or listening for
`'internalMessage'` events as it is subject to change without notice.

The optional `sendHandle` argument that may be passed to `subprocess.send()` is
for passing a TCP server or socket object to the child process. The child process will
receive the object as the second argument passed to the callback function
registered on the [`'message'`][] event. Any data that is received
and buffered in the socket will not be sent to the child. Sending IPC sockets is
not supported on Windows.

The optional `callback` is a function that is invoked after the message is
sent but before the child process may have received it. The function is called with a
single argument: `null` on success, or an [`Error`][] object on failure.

If no `callback` function is provided and the message cannot be sent, an
`'error'` event will be emitted by the [`ChildProcess`][] object. This can
happen, for instance, when the child process has already exited.

`subprocess.send()` will return `false` if the channel has closed or when the
backlog of unsent messages exceeds a threshold that makes it unwise to send
more. Otherwise, the method returns `true`. The `callback` function can be
used to implement flow control.

#### Example: sending a server object

The `sendHandle` argument can be used, for instance, to pass the handle of
a TCP server object to the child process as illustrated in the example below:

```cjs
const { fork } = require('node:child_process');
const { createServer } = require('node:net');

const subprocess = fork('subprocess.js');

// Open up the server object and send the handle.
const server = createServer();
server.on('connection', (socket) => {
  socket.end('handled by parent');
});
server.listen(1337, () => {
  subprocess.send('server', server);
});
```

```mjs
import { fork } from 'node:child_process';
import { createServer } from 'node:net';

const subprocess = fork('subprocess.js');

// Open up the server object and send the handle.
const server = createServer();
server.on('connection', (socket) => {
  socket.end('handled by parent');
});
server.listen(1337, () => {
  subprocess.send('server', server);
});
```

The child process would then receive the server object as:

```js
process.on('message', (m, server) => {
  if (m === 'server') {
    server.on('connection', (socket) => {
      socket.end('handled by child');
    });
  }
});
```

Once the server is now shared between the parent and child, some connections
can be handled by the parent and some by the child.

While the example above uses a server created using the `node:net` module,
`node:dgram` module servers use exactly the same workflow with the exceptions of
listening on a `'message'` event instead of `'connection'` and using
`server.bind()` instead of `server.listen()`. This is, however, only
supported on Unix platforms.

#### Example: sending a socket object

Similarly, the `sendHandler` argument can be used to pass the handle of a
socket to the child process. The example below spawns two children that each
handle connections with "normal" or "special" priority:

```cjs
const { fork } = require('node:child_process');
const { createServer } = require('node:net');

const normal = fork('subprocess.js', ['normal']);
const special = fork('subprocess.js', ['special']);

// Open up the server and send sockets to child. Use pauseOnConnect to prevent
// the sockets from being read before they are sent to the child process.
const server = createServer({ pauseOnConnect: true });
server.on('connection', (socket) => {

// If this is special priority...
  if (socket.remoteAddress === '74.125.127.100') {
    special.send('socket', socket);
    return;
  }
  // This is normal priority.
  normal.send('socket', socket);
});
server.listen(1337);
```

```mjs
import { fork } from 'node:child_process';
import { createServer } from 'node:net';

const normal = fork('subprocess.js', ['normal']);
const special = fork('subprocess.js', ['special']);

// Open up the server and send sockets to child. Use pauseOnConnect to prevent
// the sockets from being read before they are sent to the child process.
const server = createServer({ pauseOnConnect: true });
server.on('connection', (socket) => {

// If this is special priority...
  if (socket.remoteAddress === '74.125.127.100') {
    special.send('socket', socket);
    return;
  }
  // This is normal priority.
  normal.send('socket', socket);
});
server.listen(1337);
```

The `subprocess.js` would receive the socket handle as the second argument
passed to the event callback function:

```js
process.on('message', (m, socket) => {
  if (m === 'socket') {
    if (socket) {
      // Check that the client socket exists.
      // It is possible for the socket to be closed between the time it is
      // sent and the time it is received in the child process.
      socket.end(`Request handled with ${process.argv[2]} priority`);
    }
  }
});
```

Do not use `.maxConnections` on a socket that has been passed to a subprocess.
The parent cannot track when the socket is destroyed.

Any `'message'` handlers in the subprocess should verify that `socket` exists,
as the connection may have been closed during the time it takes to send the
connection to the child.

### `subprocess.signalCode`

* Type: {string|null}

The `subprocess.signalCode` property indicates the signal received by
the child process if any, else `null`.

When the child process is terminated by a signal, [`subprocess.exitCode`][] will be `null`.
To get the corresponding POSIX exit code, use
[`util.convertProcessSignalToExitCode(subprocess.signalCode)`][`util.convertProcessSignalToExitCode()`].

### `subprocess.spawnargs`

* Type: {Array}

The `subprocess.spawnargs` property represents the full list of command-line
arguments the child process was launched with.

### `subprocess.spawnfile`

* Type: {string}

The `subprocess.spawnfile` property indicates the executable file name of
the child process that is launched.

For [`child_process.fork()`][], its value will be equal to
[`process.execPath`][].
For [`child_process.spawn()`][], its value will be the name of
the executable file.
For [`child_process.exec()`][],  its value will be the name of the shell
in which the child process is launched.

### `subprocess.stderr`

<!-- YAML
added: v0.1.90
-->

* Type: {stream.Readable|null|undefined}

A `Readable Stream` that represents the child process's `stderr`.

If the child process was spawned with `stdio[2]` set to anything other than `'pipe'`,
then this will be `null`.

`subprocess.stderr` is an alias for `subprocess.stdio[2]`. Both properties will
refer to the same value.

The `subprocess.stderr` property can be `null` or `undefined`
if the child process could not be successfully spawned.

### `subprocess.stdin`

<!-- YAML
added: v0.1.90
-->

* Type: {stream.Writable|null|undefined}

A `Writable Stream` that represents the child process's `stdin`.

If a child process waits to read all of its input, the child process will not continue
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
