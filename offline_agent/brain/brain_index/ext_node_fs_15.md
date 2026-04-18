# Node.js fs (15/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
github.com/nodejs/node/pull/7897
    description: The `callback` parameter is no longer optional. Not passing
                 it will emit a deprecation warning with id DEP0013.
-->

* `fd` {integer}
* `string` {string}
* `position` {integer|null} **Default:** `null`
* `encoding` {string} **Default:** `'utf8'`
* `callback` {Function}
  * `err` {Error}
  * `written` {integer}
  * `string` {string}

Write `string` to the file specified by `fd`. If `string` is not a string,
an exception is thrown.

`position` refers to the offset from the beginning of the file where this data
should be written. If `typeof position !== 'number'` the data will be written at
the current position. See pwrite(2).

`encoding` is the expected string encoding.

The callback will receive the arguments `(err, written, string)` where `written`
specifies how many _bytes_ the passed string required to be written. Bytes
written is not necessarily the same as string characters written. See
[`Buffer.byteLength`][].

It is unsafe to use `fs.write()` multiple times on the same file without waiting
for the callback. For this scenario, [`fs.createWriteStream()`][] is
recommended.

On Linux, positional writes don't work when the file is opened in append mode.
The kernel ignores the position argument and always appends the data to
the end of the file.

On Windows, if the file descriptor is connected to the console (e.g. `fd == 1`
or `stdout`) a string containing non-ASCII characters will not be rendered
properly by default, regardless of the encoding used.
It is possible to configure the console to render UTF-8 properly by changing the
active codepage with the `chcp 65001` command. See the [chcp][] docs for more
details.

### `fs.writeFile(file, data[, options], callback)`

<!-- YAML
added: v0.1.29
changes:
  - version:
    - v21.0.0
    - v20.10.0
    pr-url: https://github.com/nodejs/node/pull/50009
    description: The `flush` option is now supported.
  - version: v19.0.0
    pr-url: https://github.com/nodejs/node/pull/42796
    description: Passing to the `string` parameter an object with an own
                 `toString` function is no longer supported.
  - version: v18.0.0
    pr-url: https://github.com/nodejs/node/pull/41678
    description: Passing an invalid callback to the `callback` argument
                 now throws `ERR_INVALID_ARG_TYPE` instead of
                 `ERR_INVALID_CALLBACK`.
  - version: v17.8.0
    pr-url: https://github.com/nodejs/node/pull/42149
    description: Passing to the `string` parameter an object with an own
                 `toString` function is deprecated.
  - version: v16.0.0
    pr-url: https://github.com/nodejs/node/pull/37460
    description: The error returned may be an `AggregateError` if more than one
                 error is returned.
  - version:
      - v15.2.0
      - v14.17.0
    pr-url: https://github.com/nodejs/node/pull/35993
    description: The options argument may include an AbortSignal to abort an
                 ongoing writeFile request.
  - version: v14.12.0
    pr-url: https://github.com/nodejs/node/pull/34993
    description: The `data` parameter will stringify an object with an
                 explicit `toString` function.
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/31030
    description: The `data` parameter won't coerce unsupported input to
                 strings anymore.
  - version: v10.10.0
    pr-url: https://github.com/nodejs/node/pull/22150
    description: The `data` parameter can now be any `TypedArray` or a
                 `DataView`.
  - version: v10.0.0
    pr-url: https://github.com/nodejs/node/pull/12562
    description: The `callback` parameter is no longer optional. Not passing
                 it will throw a `TypeError` at runtime.
  - version: v7.4.0
    pr-url: https://github.com/nodejs/node/pull/10382
    description: The `data` parameter can now be a `Uint8Array`.
  - version: v7.0.0
    pr-url: https://github.com/nodejs/node/pull/7897
    description: The `callback` parameter is no longer optional. Not passing
                 it will emit a deprecation warning with id DEP0013.
  - version: v5.0.0
    pr-url: https://github.com/nodejs/node/pull/3163
    description: The `file` parameter can be a file descriptor now.
-->

* `file` {string|Buffer|URL|integer} filename or file descriptor
* `data` {string|Buffer|TypedArray|DataView}
* `options` {Object|string}
  * `encoding` {string|null} **Default:** `'utf8'`
  * `mode` {integer} **Default:** `0o666`
  * `flag` {string} See [support of file system `flags`][]. **Default:** `'w'`.
  * `flush` {boolean} If all data is successfully written to the file, and
    `flush` is `true`, `fs.fsync()` is used to flush the data.
    **Default:** `false`.
  * `signal` {AbortSignal} allows aborting an in-progress writeFile
