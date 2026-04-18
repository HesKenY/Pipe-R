# Node.js fs (18/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
l: https://github.com/nodejs/node/pull/10739
    description: The `path` parameters can be a WHATWG `URL` object using
                 `file:` protocol.
-->

* `path` {string|Buffer|URL}
* `options` {Object} There are currently no options exposed. There used to
  be options for `recursive`, `maxBusyTries`, and `emfileWait` but they were
  deprecated and removed. The `options` argument is still accepted for
  backwards compatibility but it is not used.

Synchronous rmdir(2). Returns `undefined`.

Using `fs.rmdirSync()` on a file (not a directory) results in an `ENOENT` error
on Windows and an `ENOTDIR` error on POSIX.

To get a behavior similar to the `rm -rf` Unix command, use [`fs.rmSync()`][]
with options `{ recursive: true, force: true }`.

### `fs.rmSync(path[, options])`

<!-- YAML
added: v14.14.0
changes:
  - version:
      - v17.3.0
      - v16.14.0
    pr-url: https://github.com/nodejs/node/pull/41132
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
-->

* `path` {string|Buffer|URL}
* `options` {Object}
  * `force` {boolean} When `true`, exceptions will be ignored if `path` does
    not exist. **Default:** `false`.
  * `maxRetries` {integer} If an `EBUSY`, `EMFILE`, `ENFILE`, `ENOTEMPTY`, or
    `EPERM` error is encountered, Node.js will retry the operation with a linear
    backoff wait of `retryDelay` milliseconds longer on each try. This option
    represents the number of retries. This option is ignored if the `recursive`
    option is not `true`. **Default:** `0`.
  * `recursive` {boolean} If `true`, perform a recursive directory removal. In
    recursive mode operations are retried on failure. **Default:** `false`.
  * `retryDelay` {integer} The amount of time in milliseconds to wait between
    retries. This option is ignored if the `recursive` option is not `true`.
    **Default:** `100`.

Synchronously removes files and directories (modeled on the standard POSIX `rm`
utility). Returns `undefined`.

### `fs.statSync(path[, options])`

<!-- YAML
added: v0.1.21
changes:
  - version:
    - v15.3.0
    - v14.17.0
    pr-url: https://github.com/nodejs/node/pull/33716
    description: Accepts a `throwIfNoEntry` option to specify whether
                 an exception should be thrown if the entry does not exist.
  - version: v10.5.0
    pr-url: https://github.com/nodejs/node/pull/20220
    description: Accepts an additional `options` object to specify whether
                 the numeric values returned should be bigint.
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
-->

* `path` {string|Buffer|URL}
* `options` {Object}
  * `bigint` {boolean} Whether the numeric values in the returned
    {fs.Stats} object should be `bigint`. **Default:** `false`.
  * `throwIfNoEntry` {boolean} Whether an exception will be thrown
    if no file system entry exists, rather than returning `undefined`.
    **Default:** `true`.
* Returns: {fs.Stats}

Retrieves the {fs.Stats} for the path.

### `fs.statfsSync(path[, options])`

<!-- YAML
added:
  - v19.6.0
  - v18.15.0
-->

* `path` {string|Buffer|URL}
* `options` {Object}
  * `bigint` {boolean} Whether the numeric values in the returned
    {fs.StatFs} object should be `bigint`. **Default:** `false`.
* Returns: {fs.StatFs}

Synchronous statfs(2). Returns information about the mounted file system which
contains `path`.

In case of an error, the `err.code` will be one of [Common System Errors][].

### `fs.symlinkSync(target, path[, type])`

<!-- YAML
added: v0.1.31
changes:
  - version: v12.0.0
    pr-url: https://github.com/nodejs/node/pull/23724
    description: If the `type` argument is left undefined, Node will autodetect
                 `target` type and automatically select `dir` or `file`.
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `target` and `path` parameters can be WHATWG `URL` objects
                 using `file:` protocol. Support is currently still
                 *experimental*.
