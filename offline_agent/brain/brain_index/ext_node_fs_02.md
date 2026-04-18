# Node.js fs (2/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
e.log(await text(fh.pull({ autoClose: true })));

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

* `...transforms` {Function|Object} Optional transforms to apply via
  [`stream/iter pullSync()`][].
* `options` {Object}
  * `autoClose` {boolean} Close the file handle when the stream ends.
    **Default:** `false`.
  * `start` {number} Byte offset to begin reading from. When specified,
    reads use explicit positioning. **Default:** current file position.
  * `limit` {number} Maximum number of bytes to read before ending the
    iterator. **Default:** read until EOF.
  * `chunkSize` {number} Size in bytes of the buffer allocated for each
    read operation. **Default:** `131072` (128 KB).
* Returns: {Iterable\<Uint8Array\[]>}

Synchronous counterpart of [`filehandle.pull()`][]. Returns a sync iterable
that reads the file using synchronous I/O on the main thread. Reads are
performed in `chunkSize`-byte chunks (default 128 KB).

The file handle is locked while the iterable is being consumed. Unlike the
async `pull()`, this method does not support `AbortSignal` since all
operations are synchronous.

This function is only available when the `--experimental-stream-iter` flag is
enabled.

```mjs
import { open } from 'node:fs/promises';
import { textSync, pipeToSync } from 'node:stream/iter';
import { compressGzipSync, decompressGzipSync } from 'node:zlib/iter';

const fh = await open('input.txt', 'r');

// Read as text (sync)
console.log(textSync(fh.pullSync({ autoClose: true })));

// Sync compress pipeline: file -> gzip -> file
const src = await open('input.txt', 'r');
const dst = await open('output.gz', 'w');
pipeToSync(src.pullSync(compressGzipSync(), { autoClose: true }), dst.writer({ autoClose: true }));
```

```cjs
const { open } = require('node:fs/promises');
const { textSync, pipeToSync } = require('node:stream/iter');
const { compressGzipSync, decompressGzipSync } = require('node:zlib/iter');

async function run() {
  const fh = await open('input.txt', 'r');

// Read as text (sync)
  console.log(textSync(fh.pullSync({ autoClose: true })));

// Sync compress pipeline: file -> gzip -> file
  const src = await open('input.txt', 'r');
  const dst = await open('output.gz', 'w');
  pipeToSync(
    src.pullSync(compressGzipSync(), { autoClose: true }),
    dst.writer({ autoClose: true }),
  );
}

run().catch(console.error);
```

#### `filehandle.read(buffer, offset, length, position)`

<!-- YAML
added: v10.0.0
changes:
  - version: v21.0.0
    pr-url: https://github.com/nodejs/node/pull/42835
    description: Accepts bigint values as `position`.
-->

* `buffer` {Buffer|TypedArray|DataView} A buffer that will be filled with the
  file data read.
* `offset` {integer} The location in the buffer at which to start filling.
  **Default:** `0`
* `length` {integer} The number of bytes to read. **Default:**
  `buffer.byteLength - offset`
* `position` {integer|bigint|null} The location where to begin reading data
  from the file. If `null` or `-1`, data will be read from the current file
  position, and the position will be updated. If `position` is a non-negative
  integer, the current file position will remain unchanged.
  **Default:** `null`
* Returns: {Promise} Fulfills upon success with an object with two properties:
  * `bytesRead` {integer} The number of bytes read
  * `buffer` {Buffer|TypedArray|DataView} A reference to the passed in `buffer`
    argument.

Reads data from the file and stores that in the given buffer.

If the file is not modified concurrently, the end-of-file is reached when the
number of bytes read is zero.

#### `filehandle.read([options])`

<!-- YAML
added:
 - v13.11.0
 - v12.17.0
changes:
  - version: v21.0.0
    pr-url: https://github.com/nodejs/node/pull/42835
    description: Accepts bigint values as `position`.
-->

* `options` {Object}
  * `buffer` {Buffer|TypedArray|DataView} A buffer that will be filled with the
    file data read. **Default:** `Buffer.alloc(16384)`
  * `offset` {integer} The location in the buffer at which to start filling.
    **Default:** `0`
  * `length` {integer} The number of bytes to read. **Default:**
    `buffer.byteLength - offset`
  * `position` {integer|bigint|null} The location where to begin reading data
    from the file. If `null` or `-1`, data will be read from the current file
    position, and the position will be updated. If `position` is a non-negative
    integer, the current file position will remain unchanged.
    **Default:**: `null`
