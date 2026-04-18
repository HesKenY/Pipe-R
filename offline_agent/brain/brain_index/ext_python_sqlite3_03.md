# Python sqlite3 (3/7)
source: https://github.com/python/cpython/blob/main/Doc/library/sqlite3.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
gate function.

:param str name:
          The name of the SQL aggregate function.

:param int n_arg:
          The number of arguments the SQL aggregate function can accept.
          If ``-1``, it may take any number of arguments.

:param aggregate_class:
          A class must implement the following methods:

* ``step()``: Add a row to the aggregate.
          * ``finalize()``: Return the final result of the aggregate as
            :ref:`a type natively supported by SQLite <sqlite3-types>`.

The number of arguments that the ``step()`` method must accept
          is controlled by *n_arg*.

Set to ``None`` to remove an existing SQL aggregate function.
      :type aggregate_class: :term:`class` | None

.. versionchanged:: 3.15
         All three parameters are now positional-only.

Example:

.. testcode::

class MySum:
             def __init__(self):
                 self.count = 0

def step(self, value):
                 self.count += value

def finalize(self):
                 return self.count

con = sqlite3.connect(":memory:")
         con.create_aggregate("mysum", 1, MySum)
         cur = con.execute("CREATE TABLE test(i)")
         cur.execute("INSERT INTO test(i) VALUES(1)")
         cur.execute("INSERT INTO test(i) VALUES(2)")
         cur.execute("SELECT mysum(i) FROM test")
         print(cur.fetchone()[0])

con.close()

.. testoutput::
         :hide:

3

.. method:: create_window_function(name, num_params, aggregate_class, /)

Create or remove a user-defined aggregate window function.

:param str name:
          The name of the SQL aggregate window function to create or remove.

:param int num_params:
          The number of arguments the SQL aggregate window function can accept.
          If ``-1``, it may take any number of arguments.

:param aggregate_class:
          A class that must implement the following methods:

* ``step()``: Add a row to the current window.
          * ``value()``: Return the current value of the aggregate.
          * ``inverse()``: Remove a row from the current window.
          * ``finalize()``: Return the final result of the aggregate as
            :ref:`a type natively supported by SQLite <sqlite3-types>`.

The number of arguments that the ``step()`` and ``value()`` methods
          must accept is controlled by *num_params*.

Set to ``None`` to remove an existing SQL aggregate window function.

:raises NotSupportedError:
          If used with a version of SQLite older than 3.25.0,
          which does not support aggregate window functions.

:type aggregate_class: :term:`class` | None

.. versionadded:: 3.11

Example:

.. testcode::

# Example taken from https://www.sqlite.org/windowfunctions.html#udfwinfunc
         class WindowSumInt:
             def __init__(self):
                 self.count = 0

def step(self, value):
                 """Add a row to the current window."""
                 self.count += value

def value(self):
                 """Return the current value of the aggregate."""
                 return self.count

def inverse(self, value):
                 """Remove a row from the current window."""
                 self.count -= value

def finalize(self):
                 """Return the final value of the aggregate.

Any clean-up actions should be placed here.
                 """
                 return self.count

con = sqlite3.connect(":memory:")
         cur = con.execute("CREATE TABLE test(x, y)")
         values = [
             ("a", 4),
             ("b", 5),
             ("c", 3),
             ("d", 8),
             ("e", 1),
         ]
         cur.executemany("INSERT INTO test VALUES(?, ?)", values)
         con.create_window_function("sumint", 1, WindowSumInt)
         cur.execute("""
             SELECT x, sumint(y) OVER (
                 ORDER BY x ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
             ) AS sum_y
             FROM test ORDER BY x
         """)
         print(cur.fetchall())
         con.close()

.. testoutput::
         :hide:

[('a', 9), ('b', 12), ('c', 16), ('d', 12), ('e', 9)]

.. method:: create_collation(name, callable, /)

Create a collation named *name* using the collating function *callable*.
      *callable* is passed two :class:`string <str>` arguments,
      and it should return an :class:`integer <int>`:

* ``1`` if the first is ordered higher than the second
      * ``-1`` if the first is ordered lower than the second
      * ``0`` if they are ordered equal

The following example shows a reverse sorting collation:

