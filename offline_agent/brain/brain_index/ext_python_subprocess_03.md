# Python subprocess (3/5)
source: https://github.com/python/cpython/blob/main/Doc/library/subprocess.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
or of inheriting the current process' environment. This mapping can be
   str to str on any platform or bytes to bytes on POSIX platforms much like
   :data:`os.environ` or :data:`os.environb`.

.. note::

If specified, *env* must provide any variables required for the program to
      execute.  On Windows, in order to run a `side-by-side assembly`_ the
      specified *env* **must** include a valid ``%SystemRoot%``.

.. _side-by-side assembly: https://en.wikipedia.org/wiki/Side-by-Side_Assembly

If *encoding* or *errors* are specified, or *text* is true, the file objects
   *stdin*, *stdout* and *stderr* are opened in text mode with the specified
   *encoding* and *errors*, as described above in :ref:`frequently-used-arguments`.
   The *universal_newlines* argument is equivalent  to *text* and is provided
   for backwards compatibility. By default, file objects are opened in binary mode.

.. versionadded:: 3.6
      *encoding* and *errors* were added.

.. versionadded:: 3.7
      *text* was added as a more readable alias for *universal_newlines*.

If given, *startupinfo* will be a :class:`STARTUPINFO` object, which is
   passed to the underlying ``CreateProcess`` function.

If given, *creationflags*, can be one or more of the following flags:

* :data:`CREATE_NEW_CONSOLE`
   * :data:`CREATE_NEW_PROCESS_GROUP`
   * :data:`ABOVE_NORMAL_PRIORITY_CLASS`
   * :data:`BELOW_NORMAL_PRIORITY_CLASS`
   * :data:`HIGH_PRIORITY_CLASS`
   * :data:`IDLE_PRIORITY_CLASS`
   * :data:`NORMAL_PRIORITY_CLASS`
   * :data:`REALTIME_PRIORITY_CLASS`
   * :data:`CREATE_NO_WINDOW`
   * :data:`DETACHED_PROCESS`
   * :data:`CREATE_DEFAULT_ERROR_MODE`
   * :data:`CREATE_BREAKAWAY_FROM_JOB`

*pipesize* can be used to change the size of the pipe when
   :data:`PIPE` is used for *stdin*, *stdout* or *stderr*. The size of the pipe
   is only changed on platforms that support this (only Linux at this time of
   writing). Other platforms will ignore this parameter.

.. versionchanged:: 3.10
      Added the *pipesize* parameter.

Popen objects are supported as context managers via the :keyword:`with` statement:
   on exit, standard file descriptors are closed, and the process is waited for.
   ::

with Popen(["ifconfig"], stdout=PIPE) as proc:
          log.write(proc.stdout.read())

.. audit-event:: subprocess.Popen executable,args,cwd,env subprocess.Popen

Popen and the other functions in this module that use it raise an
      :ref:`auditing event <auditing>` ``subprocess.Popen`` with arguments
      ``executable``, ``args``, ``cwd``, and ``env``. The value for ``args``
      may be a single string or a list of strings, depending on platform.

.. versionchanged:: 3.2
      Added context manager support.

.. versionchanged:: 3.6
      Popen destructor now emits a :exc:`ResourceWarning` warning if the child
      process is still running.

.. versionchanged:: 3.8
      Popen can use :func:`os.posix_spawn` in some cases for better
      performance. On Windows Subsystem for Linux and QEMU User Emulation,
      Popen constructor using :func:`os.posix_spawn` no longer raise an
      exception on errors like missing program, but the child process fails
      with a non-zero :attr:`~Popen.returncode`.

Exceptions
^^^^^^^^^^

Exceptions raised in the child process, before the new program has started to
execute, will be re-raised in the parent.

The most common exception raised is :exc:`OSError`.  This occurs, for example,
when trying to execute a non-existent file.  Applications should prepare for
:exc:`OSError` exceptions. Note that, when ``shell=True``, :exc:`OSError`
will be raised by the child only if the selected shell itself was not found.
To determine if the shell failed to find the requested application, it is
necessary to check the return code or output from the subprocess.

A :exc:`ValueError` will be raised if :class:`Popen` is called with invalid
arguments.

:func:`check_call` and :func:`check_output` will raise
:exc:`CalledProcessError` if the called process returns a non-zero return
code.

All of the functions and methods that accept a *timeout* parameter, such as
:func:`run` and :meth:`Popen.communicate` will raise :exc:`TimeoutExpired` if
the timeout expires before the process exits.

Exceptions defined in this module all inherit from :exc:`SubprocessError`.

.. versionadded:: 3.3
   The :exc:`SubprocessError` base class was added.

