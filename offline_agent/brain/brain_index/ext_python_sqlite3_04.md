# Python sqlite3 (4/7)
source: https://github.com/python/cpython/blob/main/Doc/library/sqlite3.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
(the default) for the main database,
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

src = sqlite3.connect('example.db')
         dst = sqlite3.connect('backup.db')
         with dst:
             src.backup(dst, pages=1, progress=progress)
         dst.close()
         src.close()

.. testoutput::
         :hide:

Copied 0 of 0 pages...

Example 2, copy an existing database into a transient copy:

.. testcode::

src = sqlite3.connect('example.db')
         dst = sqlite3.connect(':memory:')
         src.backup(dst)
         dst.close()
         src.close()

.. versionadded:: 3.7

.. seealso::

:ref:`sqlite3-howto-encoding`

.. method:: getlimit(category, /)

Get a connection runtime limit.

:param int category:
         The `SQLite limit category`_ to be queried.

:rtype: int

:raises ProgrammingError:
         If *category* is not recognised by the underlying SQLite library.

Example, query the maximum length of an SQL statement
      for :class:`Connection` ``con`` (the default is 1000000000):

.. testsetup:: sqlite3.limits

import sqlite3
         con = sqlite3.connect(":memory:")
         con.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 1_000_000_000)
         con.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 10)

.. doctest:: sqlite3.limits

>>> con.getlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH)
         1000000000

.. versionadded:: 3.11

.. method:: setlimit(category, limit, /)

Set a connection runtime limit.
      Attempts to increase a limit above its hard upper bound are silently
      truncated to the hard upper bound. Regardless of whether or not the limit
      was changed, the prior value of the limit is returned.

:param int category:
         The `SQLite limit category`_ to be set.

:param int limit:
         The value of the new limit.
         If negative, the current limit is unchanged.

:rtype: int

:raises ProgrammingError:
         If *category* is not recognised by the underlying SQLite library.

Example, limit the number of attached databases to 1
      for :class:`Connection` ``con`` (the default limit is 10):

.. doctest:: sqlite3.limits

>>> con.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 1)
         10
         >>> con.getlimit(sqlite3.SQLITE_LIMIT_ATTACHED)
         1

.. testcleanup:: sqlite3.limits

con.close()

.. versionadded:: 3.11

.. _SQLite limit category: https://www.sqlite.org/c3ref/c_limit_attached.html

.. method:: getconfig(op, /)

Query a boolean connection configuration option.

:param int op:
         A :ref:`SQLITE_DBCONFIG code <sqlite3-dbconfig-constants>`.

:rtype: bool

.. versionadded:: 3.12

.. method:: setconfig(op, enable=True, /)

Set a boolean connection configuration option.

:param int op:
         A :ref:`SQLITE_DBCONFIG code <sqlite3-dbconfig-constants>`.

:param bool enable:
         ``True`` if the configuration option should be enabled (default);
         ``False`` if it should be disabled.

.. versionadded:: 3.12

.. method:: serialize(*, name="main")

Serialize a database into a :class:`bytes` object.  For an
      ordinary on-disk database file, the serialization is just a copy of the
      disk file.  For an in-memory database or a "temp" database, the
      serialization is the same sequence of bytes which would be written to
      disk if that database were backed up to disk.

:param str name:
         The database name to be serialized.
         Defaults to ``"main"``.

:rtype: bytes

.. note::

This method is only available if the underlying SQLite library has the
         serialize API.

.. versionadded:: 3.11

.. method:: deserialize(data, /, *, name="main")

Deserialize a :meth:`serialized <serialize>` database into a
      :class:`Connection`.
      This method causes the database connection to disconnect from database
      *name*, and reopen *name* as an in-memory database based on the
      serialization contained in *data*.

:param bytes data:
         A serialized database.

:param str name:
         The database name to deserialize into.
         Defaults to ``"main"``.

:raises OperationalError:
         If the database connection is currently involved in a read
         transaction or a backup operation.

:raises DatabaseError:
         If *data* does not contain a valid SQLite database.

:raises OverflowError:
         If :func:`len(data) <len>` is larger than ``2**63 - 1``.

.. note::

This method is only available if the underlying SQLite library has the
         deserialize API.

.. versionadded:: 3.11

.. attribute:: autocommit

This attribute controls :pep:`249`-compliant transaction behaviour.
      :attr:`!autocommit` has three allowed values:

* ``False``: Select :pep:`249`-compliant transaction behaviour,
        implying that :mod:`!sqlite3` ensures a transaction is always open.
        Use :meth:`commit` and :meth:`rollback` to close transactions.

This is the recommended value of :attr:`!autocommit`.

* ``True``: Use SQLite's `autocommit mode`_.
        :meth:`commit` and :meth:`rollback` have no effect in this mode.

* :data:`LEGACY_TRANSACTION_CONTROL`:
        Pre-Python 3.12 (non-:pep:`249`-compliant) transaction control.
        See :attr:`isolation_level` for more details.

This is currently the default value of :attr:`!autocommit`.

Changing :attr:`!autocommit` to ``False`` will open a new transaction,
      and changing it to ``True`` will commit any pending transaction.

See :ref:`sqlite3-transaction-control-autocommit` for more details.

.. note::

The :attr:`isolation_level` attribute has no effect unless
         :attr:`autocommit` is :data:`LEGACY_TRANSACTION_CONTROL`.

.. versionadded:: 3.12

.. attribute:: in_transaction

This read-only attribute corresponds to the low-level SQLite
      `autocommit mode`_.

``True`` if a transaction is active (there are uncommitted changes),
      ``False`` otherwise.

.. versionadded:: 3.2

.. attribute:: isolation_level

Controls the :ref:`legacy transaction handling mode
      <sqlite3-transaction-control-isolation-level>` of :mod:`!sqlite3`.
      If set to ``None``, transactions are never implicitly opened.
      If set to one of ``"DEFERRED"``, ``"IMMEDIATE"``, or ``"EXCLUSIVE"``,
      corresponding to the underlying `SQLite transaction behaviour`_,
      :ref:`implicit transaction management
      <sqlite3-transaction-control-isolation-level>` is performed.

If not overridden by the *isolation_level* parameter of :func:`connect`,
      the default is ``""``, which is an alias for ``"DEFERRED"``.

.. note::

Using :attr:`autocommit` to control transaction handling is
         recommended over using :attr:`!isolation_level`.
         :attr:`!isolation_level` has no effect unless :attr:`autocommit` is
         set to :data:`LEGACY_TRANSACTION_CONTROL` (the default).

.. attribute:: row_factory

The initial :attr:`~Cursor.row_factory`
      for :class:`Cursor` objects created from this connection.
      Assigning to this attribute does not affect the :attr:`!row_factory`
      of existing cursors belonging to this connection, only new ones.
      Is ``None`` by default,
      meaning each row is returned as a :class:`tuple`.

See :ref:`sqlite3-howto-row-factory` for more details.

.. attribute:: text_factory

A :term:`callable` that accepts a :class:`bytes` parameter
      and returns a text representation of it.
      The callable is invoked for SQLite values with the ``TEXT`` data type.
      By default, this attribute is set to :class:`str`.

See :ref:`sqlite3-howto-encoding` for more details.

.. attribute:: total_changes

Return the total number of database rows that have been modified, inserted, or
      deleted since the database connection was opened.

.. _sqlite3-cursor-objects:

Cursor objects
^^^^^^^^^^^^^^

A ``Cursor`` object represents a `database cursor`_
   which is used to execute SQL statements,
   and manage the context of a fetch operation.
   Cursors are created using :meth:`Connection.cursor`,
   or by using any of the :ref:`connection shortcut methods
   <sqlite3-connection-shortcuts>`.

Cursor objects are :term:`iterators <iterator>`,
   meaning that if you :meth:`~Cursor.execute` a ``SELECT`` query,
   you can simply iterate over the cursor to fetch the resulting rows:

.. testsetup:: sqlite3.cursor

import sqlite3
      con = sqlite3.connect(":memory:", isolation_level=None)
      cur = con.execute("CREATE TABLE data(t)")
      cur.execute("INSERT INTO data VALUES(1)")

.. testcode:: sqlite3.cursor

for row in cur.execute("SELECT t FROM data"):
          print(row)

.. testoutput:: sqlite3.cursor
      :hide:

(1,)

.. _database cursor: https://en.wikipedia.org/wiki/Cursor_(databases)

.. class:: Cursor

A :class:`Cursor` instance has the following attributes and methods.

.. index:: single: ? (question mark); in SQL statements
   .. index:: single: : (colon); in SQL statements

.. method:: execute(sql, parameters=(), /)

Execute a single SQL statement,
      optionally binding Python values using
      :ref:`placeholders <sqlite3-placeholders>`.

