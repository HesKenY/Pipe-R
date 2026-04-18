# Python pathlib (2/5)
source: https://github.com/python/cpython/blob/main/Doc/library/pathlib.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
gle dot ("``.``") is considered a valid suffix.

.. attribute:: PurePath.stem

The final path component, without its suffix::

>>> PurePosixPath('my/library.tar.gz').stem
      'library.tar'
      >>> PurePosixPath('my/library.tar').stem
      'library'
      >>> PurePosixPath('my/library').stem
      'library'

.. versionchanged:: 3.14

A single dot ("``.``") is considered a valid suffix.

.. method:: PurePath.as_posix()

Return a string representation of the path with forward slashes (``/``)::

>>> p = PureWindowsPath('c:\\windows')
      >>> str(p)
      'c:\\windows'
      >>> p.as_posix()
      'c:/windows'

.. method:: PurePath.is_absolute()

Return whether the path is absolute or not.  A path is considered absolute
   if it has both a root and (if the flavour allows) a drive::

>>> PurePosixPath('/a/b').is_absolute()
      True
      >>> PurePosixPath('a/b').is_absolute()
      False

>>> PureWindowsPath('c:/a/b').is_absolute()
      True
      >>> PureWindowsPath('/a/b').is_absolute()
      False
      >>> PureWindowsPath('c:').is_absolute()
      False
      >>> PureWindowsPath('//some/share').is_absolute()
      True

.. method:: PurePath.is_relative_to(other)

Return whether or not this path is relative to the *other* path.

>>> p = PurePath('/etc/passwd')
      >>> p.is_relative_to('/etc')
      True
      >>> p.is_relative_to('/usr')
      False

This method is string-based; it neither accesses the filesystem nor treats
   "``..``" segments specially. The following code is equivalent:

>>> u = PurePath('/usr')
      >>> u == p or u in p.parents
      False

.. versionadded:: 3.9

.. deprecated-removed:: 3.12 3.14

Passing additional arguments is deprecated; if supplied, they are joined
      with *other*.

.. method:: PurePath.joinpath(*pathsegments)

Calling this method is equivalent to combining the path with each of
   the given *pathsegments* in turn::

>>> PurePosixPath('/etc').joinpath('passwd')
      PurePosixPath('/etc/passwd')
      >>> PurePosixPath('/etc').joinpath(PurePosixPath('passwd'))
      PurePosixPath('/etc/passwd')
      >>> PurePosixPath('/etc').joinpath('init.d', 'apache2')
      PurePosixPath('/etc/init.d/apache2')
      >>> PureWindowsPath('c:').joinpath('/Program Files')
      PureWindowsPath('c:/Program Files')

.. method:: PurePath.full_match(pattern, *, case_sensitive=None)

Match this path against the provided glob-style pattern.  Return ``True``
   if matching is successful, ``False`` otherwise.  For example::

>>> PurePath('a/b.py').full_match('a/*.py')
      True
      >>> PurePath('a/b.py').full_match('*.py')
      False
      >>> PurePath('/a/b/c.py').full_match('/a/**')
      True
      >>> PurePath('/a/b/c.py').full_match('**/*.py')
      True

.. seealso::
      :ref:`pathlib-pattern-language` documentation.

As with other methods, case-sensitivity follows platform defaults::

>>> PurePosixPath('b.py').full_match('*.PY')
      False
      >>> PureWindowsPath('b.py').full_match('*.PY')
      True

Set *case_sensitive* to ``True`` or ``False`` to override this behaviour.

.. versionadded:: 3.13

.. method:: PurePath.match(pattern, *, case_sensitive=None)

Match this path against the provided non-recursive glob-style pattern.
   Return ``True`` if matching is successful, ``False`` otherwise.

This method is similar to :meth:`~PurePath.full_match`, but empty patterns
   aren't allowed (:exc:`ValueError` is raised), the recursive wildcard
   "``**``" isn't supported (it acts like non-recursive "``*``"), and if a
   relative pattern is provided, then matching is done from the right::

>>> PurePath('a/b.py').match('*.py')
      True
      >>> PurePath('/a/b/c.py').match('b/*.py')
      True
      >>> PurePath('/a/b/c.py').match('a/*.py')
      False

.. versionchanged:: 3.12
      The *pattern* parameter accepts a :term:`path-like object`.

.. versionchanged:: 3.12
      The *case_sensitive* parameter was added.

.. method:: PurePath.relative_to(other, walk_up=False)

Compute a version of this path relative to the path represented by
   *other*.  If it's impossible, :exc:`ValueError` is raised::