.. _subprocess-security:

Security Considerations
-----------------------

Unlike some other popen functions, this library will not
implicitly choose to call a system shell.  This means that all characters,
including shell metacharacters, can safely be passed to child processes.
If the shell is invoked explicitly, via ``shell=True``, it is the application's
responsibility to ensure that all whitespace and metacharacters are
quoted appropriately to avoid
`shell injection <https://en.wikipedia.org/wiki/Shell_injection#Shell_injection>`_
vulnerabilities. On :ref:`some platforms <shlex-quote-warning>`, it is possible
to use :func:`shlex.quote` for this escaping.

On Windows, batch files (:file:`*.bat` or :file:`*.cmd`) may be launched by the
operating system in a system shell regardless of the arguments passed to this
library. This could result in arguments being parsed according to shell rules,
but without any escaping added by Python. If you are intentionally launching a
batch file with arguments from untrusted sources, consider passing
``shell=True`` to allow Python to escape special characters. See :gh:`114539`
for additional discussion.

Popen Objects
-------------

Instances of the :class:`Popen` class have the following methods:

.. method:: Popen.poll()

Check if child process has terminated.  Set and return
   :attr:`~Popen.returncode` attribute. Otherwise, returns ``None``.

.. method:: Popen.wait(timeout=None)

Wait for child process to terminate.  Set and return
   :attr:`~Popen.returncode` attribute.

If the process does not terminate after *timeout* seconds, raise a
   :exc:`TimeoutExpired` exception.  It is safe to catch this exception and
   retry the wait.

.. note::

This will deadlock when using ``stdout=PIPE`` or ``stderr=PIPE``
      and the child process generates enough output to a pipe such that
      it blocks waiting for the OS pipe buffer to accept more data.
      Use :meth:`Popen.communicate` when using pipes to avoid that.

.. note::

When ``timeout`` is not ``None`` and the platform supports it, an
      efficient event-driven mechanism is used to wait for process termination:

- Linux >= 5.3 uses :func:`os.pidfd_open` + :func:`select.poll`
      - macOS and other BSD variants use :func:`select.kqueue` +
        ``KQ_FILTER_PROC`` + ``KQ_NOTE_EXIT``
      - Windows uses ``WaitForSingleObject``

If none of these mechanisms are available, the function falls back to a
      busy loop (non-blocking call and short sleeps).

.. note::

Use the :mod:`asyncio` module for an asynchronous wait: see
      :class:`asyncio.create_subprocess_exec`.

.. versionchanged:: 3.3
      *timeout* was added.

.. versionchanged:: 3.15
      if *timeout* is not ``None``, use efficient event-driven implementation
      on Linux >= 5.3 and macOS / BSD.

.. method:: Popen.communicate(input=None, timeout=None)

Interact with process: Send data to stdin.  Read data from stdout and stderr,
   until end-of-file is reached.  Wait for process to terminate and set the
   :attr:`~Popen.returncode` attribute.  The optional *input* argument should be
   data to be sent to the child process, or ``None``, if no data should be sent
   to the child.  If streams were opened in text mode, *input* must be a string.
   Otherwise, it must be bytes.

:meth:`communicate` returns a tuple ``(stdout_data, stderr_data)``.
   The data will be strings if streams were opened in text mode; otherwise,
   bytes.

Note that if you want to send data to the process's stdin, you need to create
   the Popen object with ``stdin=PIPE``.  Similarly, to get anything other than
   ``None`` in the result tuple, you need to give ``stdout=PIPE`` and/or
   ``stderr=PIPE`` too.

If the process does not terminate after *timeout* seconds, a
   :exc:`TimeoutExpired` exception will be raised.  Catching this exception and
   retrying communication will not lose any output.  Supplying *input* to a
   subsequent post-timeout :meth:`communicate` call is in undefined behavior
   and may become an error in the future.

The child process is not killed if the timeout expires, so in order to
   cleanup properly a well-behaved application should kill the child process and
   finish communication::

proc = subprocess.Popen(...)
      try:
          outs, errs = proc.communicate(timeout=15)
      except TimeoutExpired:
          proc.kill()
          outs, errs = proc.communicate()

After a call to :meth:`~Popen.communicate` raises :exc:`TimeoutExpired`, do
   not call :meth:`~Popen.wait`. Use an additional :meth:`~Popen.communicate`
   call to finish handling pipes and populate the :attr:`~Popen.returncode`
   attribute.

.. note::

The data read is buffered in memory, so do not use this method if the data
      size is large or unlimited.

.. versionchanged:: 3.3
      *timeout* was added.

.. method:: Popen.send_signal(signal)