:param str sql:
         A single SQL statement.

:param parameters:
         Python values to bind to placeholders in *sql*.
         A :class:`!dict` if named placeholders are used.
         A :term:`!sequence` if unnamed placeholders are used.
         See :ref:`sqlite3-placeholders`.
      :type parameters: :class:`dict` | :term:`sequence`

:raises ProgrammingError:
         When *sql* contains more than one SQL statement.
         When :ref:`named placeholders <sqlite3-placeholders>` are used
         and *parameters* is a sequence instead of a :class:`dict`.

If :attr:`~Connection.autocommit` is
      :data:`LEGACY_TRANSACTION_CONTROL`,
      :attr:`~Connection.isolation_level` is not ``None``,
      *sql* is an ``INSERT``, ``UPDATE``, ``DELETE``, or ``REPLACE`` statement,
      and there is no open transaction,
      a transaction is implicitly opened before executing *sql*.

.. versionchanged:: 3.14

:exc:`ProgrammingError` is emitted if
         :ref:`named placeholders <sqlite3-placeholders>` are used
         and *parameters* is a sequence instead of a :class:`dict`.

Use :meth:`executescript` to execute multiple SQL statements.

.. method:: executemany(sql, parameters, /)

For every item in *parameters*,
      repeatedly execute the :ref:`parameterized <sqlite3-placeholders>`
      :abbr:`DML (Data Manipulation Language)` SQL statement *sql*.

Uses the same implicit transaction handling as :meth:`~Cursor.execute`.

:param str sql:
         A single SQL DML statement.

:param parameters:
         An :term:`!iterable` of parameters to bind with
         the placeholders in *sql*.
         See :ref:`sqlite3-placeholders`.
      :type parameters: :term:`iterable`

:raises ProgrammingError:
         When *sql* contains more than one SQL statement
         or is not a DML statement,
         When :ref:`named placeholders <sqlite3-placeholders>` are used
         and the items in *parameters* are sequences instead of :class:`dict`\s.

Example:

.. testcode:: sqlite3.cursor

rows = [
             ("row1",),
             ("row2",),
         ]
         # cur is an sqlite3.Cursor object
         cur.executemany("INSERT INTO data VALUES(?)", rows)

.. testcleanup:: sqlite3.cursor

con.close()

.. note::

Any resulting rows are discarded,
         including DML statements with `RETURNING clauses`_.

.. _RETURNING clauses: https://www.sqlite.org/lang_returning.html

.. versionchanged:: 3.14

:exc:`ProgrammingError` is emitted if
         :ref:`named placeholders <sqlite3-placeholders>` are used
         and the items in *parameters* are sequences
         instead of :class:`dict`\s.

.. method:: executescript(sql_script, /)

Execute the SQL statements in *sql_script*.
      If the :attr:`~Connection.autocommit` is
      :data:`LEGACY_TRANSACTION_CONTROL`
      and there is a pending transaction,
      an implicit ``COMMIT`` statement is executed first.
      No other implicit transaction control is performed;
      any transaction control must be added to *sql_script*.

*sql_script* must be a :class:`string <str>`.

Example:

.. testcode:: sqlite3.cursor

# cur is an sqlite3.Cursor object
         cur.executescript("""
             BEGIN;
             CREATE TABLE person(firstname, lastname, age);
             CREATE TABLE book(title, author, published);
             CREATE TABLE publisher(name, address);
             COMMIT;
         """)

.. method:: fetchone()

If :attr:`~Cursor.row_factory` is ``None``,
      return the next row query result set as a :class:`tuple`.
      Else, pass it to the row factory and return its result.
      Return ``None`` if no more data is available.

.. method:: fetchmany(size=cursor.arraysize)

Return the next set of rows of a query result as a :class:`list`.
      Return an empty list if no more rows are available.

The number of rows to fetch per call is specified by the *size* parameter.
      If *size* is not given, :attr:`arraysize` determines the number of rows
      to be fetched.
      If fewer than *size* rows are available,
      as many rows as are available are returned.

Note there are performance considerations involved with the *size* parameter.
      For optimal performance, it is usually best to use the arraysize attribute.
      If the *size* parameter is used, then it is best for it to retain the same
      value from one :meth:`fetchmany` call to the next.

.. versionchanged:: 3.15
         Negative *size* values are rejected by raising :exc:`ValueError`.

.. method:: fetchall()
