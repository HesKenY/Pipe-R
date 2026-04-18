# Node.js fs (4/22)
source: https://github.com/nodejs/node/blob/main/doc/api/fs.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
e.

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

* `src` {string|Buffer|URL} source filename to copy
* `dest` {string|Buffer|URL} destination filename of the copy operation
* `mode` {integer} Optional modifiers that specify the behavior of the copy
  operation. It is possible to create a mask consisting of the bitwise OR of
  two or more values (e.g.
  `fs.constants.COPYFILE_EXCL | fs.constants.COPYFILE_FICLONE`)
  **Default:** `0`.
  * `fs.constants.COPYFILE_EXCL`: The copy operation will fail if `dest`
    already exists.
  * `fs.constants.COPYFILE_FICLONE`: The copy operation will attempt to create
    a copy-on-write reflink. If the platform does not support copy-on-write,
    then a fallback copy mechanism is used.
  * `fs.constants.COPYFILE_FICLONE_FORCE`: The copy operation will attempt to
    create a copy-on-write reflink. If the platform does not support
    copy-on-write, then the operation will fail.
* Returns: {Promise} Fulfills with `undefined` upon success.

Asynchronously copies `src` to `dest`. By default, `dest` is overwritten if it
already exists.

No guarantees are made about the atomicity of the copy operation. If an
error occurs after the destination file has been opened for writing, an attempt
will be made to remove the destination.

```mjs
import { copyFile, constants } from 'node:fs/promises';

try {
  await copyFile('source.txt', 'destination.txt');
  console.log('source.txt was copied to destination.txt');
} catch {
  console.error('The file could not be copied');
}

// By using COPYFILE_EXCL, the operation will fail if destination.txt exists.
try {
  await copyFile('source.txt', 'destination.txt', constants.COPYFILE_EXCL);
  console.log('source.txt was copied to destination.txt');
} catch {
  console.error('The file could not be copied');
}
```

### `fsPromises.cp(src, dest[, options])`

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
    See `mode` flag of [`fsPromises.copyFile()`][].
  * `preserveTimestamps` {boolean} When `true` timestamps from `src` will
    be preserved. **Default:** `false`.
  * `recursive` {boolean} copy directories recursively **Default:** `false`
  * `verbatimSymlinks` {boolean} When `true`, path resolution for symlinks will
    be skipped. **Default:** `false`
* Returns: {Promise} Fulfills with `undefined` upon success.

Asynchronously copies the entire directory structure from `src` to `dest`,
including subdirectories and files.

When copying a directory to another directory, globs are not supported and
behavior is similar to `cp dir1/ dir2/`.

### `fsPromises.glob(pattern[, options])`

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
    If a string array is provided, each string should be a glob pattern that
    specifies paths to exclude. Note: Negation patterns (e.g., '!foo.js') are
    not supported.
  * `withFileTypes` {boolean} `true` if the glob should return paths as Dirents,
    `false` otherwise. **Default:** `false`.
* Returns: {AsyncIterator} An AsyncIterator that yields the paths of files
  that match the pattern.

```mjs
import { glob } from 'node:fs/promises';

for await (const entry of glob('**/*.js'))
  console.log(entry);
```

```cjs
const { glob } = require('node:fs/promises');

(async () => {
  for await (const entry of glob('**/*.js'))
    console.log(entry);
})();
```

### `fsPromises.lchmod(path, mode)`

<!-- YAML
deprecated: v10.0.0
-->

> Stability: 0 - Deprecated

* `path` {string|Buffer|URL}
* `mode` {integer}
* Returns: {Promise} Fulfills with `undefined` upon success.

Changes the permissions on a symbolic link.

This method is only implemented on macOS.

### `fsPromises.lchown(path, uid, gid)`

<!-- YAML
added: v10.0.0
changes:
  - version: v10.6.0
    pr-url: https://github.com/nodejs/node/pull/21498
    description: This API is no longer deprecated.
-->

* `path` {string|Buffer|URL}
* `uid` {integer}
* `gid` {integer}
* Returns: {Promise}  Fulfills with `undefined` upon success.

Changes the ownership on a symbolic link.

### `fsPromises.lutimes(path, atime, mtime)`

<!-- YAML
added:
  - v14.5.0
  - v12.19.0
-->

* `path` {string|Buffer|URL}
* `atime` {number|string|Date}
* `mtime` {number|string|Date}
* Returns: {Promise}  Fulfills with `undefined` upon success.

Changes the access and modification times of a file in the same way as
[`fsPromises.utimes()`][], with the difference that if the path refers to a
symbolic link, then the link is not dereferenced: instead, the timestamps of
the symbolic link itself are changed.

### `fsPromises.link(existingPath, newPath)`

<!-- YAML
added: v10.0.0
-->

* `existingPath` {string|Buffer|URL}
* `newPath` {string|Buffer|URL}
* Returns: {Promise}  Fulfills with `undefined` upon success.

Creates a new link from the `existingPath` to the `newPath`. See the POSIX
link(2) documentation for more detail.

### `fsPromises.lstat(path[, options])`

