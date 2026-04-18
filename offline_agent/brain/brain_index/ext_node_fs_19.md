# Node.js fs (19/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
by this function are in no particular order as
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

Directory entries returned by this function are in no particular order as
provided by the operating system's underlying directory mechanisms.
Entries added or removed while iterating over the directory might not be
included in the iteration results.

#### `dir[Symbol.asyncIterator]()`

<!-- YAML
added: v12.12.0
-->

* Returns: {AsyncIterator} An AsyncIterator of {fs.Dirent}

Asynchronously iterates over the directory until all entries have
been read. Refer to the POSIX readdir(3) documentation for more detail.

Entries returned by the async iterator are always an {fs.Dirent}.
The `null` case from `dir.read()` is handled internally.

See {fs.Dir} for an example.

Directory entries returned by this iterator are in no particular order as
provided by the operating system's underlying directory mechanisms.
Entries added or removed while iterating over the directory might not be
included in the iteration results.

#### `dir[Symbol.asyncDispose]()`

<!-- YAML
added:
 - v24.1.0
 - v22.1.0
changes:
 - version: v24.2.0
   pr-url: https://github.com/nodejs/node/pull/58467
   description: No longer experimental.
-->

Calls `dir.close()` if the directory handle is open, and returns a promise that
fulfills when disposal is complete.

#### `dir[Symbol.dispose]()`

<!-- YAML
added:
 - v24.1.0
 - v22.1.0
changes:
 - version: v24.2.0
   pr-url: https://github.com/nodejs/node/pull/58467
   description: No longer experimental.
-->

Calls `dir.closeSync()` if the directory handle is open, and returns
`undefined`.

### Class: `fs.Dirent`

<!-- YAML
added: v10.10.0
-->

A representation of a directory entry, which can be a file or a subdirectory
within the directory, as returned by reading from an {fs.Dir}. The
directory entry is a combination of the file name and file type pairs.

Additionally, when [`fs.readdir()`][] or [`fs.readdirSync()`][] is called with
the `withFileTypes` option set to `true`, the resulting array is filled with
{fs.Dirent} objects, rather than strings or {Buffer}s.

#### `dirent.isBlockDevice()`

<!-- YAML
added: v10.10.0
-->

* Returns: {boolean}

Returns `true` if the {fs.Dirent} object describes a block device.

#### `dirent.isCharacterDevice()`

<!-- YAML
added: v10.10.0
-->

* Returns: {boolean}

Returns `true` if the {fs.Dirent} object describes a character device.

#### `dirent.isDirectory()`

<!-- YAML
added: v10.10.0
-->

* Returns: {boolean}

Returns `true` if the {fs.Dirent} object describes a file system
directory.

#### `dirent.isFIFO()`

<!-- YAML
added: v10.10.0
-->

* Returns: {boolean}

Returns `true` if the {fs.Dirent} object describes a first-in-first-out
(FIFO) pipe.

#### `dirent.isFile()`

<!-- YAML
added: v10.10.0
-->

* Returns: {boolean}

Returns `true` if the {fs.Dirent} object describes a regular file.

#### `dirent.isSocket()`

<!-- YAML
added: v10.10.0
-->

* Returns: {boolean}

Returns `true` if the {fs.Dirent} object describes a socket.

#### `dirent.isSymbolicLink()`

<!-- YAML
added: v10.10.0
-->

* Returns: {boolean}

Returns `true` if the {fs.Dirent} object describes a symbolic link.

#### `dirent.name`

<!-- YAML
added: v10.10.0
-->

* Type: {string|Buffer}

The file name that this {fs.Dirent} object refers to. The type of this
value is determined by the `options.encoding` passed to [`fs.readdir()`][] or
[`fs.readdirSync()`][].

#### `dirent.parentPath`

<!-- YAML
added:
  - v21.4.0
  - v20.12.0
  - v18.20.0
changes:
  - version:
      - v24.0.0
      - v22.17.0
    pr-url: https://github.com/nodejs/node/pull/57513
    description: Marking the API stable.
-->

* Type: {string}

The path to the parent directory of the file this {fs.Dirent} object refers to.

### Class: `fs.FSWatcher`

<!-- YAML
added: v0.5.8
-->

* Extends {EventEmitter}

A successful call to [`fs.watch()`][] method will return a new {fs.FSWatcher}
object.

All {fs.FSWatcher} objects emit a `'change'` event whenever a specific watched
file is modified.

#### Event: `'change'`

<!-- YAML
added: v0.5.8
-->

* `eventType` {string} The type of change event that has occurred
* `filename` {string|Buffer} The filename that changed (if relevant/available)

Emitted when something changes in a watched directory or file.
See more details in [`fs.watch()`][].

The `filename` argument may not be provided depending on operating system
support. If `filename` is provided, it will be provided as a {Buffer} if
`fs.watch()` is called with its `encoding` option set to `'buffer'`, otherwise
`filename` will be a UTF-8 string.

```mjs
import { watch } from 'node:fs';
// Example when handled through fs.watch() listener
watch('./tmp', { encoding: 'buffer' }, (eventType, filename) => {
  if (filename) {
    console.log(filename);
    // Prints: <Buffer ...>
  }
});
```