-->

* `target` {string|Buffer|URL}
* `path` {string|Buffer|URL}
* `type` {string|null} **Default:** `null`
* Returns: `undefined`.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.symlink()`][].

### `fs.truncateSync(path[, len])`

<!-- YAML
added: v0.8.6
-->

* `path` {string|Buffer|URL}
* `len` {integer} **Default:** `0`

Truncates the file. Returns `undefined`. A file descriptor can also be
passed as the first argument. In this case, `fs.ftruncateSync()` is called.

Passing a file descriptor is deprecated and may result in an error being thrown
in the future.

### `fs.unlinkSync(path)`

<!-- YAML
added: v0.1.21
changes:
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
-->

* `path` {string|Buffer|URL}

Synchronous unlink(2). Returns `undefined`.

### `fs.utimesSync(path, atime, mtime)`

<!-- YAML
added: v0.4.2
changes:
  - version: v8.0.0
    pr-url: https://github.com/nodejs/node/pull/11919
    description: "`NaN`, `Infinity`, and `-Infinity` are no longer valid time
                 specifiers."
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
  - version: v4.1.0
    pr-url: https://github.com/nodejs/node/pull/2387
    description: Numeric strings, `NaN`, and `Infinity` are now allowed
                 time specifiers.
-->

* `path` {string|Buffer|URL}
* `atime` {number|string|Date}
* `mtime` {number|string|Date}
* Returns: `undefined`.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.utimes()`][].

### `fs.writeFileSync(file, data[, options])`

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
    description: Passing to the `data` parameter an object with an own
                 `toString` function is no longer supported.
  - version: v17.8.0
    pr-url: https://github.com/nodejs/node/pull/42149
    description: Passing to the `data` parameter an object with an own
                 `toString` function is deprecated.
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
  - version: v7.4.0
    pr-url: https://github.com/nodejs/node/pull/10382
    description: The `data` parameter can now be a `Uint8Array`.
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
    `flush` is `true`, `fs.fsyncSync()` is used to flush the data.
* Returns: `undefined`.

The `mode` option only affects the newly created file. See [`fs.open()`][]
for more details.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.writeFile()`][].

### `fs.writeSync(fd, buffer, offset[, length[, position]])`

<!-- YAML
added: v0.1.21
changes:
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/31030
    description: The `buffer` parameter won't coerce unsupported input to
                 strings anymore.
  - version: v10.10.0
    pr-url: https://github.com/nodejs/node/pull/22150
    description: The `buffer` parameter can now be any `TypedArray` or a
                 `DataView`.
  - version: v7.4.0
    pr-url: https://github.com/nodejs/node/pull/10382
    description: The `buffer` parameter can now be a `Uint8Array`.
  - version: v7.2.0
    pr-url: https://github.com/nodejs/node/pull/7856
    description: The `offset` and `length` parameters are optional now.
-->

* `fd` {integer}
* `buffer` {Buffer|TypedArray|DataView}
* `offset` {integer} **Default:** `0`
* `length` {integer} **Default:** `buffer.byteLength - offset`
* `position` {integer|null} **Default:** `null`
* Returns: {number} The number of bytes written.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.write(fd, buffer...)`][].

### `fs.writeSync(fd, buffer[, options])`

<!-- YAML
added:
  - v18.3.0
  - v16.17.0
-->

* `fd` {integer}
* `buffer` {Buffer|TypedArray|DataView}
* `options` {Object}
  * `offset` {integer} **Default:** `0`
  * `length` {integer} **Default:** `buffer.byteLength - offset`
  * `position` {integer|null} **Default:** `null`
