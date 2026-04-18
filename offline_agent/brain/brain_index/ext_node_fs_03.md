# Node.js fs (3/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
ocumentation for more detail. **Default:** `null`
* Returns: {Promise}

Write `buffer` to the file.

The promise is fulfilled with an object containing two properties:

* `bytesWritten` {integer} the number of bytes written
* `buffer` {Buffer|TypedArray|DataView} a reference to the
  `buffer` written.

It is unsafe to use `filehandle.write()` multiple times on the same file
without waiting for the promise to be fulfilled (or rejected). For this
scenario, use [`filehandle.createWriteStream()`][].

On Linux, positional writes do not work when the file is opened in append mode.
The kernel ignores the position argument and always appends the data to
the end of the file.

#### `filehandle.write(buffer[, options])`

<!-- YAML
added:
  - v18.3.0
  - v16.17.0
-->

* `buffer` {Buffer|TypedArray|DataView}
* `options` {Object}
  * `offset` {integer} **Default:** `0`
  * `length` {integer} **Default:** `buffer.byteLength - offset`
  * `position` {integer|null} **Default:** `null`
* Returns: {Promise}

Write `buffer` to the file.

Similar to the above `filehandle.write` function, this version takes an
optional `options` object. If no `options` object is specified, it will
default with the above values.

#### `filehandle.write(string[, position[, encoding]])`

<!-- YAML
added: v10.0.0
changes:
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/31030
    description: The `string` parameter won't coerce unsupported input to
                 strings anymore.
-->

* `string` {string}
* `position` {integer|null} The offset from the beginning of the file where the
  data from `string` should be written. If `position` is not a `number` the
  data will be written at the current position. See the POSIX pwrite(2)
  documentation for more detail. **Default:** `null`
* `encoding` {string} The expected string encoding. **Default:** `'utf8'`
* Returns: {Promise}

Write `string` to the file. If `string` is not a string, the promise is
rejected with an error.

The promise is fulfilled with an object containing two properties:

* `bytesWritten` {integer} the number of bytes written
* `buffer` {string} a reference to the `string` written.

It is unsafe to use `filehandle.write()` multiple times on the same file
without waiting for the promise to be fulfilled (or rejected). For this
scenario, use [`filehandle.createWriteStream()`][].

On Linux, positional writes do not work when the file is opened in append mode.
The kernel ignores the position argument and always appends the data to
the end of the file.

#### `filehandle.writeFile(data, options)`

<!-- YAML
added: v10.0.0
changes:
  - version:
      - v15.14.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/37490
    description: The `data` argument supports `AsyncIterable`, `Iterable`, and `Stream`.
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/31030
    description: The `data` parameter won't coerce unsupported input to
                 strings anymore.
-->

* `data` {string|Buffer|TypedArray|DataView|AsyncIterable|Iterable|Stream}
* `options` {Object|string}
  * `encoding` {string|null} The expected character encoding when `data` is a
    string. **Default:** `'utf8'`
  * `signal` {AbortSignal|undefined} allows aborting an in-progress writeFile. **Default:** `undefined`
* Returns: {Promise}

Asynchronously writes data to a file, replacing the file if it already exists.
`data` can be a string, a buffer, an {AsyncIterable}, or an {Iterable} object.
The promise is fulfilled with no arguments upon success.

If `options` is a string, then it specifies the `encoding`.

The {FileHandle} has to support writing.

It is unsafe to use `filehandle.writeFile()` multiple times on the same file
without waiting for the promise to be fulfilled (or rejected).

If one or more `filehandle.write()` calls are made on a file handle and then a
`filehandle.writeFile()` call is made, the data will be written from the
current position till the end of the file. It doesn't always write from the
beginning of the file.

#### `filehandle.writev(buffers[, position])`

<!-- YAML
added: v12.9.0
-->

* `buffers` {Buffer\[]|TypedArray\[]|DataView\[]}
* `position` {integer|null} The offset from the beginning of the file where the
  data from `buffers` should be written. If `position` is not a `number`,
  the data will be written at the current position. **Default:** `null`
* Returns: {Promise}

Write an array of {ArrayBufferView}s to the file.

The promise is fulfilled with an object containing a two properties:

* `bytesWritten` {integer} the number of bytes written
* `buffers` {Buffer\[]|TypedArray\[]|DataView\[]} a reference to the `buffers`
  input.

It is unsafe to call `writev()` multiple times on the same file without waiting
for the promise to be fulfilled (or rejected).

