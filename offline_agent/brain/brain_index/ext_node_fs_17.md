# Node.js fs (17/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
s version of [`fs.mkdir()`][].

See the POSIX mkdir(2) documentation for more details.

### `fs.mkdtempSync(prefix[, options])`

<!-- YAML
added: v5.10.0
changes:
  - version:
    - v20.6.0
    - v18.19.0
    pr-url: https://github.com/nodejs/node/pull/48828
    description: The `prefix` parameter now accepts buffers and URL.
  - version:
      - v16.5.0
      - v14.18.0
    pr-url: https://github.com/nodejs/node/pull/39028
    description: The `prefix` parameter now accepts an empty string.
-->

* `prefix` {string|Buffer|URL}
* `options` {string|Object}
  * `encoding` {string} **Default:** `'utf8'`
* Returns: {string}

Returns the created directory path.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.mkdtemp()`][].

The optional `options` argument can be a string specifying an encoding, or an
object with an `encoding` property specifying the character encoding to use.

### `fs.mkdtempDisposableSync(prefix[, options])`

<!-- YAML
added: v24.4.0
-->

* `prefix` {string|Buffer|URL}
* `options` {string|Object}
  * `encoding` {string} **Default:** `'utf8'`
* Returns: {Object} A disposable object:
  * `path` {string} The path of the created directory.
  * `remove` {Function} A function which removes the created directory.
  * `[Symbol.dispose]` {Function} The same as `remove`.

Returns a disposable object whose `path` property holds the created directory
path. When the object is disposed, the directory and its contents will be
removed if it still exists. If the directory cannot be deleted, disposal will
throw an error. The object has a `remove()` method which will perform the same
task.

<!-- TODO: link MDN docs for disposables once https://github.com/mdn/content/pull/38027 lands -->

For detailed information, see the documentation of [`fs.mkdtemp()`][].

There is no callback-based version of this API because it is designed for use
with the `using` syntax.

The optional `options` argument can be a string specifying an encoding, or an
object with an `encoding` property specifying the character encoding to use.

### `fs.opendirSync(path[, options])`

<!-- YAML
added: v12.12.0
changes:
  - version:
    - v20.1.0
    - v18.17.0
    pr-url: https://github.com/nodejs/node/pull/41439
    description: Added `recursive` option.
  - version:
     - v13.1.0
     - v12.16.0
    pr-url: https://github.com/nodejs/node/pull/30114
    description: The `bufferSize` option was introduced.
-->

* `path` {string|Buffer|URL}
* `options` {Object}
  * `encoding` {string|null} **Default:** `'utf8'`
  * `bufferSize` {number} Number of directory entries that are buffered
    internally when reading from the directory. Higher values lead to better
    performance but higher memory usage. **Default:** `32`
  * `recursive` {boolean} **Default:** `false`
* Returns: {fs.Dir}

Synchronously open a directory. See opendir(3).

Creates an {fs.Dir}, which contains all further functions for reading from
and cleaning up the directory.

The `encoding` option sets the encoding for the `path` while opening the
directory and subsequent read operations.

### `fs.openSync(path[, flags[, mode]])`

<!-- YAML
added: v0.1.21
changes:
  - version: v11.1.0
    pr-url: https://github.com/nodejs/node/pull/23767
    description: The `flags` argument is now optional and defaults to `'r'`.
  - version: v9.9.0
    pr-url: https://github.com/nodejs/node/pull/18801
    description: The `as` and `as+` flags are supported now.
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
-->

* `path` {string|Buffer|URL}
* `flags` {string|number} **Default:** `'r'`.
  See [support of file system `flags`][].
* `mode` {string|integer} **Default:** `0o666`
* Returns: {number}

Returns an integer representing the file descriptor.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.open()`][].

### `fs.readdirSync(path[, options])`

<!-- YAML
added: v0.1.21
changes:
  - version:
    - v20.1.0
    - v18.17.0
    pr-url: https://github.com/nodejs/node/pull/41439
    description: Added `recursive` option.
  - version: v10.10.0
    pr-url: https://github.com/nodejs/node/pull/22020
    description: New option `withFileTypes` was added.
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
-->