* `callback` {Function}
  * `err` {Error|AggregateError}

When `file` is a filename, asynchronously writes data to the file, replacing the
file if it already exists. `data` can be a string or a buffer.

When `file` is a file descriptor, the behavior is similar to calling
`fs.write()` directly (which is recommended). See the notes below on using
a file descriptor.

The `encoding` option is ignored if `data` is a buffer.

The `mode` option only affects the newly created file. See [`fs.open()`][]
for more details.

```mjs
import { writeFile } from 'node:fs';
import { Buffer } from 'node:buffer';

const data = new Uint8Array(Buffer.from('Hello Node.js'));
writeFile('message.txt', data, (err) => {
  if (err) throw err;
  console.log('The file has been saved!');
});
```

If `options` is a string, then it specifies the encoding:

```mjs
import { writeFile } from 'node:fs';

writeFile('message.txt', 'Hello Node.js', 'utf8', callback);
```

It is unsafe to use `fs.writeFile()` multiple times on the same file without
waiting for the callback. For this scenario, [`fs.createWriteStream()`][] is
recommended.

Similarly to `fs.readFile` - `fs.writeFile` is a convenience method that
performs multiple `write` calls internally to write the buffer passed to it.
For performance sensitive code consider using [`fs.createWriteStream()`][].

It is possible to use an {AbortSignal} to cancel an `fs.writeFile()`.
Cancelation is "best effort", and some amount of data is likely still
to be written.

```mjs
import { writeFile } from 'node:fs';
import { Buffer } from 'node:buffer';

const controller = new AbortController();
const { signal } = controller;
const data = new Uint8Array(Buffer.from('Hello Node.js'));
writeFile('message.txt', data, { signal }, (err) => {
  // When a request is aborted - the callback is called with an AbortError
});
// When the request should be aborted
controller.abort();
```

Aborting an ongoing request does not abort individual operating
system requests but rather the internal buffering `fs.writeFile` performs.

#### Using `fs.writeFile()` with file descriptors

When `file` is a file descriptor, the behavior is almost identical to directly
calling `fs.write()` like:

```mjs
import { write } from 'node:fs';
import { Buffer } from 'node:buffer';

write(fd, Buffer.from(data, options.encoding), callback);
```

The difference from directly calling `fs.write()` is that under some unusual
conditions, `fs.write()` might write only part of the buffer and need to be
retried to write the remaining data, whereas `fs.writeFile()` retries until
the data is entirely written (or an error occurs).

The implications of this are a common source of confusion. In
the file descriptor case, the file is not replaced! The data is not necessarily
written to the beginning of the file, and the file's original data may remain
before and/or after the newly written data.

For example, if `fs.writeFile()` is called twice in a row, first to write the
string `'Hello'`, then to write the string `', World'`, the file would contain
`'Hello, World'`, and might contain some of the file's original data (depending
on the size of the original file, and the position of the file descriptor). If
a file name had been used instead of a descriptor, the file would be guaranteed
to contain only `', World'`.

### `fs.writev(fd, buffers[, position], callback)`

<!-- YAML
added: v12.9.0
changes:
  - version: v18.0.0
    pr-url: https://github.com/nodejs/node/pull/41678
    description: Passing an invalid callback to the `callback` argument
                 now throws `ERR_INVALID_ARG_TYPE` instead of
                 `ERR_INVALID_CALLBACK`.
-->

* `fd` {integer}
* `buffers` {ArrayBufferView\[]}
* `position` {integer|null} **Default:** `null`
* `callback` {Function}
  * `err` {Error}
  * `bytesWritten` {integer}
  * `buffers` {ArrayBufferView\[]}

Write an array of `ArrayBufferView`s to the file specified by `fd` using
`writev()`.

`position` is the offset from the beginning of the file where this data
should be written. If `typeof position !== 'number'`, the data will be written
at the current position.

The callback will be given three arguments: `err`, `bytesWritten`, and
`buffers`. `bytesWritten` is how many bytes were written from `buffers`.

If this method is [`util.promisify()`][]ed, it returns a promise for an
`Object` with `bytesWritten` and `buffers` properties.