<!-- YAML
added: v10.0.0
changes:
  - version: v10.5.0
    pr-url: https://github.com/nodejs/node/pull/20220
    description: Accepts an additional `options` object to specify whether
                 the numeric values returned should be bigint.
-->

* `path` {string|Buffer|URL}
* `options` {Object}
  * `bigint` {boolean} Whether the numeric values in the returned
    {fs.Stats} object should be `bigint`. **Default:** `false`.
* Returns: {Promise}  Fulfills with the {fs.Stats} object for the given
  symbolic link `path`.

Equivalent to [`fsPromises.stat()`][] unless `path` refers to a symbolic link,
in which case the link itself is stat-ed, not the file that it refers to.
Refer to the POSIX lstat(2) document for more detail.

### `fsPromises.mkdir(path[, options])`

<!-- YAML
added: v10.0.0
-->

* `path` {string|Buffer|URL}
* `options` {Object|integer}
  * `recursive` {boolean} **Default:** `false`
  * `mode` {string|integer} Not supported on Windows. See [File modes][]
    for more details. **Default:** `0o777`.
* Returns: {Promise} Upon success, fulfills with `undefined` if `recursive`
  is `false`, or the first directory path created if `recursive` is `true`.

Asynchronously creates a directory.

The optional `options` argument can be an integer specifying `mode` (permission
and sticky bits), or an object with a `mode` property and a `recursive`
property indicating whether parent directories should be created. Calling
`fsPromises.mkdir()` when `path` is a directory that exists results in a
rejection only when `recursive` is false.

```mjs
import { mkdir } from 'node:fs/promises';

try {
  const projectFolder = new URL('./test/project/', import.meta.url);
  const createDir = await mkdir(projectFolder, { recursive: true });

console.log(`created ${createDir}`);
} catch (err) {
  console.error(err.message);
}
```

```cjs
const { mkdir } = require('node:fs/promises');
const { join } = require('node:path');

async function makeDirectory() {
  const projectFolder = join(__dirname, 'test', 'project');
  const dirCreation = await mkdir(projectFolder, { recursive: true });

console.log(dirCreation);
  return dirCreation;
}

makeDirectory().catch(console.error);
```

### `fsPromises.mkdtemp(prefix[, options])`

<!-- YAML
added: v10.0.0
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
* Returns: {Promise}  Fulfills with a string containing the file system path
  of the newly created temporary directory.

Creates a unique temporary directory. A unique directory name is generated by
appending six random characters to the end of the provided `prefix`. Due to
platform inconsistencies, avoid trailing `X` characters in `prefix`. Some
platforms, notably the BSDs, can return more than six random characters, and
replace trailing `X` characters in `prefix` with random characters.

The optional `options` argument can be a string specifying an encoding, or an
object with an `encoding` property specifying the character encoding to use.

```mjs
import { mkdtemp } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

try {
  await mkdtemp(join(tmpdir(), 'foo-'));
} catch (err) {
  console.error(err);
}
```

The `fsPromises.mkdtemp()` method will append the six randomly selected
characters directly to the `prefix` string. For instance, given a directory
`/tmp`, if the intention is to create a temporary directory _within_ `/tmp`, the
`prefix` must end with a trailing platform-specific path separator
(`require('node:path').sep`).

### `fsPromises.mkdtempDisposable(prefix[, options])`

<!-- YAML
added: v24.4.0
-->

* `prefix` {string|Buffer|URL}
* `options` {string|Object}
  * `encoding` {string} **Default:** `'utf8'`
* Returns: {Promise} Fulfills with a Promise for an async-disposable Object:
  * `path` {string} The path of the created directory.
  * `remove` {AsyncFunction} A function which removes the created directory.
  * `[Symbol.asyncDispose]` {AsyncFunction} The same as `remove`.

The resulting Promise holds an async-disposable object whose `path` property
holds the created directory path. When the object is disposed, the directory
and its contents will be removed asynchronously if it still exists. If the
directory cannot be deleted, disposal will throw an error. The object has an
async `remove()` method which will perform the same task.

Both this function and the disposal function on the resulting object are
async, so it should be used with `await` + `await using` as in
`await using dir = await fsPromises.mkdtempDisposable('prefix')`.

<!-- TODO: link MDN docs for disposables once https://github.com/mdn/content/pull/38027 lands -->

For detailed information, see the documentation of [`fsPromises.mkdtemp()`][].

The optional `options` argument can be a string specifying an encoding, or an
object with an `encoding` property specifying the character encoding to use.

### `fsPromises.open(path, flags[, mode])`

<!-- YAML
added: v10.0.0
changes:
  - version: v11.1.0
    pr-url: https://github.com/nodejs/node/pull/23767
    description: The `flags` argument is now optional and defaults to `'r'`.
-->

* `path` {string|Buffer|URL}
* `flags` {string|number} See [support of file system `flags`][].
  **Default:** `'r'`.
* `mode` {string|integer} Sets the file mode (permission and sticky bits)
  if the file is created. See [File modes][] for more details.
  **Default:** `0o666` (readable and writable)
* Returns: {Promise} Fulfills with a {FileHandle} object.

Opens a {FileHandle}.

Refer to the POSIX open(2) documentation for more detail.
