# Node.js fs (16/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
odejs/node/pull/10739
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

Calling `fs.closeSync()` on any file descriptor (`fd`) that is currently in use
through any other `fs` operation may lead to undefined behavior.

See the POSIX close(2) documentation for more detail.

### `fs.copyFileSync(src, dest[, mode])`

<!-- YAML
added: v8.5.0
changes:
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/27044
    description: Changed `flags` argument to `mode` and imposed
                 stricter type validation.
-->

* `src` {string|Buffer|URL} source filename to copy
* `dest` {string|Buffer|URL} destination filename of the copy operation
* `mode` {integer} modifiers for copy operation. **Default:** `0`.

Synchronously copies `src` to `dest`. By default, `dest` is overwritten if it
already exists. Returns `undefined`. Node.js makes no guarantees about the
atomicity of the copy operation. If an error occurs after the destination file
has been opened for writing, Node.js will attempt to remove the destination.

`mode` is an optional integer that specifies the behavior
of the copy operation. It is possible to create a mask consisting of the bitwise
OR of two or more values (e.g.
`fs.constants.COPYFILE_EXCL | fs.constants.COPYFILE_FICLONE`).

* `fs.constants.COPYFILE_EXCL`: The copy operation will fail if `dest` already
  exists.
* `fs.constants.COPYFILE_FICLONE`: The copy operation will attempt to create a
  copy-on-write reflink. If the platform does not support copy-on-write, then a
  fallback copy mechanism is used.
* `fs.constants.COPYFILE_FICLONE_FORCE`: The copy operation will attempt to
  create a copy-on-write reflink. If the platform does not support
  copy-on-write, then the operation will fail.

```mjs
import { copyFileSync, constants } from 'node:fs';

// destination.txt will be created or overwritten by default.
copyFileSync('source.txt', 'destination.txt');
console.log('source.txt was copied to destination.txt');

// By using COPYFILE_EXCL, the operation will fail if destination.txt exists.
copyFileSync('source.txt', 'destination.txt', constants.COPYFILE_EXCL);
```

### `fs.cpSync(src, dest[, options])`

<!-- YAML
added: v16.7.0
changes:
  - version: v22.3.0
    pr-url: https://github.com/nodejs/node/pull/53127
    description: This API is no longer experimental.
  - version:
    - v20.1.0
    - v18.17.0
    pr-url: https://github.com/nodejs/node/pull/47084
    description: Accept an additional `mode` option to specify
                 the copy behavior as the `mode` argument of `fs.copyFile()`.
  - version:
    - v17.6.0
    - v16.15.0
    pr-url: https://github.com/nodejs/node/pull/41819
    description: Accepts an additional `verbatimSymlinks` option to specify
                 whether to perform path resolution for symlinks.
-->

* `src` {string|URL} source path to copy.
* `dest` {string|URL} destination path to copy to.
* `options` {Object}
  * `dereference` {boolean} dereference symlinks. **Default:** `false`.
  * `errorOnExist` {boolean} when `force` is `false`, and the destination
    exists, throw an error. **Default:** `false`.
  * `filter` {Function} Function to filter copied files/directories. Return
    `true` to copy the item, `false` to ignore it. When ignoring a directory,
    all of its contents will be skipped as well. **Default:** `undefined`
    * `src` {string} source path to copy.
    * `dest` {string} destination path to copy to.
    * Returns: {boolean} Any non-`Promise` value that is coercible
      to `boolean`.
  * `force` {boolean} overwrite existing file or directory. The copy
    operation will ignore errors if you set this to false and the destination
    exists. Use the `errorOnExist` option to change this behavior.
    **Default:** `true`.
  * `mode` {integer} modifiers for copy operation. **Default:** `0`.
    See `mode` flag of [`fs.copyFileSync()`][].
  * `preserveTimestamps` {boolean} When `true` timestamps from `src` will
    be preserved. **Default:** `false`.
  * `recursive` {boolean} copy directories recursively **Default:** `false`
  * `verbatimSymlinks` {boolean} When `true`, path resolution for symlinks will
    be skipped. **Default:** `false`