* Returns: {Promise} Fulfills upon success with an object with two properties:
  * `bytesRead` {integer} The number of bytes read
  * `buffer` {Buffer|TypedArray|DataView} A reference to the passed in `buffer`
    argument.

Reads data from the file and stores that in the given buffer.

If the file is not modified concurrently, the end-of-file is reached when the
number of bytes read is zero.

#### `filehandle.read(buffer[, options])`

<!-- YAML
added:
  - v18.2.0
  - v16.17.0
changes:
  - version: v21.0.0
    pr-url: https://github.com/nodejs/node/pull/42835
    description: Accepts bigint values as `position`.
-->

* `buffer` {Buffer|TypedArray|DataView} A buffer that will be filled with the
  file data read.
* `options` {Object}
  * `offset` {integer} The location in the buffer at which to start filling.
    **Default:** `0`
  * `length` {integer} The number of bytes to read. **Default:**
    `buffer.byteLength - offset`
  * `position` {integer|bigint|null} The location where to begin reading data
    from the file. If `null` or `-1`, data will be read from the current file
    position, and the position will be updated. If `position` is a non-negative
    integer, the current file position will remain unchanged.
    **Default:**: `null`
* Returns: {Promise} Fulfills upon success with an object with two properties:
  * `bytesRead` {integer} The number of bytes read
  * `buffer` {Buffer|TypedArray|DataView} A reference to the passed in `buffer`
    argument.

Reads data from the file and stores that in the given buffer.

If the file is not modified concurrently, the end-of-file is reached when the
number of bytes read is zero.

#### `filehandle.readableWebStream([options])`

<!-- YAML
added: v17.0.0
changes:

- version:
      - v24.0.0
      - v22.17.0
    pr-url: https://github.com/nodejs/node/pull/57513
    description: Marking the API stable.
  - version:
    - v23.8.0
    - v22.15.0
    pr-url: https://github.com/nodejs/node/pull/55461
    description: Removed option to create a 'bytes' stream. Streams are now always 'bytes' streams.
  - version:
    - v20.0.0
    - v18.17.0
    pr-url: https://github.com/nodejs/node/pull/46933
    description: Added option to create a 'bytes' stream.
-->

* `options` {Object}
  * `autoClose` {boolean} When true, causes the {FileHandle} to be closed when the
    stream is closed. **Default:** `false`
* Returns: {ReadableStream}

Returns a byte-oriented `ReadableStream` that may be used to read the file's
contents.

An error will be thrown if this method is called more than once or is called
after the `FileHandle` is closed or closing.

```mjs
import {
  open,
} from 'node:fs/promises';

const file = await open('./some/file/to/read');

for await (const chunk of file.readableWebStream())
  console.log(chunk);

await file.close();
```

```cjs
const {
  open,
} = require('node:fs/promises');

(async () => {
  const file = await open('./some/file/to/read');

for await (const chunk of file.readableWebStream())
    console.log(chunk);

await file.close();
})();
```

While the `ReadableStream` will read the file to completion, it will not
close the `FileHandle` automatically. User code must still call the
`fileHandle.close()` method unless the `autoClose` option is set to `true`.

#### `filehandle.readFile(options)`

<!-- YAML
added: v10.0.0
-->

* `options` {Object|string}
  * `encoding` {string|null} **Default:** `null`
  * `signal` {AbortSignal} allows aborting an in-progress readFile
* Returns: {Promise} Fulfills upon a successful read with the contents of the
  file. If no encoding is specified (using `options.encoding`), the data is
  returned as a {Buffer} object. Otherwise, the data will be a string.

Asynchronously reads the entire contents of a file.

If `options` is a string, then it specifies the `encoding`.

The {FileHandle} has to support reading.

If one or more `filehandle.read()` calls are made on a file handle and then a
`filehandle.readFile()` call is made, the data will be read from the current
position till the end of the file. It doesn't always read from the beginning
of the file.

#### `filehandle.readLines([options])`

<!-- YAML
added: v18.11.0
-->

* `options` {Object}
  * `encoding` {string} **Default:** `null`
  * `autoClose` {boolean} **Default:** `true`
  * `emitClose` {boolean} **Default:** `true`
  * `start` {integer}
  * `end` {integer} **Default:** `Infinity`
  * `highWaterMark` {integer} **Default:** `64 * 1024`
