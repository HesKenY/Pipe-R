# Python pathlib (3/5)
source: https://github.com/python/cpython/blob/main/Doc/library/pathlib.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
urn a new path object representing the user's home directory (as
   returned by :func:`os.path.expanduser` with ``~`` construct). If the home
   directory can't be resolved, :exc:`RuntimeError` is raised.

::

>>> Path.home()
      PosixPath('/home/antoine')

.. versionadded:: 3.5

.. method:: Path.expanduser()

Return a new path with expanded ``~`` and ``~user`` constructs,
   as returned by :meth:`os.path.expanduser`. If a home directory can't be
   resolved, :exc:`RuntimeError` is raised.

::

>>> p = PosixPath('~/films/Monty Python')
      >>> p.expanduser()
      PosixPath('/home/eric/films/Monty Python')

.. versionadded:: 3.5

.. classmethod:: Path.cwd()

Return a new path object representing the current directory (as returned
   by :func:`os.getcwd`)::

>>> Path.cwd()
      PosixPath('/home/antoine/pathlib')

.. method:: Path.absolute()

Make the path absolute, without normalization or resolving symlinks.
   Returns a new path object::

>>> p = Path('tests')
      >>> p
      PosixPath('tests')
      >>> p.absolute()
      PosixPath('/home/antoine/pathlib/tests')

.. method:: Path.resolve(strict=False)

Make the path absolute, resolving any symlinks.  A new path object is
   returned::

>>> p = Path()
      >>> p
      PosixPath('.')
      >>> p.resolve()
      PosixPath('/home/antoine/pathlib')

"``..``" components are also eliminated (this is the only method to do so)::

>>> p = Path('docs/../setup.py')
      >>> p.resolve()
      PosixPath('/home/antoine/pathlib/setup.py')

If a path doesn't exist or a symlink loop is encountered, and *strict* is
   ``True``, :exc:`OSError` is raised.  If *strict* is ``False``, the path is
   resolved as far as possible and any remainder is appended without checking
   whether it exists.

.. versionchanged:: 3.6
      The *strict* parameter was added (pre-3.6 behavior is strict).

.. versionchanged:: 3.13
      Symlink loops are treated like other errors: :exc:`OSError` is raised in
      strict mode, and no exception is raised in non-strict mode. In previous
      versions, :exc:`RuntimeError` is raised no matter the value of *strict*.

.. method:: Path.readlink()

Return the path to which the symbolic link points (as returned by
   :func:`os.readlink`)::

>>> p = Path('mylink')
      >>> p.symlink_to('setup.py')
      >>> p.readlink()
      PosixPath('setup.py')

.. versionadded:: 3.9

.. versionchanged:: 3.13
      Raises :exc:`UnsupportedOperation` if :func:`os.readlink` is not
      available. In previous versions, :exc:`NotImplementedError` was raised.

Querying file type and status
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. versionchanged:: 3.8

:meth:`~Path.exists`, :meth:`~Path.is_dir`, :meth:`~Path.is_file`,
   :meth:`~Path.is_mount`, :meth:`~Path.is_symlink`,
   :meth:`~Path.is_block_device`, :meth:`~Path.is_char_device`,
   :meth:`~Path.is_fifo`, :meth:`~Path.is_socket` now return ``False``
   instead of raising an exception for paths that contain characters
   unrepresentable at the OS level.

.. versionchanged:: 3.14

The methods given above now return ``False`` instead of raising any
   :exc:`OSError` exception from the operating system. In previous versions,
   some kinds of :exc:`OSError` exception are raised, and others suppressed.
   The new behaviour is consistent with :func:`os.path.exists`,
   :func:`os.path.isdir`, etc. Use :meth:`~Path.stat` to retrieve the file
   status without suppressing exceptions.

.. method:: Path.stat(*, follow_symlinks=True)

Return an :class:`os.stat_result` object containing information about this path, like :func:`os.stat`.
   The result is looked up at each call to this method.

This method normally follows symlinks; to stat a symlink add the argument
   ``follow_symlinks=False``, or use :meth:`~Path.lstat`.

::

>>> p = Path('setup.py')
      >>> p.stat().st_size
      956
      >>> p.stat().st_mtime
      1327883547.852554

.. versionchanged:: 3.10
      The *follow_symlinks* parameter was added.

.. method:: Path.lstat()

Like :meth:`Path.stat` but, if the path points to a symbolic link, return
   the symbolic link's information rather than its target's.

.. method:: Path.exists(*, follow_symlinks=True)

Return ``True`` if the path points to an existing file or directory.
   ``False`` will be returned if the path is invalid, inaccessible or missing.
   Use :meth:`Path.stat` to distinguish between these cases.