On Linux, positional writes don't work when the file is opened in append mode.
The kernel ignores the position argument and always appends the data to
the end of the file.

#### `filehandle.writer([options])`

<!-- YAML
added: v25.9.0
-->

> Stability: 1 - Experimental

* `options` {Object}
  * `autoClose` {boolean} Close the file handle when the writer ends or
    fails. **Default:** `false`.
  * `start` {number} Byte offset to start writing at. When specified,
    writes use explicit positioning. **Default:** current file position.
  * `limit` {number} Maximum number of bytes the writer will accept.
    Async writes (`write()`, `writev()`) that would exceed the limit reject
    with `ERR_OUT_OF_RANGE`. Sync writes (`writeSync()`, `writevSync()`)
    return `false`. **Default:** no limit.
  * `chunkSize` {number} Maximum chunk size in bytes for synchronous write
    operations. Writes larger than this threshold fall back to async I/O.
    Set this to match the reader's `chunkSize` for optimal `pipeTo()`
    performance. **Default:** `131072` (128 KB).
* Returns: {Object}
  * `write(chunk[, options])` {Function} Returns {Promise\<void>}.
    Accepts `Uint8Array`, `Buffer`, or string (UTF-8 encoded).
    * `chunk` {Buffer|TypedArray|DataView|string}
    * `options` {Object}
      * `signal` {AbortSignal} If the signal is already aborted, the write
        rejects with `AbortError` without performing I/O.
  * `writev(chunks[, options])` {Function} Returns {Promise\<void>}. Uses
    scatter/gather I/O via a single `writev()` syscall. Accepts mixed
    `Uint8Array`/string arrays.
    * `chunks` {Array\<Buffer|TypedArray|DataView|string>}
    * `options` {Object}
      * `signal` {AbortSignal} If the signal is already aborted, the write
        rejects with `AbortError` without performing I/O.
  * `writeSync(chunk)` {Function} Returns {boolean}. Attempts a synchronous
    write. Returns `true` if the write succeeded, `false` if the caller
    should fall back to async `write()`. Returns `false` when: the writer
    is closed/errored, an async operation is in flight, the chunk exceeds
    `chunkSize`, or the write would exceed `limit`.
    * `chunk` {Buffer|TypedArray|DataView|string}
  * `writevSync(chunks)` {Function} Returns {boolean}. Synchronous batch
    write. Same fallback semantics as `writeSync()`.
    * `chunks` {Array\<Buffer|TypedArray|DataView|string>}
  * `end([options])` {Function} Returns {Promise\<number>} total bytes
    written. Idempotent: returns `totalBytesWritten` if already closed,
    returns the pending promise if already closing. Rejects if the writer
    is in an errored state.
    * `options` {Object}
      * `signal` {AbortSignal} If the signal is already aborted, `end()`
        rejects with `AbortError` and the writer remains open.
  * `endSync()` {Function} Returns {number|number} total bytes written on
    success, `-1` if the writer is errored or an async operation is in
    flight. Idempotent when already closed.
  * `fail(reason)` {Function} Puts the writer into a terminal error state.
    Synchronous. If the writer is already closed or errored, this is a
    no-op. If `autoClose` is true, closes the file handle synchronously.

Return a [`node:stream/iter`][] writer backed by this file handle.

The writer supports both `Symbol.asyncDispose` and `Symbol.dispose`:

* `await using w = fh.writer()` — if the writer is still open (no `end()`
  called), `asyncDispose` calls `fail()`. If `end()` is pending, it waits
  for it to complete.
* `using w = fh.writer()` — calls `fail()` unconditionally.

The `writeSync()` and `writevSync()` methods enable the try-sync fast path
used by [`stream/iter pipeTo()`][]. When the reader's chunk size matches the
writer's `chunkSize`, all writes in a `pipeTo()` pipeline complete
synchronously with zero promise overhead.

This function is only available when the `--experimental-stream-iter` flag is
enabled.

```mjs
import { open } from 'node:fs/promises';
import { from, pipeTo } from 'node:stream/iter';
import { compressGzip } from 'node:zlib/iter';

// Async pipeline
const fh = await open('output.gz', 'w');
await pipeTo(from('Hello!'), compressGzip(), fh.writer({ autoClose: true }));

// Sync pipeline with limit
const src = await open('input.txt', 'r');
const dst = await open('output.txt', 'w');
const w = dst.writer({ limit: 1024 * 1024 }); // Max 1 MB
await pipeTo(src.pull({ autoClose: true }), w);
await w.end();
await dst.close();
```