#### Event: `'close'`

<!-- YAML
added: v10.0.0
-->

Emitted when the watcher stops watching for changes. The closed
{fs.FSWatcher} object is no longer usable in the event handler.

#### Event: `'error'`

<!-- YAML
added: v0.5.8
-->

* `error` {Error}

Emitted when an error occurs while watching the file. The errored
{fs.FSWatcher} object is no longer usable in the event handler.

#### `watcher.close()`

<!-- YAML
added: v0.5.8
-->

Stop watching for changes on the given {fs.FSWatcher}. Once stopped, the
{fs.FSWatcher} object is no longer usable.

#### `watcher.ref()`

<!-- YAML
added:
  - v14.3.0
  - v12.20.0
-->

* Returns: {fs.FSWatcher}

When called, requests that the Node.js event loop _not_ exit so long as the
{fs.FSWatcher} is active. Calling `watcher.ref()` multiple times will have
no effect.

By default, all {fs.FSWatcher} objects are "ref'ed", making it normally
unnecessary to call `watcher.ref()` unless `watcher.unref()` had been
called previously.

#### `watcher.unref()`

<!-- YAML
added:
  - v14.3.0
  - v12.20.0
-->

* Returns: {fs.FSWatcher}

When called, the active {fs.FSWatcher} object will not require the Node.js
event loop to remain active. If there is no other activity keeping the
event loop running, the process may exit before the {fs.FSWatcher} object's
callback is invoked. Calling `watcher.unref()` multiple times will have
no effect.

### Class: `fs.StatWatcher`

<!-- YAML
added:
  - v14.3.0
  - v12.20.0
-->

* Extends {EventEmitter}

A successful call to `fs.watchFile()` method will return a new {fs.StatWatcher}
object.

#### `watcher.ref()`

<!-- YAML
added:
  - v14.3.0
  - v12.20.0
-->

* Returns: {fs.StatWatcher}

When called, requests that the Node.js event loop _not_ exit so long as the
{fs.StatWatcher} is active. Calling `watcher.ref()` multiple times will have
no effect.

By default, all {fs.StatWatcher} objects are "ref'ed", making it normally
unnecessary to call `watcher.ref()` unless `watcher.unref()` had been
called previously.

#### `watcher.unref()`

<!-- YAML
added:
  - v14.3.0
  - v12.20.0
-->

* Returns: {fs.StatWatcher}

When called, the active {fs.StatWatcher} object will not require the Node.js
event loop to remain active. If there is no other activity keeping the
event loop running, the process may exit before the {fs.StatWatcher} object's
callback is invoked. Calling `watcher.unref()` multiple times will have
no effect.

### Class: `fs.ReadStream`

<!-- YAML
added: v0.1.93
-->

* Extends: {stream.Readable}

Instances of {fs.ReadStream} cannot be constructed directly. They are created and
returned using the [`fs.createReadStream()`][] function.

#### Event: `'close'`

<!-- YAML
added: v0.1.93
-->

Emitted when the {fs.ReadStream}'s underlying file descriptor has been closed.

#### Event: `'open'`

<!-- YAML
added: v0.1.93
-->

* `fd` {integer} Integer file descriptor used by the {fs.ReadStream}.

Emitted when the {fs.ReadStream}'s file descriptor has been opened.

#### Event: `'ready'`

<!-- YAML
added: v9.11.0
-->

Emitted when the {fs.ReadStream} is ready to be used.

Fires immediately after `'open'`.

#### `readStream.bytesRead`

<!-- YAML
added: v6.4.0
-->

* Type: {number}

The number of bytes that have been read so far.

#### `readStream.path`

<!-- YAML
added: v0.1.93
-->

* Type: {string|Buffer}

The path to the file the stream is reading from as specified in the first
argument to `fs.createReadStream()`. If `path` is passed as a string, then
`readStream.path` will be a string. If `path` is passed as a {Buffer}, then
`readStream.path` will be a {Buffer}. If `fd` is specified, then
`readStream.path` will be `undefined`.

#### `readStream.pending`

<!-- YAML
added:
 - v11.2.0
 - v10.16.0
-->

* Type: {boolean}

This property is `true` if the underlying file has not been opened yet,
i.e. before the `'ready'` event is emitted.

### Class: `fs.Stats`

<!-- YAML
added: v0.1.21
changes:
  - version:
    - v22.0.0
    - v20.13.0
    pr-url: https://github.com/nodejs/node/pull/51879
    description: Public constructor is deprecated.
  - version: v8.1.0
    pr-url: https://github.com/nodejs/node/pull/13173
    description: Added times as numbers.
-->

A {fs.Stats} object provides information about a file.

Objects returned from [`fs.stat()`][], [`fs.lstat()`][], [`fs.fstat()`][], and
their synchronous counterparts are of this type.
If `bigint` in the `options` passed to those methods is true, the numeric values
will be `bigint` instead of `number`, and the object will contain additional
nanosecond-precision properties suffixed with `Ns`.
`Stat` objects are not to be created directly using the `new` keyword.