It is unsafe to use `fs.writev()` multiple times on the same file without
waiting for the callback. For this scenario, use [`fs.createWriteStream()`][].

On Linux, positional writes don't work when the file is opened in append mode.
The kernel ignores the position argument and always appends the data to
the end of the file.

## Synchronous API

The synchronous APIs perform all operations synchronously, blocking the
event loop until the operation completes or fails.

### `fs.accessSync(path[, mode])`

<!-- YAML
added: v0.11.15
changes:
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
-->

* `path` {string|Buffer|URL}
* `mode` {integer} **Default:** `fs.constants.F_OK`

Synchronously tests a user's permissions for the file or directory specified
by `path`. The `mode` argument is an optional integer that specifies the
accessibility checks to be performed. `mode` should be either the value
`fs.constants.F_OK` or a mask consisting of the bitwise OR of any of
`fs.constants.R_OK`, `fs.constants.W_OK`, and `fs.constants.X_OK` (e.g.
`fs.constants.W_OK | fs.constants.R_OK`). Check [File access constants][] for
possible values of `mode`.

If any of the accessibility checks fail, an `Error` will be thrown. Otherwise,
the method will return `undefined`.

```mjs
import { accessSync, constants } from 'node:fs';

try {
  accessSync('etc/passwd', constants.R_OK | constants.W_OK);
  console.log('can read/write');
} catch (err) {
  console.error('no access!');
}
```

### `fs.appendFileSync(path, data[, options])`

<!-- YAML
added: v0.6.7
changes:
  - version:
    - v21.1.0
    - v20.10.0
    pr-url: https://github.com/nodejs/node/pull/50095
    description: The `flush` option is now supported.
  - version: v7.0.0
    pr-url: https://github.com/nodejs/node/pull/7831
    description: The passed `options` object will never be modified.
  - version: v5.0.0
    pr-url: https://github.com/nodejs/node/pull/3163
    description: The `file` parameter can be a file descriptor now.
-->

* `path` {string|Buffer|URL|number} filename or file descriptor
* `data` {string|Buffer}
* `options` {Object|string}
  * `encoding` {string|null} **Default:** `'utf8'`
  * `mode` {integer} **Default:** `0o666`
  * `flag` {string} See [support of file system `flags`][]. **Default:** `'a'`.
  * `flush` {boolean} If `true`, the underlying file descriptor is flushed
    prior to closing it. **Default:** `false`.

Synchronously append data to a file, creating the file if it does not yet
exist. `data` can be a string or a {Buffer}.

The `mode` option only affects the newly created file. See [`fs.open()`][]
for more details.

```mjs
import { appendFileSync } from 'node:fs';

try {
  appendFileSync('message.txt', 'data to append');
  console.log('The "data to append" was appended to file!');
} catch (err) {
  /* Handle the error */
}
```

If `options` is a string, then it specifies the encoding:

```mjs
import { appendFileSync } from 'node:fs';

appendFileSync('message.txt', 'data to append', 'utf8');
```

The `path` may be specified as a numeric file descriptor that has been opened
for appending (using `fs.open()` or `fs.openSync()`). The file descriptor will
not be closed automatically.

```mjs
import { openSync, closeSync, appendFileSync } from 'node:fs';

let fd;

try {
  fd = openSync('message.txt', 'a');
  appendFileSync(fd, 'data to append', 'utf8');
} catch (err) {
  /* Handle the error */
} finally {
  if (fd !== undefined)
    closeSync(fd);
}
```

### `fs.chmodSync(path, mode)`

<!-- YAML
added: v0.6.7
changes:
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
-->

* `path` {string|Buffer|URL}
* `mode` {string|integer}

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.chmod()`][].

See the POSIX chmod(2) documentation for more detail.

### `fs.chownSync(path, uid, gid)`

<!-- YAML
added: v0.1.97
changes:
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
-->

* `path` {string|Buffer|URL}
* `uid` {integer}
* `gid` {integer}

Synchronously changes owner and group of a file. Returns `undefined`.
This is the synchronous version of [`fs.chown()`][].

See the POSIX chown(2) documentation for more detail.

### `fs.closeSync(fd)`

<!-- YAML
added: v0.1.21
-->

* `fd` {integer}

Closes the file descriptor. Returns `undefined`.
