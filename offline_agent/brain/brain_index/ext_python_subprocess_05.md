# Python subprocess (5/5)
source: https://github.com/python/cpython/blob/main/Doc/library/subprocess.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
p1.stdout.close()`` call after starting the p2 is important in order for
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

* Calling the program through the shell is usually not required.
* The :func:`call` return value is encoded differently to that of
  :func:`os.system`.

* The :func:`os.system` function ignores SIGINT and SIGQUIT signals while
  the command is running, but the caller must do this separately when
  using the :mod:`!subprocess` module.

A more realistic example would look like this::

try:
       retcode = call("mycmd" + " myarg", shell=True)
       if retcode < 0:
           print("Child was terminated by signal", -retcode, file=sys.stderr)
       else:
           print("Child returned", retcode, file=sys.stderr)
   except OSError as e:
       print("Execution failed:", e, file=sys.stderr)

Replacing the :func:`os.spawn <os.spawnl>` family
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

P_NOWAIT example::

pid = os.spawnlp(os.P_NOWAIT, "/bin/mycmd", "mycmd", "myarg")
   ==>
   pid = Popen(["/bin/mycmd", "myarg"]).pid

P_WAIT example::

retcode = os.spawnlp(os.P_WAIT, "/bin/mycmd", "mycmd", "myarg")
   ==>
   retcode = call(["/bin/mycmd", "myarg"])

Vector example::

os.spawnvp(os.P_NOWAIT, path, args)
   ==>
   Popen([path] + args[1:])

Environment example::

os.spawnlpe(os.P_NOWAIT, "/bin/mycmd", "mycmd", "myarg", env)
   ==>
   Popen(["/bin/mycmd", "myarg"], env={"PATH": "/usr/bin"})

Replacing :func:`os.popen`
^^^^^^^^^^^^^^^^^^^^^^^^^^

Return code handling translates as follows::

pipe = os.popen(cmd, 'w')
   ...
   rc = pipe.close()
   if rc is not None and rc >> 8:
       print("There were some errors")
   ==>
   process = Popen(cmd, stdin=PIPE)
   ...
   process.stdin.close()
   if process.wait() != 0:
       print("There were some errors")

Legacy Shell Invocation Functions
---------------------------------

This module also provides the following legacy functions from the 2.x
``commands`` module. These operations implicitly invoke the system shell and
none of the guarantees described above regarding security and exception
handling consistency are valid for these functions.

.. function:: getstatusoutput(cmd, *, encoding=None, errors=None)

Return ``(exitcode, output)`` of executing *cmd* in a shell.

Execute the string *cmd* in a shell with :func:`check_output` and
   return a 2-tuple ``(exitcode, output)``.
   *encoding* and *errors* are used to decode output;
   see the notes on :ref:`frequently-used-arguments` for more details.

A trailing newline is stripped from the output.
   The exit code for the command can be interpreted as the return code
   of subprocess.  Example::

>>> subprocess.getstatusoutput('ls /bin/ls')
      (0, '/bin/ls')
      >>> subprocess.getstatusoutput('cat /bin/junk')
      (1, 'cat: /bin/junk: No such file or directory')
      >>> subprocess.getstatusoutput('/bin/junk')
      (127, 'sh: /bin/junk: not found')
      >>> subprocess.getstatusoutput('/bin/kill $$')
      (-15, '')

.. availability:: Unix, Windows.

.. versionchanged:: 3.3.4
      Windows support was added.

The function now returns (exitcode, output) instead of (status, output)
      as it did in Python 3.3.3 and earlier.  exitcode has the same value as
      :attr:`~Popen.returncode`.

.. versionchanged:: 3.11
      Added the *encoding* and *errors* parameters.

.. function:: getoutput(cmd, *, encoding=None, errors=None)

Return output (stdout and stderr) of executing *cmd* in a shell.

Like :func:`getstatusoutput`, except the exit code is ignored and the return
   value is a string containing the command's output.  Example::

>>> subprocess.getoutput('ls /bin/ls')
      '/bin/ls'

.. availability:: Unix, Windows.

.. versionchanged:: 3.3.4
      Windows support added

.. versionchanged:: 3.11
      Added the *encoding* and *errors* parameters.

Notes
-----

.. _subprocess-timeout-behavior:

Timeout Behavior
^^^^^^^^^^^^^^^^

When using the ``timeout`` parameter in functions like :func:`run`,
:meth:`Popen.wait`, or :meth:`Popen.communicate`,
users should be aware of the following behaviors:

1. **Process Creation Delay**: The initial process creation itself cannot be interrupted
   on many platform APIs. This means that even when specifying a timeout, you are not
   guaranteed to see a timeout exception until at least after however long process
   creation takes.

2. **Extremely Small Timeout Values**: Setting very small timeout values (such as a few
   milliseconds) may result in almost immediate :exc:`TimeoutExpired` exceptions because
   process creation and system scheduling inherently require time.

.. _converting-argument-sequence:

Converting an argument sequence to a string on Windows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On Windows, an *args* sequence is converted to a string that can be parsed
using the following rules (which correspond to the rules used by the MS C
runtime):

1. Arguments are delimited by white space, which is either a
   space or a tab.

2. A string surrounded by double quotation marks is
   interpreted as a single argument, regardless of white space
   contained within.  A quoted string can be embedded in an
   argument.

3. A double quotation mark preceded by a backslash is
   interpreted as a literal double quotation mark.

4. Backslashes are interpreted literally, unless they
   immediately precede a double quotation mark.

5. If backslashes immediately precede a double quotation mark,
   every pair of backslashes is interpreted as a literal
   backslash.  If the number of backslashes is odd, the last
   backslash escapes the next double quotation mark as
   described in rule 3.

.. seealso::

:mod:`shlex`
      Module which provides function to parse and escape command lines.

.. _disable_posix_spawn:

Disable use of ``posix_spawn()``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On Linux, :mod:`!subprocess` defaults to using the ``vfork()`` system call
internally when it is safe to do so rather than ``fork()``. This greatly
improves performance.

::

subprocess._USE_POSIX_SPAWN = False  # See CPython issue gh-NNNNNN.

It is safe to set this to false on any Python version. It will have no
effect on older or newer versions where unsupported. Do not assume the attribute
is available to read. Despite the name, a true value does not indicate the
corresponding function will be used, only that it may be.

Please file issues any time you have to use these private knobs with a way to
reproduce the issue you were seeing. Link to that issue from a comment in your
code.

.. versionadded:: 3.8 ``_USE_POSIX_SPAWN``
