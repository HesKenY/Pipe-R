# Python subprocess (1/5)
source: https://github.com/python/cpython/blob/main/Doc/library/subprocess.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
:mod:`!subprocess` --- Subprocess management
============================================

.. module:: subprocess
   :synopsis: Subprocess management.

**Source code:** :source:`Lib/subprocess.py`

--------------

The :mod:`!subprocess` module allows you to spawn new processes, connect to their
input/output/error pipes, and obtain their return codes.  This module intends to
replace several older modules and functions::

os.system
   os.spawn*

Information about how the :mod:`!subprocess` module can be used to replace these
modules and functions can be found in the following sections.

.. seealso::

:pep:`324` -- PEP proposing the subprocess module

.. include:: ../includes/wasm-mobile-notavail.rst

Using the :mod:`!subprocess` Module
-----------------------------------

The recommended approach to invoking subprocesses is to use the :func:`run`
function for all use cases it can handle. For more advanced use cases, the
underlying :class:`Popen` interface can be used directly.

.. function:: run(args, *, stdin=None, input=None, stdout=None, stderr=None,\
                  capture_output=False, shell=False, cwd=None, timeout=None, \
                  check=False, encoding=None, errors=None, text=None, env=None, \
                  universal_newlines=None, **other_popen_kwargs)

Run the command described by *args*.  Wait for command to complete, then
   return a :class:`CompletedProcess` instance.

The arguments shown above are merely the most common ones, described below
   in :ref:`frequently-used-arguments` (hence the use of keyword-only notation
   in the abbreviated signature). The full function signature is largely the
   same as that of the :class:`Popen` constructor - most of the arguments to
   this function are passed through to that interface. (*timeout*,  *input*,
   *check*, and *capture_output* are not.)

If *capture_output* is true, stdout and stderr will be captured.
   When used, the internal :class:`Popen` object is automatically created with
   *stdout* and *stderr* both set to :data:`~subprocess.PIPE`.
   The *stdout* and *stderr* arguments may not be supplied at the same time as *capture_output*.
   If you wish to capture and combine both streams into one,
   set *stdout* to :data:`~subprocess.PIPE`
   and *stderr* to :data:`~subprocess.STDOUT`,
   instead of using *capture_output*.

A *timeout* may be specified in seconds, it is internally passed on to
   :meth:`Popen.communicate`. If the timeout expires, the child process will be
   killed and waited for. The :exc:`TimeoutExpired` exception will be
   re-raised after the child process has terminated. The initial process
   creation itself cannot be interrupted on many platform APIs so you are not
   guaranteed to see a timeout exception until at least after however long
   process creation takes.

The *input* argument is passed to :meth:`Popen.communicate` and thus to the
   subprocess's stdin.  If used it must be a byte sequence, or a string if
   *encoding* or *errors* is specified or *text* is true.  When
   used, the internal :class:`Popen` object is automatically created with
   *stdin* set to :data:`~subprocess.PIPE`,
   and the *stdin* argument may not be used as well.

If *check* is true, and the process exits with a non-zero exit code, a
   :exc:`CalledProcessError` exception will be raised. Attributes of that
   exception hold the arguments, the exit code, and stdout and stderr if they
   were captured.

If *encoding* or *errors* are specified, or *text* is true,
   file objects for stdin, stdout and stderr are opened in text mode using the
   specified *encoding* and *errors* or the :class:`io.TextIOWrapper` default.
   The *universal_newlines* argument is equivalent  to *text* and is provided
   for backwards compatibility. By default, file objects are opened in binary mode.

If *env* is not ``None``, it must be a mapping that defines the environment
   variables for the new process; these are used instead of the default
   behavior of inheriting the current process' environment. It is passed
   directly to :class:`Popen`. This mapping can be str to str on any platform
   or bytes to bytes on POSIX platforms much like :data:`os.environ` or
   :data:`os.environb`.

Examples::

>>> subprocess.run(["ls", "-l"])  # doesn't capture output
      CompletedProcess(args=['ls', '-l'], returncode=0)

>>> subprocess.run("exit 1", shell=True, check=True)
      Traceback (most recent call last):
        ...
      subprocess.CalledProcessError: Command 'exit 1' returned non-zero exit status 1