This method normally follows symlinks; to check if a symlink exists, add
   the argument ``follow_symlinks=False``.

::

>>> Path('.').exists()
      True
      >>> Path('setup.py').exists()
      True
      >>> Path('/etc').exists()
      True
      >>> Path('nonexistentfile').exists()
      False

.. versionchanged:: 3.12
      The *follow_symlinks* parameter was added.

.. method:: Path.is_file(*, follow_symlinks=True)

Return ``True`` if the path points to a regular file. ``False`` will be
   returned if the path is invalid, inaccessible or missing, or if it points
   to something other than a regular file. Use :meth:`Path.stat` to
   distinguish between these cases.

This method normally follows symlinks; to exclude symlinks, add the
   argument ``follow_symlinks=False``.

.. versionchanged:: 3.13
      The *follow_symlinks* parameter was added.

.. method:: Path.is_dir(*, follow_symlinks=True)

Return ``True`` if the path points to a directory. ``False`` will be
   returned if the path is invalid, inaccessible or missing, or if it points
   to something other than a directory. Use :meth:`Path.stat` to distinguish
   between these cases.

This method normally follows symlinks; to exclude symlinks to directories,
   add the argument ``follow_symlinks=False``.

.. versionchanged:: 3.13
      The *follow_symlinks* parameter was added.

.. method:: Path.is_symlink()

Return ``True`` if the path points to a symbolic link, even if that symlink
   is broken. ``False`` will be returned if the path is invalid, inaccessible
   or missing, or if it points to something other than a symbolic link. Use
   :meth:`Path.stat` to distinguish between these cases.

.. method:: Path.is_junction()

Return ``True`` if the path points to a junction, and ``False`` for any other
   type of file. Currently only Windows supports junctions.

.. versionadded:: 3.12

.. method:: Path.is_mount()

Return ``True`` if the path is a :dfn:`mount point`: a point in a
   file system where a different file system has been mounted.  On POSIX, the
   function checks whether *path*'s parent, :file:`path/..`, is on a different
   device than *path*, or whether :file:`path/..` and *path* point to the same
   i-node on the same device --- this should detect mount points for all Unix
   and POSIX variants.  On Windows, a mount point is considered to be a drive
   letter root (e.g. ``c:\``), a UNC share (e.g. ``\\server\share``), or a
   mounted filesystem directory.

.. versionadded:: 3.7

.. versionchanged:: 3.12
      Windows support was added.

.. method:: Path.is_socket()

Return ``True`` if the path points to a Unix socket. ``False`` will be
   returned if the path is invalid, inaccessible or missing, or if it points
   to something other than a Unix socket. Use :meth:`Path.stat` to
   distinguish between these cases.

.. method:: Path.is_fifo()

Return ``True`` if the path points to a FIFO. ``False`` will be returned if
   the path is invalid, inaccessible or missing, or if it points to something
   other than a FIFO. Use :meth:`Path.stat` to distinguish between these
   cases.

.. method:: Path.is_block_device()

Return ``True`` if the path points to a block device. ``False`` will be
   returned if the path is invalid, inaccessible or missing, or if it points
   to something other than a block device. Use :meth:`Path.stat` to
   distinguish between these cases.

.. method:: Path.is_char_device()

Return ``True`` if the path points to a character device. ``False`` will be
   returned if the path is invalid, inaccessible or missing, or if it points
   to something other than a character device. Use :meth:`Path.stat` to
   distinguish between these cases.

.. method:: Path.samefile(other_path)

Return whether this path points to the same file as *other_path*, which
   can be either a Path object, or a string.  The semantics are similar
   to :func:`os.path.samefile` and :func:`os.path.samestat`.

An :exc:`OSError` can be raised if either file cannot be accessed for some
   reason.

::

>>> p = Path('spam')
      >>> q = Path('eggs')
      >>> p.samefile(q)
      False
      >>> p.samefile('spam')
      True

.. versionadded:: 3.5

.. attribute:: Path.info

A :class:`~pathlib.types.PathInfo` object that supports querying file type
   information. The object exposes methods that cache their results, which can
   help reduce the number of system calls needed when switching on file type.
   For example::

>>> p = Path('src')
      >>> if p.info.is_symlink():
      ...     print('symlink')
      ... elif p.info.is_dir():
      ...     print('directory')
      ... elif p.info.exists():
      ...     print('something else')
      ... else:
      ...     print('not found')
      ...
      directory

If the path was generated from :meth:`Path.iterdir` then this attribute is
   initialized with some information about the file type gleaned from scanning
   the parent directory. Merely accessing :attr:`Path.info` does not perform
   any filesystem queries.

