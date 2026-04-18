# Node.js fs (8/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
File()`.
  - version: v18.0.0
    pr-url: https://github.com/nodejs/node/pull/41678
    description: Passing an invalid callback to the `callback` argument
                 now throws `ERR_INVALID_ARG_TYPE` instead of
                 `ERR_INVALID_CALLBACK`.
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
    all of its contents will be skipped as well. Can also return a `Promise`
    that resolves to `true` or `false` **Default:** `undefined`.
    * `src` {string} source path to copy.
    * `dest` {string} destination path to copy to.
    * Returns: {boolean|Promise} A value that is coercible to `boolean` or
      a `Promise` that fulfils with such value.
  * `force` {boolean} overwrite existing file or directory. The copy
    operation will ignore errors if you set this to false and the destination
    exists. Use the `errorOnExist` option to change this behavior.
    **Default:** `true`.
  * `mode` {integer} modifiers for copy operation. **Default:** `0`.
    See `mode` flag of [`fs.copyFile()`][].
  * `preserveTimestamps` {boolean} When `true` timestamps from `src` will
    be preserved. **Default:** `false`.
  * `recursive` {boolean} copy directories recursively **Default:** `false`
  * `verbatimSymlinks` {boolean} When `true`, path resolution for symlinks will
    be skipped. **Default:** `false`
* `callback` {Function}
  * `err` {Error}

Asynchronously copies the entire directory structure from `src` to `dest`,
including subdirectories and files.

When copying a directory to another directory, globs are not supported and
behavior is similar to `cp dir1/ dir2/`.

### `fs.createReadStream(path[, options])`

<!-- YAML
added: v0.1.31
changes:
  - version: v16.10.0
    pr-url: https://github.com/nodejs/node/pull/40013
    description: The `fs` option does not need `open` method if an `fd` was provided.
  - version: v16.10.0
    pr-url: https://github.com/nodejs/node/pull/40013
    description: The `fs` option does not need `close` method if `autoClose` is `false`.
  - version: v15.5.0
    pr-url: https://github.com/nodejs/node/pull/36431
    description: Add support for `AbortSignal`.
  - version:
     - v15.4.0
    pr-url: https://github.com/nodejs/node/pull/35922
    description: The `fd` option accepts FileHandle arguments.
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/31408
    description: Change `emitClose` default to `true`.
  - version:
     - v13.6.0
     - v12.17.0
    pr-url: https://github.com/nodejs/node/pull/29083
    description: The `fs` options allow overriding the used `fs`
                 implementation.
  - version: v12.10.0
    pr-url: https://github.com/nodejs/node/pull/29212
    description: Enable `emitClose` option.
  - version: v11.0.0
    pr-url: https://github.com/nodejs/node/pull/19898
    description: Impose new restrictions on `start` and `end`, throwing
                 more appropriate errors in cases when we cannot reasonably
                 handle the input values.
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using
                 `file:` protocol.
  - version: v7.0.0
    pr-url: https://github.com/nodejs/node/pull/7831
    description: The passed `options` object will never be modified.
  - version: v2.3.0
    pr-url: https://github.com/nodejs/node/pull/1845
    description: The passed `options` object can be a string now.
-->

* `path` {string|Buffer|URL}
* `options` {string|Object}
  * `flags` {string} See [support of file system `flags`][]. **Default:**
    `'r'`.
  * `encoding` {string} **Default:** `null`
  * `fd` {integer|FileHandle} **Default:** `null`
  * `mode` {integer} **Default:** `0o666`
  * `autoClose` {boolean} **Default:** `true`
  * `emitClose` {boolean} **Default:** `true`
  * `start` {integer}
  * `end` {integer} **Default:** `Infinity`
  * `highWaterMark` {integer} **Default:** `64 * 1024`
  * `fs` {Object|null} **Default:** `null`
  * `signal` {AbortSignal|null} **Default:** `null`
* Returns: {fs.ReadStream}

`options` can include `start` and `end` values to read a range of bytes from
the file instead of the entire file. Both `start` and `end` are inclusive and
start counting at 0, allowed values are in the
\[0, [`Number.MAX_SAFE_INTEGER`][]] range. If `fd` is specified and `start` is
omitted or `undefined`, `fs.createReadStream()` reads sequentially from the
current file position. The `encoding` can be any one of those accepted by
{Buffer}.

If `fd` is specified, `ReadStream` will ignore the `path` argument and will use
the specified file descriptor. This means that no `'open'` event will be
emitted. `fd` should be blocking; non-blocking `fd`s should be passed to
{net.Socket}.

If `fd` points to a character device that only supports blocking reads
(such as keyboard or sound card), read operations do not finish until data is
available. This can prevent the process from exiting and the stream from
closing naturally.

By default, the stream will emit a `'close'` event after it has been
destroyed.  Set the `emitClose` option to `false` to change this behavior.

By providing the `fs` option, it is possible to override the corresponding `fs`
implementations for `open`, `read`, and `close`. When providing the `fs` option,
an override for `read` is required. If no `fd` is provided, an override for
`open` is also required. If `autoClose` is `true`, an override for `close` is
also required.

```mjs
import { createReadStream } from 'node:fs';