Sends the signal *signal* to the child.

Do nothing if the process completed.

.. note::

On Windows, SIGTERM is an alias for :meth:`terminate`. CTRL_C_EVENT and
      CTRL_BREAK_EVENT can be sent to processes started with a *creationflags*
      parameter which includes ``CREATE_NEW_PROCESS_GROUP``.

.. method:: Popen.terminate()

Stop the child. On POSIX OSs the method sends :py:const:`~signal.SIGTERM` to the
   child. On Windows the Win32 API function :c:func:`!TerminateProcess` is called
   to stop the child.

.. method:: Popen.kill()

Kills the child. On POSIX OSs the function sends SIGKILL to the child.
   On Windows :meth:`kill` is an alias for :meth:`terminate`.

The following attributes are also set by the class for you to access.
Reassigning them to new values is unsupported:

.. attribute:: Popen.args

The *args* argument as it was passed to :class:`Popen` -- a
   sequence of program arguments or else a single string.

.. versionadded:: 3.3

.. attribute:: Popen.stdin

If the *stdin* argument was :data:`PIPE`, this attribute is a writeable
   stream object as returned by :func:`open`. If the *encoding* or *errors*
   arguments were specified or the *text* or *universal_newlines* argument
   was ``True``, the stream is a text stream, otherwise it is a byte stream.
   If the *stdin* argument was not :data:`PIPE`, this attribute is ``None``.

.. attribute:: Popen.stdout

If the *stdout* argument was :data:`PIPE`, this attribute is a readable
   stream object as returned by :func:`open`. Reading from the stream provides
   output from the child process. If the *encoding* or *errors* arguments were
   specified or the *text* or *universal_newlines* argument was ``True``, the
   stream is a text stream, otherwise it is a byte stream. If the *stdout*
   argument was not :data:`PIPE`, this attribute is ``None``.

.. attribute:: Popen.stderr

If the *stderr* argument was :data:`PIPE`, this attribute is a readable
   stream object as returned by :func:`open`. Reading from the stream provides
   error output from the child process. If the *encoding* or *errors* arguments
   were specified or the *text* or *universal_newlines* argument was ``True``, the
   stream is a text stream, otherwise it is a byte stream. If the *stderr* argument
   was not :data:`PIPE`, this attribute is ``None``.

.. warning::

Use :meth:`~Popen.communicate` rather than :attr:`.stdin.write <Popen.stdin>`,
   :attr:`.stdout.read <Popen.stdout>` or :attr:`.stderr.read <Popen.stderr>` to avoid
   deadlocks due to any of the other OS pipe buffers filling up and blocking the
   child process.

.. attribute:: Popen.pid

The process ID of the child process.

Note that if you set the *shell* argument to ``True``, this is the process ID
   of the spawned shell.

.. attribute:: Popen.returncode

The child return code. Initially ``None``, :attr:`returncode` is set by
   a call to the :meth:`poll`, :meth:`wait`, or :meth:`communicate` methods
   if they detect that the process has terminated.

A ``None`` value indicates that the process hadn't yet terminated at the
   time of the last method call.

A negative value ``-N`` indicates that the child was terminated by signal
   ``N`` (POSIX only).

When ``shell=True``, the return code reflects the exit status of the shell
   itself (e.g. ``/bin/sh``), which may map signals to codes such as
   ``128+N``. See the documentation of the shell (for example, the Bash
   manual's Exit Status) for details.

Windows Popen Helpers
---------------------

The :class:`STARTUPINFO` class and following constants are only available
on Windows.

.. class:: STARTUPINFO(*, dwFlags=0, hStdInput=None, hStdOutput=None, \
                       hStdError=None, wShowWindow=0, lpAttributeList=None)

Partial support of the Windows
   `STARTUPINFO <https://msdn.microsoft.com/en-us/library/ms686331(v=vs.85).aspx>`__
   structure is used for :class:`Popen` creation.  The following attributes can
   be set by passing them as keyword-only arguments.

.. versionchanged:: 3.7
      Keyword-only argument support was added.

.. attribute:: dwFlags

A bit field that determines whether certain :class:`STARTUPINFO`
      attributes are used when the process creates a window. ::

si = subprocess.STARTUPINFO()
         si.dwFlags = subprocess.STARTF_USESTDHANDLES | subprocess.STARTF_USESHOWWINDOW

.. attribute:: hStdInput

If :attr:`dwFlags` specifies :data:`STARTF_USESTDHANDLES`, this attribute
      is the standard input handle for the process. If
      :data:`STARTF_USESTDHANDLES` is not specified, the default for standard
      input is the keyboard buffer.

.. attribute:: hStdOutput