* Returns: {readline.InterfaceConstructor}

Convenience method to create a `readline` interface and stream over the file.
See [`filehandle.createReadStream()`][] for the options.

```mjs
import { open } from 'node:fs/promises';

const file = await open('./some/file/to/read');

for await (const line of file.readLines()) {
  console.log(line);
}
```

```cjs
const { open } = require('node:fs/promises');

(async () => {
  const file = await open('./some/file/to/read');

for await (const line of file.readLines()) {
    console.log(line);
  }
})();
```

#### `filehandle.readv(buffers[, position])`

<!-- YAML
added:
 - v13.13.0
 - v12.17.0
-->

* `buffers` {Buffer\[]|TypedArray\[]|DataView\[]}
* `position` {integer|null} The offset from the beginning of the file where
  the data should be read from. If `position` is not a `number`, the data will
  be read from the current position. **Default:** `null`
* Returns: {Promise} Fulfills upon success an object containing two properties:
  * `bytesRead` {integer} the number of bytes read
  * `buffers` {Buffer\[]|TypedArray\[]|DataView\[]} property containing
    a reference to the `buffers` input.

Read from a file and write to an array of {ArrayBufferView}s

#### `filehandle.stat([options])`

<!-- YAML
added: v10.0.0
changes:
  - version: REPLACEME
    pr-url: https://github.com/nodejs/node/pull/57775
    description: Now accepts an additional `signal` property to allow aborting the operation.
  - version: v10.5.0
    pr-url: https://github.com/nodejs/node/pull/20220
    description: Accepts an additional `options` object to specify whether the numeric values returned should be bigint.
-->

* `options` {Object}
  * `bigint` {boolean} Whether the numeric values in the returned {fs.Stats} object should be `bigint`. **Default:** `false`.
  * `signal` {AbortSignal} An AbortSignal to cancel the operation. **Default:** `undefined`.
* Returns: {Promise} Fulfills with an {fs.Stats} for the file.

#### `filehandle.sync()`

<!-- YAML
added: v10.0.0
-->

* Returns: {Promise} Fulfills with `undefined` upon success.

Request that all data for the open file descriptor is flushed to the storage
device. The specific implementation is operating system and device specific.
Refer to the POSIX fsync(2) documentation for more detail.

#### `filehandle.truncate(len)`

<!-- YAML
added: v10.0.0
-->

* `len` {integer} **Default:** `0`
* Returns: {Promise} Fulfills with `undefined` upon success.

Truncates the file.

If the file was larger than `len` bytes, only the first `len` bytes will be
retained in the file.

The following example retains only the first four bytes of the file:

```mjs
import { open } from 'node:fs/promises';

let filehandle = null;
try {
  filehandle = await open('temp.txt', 'r+');
  await filehandle.truncate(4);
} finally {
  await filehandle?.close();
}
```

If the file previously was shorter than `len` bytes, it is extended, and the
extended part is filled with null bytes (`'\0'`):

If `len` is negative then `0` will be used.

#### `filehandle.utimes(atime, mtime)`

<!-- YAML
added: v10.0.0
-->

* `atime` {number|string|Date}
* `mtime` {number|string|Date}
* Returns: {Promise}

Change the file system timestamps of the object referenced by the {FileHandle}
then fulfills the promise with no arguments upon success.

#### `filehandle.write(buffer, offset[, length[, position]])`

<!-- YAML
added: v10.0.0
changes:
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/31030
    description: The `buffer` parameter won't coerce unsupported input to
                 buffers anymore.
-->

* `buffer` {Buffer|TypedArray|DataView}
* `offset` {integer} The start position from within `buffer` where the data
  to write begins.
* `length` {integer} The number of bytes from `buffer` to write. **Default:**
  `buffer.byteLength - offset`
* `position` {integer|null} The offset from the beginning of the file where the
  data from `buffer` should be written. If `position` is not a `number`,
  the data will be written at the current position. See the POSIX pwrite(2)
  documentation for more detail. **Default:** `null`
* Returns: {Promise}

Write `buffer` to the file.

The promise is fulfilled with an object containing two properties:

* `bytesWritten` {integer} the number of bytes written
* `buffer` {Buffer|TypedArray|DataView} a reference to the
  `buffer` written.

It is unsafe to use `filehandle.write()` multiple times on the same file
without waiting for the promise to be fulfilled (or rejected). For this
scenario, use [`filehandle.createWriteStream()`][].