// Create a stream from some character device.
const stream = createReadStream('/dev/input/event0');
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

`mode` sets the file mode (permission and sticky bits), but only if the
file was created.

An example to read the last 10 bytes of a file which is 100 bytes long:

```mjs
import { createReadStream } from 'node:fs';

createReadStream('sample.txt', { start: 90, end: 99 });
```

If `options` is a string, then it specifies the encoding.

### `fs.createWriteStream(path[, options])`

<!-- YAML
added: v0.1.31
changes:
  - version:
    - v21.0.0
    - v20.10.0
    pr-url: https://github.com/nodejs/node/pull/50093
    description: The `flush` option is now supported.
  - version: v16.10.0
    pr-url: https://github.com/nodejs/node/pull/40013
    description: The `fs` option does not need `open` method if an `fd` was provided.
  - version: v16.10.0
    pr-url: https://github.com/nodejs/node/pull/40013
    description: The `fs` option does not need `close` method if `autoClose` is `false`.
  - version: v15.5.0
    pr-url: https://github.com/nodejs/node/pull/36431
    description: Add support for `AbortSignal`.
  - version:
     - v15.4.0
    pr-url: https://github.com/nodejs/node/pull/35922
    description: The `fd` option accepts FileHandle arguments.
  - version: v14.0.0
    pr-url: https://github.com/nodejs/node/pull/31408
    description: Change `emitClose` default to `true`.
  - version:
     - v13.6.0
     - v12.17.0
    pr-url: https://github.com/nodejs/node/pull/29083
    description: The `fs` options allow overriding the used `fs`
                 implementation.
  - version: v12.10.0
    pr-url: https://github.com/nodejs/node/pull/29212
    description: Enable `emitClose` option.
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using
                 `file:` protocol.
  - version: v7.0.0
    pr-url: https://github.com/nodejs/node/pull/7831
    description: The passed `options` object will never be modified.
  - version: v5.5.0
    pr-url: https://github.com/nodejs/node/pull/3679
    description: The `autoClose` option is supported now.
  - version: v2.3.0
    pr-url: https://github.com/nodejs/node/pull/1845
    description: The passed `options` object can be a string now.
-->

* `path` {string|Buffer|URL}
* `options` {string|Object}
  * `flags` {string} See [support of file system `flags`][]. **Default:**
    `'w'`.
  * `encoding` {string} **Default:** `'utf8'`
  * `fd` {integer|FileHandle} **Default:** `null`
  * `mode` {integer} **Default:** `0o666`
  * `autoClose` {boolean} **Default:** `true`
  * `emitClose` {boolean} **Default:** `true`
  * `start` {integer}
  * `fs` {Object|null} **Default:** `null`
  * `signal` {AbortSignal|null} **Default:** `null`
  * `highWaterMark` {number} **Default:** `16384`
  * `flush` {boolean} If `true`, the underlying file descriptor is flushed
    prior to closing it. **Default:** `false`.
