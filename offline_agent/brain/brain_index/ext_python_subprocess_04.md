# Python subprocess (4/5)
source: https://github.com/python/cpython/blob/main/Doc/library/subprocess.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
:class:`STARTUPINFO`
      attributes are used when the process creates a window. ::

si = subprocess.STARTUPINFO()
         si.dwFlags = subprocess.STARTF_USESTDHANDLES | subprocess.STARTF_USESHOWWINDOW

.. attribute:: hStdInput

If :attr:`dwFlags` specifies :data:`STARTF_USESTDHANDLES`, this attribute
      is the standard input handle for the process. If
      :data:`STARTF_USESTDHANDLES` is not specified, the default for standard
      input is the keyboard buffer.

.. attribute:: hStdOutput

If :attr:`dwFlags` specifies :data:`STARTF_USESTDHANDLES`, this attribute
      is the standard output handle for the process. Otherwise, this attribute
      is ignored and the default for standard output is the console window's
      buffer.

.. attribute:: hStdError

If :attr:`dwFlags` specifies :data:`STARTF_USESTDHANDLES`, this attribute
      is the standard error handle for the process. Otherwise, this attribute is
      ignored and the default for standard error is the console window's buffer.

.. attribute:: wShowWindow

If :attr:`dwFlags` specifies :data:`STARTF_USESHOWWINDOW`, this attribute
      can be any of the values that can be specified in the ``nCmdShow``
      parameter for the
      `ShowWindow <https://msdn.microsoft.com/en-us/library/ms633548(v=vs.85).aspx>`__
      function, except for ``SW_SHOWDEFAULT``. Otherwise, this attribute is
      ignored.

:data:`SW_HIDE` is provided for this attribute. It is used when
      :class:`Popen` is called with ``shell=True``.

.. attribute:: lpAttributeList

A dictionary of additional attributes for process creation as given in
      ``STARTUPINFOEX``, see
      `UpdateProcThreadAttribute <https://msdn.microsoft.com/en-us/library/windows/desktop/ms686880(v=vs.85).aspx>`__.

Supported attributes:

**handle_list**
         Sequence of handles that will be inherited. *close_fds* must be true if
         non-empty.

The handles must be temporarily made inheritable by
         :func:`os.set_handle_inheritable` when passed to the :class:`Popen`
         constructor, else :class:`OSError` will be raised with Windows error
         ``ERROR_INVALID_PARAMETER`` (87).

.. warning::

In a multithreaded process, use caution to avoid leaking handles
            that are marked inheritable when combining this feature with
            concurrent calls to other process creation functions that inherit
            all handles such as :func:`os.system`.  This also applies to
            standard handle redirection, which temporarily creates inheritable
            handles.

.. versionadded:: 3.7

Windows Constants
^^^^^^^^^^^^^^^^^

The :mod:`!subprocess` module exposes the following constants.

.. data:: STD_INPUT_HANDLE

The standard input device. Initially, this is the console input buffer,
   ``CONIN$``.

.. data:: STD_OUTPUT_HANDLE

The standard output device. Initially, this is the active console screen
   buffer, ``CONOUT$``.

.. data:: STD_ERROR_HANDLE

The standard error device. Initially, this is the active console screen
   buffer, ``CONOUT$``.

.. data:: SW_HIDE

Hides the window. Another window will be activated.

.. data:: STARTF_USESTDHANDLES

Specifies that the :attr:`STARTUPINFO.hStdInput`,
   :attr:`STARTUPINFO.hStdOutput`, and :attr:`STARTUPINFO.hStdError` attributes
   contain additional information.

.. data:: STARTF_USESHOWWINDOW

Specifies that the :attr:`STARTUPINFO.wShowWindow` attribute contains
   additional information.

.. data:: STARTF_FORCEONFEEDBACK

A :attr:`STARTUPINFO.dwFlags` parameter to specify that the
   *Working in Background* mouse cursor will be displayed while a
   process is launching. This is the default behavior for GUI
   processes.

.. versionadded:: 3.13

.. data:: STARTF_FORCEOFFFEEDBACK

A :attr:`STARTUPINFO.dwFlags` parameter to specify that the mouse
   cursor will not be changed when launching a process.

.. versionadded:: 3.13

.. data:: CREATE_NEW_CONSOLE

The new process has a new console, instead of inheriting its parent's
   console (the default).

