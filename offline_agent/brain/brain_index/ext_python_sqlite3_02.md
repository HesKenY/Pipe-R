# Python sqlite3 (2/7)
source: https://github.com/python/cpython/blob/main/Doc/library/sqlite3.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
For example:

.. doctest::

>>> sqlite3.complete_statement("SELECT foo FROM bar;")
      True
      >>> sqlite3.complete_statement("SELECT foo")
      False

This function may be useful during command-line input
   to determine if the entered text seems to form a complete SQL statement,
   or if additional input is needed before calling :meth:`~Cursor.execute`.

See :func:`!runsource` in :source:`Lib/sqlite3/__main__.py`
   for real-world use.

.. function:: enable_callback_tracebacks(flag, /)

Enable or disable callback tracebacks.
   By default you will not get any tracebacks in user-defined functions,
   aggregates, converters, authorizer callbacks etc. If you want to debug them,
   you can call this function with *flag* set to ``True``. Afterwards, you
   will get tracebacks from callbacks on :data:`sys.stderr`. Use ``False``
   to disable the feature again.

.. note::

Errors in user-defined function callbacks are logged as unraisable exceptions.
      Use an :func:`unraisable hook handler <sys.unraisablehook>` for
      introspection of the failed callback.

.. function:: register_adapter(type, adapter, /)

Register an *adapter* :term:`callable` to adapt the Python type *type*
   into an SQLite type.
   The adapter is called with a Python object of type *type* as its sole
   argument, and must return a value of a
   :ref:`type that SQLite natively understands <sqlite3-types>`.

.. function:: register_converter(typename, converter, /)

Register the *converter* :term:`callable` to convert SQLite objects of type
   *typename* into a Python object of a specific type.
   The converter is invoked for all SQLite values of type *typename*;
   it is passed a :class:`bytes` object and should return an object of the
   desired Python type.
   Consult the parameter *detect_types* of
   :func:`connect` for information regarding how type detection works.

Note: *typename* and the name of the type in your query are matched
   case-insensitively.

.. _sqlite3-module-constants:

Module constants
^^^^^^^^^^^^^^^^

.. data:: LEGACY_TRANSACTION_CONTROL

Set :attr:`~Connection.autocommit` to this constant to select
   old style (pre-Python 3.12) transaction control behaviour.
   See :ref:`sqlite3-transaction-control-isolation-level` for more information.

.. data:: PARSE_DECLTYPES

Pass this flag value to the *detect_types* parameter of
   :func:`connect` to look up a converter function using
   the declared types for each column.
   The types are declared when the database table is created.
   :mod:`!sqlite3` will look up a converter function using the first word of the
   declared type as the converter dictionary key.
   For example:

.. code-block:: sql

CREATE TABLE test(
         i integer primary key,  ! will look up a converter named "integer"
         p point,                ! will look up a converter named "point"
         n number(10)            ! will look up a converter named "number"
       )

This flag may be combined with :const:`PARSE_COLNAMES` using the ``|``
   (bitwise or) operator.

.. note::

Generated fields (for example ``MAX(p)``) are returned as :class:`str`.
      Use :const:`!PARSE_COLNAMES` to enforce types for such queries.

.. data:: PARSE_COLNAMES

