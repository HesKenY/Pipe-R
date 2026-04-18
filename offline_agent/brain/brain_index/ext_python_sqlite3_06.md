# Python sqlite3 (6/7)
source: https://github.com/python/cpython/blob/main/Doc/library/sqlite3.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
types to
  :class:`datetime.date` objects.
* A converter for declared "timestamp" types to
  :class:`datetime.datetime` objects.
  Fractional parts will be truncated to 6 digits (microsecond precision).

.. note::

The default "timestamp" converter ignores UTC offsets in the database and
   always returns a naive :class:`datetime.datetime` object. To preserve UTC
   offsets in timestamps, either leave converters disabled, or register an
   offset-aware converter with :func:`register_converter`.

.. deprecated:: 3.12

.. _ISO 8601: https://en.wikipedia.org/wiki/ISO_8601

.. _sqlite3-cli:

Command-line interface
^^^^^^^^^^^^^^^^^^^^^^

The :mod:`!sqlite3` module can be invoked as a script,
using the interpreter's :option:`-m` switch,
in order to provide a simple SQLite shell.
The argument signature is as follows::

python -m sqlite3 [-h] [-v] [filename] [sql]

Type ``.quit`` or CTRL-D to exit the shell.

.. program:: python -m sqlite3 [-h] [-v] [filename] [sql]

.. option:: -h, --help

Print CLI help.

.. option:: -v, --version

Print underlying SQLite library version.

.. versionadded:: 3.12

.. _sqlite3-howtos:

How-to guides
-------------

.. _sqlite3-placeholders:

How to use placeholders to bind values in SQL queries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SQL operations usually need to use values from Python variables. However,
beware of using Python's string operations to assemble queries, as they
are vulnerable to `SQL injection attacks`_. For example, an attacker can simply
close the single quote and inject ``OR TRUE`` to select all rows::

>>> # Never do this -- insecure!
   >>> symbol = input()
   ' OR TRUE; --
   >>> sql = "SELECT * FROM stocks WHERE symbol = '%s'" % symbol
   >>> print(sql)
   SELECT * FROM stocks WHERE symbol = '' OR TRUE; --'
   >>> cur.execute(sql)

Instead, use the DB-API's parameter substitution. To insert a variable into a
query string, use a placeholder in the string, and substitute the actual values
into the query by providing them as a :class:`tuple` of values to the second
argument of the cursor's :meth:`~Cursor.execute` method.

An SQL statement may use one of two kinds of placeholders:
question marks (qmark style) or named placeholders (named style).
For the qmark style, *parameters* must be a
:term:`sequence` whose length must match the number of placeholders,
or a :exc:`ProgrammingError` is raised.
For the named style, *parameters* must be
an instance of a :class:`dict` (or a subclass),
which must contain keys for all named parameters;
any extra items are ignored.
Here's an example of both styles:

.. testcode::

con = sqlite3.connect(":memory:")
   cur = con.execute("CREATE TABLE lang(name, first_appeared)")

# This is the named style used with executemany():
   data = (
       {"name": "C", "year": 1972},
       {"name": "Fortran", "year": 1957},
       {"name": "Python", "year": 1991},
       {"name": "Go", "year": 2009},
   )
   cur.executemany("INSERT INTO lang VALUES(:name, :year)", data)

# This is the qmark style used in a SELECT query:
   params = (1972,)
   cur.execute("SELECT * FROM lang WHERE first_appeared = ?", params)
   print(cur.fetchall())
   con.close()

.. testoutput::
   :hide:

[('C', 1972)]

.. note::

:pep:`249` numeric placeholders are *not* supported.
   If used, they will be interpreted as named placeholders.

.. _sqlite3-adapters:

How to adapt custom Python types to SQLite values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SQLite supports only a limited set of data types natively.
To store custom Python types in SQLite databases, *adapt* them to one of the
:ref:`Python types SQLite natively understands <sqlite3-types>`.

There are two ways to adapt Python objects to SQLite types:
letting your object adapt itself, or using an *adapter callable*.
The latter will take precedence above the former.
For a library that exports a custom type,
it may make sense to enable that type to adapt itself.
As an application developer, it may make more sense to take direct control by
registering custom adapter functions.

.. _sqlite3-conform:

How to write adaptable objects
""""""""""""""""""""""""""""""

Suppose we have a :class:`!Point` class that represents a pair of coordinates,
``x`` and ``y``, in a Cartesian coordinate system.
The coordinate pair will be stored as a text string in the database,
using a semicolon to separate the coordinates.
This can be implemented by adding a ``__conform__(self, protocol)``
method which returns the adapted value.
The object passed to *protocol* will be of type :class:`PrepareProtocol`.