* `path` {string|Buffer|URL}
* `options` {string|Object}
  * `encoding` {string} **Default:** `'utf8'`
  * `withFileTypes` {boolean} **Default:** `false`
  * `recursive` {boolean} If `true`, reads the contents of a directory
    recursively. In recursive mode, it will list all files, sub files, and
    directories. **Default:** `false`.
* Returns: {string\[]|Buffer\[]|fs.Dirent\[]}

Reads the contents of the directory.

See the POSIX readdir(3) documentation for more details.

The optional `options` argument can be a string specifying an encoding, or an
object with an `encoding` property specifying the character encoding to use for
the filenames returned. If the `encoding` is set to `'buffer'`,
the filenames returned will be passed as {Buffer} objects.

If `options.withFileTypes` is set to `true`, the result will contain
{fs.Dirent} objects.

### `fs.readFileSync(path[, options])`

<!-- YAML
added: v0.1.8
changes:
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
  - version: v5.0.0
    pr-url: https://github.com/nodejs/node/pull/3163
    description: The `path` parameter can be a file descriptor now.
-->

* `path` {string|Buffer|URL|integer} filename or file descriptor
* `options` {Object|string}
  * `encoding` {string|null} **Default:** `null`
  * `flag` {string} See [support of file system `flags`][]. **Default:** `'r'`.
* Returns: {string|Buffer}

Returns the contents of the `path`.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.readFile()`][].

If the `encoding` option is specified then this function returns a
string. Otherwise it returns a buffer.

Similar to [`fs.readFile()`][], when the path is a directory, the behavior of
`fs.readFileSync()` is platform-specific.

```mjs
import { readFileSync } from 'node:fs';

// macOS, Linux, and Windows
readFileSync('<directory>');
// => [Error: EISDIR: illegal operation on a directory, read <directory>]

//  FreeBSD
readFileSync('<directory>'); // => <data>
```

### `fs.readlinkSync(path[, options])`

<!-- YAML
added: v0.1.31
changes:
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
-->

* `path` {string|Buffer|URL}
* `options` {string|Object}
  * `encoding` {string} **Default:** `'utf8'`
* Returns: {string|Buffer}

Returns the symbolic link's string value.

See the POSIX readlink(2) documentation for more details.

The optional `options` argument can be a string specifying an encoding, or an
object with an `encoding` property specifying the character encoding to use for
the link path returned. If the `encoding` is set to `'buffer'`,
the link path returned will be passed as a {Buffer} object.

### `fs.readSync(fd, buffer, offset, length[, position])`

<!-- YAML
added: v0.1.21
changes:
  - version: v10.10.0
    pr-url: https://github.com/nodejs/node/pull/22150
    description: The `buffer` parameter can now be any `TypedArray` or a
                 `DataView`.
  - version: v6.0.0
    pr-url: https://github.com/nodejs/node/pull/4518
    description: The `length` parameter can now be `0`.
-->

* `fd` {integer}
* `buffer` {Buffer|TypedArray|DataView}
* `offset` {integer}
* `length` {integer}
* `position` {integer|bigint|null} **Default:** `null`
* Returns: {number}

Returns the number of `bytesRead`.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.read()`][].

### `fs.readSync(fd, buffer[, options])`

<!-- YAML
added:
 - v13.13.0
 - v12.17.0
changes:
  - version:
     - v13.13.0
     - v12.17.0
    pr-url: https://github.com/nodejs/node/pull/32460
    description: Options object can be passed in
                 to make offset, length, and position optional.
-->

* `fd` {integer}
* `buffer` {Buffer|TypedArray|DataView}
* `options` {Object}
  * `offset` {integer} **Default:** `0`
  * `length` {integer} **Default:** `buffer.byteLength - offset`
  * `position` {integer|bigint|null} **Default:** `null`
* Returns: {number}

Returns the number of `bytesRead`.

Similar to the above `fs.readSync` function, this version takes an optional `options` object.
If no `options` object is specified, it will default with the above values.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.read()`][].

### `fs.readvSync(fd, buffers[, position])`

<!-- YAML
added:
 - v13.13.0
 - v12.17.0
-->

* `fd` {integer}
* `buffers` {ArrayBufferView\[]}
* `position` {integer|null} **Default:** `null`
* Returns: {number} The number of bytes read.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.readv()`][].

### `fs.realpathSync(path[, options])`

<!-- YAML
added: v0.1.31
changes:
  - version: v8.0.0
    pr-url: https://github.com/nodejs/node/pull/13028
    description: Pipe/Socket resolve support was added.
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using
                 `file:` protocol.
  - version: v6.4.0
    pr-url: https://github.com/nodejs/node/pull/7899
    description: Calling `realpathSync` now works again for various edge cases
                 on Windows.
  - version: v6.0.0
    pr-url: https://github.com/nodejs/node/pull/3594
    description: The `cache` parameter was removed.
-->

* `path` {string|Buffer|URL}
* `options` {string|Object}
  * `encoding` {string} **Default:** `'utf8'`
* Returns: {string|Buffer}

Returns the resolved pathname.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.realpath()`][].

### `fs.realpathSync.native(path[, options])`

<!-- YAML
added: v9.2.0
-->

* `path` {string|Buffer|URL}
* `options` {string|Object}
  * `encoding` {string} **Default:** `'utf8'`
* Returns: {string|Buffer}

Synchronous realpath(3).

Only paths that can be converted to UTF8 strings are supported.

The optional `options` argument can be a string specifying an encoding, or an
object with an `encoding` property specifying the character encoding to use for
the path returned. If the `encoding` is set to `'buffer'`,
the path returned will be passed as a {Buffer} object.

On Linux, when Node.js is linked against musl libc, the procfs file system must
be mounted on `/proc` in order for this function to work. Glibc does not have
this restriction.

### `fs.renameSync(oldPath, newPath)`

<!-- YAML
added: v0.1.21
changes:
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `oldPath` and `newPath` parameters can be WHATWG `URL`
                 objects using `file:` protocol. Support is currently still
                 *experimental*.
-->

* `oldPath` {string|Buffer|URL}
* `newPath` {string|Buffer|URL}

Renames the file from `oldPath` to `newPath`. Returns `undefined`.

See the POSIX rename(2) documentation for more details.

### `fs.rmdirSync(path[, options])`

<!-- YAML
added: v0.1.21
changes:
  - version: v25.0.0
    pr-url: https://github.com/nodejs/node/pull/58616
    description: Remove `recursive` option.
  - version: v16.0.0
    pr-url: https://github.com/nodejs/node/pull/37216
    description: "Using `fs.rmdirSync(path, { recursive: true })` on a `path`
                 that is a file is no longer permitted and results in an
                 `ENOENT` error on Windows and an `ENOTDIR` error on POSIX."
  - version: v16.0.0
    pr-url: https://github.com/nodejs/node/pull/37216
    description: "Using `fs.rmdirSync(path, { recursive: true })` on a `path`
                 that does not exist is no longer permitted and results in a
                 `ENOENT` error."
  - version: v16.0.0
    pr-url: https://github.com/nodejs/node/pull/37302
    description: The `recursive` option is deprecated, using it triggers a
                 deprecation warning.
  - version: v14.14.0
    pr-url: https://github.com/nodejs/node/pull/35579
    description: The `recursive` option is deprecated, use `fs.rmSync` instead.
  - version:
     - v13.3.0
     - v12.16.0
    pr-url: https://github.com/nodejs/node/pull/30644
    description: The `maxBusyTries` option is renamed to `maxRetries`, and its
                 default is 0. The `emfileWait` option has been removed, and
                 `EMFILE` errors use the same retry logic as other errors. The
                 `retryDelay` option is now supported. `ENFILE` errors are now
                 retried.
  - version: v12.10.0
    pr-url: https://github.com/nodejs/node/pull/29168
    description: The `recursive`, `maxBusyTries`, and `emfileWait` options are
                 now supported.
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameters can be a WHATWG `URL` object using
                 `file:` protocol.
-->

* `path` {string|Buffer|URL}
* `options` {Object} There are currently no options exposed. There used to
  be options for `recursive`, `maxBusyTries`, and `emfileWait` but they were
  deprecated and removed. The `options` argument is still accepted for
  backwards compatibility but it is not used.

Synchronous rmdir(2). Returns `undefined`.
