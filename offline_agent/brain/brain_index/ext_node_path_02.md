# Node.js path (2/2)
source: https://github.com/nodejs/node/blob/main/doc/api/path.md
repo: https://github.com/nodejs/node
license: MIT-like Node.js license | https://github.com/nodejs/node/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
ce of paths or path segments
* Returns: {string}

The `path.resolve()` method resolves a sequence of paths or path segments into
an absolute path.

The given sequence of paths is processed from right to left, with each
subsequent `path` prepended until an absolute path is constructed.
For instance, given the sequence of path segments: `/foo`, `/bar`, `baz`,
calling `path.resolve('/foo', '/bar', 'baz')` would return `/bar/baz`
because `'baz'` is not an absolute path but `'/bar' + '/' + 'baz'` is.

If, after processing all given `path` segments, an absolute path has not yet
been generated, the current working directory is used.

The resulting path is normalized and trailing slashes are removed unless the
path is resolved to the root directory.

Zero-length `path` segments are ignored.

If no `path` segments are passed, `path.resolve()` will return the absolute path
of the current working directory.

```js
path.resolve('/foo/bar', './baz');
// Returns: '/foo/bar/baz'

path.resolve('/foo/bar', '/tmp/file/');
// Returns: '/tmp/file'

path.resolve('wwwroot', 'static_files/png/', '../gif/image.gif');
// If the current working directory is /home/myself/node,
// this returns '/home/myself/node/wwwroot/static_files/gif/image.gif'
```

A [`TypeError`][] is thrown if any of the arguments is not a string.

## `path.sep`

<!-- YAML
added: v0.7.9
-->

* Type: {string}

Provides the platform-specific path segment separator:

* `\` on Windows
* `/` on POSIX

For example, on POSIX:

```js
'foo/bar/baz'.split(path.sep);
// Returns: ['foo', 'bar', 'baz']
```

On Windows:

```js
'foo\\bar\\baz'.split(path.sep);
// Returns: ['foo', 'bar', 'baz']
```

On Windows, both the forward slash (`/`) and backward slash (`\`) are accepted
as path segment separators; however, the `path` methods only add backward
slashes (`\`).

## `path.toNamespacedPath(path)`

<!-- YAML
added: v9.0.0
-->

* `path` {string}
* Returns: {string}

On Windows systems only, returns an equivalent [namespace-prefixed path][] for
the given `path`. If `path` is not a string, `path` will be returned without
modifications.

This method is meaningful only on Windows systems. On POSIX systems, the
method is non-operational and always returns `path` without modifications.

## `path.win32`

<!-- YAML
added: v0.11.15
changes:
  - version: v15.3.0
    pr-url: https://github.com/nodejs/node/pull/34962
    description: Exposed as `require('path/win32')`.
-->

* Type: {Object}

The `path.win32` property provides access to Windows-specific implementations
of the `path` methods.

The API is accessible via `require('node:path').win32` or `require('node:path/win32')`.

[MSDN-Rel-Path]: https://docs.microsoft.com/en-us/windows/desktop/FileIO/naming-a-file#fully-qualified-vs-relative-paths
[`TypeError`]: errors.md#class-typeerror
[`path.parse()`]: #pathparsepath
[`path.posix`]: #pathposix
[`path.sep`]: #pathsep
[`path.win32`]: #pathwin32
[namespace-prefixed path]: https://docs.microsoft.com/en-us/windows/desktop/FileIO/naming-a-file#namespaces