Synchronously copies the entire directory structure from `src` to `dest`,
including subdirectories and files.

When copying a directory to another directory, globs are not supported and
behavior is similar to `cp dir1/ dir2/`.

### `fs.existsSync(path)`

<!-- YAML
added: v0.1.21
changes:
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using
                 `file:` protocol.
-->

* `path` {string|Buffer|URL}
* Returns: {boolean}

Returns `true` if the path exists, `false` otherwise.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.exists()`][].

`fs.exists()` is deprecated, but `fs.existsSync()` is not. The `callback`
parameter to `fs.exists()` accepts parameters that are inconsistent with other
Node.js callbacks. `fs.existsSync()` does not use a callback.

```mjs
import { existsSync } from 'node:fs';

if (existsSync('/etc/passwd'))
  console.log('The path exists.');
```

### `fs.fchmodSync(fd, mode)`

<!-- YAML
added: v0.4.7
-->

* `fd` {integer}
* `mode` {string|integer}

Sets the permissions on the file. Returns `undefined`.

See the POSIX fchmod(2) documentation for more detail.

### `fs.fchownSync(fd, uid, gid)`

<!-- YAML
added: v0.4.7
-->

* `fd` {integer}
* `uid` {integer} The file's new owner's user id.
* `gid` {integer} The file's new group's group id.

Sets the owner of the file. Returns `undefined`.

See the POSIX fchown(2) documentation for more detail.

### `fs.fdatasyncSync(fd)`

<!-- YAML
added: v0.1.96
-->

* `fd` {integer}

Forces all currently queued I/O operations associated with the file to the
operating system's synchronized I/O completion state. Refer to the POSIX
fdatasync(2) documentation for details. Returns `undefined`.

### `fs.fstatSync(fd[, options])`

<!-- YAML
added: v0.1.95
changes:
  - version: v10.5.0
    pr-url: https://github.com/nodejs/node/pull/20220
    description: Accepts an additional `options` object to specify whether
                 the numeric values returned should be bigint.
-->

* `fd` {integer}
* `options` {Object}
  * `bigint` {boolean} Whether the numeric values in the returned
    {fs.Stats} object should be `bigint`. **Default:** `false`.
* Returns: {fs.Stats}

Retrieves the {fs.Stats} for the file descriptor.

See the POSIX fstat(2) documentation for more detail.

### `fs.fsyncSync(fd)`

<!-- YAML
added: v0.1.96
-->

* `fd` {integer}

Request that all data for the open file descriptor is flushed to the storage
device. The specific implementation is operating system and device specific.
Refer to the POSIX fsync(2) documentation for more detail. Returns `undefined`.

### `fs.ftruncateSync(fd[, len])`

<!-- YAML
added: v0.8.6
-->

* `fd` {integer}
* `len` {integer} **Default:** `0`

Truncates the file descriptor. Returns `undefined`.

For detailed information, see the documentation of the asynchronous version of
this API: [`fs.ftruncate()`][].

### `fs.futimesSync(fd, atime, mtime)`

<!-- YAML
added: v0.4.2
changes:
  - version: v4.1.0
    pr-url: https://github.com/nodejs/node/pull/2387
    description: Numeric strings, `NaN`, and `Infinity` are now allowed
                 time specifiers.
-->

* `fd` {integer}
* `atime` {number|string|Date}
* `mtime` {number|string|Date}

Synchronous version of [`fs.futimes()`][]. Returns `undefined`.

### `fs.globSync(pattern[, options])`

<!-- YAML
added: v22.0.0
changes:
  - version:
      - v24.1.0
      - v22.17.0
    pr-url: https://github.com/nodejs/node/pull/58182
    description: Add support for `URL` instances for `cwd` option.
  - version:
      - v24.0.0
      - v22.17.0
    pr-url: https://github.com/nodejs/node/pull/57513
    description: Marking the API stable.
  - version:
    - v23.7.0
    - v22.14.0
    pr-url: https://github.com/nodejs/node/pull/56489
    description: Add support for `exclude` option to accept glob patterns.
  - version: v22.2.0
    pr-url: https://github.com/nodejs/node/pull/52837
    description: Add support for `withFileTypes` as an option.
-->

* `pattern` {string|string\[]}
* `options` {Object}
  * `cwd` {string|URL} current working directory. **Default:** `process.cwd()`
  * `exclude` {Function|string\[]} Function to filter out files/directories or a
    list of glob patterns to be excluded. If a function is provided, return
    `true` to exclude the item, `false` to include it. **Default:** `undefined`.
  * `withFileTypes` {boolean} `true` if the glob should return paths as Dirents,
    `false` otherwise. **Default:** `false`.
* Returns: {string\[]} paths of files that match the pattern.

```mjs
import { globSync } from 'node:fs';

