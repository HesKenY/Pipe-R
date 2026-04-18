# Node.js fs (20/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
le was accessed expressed in
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

* Type: {number|bigint}

The timestamp indicating the creation time of this file expressed in
milliseconds since the POSIX Epoch.

#### `stats.atimeNs`

<!-- YAML
added: v12.10.0
-->

* Type: {bigint}

Only present when `bigint: true` is passed into the method that generates
the object.
The timestamp indicating the last time this file was accessed expressed in
nanoseconds since the POSIX Epoch.

#### `stats.mtimeNs`

<!-- YAML
added: v12.10.0
-->

* Type: {bigint}

Only present when `bigint: true` is passed into the method that generates
the object.
The timestamp indicating the last time this file was modified expressed in
nanoseconds since the POSIX Epoch.

#### `stats.ctimeNs`

<!-- YAML
added: v12.10.0
-->

* Type: {bigint}

Only present when `bigint: true` is passed into the method that generates
the object.
The timestamp indicating the last time the file status was changed expressed
in nanoseconds since the POSIX Epoch.

#### `stats.birthtimeNs`

<!-- YAML
added: v12.10.0
-->

* Type: {bigint}

Only present when `bigint: true` is passed into the method that generates
the object.
The timestamp indicating the creation time of this file expressed in
nanoseconds since the POSIX Epoch.

#### `stats.atime`

<!-- YAML
added: v0.11.13
-->

* Type: {Date}

The timestamp indicating the last time this file was accessed.

#### `stats.mtime`

<!-- YAML
added: v0.11.13
-->

* Type: {Date}

The timestamp indicating the last time this file was modified.

#### `stats.ctime`

<!-- YAML
added: v0.11.13
-->

* Type: {Date}

The timestamp indicating the last time the file status was changed.

#### `stats.birthtime`

<!-- YAML
added: v0.11.13
-->

* Type: {Date}

The timestamp indicating the creation time of this file.

#### Stat time values

The `atimeMs`, `mtimeMs`, `ctimeMs`, `birthtimeMs` properties are
numeric values that hold the corresponding times in milliseconds. Their
precision is platform specific. When `bigint: true` is passed into the
method that generates the object, the properties will be [bigints][],
otherwise they will be [numbers][MDN-Number].

The `atimeNs`, `mtimeNs`, `ctimeNs`, `birthtimeNs` properties are
[bigints][] that hold the corresponding times in nanoseconds. They are
only present when `bigint: true` is passed into the method that generates
the object. Their precision is platform specific.

`atime`, `mtime`, `ctime`, and `birthtime` are
[`Date`][MDN-Date] object alternate representations of the various times. The
`Date` and number values are not connected. Assigning a new number value, or
mutating the `Date` value, will not be reflected in the corresponding alternate
representation.

The times in the stat object have the following semantics:

* `atime` "Access Time": Time when file data last accessed. Changed
  by the mknod(2), utimes(2), and read(2) system calls.
* `mtime` "Modified Time": Time when file data last modified.
  Changed by the mknod(2), utimes(2), and write(2) system calls.
* `ctime` "Change Time": Time when file status was last changed
  (inode data modification). Changed by the chmod(2), chown(2),
  link(2), mknod(2), rename(2), unlink(2), utimes(2),
  read(2), and write(2) system calls.
* `birthtime` "Birth Time": Time of file creation. Set once when the
  file is created. On file systems where birthtime is not available,
  this field may instead hold either the `ctime` or
  `1970-01-01T00:00Z` (ie, Unix epoch timestamp `0`). This value may be greater
  than `atime` or `mtime` in this case. On Darwin and other FreeBSD variants,
  also set if the `atime` is explicitly set to an earlier value than the current
  `birthtime` using the utimes(2) system call.

Prior to Node.js 0.12, the `ctime` held the `birthtime` on Windows systems. As
of 0.12, `ctime` is not "creation time", and on Unix systems, it never was.

### Class: `fs.StatFs`

<!-- YAML
added:
  - v19.6.0
  - v18.15.0
-->

Provides information about a mounted file system.

Objects returned from [`fs.statfs()`][] and its synchronous counterpart are of
this type. If `bigint` in the `options` passed to those methods is `true`, the
numeric values will be `bigint` instead of `number`.

```console
StatFs {
  type: 1397114950,
  bsize: 4096,
  frsize: 4096,
  blocks: 121938943,
  bfree: 61058895,
  bavail: 61058895,
  files: 999,
  ffree: 1000000
}
```

`bigint` version:

```console
StatFs {
  type: 1397114950n,
  bsize: 4096n,
  frsize: 4096n,
  blocks: 121938943n,
  bfree: 61058895n,
  bavail: 61058895n,
  files: 999n,
  ffree: 1000000n
}
```

#### `statfs.bavail`

<!-- YAML
added:
  - v19.6.0
  - v18.15.0
-->

* Type: {number|bigint}

Free blocks available to unprivileged users.

#### `statfs.bfree`

<!-- YAML
added:
  - v19.6.0
  - v18.15.0
-->

* Type: {number|bigint}

Free blocks in file system.

#### `statfs.blocks`

<!-- YAML
added:
  - v19.6.0
  - v18.15.0
-->

* Type: {number|bigint}

Total data blocks in file system.

#### `statfs.bsize`

<!-- YAML
added:
  - v19.6.0
  - v18.15.0
-->

* Type: {number|bigint}

Optimal transfer block size.

#### `statfs.frsize`

<!-- YAML
added: REPLACEME
-->

* Type: {number|bigint}

Fundamental file system block size.

#### `statfs.ffree`

<!-- YAML
added:
  - v19.6.0
  - v18.15.0
-->

* Type: {number|bigint}

Free file nodes in file system.

#### `statfs.files`

<!-- YAML
added:
  - v19.6.0
  - v18.15.0
-->

* Type: {number|bigint}

Total file nodes in file system.

#### `statfs.type`

<!-- YAML
added:
  - v19.6.0
  - v18.15.0
-->

* Type: {number|bigint}

Type of file system.

### Class: `fs.Utf8Stream`

<!-- YAML
added: v24.6.0
-->

> Stability: 1 - Experimental

An optimized UTF-8 stream writer that allows for flushing all the internal
buffering on demand. It handles `EAGAIN` errors correctly, allowing for
customization, for example, by dropping content if the disk is busy.

#### Event: `'close'`

The `'close'` event is emitted when the stream is fully closed.

#### Event: `'drain'`

The `'drain'` event is emitted when the internal buffer has drained sufficiently
to allow continued writing.

#### Event: `'drop'`

The `'drop'` event is emitted when the maximal length is reached and that data
will not be written. The data that was dropped is passed as the first argument
to the event handler.

#### Event: `'error'`

The `'error'` event is emitted when an error occurs.

#### Event: `'finish'`

The `'finish'` event is emitted when the stream has been ended and all data has
been flushed to the underlying file.

#### Event: `'ready'`

The `'ready'` event is emitted when the stream is ready to accept writes.

#### Event: `'write'`

The `'write'` event is emitted when a write operation has completed. The number
of bytes written is passed as the first argument to the event handler.

#### `new fs.Utf8Stream([options])`

* `options` {Object}
  * `append`: {boolean} Appends writes to dest file instead of truncating it.
    **Default**: `true`.
  * `contentMode`: {string} Which type of data you can send to the write
    function, supported values are `'utf8'` or `'buffer'`. **Default**:
    `'utf8'`.
  * `dest`: {string} A path to a file to be written to (mode controlled by the
    append option).
  * `fd`: {number} A file descriptor, something that is returned by `fs.open()`
    or `fs.openSync()`.
  * `fs`: {Object} An object that has the same API as the `fs` module, useful
    for mocking, testing, or customizing the behavior of the stream.
  * `fsync`: {boolean} Perform a `fs.fsyncSync()` every time a write is
    completed.
  * `maxLength`: {number} The maximum length of the internal buffer. If a write
    operation would cause the buffer to exceed `maxLength`, the data written is
    dropped and a drop event is emitted with the dropped data
  * `maxWrite`: {number} The maximum number of bytes that can be written;
    **Default**: `16384`
  * `minLength`: {number} The minimum length of the internal buffer that is
    required to be full before flushing.
  * `mkdir`: {boolean} Ensure directory for `dest` file exists when true.
    **Default**: `false`.
  * `mode`: {number|string} Specify the creating file mode (see `fs.open()`).
  * `periodicFlush`: {number} Calls flush every `periodicFlush` milliseconds.
  * `retryEAGAIN` {Function} A function that will be called when `write()`,
    `writeSync()`, or `flushSync()` encounters an `EAGAIN` or `EBUSY` error.
    If the return value is `true` the operation will be retried, otherwise it
    will bubble the error. The `err` is the error that caused this function to
    be called, `writeBufferLen` is the length of the buffer that was written,
    and `remainingBufferLen` is the length of the remaining buffer that the
    stream did not try to write.
    * `err` {any} An error or `null`.
    * `writeBufferLen` {number}
    * `remainingBufferLen`: {number}
  * `sync`: {boolean} Perform writes synchronously.

