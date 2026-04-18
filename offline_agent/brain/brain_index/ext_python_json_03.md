# Python json (3/3)
source: https://github.com/python/cpython/blob/main/Doc/library/json.rst
repo: https://github.com/python/cpython
license: PSF License Version 2 | https://github.com/python/cpython/blob/main/LICENSE
fetched_at: 2026-04-15T11:52:35+00:00
pecifies that the names within a JSON object should be unique, but
does not mandate how repeated names in JSON objects should be handled.  By
default, this module does not raise an exception; instead, it ignores all but
the last name-value pair for a given name::

>>> weird_json = '{"x": 1, "x": 2, "x": 3}'
   >>> json.loads(weird_json)
   {'x': 3}

The *object_pairs_hook* parameter can be used to alter this behavior.

Top-level Non-Object, Non-Array Values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The old version of JSON specified by the obsolete :rfc:`4627` required that
the top-level value of a JSON text must be either a JSON object or array
(Python :class:`dict` or :class:`list`), and could not be a JSON null,
boolean, number, or string value.  :rfc:`7159` removed that restriction, and
this module does not and has never implemented that restriction in either its
serializer or its deserializer.

Regardless, for maximum interoperability, you may wish to voluntarily adhere
to the restriction yourself.

Implementation Limitations
^^^^^^^^^^^^^^^^^^^^^^^^^^

Some JSON deserializer implementations may set limits on:

* the size of accepted JSON texts
* the maximum level of nesting of JSON objects and arrays
* the range and precision of JSON numbers
* the content and maximum length of JSON strings

This module does not impose any such limits beyond those of the relevant
Python datatypes themselves or the Python interpreter itself.

When serializing to JSON, beware any such limitations in applications that may
consume your JSON.  In particular, it is common for JSON numbers to be
deserialized into IEEE 754 double precision numbers and thus subject to that
representation's range and precision limitations.  This is especially relevant
when serializing Python :class:`int` values of extremely large magnitude, or
when serializing instances of "exotic" numerical types such as
:class:`decimal.Decimal`.

.. _json-commandline:
.. program:: json

Command-line interface
----------------------

.. module:: json.tool
    :synopsis: A command-line interface to validate and pretty-print JSON.

**Source code:** :source:`Lib/json/tool.py`

--------------

The :mod:`!json` module can be invoked as a script via ``python -m json``
to validate and pretty-print JSON objects. The :mod:`!json.tool` submodule
implements this interface.

If the optional ``infile`` and ``outfile`` arguments are not
specified, :data:`sys.stdin` and :data:`sys.stdout` will be used respectively:

.. code-block:: shell-session

$ echo '{"json": "obj"}' | python -m json
    {
        "json": "obj"
    }
    $ echo '{1.2:3.4}' | python -m json
    Expecting property name enclosed in double quotes: line 1 column 2 (char 1)

.. versionchanged:: 3.5
   The output is now in the same order as the input. Use the
   :option:`--sort-keys` option to sort the output of dictionaries
   alphabetically by key.

.. versionchanged:: 3.14
   The :mod:`!json` module may now be directly executed as
   ``python -m json``. For backwards compatibility, invoking
   the CLI as ``python -m json.tool`` remains supported.

Command-line options
^^^^^^^^^^^^^^^^^^^^

.. option:: infile

The JSON file to be validated or pretty-printed:

.. code-block:: shell-session

$ python -m json mp_films.json
      [
          {
              "title": "And Now for Something Completely Different",
              "year": 1971
          },
          {
              "title": "Monty Python and the Holy Grail",
              "year": 1975
          }
      ]

If *infile* is not specified, read from :data:`sys.stdin`.

.. option:: outfile

Write the output of the *infile* to the given *outfile*. Otherwise, write it
   to :data:`sys.stdout`.

.. option:: --sort-keys

Sort the output of dictionaries alphabetically by key.

.. versionadded:: 3.5

.. option:: --no-ensure-ascii

Disable escaping of non-ascii characters, see :func:`json.dumps` for more information.

.. versionadded:: 3.9

.. option:: --json-lines

Parse every input line as separate JSON object.

.. versionadded:: 3.8

.. option:: --indent, --tab, --no-indent, --compact

Mutually exclusive options for whitespace control.

.. versionadded:: 3.9

.. option:: -h, --help

Show the help message.

.. rubric:: Footnotes

.. [#rfc-errata] As noted in `the errata for RFC 7159
   <https://www.rfc-editor.org/errata_search.php?rfc=7159>`_,
   JSON permits literal U+2028 (LINE SEPARATOR) and
   U+2029 (PARAGRAPH SEPARATOR) characters in strings, whereas JavaScript
   (as of ECMAScript Edition 5.1) does not.