.. data:: CREATE_NEW_PROCESS_GROUP

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   group will be created. This flag is necessary for using :func:`os.kill`
   on the subprocess.

This flag is ignored if :data:`CREATE_NEW_CONSOLE` is specified.

.. data:: ABOVE_NORMAL_PRIORITY_CLASS

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   will have an above average priority.

.. versionadded:: 3.7

.. data:: BELOW_NORMAL_PRIORITY_CLASS

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   will have a below average priority.

.. versionadded:: 3.7

.. data:: HIGH_PRIORITY_CLASS

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   will have a high priority.

.. versionadded:: 3.7

.. data:: IDLE_PRIORITY_CLASS

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   will have an idle (lowest) priority.

.. versionadded:: 3.7

.. data:: NORMAL_PRIORITY_CLASS

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   will have a normal priority. (default)

.. versionadded:: 3.7

.. data:: REALTIME_PRIORITY_CLASS

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   will have realtime priority.
   You should almost never use REALTIME_PRIORITY_CLASS, because this interrupts
   system threads that manage mouse input, keyboard input, and background disk
   flushing. This class can be appropriate for applications that "talk" directly
   to hardware or that perform brief tasks that should have limited interruptions.

.. versionadded:: 3.7

.. data:: CREATE_NO_WINDOW

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   will not create a window.

.. versionadded:: 3.7

.. data:: DETACHED_PROCESS

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   will not inherit its parent's console.
   This value cannot be used with CREATE_NEW_CONSOLE.

.. versionadded:: 3.7

.. data:: CREATE_DEFAULT_ERROR_MODE

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   does not inherit the error mode of the calling process. Instead, the new
   process gets the default error mode.
   This feature is particularly useful for multithreaded shell applications
   that run with hard errors disabled.

.. versionadded:: 3.7

.. data:: CREATE_BREAKAWAY_FROM_JOB

A :class:`Popen` ``creationflags`` parameter to specify that a new process
   is not associated with the job.

.. versionadded:: 3.7

.. _call-function-trio:

Older high-level API
--------------------

Prior to Python 3.5, these three functions comprised the high level API to
subprocess. You can now use :func:`run` in many cases, but lots of existing code
calls these functions.

.. function:: call(args, *, stdin=None, stdout=None, stderr=None, \
                   shell=False, cwd=None, timeout=None, **other_popen_kwargs)

Run the command described by *args*.  Wait for command to complete, then
   return the :attr:`~Popen.returncode` attribute.

Code needing to capture stdout or stderr should use :func:`run` instead::

run(...).returncode

To suppress stdout or stderr, supply a value of :data:`DEVNULL`.

The arguments shown above are merely some common ones.
   The full function signature is the
   same as that of the :class:`Popen` constructor - this function passes all
   supplied arguments other than *timeout* directly through to that interface.

.. note::

Do not use ``stdout=PIPE`` or ``stderr=PIPE`` with this
      function.  The child process will block if it generates enough
      output to a pipe to fill up the OS pipe buffer as the pipes are
      not being read from.

.. versionchanged:: 3.3
      *timeout* was added.

.. versionchanged:: 3.12

Changed Windows shell search order for ``shell=True``. The current
      directory and ``%PATH%`` are replaced with ``%COMSPEC%`` and
      ``%SystemRoot%\System32\cmd.exe``. As a result, dropping a
      malicious program named ``cmd.exe`` into a current directory no
      longer works.

.. function:: check_call(args, *, stdin=None, stdout=None, stderr=None, \
                         shell=False, cwd=None, timeout=None, \
                         **other_popen_kwargs)

Run command with arguments.  Wait for command to complete. If the return
   code was zero then return, otherwise raise :exc:`CalledProcessError`. The
   :exc:`CalledProcessError` object will have the return code in the
   :attr:`~CalledProcessError.returncode` attribute.
   If :func:`check_call` was unable to start the process it will propagate the exception
   that was raised.

Code needing to capture stdout or stderr should use :func:`run` instead::

run(..., check=True)

To suppress stdout or stderr, supply a value of :data:`DEVNULL`.

The arguments shown above are merely some common ones.
   The full function signature is the
   same as that of the :class:`Popen` constructor - this function passes all
   supplied arguments other than *timeout* directly through to that interface.

.. note::

Do not use ``stdout=PIPE`` or ``stderr=PIPE`` with this
      function.  The child process will block if it generates enough
      output to a pipe to fill up the OS pipe buffer as the pipes are
      not being read from.