>>> subprocess.run(["ls", "-l", "/dev/null"], capture_output=True)
      CompletedProcess(args=['ls', '-l', '/dev/null'], returncode=0,
      stdout=b'crw-rw-rw- 1 root root 1, 3 Jan 23 16:23 /dev/null\n', stderr=b'')

.. versionadded:: 3.5

.. versionchanged:: 3.6

Added *encoding* and *errors* parameters

.. versionchanged:: 3.7

Added the *text* parameter, as a more understandable alias of *universal_newlines*.
      Added the *capture_output* parameter.

.. versionchanged:: 3.12

Changed Windows shell search order for ``shell=True``. The current
      directory and ``%PATH%`` are replaced with ``%COMSPEC%`` and
      ``%SystemRoot%\System32\cmd.exe``. As a result, dropping a
      malicious program named ``cmd.exe`` into a current directory no
      longer works.

.. class:: CompletedProcess

The return value from :func:`run`, representing a process that has finished.

.. attribute:: args

The arguments used to launch the process. This may be a list or a string.

.. attribute:: returncode

Exit status of the child process. Typically, an exit status of 0 indicates
      that it ran successfully.

A negative value ``-N`` indicates that the child was terminated by signal
      ``N`` (POSIX only).

.. attribute:: stdout

Captured stdout from the child process. A bytes sequence, or a string if
      :func:`run` was called with an encoding, errors, or text=True.
      ``None`` if stdout was not captured.

If you ran the process with ``stderr=subprocess.STDOUT``, stdout and
      stderr will be combined in this attribute, and :attr:`stderr` will be
      ``None``.

.. attribute:: stderr

Captured stderr from the child process. A bytes sequence, or a string if
      :func:`run` was called with an encoding, errors, or text=True.
      ``None`` if stderr was not captured.

.. method:: check_returncode()

If :attr:`returncode` is non-zero, raise a :exc:`CalledProcessError`.

.. versionadded:: 3.5

.. data:: DEVNULL

Special value that can be used as the *stdin*, *stdout* or *stderr* argument
   to :class:`Popen` and indicates that the special file :data:`os.devnull`
   will be used.

.. versionadded:: 3.3

.. data:: PIPE

Special value that can be used as the *stdin*, *stdout* or *stderr* argument
   to :class:`Popen` and indicates that a pipe to the standard stream should be
   opened.  Most useful with :meth:`Popen.communicate`.

.. data:: STDOUT

Special value that can be used as the *stderr* argument to :class:`Popen` and
   indicates that standard error should go into the same handle as standard
   output.

.. exception:: SubprocessError

Base class for all other exceptions from this module.

.. versionadded:: 3.3

.. exception:: TimeoutExpired

Subclass of :exc:`SubprocessError`, raised when a timeout expires
    while waiting for a child process.

.. attribute:: cmd

Command that was used to spawn the child process.

.. attribute:: timeout

Timeout in seconds.

.. attribute:: output

Output of the child process if it was captured by :func:`run` or
        :func:`check_output`.  Otherwise, ``None``.  This is always
        :class:`bytes` when any output was captured regardless of the
        ``text=True`` setting.  It may remain ``None`` instead of ``b''``
        when no output was observed.

.. attribute:: stdout

Alias for output, for symmetry with :attr:`stderr`.

.. attribute:: stderr

Stderr output of the child process if it was captured by :func:`run`.
        Otherwise, ``None``.  This is always :class:`bytes` when stderr output
        was captured regardless of the ``text=True`` setting.  It may remain
        ``None`` instead of ``b''`` when no stderr output was observed.

.. versionadded:: 3.3

.. versionchanged:: 3.5
        *stdout* and *stderr* attributes added

.. exception:: CalledProcessError

Subclass of :exc:`SubprocessError`, raised when a process run by
    :func:`check_call`, :func:`check_output`, or :func:`run` (with ``check=True``)
    returns a non-zero exit status.

.. attribute:: returncode

Exit status of the child process.  If the process exited due to a
        signal, this will be the negative signal number.

.. attribute:: cmd

Command that was used to spawn the child process.

.. attribute:: output

Output of the child process if it was captured by :func:`run` or
        :func:`check_output`.  Otherwise, ``None``.

.. attribute:: stdout

Alias for output, for symmetry with :attr:`stderr`.

.. attribute:: stderr

Stderr output of the child process if it was captured by :func:`run`.
        Otherwise, ``None``.

.. versionchanged:: 3.5
        *stdout* and *stderr* attributes added

