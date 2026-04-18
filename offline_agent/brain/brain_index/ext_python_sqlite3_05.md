# Python sqlite3 (5/7)
source: https://github.com/python/cpython/blob/main/Doc/library/sqlite3.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
*size* rows are available,
      as many rows as are available are returned.

Note there are performance considerations involved with the *size* parameter.
      For optimal performance, it is usually best to use the arraysize attribute.
      If the *size* parameter is used, then it is best for it to retain the same
      value from one :meth:`fetchmany` call to the next.

.. versionchanged:: 3.15
         Negative *size* values are rejected by raising :exc:`ValueError`.

.. method:: fetchall()

Return all (remaining) rows of a query result as a :class:`list`.
      Return an empty list if no rows are available.
      Note that the :attr:`arraysize` attribute can affect the performance of
      this operation.

.. method:: close()

Close the cursor now (rather than whenever ``__del__`` is called).

The cursor will be unusable from this point forward; a :exc:`ProgrammingError`
      exception will be raised if any operation is attempted with the cursor.

.. method:: setinputsizes(sizes, /)

Required by the DB-API. Does nothing in :mod:`!sqlite3`.

.. method:: setoutputsize(size, column=None, /)

Required by the DB-API. Does nothing in :mod:`!sqlite3`.

.. attribute:: arraysize

Read/write attribute that controls the number of rows returned by :meth:`fetchmany`.
      The default value is 1 which means a single row would be fetched per call.

.. versionchanged:: 3.15
         Negative values are rejected by raising :exc:`ValueError`.

.. attribute:: connection

Read-only attribute that provides the SQLite database :class:`Connection`
      belonging to the cursor.  A :class:`Cursor` object created by
      calling :meth:`con.cursor() <Connection.cursor>` will have a
      :attr:`connection` attribute that refers to *con*:

.. doctest::

>>> con = sqlite3.connect(":memory:")
         >>> cur = con.cursor()
         >>> cur.connection == con
         True
         >>> con.close()

.. attribute:: description

Read-only attribute that provides the column names of the last query. To
      remain compatible with the Python DB API, it returns a 7-tuple for each
      column where the last six items of each tuple are ``None``.

It is set for ``SELECT`` statements without any matching rows as well.

.. attribute:: lastrowid

Read-only attribute that provides the row id of the last inserted row. It
      is only updated after successful ``INSERT`` or ``REPLACE`` statements
      using the :meth:`execute` method.  For other statements, after
      :meth:`executemany` or :meth:`executescript`, or if the insertion failed,
      the value of ``lastrowid`` is left unchanged.  The initial value of
      ``lastrowid`` is ``None``.

.. note::
         Inserts into ``WITHOUT ROWID`` tables are not recorded.

.. versionchanged:: 3.6
         Added support for the ``REPLACE`` statement.

.. attribute:: rowcount

Read-only attribute that provides the number of modified rows for
      ``INSERT``, ``UPDATE``, ``DELETE``, and ``REPLACE`` statements;
      is ``-1`` for other statements,
      including :abbr:`CTE (Common Table Expression)` queries.
      It is only updated by the :meth:`execute` and :meth:`executemany` methods,
      after the statement has run to completion.
      This means that any resulting rows must be fetched in order for
      :attr:`!rowcount` to be updated.

.. attribute:: row_factory

Control how a row fetched from this :class:`!Cursor` is represented.
      If ``None``, a row is represented as a :class:`tuple`.
      Can be set to the included :class:`sqlite3.Row`;
      or a :term:`callable` that accepts two arguments,
      a :class:`Cursor` object and the :class:`!tuple` of row values,
      and returns a custom object representing an SQLite row.

Defaults to what :attr:`Connection.row_factory` was set to
      when the :class:`!Cursor` was created.
      Assigning to this attribute does not affect
      :attr:`Connection.row_factory` of the parent connection.

See :ref:`sqlite3-howto-row-factory` for more details.

.. The sqlite3.Row example used to be a how-to. It has now been incorporated
   into the Row reference. We keep the anchor here in order not to break
   existing links.

.. _sqlite3-columns-by-name:
.. _sqlite3-row-objects:

Row objects
^^^^^^^^^^^

.. class:: Row

A :class:`!Row` instance serves as a highly optimized
   :attr:`~Connection.row_factory` for :class:`Connection` objects.
   It supports iteration, equality testing, :func:`len`,
   and :term:`mapping` access by column name and index.