.. testcode::

def collate_reverse(string1, string2):
             if string1 == string2:
                 return 0
             elif string1 < string2:
                 return 1
             else:
                 return -1

con = sqlite3.connect(":memory:")
         con.create_collation("reverse", collate_reverse)

cur = con.execute("CREATE TABLE test(x)")
         cur.executemany("INSERT INTO test(x) VALUES(?)", [("a",), ("b",)])
         cur.execute("SELECT x FROM test ORDER BY x COLLATE reverse")
         for row in cur:
             print(row)
         con.close()

.. testoutput::
         :hide:

('b',)
         ('a',)

Remove a collation function by setting *callable* to ``None``.

.. versionchanged:: 3.11
         The collation name can contain any Unicode character.  Earlier, only
         ASCII characters were allowed.

.. method:: interrupt()

Call this method from a different thread to abort any queries that might
      be executing on the connection.
      Aborted queries will raise an :exc:`OperationalError`.

.. method:: set_authorizer(authorizer_callback, /)

Register :term:`callable` *authorizer_callback* to be invoked
      for each attempt to access a column of a table in the database.
      The callback should return one of :const:`SQLITE_OK`,
      :const:`SQLITE_DENY`, or :const:`SQLITE_IGNORE`
      to signal how access to the column should be handled
      by the underlying SQLite library.

The first argument to the callback signifies what kind of operation is to be
      authorized. The second and third argument will be arguments or ``None``
      depending on the first argument. The 4th argument is the name of the database
      ("main", "temp", etc.) if applicable. The 5th argument is the name of the
      inner-most trigger or view that is responsible for the access attempt or
      ``None`` if this access attempt is directly from input SQL code.

Please consult the SQLite documentation about the possible values for the first
      argument and the meaning of the second and third argument depending on the first
      one. All necessary constants are available in the :mod:`!sqlite3` module.

Passing ``None`` as *authorizer_callback* will disable the authorizer.

.. versionchanged:: 3.11
         Added support for disabling the authorizer using ``None``.

.. versionchanged:: 3.15
         The only parameter is now positional-only.

.. method:: set_progress_handler(progress_handler, /, n)

Register :term:`callable` *progress_handler* to be invoked for every *n*
      instructions of the SQLite virtual machine. This is useful if you want to
      get called from SQLite during long-running operations, for example to update
      a GUI.

If you want to clear any previously installed progress handler, call the
      method with ``None`` for *progress_handler*.

Returning a non-zero value from the handler function will terminate the
      currently executing query and cause it to raise a :exc:`DatabaseError`
      exception.

.. versionchanged:: 3.15
         The first parameter is now positional-only.

.. method:: set_trace_callback(trace_callback, /)

Register :term:`callable` *trace_callback* to be invoked
      for each SQL statement that is actually executed by the SQLite backend.

The only argument passed to the callback is the statement (as
      :class:`str`) that is being executed. The return value of the callback is
      ignored. Note that the backend does not only run statements passed to the
      :meth:`Cursor.execute` methods.  Other sources include the
      :ref:`transaction management <sqlite3-controlling-transactions>` of the
      :mod:`!sqlite3` module and the execution of triggers defined in the current
      database.

Passing ``None`` as *trace_callback* will disable the trace callback.

.. note::
         Exceptions raised in the trace callback are not propagated. As a
         development and debugging aid, use
         :meth:`~sqlite3.enable_callback_tracebacks` to enable printing
         tracebacks from exceptions raised in the trace callback.

.. versionadded:: 3.3

.. versionchanged:: 3.15
         The first parameter is now positional-only.

.. method:: enable_load_extension(enabled, /)

Enable the SQLite engine to load SQLite extensions from shared libraries
      if *enabled* is ``True``;
      else, disallow loading SQLite extensions.
      SQLite extensions can define new functions,
      aggregates or whole new virtual table implementations.  One well-known
      extension is the fulltext-search extension distributed with SQLite.

.. note::

The :mod:`!sqlite3` module is not built with loadable extension support by
         default, because some platforms (notably macOS) have SQLite
         libraries which are compiled without this feature.
         To get loadable extension support,
         you must pass the :option:`--enable-loadable-sqlite-extensions` option
         to :program:`configure`.