.. _frequently-used-arguments:

Frequently Used Arguments
^^^^^^^^^^^^^^^^^^^^^^^^^

To support a wide variety of use cases, the :class:`Popen` constructor (and
the convenience functions) accept a large number of optional arguments. For
most typical use cases, many of these arguments can be safely left at their
default values. The arguments that are most commonly needed are:

*args* is required for all calls and should be a string, or a sequence of
   program arguments. Providing a sequence of arguments is generally
   preferred, as it allows the module to take care of any required escaping
   and quoting of arguments (e.g. to permit spaces in file names). If passing
   a single string, either *shell* must be :const:`True` (see below) or else
   the string must simply name the program to be executed without specifying
   any arguments.

*stdin*, *stdout* and *stderr* specify the executed program's standard input,
   standard output and standard error file handles, respectively.  Valid values
   are ``None``, :data:`PIPE`, :data:`DEVNULL`, an existing file descriptor (a
   positive integer), and an existing :term:`file object` with a valid file
   descriptor.  With the default settings of ``None``, no redirection will
   occur.  :data:`PIPE` indicates that a new pipe to the child should be
   created.  :data:`DEVNULL` indicates that the special file :data:`os.devnull`
   will be used.  Additionally, *stderr* can be :data:`STDOUT`, which indicates
   that the stderr data from the child process should be captured into the same
   file handle as for *stdout*.

.. index::
      single: universal newlines; subprocess module

If *encoding* or *errors* are specified, or *text* (also known as
   *universal_newlines*) is true,
   the file objects *stdin*, *stdout* and *stderr* will be opened in text
   mode using the *encoding* and *errors* specified in the call or the
   defaults for :class:`io.TextIOWrapper`.

For *stdin*, line ending characters ``'\n'`` in the input will be converted
   to the default line separator :data:`os.linesep`. For *stdout* and *stderr*,
   all line endings in the output will be converted to ``'\n'``.  For more
   information see the documentation of the :class:`io.TextIOWrapper` class
   when the *newline* argument to its constructor is ``None``.

If text mode is not used, *stdin*, *stdout* and *stderr* will be opened as
   binary streams. No encoding or line ending conversion is performed.

.. versionchanged:: 3.6
      Added the *encoding* and *errors* parameters.

.. versionchanged:: 3.7
      Added the *text* parameter as an alias for *universal_newlines*.

.. note::

The newlines attribute of the file objects :attr:`Popen.stdin`,
      :attr:`Popen.stdout` and :attr:`Popen.stderr` are not updated by
      the :meth:`Popen.communicate` method.

If *shell* is ``True``, the specified command will be executed through
   the shell.  This can be useful if you are using Python primarily for the
   enhanced control flow it offers over most system shells and still want
   convenient access to other shell features such as shell pipes, filename
   wildcards, environment variable expansion, and expansion of ``~`` to a
   user's home directory.  However, note that Python itself offers
   implementations of many shell-like features (in particular, :mod:`glob`,
   :mod:`fnmatch`, :func:`os.walk`, :func:`os.path.expandvars`,
   :func:`os.path.expanduser`, and :mod:`shutil`).

.. versionchanged:: 3.3
      When *universal_newlines* is ``True``, the class uses the encoding
      :func:`locale.getpreferredencoding(False) <locale.getpreferredencoding>`
      instead of ``locale.getpreferredencoding()``.  See the
      :class:`io.TextIOWrapper` class for more information on this change.

.. note::

Read the `Security Considerations`_ section before using ``shell=True``.

These options, along with all of the other options, are described in more
detail in the :class:`Popen` constructor documentation.

Popen Constructor
^^^^^^^^^^^^^^^^^

The underlying process creation and management in this module is handled by
the :class:`Popen` class. It offers a lot of flexibility so that developers
are able to handle the less common cases not covered by the convenience
functions.

.. class:: Popen(args, bufsize=-1, executable=None, stdin=None, stdout=None, \
                 stderr=None, preexec_fn=None, close_fds=True, shell=False, \
                 cwd=None, env=None, universal_newlines=None, \
                 startupinfo=None, creationflags=0, restore_signals=True, \
                 start_new_session=False, pass_fds=(), *, group=None, \
                 extra_groups=None, user=None, umask=-1, \
                 encoding=None, errors=None, text=None, pipesize=-1, \
                 process_group=None)