#### `utf8Stream.append`

* {boolean} Whether the stream is appending to the file or truncating it.

#### `utf8Stream.contentMode`

* {string} The type of data that can be written to the stream. Supported
  values are `'utf8'` or `'buffer'`. **Default**: `'utf8'`.

#### `utf8Stream.destroy()`

Close the stream immediately, without flushing the internal buffer.

#### `utf8Stream.end()`

Close the stream gracefully, flushing the internal buffer before closing.

#### `utf8Stream.fd`

* {number} The file descriptor that is being written to.

#### `utf8Stream.file`

* {string} The file that is being written to.

#### `utf8Stream.flush(callback)`

* `callback` {Function}
  * `err` {Error|null} An error if the flush failed, otherwise `null`.

Writes the current buffer to the file if a write was not in progress. Do
nothing if `minLength` is zero or if it is already writing.

#### `utf8Stream.flushSync()`

Flushes the buffered data synchronously. This is a costly operation.

#### `utf8Stream.fsync`

* {boolean} Whether the stream is performing a `fs.fsyncSync()` after every
  write operation.

#### `utf8Stream.maxLength`

* {number} The maximum length of the internal buffer. If a write
  operation would cause the buffer to exceed `maxLength`, the data written is
  dropped and a drop event is emitted with the dropped data.

#### `utf8Stream.minLength`

* {number} The minimum length of the internal buffer that is required to be
  full before flushing.

#### `utf8Stream.mkdir`

* {boolean} Whether the stream should ensure that the directory for the
  `dest` file exists. If `true`, it will create the directory if it does not
  exist. **Default**: `false`.

#### `utf8Stream.mode`

* {number|string} The mode of the file that is being written to.

#### `utf8Stream.periodicFlush`

* {number} The number of milliseconds between flushes. If set to `0`, no
  periodic flushes will be performed.

#### `utf8Stream.reopen(file)`

* `file`: {string|Buffer|URL} A path to a file to be written to (mode
  controlled by the append option).

Reopen the file in place, useful for log rotation.

#### `utf8Stream.sync`

* {boolean} Whether the stream is writing synchronously or asynchronously.

#### `utf8Stream.write(data)`

* `data` {string|Buffer} The data to write.
* Returns {boolean}

When the `options.contentMode` is set to `'utf8'` when the stream is created,
the `data` argument must be a string. If the `contentMode` is set to `'buffer'`,
the `data` argument must be a {Buffer}.

#### `utf8Stream.writing`

* {boolean} Whether the stream is currently writing data to the file.

#### `utf8Stream[Symbol.dispose]()`

Calls `utf8Stream.destroy()`.

### Class: `fs.WriteStream`

<!-- YAML
added: v0.1.93
-->

* Extends {stream.Writable}

Instances of {fs.WriteStream} cannot be constructed directly. They are created and
returned using the [`fs.createWriteStream()`][] function.

#### Event: `'close'`

<!-- YAML
added: v0.1.93
-->

Emitted when the {fs.WriteStream}'s underlying file descriptor has been closed.

#### Event: `'open'`

<!-- YAML
added: v0.1.93
-->

* `fd` {integer} Integer file descriptor used by the {fs.WriteStream}.

Emitted when the {fs.WriteStream}'s file is opened.

#### Event: `'ready'`

<!-- YAML
added: v9.11.0
-->

Emitted when the {fs.WriteStream} is ready to be used.

Fires immediately after `'open'`.

#### `writeStream.bytesWritten`

<!-- YAML
added: v0.4.7
-->

The number of bytes written so far. Does not include data that is still queued
for writing.

#### `writeStream.close([callback])`

<!-- YAML
added: v0.9.4
-->

* `callback` {Function}
  * `err` {Error}

Closes `writeStream`. Optionally accepts a
callback that will be executed once the `writeStream`
is closed.

#### `writeStream.path`

<!-- YAML
added: v0.1.93
-->

The path to the file the stream is writing to as specified in the first
argument to [`fs.createWriteStream()`][]. If `path` is passed as a string, then
`writeStream.path` will be a string. If `path` is passed as a {Buffer}, then
`writeStream.path` will be a {Buffer}.

#### `writeStream.pending`

<!-- YAML
added: v11.2.0
-->

* Type: {boolean}

This property is `true` if the underlying file has not been opened yet,
i.e. before the `'ready'` event is emitted.

### `fs.constants`

* Type: {Object}

Returns an object containing commonly used constants for file system
operations.

#### FS constants

The following constants are exported by `fs.constants` and `fsPromises.constants`.