.. audit-event:: sqlite3.enable_load_extension connection,enabled sqlite3.Connection.enable_load_extension

.. versionadded:: 3.2

.. versionchanged:: 3.10
         Added the ``sqlite3.enable_load_extension`` auditing event.

.. We cannot doctest the load extension API, since there is no convenient
         way to skip it.

.. code-block::

con.enable_load_extension(True)

# Load the fulltext search extension
         con.execute("select load_extension('./fts3.so')")

# alternatively you can load the extension using an API call:
         # con.load_extension("./fts3.so")

# disable extension loading again
         con.enable_load_extension(False)

# example from SQLite wiki
         con.execute("CREATE VIRTUAL TABLE recipe USING fts3(name, ingredients)")
         con.executescript("""
             INSERT INTO recipe (name, ingredients) VALUES('broccoli stew', 'broccoli peppers cheese tomatoes');
             INSERT INTO recipe (name, ingredients) VALUES('pumpkin stew', 'pumpkin onions garlic celery');
             INSERT INTO recipe (name, ingredients) VALUES('broccoli pie', 'broccoli cheese onions flour');
             INSERT INTO recipe (name, ingredients) VALUES('pumpkin pie', 'pumpkin sugar flour butter');
             """)
         for row in con.execute("SELECT rowid, name, ingredients FROM recipe WHERE name MATCH 'pie'"):
             print(row)

.. method:: load_extension(path, /, *, entrypoint=None)

Load an SQLite extension from a shared library.
      Enable extension loading with :meth:`enable_load_extension` before
      calling this method.

:param str path:

The path to the SQLite extension.

:param entrypoint:

Entry point name.
         If ``None`` (the default),
         SQLite will come up with an entry point name of its own;
         see the SQLite docs `Loading an Extension`_ for details.

:type entrypoint: str | None

.. audit-event:: sqlite3.load_extension connection,path sqlite3.Connection.load_extension

.. versionadded:: 3.2

.. versionchanged:: 3.10
         Added the ``sqlite3.load_extension`` auditing event.

.. versionchanged:: 3.12
         Added the *entrypoint* parameter.

.. _Loading an Extension: https://www.sqlite.org/loadext.html#loading_an_extension

.. method:: iterdump(*, filter=None)

Return an :term:`iterator` to dump the database as SQL source code.
      Useful when saving an in-memory database for later restoration.
      Similar to the ``.dump`` command in the :program:`sqlite3` shell.

:param filter:

An optional ``LIKE`` pattern for database objects to dump, e.g. ``prefix_%``.
        If ``None`` (the default), all database objects will be included.

:type filter: str | None

Example:

.. testcode::

# Convert file example.db to SQL dump file dump.sql
         con = sqlite3.connect('example.db')
         with open('dump.sql', 'w') as f:
             for line in con.iterdump():
                 f.write('%s\n' % line)
         con.close()

.. seealso::

:ref:`sqlite3-howto-encoding`

.. versionchanged:: 3.13
         Added the *filter* parameter.

.. method:: backup(target, *, pages=-1, progress=None, name="main", sleep=0.250)

Create a backup of an SQLite database.

Works even if the database is being accessed by other clients
      or concurrently by the same connection.

:param ~sqlite3.Connection target:
          The database connection to save the backup to.

:param int pages:
          The number of pages to copy at a time.
          If equal to or less than ``0``,
          the entire database is copied in a single step.
          Defaults to ``-1``.

:param progress:
          If set to a :term:`callable`,
          it is invoked with three integer arguments for every backup iteration:
          the *status* of the last iteration,
          the *remaining* number of pages still to be copied,
          and the *total* number of pages.
          Defaults to ``None``.
      :type progress: :term:`callback` | None

:param str name:
          The name of the database to back up.
          Either ``"main"`` (the default) for the main database,
          ``"temp"`` for the temporary database,
          or the name of a custom database as attached using the
          ``ATTACH DATABASE`` SQL statement.

:param float sleep:
          The number of seconds to sleep between successive attempts
          to back up remaining pages.

Example 1, copy an existing database into another:

.. testcode::

def progress(status, remaining, total):
             print(f'Copied {total-remaining} of {total} pages...')