* Returns: {number} The number of bytes written.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.write(fd, buffer...)`][].

### `fs.writeSync(fd, string[, position[, encoding]])`

<!-- YAML
added: v0.11.5
changes:
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/31030
    description: The `string` parameter won't coerce unsupported input to
                 strings anymore.
  - version: v7.2.0
    pr-url: https://github.com/nodejs/node/pull/7856
    description: The `position` parameter is optional now.
-->

* `fd` {integer}
* `string` {string}
* `position` {integer|null} **Default:** `null`
* `encoding` {string} **Default:** `'utf8'`
* Returns: {number} The number of bytes written.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.write(fd, string...)`][].

### `fs.writevSync(fd, buffers[, position])`

<!-- YAML
added: v12.9.0
-->

* `fd` {integer}
* `buffers` {ArrayBufferView\[]}
* `position` {integer|null} **Default:** `null`
* Returns: {number} The number of bytes written.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.writev()`][].

## Common Objects

The common objects are shared by all of the file system API variants
(promise, callback, and synchronous).

### Class: `fs.Dir`

<!-- YAML
added: v12.12.0
-->

A class representing a directory stream.

Created by [`fs.opendir()`][], [`fs.opendirSync()`][], or
[`fsPromises.opendir()`][].

```mjs
import { opendir } from 'node:fs/promises';

try {
  const dir = await opendir('./');
  for await (const dirent of dir)
    console.log(dirent.name);
} catch (err) {
  console.error(err);
}
```

When using the async iterator, the {fs.Dir} object will be automatically
closed after the iterator exits.

#### `dir.close()`

<!-- YAML
added: v12.12.0
-->

* Returns: {Promise}

Asynchronously close the directory's underlying resource handle.
Subsequent reads will result in errors.

A promise is returned that will be fulfilled after the resource has been
closed.

#### `dir.close(callback)`

<!-- YAML
added: v12.12.0
changes:
  - version: v18.0.0
    pr-url: https://github.com/nodejs/node/pull/41678
    description: Passing an invalid callback to the `callback` argument
                 now throws `ERR_INVALID_ARG_TYPE` instead of
                 `ERR_INVALID_CALLBACK`.
-->

* `callback` {Function}
  * `err` {Error}

Asynchronously close the directory's underlying resource handle.
Subsequent reads will result in errors.

The `callback` will be called after the resource handle has been closed.

#### `dir.closeSync()`

<!-- YAML
added: v12.12.0
-->

Synchronously close the directory's underlying resource handle.
Subsequent reads will result in errors.

#### `dir.path`

<!-- YAML
added: v12.12.0
-->

* Type: {string}

The read-only path of this directory as was provided to [`fs.opendir()`][],
[`fs.opendirSync()`][], or [`fsPromises.opendir()`][].

#### `dir.read()`

<!-- YAML
added: v12.12.0
-->

* Returns: {Promise} Fulfills with a {fs.Dirent|null}

Asynchronously read the next directory entry via readdir(3) as an
{fs.Dirent}.

A promise is returned that will be fulfilled with an {fs.Dirent}, or `null`
if there are no more directory entries to read.

Directory entries returned by this function are in no particular order as
provided by the operating system's underlying directory mechanisms.
Entries added or removed while iterating over the directory might not be
included in the iteration results.

#### `dir.read(callback)`

<!-- YAML
added: v12.12.0
-->

* `callback` {Function}
  * `err` {Error}
  * `dirent` {fs.Dirent|null}

Asynchronously read the next directory entry via readdir(3) as an
{fs.Dirent}.

After the read is completed, the `callback` will be called with an
{fs.Dirent}, or `null` if there are no more directory entries to read.

Directory entries returned by this function are in no particular order as
provided by the operating system's underlying directory mechanisms.
Entries added or removed while iterating over the directory might not be
included in the iteration results.

#### `dir.readSync()`

<!-- YAML
added: v12.12.0
-->

* Returns: {fs.Dirent|null}

Synchronously read the next directory entry as an {fs.Dirent}. See the
POSIX readdir(3) documentation for more detail.

If there are no more directory entries to read, `null` will be returned.