```console
Stats {
  dev: 2114,
  ino: 48064969,
  mode: 33188,
  nlink: 1,
  uid: 85,
  gid: 100,
  rdev: 0,
  size: 527,
  blksize: 4096,
  blocks: 8,
  atimeMs: 1318289051000.1,
  mtimeMs: 1318289051000.1,
  ctimeMs: 1318289051000.1,
  birthtimeMs: 1318289051000.1,
  atime: Mon, 10 Oct 2011 23:24:11 GMT,
  mtime: Mon, 10 Oct 2011 23:24:11 GMT,
  ctime: Mon, 10 Oct 2011 23:24:11 GMT,
  birthtime: Mon, 10 Oct 2011 23:24:11 GMT }
```

`bigint` version:

```console
BigIntStats {
  dev: 2114n,
  ino: 48064969n,
  mode: 33188n,
  nlink: 1n,
  uid: 85n,
  gid: 100n,
  rdev: 0n,
  size: 527n,
  blksize: 4096n,
  blocks: 8n,
  atimeMs: 1318289051000n,
  mtimeMs: 1318289051000n,
  ctimeMs: 1318289051000n,
  birthtimeMs: 1318289051000n,
  atimeNs: 1318289051000000000n,
  mtimeNs: 1318289051000000000n,
  ctimeNs: 1318289051000000000n,
  birthtimeNs: 1318289051000000000n,
  atime: Mon, 10 Oct 2011 23:24:11 GMT,
  mtime: Mon, 10 Oct 2011 23:24:11 GMT,
  ctime: Mon, 10 Oct 2011 23:24:11 GMT,
  birthtime: Mon, 10 Oct 2011 23:24:11 GMT }
```

#### `stats.isBlockDevice()`

<!-- YAML
added: v0.1.10
-->

* Returns: {boolean}

Returns `true` if the {fs.Stats} object describes a block device.

#### `stats.isCharacterDevice()`

<!-- YAML
added: v0.1.10
-->

* Returns: {boolean}

Returns `true` if the {fs.Stats} object describes a character device.

#### `stats.isDirectory()`

<!-- YAML
added: v0.1.10
-->

* Returns: {boolean}

Returns `true` if the {fs.Stats} object describes a file system directory.

If the {fs.Stats} object was obtained from calling [`fs.lstat()`][] on a
symbolic link which resolves to a directory, this method will return `false`.
This is because [`fs.lstat()`][] returns information
about a symbolic link itself and not the path it resolves to.

#### `stats.isFIFO()`

<!-- YAML
added: v0.1.10
-->

* Returns: {boolean}

Returns `true` if the {fs.Stats} object describes a first-in-first-out (FIFO)
pipe.

#### `stats.isFile()`

<!-- YAML
added: v0.1.10
-->

* Returns: {boolean}

Returns `true` if the {fs.Stats} object describes a regular file.

#### `stats.isSocket()`

<!-- YAML
added: v0.1.10
-->

* Returns: {boolean}

Returns `true` if the {fs.Stats} object describes a socket.

#### `stats.isSymbolicLink()`

<!-- YAML
added: v0.1.10
-->

* Returns: {boolean}

Returns `true` if the {fs.Stats} object describes a symbolic link.

This method is only valid when using [`fs.lstat()`][].

#### `stats.dev`

* Type: {number|bigint}

The numeric identifier of the device containing the file.

#### `stats.ino`

* Type: {number|bigint}

The file system specific "Inode" number for the file.

#### `stats.mode`

* Type: {number|bigint}

A bit-field describing the file type and mode.

#### `stats.nlink`

* Type: {number|bigint}

The number of hard-links that exist for the file.

#### `stats.uid`

* Type: {number|bigint}

The numeric user identifier of the user that owns the file (POSIX).

#### `stats.gid`

* Type: {number|bigint}

The numeric group identifier of the group that owns the file (POSIX).

#### `stats.rdev`

* Type: {number|bigint}

A numeric device identifier if the file represents a device.

#### `stats.size`

* Type: {number|bigint}

The size of the file in bytes.

If the underlying file system does not support getting the size of the file,
this will be `0`.

#### `stats.blksize`

* Type: {number|bigint}

The file system block size for i/o operations.

#### `stats.blocks`

* Type: {number|bigint}

The number of blocks allocated for this file.

#### `stats.atimeMs`

<!-- YAML
added: v8.1.0
-->

* Type: {number|bigint}

The timestamp indicating the last time this file was accessed expressed in
milliseconds since the POSIX Epoch.

#### `stats.mtimeMs`

<!-- YAML
added: v8.1.0
-->

* Type: {number|bigint}

The timestamp indicating the last time this file was modified expressed in
milliseconds since the POSIX Epoch.

#### `stats.ctimeMs`

<!-- YAML
added: v8.1.0
-->

* Type: {number|bigint}

The timestamp indicating the last time the file status was changed expressed
in milliseconds since the POSIX Epoch.

#### `stats.birthtimeMs`

<!-- YAML
added: v8.1.0
-->