console.log(globSync('**/*.js'));
```

```cjs
const { globSync } = require('node:fs');

console.log(globSync('**/*.js'));
```

### `fs.lchmodSync(path, mode)`

<!-- YAML
deprecated: v0.4.7
-->

> Stability: 0 - Deprecated

* `path` {string|Buffer|URL}
* `mode` {integer}

Changes the permissions on a symbolic link. Returns `undefined`.

This method is only implemented on macOS.

See the POSIX lchmod(2) documentation for more detail.

### `fs.lchownSync(path, uid, gid)`

<!-- YAML
changes:
  - version: v10.6.0
    pr-url: https://github.com/nodejs/node/pull/21498
    description: This API is no longer deprecated.
  - version: v0.4.7
    description: Documentation-only deprecation.
-->

* `path` {string|Buffer|URL}
* `uid` {integer} The file's new owner's user id.
* `gid` {integer} The file's new group's group id.

Set the owner for the path. Returns `undefined`.

See the POSIX lchown(2) documentation for more details.

### `fs.lutimesSync(path, atime, mtime)`

<!-- YAML
added:
  - v14.5.0
  - v12.19.0
-->

* `path` {string|Buffer|URL}
* `atime` {number|string|Date}
* `mtime` {number|string|Date}

Change the file system timestamps of the symbolic link referenced by `path`.
Returns `undefined`, or throws an exception when parameters are incorrect or
the operation fails. This is the synchronous version of [`fs.lutimes()`][].

### `fs.linkSync(existingPath, newPath)`

<!-- YAML
added: v0.1.31
changes:
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `existingPath` and `newPath` parameters can be WHATWG
                 `URL` objects using `file:` protocol. Support is currently
                 still *experimental*.
-->

* `existingPath` {string|Buffer|URL}
* `newPath` {string|Buffer|URL}

Creates a new link from the `existingPath` to the `newPath`. See the POSIX
link(2) documentation for more detail. Returns `undefined`.

### `fs.lstatSync(path[, options])`

<!-- YAML
added: v0.1.30
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

Retrieves the {fs.Stats} for the symbolic link referred to by `path`.

See the POSIX lstat(2) documentation for more details.

### `fs.mkdirSync(path[, options])`

<!-- YAML
added: v0.1.21
changes:
  - version:
     - v13.11.0
     - v12.17.0
    pr-url: https://github.com/nodejs/node/pull/31530
    description: In `recursive` mode, the first created path is returned now.
  - version: v10.12.0
    pr-url: https://github.com/nodejs/node/pull/21875
    description: The second argument can now be an `options` object with
                 `recursive` and `mode` properties.
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using `file:`
                 protocol.
-->

* `path` {string|Buffer|URL}
* `options` {Object|integer}
  * `recursive` {boolean} **Default:** `false`
  * `mode` {string|integer} Not supported on Windows. **Default:** `0o777`.
* Returns: {string|undefined}

Synchronously creates a directory. Returns `undefined`, or if `recursive` is
`true`, the first directory path created.
This is the synchronous version of [`fs.mkdir()`][].

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