```cjs
const { open } = require('node:fs/promises');
const { from, pipeTo } = require('node:stream/iter');
const { compressGzip } = require('node:zlib/iter');

async function run() {
  // Async pipeline
  const fh = await open('output.gz', 'w');
  await pipeTo(from('Hello!'), compressGzip(), fh.writer({ autoClose: true }));

// Sync pipeline with limit
  const src = await open('input.txt', 'r');
  const dst = await open('output.txt', 'w');
  const w = dst.writer({ limit: 1024 * 1024 }); // Max 1 MB
  await pipeTo(src.pull({ autoClose: true }), w);
  await w.end();
  await dst.close();
}

run().catch(console.error);
```

#### `filehandle[Symbol.asyncDispose]()`

<!-- YAML
added:
 - v20.4.0
 - v18.18.0
changes:
 - version: v24.2.0
   pr-url: https://github.com/nodejs/node/pull/58467
   description: No longer experimental.
-->

Calls `filehandle.close()` and returns a promise that fulfills when the
filehandle is closed.

### `fsPromises.access(path[, mode])`

<!-- YAML
added: v10.0.0
-->

* `path` {string|Buffer|URL}
* `mode` {integer} **Default:** `fs.constants.F_OK`
* Returns: {Promise} Fulfills with `undefined` upon success.

Tests a user's permissions for the file or directory specified by `path`.
The `mode` argument is an optional integer that specifies the accessibility
checks to be performed. `mode` should be either the value `fs.constants.F_OK`
or a mask consisting of the bitwise OR of any of `fs.constants.R_OK`,
`fs.constants.W_OK`, and `fs.constants.X_OK` (e.g.
`fs.constants.W_OK | fs.constants.R_OK`). Check [File access constants][] for
possible values of `mode`.

If the accessibility check is successful, the promise is fulfilled with no
value. If any of the accessibility checks fail, the promise is rejected
with an {Error} object. The following example checks if the file
`/etc/passwd` can be read and written by the current process.

```mjs
import { access, constants } from 'node:fs/promises';

try {
  await access('/etc/passwd', constants.R_OK | constants.W_OK);
  console.log('can access');
} catch {
  console.error('cannot access');
}
```

Using `fsPromises.access()` to check for the accessibility of a file before
calling `fsPromises.open()` is not recommended. Doing so introduces a race
condition, since other processes may change the file's state between the two
calls. Instead, user code should open/read/write the file directly and handle
the error raised if the file is not accessible.

### `fsPromises.appendFile(path, data[, options])`

<!-- YAML
added: v10.0.0
changes:
  - version:
    - v21.1.0
    - v20.10.0
    pr-url: https://github.com/nodejs/node/pull/50095
    description: The `flush` option is now supported.
-->

* `path` {string|Buffer|URL|FileHandle} filename or {FileHandle}
* `data` {string|Buffer}
* `options` {Object|string}
  * `encoding` {string|null} **Default:** `'utf8'`
  * `mode` {integer} **Default:** `0o666`
  * `flag` {string} See [support of file system `flags`][]. **Default:** `'a'`.
  * `flush` {boolean} If `true`, the underlying file descriptor is flushed
    prior to closing it. **Default:** `false`.
* Returns: {Promise} Fulfills with `undefined` upon success.

Asynchronously append data to a file, creating the file if it does not yet
exist. `data` can be a string or a {Buffer}.

If `options` is a string, then it specifies the `encoding`.

The `mode` option only affects the newly created file. See [`fs.open()`][]
for more details.

The `path` may be specified as a {FileHandle} that has been opened
for appending (using `fsPromises.open()`).

### `fsPromises.chmod(path, mode)`

<!-- YAML
added: v10.0.0
-->

* `path` {string|Buffer|URL}
* `mode` {string|integer}
* Returns: {Promise} Fulfills with `undefined` upon success.

Changes the permissions of a file.

### `fsPromises.chown(path, uid, gid)`

<!-- YAML
added: v10.0.0
-->

* `path` {string|Buffer|URL}
* `uid` {integer}
* `gid` {integer}
* Returns: {Promise} Fulfills with `undefined` upon success.

Changes the ownership of a file.

### `fsPromises.copyFile(src, dest[, mode])`

<!-- YAML
added: v10.0.0
changes:
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/27044
    description: Changed `flags` argument to `mode` and imposed
                 stricter type validation.
-->