Two :class:`!Row` objects compare equal
   if they have identical column names and values.

See :ref:`sqlite3-howto-row-factory` for more details.

.. method:: keys

Return a :class:`list` of column names as :class:`strings <str>`.
      Immediately after a query,
      it is the first member of each tuple in :attr:`Cursor.description`.

.. versionchanged:: 3.5
      Added support of slicing.

.. _sqlite3-blob-objects:

Blob objects
^^^^^^^^^^^^

.. class:: Blob

.. versionadded:: 3.11

A :class:`Blob` instance is a :term:`file-like object`
   that can read and write data in an SQLite :abbr:`BLOB (Binary Large OBject)`.
   Call :func:`len(blob) <len>` to get the size (number of bytes) of the blob.
   Use indices and :term:`slices <slice>` for direct access to the blob data.

Use the :class:`Blob` as a :term:`context manager` to ensure that the blob
   handle is closed after use.

.. testcode::

con = sqlite3.connect(":memory:")
      con.execute("CREATE TABLE test(blob_col blob)")
      con.execute("INSERT INTO test(blob_col) VALUES(zeroblob(13))")

# Write to our blob, using two write operations:
      with con.blobopen("test", "blob_col", 1) as blob:
          blob.write(b"hello, ")
          blob.write(b"world.")
          # Modify the first and last bytes of our blob
          blob[0] = ord("H")
          blob[-1] = ord("!")

# Read the contents of our blob
      with con.blobopen("test", "blob_col", 1) as blob:
          greeting = blob.read()

print(greeting)  # outputs "b'Hello, world!'"
      con.close()

.. testoutput::
      :hide:

b'Hello, world!'

.. method:: close()

Close the blob.

The blob will be unusable from this point onward.  An
      :class:`~sqlite3.Error` (or subclass) exception will be raised if any
      further operation is attempted with the blob.

.. method:: read(length=-1, /)

Read *length* bytes of data from the blob at the current offset position.
      If the end of the blob is reached, the data up to
      :abbr:`EOF (End of File)` will be returned.  When *length* is not
      specified, or is negative, :meth:`~Blob.read` will read until the end of
      the blob.

.. method:: write(data, /)

Write *data* to the blob at the current offset.  This function cannot
      change the blob length.  Writing beyond the end of the blob will raise
      :exc:`ValueError`.

.. method:: tell()

Return the current access position of the blob.

.. method:: seek(offset, origin=os.SEEK_SET, /)

Set the current access position of the blob to *offset*.  The *origin*
      argument defaults to :const:`os.SEEK_SET` (absolute blob positioning).
      Other values for *origin* are :const:`os.SEEK_CUR` (seek relative to the
      current position) and :const:`os.SEEK_END` (seek relative to the blob’s
      end).

PrepareProtocol objects
^^^^^^^^^^^^^^^^^^^^^^^

.. class:: PrepareProtocol

The PrepareProtocol type's single purpose is to act as a :pep:`246` style
   adaption protocol for objects that can :ref:`adapt themselves
   <sqlite3-conform>` to :ref:`native SQLite types <sqlite3-types>`.

.. _sqlite3-exceptions:

Exceptions
^^^^^^^^^^

The exception hierarchy is defined by the DB-API 2.0 (:pep:`249`).

.. exception:: Warning

This exception is not currently raised by the :mod:`!sqlite3` module,
   but may be raised by applications using :mod:`!sqlite3`,
   for example if a user-defined function truncates data while inserting.
   ``Warning`` is a subclass of :exc:`Exception`.

.. exception:: Error

The base class of the other exceptions in this module.
   Use this to catch all errors with one single :keyword:`except` statement.
   ``Error`` is a subclass of :exc:`Exception`.

If the exception originated from within the SQLite library,
   the following two attributes are added to the exception:

.. attribute:: sqlite_errorcode

The numeric error code from the
      `SQLite API <https://sqlite.org/rescode.html>`_

.. versionadded:: 3.11

.. attribute:: sqlite_errorname

The symbolic name of the numeric error code
      from the `SQLite API <https://sqlite.org/rescode.html>`_

.. versionadded:: 3.11

.. exception:: InterfaceError

Exception raised for misuse of the low-level SQLite C API.
   In other words, if this exception is raised, it probably indicates a bug in the
   :mod:`!sqlite3` module.
   ``InterfaceError`` is a subclass of :exc:`Error`.

.. exception:: DatabaseError