.. testcode::

class Point:
       def __init__(self, x, y):
           self.x, self.y = x, y

def __conform__(self, protocol):
           if protocol is sqlite3.PrepareProtocol:
               return f"{self.x};{self.y}"

con = sqlite3.connect(":memory:")
   cur = con.cursor()

cur.execute("SELECT ?", (Point(4.0, -3.2),))
   print(cur.fetchone()[0])
   con.close()

.. testoutput::
   :hide:

4.0;-3.2

How to register adapter callables
"""""""""""""""""""""""""""""""""

The other possibility is to create a function that converts the Python object
to an SQLite-compatible type.
This function can then be registered using :func:`register_adapter`.

.. testcode::

class Point:
       def __init__(self, x, y):
           self.x, self.y = x, y

def adapt_point(point):
       return f"{point.x};{point.y}"

sqlite3.register_adapter(Point, adapt_point)

con = sqlite3.connect(":memory:")
   cur = con.cursor()

cur.execute("SELECT ?", (Point(1.0, 2.5),))
   print(cur.fetchone()[0])
   con.close()

.. testoutput::
   :hide:

1.0;2.5

.. _sqlite3-converters:

How to convert SQLite values to custom Python types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Writing an adapter lets you convert *from* custom Python types *to* SQLite
values.
To be able to convert *from* SQLite values *to* custom Python types,
we use *converters*.

Let's go back to the :class:`!Point` class. We stored the x and y coordinates
separated via semicolons as strings in SQLite.

First, we'll define a converter function that accepts the string as a parameter
and constructs a :class:`!Point` object from it.

.. note::

Converter functions are **always** passed a :class:`bytes` object,
   no matter the underlying SQLite data type.

.. testcode::

def convert_point(s):
       x, y = map(float, s.split(b";"))
       return Point(x, y)

We now need to tell :mod:`!sqlite3` when it should convert a given SQLite value.
This is done when connecting to a database, using the *detect_types* parameter
of :func:`connect`. There are three options:

* Implicit: set *detect_types* to :const:`PARSE_DECLTYPES`
* Explicit: set *detect_types* to :const:`PARSE_COLNAMES`
* Both: set *detect_types* to
  ``sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES``.
  Column names take precedence over declared types.

The following example illustrates the implicit and explicit approaches:

.. testcode::

class Point:
       def __init__(self, x, y):
           self.x, self.y = x, y

def __repr__(self):
           return f"Point({self.x}, {self.y})"

def adapt_point(point):
       return f"{point.x};{point.y}"

def convert_point(s):
       x, y = list(map(float, s.split(b";")))
       return Point(x, y)

# Register the adapter and converter
   sqlite3.register_adapter(Point, adapt_point)
   sqlite3.register_converter("point", convert_point)

# 1) Parse using declared types
   p = Point(4.0, -3.2)
   con = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
   cur = con.execute("CREATE TABLE test(p point)")

cur.execute("INSERT INTO test(p) VALUES(?)", (p,))
   cur.execute("SELECT p FROM test")
   print("with declared types:", cur.fetchone()[0])
   cur.close()
   con.close()

# 2) Parse using column names
   con = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_COLNAMES)
   cur = con.execute("CREATE TABLE test(p)")

cur.execute("INSERT INTO test(p) VALUES(?)", (p,))
   cur.execute('SELECT p AS "p [point]" FROM test')
   print("with column names:", cur.fetchone()[0])
   cur.close()
   con.close()

.. testoutput::
   :hide:

with declared types: Point(4.0, -3.2)
   with column names: Point(4.0, -3.2)

.. _sqlite3-adapter-converter-recipes:

Adapter and converter recipes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section shows recipes for common adapters and converters.

.. testcode::

import datetime as dt
   import sqlite3

def adapt_date_iso(val):
       """Adapt datetime.date to ISO 8601 date."""
       return val.isoformat()

def adapt_datetime_iso(val):
       """Adapt datetime.datetime to timezone-naive ISO 8601 date."""
       return val.replace(tzinfo=None).isoformat()

def adapt_datetime_epoch(val):
       """Adapt datetime.datetime to Unix timestamp."""
       return int(val.timestamp())

sqlite3.register_adapter(dt.date, adapt_date_iso)
   sqlite3.register_adapter(dt.datetime, adapt_datetime_iso)
   sqlite3.register_adapter(dt.datetime, adapt_datetime_epoch)

def convert_date(val):
       """Convert ISO 8601 date to datetime.date object."""
       return dt.date.fromisoformat(val.decode())

def convert_datetime(val):
       """Convert ISO 8601 datetime to datetime.datetime object."""
       return dt.datetime.fromisoformat(val.decode())

def convert_timestamp(val):
       """Convert Unix epoch timestamp to datetime.datetime object."""
       return dt.datetime.fromtimestamp(int(val))

sqlite3.register_converter("date", convert_date)
   sqlite3.register_converter("datetime", convert_datetime)
   sqlite3.register_converter("timestamp", convert_timestamp)

.. testcode::
   :hide:

when = dt.datetime(2019, 5, 18, 15, 17, 8, 123456)

assert adapt_date_iso(when.date()) == "2019-05-18"
   assert convert_date(b"2019-05-18") == when.date()

assert adapt_datetime_iso(when) == "2019-05-18T15:17:08.123456"
   assert convert_datetime(b"2019-05-18T15:17:08.123456") == when

# Using current time as fromtimestamp() returns local date/time.
   # Dropping microseconds as adapt_datetime_epoch truncates fractional second part.
   now = dt.datetime.now().replace(microsecond=0)
   current_timestamp = int(now.timestamp())

assert adapt_datetime_epoch(now) == current_timestamp
   assert convert_timestamp(str(current_timestamp).encode()) == now

.. _sqlite3-connection-shortcuts:

How to use connection shortcut methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Using the :meth:`~Connection.execute`,
:meth:`~Connection.executemany`, and :meth:`~Connection.executescript`
methods of the :class:`Connection` class, your code can
be written more concisely because you don't have to create the (often
superfluous) :class:`Cursor` objects explicitly. Instead, the :class:`Cursor`
objects are created implicitly and these shortcut methods return the cursor
objects. This way, you can execute a ``SELECT`` statement and iterate over it
directly using only a single call on the :class:`Connection` object.

.. testcode::

# Create and fill the table.
   con = sqlite3.connect(":memory:")
   con.execute("CREATE TABLE lang(name, first_appeared)")
   data = [
       ("C++", 1985),
       ("Objective-C", 1984),
   ]
   con.executemany("INSERT INTO lang(name, first_appeared) VALUES(?, ?)", data)

# Print the table contents
   for row in con.execute("SELECT name, first_appeared FROM lang"):
       print(row)

print("I just deleted", con.execute("DELETE FROM lang").rowcount, "rows")

# close() is not a shortcut method and it's not called automatically;
   # the connection object should be closed manually
   con.close()

.. testoutput::
   :hide:

('C++', 1985)
   ('Objective-C', 1984)
   I just deleted 2 rows

.. _sqlite3-connection-context-manager:

How to use the connection context manager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A :class:`Connection` object can be used as a context manager that
automatically commits or rolls back open transactions when leaving the body of
the context manager.
If the body of the :keyword:`with` statement finishes without exceptions,
the transaction is committed.
If this commit fails,
or if the body of the ``with`` statement raises an uncaught exception,
the transaction is rolled back.
If :attr:`~Connection.autocommit` is ``False``,
a new transaction is implicitly opened after committing or rolling back.

If there is no open transaction upon leaving the body of the ``with`` statement,
or if :attr:`~Connection.autocommit` is ``True``,
the context manager does nothing.

.. note::
   The context manager neither implicitly opens a new transaction
   nor closes the connection. If you need a closing context manager, consider
   using :meth:`contextlib.closing`.

.. testcode::

con = sqlite3.connect(":memory:")
   con.execute("CREATE TABLE lang(id INTEGER PRIMARY KEY, name VARCHAR UNIQUE)")

# Successful, con.commit() is called automatically afterwards
   with con:
       con.execute("INSERT INTO lang(name) VALUES(?)", ("Python",))

# con.rollback() is called after the with block finishes with an exception,
   # the exception is still raised and must be caught
   try:
       with con:
           con.execute("INSERT INTO lang(name) VALUES(?)", ("Python",))
   except sqlite3.IntegrityError:
       print("couldn't add Python twice")

# Connection object used as context manager only commits or rollbacks transactions,
   # so the connection object should be closed manually
   con.close()

.. testoutput::
   :hide:

couldn't add Python twice

.. _sqlite3-uri-tricks:

How to work with SQLite URIs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some useful URI tricks include:

* Open a database in read-only mode:

.. doctest::

>>> con = sqlite3.connect("file:tutorial.db?mode=ro", uri=True)
   >>> con.execute("CREATE TABLE readonly(data)")
   Traceback (most recent call last):
   OperationalError: attempt to write a readonly database
   >>> con.close()

* Do not implicitly create a new database file if it does not already exist;
  will raise :exc:`~sqlite3.OperationalError` if unable to create a new file:

.. doctest::