To fetch up-to-date information, it's best to call :meth:`Path.is_dir`,
   :meth:`~Path.is_file` and :meth:`~Path.is_symlink` rather than methods of
   this attribute. There is no way to reset the cache; instead you can create
   a new path object with an empty info cache via ``p = Path(p)``.

.. versionadded:: 3.14

Reading and writing files
^^^^^^^^^^^^^^^^^^^^^^^^^

.. method:: Path.open(mode='r', buffering=-1, encoding=None, errors=None, newline=None)

Open the file pointed to by the path, like the built-in :func:`open`
   function does::

>>> p = Path('setup.py')
      >>> with p.open() as f:
      ...     f.readline()
      ...
      '#!/usr/bin/env python3\n'

.. method:: Path.read_text(encoding=None, errors=None, newline=None)

Return the decoded contents of the pointed-to file as a string::

>>> p = Path('my_text_file')
      >>> p.write_text('Text file contents')
      18
      >>> p.read_text()
      'Text file contents'

The file is opened and then closed. The optional parameters have the same
   meaning as in :func:`open`.

.. versionadded:: 3.5

.. versionchanged:: 3.13
      The *newline* parameter was added.

.. method:: Path.read_bytes()

Return the binary contents of the pointed-to file as a bytes object::

>>> p = Path('my_binary_file')
      >>> p.write_bytes(b'Binary file contents')
      20
      >>> p.read_bytes()
      b'Binary file contents'

.. versionadded:: 3.5

.. method:: Path.write_text(data, encoding=None, errors=None, newline=None)

Open the file pointed to in text mode, write *data* to it, and close the
   file::

>>> p = Path('my_text_file')
      >>> p.write_text('Text file contents')
      18
      >>> p.read_text()
      'Text file contents'

An existing file of the same name is overwritten. The optional parameters
   have the same meaning as in :func:`open`.

.. versionadded:: 3.5

.. versionchanged:: 3.10
      The *newline* parameter was added.

.. method:: Path.write_bytes(data)

Open the file pointed to in bytes mode, write *data* to it, and close the
   file::

>>> p = Path('my_binary_file')
      >>> p.write_bytes(b'Binary file contents')
      20
      >>> p.read_bytes()
      b'Binary file contents'

An existing file of the same name is overwritten.

.. versionadded:: 3.5

Reading directories
^^^^^^^^^^^^^^^^^^^

.. method:: Path.iterdir()

When the path points to a directory, yield path objects of the directory
   contents::

>>> p = Path('docs')
      >>> for child in p.iterdir(): child
      ...
      PosixPath('docs/conf.py')
      PosixPath('docs/_templates')
      PosixPath('docs/make.bat')
      PosixPath('docs/index.rst')
      PosixPath('docs/_build')
      PosixPath('docs/_static')
      PosixPath('docs/Makefile')

The children are yielded in arbitrary order, and the special entries
   ``'.'`` and ``'..'`` are not included.  If a file is removed from or added
   to the directory after creating the iterator, it is unspecified whether
   a path object for that file is included.

If the path is not a directory or otherwise inaccessible, :exc:`OSError` is
   raised.

.. method:: Path.glob(pattern, *, case_sensitive=None, recurse_symlinks=False)

Glob the given relative *pattern* in the directory represented by this path,
   yielding all matching files (of any kind)::

>>> sorted(Path('.').glob('*.py'))
      [PosixPath('pathlib.py'), PosixPath('setup.py'), PosixPath('test_pathlib.py')]
      >>> sorted(Path('.').glob('*/*.py'))
      [PosixPath('docs/conf.py')]
      >>> sorted(Path('.').glob('**/*.py'))
      [PosixPath('build/lib/pathlib.py'),
       PosixPath('docs/conf.py'),
       PosixPath('pathlib.py'),
       PosixPath('setup.py'),
       PosixPath('test_pathlib.py')]

.. note::
      The paths are returned in no particular order.
      If you need a specific order, sort the results.

.. seealso::
      :ref:`pathlib-pattern-language` documentation.

By default, or when the *case_sensitive* keyword-only argument is set to
   ``None``, this method matches paths using platform-specific casing rules:
   typically, case-sensitive on POSIX, and case-insensitive on Windows.
   Set *case_sensitive* to ``True`` or ``False`` to override this behaviour.

By default, or when the *recurse_symlinks* keyword-only argument is set to
   ``False``, this method follows symlinks except when expanding "``**``"
   wildcards. Set *recurse_symlinks* to ``True`` to always follow symlinks.

.. note::
      Any :exc:`OSError` exceptions raised from scanning the filesystem are
      suppressed. This includes :exc:`PermissionError` when accessing
      directories without read permission.