Exception raised for errors that are related to the database.
   This serves as the base exception for several types of database errors.
   It is only raised implicitly through the specialised subclasses.
   ``DatabaseError`` is a subclass of :exc:`Error`.

.. exception:: DataError

Exception raised for errors caused by problems with the processed data,
   like numeric values out of range, and strings which are too long.
   ``DataError`` is a subclass of :exc:`DatabaseError`.

.. exception:: OperationalError

Exception raised for errors that are related to the database's operation,
   and not necessarily under the control of the programmer.
   For example, the database path is not found,
   or a transaction could not be processed.
   ``OperationalError`` is a subclass of :exc:`DatabaseError`.

.. exception:: IntegrityError

Exception raised when the relational integrity of the database is affected,
   e.g. a foreign key check fails.  It is a subclass of :exc:`DatabaseError`.

.. exception:: InternalError

Exception raised when SQLite encounters an internal error.
   If this is raised, it may indicate that there is a problem with the runtime
   SQLite library.
   ``InternalError`` is a subclass of :exc:`DatabaseError`.

.. exception:: ProgrammingError

Exception raised for :mod:`!sqlite3` API programming errors,
   for example supplying the wrong number of bindings to a query,
   or trying to operate on a closed :class:`Connection`.
   ``ProgrammingError`` is a subclass of :exc:`DatabaseError`.

.. exception:: NotSupportedError

Exception raised in case a method or database API is not supported by the
   underlying SQLite library. For example, setting *deterministic* to
   ``True`` in :meth:`~Connection.create_function`, if the underlying SQLite library
   does not support deterministic functions.
   ``NotSupportedError`` is a subclass of :exc:`DatabaseError`.

.. _sqlite3-types:

SQLite and Python types
^^^^^^^^^^^^^^^^^^^^^^^

SQLite natively supports the following types: ``NULL``, ``INTEGER``,
``REAL``, ``TEXT``, ``BLOB``.

The following Python types can thus be sent to SQLite without any problem:

+-------------------------------+-------------+
| Python type                   | SQLite type |
+===============================+=============+
| ``None``                      | ``NULL``    |
+-------------------------------+-------------+
| :class:`int`                  | ``INTEGER`` |
+-------------------------------+-------------+
| :class:`float`                | ``REAL``    |
+-------------------------------+-------------+
| :class:`str`                  | ``TEXT``    |
+-------------------------------+-------------+
| :class:`bytes`                | ``BLOB``    |
+-------------------------------+-------------+

This is how SQLite types are converted to Python types by default:

+-------------+----------------------------------------------+
| SQLite type | Python type                                  |
+=============+==============================================+
| ``NULL``    | ``None``                                     |
+-------------+----------------------------------------------+
| ``INTEGER`` | :class:`int`                                 |
+-------------+----------------------------------------------+
| ``REAL``    | :class:`float`                               |
+-------------+----------------------------------------------+
| ``TEXT``    | depends on :attr:`~Connection.text_factory`, |
|             | :class:`str` by default                      |
+-------------+----------------------------------------------+
| ``BLOB``    | :class:`bytes`                               |
+-------------+----------------------------------------------+

The type system of the :mod:`!sqlite3` module is extensible in two ways: you can
store additional Python types in an SQLite database via
:ref:`object adapters <sqlite3-adapters>`,
and you can let the :mod:`!sqlite3` module convert SQLite types to
Python types via :ref:`converters <sqlite3-converters>`.

.. _sqlite3-default-converters:

Default adapters and converters (deprecated)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

The default adapters and converters are deprecated as of Python 3.12.
   Instead, use the :ref:`sqlite3-adapter-converter-recipes`
   and tailor them to your needs.

The deprecated default adapters and converters consist of:

* An adapter for :class:`datetime.date` objects to :class:`strings <str>` in
  `ISO 8601`_ format.
* An adapter for :class:`datetime.datetime` objects to strings in
  ISO 8601 format.
* A converter for :ref:`declared <sqlite3-converters>` "date" types to
  :class:`datetime.date` objects.
* A converter for declared "timestamp" types to
  :class:`datetime.datetime` objects.
  Fractional parts will be truncated to 6 digits (microsecond precision).

.. note::

The default "timestamp" converter ignores UTC offsets in the database and
   always returns a naive :class:`datetime.datetime` object. To preserve UTC
   offsets in timestamps, either leave converters disabled, or register an
   offset-aware converter with :func:`register_converter`.