.. versionchanged:: 3.3
      *timeout* was added.

.. versionchanged:: 3.12

Changed Windows shell search order for ``shell=True``. The current
      directory and ``%PATH%`` are replaced with ``%COMSPEC%`` and
      ``%SystemRoot%\System32\cmd.exe``. As a result, dropping a
      malicious program named ``cmd.exe`` into a current directory no
      longer works.

.. function:: check_output(args, *, stdin=None, stderr=None, shell=False, \
                           cwd=None, encoding=None, errors=None, \
                           universal_newlines=None, timeout=None, text=None, \
                           **other_popen_kwargs)

Run command with arguments and return its output.

If the return code was non-zero it raises a :exc:`CalledProcessError`. The
   :exc:`CalledProcessError` object will have the return code in the
   :attr:`~CalledProcessError.returncode` attribute and any output in the
   :attr:`~CalledProcessError.output` attribute.

This is equivalent to::

run(..., check=True, stdout=PIPE).stdout

The arguments shown above are merely some common ones.
   The full function signature is largely the same as that of :func:`run` -
   most arguments are passed directly through to that interface.
   One API deviation from :func:`run` behavior exists: passing ``input=None``
   will behave the same as ``input=b''`` (or ``input=''``, depending on other
   arguments) rather than using the parent's standard input file handle.

By default, this function will return the data as encoded bytes. The actual
   encoding of the output data may depend on the command being invoked, so the
   decoding to text will often need to be handled at the application level.

This behaviour may be overridden by setting *text*, *encoding*, *errors*,
   or *universal_newlines* to ``True`` as described in
   :ref:`frequently-used-arguments` and :func:`run`.

To also capture standard error in the result, use
   ``stderr=subprocess.STDOUT``::

>>> subprocess.check_output(
      ...     "ls non_existent_file; exit 0",
      ...     stderr=subprocess.STDOUT,
      ...     shell=True)
      'ls: non_existent_file: No such file or directory\n'

.. versionadded:: 3.1

.. versionchanged:: 3.3
      *timeout* was added.

.. versionchanged:: 3.4
      Support for the *input* keyword argument was added.

.. versionchanged:: 3.6
      *encoding* and *errors* were added.  See :func:`run` for details.

.. versionadded:: 3.7
      *text* was added as a more readable alias for *universal_newlines*.

.. versionchanged:: 3.12

Changed Windows shell search order for ``shell=True``. The current
      directory and ``%PATH%`` are replaced with ``%COMSPEC%`` and
      ``%SystemRoot%\System32\cmd.exe``. As a result, dropping a
      malicious program named ``cmd.exe`` into a current directory no
      longer works.

.. _subprocess-replacements:

Replacing Older Functions with the :mod:`!subprocess` Module
------------------------------------------------------------

In this section, "a becomes b" means that b can be used as a replacement for a.

.. note::

All "a" functions in this section fail (more or less) silently if the
   executed program cannot be found; the "b" replacements raise :exc:`OSError`
   instead.

In addition, the replacements using :func:`check_output` will fail with a
   :exc:`CalledProcessError` if the requested operation produces a non-zero
   return code. The output is still available as the
   :attr:`~CalledProcessError.output` attribute of the raised exception.

In the following examples, we assume that the relevant functions have already
been imported from the :mod:`!subprocess` module.

Replacing :program:`/bin/sh` shell command substitution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

output=$(mycmd myarg)

becomes::

output = check_output(["mycmd", "myarg"])

Replacing shell pipeline
^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

output=$(dmesg | grep hda)

becomes::

p1 = Popen(["dmesg"], stdout=PIPE)
   p2 = Popen(["grep", "hda"], stdin=p1.stdout, stdout=PIPE)
   p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
   output = p2.communicate()[0]

The ``p1.stdout.close()`` call after starting the p2 is important in order for
p1 to receive a SIGPIPE if p2 exits before p1.

Alternatively, for trusted input, the shell's own pipeline support may still
be used directly:

.. code-block:: bash

output=$(dmesg | grep hda)

becomes::

output = check_output("dmesg | grep hda", shell=True)

Replacing :func:`os.system`
^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

sts = os.system("mycmd" + " myarg")
   # becomes
   retcode = call("mycmd" + " myarg", shell=True)

Notes:
