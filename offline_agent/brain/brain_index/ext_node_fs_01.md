# Node.js fs (1/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
# File system

<!--introduced_in=v0.10.0-->

> Stability: 2 - Stable

<!--name=fs-->

<!-- source_link=lib/fs.js -->

The `node:fs` module enables interacting with the file system in a
way modeled on standard POSIX functions.

To use the promise-based APIs:

```mjs
import * as fs from 'node:fs/promises';
```

```cjs
const fs = require('node:fs/promises');
```

To use the callback and sync APIs:

```mjs
import * as fs from 'node:fs';
```

```cjs
const fs = require('node:fs');
```

All file system operations have synchronous, callback, and promise-based
forms, and are accessible using both CommonJS syntax and ES6 Modules (ESM).

## Promise example

Promise-based operations return a promise that is fulfilled when the
asynchronous operation is complete.

```mjs
import { unlink } from 'node:fs/promises';

try {
  await unlink('/tmp/hello');
  console.log('successfully deleted /tmp/hello');
} catch (error) {
  console.error('there was an error:', error.message);
}
```

```cjs
const { unlink } = require('node:fs/promises');

(async function(path) {
  try {
    await unlink(path);
    console.log(`successfully deleted ${path}`);
  } catch (error) {
    console.error('there was an error:', error.message);
  }
})('/tmp/hello');
```

## Callback example

The callback form takes a completion callback function as its last
argument and invokes the operation asynchronously. The arguments passed to
the completion callback depend on the method, but the first argument is always
reserved for an exception. If the operation is completed successfully, then
the first argument is `null` or `undefined`.

```mjs
import { unlink } from 'node:fs';

unlink('/tmp/hello', (err) => {
  if (err) throw err;
  console.log('successfully deleted /tmp/hello');
});
```

```cjs
const { unlink } = require('node:fs');

unlink('/tmp/hello', (err) => {
  if (err) throw err;
  console.log('successfully deleted /tmp/hello');
});
```

The callback-based versions of the `node:fs` module APIs are preferable over
the use of the promise APIs when maximal performance (both in terms of
execution time and memory allocation) is required.

## Synchronous example

The synchronous APIs block the Node.js event loop and further JavaScript
execution until the operation is complete. Exceptions are thrown immediately
and can be handled using `try…catch`, or can be allowed to bubble up.

```mjs
import { unlinkSync } from 'node:fs';

try {
  unlinkSync('/tmp/hello');
  console.log('successfully deleted /tmp/hello');
} catch (err) {
  // handle the error
}
```

```cjs
const { unlinkSync } = require('node:fs');

try {
  unlinkSync('/tmp/hello');
  console.log('successfully deleted /tmp/hello');
} catch (err) {
  // handle the error
}
```

## Promises API

<!-- YAML
added: v10.0.0
changes:
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/31553
    description: Exposed as `require('fs/promises')`.
  - version:
    - v11.14.0
    - v10.17.0
    pr-url: https://github.com/nodejs/node/pull/26581
    description: This API is no longer experimental.
  - version: v10.1.0
    pr-url: https://github.com/nodejs/node/pull/20504
    description: The API is accessible via `require('fs').promises` only.
-->

The `fs/promises` API provides asynchronous file system methods that return
promises.

The promise APIs use the underlying Node.js threadpool to perform file
system operations off the event loop thread. These operations are not
synchronized or threadsafe. Care must be taken when performing multiple
concurrent modifications on the same file or data corruption may occur.

### Class: `FileHandle`

<!-- YAML
added: v10.0.0
-->

A {FileHandle} object is an object wrapper for a numeric file descriptor.

Instances of the {FileHandle} object are created by the `fsPromises.open()`
method.

All {FileHandle} objects are {EventEmitter}s.

If a {FileHandle} is not closed using the `filehandle.close()` method, it will
try to automatically close the file descriptor and emit a process warning,
helping to prevent memory leaks. Please do not rely on this behavior because
it can be unreliable and the file may not be closed. Instead, always explicitly
close {FileHandle}s. Node.js may change this behavior in the future.

#### Event: `'close'`

<!-- YAML
added: v15.4.0
-->

The `'close'` event is emitted when the {FileHandle} has been closed and can no
longer be used.

#### `filehandle.appendFile(data[, options])`

<!-- YAML
added: v10.0.0
changes:
  - version:
    - v21.1.0
    - v20.10.0
    pr-url: https://github.com/nodejs/node/pull/50095
    description: The `flush` option is now supported.
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
  * `encoding` {string|null} **Default:** `'utf8'`
  * `signal` {AbortSignal|undefined} allows aborting an in-progress writeFile. **Default:** `undefined`
* Returns: {Promise} Fulfills with `undefined` upon success.

Alias of [`filehandle.writeFile()`][].

When operating on file handles, the mode cannot be changed from what it was set
to with [`fsPromises.open()`][]. Therefore, this is equivalent to
[`filehandle.writeFile()`][].

#### `filehandle.chmod(mode)`

<!-- YAML
added: v10.0.0
-->

* `mode` {integer} the file mode bit mask.
* Returns: {Promise} Fulfills with `undefined` upon success.

Modifies the permissions on the file. See chmod(2).

#### `filehandle.chown(uid, gid)`

<!-- YAML
added: v10.0.0
-->

* `uid` {integer} The file's new owner's user id.
* `gid` {integer} The file's new group's group id.
* Returns: {Promise} Fulfills with `undefined` upon success.

Changes the ownership of the file. A wrapper for chown(2).

#### `filehandle.close()`

<!-- YAML
added: v10.0.0
-->

* Returns: {Promise} Fulfills with `undefined` upon success.

Closes the file handle after waiting for any pending operation on the handle to
complete.

```mjs
import { open } from 'node:fs/promises';

let filehandle;
try {
  filehandle = await open('thefile.txt', 'r');
} finally {
  await filehandle?.close();
}
```

#### `filehandle.createReadStream([options])`

<!-- YAML
added: v16.11.0
-->

* `options` {Object}
  * `encoding` {string} **Default:** `null`
  * `autoClose` {boolean} **Default:** `true`
  * `emitClose` {boolean} **Default:** `true`
  * `start` {integer}
  * `end` {integer} **Default:** `Infinity`
  * `highWaterMark` {integer} **Default:** `64 * 1024`
  * `signal` {AbortSignal|undefined} **Default:** `undefined`
* Returns: {fs.ReadStream}

`options` can include `start` and `end` values to read a range of bytes from
the file instead of the entire file. Both `start` and `end` are inclusive and
start counting at 0, allowed values are in the
\[0, [`Number.MAX_SAFE_INTEGER`][]] range. If `start` is
omitted or `undefined`, `filehandle.createReadStream()` reads sequentially from
the current file position. The `encoding` can be any one of those accepted by
{Buffer}.

If the `FileHandle` points to a character device that only supports blocking
reads (such as keyboard or sound card), read operations do not finish until data
is available. This can prevent the process from exiting and the stream from
closing naturally.

By default, the stream will emit a `'close'` event after it has been
destroyed.  Set the `emitClose` option to `false` to change this behavior.

```mjs
import { open } from 'node:fs/promises';

const fd = await open('/dev/input/event0');
// Create a stream from some character device.
const stream = fd.createReadStream();
setTimeout(() => {
  stream.close(); // This may not close the stream.
  // Artificially marking end-of-stream, as if the underlying resource had
  // indicated end-of-file by itself, allows the stream to close.
  // This does not cancel pending read operations, and if there is such an
  // operation, the process may still not be able to exit successfully
  // until it finishes.
  stream.push(null);
  stream.read(0);
}, 100);
```

If `autoClose` is false, then the file descriptor won't be closed, even if
there's an error. It is the application's responsibility to close it and make
sure there's no file descriptor leak. If `autoClose` is set to true (default
behavior), on `'error'` or `'end'` the file descriptor will be closed
automatically.

An example to read the last 10 bytes of a file which is 100 bytes long:

```mjs
import { open } from 'node:fs/promises';

const fd = await open('sample.txt');
fd.createReadStream({ start: 90, end: 99 });
```

#### `filehandle.createWriteStream([options])`

<!-- YAML
added: v16.11.0
changes:
  - version:
    - v21.0.0
    - v20.10.0
    pr-url: https://github.com/nodejs/node/pull/50093
    description: The `flush` option is now supported.
-->