Pass this flag value to the *detect_types* parameter of
   :func:`connect` to look up a converter function by
   using the type name, parsed from the query column name,
   as the converter dictionary key.
   The query column name must be wrapped in double quotes (``"``)
   and the type name must be wrapped in square brackets (``[]``).

.. code-block:: sql

SELECT MAX(p) as "p [point]" FROM test;  ! will look up converter "point"

This flag may be combined with :const:`PARSE_DECLTYPES` using the ``|``
   (bitwise or) operator.

.. data:: SQLITE_OK
          SQLITE_DENY
          SQLITE_IGNORE

Flags that should be returned by the *authorizer_callback* :term:`callable`
   passed to :meth:`Connection.set_authorizer`, to indicate whether:

* Access is allowed (:const:`!SQLITE_OK`),
   * The SQL statement should be aborted with an error (:const:`!SQLITE_DENY`)
   * The column should be treated as a ``NULL`` value (:const:`!SQLITE_IGNORE`)

.. data:: apilevel

String constant stating the supported DB-API level. Required by the DB-API.
   Hard-coded to ``"2.0"``.

.. data:: paramstyle

String constant stating the type of parameter marker formatting expected by
   the :mod:`!sqlite3` module. Required by the DB-API. Hard-coded to
   ``"qmark"``.

.. note::

The ``named`` DB-API parameter style is also supported.

.. data:: sqlite_version

Version number of the runtime SQLite library as a :class:`string <str>`.

.. data:: sqlite_version_info

Version number of the runtime SQLite library as a :class:`tuple` of
   :class:`integers <int>`.

.. data:: SQLITE_KEYWORDS

A :class:`tuple` containing all SQLite keywords.

This constant is only available if Python was compiled with SQLite
   3.24.0 or greater.

.. versionadded:: 3.15

.. data:: threadsafety

Integer constant required by the DB-API 2.0, stating the level of thread
   safety the :mod:`!sqlite3` module supports. This attribute is set based on
   the default `threading mode <https://sqlite.org/threadsafe.html>`_ the
   underlying SQLite library is compiled with. The SQLite threading modes are:

1. **Single-thread**: In this mode, all mutexes are disabled and SQLite is
      unsafe to use in more than a single thread at once.
   2. **Multi-thread**: In this mode, SQLite can be safely used by multiple
      threads provided that no single database connection is used
      simultaneously in two or more threads.
   3. **Serialized**: In serialized mode, SQLite can be safely used by
      multiple threads with no restriction.

The mappings from SQLite threading modes to DB-API 2.0 threadsafety levels
   are as follows:

+------------------+----------------------+----------------------+-------------------------------+
   | SQLite threading | :pep:`threadsafety   | `SQLITE_THREADSAFE`_ | DB-API 2.0 meaning            |
   | mode             | <0249#threadsafety>` |                      |                               |
   +==================+======================+======================+===============================+
   | single-thread    | 0                    | 0                    | Threads may not share the     |
   |                  |                      |                      | module                        |
   +------------------+----------------------+----------------------+-------------------------------+
   | multi-thread     | 1                    | 2                    | Threads may share the module, |
   |                  |                      |                      | but not connections           |
   +------------------+----------------------+----------------------+-------------------------------+
   | serialized       | 3                    | 1                    | Threads may share the module, |
   |                  |                      |                      | connections and cursors       |
   +------------------+----------------------+----------------------+-------------------------------+

.. _SQLITE_THREADSAFE: https://sqlite.org/compile.html#threadsafe

.. versionchanged:: 3.11
      Set *threadsafety* dynamically instead of hard-coding it to ``1``.

.. _sqlite3-dbconfig-constants:

.. data:: SQLITE_DBCONFIG_DEFENSIVE
          SQLITE_DBCONFIG_DQS_DDL
          SQLITE_DBCONFIG_DQS_DML
          SQLITE_DBCONFIG_ENABLE_FKEY
          SQLITE_DBCONFIG_ENABLE_FTS3_TOKENIZER
          SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION
          SQLITE_DBCONFIG_ENABLE_QPSG
          SQLITE_DBCONFIG_ENABLE_TRIGGER
          SQLITE_DBCONFIG_ENABLE_VIEW
          SQLITE_DBCONFIG_LEGACY_ALTER_TABLE
          SQLITE_DBCONFIG_LEGACY_FILE_FORMAT
          SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE
          SQLITE_DBCONFIG_RESET_DATABASE
          SQLITE_DBCONFIG_TRIGGER_EQP
          SQLITE_DBCONFIG_TRUSTED_SCHEMA
          SQLITE_DBCONFIG_WRITABLE_SCHEMA

These constants are used for the :meth:`Connection.setconfig`
   and :meth:`~Connection.getconfig` methods.

The availability of these constants varies depending on the version of SQLite
   Python was compiled with.

.. versionadded:: 3.12

.. seealso::

https://www.sqlite.org/c3ref/c_dbconfig_defensive.html
        SQLite docs: Database Connection Configuration Options

.. deprecated-removed:: 3.12 3.14
   The :data:`!version` and :data:`!version_info` constants.

.. _sqlite3-connection-objects:

Connection objects
^^^^^^^^^^^^^^^^^^

.. class:: Connection

Each open SQLite database is represented by a ``Connection`` object,
   which is created using :func:`sqlite3.connect`.
   Their main purpose is creating :class:`Cursor` objects,
   and :ref:`sqlite3-controlling-transactions`.

.. seealso::

* :ref:`sqlite3-connection-shortcuts`
      * :ref:`sqlite3-connection-context-manager`

.. versionchanged:: 3.13

A :exc:`ResourceWarning` is emitted if :meth:`close` is not called before
      a :class:`!Connection` object is deleted.

An SQLite database connection has the following attributes and methods:

.. method:: cursor(factory=Cursor)

Create and return a :class:`Cursor` object.
      The cursor method accepts a single optional parameter *factory*. If
      supplied, this must be a :term:`callable` returning
      an instance of :class:`Cursor` or its subclasses.

.. method:: blobopen(table, column, rowid, /, *, readonly=False, name="main")

Open a :class:`Blob` handle to an existing
      :abbr:`BLOB (Binary Large OBject)`.

:param str table:
          The name of the table where the blob is located.

:param str column:
          The name of the column where the blob is located.

:param int rowid:
          The row id where the blob is located.

:param bool readonly:
          Set to ``True`` if the blob should be opened without write
          permissions.
          Defaults to ``False``.

:param str name:
          The name of the database where the blob is located.
          Defaults to ``"main"``.

:raises OperationalError:
          When trying to open a blob in a ``WITHOUT ROWID`` table.

:rtype: Blob

.. note::

The blob size cannot be changed using the :class:`Blob` class.
         Use the SQL function ``zeroblob`` to create a blob with a fixed size.

.. versionadded:: 3.11

.. method:: commit()

Commit any pending transaction to the database.
      If :attr:`autocommit` is ``True``, or there is no open transaction,
      this method does nothing.
      If :attr:`!autocommit` is ``False``, a new transaction is implicitly
      opened if a pending transaction was committed by this method.

.. method:: rollback()

Roll back to the start of any pending transaction.
      If :attr:`autocommit` is ``True``, or there is no open transaction,
      this method does nothing.
      If :attr:`!autocommit` is ``False``, a new transaction is implicitly
      opened if a pending transaction was rolled back by this method.

.. method:: close()

Close the database connection.
      If :attr:`autocommit` is ``False``,
      any pending transaction is implicitly rolled back.
      If :attr:`!autocommit` is ``True`` or :data:`LEGACY_TRANSACTION_CONTROL`,
      no implicit transaction control is executed.
      Make sure to :meth:`commit` before closing
      to avoid losing pending changes.

.. method:: execute(sql, parameters=(), /)

Create a new :class:`Cursor` object and call
      :meth:`~Cursor.execute` on it with the given *sql* and *parameters*.
      Return the new cursor object.

.. method:: executemany(sql, parameters, /)

Create a new :class:`Cursor` object and call
      :meth:`~Cursor.executemany` on it with the given *sql* and *parameters*.
      Return the new cursor object.

.. method:: executescript(sql_script, /)

Create a new :class:`Cursor` object and call
      :meth:`~Cursor.executescript` on it with the given *sql_script*.
      Return the new cursor object.

.. method:: create_function(name, narg, func, /, *, deterministic=False)

Create or remove a user-defined SQL function.

:param str name:
          The name of the SQL function.

:param int narg:
          The number of arguments the SQL function can accept.
          If ``-1``, it may take any number of arguments.

:param func:
          A :term:`callable` that is called when the SQL function is invoked.
          The callable must return :ref:`a type natively supported by SQLite
          <sqlite3-types>`.
          Set to ``None`` to remove an existing SQL function.
      :type func: :term:`callback` | None

:param bool deterministic:
          If ``True``, the created SQL function is marked as
          `deterministic <https://sqlite.org/deterministic.html>`_,
          which allows SQLite to perform additional optimizations.

.. versionchanged:: 3.8
         Added the *deterministic* parameter.

.. versionchanged:: 3.15
         The first three parameters are now positional-only.

Example:

.. doctest::

>>> import hashlib
         >>> def md5sum(t):
         ...     return hashlib.md5(t).hexdigest()
         >>> con = sqlite3.connect(":memory:")
         >>> con.create_function("md5", 1, md5sum)
         >>> for row in con.execute("SELECT md5(?)", (b"foo",)):
         ...     print(row)
         ('acbd18db4cc2f85cedef654fccc4a4d8',)
         >>> con.close()

.. method:: create_aggregate(name, n_arg, aggregate_class, /)

Create or remove a user-defined SQL aggregate function.

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