>>> p = PurePosixPath('/etc/passwd')
      >>> p.relative_to('/')
      PurePosixPath('etc/passwd')
      >>> p.relative_to('/etc')
      PurePosixPath('passwd')
      >>> p.relative_to('/usr')
      Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "pathlib.py", line 941, in relative_to
          raise ValueError(error_message.format(str(self), str(formatted)))
      ValueError: '/etc/passwd' is not in the subpath of '/usr' OR one path is relative and the other is absolute.

When *walk_up* is false (the default), the path must start with *other*.
   When the argument is true, ``..`` entries may be added to form the
   relative path. In all other cases, such as the paths referencing
   different drives, :exc:`ValueError` is raised.::

>>> p.relative_to('/usr', walk_up=True)
      PurePosixPath('../etc/passwd')
      >>> p.relative_to('foo', walk_up=True)
      Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "pathlib.py", line 941, in relative_to
          raise ValueError(error_message.format(str(self), str(formatted)))
      ValueError: '/etc/passwd' is not on the same drive as 'foo' OR one path is relative and the other is absolute.

.. warning::
      This function is part of :class:`PurePath` and works with strings.
      It does not check or access the underlying file structure.
      This can impact the *walk_up* option as it assumes that no symlinks
      are present in the path; call :meth:`~Path.resolve` first if
      necessary to resolve symlinks.

.. versionchanged:: 3.12
      The *walk_up* parameter was added (old behavior is the same as ``walk_up=False``).

.. deprecated-removed:: 3.12 3.14

Passing additional positional arguments is deprecated; if supplied,
      they are joined with *other*.

.. method:: PurePath.with_name(name)

Return a new path with the :attr:`name` changed.  If the original path
   doesn't have a name, ValueError is raised::

>>> p = PureWindowsPath('c:/Downloads/pathlib.tar.gz')
      >>> p.with_name('setup.py')
      PureWindowsPath('c:/Downloads/setup.py')
      >>> p = PureWindowsPath('c:/')
      >>> p.with_name('setup.py')
      Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "/home/antoine/cpython/default/Lib/pathlib.py", line 751, in with_name
          raise ValueError("%r has an empty name" % (self,))
      ValueError: PureWindowsPath('c:/') has an empty name

.. method:: PurePath.with_stem(stem)

Return a new path with the :attr:`stem` changed.  If the original path
   doesn't have a name, ValueError is raised::

>>> p = PureWindowsPath('c:/Downloads/draft.txt')
      >>> p.with_stem('final')
      PureWindowsPath('c:/Downloads/final.txt')
      >>> p = PureWindowsPath('c:/Downloads/pathlib.tar.gz')
      >>> p.with_stem('lib')
      PureWindowsPath('c:/Downloads/lib.gz')
      >>> p = PureWindowsPath('c:/')
      >>> p.with_stem('')
      Traceback (most recent call last):
        File "<stdin>", line 1, in <module>
        File "/home/antoine/cpython/default/Lib/pathlib.py", line 861, in with_stem
          return self.with_name(stem + self.suffix)
        File "/home/antoine/cpython/default/Lib/pathlib.py", line 851, in with_name
          raise ValueError("%r has an empty name" % (self,))
      ValueError: PureWindowsPath('c:/') has an empty name

.. versionadded:: 3.9

.. method:: PurePath.with_suffix(suffix)

Return a new path with the :attr:`suffix` changed.  If the original path
   doesn't have a suffix, the new *suffix* is appended instead.  If the
   *suffix* is an empty string, the original suffix is removed::

>>> p = PureWindowsPath('c:/Downloads/pathlib.tar.gz')
      >>> p.with_suffix('.bz2')
      PureWindowsPath('c:/Downloads/pathlib.tar.bz2')
      >>> p = PureWindowsPath('README')
      >>> p.with_suffix('.txt')
      PureWindowsPath('README.txt')
      >>> p = PureWindowsPath('README.txt')
      >>> p.with_suffix('')
      PureWindowsPath('README')

.. versionchanged:: 3.14

A single dot ("``.``") is considered a valid suffix. In previous
      versions, :exc:`ValueError` is raised if a single dot is supplied.

.. method:: PurePath.with_segments(*pathsegments)

Create a new path object of the same type by combining the given
   *pathsegments*. This method is called whenever a derivative path is created,
   such as from :attr:`parent` and :meth:`relative_to`. Subclasses may
   override this method to pass information to derivative paths, for example::

from pathlib import PurePosixPath

class MyPath(PurePosixPath):
          def __init__(self, *pathsegments, session_id):
              super().__init__(*pathsegments)
              self.session_id = session_id

def with_segments(self, *pathsegments):
              return type(self)(*pathsegments, session_id=self.session_id)