* `options` {Object}
  * `encoding` {string} **Default:** `'utf8'`
  * `autoClose` {boolean} **Default:** `true`
  * `emitClose` {boolean} **Default:** `true`
  * `start` {integer}
  * `highWaterMark` {number} **Default:** `16384`
  * `flush` {boolean} If `true`, the underlying file descriptor is flushed
    prior to closing it. **Default:** `false`.
* Returns: {fs.WriteStream}

`options` may also include a `start` option to allow writing data at some
position past the beginning of the file, allowed values are in the
\[0, [`Number.MAX_SAFE_INTEGER`][]] range. Modifying a file rather than
replacing it may require the `flags` `open` option to be set to `r+` rather than
the default `r`. The `encoding` can be any one of those accepted by {Buffer}.

If `autoClose` is set to true (default behavior) on `'error'` or `'finish'`
the file descriptor will be closed automatically. If `autoClose` is false,
then the file descriptor won't be closed, even if there's an error.
It is the application's responsibility to close it and make sure there's no
file descriptor leak.

By default, the stream will emit a `'close'` event after it has been
destroyed.  Set the `emitClose` option to `false` to change this behavior.

#### `filehandle.datasync()`

<!-- YAML
added: v10.0.0
-->

* Returns: {Promise} Fulfills with `undefined` upon success.

Forces all currently queued I/O operations associated with the file to the
operating system's synchronized I/O completion state. Refer to the POSIX
fdatasync(2) documentation for details.

Unlike `filehandle.sync` this method does not flush modified metadata.

#### `filehandle.fd`

<!-- YAML
added: v10.0.0
-->

* Type: {number} The numeric file descriptor managed by the {FileHandle} object.

#### `filehandle.pull([...transforms][, options])`

<!-- YAML
added: v25.9.0
-->

> Stability: 1 - Experimental

* `...transforms` {Function|Object} Optional transforms to apply via
  [`stream/iter pull()`][].
* `options` {Object}
  * `signal` {AbortSignal}
  * `autoClose` {boolean} Close the file handle when the stream ends.
    **Default:** `false`.
  * `start` {number} Byte offset to begin reading from. When specified,
    reads use explicit positioning (`pread` semantics). **Default:** current
    file position.
  * `limit` {number} Maximum number of bytes to read before ending the
    iterator. Reads stop when `limit` bytes have been delivered or EOF is
    reached, whichever comes first. **Default:** read until EOF.
  * `chunkSize` {number} Size in bytes of the buffer allocated for each
    read operation. **Default:** `131072` (128 KB).
* Returns: {AsyncIterable\<Uint8Array\[]>}

Return the file contents as an async iterable using the
[`node:stream/iter`][] pull model. Reads are performed in `chunkSize`-byte
chunks (default 128 KB). If transforms are provided, they are applied
via [`stream/iter pull()`][].

The file handle is locked while the iterable is being consumed and unlocked
when iteration completes, an error occurs, or the consumer breaks.

This function is only available when the `--experimental-stream-iter` flag is
enabled.

```mjs
import { open } from 'node:fs/promises';
import { text } from 'node:stream/iter';
import { compressGzip } from 'node:zlib/iter';

const fh = await open('input.txt', 'r');

// Read as text
console.log(await text(fh.pull({ autoClose: true })));

// Read 1 KB starting at byte 100
const fh2 = await open('input.txt', 'r');
console.log(await text(fh2.pull({ start: 100, limit: 1024, autoClose: true })));

// Read with compression
const fh3 = await open('input.txt', 'r');
const compressed = fh3.pull(compressGzip(), { autoClose: true });
```

```cjs
const { open } = require('node:fs/promises');
const { text } = require('node:stream/iter');
const { compressGzip } = require('node:zlib/iter');

async function run() {
  const fh = await open('input.txt', 'r');

// Read as text
  console.log(await text(fh.pull({ autoClose: true })));

// Read 1 KB starting at byte 100
  const fh2 = await open('input.txt', 'r');
  console.log(await text(fh2.pull({ start: 100, limit: 1024, autoClose: true })));

// Read with compression
  const fh3 = await open('input.txt', 'r');
  const compressed = fh3.pull(compressGzip(), { autoClose: true });
}

run().catch(console.error);
```

#### `filehandle.pullSync([...transforms][, options])`

<!-- YAML
added: v25.9.0
-->

> Stability: 1 - Experimental