* Returns: {fs.WriteStream}

`options` may also include a `start` option to allow writing data at some
position past the beginning of the file, allowed values are in the
\[0, [`Number.MAX_SAFE_INTEGER`][]] range. Modifying a file rather than
replacing it may require the `flags` option to be set to `r+` rather than the
default `w`. The `encoding` can be any one of those accepted by {Buffer}.

If `autoClose` is set to true (default behavior) on `'error'` or `'finish'`
the file descriptor will be closed automatically. If `autoClose` is false,
then the file descriptor won't be closed, even if there's an error.
It is the application's responsibility to close it and make sure there's no
file descriptor leak.

By default, the stream will emit a `'close'` event after it has been
destroyed.  Set the `emitClose` option to `false` to change this behavior.

By providing the `fs` option it is possible to override the corresponding `fs`
implementations for `open`, `write`, `writev`, and `close`. Overriding `write()`
without `writev()` can reduce performance as some optimizations (`_writev()`)
will be disabled. When providing the `fs` option, overrides for at least one of
`write` and `writev` are required. If no `fd` option is supplied, an override
for `open` is also required. If `autoClose` is `true`, an override for `close`
is also required.

Like {fs.ReadStream}, if `fd` is specified, {fs.WriteStream} will ignore the
`path` argument and will use the specified file descriptor. This means that no
`'open'` event will be emitted. `fd` should be blocking; non-blocking `fd`s
should be passed to {net.Socket}.

If `options` is a string, then it specifies the encoding.

### `fs.exists(path, callback)`

<!-- YAML
added: v0.0.2
deprecated: v1.0.0
changes:
  - version: v18.0.0
    pr-url: https://github.com/nodejs/node/pull/41678
    description: Passing an invalid callback to the `callback` argument
                 now throws `ERR_INVALID_ARG_TYPE` instead of
                 `ERR_INVALID_CALLBACK`.
  - version: v7.6.0
    pr-url: https://github.com/nodejs/node/pull/10739
    description: The `path` parameter can be a WHATWG `URL` object using
                 `file:` protocol.
-->

> Stability: 0 - Deprecated: Use [`fs.stat()`][] or [`fs.access()`][] instead.

* `path` {string|Buffer|URL}
* `callback` {Function}
  * `exists` {boolean}

Test whether or not the element at the given `path` exists by checking with the file system.
Then call the `callback` argument with either true or false:

```mjs
import { exists } from 'node:fs';

exists('/etc/passwd', (e) => {
  console.log(e ? 'it exists' : 'no passwd!');
});
```

**The parameters for this callback are not consistent with other Node.js
callbacks.** Normally, the first parameter to a Node.js callback is an `err`
parameter, optionally followed by other parameters. The `fs.exists()` callback
has only one boolean parameter. This is one reason `fs.access()` is recommended
instead of `fs.exists()`.

If `path` is a symbolic link, it is followed. Thus, if `path` exists but points
to a non-existent element, the callback will receive the value `false`.

Using `fs.exists()` to check for the existence of a file before calling
`fs.open()`, `fs.readFile()`, or `fs.writeFile()` is not recommended. Doing
so introduces a race condition, since other processes may change the file's
state between the two calls. Instead, user code should open/read/write the
file directly and handle the error raised if the file does not exist.

**write (NOT RECOMMENDED)**

```mjs
import { exists, open, close } from 'node:fs';

exists('myfile', (e) => {
  if (e) {
    console.error('myfile already exists');
  } else {
    open('myfile', 'wx', (err, fd) => {
      if (err) throw err;

try {
        writeMyData(fd);
      } finally {
        close(fd, (err) => {
          if (err) throw err;
        });
      }
    });
  }
});
```

**write (RECOMMENDED)**