etc = MyPath('/etc', session_id=42)
      hosts = etc / 'hosts'
      print(hosts.session_id)  # 42

.. versionadded:: 3.12

.. _concrete-paths:

Concrete paths
--------------

Concrete paths are subclasses of the pure path classes.  In addition to
operations provided by the latter, they also provide methods to do system
calls on path objects.  There are three ways to instantiate concrete paths:

.. class:: Path(*pathsegments)

A subclass of :class:`PurePath`, this class represents concrete paths of
   the system's path flavour (instantiating it creates either a
   :class:`PosixPath` or a :class:`WindowsPath`)::

>>> Path('setup.py')
      PosixPath('setup.py')

*pathsegments* is specified similarly to :class:`PurePath`.

.. class:: PosixPath(*pathsegments)

A subclass of :class:`Path` and :class:`PurePosixPath`, this class
   represents concrete non-Windows filesystem paths::

>>> PosixPath('/etc/hosts')
      PosixPath('/etc/hosts')

*pathsegments* is specified similarly to :class:`PurePath`.

.. versionchanged:: 3.13
      Raises :exc:`UnsupportedOperation` on Windows. In previous versions,
      :exc:`NotImplementedError` was raised instead.

.. class:: WindowsPath(*pathsegments)

A subclass of :class:`Path` and :class:`PureWindowsPath`, this class
   represents concrete Windows filesystem paths::

>>> WindowsPath('c:/', 'Users', 'Ximénez')
      WindowsPath('c:/Users/Ximénez')

*pathsegments* is specified similarly to :class:`PurePath`.

.. versionchanged:: 3.13
      Raises :exc:`UnsupportedOperation` on non-Windows platforms. In previous
      versions, :exc:`NotImplementedError` was raised instead.

You can only instantiate the class flavour that corresponds to your system
(allowing system calls on non-compatible path flavours could lead to
bugs or failures in your application)::

>>> import os
   >>> os.name
   'posix'
   >>> Path('setup.py')
   PosixPath('setup.py')
   >>> PosixPath('setup.py')
   PosixPath('setup.py')
   >>> WindowsPath('setup.py')
   Traceback (most recent call last):
     File "<stdin>", line 1, in <module>
     File "pathlib.py", line 798, in __new__
       % (cls.__name__,))
   UnsupportedOperation: cannot instantiate 'WindowsPath' on your system

Some concrete path methods can raise an :exc:`OSError` if a system call fails
(for example because the path doesn't exist).

Parsing and generating URIs
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Concrete path objects can be created from, and represented as, 'file' URIs
conforming to :rfc:`8089`.

.. note::

File URIs are not portable across machines with different
   :ref:`filesystem encodings <filesystem-encoding>`.

.. classmethod:: Path.from_uri(uri)

Return a new path object from parsing a 'file' URI. For example::

>>> p = Path.from_uri('file:///etc/hosts')
      PosixPath('/etc/hosts')

On Windows, DOS device and UNC paths may be parsed from URIs::

>>> p = Path.from_uri('file:///c:/windows')
      WindowsPath('c:/windows')
      >>> p = Path.from_uri('file://server/share')
      WindowsPath('//server/share')

Several variant forms are supported::

>>> p = Path.from_uri('file:////server/share')
      WindowsPath('//server/share')
      >>> p = Path.from_uri('file://///server/share')
      WindowsPath('//server/share')
      >>> p = Path.from_uri('file:c:/windows')
      WindowsPath('c:/windows')
      >>> p = Path.from_uri('file:/c|/windows')
      WindowsPath('c:/windows')

:exc:`ValueError` is raised if the URI does not start with ``file:``, or
   the parsed path isn't absolute.

.. versionadded:: 3.13

.. versionchanged:: 3.14
      The URL authority is discarded if it matches the local hostname.
      Otherwise, if the authority isn't empty or ``localhost``, then on
      Windows a UNC path is returned (as before), and on other platforms a
      :exc:`ValueError` is raised.

.. method:: Path.as_uri()

Represent the path as a 'file' URI.  :exc:`ValueError` is raised if
   the path isn't absolute.

.. code-block:: pycon

>>> p = PosixPath('/etc/passwd')
      >>> p.as_uri()
      'file:///etc/passwd'
      >>> p = WindowsPath('c:/Windows')
      >>> p.as_uri()
      'file:///c:/Windows'

.. deprecated-removed:: 3.14 3.19

Calling this method from :class:`PurePath` rather than :class:`Path` is
      possible but deprecated. The method's use of :func:`os.fsencode` makes
      it strictly impure.

Expanding and resolving paths
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. classmethod:: Path.home()

Return a new path object representing the user's home directory (as
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
